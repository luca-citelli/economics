from collections import defaultdict
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from economic_sim.money import ZERO, money, money_context


class AccountingError(ValueError):
    pass


class AccountKind(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"

    @property
    def sign(self):
        return 1 if self in (self.ASSET, self.EXPENSE) else -1


@dataclass(frozen=True)
class Account:
    id: str
    entity_id: int
    kind: AccountKind
    purpose: str
    nonnegative: bool = False
    counterparty_id: int | None = None
    instrument_id: str | None = None


@dataclass(frozen=True)
class Posting:
    account_id: str
    debit: Decimal  # positivo = dare, negativo = avere


@dataclass(frozen=True)
class Transaction:
    id: str
    week: int
    phase: str
    reason: str
    postings: tuple[Posting, ...]


class Ledger:
    """Saldi signed-debit autorevoli; journal append-only, staging dei soli delta."""

    def __init__(self):
        self._accounts: dict[str, Account] = {}
        self._balances: dict[str, Decimal] = {}
        self._journal: list[Transaction] = []
        self._transaction_ids: set[str] = set()
        self._holds: dict[str, tuple[str, Decimal]] = {}

    @property
    def accounts(self):
        return MappingProxyType(self._accounts)

    @property
    def journal(self):
        return tuple(self._journal)

    @property
    def holds(self):
        return MappingProxyType(self._holds)

    @money_context
    def balance(self, account_id: str) -> Decimal:
        return self._balances[account_id] * self._accounts[account_id].kind.sign

    @money_context
    def available(self, account_id: str) -> Decimal:
        return self.balance(account_id) - sum(
            (amount for account, amount in self._holds.values() if account == account_id), ZERO
        )

    def reserve(self, hold_id: str, account_id: str, amount: Decimal):
        amount = money(amount)
        if hold_id in self._holds or amount <= ZERO:
            raise AccountingError("Vincolo duplicato o non positivo")
        if not self._accounts[account_id].nonnegative or self.available(account_id) < amount:
            raise AccountingError("Fondi disponibili insufficienti per il vincolo")
        self._holds[hold_id] = (account_id, amount)

    def release(self, hold_id: str):
        del self._holds[hold_id]

    @money_context
    def post(self, transaction: Transaction, *, new_accounts: tuple[Account, ...] = ()):
        """Validazione completa prima del commit; un rifiuto non apre neppure i conti."""
        tx = replace(transaction, postings=tuple(transaction.postings))
        if (
            not tx.id
            or tx.id in self._transaction_ids
            or type(tx.week) is not int
            or tx.week < 0
            or not tx.phase
            or not tx.reason
            or not tx.postings
        ):
            raise AccountingError("Metadati transazione invalidi o ID duplicato")
        additions = {a.id: a for a in new_accounts}
        if len(additions) != len(new_accounts) or additions.keys() & self._accounts.keys():
            raise AccountingError("Conti duplicati")
        for a in new_accounts:
            if not a.id or not isinstance(a.kind, AccountKind) or not a.purpose:
                raise AccountingError("Conto non valido")
        entity_sums = defaultdict(lambda: ZERO)
        deltas = defaultdict(lambda: ZERO)
        for line in tx.postings:
            a = additions.get(line.account_id) or self._accounts.get(line.account_id)
            if a is None:
                raise AccountingError(f"Conto inesistente: {line.account_id}")
            if not isinstance(line.debit, Decimal) or money(line.debit) != line.debit:
                raise AccountingError("Scritture richieste in Decimal quantizzato a 0.000001 UM")
            deltas[a.id] += line.debit
            entity_sums[a.entity_id] += line.debit
        if any(v != ZERO for v in entity_sums.values()):
            raise AccountingError("Scrittura non bilanciata per entità")
        pending = {}
        for account_id in additions.keys() | deltas.keys():
            a = additions.get(account_id) or self._accounts[account_id]
            candidate = money(self._balances.get(account_id, ZERO) + deltas[account_id])
            held = sum((v for key, v in self._holds.values() if key == account_id), ZERO)
            if a.nonnegative and candidate * a.kind.sign < held:
                raise AccountingError(f"Saldo disponibile negativo: {account_id}")
            pending[account_id] = candidate
        self._accounts.update(additions)
        self._balances.update(pending)
        self._journal.append(tx)
        self._transaction_ids.add(tx.id)

    @money_context
    def balance_sheets(self) -> dict[int, dict[str, Decimal]]:
        totals = defaultdict(lambda: {kind.value: ZERO for kind in AccountKind})
        for aid, account in self._accounts.items():
            totals[account.entity_id][account.kind.value] += self.balance(aid)
        result = {}
        for entity_id, t in sorted(totals.items()):
            equity = t["equity"] + t["income"] - t["expense"]
            result[entity_id] = {
                "assets": t["asset"],
                "liabilities": t["liability"],
                "equity": equity,
                "difference": t["asset"] - t["liability"] - equity,
            }
        return result

    @money_context
    def validate(self):
        if any(b["difference"] != ZERO for b in self.balance_sheets().values()):
            raise AccountingError("Invariante attività = passività + patrimonio violata")
        for aid, account in self._accounts.items():
            if money(self._balances[aid]) != self._balances[aid]:
                raise AccountingError("Saldo non quantizzato")
            if account.nonnegative and self.available(aid) < ZERO:
                raise AccountingError(f"Saldo negativo: {aid}")
        reconstructed = dict.fromkeys(self._accounts, ZERO)
        seen = set()
        for tx in self._journal:
            if tx.id in seen:
                raise AccountingError("Journal con ID duplicati")
            seen.add(tx.id)
            entity_sums = defaultdict(lambda: ZERO)
            for line in tx.postings:
                reconstructed[line.account_id] += line.debit
                entity_sums[self._accounts[line.account_id].entity_id] += line.debit
            if any(entity_sums.values()):
                raise AccountingError("Journal non bilanciato")
        if reconstructed != self._balances or seen != self._transaction_ids:
            raise AccountingError("Saldi e journal non riconciliati")

    def to_dict(self):
        from dataclasses import asdict

        return {
            "accounts": [
                dict(asdict(a), balance=self.balance(a.id))
                for a in sorted(self._accounts.values(), key=lambda a: a.id)
            ],
            "journal": [asdict(tx) for tx in self._journal],
            "holds": dict(sorted(self._holds.items())),
        }


@money_context
def change(account: Account, natural_delta: Decimal) -> Posting:
    return Posting(account.id, money(natural_delta) * account.kind.sign)
