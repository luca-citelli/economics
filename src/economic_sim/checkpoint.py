"""Checkpoint JSON portabile dello stato economico, senza oggetti runtime."""

import json
import os
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4

import numpy as np

from economic_sim import __version__
from economic_sim.accounting.ledger import Account, AccountKind, Posting, Transaction
from economic_sim.accounting.physical import PhysicalEntry
from economic_sim.accounting.settlement import DepositAccount, ReserveAccount
from economic_sim.agents.state import LAYOUT_VERSION, BankState, FirmState, HouseholdState
from economic_sim.config import Config
from economic_sim.contracts import (
    Bond,
    CentralBankLoan,
    CreditDecision,
    Loan,
    MarketResult,
    ShareHolding,
    ShareIssue,
)
from economic_sim.finance import PolicyState
from economic_sim.markets.labor import Employment
from economic_sim.money import money
from economic_sim.serialization import canonical_value, checksum

CHECKPOINT_VERSION = 1


def _decode(model, value):
    return model.model_validate_json(json.dumps(value, ensure_ascii=False, allow_nan=False))


def save_checkpoint(sim, path, *, commands=(), server_sequence=0, policies=(), orders=()):
    if sim.status != "PAUSED":
        raise ValueError("Il checkpoint richiede una pausa a confine di step")
    state = sim.economic_state()
    # Il log conserva l'idempotenza dopo la ripresa; resta fuori dal checksum economico.
    payload = {
        "checkpoint_version": CHECKPOINT_VERSION,
        "engine_version": __version__,
        "layout_version": LAYOUT_VERSION,
        "economic_checksum": checksum(state),
        "state": state,
        "config_ordered": sim.config.model_dump(mode="json"),
        "orders": {
            "deposits": list(sim.deposits),
            "reserves": list(sim.reserves),
            "employment": list(sim.employment),
            "loans": list(sim.loans),
            "bonds": list(sim.bonds),
            "share_issues": list(sim.share_issues),
            "central_bank_loans": list(sim.finance.cb_loans),
            "processed_credit_requests": list(sim.finance.processed_requests),
        },
        "runtime": {
            "commands": list(commands),
            "server_sequence": server_sequence,
            "policies": list(policies),
            "orders": list(orders),
        },
    }
    payload = canonical_value(payload)
    payload["checksum"] = checksum({k: v for k, v in payload.items() if k != "checksum"})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return payload["economic_checksum"]


