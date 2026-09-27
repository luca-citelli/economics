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
        for name, value in sim.__dict__.items():
            if isinstance(value, np.ndarray):
                self.attributes[name] = value.copy()
        self.history_length = len(sim.history)
        self.cpi_length = len(sim.cpi_history)

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
        del sim.cpi_history[self.cpi_length :]
        sim.__dict__.clear()
        sim.__dict__.update(self.attributes)
