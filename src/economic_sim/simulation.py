from dataclasses import fields
from types import MappingProxyType
from uuid import uuid4

from economic_sim import __version__
from economic_sim.accounting.settlement import Settlement
from economic_sim.agents.state import LAYOUT_VERSION, AgentView, readonly_copy
from economic_sim.config import Config
from economic_sim.contracts import Snapshot
from economic_sim.initialization import initialize
from economic_sim.money import ZERO, money_context
from economic_sim.serialization import canonical_value, checksum
from economic_sim.validation import validate_state


class Simulation:
    """Fondamenta D0. Non espone un finto step o un runner parziale."""

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
        sim.validate()
        return sim

    def validate(self):
        validate_state(self)

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
            }
        )

    def economic_checksum(self):
        return checksum(self.economic_state())

    @money_context
    def metrics(self):
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

    def snapshot(self):
        return Snapshot(
            schema_version=1,
            engine_version=__version__,
            run_id=self.run_id,
            week=self.week,
            state_version=self.state_version,
            status="PAUSED",
            checksum=self.economic_checksum(),
            metrics=self.metrics(),
            markets=(),
            events=(),
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
                "limitations": [
                    "Solo settimana 0; fasi economiche disattivate",
                    "Calibrazione proposta; nessuna dinamica macro verificata",
                ],
            }
        )
