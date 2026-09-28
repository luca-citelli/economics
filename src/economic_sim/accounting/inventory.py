"""Trasformazioni fisiche e valori al costo medio, nello stesso commit del ledger."""

from decimal import Decimal

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.accounting.physical import PhysicalEntry
from economic_sim.money import ZERO, money, money_context


class InventoryAccounting:
    def __init__(self, sim):
        self.sim = sim

    def value(self, entity, suffix):
        aid = f"{entity}:{suffix}"
        return self.sim.ledger.balance(aid) if aid in self.sim.ledger.accounts else ZERO

    @money_context
    def carrying(self, entity, product, quantity, stock="inventory"):
        total = self.sim.physical.quantity(entity, product, stock)
        suffix = f"inventory:{product}" if stock == "inventory" else stock
        value = self.value(entity, suffix)
        if quantity < 0 or quantity > total:
            raise ValueError("Scarico fisico oltre lo stock")
        return (
            value
            if quantity == total
            else money(value * Decimal(str(quantity)) / Decimal(str(total)))
        )

    def post(self, tx_id, phase, reason, entries, changes):
        sim = self.sim
        accounts, lines = [], []
        for entity, suffix, kind, amount in changes:
            account = Account(
                f"{entity}:{suffix}",
                entity,
                kind,
                suffix.split(":")[0],
                kind == AccountKind.ASSET,
                instrument_id=suffix.split(":")[1] if ":" in suffix else None,
            )
            if account.id not in sim.ledger.accounts:
                accounts.append(account)
            lines.append(change(account, amount))
        physical = tuple(
            PhysicalEntry(tx_id, sim.week, phase, reason, e, p, q, s) for e, p, q, s in entries
        )
        pending = sim.physical.prepare(physical) if physical else None
        sim.ledger.post(
            Transaction(tx_id, sim.week, phase, reason, tuple(lines)), new_accounts=tuple(accounts)
        )
        if physical:
            sim.physical._commit_prepared(physical, pending)

    @money_context
    def consume(self, tx_id, entity, product, quantity, *, reason="consumption", stock="inventory"):
        if quantity <= 0:
            return ZERO
        cost = self.carrying(entity, product, quantity, stock)
        suffix = f"inventory:{product}" if stock == "inventory" else stock
        self.post(
            tx_id,
            "final_goods"
            if reason == "consumption"
            else "crisis"
            if reason == "liquidation_loss"
            else "operating_close",
            reason,
            [(entity, product, -quantity, stock)],
            [
                (entity, suffix, AccountKind.ASSET, -cost),
                (entity, reason, AccountKind.EXPENSE, cost),
            ],
        )
        return cost

    @money_context
    def produce(self, firm, product, quantity):
        sim = self.sim
        wages = self.value(firm, "work_in_progress")
        phase = "extraction" if product.kind == "resource" else "production"
        tx_id = f"w{sim.week}:{phase}:{firm}"
        if quantity <= 0:
            if wages:
                self.post(
                    tx_id,
                    phase,
                    "Salari senza output",
                    [],
                    [
                        (firm, "work_in_progress", AccountKind.ASSET, -wages),
                        (firm, "idle_wages", AccountKind.EXPENSE, wages),
                    ],
                )
            return ZERO, ZERO
        entries, changes = [], []
        inputs_cost = ZERO
        for name, coefficient in product.recipe.items():
            pid = sim.product_by_name[name].id
            used = quantity * coefficient
            cost = self.carrying(firm, pid, used)
            inputs_cost += cost
            entries.append((firm, pid, -used, "inventory"))
            changes.append((firm, f"inventory:{pid}", AccountKind.ASSET, -cost))
        if product.kind == "resource":
            entries.append((firm, product.id, -quantity, "natural_reserve"))
        entries.append((firm, product.id, quantity, "inventory"))
        changes.extend(
            [
                (firm, "work_in_progress", AccountKind.ASSET, -wages),
                (firm, f"inventory:{product.id}", AccountKind.ASSET, wages + inputs_cost),
            ]
        )
        self.post(tx_id, phase, "Produzione al costo", entries, changes)
        return wages + inputs_cost, inputs_cost

    def install_capital(self, firm, quantity):
        sim = self.sim
        source, target = "pending_capital", "installed_capital"
        cost = self.carrying(firm, 11, quantity, source)
        self.post(
            f"w{sim.week}:{target}:{firm}",
            "opening",
            "Installazione",
            [(firm, 11, -quantity, source), (firm, 11, quantity, target)],
            [
                (firm, source, AccountKind.ASSET, -cost),
                (firm, target, AccountKind.ASSET, cost),
            ],
        )
