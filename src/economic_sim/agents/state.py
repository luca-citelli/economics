from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

NO_ID = -1
LAYOUT_VERSION = 1


def readonly_copy(values, dtype=None):
    """Copia senza alias, buffer bytes immutabile anche via setflags(write=True)."""
    a = np.asarray(values, dtype=dtype)
    return np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)


class ColumnTable:
    schema: dict[str, np.dtype] = {}
    trailing_shapes: dict[str, tuple[int, ...]] = {}

    def __init__(self, ids, **columns):
        self.ids = readonly_copy(ids, np.int64)
        if self.ids.ndim != 1 or len(set(self.ids.tolist())) != len(self.ids):
            raise ValueError("ID tabella duplicati o shape errata")
        self.id_to_row = MappingProxyType({int(i): row for row, i in enumerate(self.ids)})
        if set(columns) != set(self.schema):
            raise ValueError("Colonne mancanti o sconosciute")
        self._columns = {}
        for name, dtype in self.schema.items():
            array = np.array(columns[name], dtype=dtype, copy=True)
            if array.shape != (len(self.ids), *self.trailing_shapes.get(name, ())):
                raise ValueError(f"Shape errata: {name}")
            if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                raise ValueError(f"Dati non finiti: {name}")
            self._columns[name] = array

    def column(self, name):
        """Copia di lettura; il worker usa replace_column al confine della fase."""
        return readonly_copy(self._columns[name])

    def replace_column(self, name, values):
        old = self._columns[name]
        values = np.asarray(values, dtype=old.dtype)
        if values.shape != old.shape or not np.isfinite(values).all():
            raise ValueError("Shape o valori non validi")
        self._columns[name] = values.copy()

    def to_dict(self):
        return {"ids": self.ids.tolist(), **{k: v.tolist() for k, v in self._columns.items()}}


class HouseholdState(ColumnTable):
    trailing_shapes = {"needs": (11,), "satisfaction": (7,)}
    schema = {
        "bank_id": np.int64,
        "employer_id": np.int64,
        "age_weeks": np.int64,
        "active": np.bool_,
        "saving_propensity": np.float64,
        "risk_propensity": np.float64,
        "quality_propensity": np.float64,
        "reservation_wage": np.float64,
        "expected_income": np.float64,
        "needs": np.float64,
        "satisfaction": np.float64,
    }


class FirmState(ColumnTable):
    schema = {
        "bank_id": np.int64,
        "product_id": np.int64,
        "active": np.bool_,
        "extractive": np.bool_,
        "productivity": np.float64,
        "offered_wage": np.float64,
        "offered_price": np.float64,
        "quality": np.float64,
        "reputation": np.float64,
        "planned_workers": np.int64,
        "previous_sales": np.float64,
        "previous_orders": np.float64,
    }


class BankState(ColumnTable):
    schema = {"active": np.bool_, "deposit_rate": np.float64}


@dataclass(frozen=True)
class Institution:
    id: int
    kind: str
    name: str


@dataclass(frozen=True)
class AgentView:
    """Vista su un ID: i saldi sono interrogati dal ledger a ogni accesso."""

    id: int
    table: ColumnTable
    ledger: object
    deposit_account: str | None

    @property
    def row(self):
        return self.table.id_to_row[self.id]

    @property
    def deposit(self):
        if self.deposit_account is None:
            raise ValueError("Questo agente non ha un deposito privato")
        return self.ledger.balance(self.deposit_account)