def load_checkpoint(path):
    from economic_sim.simulation import Simulation

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError("Versione checkpoint incompatibile")
    if data.get("engine_version") != __version__ or data.get("layout_version") != LAYOUT_VERSION:
        raise ValueError(
            "Versione motore/layout incompatibile; usare la versione che ha salvato il file"
        )
    actual = checksum({k: v for k, v in data.items() if k != "checksum"})
    if actual != data.get("checksum") or checksum(data["state"]) != data.get("economic_checksum"):
        raise ValueError("Checksum checkpoint non valido")
    state = data["state"]
    sim = Simulation.from_config(Config.model_validate(data["config_ordered"]))
    sim.week = state["week"]
    sim.state_version = sim.week
    for name, cls in (("people", HouseholdState), ("firms", FirmState), ("banks", BankState)):
        table = state[name]
        setattr(sim, name, cls(table["ids"], **{k: table[k] for k in cls.schema}))
    ledger = sim.ledger
    ledger._accounts = {
        row["id"]: Account(
            row["id"],
            row["entity_id"],
            AccountKind(row["kind"]),
            row["purpose"],
            row["nonnegative"],
            row["counterparty_id"],
            row["instrument_id"],
        )
        for row in state["ledger"]["accounts"]
    }
    ledger._balances = {
        row["id"]: money(row["balance"]) * ledger._accounts[row["id"]].kind.sign
        for row in state["ledger"]["accounts"]
    }
    ledger._journal = [
        Transaction(
            row["id"],
            row["week"],
            row["phase"],
            row["reason"],
            tuple(Posting(p["account_id"], money(p["debit"])) for p in row["postings"]),
        )
        for row in state["ledger"]["journal"]
    ]
    ledger._transaction_ids = {tx.id for tx in ledger._journal}
    ledger._holds = {k: (v[0], money(v[1])) for k, v in state["ledger"]["holds"].items()}
    physical = sim.physical
    if (
        physical.entity_ids.tolist() != state["physical"]["entity_ids"]
        or physical.product_ids.tolist() != state["physical"]["product_ids"]
    ):
        raise ValueError("Mapping degli ID fisici incompatibile")
    physical._stocks = {
        k: np.array(v, dtype=np.float64) for k, v in state["physical"]["stocks"].items()
    }
    physical._journal = [PhysicalEntry(**entry) for entry in state["physical"]["journal"]]
    physical._transaction_ids = {entry.transaction_id for entry in physical._journal}
    physical._holds = {k: tuple(v) for k, v in state["physical"]["holds"].items()}
    sim.rng.restore(state["rng"])
    order = data["orders"]
    sim.deposits = MappingProxyType(
        {int(k): DepositAccount(**state["deposits"][str(k)]) for k in order["deposits"]}
    )
    sim.reserves = MappingProxyType(
        {int(k): ReserveAccount(**state["reserves"][str(k)]) for k in order["reserves"]}
    )
    sim.settlement.deposits = sim.deposits
    sim.settlement.reserves = sim.reserves
    sim._loans = {k: _decode(Loan, state["loans"][k]) for k in order["loans"]}
    sim.loans = MappingProxyType(sim._loans)
    sim._bonds = {k: _decode(Bond, state["bonds"][k]) for k in order["bonds"]}
    sim.bonds = MappingProxyType(sim._bonds)
    sim._share_issues = {
        k: _decode(ShareIssue, state["share_issues"][k]) for k in order["share_issues"]
    }
    sim.share_issues = MappingProxyType(sim._share_issues)
    sim.share_holdings = tuple(_decode(ShareHolding, v) for v in state["share_holdings"])
    sim.settlement.loans = sim._loans
    sim.finance.cb_loans = {
        k: _decode(CentralBankLoan, state["central_bank_loans"][k])
        for k in order["central_bank_loans"]
    }
    sim.finance.policy = PolicyState(**state["active_policy"])
    sim.finance.pending_policy = {
        int(k): PolicyState(**v) for k, v in state["pending_policy"].items()
    }
    sim.finance.processed_requests = {
        k: _decode(CreditDecision, state["processed_credit_requests"][k])
        for k in order["processed_credit_requests"]
    }
    sim.finance.rejections = {k: int(v) for k, v in state["credit_rejections"].items()}
    sim.finance.flows = {k: money(v) for k, v in state["finance_flows"].items()}
    treasury = state["treasury_state"]
    sim.treasury.last_price = money(treasury["last_price"]) if treasury["last_price"] else None
    sim.treasury.expected_policy_rate = treasury["expected_policy_rate"]
    sim.treasury.pending_cb_orders = {
        int(k): [(money(budget), money(price)) for budget, price in values]
        for k, values in treasury["pending_cb_orders"].items()
    }
    sim.treasury.pending_budgets = {
        int(k): money(v) for k, v in treasury["pending_budgets"].items()
    }
    sim.treasury.active_bond_purchase_budget = money(treasury["active_bond_purchase_budget"])
    sim.treasury.tax_due = {int(k): (v[0], money(v[1])) for k, v in treasury["tax_due"].items()}
    sim.treasury.tax_arrears = {int(k): money(v) for k, v in treasury["tax_arrears"].items()}
    sim.treasury.default_arrears = money(treasury["default_arrears"])
    sim.treasury.flows = {k: money(v) for k, v in treasury["flows"].items()}
    sim.treasury.opening_balance = money(treasury["opening_balance"])
    equity = state["equity_state"]
    sim.equity.last_results = equity["last_results"]
    sim.equity.flows = {k: money(v) for k, v in equity["flows"].items()}
    sim.equity.profit_history = {
        int(k): [money(v) for v in values] for k, values in equity["profit_history"].items()
    }
    crisis = state["crisis_state"]
    sim.crisis.liquidations = {int(k): v for k, v in crisis["liquidations"].items()}
    for name in (
        "closed_liquidations",
        "resolved_banks",
        "resolved_this_week",
        "defaulted_people",
        "loss_exposed_firms",
    ):
        setattr(sim.crisis, name, set(crisis[name]))
    sim.crisis.tax_arrears_weeks = {int(k): v for k, v in crisis["tax_arrears_weeks"].items()}
    sim.crisis.asset_proceeds = {int(k): money(v) for k, v in crisis["asset_proceeds"].items()}
    sim.crisis.flows = {k: money(v) for k, v in crisis["flows"].items()}
    sim.employment = {
        int(k): Employment(
            **{**state["employment"][str(k)], "wage": money(state["employment"][str(k)]["wage"])}
        )
        for k in order["employment"]
    }
    sim.cpi_prices = np.array(state["cpi_prices"], dtype=np.float64)
    sim.cpi_ages = np.array(state["cpi_ages"], dtype=np.int64)
    sim.cpi_history = list(state["cpi_history"])
    sim.history = [dict(row) for row in state["history"]]
    sim.weekly_metrics = sim.history[-1].copy() if sim.history else {}
    sim.event_history = list(state["event_history"])
    sim.events = list(sim.event_history[-1]["events"]) if sim.event_history else []
    sim.market_results = [_decode(MarketResult, row) for row in state["market_results"]]
    sim.phase_trace = list(state["phase_trace"])
    sim.status = "PAUSED"
    sim.run_id = str(uuid4())
    sim.validate()
    if sim.economic_checksum() != data["economic_checksum"]:
        raise ValueError("Ripristino economico non identico al checkpoint")
    return sim, data["runtime"]
