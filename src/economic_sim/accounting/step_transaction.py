"""Undo dello stato corrente e della sola coda append-only dello step."""

import numpy as np


class StepTransaction:
    def __init__(self, sim):
        self.sim = sim
        self.attributes = dict(sim.__dict__)
        # Stato corrente copiato, storico e journal conservati con offset.
        self.tables = [
            (table, {k: v.copy() for k, v in table._columns.items()})
            for table in (sim.people, sim.firms, sim.banks)
        ]
        self.ledger = (
            sim.ledger._accounts.copy(),
            sim.ledger._balances.copy(),
            sim.ledger._holds.copy(),
            len(sim.ledger._journal),
        )
        self.physical = (
            {k: v.copy() for k, v in sim.physical._stocks.items()},
            sim.physical._holds.copy(),
            len(sim.physical._journal),
        )
        self.rng = sim.rng.states()
        self.attributes["employment"] = sim.employment.copy()
        self.attributes["_loans"] = sim._loans.copy()
        self.attributes["_bonds"] = sim._bonds.copy()
        self.attributes["_share_issues"] = sim._share_issues.copy()
        for name, value in sim.__dict__.items():
            if isinstance(value, np.ndarray):
                self.attributes[name] = value.copy()
        self.history_length = len(sim.history)
        self.event_history_length = len(sim.event_history)
        self.cpi_length = len(sim.cpi_history)
        if hasattr(sim, "finance"):
            self.finance = (
                sim.finance.policy,
                sim.finance.pending_policy.copy(),
                sim.finance.cb_loans.copy(),
                sim.finance.processed_requests.copy(),
                sim.finance.rejections.copy(),
                sim.finance.flows.copy(),
            )
        if hasattr(sim, "treasury"):
            self.treasury = (
                sim.treasury.last_price,
                sim.treasury.expected_policy_rate,
                sim.treasury.pending_cb_orders.copy(),
                sim.treasury.pending_budgets.copy(),
                sim.treasury.active_bond_purchase_budget,
                sim.treasury.tax_due.copy(),
                sim.treasury.tax_arrears.copy(),
                sim.treasury.default_arrears,
                sim.treasury.flows.copy(),
                sim.treasury.opening_balance,
                getattr(sim.treasury, "spending_budget", None),
            )
        if hasattr(sim, "equity"):
            self.equity = (
                sim.equity.last_results.copy(),
                sim.equity.flows.copy(),
                {k: list(v) for k, v in sim.equity.profit_history.items()},
            )
        if hasattr(sim, "crisis"):
            self.crisis = (
                sim.crisis.liquidations.copy(),
                sim.crisis.closed_liquidations.copy(),
                sim.crisis.resolved_banks.copy(),
                sim.crisis.resolved_this_week.copy(),
                sim.crisis.defaulted_people.copy(),
                sim.crisis.flows.copy(),
                sim.crisis.loss_exposed_firms.copy(),
                sim.crisis.tax_arrears_weeks.copy(),
                sim.crisis.asset_proceeds.copy(),
            )

    def rollback(self):
        sim = self.sim
        ledger, physical = sim.ledger, sim.physical
        accounts, balances, holds, offset = self.ledger
        for tx in ledger._journal[offset:]:
            ledger._transaction_ids.remove(tx.id)
        del ledger._journal[offset:]
        ledger._accounts, ledger._balances, ledger._holds = accounts, balances, holds
        stocks, holds, offset = self.physical
        for entry in physical._journal[offset:]:
            physical._transaction_ids.discard(entry.transaction_id)
        del physical._journal[offset:]
        physical._stocks, physical._holds = stocks, holds
        for table, columns in self.tables:
            table._columns = columns
        sim.rng.restore(self.rng)
        del sim.history[self.history_length :]
        del sim.event_history[self.event_history_length :]
        del sim.cpi_history[self.cpi_length :]
        sim.__dict__.clear()
        sim.__dict__.update(self.attributes)
        from types import MappingProxyType

        sim.bonds = MappingProxyType(sim._bonds)
        sim.share_issues = MappingProxyType(sim._share_issues)
        sim.loans = MappingProxyType(sim._loans)
        sim.settlement.loans = sim._loans
        if hasattr(self, "finance"):
            (
                sim.finance.policy,
                sim.finance.pending_policy,
                sim.finance.cb_loans,
                sim.finance.processed_requests,
                sim.finance.rejections,
                sim.finance.flows,
            ) = self.finance
        if hasattr(self, "treasury"):
            (
                sim.treasury.last_price,
                sim.treasury.expected_policy_rate,
                sim.treasury.pending_cb_orders,
                sim.treasury.pending_budgets,
                sim.treasury.active_bond_purchase_budget,
                sim.treasury.tax_due,
                sim.treasury.tax_arrears,
                sim.treasury.default_arrears,
                sim.treasury.flows,
                sim.treasury.opening_balance,
                spending_budget,
            ) = self.treasury
            if spending_budget is None:
                sim.treasury.__dict__.pop("spending_budget", None)
            else:
                sim.treasury.spending_budget = spending_budget
        if hasattr(self, "equity"):
            sim.equity.last_results, sim.equity.flows, sim.equity.profit_history = self.equity
        if hasattr(self, "crisis"):
            (
                sim.crisis.liquidations,
                sim.crisis.closed_liquidations,
                sim.crisis.resolved_banks,
                sim.crisis.resolved_this_week,
                sim.crisis.defaulted_people,
                sim.crisis.flows,
                sim.crisis.loss_exposed_firms,
                sim.crisis.tax_arrears_weeks,
                sim.crisis.asset_proceeds,
            ) = self.crisis
