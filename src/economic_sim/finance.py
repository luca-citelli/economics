"""Credito e strumenti monetari T03, separati dalle decisioni dell'economia reale."""

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.accounting.settlement import SettlementError
from economic_sim.contracts import CentralBankLoan, CreditDecision
from economic_sim.money import ZERO, money, money_context


def weekly_rate(annual_rate: float) -> Decimal:
    """Converte un tasso annuo effettivo; il Decimal finale è monetariamente stabile."""
    if not np.isfinite(annual_rate) or annual_rate <= -1:
        raise ValueError("Il tasso annuo deve essere finito e maggiore di -100%")
    return Decimal(str((1.0 + annual_rate) ** (1.0 / 52.0) - 1.0))


def default_probabilities(debt, annual_income, arrears_weeks, *, intercept=-3.0):
    """Score annuale batch; reddito nullo è trattato senza divisioni non finite."""
    debt = np.asarray(debt, dtype=np.float64)
    income = np.asarray(annual_income, dtype=np.float64)
    arrears = np.asarray(arrears_weeks, dtype=np.float64)
    ratio = np.divide(debt, income, out=np.full_like(debt, 20.0), where=income > 0)
    z = np.clip(intercept + 0.35 * ratio + 0.6 * arrears, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class PolicyState:
    reserve_rate: float
    policy_rate: float
    emergency_rate: float

    def __post_init__(self):
        if not (-1 < self.reserve_rate <= self.policy_rate <= self.emergency_rate):
            raise ValueError("Richiesto reserve_rate <= policy_rate <= emergency_rate")


class Finance:
    def __init__(self, sim):
        self.sim = sim
        cb = sim.config.central_bank
        self.policy = PolicyState(cb.reserve_rate, cb.policy_rate, cb.emergency_rate)
        self.pending_policy: dict[int, PolicyState] = {}
        self.cb_loans: dict[str, CentralBankLoan] = {}
        self.processed_requests: dict[str, CreditDecision] = {}
        self.rejections: dict[str, int] = {}
        self.flows = {
            "loan_interest": ZERO,
            "deposit_interest": ZERO,
            "reserve_interest": ZERO,
            "central_bank_credit": ZERO,
        }

    def schedule_policy(self, effective_week, *, reserve_rate, policy_rate, emergency_rate):
        if type(effective_week) is not int or effective_week <= self.sim.week:
            raise ValueError("La politica va programmata a un confine futuro")
        state = PolicyState(reserve_rate, policy_rate, emergency_rate)
        self.pending_policy[effective_week] = state
        return effective_week

    def open_week(self):
        if self.sim.week in self.pending_policy:
            self.policy = self.pending_policy.pop(self.sim.week)
        self.flows = {
            "loan_interest": ZERO,
            "deposit_interest": ZERO,
            "reserve_interest": ZERO,
            "central_bank_credit": ZERO,
        }

    def loan_rate(self, probability: float) -> float:
        b = self.sim.config.banks
        expected_loss = probability * b.loss_given_default
        return (
            max(self.policy.policy_rate + b.funding_spread, self.policy.reserve_rate)
            + b.operating_spread
            + expected_loss
            + b.capital_premium
        )

    @money_context
    def finance_plans(self):
        """Richiede credito per circolante e per i bisogni primari non coperti."""
        sim = self.sim
        wages = sim.firms.column("offered_wage") * sim.firms.column("planned_workers")
        prices = sim.firms.column("offered_price")
        for row, firm_id in enumerate(sim.firms.ids):
            firm = int(firm_id)
            shortfall = money(
                Decimal(
                    str(
                        max(
                            0.0,
                            wages[row] - float(sim.ledger.available(sim.deposits[firm].asset)),
                        )
                    )
                )
            )
            if shortfall == ZERO:
                continue
            expected_income = money(
                Decimal(
                    str(max(wages[row], prices[row] * max(sim.production_targets[row], 1.0)) * 52)
                )
            )
            self.request_credit(
                f"plan:{sim.week}:{firm}",
                firm,
                shortfall,
                annual_income=expected_income,
                purpose="working_capital",
            )

        people = sim.people
        needs = people.column("needs")[:, :3]
        reference = sim.reference_prices[:3]
        expected_income = people.column("expected_income")
        for row, person_id in enumerate(people.ids):
            person = int(person_id)
            deposit = sim.deposits[person]
            primary_cost = money(
                sum(
                    (
                        Decimal(str(float(quantity))) * Decimal(str(float(price)))
                        for quantity, price in zip(needs[row], reference, strict=True)
                    ),
                    Decimal(0),
                )
            )
            expected_weekly_income = money(str(max(0.0, float(expected_income[row]))))
            contract = sim.employment.get(person)
            if contract is not None:
                expected_contract_income = contract.wage
                if sim.config.execution.profile in {"fiscal_economy", "complete_economy"}:
                    expected_contract_income *= Decimal(
                        str(1 - sim.config.government.labor_income_tax_rate)
                    )
                expected_weekly_income = max(
                    expected_weekly_income, money(expected_contract_income)
                )
            available = sim.ledger.available(deposit.asset)
            shortfall = max(ZERO, primary_cost - available - expected_weekly_income)
            if shortfall == ZERO:
                continue
            self.request_credit(
                f"primary:{sim.week}:{person}",
                person,
                shortfall,
                annual_income=money(expected_weekly_income * 52),
                purpose="primary_needs",
            )

    def _reject(self, request_id, borrower, requested, reason):
        self.rejections[reason] = self.rejections.get(reason, 0) + 1
        decision = CreditDecision(
            request_id=request_id,
            borrower_id=borrower,
            bank_id=None,
            requested=requested,
            granted=ZERO,
            annual_rate=None,
            status="rejected",
            reason=reason,
        )
        self.processed_requests[request_id] = decision
        return decision

    @money_context
    def request_credit(
        self,
        request_id,
        borrower,
        amount,
        *,
        annual_income,
        purpose="working_capital",
        collateral_value=ZERO,
    ):
        amount, annual_income = money(amount), money(annual_income)
        if request_id in self.processed_requests:
            prior = self.processed_requests[request_id]
            return prior.model_copy(update={"status": "duplicate", "reason": "duplicate_request"})
        if amount <= ZERO:
            raise ValueError("Importo richiesto non positivo")
        sim, cfg = self.sim, self.sim.config.banks
        if borrower in sim.crisis.defaulted_people or borrower in sim.crisis.liquidations:
            return self._reject(request_id, borrower, amount, "borrower_in_default")
        home = sim.deposits[borrower].bank_id
        active_banks = sim.banks.column("active")
        candidates = [home] + [
            int(x)
            for x in sim.banks.ids
            if int(x) != home and active_banks[sim.banks.id_to_row[int(x)]]
        ]
        candidates = [bank for bank in candidates if active_banks[sim.banks.id_to_row[bank]]]
        candidates = candidates[: cfg.max_banks_compared]
        debt = sum(
            (
                sim.ledger.balance(x.debt_account)
                for x in sim.loans.values()
                if x.borrower_id == borrower
            ),
            ZERO,
        )
        income_f = float(annual_income)
        pd = float(default_probabilities([float(debt)], [income_f], [0])[0])
        rate = self.loan_rate(pd)
        if annual_income <= ZERO:
            return self._reject(request_id, borrower, amount, "zero_income")
        if float(debt + amount) / income_f > cfg.max_debt_to_income:
            return self._reject(request_id, borrower, amount, "debt_to_income")
        sheets = sim.ledger.balance_sheets()
        offers = []
        rejected_reasons = []
        for bank in candidates:
            bank_row = sim.banks.id_to_row[bank]
            if not sim.banks.column("active")[bank_row]:
                continue
            assets = sheets[bank]["assets"]
            equity = sheets[bank]["equity"]
            if sim.config.execution.profile == "complete_economy":
                own_shares = sim.crisis.own_share_value(bank)
                assets -= own_shares
                equity -= own_shares
            capital_capacity = money(
                max(ZERO, equity / Decimal(str(cfg.min_equity_ratio)) - assets)
            )
            exposure = sum(
                (
                    sim.ledger.balance(x.asset_account)
                    for x in sim.loans.values()
                    if x.bank_id == bank and x.borrower_id == borrower
                ),
                ZERO,
            )
            concentration_capacity = money(
                max(ZERO, assets * Decimal(str(cfg.max_borrower_share)) - exposure)
            )
            reserve_cash = sim.ledger.available(sim.reserves[bank].asset)
            liquidity_capacity = money(
                reserve_cash / Decimal(str(max(cfg.expected_outflow_share, 1e-12)))
            )
            if bank != home:
                # Il prestito accredita il conto esistente del cliente: il regolamento
                # interbancario trasferisce riserve e limita la quota erogabile.
                liquidity_capacity = min(liquidity_capacity, reserve_cash)
            capacities = {
                "capital": capital_capacity,
                "concentration": concentration_capacity,
                "liquidity": liquidity_capacity,
            }
            grant = min(amount, *capacities.values())
            if grant <= ZERO:
                rejected_reasons.append(
                    min(
                        capacities,
                        key=lambda name: (
                            capacities[name],
                            ("capital", "concentration", "liquidity").index(name),
                        ),
                    )
                )
                continue
            interest = money(grant * weekly_rate(rate))
            if (
                interest > ZERO
                and float(annual_income / Decimal(52)) / float(interest) < cfg.min_interest_coverage
            ):
                rejected_reasons.append("interest_coverage")
                continue
            binding = min(capacities, key=capacities.get)
            reason = "approved" if grant == amount else binding
            offers.append((rate, -grant, bank != home, bank, grant, reason))
        if not offers:
            reason = (
                min(
                    set(rejected_reasons),
                    key=lambda item: (
                        -rejected_reasons.count(item),
                        ("capital", "concentration", "liquidity", "interest_coverage").index(item),
                    ),
                )
                if rejected_reasons
                else "no_active_lender"
            )
            return self._reject(request_id, borrower, amount, reason)
        _, _, _, bank, grant, limiting_reason = min(offers)
        loan = sim.settlement.originate_loan(
            request_id, borrower, bank, grant, rate, week=sim.week, purpose=purpose
        )
        sim._loans[loan.id] = loan.model_copy(update={"collateral_value": collateral_value})
        status = "approved" if grant == amount else "partial"
        decision = CreditDecision(
            request_id=request_id,
            borrower_id=borrower,
            bank_id=bank,
            requested=amount,
            granted=grant,
            annual_rate=rate,
            status=status,
            reason="approved" if status == "approved" else limiting_reason,
        )
        self.processed_requests[request_id] = decision
        return decision

    @money_context
    def refinance(self, bank_id, amount):
        """Facility garantita: ordinaria su bond, emergenza su prestiti performing."""
        sim, cfg = self.sim, self.sim.config.banks
        amount = money(amount)
        if amount <= ZERO:
            return ZERO
        choices = []
        for bond in sim.bonds.values():
            if bond.holder_id == bank_id:
                choices.append(
                    ("ordinary", bond.asset_account, self.policy.policy_rate, cfg.ordinary_haircut)
                )
        if sim.config.central_bank.emergency_lending_enabled:
            for loan in sim.loans.values():
                if loan.bank_id == bank_id and loan.status == "performing":
                    choices.append(
                        (
                            "emergency",
                            loan.asset_account,
                            self.policy.emergency_rate,
                            cfg.emergency_haircut,
                        )
                    )
        for facility, collateral, rate, haircut in choices:
            available = sim.ledger.available(collateral)
            capacity = money(available * Decimal(str(1 - haircut)))
            cap = money(
                sim.ledger.balance_sheets()[bank_id]["assets"]
                * Decimal(str(cfg.facility_cap_share))
            )
            granted = min(amount, capacity, cap)
            if granted <= ZERO:
                continue
            pledged = money(granted / Decimal(str(1 - haircut)))
            loan_id = f"cb:{sim.week}:{bank_id}:{len(self.cb_loans)}"
            sim.ledger.reserve(f"collateral:{loan_id}", collateral, pledged)
            reserve = sim.reserves[bank_id]
            bank_debt = Account(
                f"{bank_id}:cb_loan:{loan_id}",
                bank_id,
                AccountKind.LIABILITY,
                "central_bank_loan",
                True,
                sim.central_bank.id,
                loan_id,
            )
            cb_asset = Account(
                f"{sim.central_bank.id}:cb_loan:{loan_id}",
                sim.central_bank.id,
                AccountKind.ASSET,
                "central_bank_loan",
                True,
                bank_id,
                loan_id,
            )
            sim.ledger.post(
                Transaction(
                    f"facility:{loan_id}",
                    sim.week,
                    "financial_service",
                    "Rifinanziamento garantito",
                    (
                        change(sim.ledger.accounts[reserve.asset], granted),
                        change(bank_debt, granted),
                        change(cb_asset, granted),
                        change(sim.ledger.accounts[reserve.liability], granted),
                    ),
                ),
                new_accounts=(bank_debt, cb_asset),
            )
            self.cb_loans[loan_id] = CentralBankLoan(
                id=loan_id,
                bank_id=bank_id,
                principal=granted,
                annual_rate=rate,
                originated_week=sim.week,
                due_week=sim.week + 1,
                facility=facility,
                collateral_account=collateral,
                collateral_amount=pledged,
                haircut=haircut,
                status="performing",
            )
            self.flows["central_bank_credit"] += granted
            return granted
        return ZERO

    @money_context
    def service(self):
        """Interessi sullo stock di apertura; nessun interesse sui nuovi utilizzi."""
        self.open_week()
        sim = self.sim
        for loan_id, facility in list(self.cb_loans.items()):
            if facility.status == "closed" or facility.due_week > sim.week:
                continue
            reserve = sim.reserves[facility.bank_id]
            interest = money(facility.principal * weekly_rate(facility.annual_rate))
            due = money(facility.principal + max(interest, ZERO))
            if sim.ledger.available(reserve.asset) < due:
                # Il rinnovo è esplicito e non nasconde gli interessi non pagati.
                self.cb_loans[loan_id] = facility.model_copy(
                    update={"due_week": sim.week + 1, "status": "arrears"}
                )
                continue
            bank_debt = sim.ledger.accounts[f"{facility.bank_id}:cb_loan:{loan_id}"]
            cb_asset = sim.ledger.accounts[f"{sim.central_bank.id}:cb_loan:{loan_id}"]
            postings = [
                change(sim.ledger.accounts[reserve.asset], -facility.principal),
                change(bank_debt, -facility.principal),
                change(cb_asset, -facility.principal),
                change(sim.ledger.accounts[reserve.liability], -facility.principal),
            ]
            additions = ()
            if interest > ZERO:
                expense = Account(
                    f"{facility.bank_id}:cb_interest",
                    facility.bank_id,
                    AccountKind.EXPENSE,
                    "central_bank_interest",
                )
                income = Account(
                    f"{sim.central_bank.id}:cb_interest",
                    sim.central_bank.id,
                    AccountKind.INCOME,
                    "central_bank_interest",
                )
                postings.extend(
                    (
                        change(sim.ledger.accounts[reserve.asset], -interest),
                        change(expense, interest),
                        change(sim.ledger.accounts[reserve.liability], -interest),
                        change(income, interest),
                    )
                )
                additions = tuple(x for x in (expense, income) if x.id not in sim.ledger.accounts)
            sim.ledger.post(
                Transaction(
                    f"facility-repayment:{sim.week}:{loan_id}",
                    sim.week,
                    "financial_service",
                    "Rientro facility BC",
                    tuple(postings),
                ),
                new_accounts=additions,
            )
            sim.ledger.release(f"collateral:{loan_id}")
            self.cb_loans[loan_id] = facility.model_copy(update={"status": "closed"})
        deposit_rate = sim.config.banks.deposit_rate_pass_through * self.policy.reserve_rate
        for owner, dep in sim.deposits.items():
            due = money(sim.ledger.balance(dep.asset) * weekly_rate(deposit_rate))
            if due == ZERO:
                continue
            owner_income = Account(
                f"{owner}:deposit_interest", owner, AccountKind.INCOME, "deposit_interest"
            )
            bank_expense = Account(
                f"{dep.bank_id}:deposit_interest",
                dep.bank_id,
                AccountKind.EXPENSE,
                "deposit_interest",
            )
            # Per tassi negativi il segno inverte il flusso; non è ammesso uno scoperto.
            if due < ZERO and sim.ledger.available(dep.asset) < -due:
                due = -sim.ledger.available(dep.asset)
            sim.ledger.post(
                Transaction(
                    f"deposit-interest:{sim.week}:{owner}",
                    sim.week,
                    "financial_service",
                    "Remunerazione deposito",
                    (
                        change(sim.ledger.accounts[dep.asset], due),
                        change(owner_income, due),
                        change(sim.ledger.accounts[dep.liability], due),
                        change(bank_expense, due),
                    ),
                ),
                new_accounts=tuple(
                    a for a in (owner_income, bank_expense) if a.id not in sim.ledger.accounts
                ),
            )
            self.flows["deposit_interest"] += due
        for bank, reserve in sim.reserves.items():
            due = money(sim.ledger.balance(reserve.asset) * weekly_rate(self.policy.reserve_rate))
            if due == ZERO:
                continue
            if due < ZERO and sim.ledger.available(reserve.asset) < -due:
                due = -sim.ledger.available(reserve.asset)
            bank_income = Account(
                f"{bank}:reserve_interest", bank, AccountKind.INCOME, "reserve_interest"
            )
            cb_expense = Account(
                f"{sim.central_bank.id}:reserve_interest",
                sim.central_bank.id,
                AccountKind.EXPENSE,
                "reserve_interest",
            )
            sim.ledger.post(
                Transaction(
                    f"reserve-interest:{sim.week}:{bank}",
                    sim.week,
                    "financial_service",
                    "Remunerazione riserve",
                    (
                        change(sim.ledger.accounts[reserve.asset], due),
                        change(bank_income, due),
                        change(sim.ledger.accounts[reserve.liability], due),
                        change(cb_expense, due),
                    ),
                ),
                new_accounts=tuple(
                    a for a in (bank_income, cb_expense) if a.id not in sim.ledger.accounts
                ),
            )
            self.flows["reserve_interest"] += due
        for loan_id, loan in list(sim.loans.items()):
            if loan.status not in {"performing", "arrears"} or sim.week < loan.interest_from_week:
                continue
            principal = sim.ledger.balance(loan.debt_account)
            current = money(principal * weekly_rate(loan.annual_rate))
            due = money(current + loan.arrears)
            if due <= ZERO:
                continue  # tassi prestiti negativi non sono offerti dalla formula D1
            dep = sim.deposits[loan.borrower_id]
            if sim.ledger.available(dep.asset) < due:
                sim._loans[loan_id] = loan.model_copy(
                    update={
                        "arrears": money(loan.arrears + current),
                        "status": "arrears",
                    }
                )
                continue
            try:
                reserve_lines = sim.settlement._reserve_transfer_lines(
                    dep.bank_id, loan.bank_id, due
                )
            except SettlementError as exc:
                if exc.code != "bank_settlement_failure":
                    raise
                sim._loans[loan_id] = loan.model_copy(
                    update={
                        "arrears": money(loan.arrears + current),
                        "status": "arrears",
                    }
                )
                continue
            expense = Account(
                f"{loan.borrower_id}:loan_interest",
                loan.borrower_id,
                AccountKind.EXPENSE,
                "loan_interest",
            )
            income = Account(
                f"{loan.bank_id}:loan_interest", loan.bank_id, AccountKind.INCOME, "loan_interest"
            )
            postings = [
                change(sim.ledger.accounts[dep.asset], -due),
                change(expense, due),
                change(sim.ledger.accounts[dep.liability], -due),
                change(income, due),
                *reserve_lines,
            ]
            sim.ledger.post(
                Transaction(
                    f"interest:{sim.week}:{loan_id}",
                    sim.week,
                    "financial_service",
                    "Interesse prestito",
                    tuple(postings),
                ),
                new_accounts=tuple(a for a in (expense, income) if a.id not in sim.ledger.accounts),
            )
            self.flows["loan_interest"] += due
            update = {"arrears": ZERO, "arrears_weeks": 0, "status": "performing"}
            if sim.week >= loan.next_review_week:
                update.update(
                    annual_rate=self.loan_rate(0.0),
                    next_review_week=sim.week + sim.config.banks.review_weeks,
                )
            sim._loans[loan_id] = loan.model_copy(update=update)
