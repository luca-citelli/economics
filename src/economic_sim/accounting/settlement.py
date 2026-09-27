from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.accounting.physical import PhysicalEntry
from economic_sim.contracts import Loan
from economic_sim.money import ZERO, money, money_context, positive_money


class SettlementError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DepositAccount:
    owner_id: int
    bank_id: int
    asset: str
    liability: str


@dataclass(frozen=True)
class ReserveAccount:
    bank_id: int
    asset: str
    liability: str


class Settlement:
    def __init__(self, ledger, deposits, reserves, loans):
        self.ledger = ledger
        self.deposits = deposits
        self.reserves = reserves
        self.loans = loans

    def _delta(self, aid, amount):
        return change(self.ledger.accounts[aid], amount)

    def _payment_lines(self, payer, payee, amount):
        source, target = self.deposits[payer], self.deposits[payee]
        if payer == payee:
            raise SettlementError("same_party_payment")
        if self.ledger.available(source.asset) < amount:
            raise SettlementError("insufficient_customer_funds")
        lines = [
            self._delta(source.asset, -amount),
            self._delta(source.liability, -amount),
            self._delta(target.asset, amount),
            self._delta(target.liability, amount),
        ]
        if source.bank_id != target.bank_id:
            a, b = self.reserves[source.bank_id], self.reserves[target.bank_id]
            if self.ledger.available(a.asset) < amount:
                raise SettlementError("bank_settlement_failure")
            lines += [
                self._delta(a.asset, -amount),
                self._delta(a.liability, -amount),
                self._delta(b.asset, amount),
                self._delta(b.liability, amount),
            ]
        return lines

    @money_context
    def pay_wage(self, tx_id, employer, worker, amount, *, week):
        amount = positive_money(amount)
        lines = self._payment_lines(employer, worker, amount)
        work = Account(
            f"{employer}:work_in_progress", employer, AccountKind.ASSET, "work_in_progress", True
        )
        wage = Account(f"{worker}:wage_income", worker, AccountKind.INCOME, "wage_income")
        lines += [change(work, amount), change(wage, amount)]
        self.ledger.post(
            Transaction(tx_id, week, "labor_wages", "Salario anticipato T02", tuple(lines)),
            new_accounts=tuple(a for a in (work, wage) if a.id not in self.ledger.accounts),
        )

    @money_context
    def transfer(self, tx_id, payer, payee, amount, *, week=0, reason="Trasferimento"):
        """Trasferimento esplicito senza consegna: spesa del pagante, reddito ricevente."""
        amount = positive_money(amount)
        lines = self._payment_lines(payer, payee, amount)
        expense = Account(f"{payer}:transfers_out", payer, AccountKind.EXPENSE, "transfer_expense")
        income = Account(f"{payee}:transfers_in", payee, AccountKind.INCOME, "transfer_income")
        additions = tuple(a for a in (expense, income) if a.id not in self.ledger.accounts)
        lines += [change(expense, amount), change(income, amount)]
        self.ledger.post(
            Transaction(tx_id, week, "settlement", reason, tuple(lines)), new_accounts=additions
        )

    @money_context
    def purchase(
        self,
        tx_id,
        buyer,
        seller,
        product,
        quantity,
        unit_price,
        physical,
        *,
        week=0,
        destination="inventory",
    ):
        """Vendita al costo medio: consegna e pagamento nella stessa transazione."""
        if not np.isfinite(quantity) or quantity <= 0 or buyer == seller:
            raise SettlementError("invalid_quantity_or_party")
        if destination not in {"inventory", "pending_capital"} or (
            destination == "pending_capital" and product != 11
        ):
            raise SettlementError("invalid_delivery_destination")
        if quantity > physical.available(seller, product):
            raise SettlementError("insufficient_inventory")
        total = positive_money(positive_money(unit_price) * Decimal(str(quantity)))
        lines = self._payment_lines(buyer, seller, total)
        seller_stock = f"{seller}:inventory:{product}"
        buyer_stock = Account(
            f"{buyer}:inventory:{product}"
            if destination == "inventory"
            else f"{buyer}:pending_capital",
            buyer,
            AccountKind.ASSET,
            destination,
            True,
            instrument_id=str(product),
        )
        revenue = Account(f"{seller}:sales", seller, AccountKind.INCOME, "sales")
        cost = Account(f"{seller}:cost_of_sales", seller, AccountKind.EXPENSE, "cost_of_sales")
        value = self.ledger.balance(seller_stock)
        seller_qty = physical.quantity(seller, product)
        carrying = (
            value
            if quantity == seller_qty
            else money(value * Decimal(str(quantity)) / Decimal(str(seller_qty)))
        )
        lines += [
            change(buyer_stock, total),
            change(revenue, total),
            change(cost, carrying),
            self._delta(seller_stock, -carrying),
        ]
        entries = (
            PhysicalEntry(tx_id, week, "settlement", "Vendita", seller, product, -quantity),
            PhysicalEntry(
                tx_id, week, "settlement", "Acquisto", buyer, product, quantity, destination
            ),
        )
        pending = physical.prepare(entries)
        additions = tuple(
            a for a in (buyer_stock, revenue, cost) if a.id not in self.ledger.accounts
        )
        self.ledger.post(
            Transaction(tx_id, week, "settlement", "Acquisto beni", tuple(lines)),
            new_accounts=additions,
        )
        physical._commit_prepared(entries, pending)

    @money_context
    def originate_loan(
        self, loan_id, borrower, bank, amount, annual_rate, *, week=0, purpose="working_capital"
    ):
        amount = positive_money(amount)
        if loan_id in self.loans:
            raise SettlementError("duplicate_loan")
        deposit = self.deposits[borrower]
        if deposit.bank_id != bank:
            raise SettlementError("loan_requires_account_at_lender")
        asset = Account(
            f"{bank}:loan:{loan_id}", bank, AccountKind.ASSET, "loan", True, borrower, loan_id
        )
        debt = Account(
            f"{borrower}:debt:{loan_id}",
            borrower,
            AccountKind.LIABILITY,
            "loan",
            True,
            bank,
            loan_id,
        )
        loan = Loan(
            id=loan_id,
            borrower_id=borrower,
            bank_id=bank,
            asset_account=asset.id,
            debt_account=debt.id,
            annual_rate=annual_rate,
            originated_week=week,
            next_review_week=week + 1,
            interest_from_week=week + 1,
            arrears=ZERO,
            purpose=purpose,
            collateral_ids=(),
            status="performing",
        )
        lines = (
            change(asset, amount),
            change(debt, amount),
            self._delta(deposit.asset, amount),
            self._delta(deposit.liability, amount),
        )
        self.ledger.post(
            Transaction(f"loan:{loan_id}", week, "credit", "Erogazione", lines),
            new_accounts=(asset, debt),
        )
        self.loans[loan_id] = loan
        return loan

    @money_context
    def repay_loan(self, tx_id, loan_id, amount, *, week=0):
        amount = positive_money(amount)
        loan = self.loans[loan_id]
        if week < loan.originated_week:
            raise SettlementError("repayment_before_origination")
        if amount > self.ledger.balance(loan.debt_account):
            raise SettlementError("repayment_exceeds_principal")
        deposit = self.deposits[loan.borrower_id]
        if self.ledger.available(deposit.asset) < amount:
            raise SettlementError("insufficient_customer_funds")
        lines = (
            self._delta(deposit.asset, -amount),
            self._delta(deposit.liability, -amount),
            self._delta(loan.asset_account, -amount),
            self._delta(loan.debt_account, -amount),
        )
        self.ledger.post(Transaction(tx_id, week, "credit", "Rimborso capitale", lines))
        if self.ledger.balance(loan.debt_account) == ZERO:
            self.loans[loan_id] = loan.model_copy(update={"status": "closed"})
