"""API locale v1: un solo RunService nel processo Uvicorn."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import yaml
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import Field, ValidationError, model_validator

from economic_sim.config import Config, StrictModel, load_config
from economic_sim.contracts import PolicyPatch
from economic_sim.runner import Command, Conflict, RunService

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
CONFIGS = ROOT / "configs"
WEB = Path(__file__).resolve().parent / "web"
service = RunService()


@asynccontextmanager
async def lifespan(_app):
    yield
    await asyncio.to_thread(service.close)


app = FastAPI(title="Economic Sim", version="1", lifespan=lifespan)


class CreateRun(StrictModel):
    schema_version: Literal[1]
    config_path: str = "configs/t05.yaml"
    seed: Annotated[int, Field(ge=0, lt=2**63)] | None = None
    initial_population: Annotated[int, Field(ge=1, le=1_000_000)] | None = None
    initial_banks: Annotated[int, Field(ge=2, le=1000)] | None = None


class ImportRun(StrictModel):
    schema_version: Literal[1]
    path: str


class SaveRun(StrictModel):
    schema_version: Literal[1]
    path: str


class CommandBody(StrictModel):
    schema_version: Literal[1]
    command_id: Annotated[str, Field(min_length=1)]
    type: Literal["step", "batch", "run", "pause", "speed", "policy", "bond_purchase"]
    steps: Annotated[int, Field(ge=1)] | None = None
    speed: Annotated[float, Field(gt=0, le=1000)] | None = None
    max_speed: bool = False
    submitted_at: str | None = None
    effective_week: Annotated[int, Field(ge=1)] | None = None
    patch: PolicyPatch | None = None
    budget: str | None = None
    max_price: str | None = None

    @model_validator(mode="after")
    def required_fields(self):
        if self.type == "batch" and self.steps is None:
            raise ValueError("batch richiede steps")
        if self.type == "policy" and (self.patch is None or self.submitted_at is None):
            raise ValueError("policy richiede patch e submitted_at")
        if self.type == "speed" and not self.max_speed and self.speed is None:
            raise ValueError("speed richiede speed o max_speed")
        if self.type == "bond_purchase" and (self.budget is None or self.max_price is None):
            raise ValueError("bond_purchase richiede budget e max_price")
        return self


def _safe_path(path, directory, suffix):
    target = (ROOT / path).resolve()
    if not target.is_relative_to(directory.resolve()) or target.suffix.lower() != suffix:
        raise ValueError(f"Il file deve essere {suffix} nella directory {directory.name}/")
    return target


def _runner(run_id):
    try:
        return service.current(run_id)
    except KeyError as exc:
        raise HTTPException(404, detail="Run non trovato") from exc


@app.exception_handler(Conflict)
async def conflict_handler(_request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=409, content={"schema_version": 1, "error": "conflict", "detail": str(exc)}
    )


@app.exception_handler(ValueError)
async def value_handler(_request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=400, content={"schema_version": 1, "error": "invalid", "detail": str(exc)}
    )


@app.post("/api/runs")
def create_run(body: CreateRun):
    try:
        config = load_config(_safe_path(body.config_path, CONFIGS, ".yaml"))
        changes = body.model_dump(exclude_none=True, exclude={"schema_version", "config_path"})
        if changes:
            data = config.model_dump()
            data["simulation"].update(changes)
            config = Config.model_validate(data)
        return service.create(config).snapshot()
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise HTTPException(400, detail=f"Scenario non valido: {exc}") from exc


@app.get("/api/runs/{run_id}/snapshot")
def snapshot(run_id: str):
    return _runner(run_id).snapshot()


@app.post("/api/runs/{run_id}/commands")
def command(run_id: str, body: CommandBody):
    data = body.model_dump(exclude={"schema_version", "patch"})
    return _runner(run_id).command(Command(**data, patch=body.patch))


@app.get("/api/runs/{run_id}/metrics")
def metrics(
    run_id: str,
    from_week: Annotated[int, Query(ge=1)] = 1,
    to_week: Annotated[int | None, Query(ge=1)] = None,
):
    if to_week is not None and to_week < from_week:
        raise ValueError("to_week precede from_week")
    return {"schema_version": 1, "rows": _runner(run_id).metrics(from_week, to_week)}


@app.get("/api/runs/{run_id}/event-history")
def event_history(run_id: str):
    return {"schema_version": 1, "rows": _runner(run_id).event_history()}


@app.get("/api/runs/{run_id}/markets/{market_id}")
def market(run_id: str, market_id: str):
    snapshot = _runner(run_id).snapshot()
    for row in snapshot["markets"]:
        if row["market_id"] == market_id:
            return {"schema_version": 1, "week": snapshot["week"], "market": row}
    raise HTTPException(404, detail="Mercato non presente nell'ultimo snapshot")


@app.get("/api/runs/{run_id}/agents/{agent_id}")
def agent(
    run_id: str,
    agent_id: int,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    try:
        return {"schema_version": 1, **_runner(run_id).agent(agent_id, offset, limit)}
    except KeyError as exc:
        raise HTTPException(404, detail="Agente non trovato") from exc


@app.post("/api/runs/{run_id}/checkpoints")
def checkpoint(run_id: str, body: SaveRun):
    path = _safe_path(body.path, RUNS, ".json")
    checksum = _runner(run_id).checkpoint(path)
    return {"schema_version": 1, "path": str(path.relative_to(ROOT)), "economic_checksum": checksum}


@app.post("/api/runs/import")
def import_run(body: ImportRun):
    path = _safe_path(body.path, RUNS, ".json")
    try:
        return service.import_checkpoint(path).snapshot()
    except (OSError, KeyError, TypeError, ValidationError) as exc:
        raise HTTPException(400, detail=f"Checkpoint non valido: {exc}") from exc


@app.get("/api/runs/{run_id}/export/metrics.csv", response_class=PlainTextResponse)
def export_csv(run_id: str):
    return PlainTextResponse(_runner(run_id).csv(), media_type="text/csv; charset=utf-8")


@app.websocket("/api/runs/{run_id}/events")
async def events(socket: WebSocket, run_id: str):
    try:
        runner = service.current(run_id)
    except KeyError:
        await socket.close(code=4404)
        return
    await socket.accept()
    runner.connect()
    try:
        snapshot = runner.snapshot()
        await socket.send_json(snapshot)
        sequence = snapshot["sequence_number"]
        while True:
            update = await asyncio.to_thread(runner.wait_event, sequence)
            if update["sequence_number"] > sequence:
                await asyncio.sleep(1.0 / runner.sim.config.runtime.max_ui_updates_per_second)
                update = runner.snapshot()
                await socket.send_json(update)
                sequence = update["sequence_number"]
            else:
                # Un receive non bloccante rileva la chiusura anche senza nuovi eventi.
                try:
                    message = await asyncio.wait_for(socket.receive(), timeout=0.01)
                    if message["type"] == "websocket.disconnect":
                        break
                except TimeoutError:
                    pass
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        runner.disconnect()


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Serve the production build without exposing arbitrary local files."""
    index = WEB / "index.html"
    if not index.is_file():
        raise HTTPException(
            404, detail="Frontend non compilato: eseguire npm run build in frontend/"
        )
    if path:
        if path.startswith("api/"):
            raise HTTPException(404, detail="Endpoint API non trovato")
        asset = (WEB / path).resolve()
        if asset.is_relative_to(WEB.resolve()) and asset.is_file():
            return FileResponse(asset)
        if path.startswith("assets/") or "." in Path(path).name:
            raise HTTPException(404, detail="Risorsa non trovata")
    return FileResponse(index)
