from dataclasses import fields
from types import MappingProxyType
from uuid import uuid4

import numpy as np

from economic_sim import __version__
from economic_sim.accounting.inventory import InventoryAccounting
from economic_sim.accounting.settlement import Settlement
from economic_sim.accounting.step_transaction import StepTransaction
from economic_sim.agents.firms import plan
from economic_sim.agents.households import consume_households
from economic_sim.agents.production import operating_close, produce
from economic_sim.agents.state import LAYOUT_VERSION, AgentView, readonly_copy
from economic_sim.config import PHASES, Config
from economic_sim.contracts import Snapshot
from economic_sim.initialization import initialize
from economic_sim.markets.capital import buy_capital, plan_investment
from economic_sim.markets.labor import match_and_pay
from economic_sim.markets.resources import buy_resources
from economic_sim.metrics.weekly import collect, export_csv, firm_accounts, initialize_metrics
from economic_sim.money import ZERO, money_context
from economic_sim.serialization import canonical_value, checksum
from economic_sim.validation import validate_state


class Simulation:
    """Motore sincrono a proprietario unico; il runner concorrente resta T06."""

    @classmethod
    def from_config(cls, config: Config):
        # Rivalida anche oggetti costruiti con model_copy(update=...) senza validazione.
        config = Config.model_validate(config.model_dump())
        state = initialize(config)
        sim = cls()
        sim.config = config
        sim.run_id = str(uuid4())  # solo identità della sessione, esclusa dall'economia
        sim.week = 0
        sim.state_version = 0
        for field in fields(state):
            setattr(sim, field.name, getattr(state, field.name))
        sim.deposits = MappingProxyType(sim.deposits)
        sim.reserves = MappingProxyType(sim.reserves)
        sim.bonds = MappingProxyType(sim.bonds)
        sim.share_issues = MappingProxyType(sim.share_issues)
        sim._loans = {}
        sim.loans = MappingProxyType(sim._loans)
        sim.settlement = Settlement(sim.ledger, sim.deposits, sim.reserves, sim._loans)
        sim.products = sorted(config.catalog.products, key=lambda p: p.id)
        sim.product_by_name = {p.name: p for p in sim.products}
        sim.inventory = InventoryAccounting(sim)
        sim.employment = {}
        sim.status = "PAUSED"
        sim.last_error = None
        sim.market_results = []
        sim.events = []
        sim.phase_trace = []
        initialize_metrics(sim)
        sim.validate()
        return sim

    def validate(self, *, full=True):
        validate_state(self, full=full)

    @money_context
    def step(self):
        if self.config.execution.profile != "real_economy":
            raise ValueError("step richiede il profilo incrementale real_economy")
        if self.status != "PAUSED":
            raise ValueError("Simulazione in ERROR: ricreare il run prima di proseguire")
        if self.loans:
            raise ValueError("Il profilo T02 non esegue il servizio dei prestiti")
        undo = StepTransaction(self)
        try:
            self.week += 1
            self.events, self.market_results = [], []
            self.phase_trace = ["opening"]
            for firm_id in self.firms.ids:
                firm = int(firm_id)
                quantity = self.physical.quantity(firm, 11, "pending_capital")
                if quantity > 0:
                    self.inventory.install_capital(firm, quantity)
            f = len(self.firms.ids)
            self.output = np.zeros(f)
            self.output_costs = [ZERO] * f
            self.input_costs = [ZERO] * f
            self.inputs_used = np.zeros((f, 3))
            self.opening_capacity = np.array(
                [
                    self.physical.quantity(int(i), 11, "installed_capital")
                    * self.products[int(p) - 1].capacity_per_capital
                    for i, p in zip(self.firms.ids, self.firms.column("product_id"), strict=True)
                ]
            )
            start_accounts = firm_accounts(self)
            labor, consumption, investment, depreciation, spoilage = {}, ZERO, ZERO, ZERO, ZERO
            for phase in PHASES:
                if not self.config.execution.phases[phase]:
                    self.phase_trace.append(f"{phase}:disabled")
                    self.events.append(f"noop:{phase}:T02")
                    continue
                self.phase_trace.append(phase)
                if phase == "planning_credit":
                    plan(self)
                    plan_investment(self)
                    self.events.append("noop:dynamic_credit:T02")
                elif phase == "labor_wages":
                    labor = match_and_pay(self)
                elif phase == "extraction":
                    produce(self, extraction=True)
                elif phase == "resources":
                    buy_resources(self)
                elif phase == "production":
                    produce(self, extraction=False)
                elif phase == "final_goods":
                    consumption = consume_households(self)
                    self.events.append("noop:government_purchases:T02")
                elif phase == "investment":
                    self.events.append("noop:primary_equity:T02")
                    investment = buy_capital(self)
                elif phase == "operating_close":
                    depreciation, spoilage = operating_close(self)
            metrics = collect(
                self, start_accounts, consumption, investment, depreciation, spoilage, labor
            )
            self.validate(full=False)
            if metrics["gdp_discrepancy"] != ZERO:
                raise ValueError("PIL produzione/spesa non riconciliato")
            self.phase_trace.append("commit")
            self.weekly_metrics = metrics
            self.history.append(metrics.copy())
            self.state_version += 1
            return metrics.copy()
        except Exception as exc:
            undo.rollback()
            self.status = "ERROR"
            self.last_error = f"{type(exc).__name__}: {exc}"
            raise

    def export_csv(self, path):
        export_csv(self, path)

    def agent(self, entity_id):
        for table in (self.people, self.firms, self.banks):
            if entity_id in table.id_to_row:
                account = self.deposits.get(entity_id)
                return AgentView(entity_id, table, self.ledger, account.asset if account else None)
        raise KeyError(entity_id)

    def deposit_projection(self, entity_ids):
        return readonly_copy(
            [float(self.ledger.balance(self.deposits[int(i)].asset)) for i in entity_ids],
            dtype="float64",
        )

    def economic_state(self):
        config = self.config.model_dump(exclude={"runtime"})
        config["catalog"]["products"].sort(key=lambda p: p["id"])
        return canonical_value(
            {
                "schema_version": 1,
                "engine_version": __version__,
                "layout_version": LAYOUT_VERSION,
                "week": self.week,
                "config": config,
                "people": self.people.to_dict(),
                "firms": self.firms.to_dict(),
                "banks": self.banks.to_dict(),
                "government": self.government,
                "central_bank": self.central_bank,
                "ledger": self.ledger.to_dict(),
                "physical": self.physical.to_dict(),
                "rng": self.rng.states(),
                "deposits": dict(self.deposits),
                "reserves": dict(self.reserves),
                "loans": dict(self.loans),
                "bonds": dict(self.bonds),
                "share_issues": dict(self.share_issues),
                "share_holdings": self.share_holdings,
                "employment": self.employment,
                "cpi_prices": self.cpi_prices,
                "cpi_ages": self.cpi_ages,
                "cpi_history": self.cpi_history,
                "history": self.history,
                "phase_trace": self.phase_trace,
            }
        )

    def economic_checksum(self):
        return checksum(self.economic_state())

    @money_context
    def monetary_metrics(self):
        return {
            "private_deposits": sum(
                (self.ledger.balance(a.asset) for a in self.deposits.values()), ZERO
            ),
            "bank_reserves": sum(
                (self.ledger.balance(a.asset) for a in self.reserves.values()), ZERO
            ),
            "treasury_balance": self.ledger.balance(f"{self.government.id}:treasury"),
            "central_bank_liabilities": self.ledger.balance_sheets()[self.central_bank.id][
                "liabilities"
            ],
            "private_credit": sum(
                (self.ledger.balance(loan.asset_account) for loan in self.loans.values()), ZERO
            ),
            "public_debt_face": sum((bond.face_value for bond in self.bonds.values()), ZERO),
            "public_debt_carrying": sum(
                (self.ledger.balance(bond.liability_account) for bond in self.bonds.values()), ZERO
            ),
        }

    def metrics(self):
        return self.weekly_metrics.copy() if self.weekly_metrics else self.monetary_metrics()

    def snapshot(self):
        return Snapshot(
            schema_version=1,
            engine_version=__version__,
            run_id=self.run_id,
            week=self.week,
            state_version=self.state_version,
            status=self.status,
            checksum=self.economic_checksum(),
            metrics=self.metrics(),
            markets=tuple(m.model_copy(deep=True) for m in self.market_results),
            events=tuple(self.events) + ((f"error:{self.last_error}",) if self.last_error else ()),
            pending_commands=(),
        )

    def diagnostic_summary(self):
        self.validate()
        return canonical_value(
            {
                "snapshot": self.snapshot(),
                "counts": {
                    "people": len(self.people.ids),
                    "firms": len(self.firms.ids),
                    "extractive_firms": int(self.firms.column("extractive").sum()),
                    "banks": len(self.banks.ids),
                    "products": 11,
                },
                "balance_sheets": self.ledger.balance_sheets(),
                "ledger": self.ledger.to_dict(),
                "bonds": dict(self.bonds),
                "share_issues": dict(self.share_issues),
                "share_holdings": self.share_holdings,
                "physical": self.physical.to_dict(),
                "phase_trace": self.phase_trace,
                "limitations": [
                    "Profilo: " + self.config.execution.profile,
                    "Credito/fisco/debito dinamico, crisi e dividendi non implementati",
                    "Calibrazione proposta; non è il deliverable D1",
                ],
            }
        )

    def firm_diagnostics(self):
        """Vista finale per diagnosticare vincoli di cassa, lavoro e input nel run CLI."""
        sheets = self.ledger.balance_sheets()
        rows = []
        for row, firm_id in enumerate(self.firms.ids):
            firm = int(firm_id)
            pid = int(self.firms.column("product_id")[row])
            rows.append(
                {
                    "id": firm,
                    "product": self.products[pid - 1].name,
                    "deposit": self.ledger.balance(self.deposits[firm].asset),
                    "equity": sheets[firm]["equity"],
                    "offered_price": float(self.firms.column("offered_price")[row]),
                    "offered_wage": float(self.firms.column("offered_wage")[row]),
                    "observed_unit_cost": float(self.firms.column("observed_unit_cost")[row]),
                    "planned_workers": int(self.firms.column("planned_workers")[row]),
                    "paid_workers": int(self.paid_workers[row]),
                    "output": float(self.output[row]),
                    "target": float(self.production_targets[row]),
                    "inventory": {
                        p.name: self.physical.quantity(firm, p.id) for p in self.products
                    },
                    "installed_capital": self.physical.quantity(firm, 11, "installed_capital"),
                    "natural_reserve": self.physical.quantity(firm, pid, "natural_reserve"),
                }
            )
        return canonical_value(rows)
