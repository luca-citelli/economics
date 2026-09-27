from dataclasses import asdict, dataclass
from types import MappingProxyType

import numpy as np

from economic_sim.agents.state import readonly_copy

PHYSICAL_ATOL = 1e-9
PHYSICAL_RTOL = 1e-12


@dataclass(frozen=True)
class PhysicalEntry:
    transaction_id: str
    week: int
    phase: str
    reason: str
    entity_id: int
    product_id: int
    delta: float
    stock: str = "inventory"


class PhysicalRegister:
    """Unica autorità delle quantità: magazzino, capitale installato, giacimenti."""

    def __init__(self, entity_ids, product_ids):
        self.entity_ids = readonly_copy(entity_ids, np.int64)
        self.product_ids = readonly_copy(product_ids, np.int64)
        self.entity_rows = MappingProxyType({int(i): r for r, i in enumerate(entity_ids)})
        self.product_rows = MappingProxyType({int(i): r for r, i in enumerate(product_ids)})
        if len(self.entity_rows) != len(entity_ids) or len(self.product_rows) != len(product_ids):
            raise ValueError("ID fisici duplicati")
        shape = (len(entity_ids), len(product_ids))
        self._stocks = {
            name: np.zeros(shape, dtype=np.float64)
            for name in ("inventory", "installed_capital", "natural_reserve")
        }
        self._journal: list[PhysicalEntry] = []
        self._transaction_ids: set[str] = set()
        self._holds: dict[str, tuple[int, int, float]] = {}

    @property
    def journal(self):
        return tuple(self._journal)

    def quantities(self, stock="inventory"):
        return readonly_copy(self._stocks[stock])

    def quantity(self, entity, product, stock="inventory"):
        return float(self._stocks[stock][self.entity_rows[entity], self.product_rows[product]])

    def available(self, entity, product):
        return self.quantity(entity, product) - sum(
            q for e, p, q in self._holds.values() if (e, p) == (entity, product)
        )

    def reserve(self, hold_id, entity, product, quantity):
        if (
            hold_id in self._holds
            or not np.isfinite(quantity)
            or quantity <= 0
            or quantity > self.available(entity, product)
        ):
            raise ValueError("Vincolo fisico duplicato o quantità non disponibile")
        self._holds[hold_id] = (entity, product, float(quantity))

    def release(self, hold_id):
        del self._holds[hold_id]

    def prepare(self, entries: tuple[PhysicalEntry, ...]):
        """Staging privato usato dal settlement prima del posting monetario."""
        if not entries or len({e.transaction_id for e in entries}) != 1:
            raise ValueError("Una transazione fisica deve avere un ID comune")
        tx_id = entries[0].transaction_id
        if not tx_id or tx_id in self._transaction_ids:
            raise ValueError("Transazione fisica duplicata")
        pending = {}
        for e in entries:
            if e.week < 0 or not e.phase or not e.reason or not np.isfinite(e.delta):
                raise ValueError("Movimento fisico non valido")
            row, col = self.entity_rows[e.entity_id], self.product_rows[e.product_id]
            key = (e.stock, row, col)
            pending[key] = pending.get(key, self._stocks[e.stock][row, col]) + e.delta
        for (stock, row, col), quantity in pending.items():
            held = sum(
                q
                for e, p, q in self._holds.values()
                if stock == "inventory"
                and self.entity_rows[e] == row
                and self.product_rows[p] == col
            )
            # Tolleranze usate per riconciliare, mai per autorizzare uno stock negativo.
            if not np.isfinite(quantity) or quantity < held:
                raise ValueError("Inventario disponibile insufficiente")
        return pending

    def _commit_prepared(self, entries, pending):
        # Nessuna validazione/operazione fallibile dopo il commit del ledger.
        for (stock, row, col), quantity in pending.items():
            self._stocks[stock][row, col] = quantity
        self._journal.extend(entries)
        self._transaction_ids.add(entries[0].transaction_id)

    def post(self, entries):
        self._commit_prepared(entries, self.prepare(entries))

    def validate(self):
        reconstructed = {key: np.zeros_like(value) for key, value in self._stocks.items()}
        for e in self._journal:
            reconstructed[e.stock][
                self.entity_rows[e.entity_id], self.product_rows[e.product_id]
            ] += e.delta
        for key, values in self._stocks.items():
            if not np.isfinite(values).all() or (values < 0).any():
                raise ValueError("Stock fisico negativo/non finito")
            if not np.allclose(values, reconstructed[key], atol=PHYSICAL_ATOL, rtol=PHYSICAL_RTOL):
                raise ValueError("Registro fisico non riconciliato")

    def to_dict(self):
        return {
            "entity_ids": self.entity_ids.tolist(),
            "product_ids": self.product_ids.tolist(),
            "stocks": {k: v.tolist() for k, v in self._stocks.items()},
            "journal": [asdict(e) for e in self._journal],
            "holds": dict(sorted(self._holds.items())),
        }
