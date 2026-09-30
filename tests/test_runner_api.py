import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from economic_sim import Simulation
from economic_sim.api import app, service
from economic_sim.checkpoint import load_checkpoint, save_checkpoint
from economic_sim.config import Config, load_config
from economic_sim.contracts import PolicyPatch
from economic_sim.money import money
from economic_sim.runner import Command, Conflict, Runner
from economic_sim.treasury import BondBid, clear_bond_auction


@pytest.fixture
def small_config():
    return load_config("configs/t05-crisis.yaml")


def wait_week(runner, week, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = runner.snapshot()
        if snap["week"] >= week or snap["status"] in {"ERROR", "TERMINATED"}:
            return snap
        runner.wait_event(snap["sequence_number"], 0.5)
    pytest.fail(f"La settimana {week} non è stata pubblicata")


def test_checkpoint_roundtrip_and_next_week(small_config, tmp_path):
    first = Simulation.from_config(small_config)
    first.step()
    path = tmp_path / "checkpoint.json"
    original_checksum = save_checkpoint(first, path)
    resumed, runtime = load_checkpoint(path)
    assert runtime["commands"] == []
    assert resumed.run_id != first.run_id
    assert resumed.economic_checksum() == original_checksum
    assert len(resumed.market_results) == len(first.market_results)
    first.step()
    resumed.step()
    assert first.economic_checksum() == resumed.economic_checksum()
    tampered = path.read_text(encoding="utf-8").replace('"week":1', '"week":2', 1)
    path.write_text(tampered, encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum"):
        load_checkpoint(path)


def test_runner_idempotency_pause_policy_and_concurrent_step(small_config):
    runner = Runner(Simulation.from_config(small_config))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(runner.command, [Command("same", "step"), Command("same", "step")])
            )
        assert results[0] == results[1]
        assert wait_week(runner, 1)["status"] == "PAUSED"
        assert runner.snapshot()["week"] == 1
        patch = PolicyPatch(policy_rate=0.04)
        accepted = runner.command(Command("policy", "policy", submitted_at="test", patch=patch))
        assert accepted["effective_week"] == 2
        runner.command(Command("batch", "batch", steps=10))
        runner.command(Command("stop", "pause"))
        snap = runner.snapshot()
        if snap["status"] == "PAUSING":
            runner.wait_event(snap["sequence_number"], 30)
            snap = runner.snapshot()
        assert snap["status"] == "PAUSED"
        assert 1 <= snap["week"] <= 2
        assert len(runner.metrics()) == snap["week"]
        assert len(runner.csv().splitlines()) == snap["week"] + 1
    finally:
        runner.close()


def test_policy_during_step_uses_next_available_week(small_config):
    sim = Simulation.from_config(small_config)
    original = sim.finance.service
    inside = threading.Event()

    def slow_service():
        inside.set()
        time.sleep(0.2)
        return original()

    sim.finance.service = slow_service
    runner = Runner(sim)
    try:
        runner.command(Command("go", "step"))
        assert inside.wait(5)
        assert sim.week == 1  # settimana in lavorazione, non ancora pubblicata
        accepted = runner.command(
            Command("late", "policy", submitted_at="test", patch=PolicyPatch(policy_rate=0.04))
        )
        assert accepted["effective_week"] == 2
        assert runner.snapshot()["week"] == 0
        assert wait_week(runner, 1)["status"] == "PAUSED"
        assert sim.finance.policy.policy_rate != 0.04
        runner.command(Command("next", "step"))
        assert wait_week(runner, 2)["status"] == "PAUSED"
        assert sim.finance.policy.policy_rate == 0.04
    finally:
        runner.close()


def test_batch_pause_finishes_only_current_step(small_config):
    sim = Simulation.from_config(small_config)
    original = sim.step

    def slow_step():
        time.sleep(0.2)
        return original()

    sim.step = slow_step
    runner = Runner(sim)
    try:
        runner.command(Command("ten", "batch", steps=10))
        deadline = time.monotonic() + 5
        while not runner._in_step and time.monotonic() < deadline:
            time.sleep(0.001)
        assert runner._in_step
        start = time.monotonic()
        runner.command(Command("pause", "pause"))
        assert time.monotonic() - start < 0.2
        assert runner.snapshot()["week"] == 0
        assert wait_week(runner, 1)["status"] == "PAUSED"
        assert len(runner.metrics()) == 1
    finally:
        runner.close()


def test_checkpoint_keeps_pending_policy_and_command_id(small_config, tmp_path):
    runner = Runner(Simulation.from_config(small_config))
    try:
        command = Command(
            "rate-next",
            "policy",
            submitted_at="test",
            effective_week=2,
            patch=PolicyPatch(policy_rate=0.04, weekly_bond_purchase_budget=money("0")),
        )
        accepted = runner.command(command)
        checkpoint = tmp_path / "pending.json"
        runner.checkpoint(checkpoint)
        sim, runtime = load_checkpoint(checkpoint)
        resumed = Runner(sim, runtime=runtime)
        try:
            assert resumed.command(command) == accepted
            assert resumed.snapshot()["pending_commands"][0]["effective_week"] == 2
            resumed.command(Command("two", "batch", steps=2, max_speed=True))
            assert wait_week(resumed, 2)["status"] == "PAUSED"
            assert sim.finance.policy.policy_rate == 0.04
            assert sim.treasury.active_bond_purchase_budget == money("0")
        finally:
            resumed.close()
    finally:
        runner.close()


def test_distinct_one_time_orders_keep_individual_price_limits(small_config):
    sim = Simulation.from_config(small_config)
    runner = Runner(sim)
    try:
        a = runner.command(
            Command("bond-a", "bond_purchase", effective_week=1, budget="2", max_price="1.0")
        )
        b = runner.command(
            Command("bond-b", "bond_purchase", effective_week=1, budget="2", max_price="0.9")
        )
        assert a["server_sequence"] + 1 == b["server_sequence"]
        assert len(sim.treasury.pending_cb_orders[1]) == 2
        price, allocation, _ = clear_bond_auction(
            4,
            [
                BondBid(sim.central_bank.id, 2, money("1.0"), money("2"), -1),
                BondBid(sim.central_bank.id, 2, money("0.9"), money("2"), -2),
            ],
            money("0.8"),
        )
        assert price == money("0.9") and allocation == {-1: 2, -2: 2}
    finally:
        runner.close()


def test_manual_batch_and_two_speeds_have_same_economy(small_config):
    checksums = []
    for mode in ("manual", "paced", "maximum"):
        runner = Runner(Simulation.from_config(small_config))
        try:
            if mode == "paced":
                runner.command(Command("speed", "speed", speed=5))
            if mode == "maximum":
                runner.command(Command("speed", "speed", max_speed=True))
            if mode == "manual":
                for week in range(1, 4):
                    runner.command(Command(f"step-{week}", "step"))
                    assert wait_week(runner, week)["status"] == "PAUSED"
            else:
                runner.command(Command("three", "batch", steps=3))
                assert wait_week(runner, 3)["status"] == "PAUSED"
            checksums.append(runner.sim.economic_checksum())
        finally:
            runner.close()
    assert len(set(checksums)) == 1


def test_sovereign_default_is_runner_termination(small_config):
    data = small_config.model_dump()
    data["central_bank"].update(
        primary_bond_purchases_enabled=False, weekly_bond_purchase_budget="0"
    )
    data["government"].update(household_bond_budget_share=0, bank_bond_budget_share=0)
    sim = Simulation.from_config(Config.model_validate(data))
    # Posiziona la prova al confine di scadenza del bond ereditato.
    sim.week = 51
    sim.state_version = 51
    runner = Runner(sim)
    try:
        runner.command(Command("until-default", "step"))
        snap = wait_week(runner, 52, timeout=30)
        assert snap["status"] == "TERMINATED"
        assert snap["week"] == 52
        assert sim.last_error is None
        sim.validate()
    finally:
        runner.close()


def test_runner_error_rolls_back_and_blocks_commands(small_config):
    sim = Simulation.from_config(small_config)
    checksum = sim.economic_checksum()

    def fail():
        raise RuntimeError("guasto iniettato")

    sim.finance.service = fail
    runner = Runner(sim)
    try:
        runner.command(Command("go", "step"))
        snap = wait_week(runner, 1)
        assert snap["status"] == "ERROR" and snap["week"] == 0
        assert sim.economic_checksum() == checksum
        with pytest.raises(Conflict):
            runner.command(Command("again", "step"))
    finally:
        runner.close()


def test_http_snapshot_commands_history_and_import(small_config):
    with TestClient(app) as client:
        created = client.post(
            "/api/runs", json={"schema_version": 1, "config_path": "configs/t05-crisis.yaml"}
        )
        assert created.status_code == 200
        run_id = created.json()["run_id"]
        assert created.json()["week"] == 0
        with client.websocket_connect(f"/api/runs/{run_id}/events") as socket:
            initial = socket.receive_json()
            assert initial["run_id"] == run_id
            command = client.post(
                f"/api/runs/{run_id}/commands",
                json={"schema_version": 1, "command_id": "http-step", "type": "step"},
            )
            assert command.status_code == 200
            assert (
                client.post(
                    f"/api/runs/{run_id}/commands",
                    json={"schema_version": 1, "command_id": "http-step", "type": "step"},
                ).json()
                == command.json()
            )
            events = socket.receive_json()
            assert events["sequence_number"] > initial["sequence_number"]
        runner = service.current(run_id)
        assert wait_week(runner, 1)["status"] == "PAUSED"
        assert len(client.get(f"/api/runs/{run_id}/metrics").json()["rows"]) == 1
        assert len(client.get(f"/api/runs/{run_id}/export/metrics.csv").text.splitlines()) == 2
        agent_id = int(runner.sim.people.ids[0])
        assert (
            client.get(f"/api/runs/{run_id}/agents/{agent_id}?limit=2").json()["agent_id"]
            == agent_id
        )
        path = "runs/test-api-checkpoint.json"
        assert (
            client.post(
                f"/api/runs/{run_id}/checkpoints", json={"schema_version": 1, "path": path}
            ).status_code
            == 200
        )
        imported = client.post("/api/runs/import", json={"schema_version": 1, "path": path})
        assert imported.status_code == 200
        assert imported.json()["run_id"] != run_id
        assert imported.json()["checksum"] == runner.sim.economic_checksum()


def test_frontend_create_overrides_and_served_build():
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Laboratorio monetario" in page.text
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/unknown").status_code == 404
        created = client.post(
            "/api/runs",
            json={
                "schema_version": 1,
                "config_path": "configs/t05-crisis.yaml",
                "seed": 7,
                "initial_population": 120,
                "initial_banks": 2,
            },
        )
        assert created.status_code == 200
        run_id = created.json()["run_id"]
        config = service.current(run_id).sim.config.simulation
        assert (config.seed, config.initial_population, config.initial_banks) == (7, 120, 2)
        assert created.json()["week"] == 0
        assert created.json()["status"] == "PAUSED"


def test_facility_policy_pending_active_and_history(small_config):
    runner = Runner(Simulation.from_config(small_config))
    try:
        before = runner.snapshot()["central_bank_controls"]
        patch = PolicyPatch(
            emergency_lending_enabled=False,
            facility_cap_share=0.25,
            ordinary_haircut=0.10,
        )
        result = runner.command(Command("facility", "policy", submitted_at="test", patch=patch))
        pending = runner.snapshot()
        assert result["effective_week"] == 1
        assert pending["central_bank_controls"] == before
        assert pending["pending_commands"][0]["parameters"]["facility_cap_share"] == 0.25
        assert pending["decision_history"][-1]["command_id"] == "facility"
        runner.command(Command("one", "step"))
        after = wait_week(runner, 1)
        assert after["status"] == "PAUSED"
        assert after["central_bank_controls"]["emergency_lending_enabled"] is False
        assert after["central_bank_controls"]["facility_cap_share"] == 0.25
        assert after["central_bank_controls"]["ordinary_haircut"] == 0.10
        assert after["pending_commands"] == []
        assert len(runner.event_history()) == 1
        assert after["inventories"]["food"] == pytest.approx(
            sum(runner.sim.physical.quantities("inventory")[:, 0])
        )
    finally:
        runner.close()


def test_http_policy_patch_is_validated_and_scheduled():
    with TestClient(app) as client:
        created = client.post(
            "/api/runs", json={"schema_version": 1, "config_path": "configs/t05-crisis.yaml"}
        ).json()
        run_id = created["run_id"]
        result = client.post(
            f"/api/runs/{run_id}/commands",
            json={
                "schema_version": 1,
                "command_id": "http-policy",
                "type": "policy",
                "submitted_at": "test",
                "patch": {"policy_rate": 0.03, "emergency_lending_enabled": False},
            },
        )
        assert result.status_code == 200
        assert result.json()["effective_week"] == 1
        pending = client.get(f"/api/runs/{run_id}/snapshot").json()
        assert pending["central_bank_controls"]["policy_rate"] == 0.02
        assert pending["pending_commands"][0]["parameters"]["policy_rate"] == 0.03
