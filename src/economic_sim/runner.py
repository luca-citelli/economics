"""Un worker seriale per il motore; letture da uno snapshot pubblicato."""

import copy
import csv
import io
import threading
import time
from dataclasses import dataclass

from economic_sim.checkpoint import load_checkpoint, save_checkpoint
from economic_sim.contracts import PolicyPatch
from economic_sim.finance import PolicyState
from economic_sim.money import money
from economic_sim.serialization import canonical_value


class Conflict(ValueError):
    pass


@dataclass(frozen=True)
class Command:
    command_id: str
    type: str
    steps: int | None = None
    speed: float | None = None
    max_speed: bool = False
    effective_week: int | None = None
    submitted_at: str | None = None
    patch: PolicyPatch | None = None
    budget: str | None = None
    max_price: str | None = None


class Runner:
    def __init__(self, sim, *, browser_owned=False, runtime=None):
        self.sim = sim
        self.browser_owned = browser_owned
        self.clients = 0
        self._condition = threading.Condition()
        self._closed = False
        self._in_step = False
        self._remaining = 0
        self._mode = "PAUSED"
        self._speed = sim.config.runtime.default_steps_per_second
        self._max_speed = False
        self._effective_speed = 0.0
        self._last_runtime_error = None
        self._last_step_time = None
        self._last_start = None
        self._sequence = 0
        self._command_sequence = (runtime or {}).get("server_sequence", 0)
        self._commands = {row["command_id"]: row for row in (runtime or {}).get("commands", [])}
        self._policies = list((runtime or {}).get("policies", []))
        self._orders = list((runtime or {}).get("orders", []))
        self._core_snapshot = canonical_value(self.sim.snapshot())
        self._published_policy = self.sim.finance.policy
        self._history = [canonical_value(row) for row in sim.history]
        self._agent_data = {}
        self._transactions = {}
        self._journal_offset = 0
        self._capture_agents()
        self._snapshot = self._publish_locked()
        self._worker = threading.Thread(target=self._loop, name="economic-sim-worker", daemon=True)
        self._worker.start()

    def _publish_locked(self):
        snap = copy.deepcopy(self._core_snapshot)
        snap["status"] = self._mode
        snap["runner"] = {
            "requested_steps_per_second": self._speed,
            "effective_steps_per_second": self._effective_speed,
            "max_speed": self._max_speed,
            "remaining_steps": self._remaining,
            "clients": self.clients,
            "error": self._last_runtime_error,
        }
        snap["sequence_number"] = self._sequence
        snap["pending_commands"] = [
            {
                "command_id": row["command_id"],
                "type": row["type"],
                "effective_week": row["effective_week"],
            }
            for row in self._policies + self._orders
            if row["effective_week"] > self._core_snapshot["week"]
        ]
        return snap

    def snapshot(self):
        with self._condition:
            return copy.deepcopy(self._snapshot)

    def metrics(self, from_week=1, to_week=None):
        with self._condition:
            return copy.deepcopy(
                [
                    row
                    for row in self._history
                    if row["week"] >= from_week and (to_week is None or row["week"] <= to_week)
                ]
            )

    def csv(self):
        with self._condition:
            rows = copy.deepcopy(self._history)
        stream = io.StringIO()
        if rows:
            writer = csv.DictWriter(
                stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row))
            )
            writer.writeheader()
            writer.writerows(rows)
        return stream.getvalue()

    def agent(self, agent_id, offset=0, limit=50):
        with self._condition:
            if agent_id not in self._agent_data:
                raise KeyError(agent_id)
            transactions = self._transactions.get(agent_id, ())
            return {
                **copy.deepcopy(self._agent_data[agent_id]),
                "transactions": copy.deepcopy(transactions[offset : offset + limit]),
                "total_transactions": len(transactions),
                "offset": offset,
                "limit": limit,
            }

    def _capture_agents(self):
        sheets = self.sim.ledger.balance_sheets()
        for table, kind in (
            (self.sim.people, "person"),
            (self.sim.firms, "firm"),
            (self.sim.banks, "bank"),
        ):
            for row, entity_id in enumerate(table.ids):
                entity_id = int(entity_id)
                account = self.sim.deposits.get(entity_id)
                reserve = self.sim.reserves.get(entity_id)
                self._agent_data[entity_id] = {
                    "agent_id": entity_id,
                    "kind": kind,
                    "week": self.sim.week,
                    "columns": {k: canonical_value(v[row]) for k, v in table._columns.items()},
                    "deposit": str(self.sim.ledger.balance(account.asset)) if account else None,
                    "reserves": str(self.sim.ledger.balance(reserve.asset)) if reserve else None,
                    "balance_sheet": canonical_value(sheets[entity_id]),
                }
        journal = self.sim.ledger._journal
        for tx in journal[self._journal_offset :]:
            involved = {self.sim.ledger.accounts[p.account_id].entity_id for p in tx.postings}
            row = canonical_value(tx)
            for entity_id in involved:
                self._transactions.setdefault(entity_id, []).append(row)
        self._journal_offset = len(journal)

    def _notify(self):
        self._sequence += 1
        self._snapshot = self._publish_locked()
        self._condition.notify_all()

    def wait_event(self, after, timeout=1.0):
        with self._condition:
            self._condition.wait_for(lambda: self._sequence > after or self._closed, timeout)
            return copy.deepcopy(self._snapshot)

    def connect(self):
        with self._condition:
            self.clients += 1
            self._notify()

    def disconnect(self):
        with self._condition:
            self.clients = max(0, self.clients - 1)
            if (
                self.browser_owned
                and self.clients == 0
                and self.sim.config.runtime.pause_on_all_clients_disconnected
            ):
                if self._mode in {"RUNNING", "STEPPING"}:
                    self._mode = "PAUSING" if self._in_step else "PAUSED"
                    self._remaining = 0
            self._notify()

    def command(self, command: Command):
        with self._condition:
            published_week = self._core_snapshot["week"]
            if command.command_id in self._commands:
                return copy.deepcopy(self._commands[command.command_id])
            if self._closed:
                raise Conflict("Run sostituito da una nuova simulazione")
            if not command.command_id:
                raise ValueError("command_id richiesto")
            if self._mode in {"ERROR", "TERMINATED"}:
                raise Conflict(f"Run in stato {self._mode}")
            kind = command.type
            if kind in {"step", "batch", "run"}:
                if self._mode != "PAUSED":
                    raise Conflict(f"Comando {kind} incompatibile con {self._mode}")
                if kind == "batch" and (type(command.steps) is not int or command.steps < 1):
                    raise ValueError("steps deve essere un intero positivo")
                self._remaining = 1 if kind == "step" else command.steps if kind == "batch" else 0
                self._mode = "RUNNING" if kind == "run" else "STEPPING"
                self._last_start = None
            elif kind == "pause":
                if self._mode not in {"RUNNING", "STEPPING", "PAUSING", "PAUSED"}:
                    raise Conflict(f"Pausa incompatibile con {self._mode}")
                self._mode = "PAUSING" if self._in_step else "PAUSED"
                self._remaining = 0
            elif kind == "speed":
                if command.max_speed:
                    self._max_speed = True
                else:
                    if command.speed is None or not 0 < command.speed <= 1000:
                        raise ValueError("speed deve essere >0 e <=1000 settimane/s")
                    self._speed = command.speed
                    self._max_speed = False
                self._last_start = None
            elif kind == "policy":
                if not self.sim.config.execution.phases["financial_service"]:
                    raise Conflict("Politica monetaria disattivata nel profilo")
                if command.patch is None or command.submitted_at is None:
                    raise ValueError("patch e submitted_at richiesti")
                if (
                    command.patch.weekly_bond_purchase_budget is not None
                    and not self.sim.config.execution.phases["treasury"]
                ):
                    raise Conflict("Asta pubblica disattivata nel profilo")
                if (
                    command.patch.weekly_bond_purchase_budget is not None
                    and not self.sim.config.central_bank.primary_bond_purchases_enabled
                ):
                    raise Conflict("Acquisti BC periodici disattivati nello scenario")
                earliest = published_week + (2 if self._in_step else 1)
                week = command.effective_week or earliest
                if week < earliest:
                    raise ValueError(f"Prima settimana disponibile: {earliest}")
                self._validate_policy(week, command.patch)
                self._policies.append(
                    {
                        "command_id": command.command_id,
                        "type": kind,
                        "effective_week": week,
                        "patch": command.patch.model_dump(exclude_none=True),
                        "server_sequence": self._command_sequence + 1,
                        "submitted_at": command.submitted_at,
                    }
                )
                if not self._in_step:
                    self._apply_pending()
                    self._core_snapshot = canonical_value(self.sim.snapshot())
            elif kind == "bond_purchase":
                if not self.sim.config.execution.phases["treasury"]:
                    raise Conflict("Asta pubblica disattivata nel profilo")
                if command.budget is None or command.max_price is None:
                    raise ValueError("budget e max_price richiesti")
                if money(command.budget) <= 0 or money(command.max_price) <= 0:
                    raise ValueError("budget e max_price devono essere positivi")
                earliest = published_week + (2 if self._in_step else 1)
                week = command.effective_week or earliest
                if week < earliest:
                    raise ValueError(f"Prima settimana disponibile: {earliest}")
                self._orders.append(
                    {
                        "command_id": command.command_id,
                        "type": kind,
                        "effective_week": week,
                        "budget": command.budget,
                        "max_price": command.max_price,
                    }
                )
                if not self._in_step:
                    self._apply_pending()
                    self._core_snapshot = canonical_value(self.sim.snapshot())
            else:
                raise ValueError(f"Tipo di comando sconosciuto: {kind}")
            self._command_sequence += 1
            result = {
                "schema_version": 1,
                "command_id": command.command_id,
                "server_sequence": self._command_sequence,
                "type": kind,
                "status": self._mode,
                "effective_week": week if kind in {"policy", "bond_purchase"} else None,
                "week": published_week,
                "parameters": (
                    command.patch.model_dump(exclude_none=True)
                    if kind == "policy"
                    else {"budget": command.budget, "max_price": command.max_price}
                    if kind == "bond_purchase"
                    else {}
                ),
                "submitted_at": command.submitted_at,
            }
            result = canonical_value(result)
            self._commands[command.command_id] = result
            self._notify()
            return copy.deepcopy(result)

    def _validate_policy(self, week, patch):
        policy = self._published_policy
        data = {
            "reserve_rate": policy.reserve_rate,
            "policy_rate": policy.policy_rate,
            "emergency_rate": policy.emergency_rate,
        }
        candidate = {
            "effective_week": week,
            "server_sequence": self._command_sequence + 1,
            "patch": patch.model_dump(exclude_none=True),
        }
        for row in sorted(
            [*self._policies, candidate], key=lambda x: (x["effective_week"], x["server_sequence"])
        ):
            data.update({k: v for k, v in row["patch"].items() if k in data})
            PolicyState(**data)

    def _apply_pending(self):
        policy = self.sim.finance.policy
        data = {
            "reserve_rate": policy.reserve_rate,
            "policy_rate": policy.policy_rate,
            "emergency_rate": policy.emergency_rate,
        }
        for row in sorted(
            self._policies, key=lambda x: (x["effective_week"], x["server_sequence"])
        ):
            if row["effective_week"] > self.sim.week:
                for key, value in row["patch"].items():
                    if key in data:
                        data[key] = value
                    elif key == "weekly_bond_purchase_budget":
                        self.sim.treasury.pending_budgets[row["effective_week"]] = money(value)
                self.sim.finance.schedule_policy(row["effective_week"], **data)
        for week in {
            row["effective_week"] for row in self._orders if row["effective_week"] > self.sim.week
        }:
            self.sim.treasury.pending_cb_orders[week] = [
                (money(row["budget"]), money(row["max_price"]))
                for row in self._orders
                if row["effective_week"] == week
            ]

    def _loop(self):
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: self._closed or self._mode in {"RUNNING", "STEPPING"}
                )
                if self._closed:
                    return
                self._apply_pending()
                self._in_step = True
                started = time.perf_counter()
                previous_start = self._last_start
                self._last_start = started
            try:
                self.sim.step()
                error = None
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - started
            with self._condition:
                self._in_step = False
                interval = started - previous_start if previous_start is not None else elapsed
                self._effective_speed = 1.0 / interval if interval > 0 else 0.0
                if error:
                    self._mode = "ERROR"
                    self._last_runtime_error = error
                elif self.sim.status == "TERMINATED":
                    self._mode = "TERMINATED"
                elif self._mode == "PAUSING":
                    self._mode = "PAUSED"
                elif self._mode == "STEPPING":
                    self._remaining -= 1
                    if self._remaining == 0:
                        self._mode = "PAUSED"
                self._policies = [x for x in self._policies if x["effective_week"] > self.sim.week]
                self._orders = [x for x in self._orders if x["effective_week"] > self.sim.week]
                if not error and self.sim.status != "TERMINATED":
                    self._apply_pending()
                self._published_policy = self.sim.finance.policy
                self._core_snapshot = canonical_value(self.sim.snapshot())
                if not error:
                    self._history.append(canonical_value(self.sim.history[-1]))
                    self._capture_agents()
                self._notify()
                if self._mode in {"RUNNING", "STEPPING"} and not self._max_speed:
                    delay = max(0.0, 1.0 / self._speed - elapsed)
                    self._condition.wait(timeout=delay)

    def checkpoint(self, path):
        with self._condition:
            if self._mode != "PAUSED" or self._in_step:
                raise Conflict("Salvataggio disponibile solo in pausa")
            return save_checkpoint(
                self.sim,
                path,
                commands=self._commands.values(),
                server_sequence=self._command_sequence,
                policies=self._policies,
                orders=self._orders,
            )

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._worker.join()


class RunService:
    def __init__(self):
        self._lock = threading.Lock()
        self._runner = None

    def current(self, run_id):
        with self._lock:
            if self._runner is None or self._runner.sim.run_id != run_id:
                raise KeyError(run_id)
            return self._runner

    def create(self, config):
        from economic_sim.simulation import Simulation

        sim = Simulation.from_config(config)
        with self._lock:
            if self._runner:
                self._runner.close()
            self._runner = Runner(sim, browser_owned=True)
            return self._runner

    def import_checkpoint(self, path):
        sim, runtime = load_checkpoint(path)
        with self._lock:
            if self._runner:
                self._runner.close()
            self._runner = Runner(sim, browser_owned=True, runtime=runtime)
            return self._runner

    def close(self):
        with self._lock:
            if self._runner:
                self._runner.close()
                self._runner = None
