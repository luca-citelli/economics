"""Fiscalità e mercato primario dei titoli pubblici T04."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.accounting.physical import PhysicalEntry
from economic_sim.accounting.settlement import SettlementError
from economic_sim.contracts import Bond
from economic_sim.finance import weekly_rate
from economic_sim.money import ZERO, money, money_context


@dataclass(frozen=True)
class BondBid:
    holder_id: int
    quantity: int
    max_price: Decimal
    budget: Decimal
    bid_id: int | None = None

    @property
    def key(self):
        return self.holder_id if self.bid_id is None else self.bid_id


def price_from_yield(annual_yield: float, weeks: int = 52) -> Decimal:
    if annual_yield <= -1:
        raise ValueError("Rendimento richiesto non valido")
    return money(Decimal(str((1 + annual_yield) ** (-weeks / 52))))


@money_context
def clear_bond_auction(quantity: int, bids: list[BondBid], reserve_price: Decimal):
    """Prezzo marginale uniforme; quantità intere e residui ai minori ID."""
    if quantity < 0 or reserve_price <= ZERO:
        raise ValueError("Offerta o prezzo di riserva non valido")
    eligible = []
    seen = set()
    for bid in bids:
        if bid.key in seen or bid.quantity < 0 or bid.max_price <= ZERO or bid.budget < ZERO:
            raise ValueError("Offerta duplicata o invalida")
        seen.add(bid.key)
        affordable = int((bid.budget / bid.max_price).to_integral_value(rounding=ROUND_FLOOR))
        if bid.max_price >= reserve_price and affordable > 0:
            eligible.append((bid, min(bid.quantity, affordable)))
    eligible.sort(key=lambda x: (-x[0].max_price, x[0].key))
    allocations = {}
    remaining = quantity
    clearing_price = None
    for price in sorted({bid.max_price for bid, _ in eligible}, reverse=True):
        group = [(bid, q) for bid, q in eligible if bid.max_price == price]
        total = sum(q for _, q in group)
        if remaining <= 0:
            break
        if total <= remaining:
            for bid, q in group:
                allocations[bid.key] = q
            remaining -= total
        else:
            base = {bid.key: remaining * q // total for bid, q in group}
            residue = remaining - sum(base.values())
            order = sorted(group, key=lambda x: (-(remaining * x[1] % total), x[0].key))
            for bid, _ in order[:residue]:
                base[bid.key] += 1
            allocations.update(base)
            remaining = 0
        clearing_price = price
    return clearing_price, {k: v for k, v in allocations.items() if v}, remaining


class Treasury:
    def __init__(self, sim):
        self.sim = sim
        self.last_price = None
        self.expected_policy_rate = sim.config.central_bank.policy_rate
        self.pending_cb_orders = {}
        self.pending_budgets = {}
        self.active_bond_purchase_budget = sim.config.central_bank.weekly_bond_purchase_budget
        self.tax_due = {}
        self.tax_arrears = {}
        self.default_arrears = ZERO
        self.flows = {}
        self.open_week()

    def open_week(self):
        if self.sim.week in self.pending_budgets:
            self.active_bond_purchase_budget = self.pending_budgets.pop(self.sim.week)
        self.flows = dict(
            tax=ZERO,
            labor_tax=ZERO,
            profit_tax=ZERO,
            profit_tax_accrued=ZERO,
            spending=ZERO,
            bonds_issued=ZERO,
            bond_proceeds=ZERO,
            bond_repaid=ZERO,
            bond_interest=ZERO,
            spending_rationed=ZERO,
            bond_offered=ZERO,
            bond_unsold=ZERO,
            funding_shortfall=ZERO,
        )
        self.opening_balance = self.available()

    def schedule_cb_order(self, week, budget, max_price):
        if week <= self.sim.week or money(budget) <= ZERO or money(max_price) <= ZERO:
            raise ValueError("Ordine BC una tantum: settimana futura e importi positivi")
        self.pending_cb_orders.setdefault(week, []).append((money(budget), money(max_price)))

    def _a(self, aid):
        return self.sim.ledger.accounts[aid]

    def _post(self, tx_id, phase, reason, lines, additions=()):
        sim = self.sim
        sim.ledger.post(
            Transaction(tx_id, sim.week, phase, reason, tuple(lines)),
            new_accounts=tuple(a for a in additions if a.id not in sim.ledger.accounts),
        )

    def _cash_lines(self, holder, amount, *, into_treasury):
        """Sposta liquidità fra detentore e Tesoro senza creare depositi o riserve."""
        sim = self.sim
        sign = 1 if into_treasury else -1
        gov, cb = sim.government.id, sim.central_bank.id
        lines = [
            change(self._a(f"{gov}:treasury"), sign * amount),
            change(self._a(f"{cb}:treasury"), sign * amount),
        ]
        if holder == cb:
            return lines
        if holder in sim.deposits:
            dep = sim.deposits[holder]
            reserve = sim.reserves[dep.bank_id]
            lines += [
                change(self._a(dep.asset), -sign * amount),
                change(self._a(dep.liability), -sign * amount),
            ]
        elif holder in sim.reserves:
            reserve = sim.reserves[holder]
        else:
            raise ValueError("Detentore non ammesso")
        lines += [
            change(self._a(reserve.asset), -sign * amount),
            change(self._a(reserve.liability), -sign * amount),
        ]
        return lines

    def available(self):
        return self.sim.ledger.available(f"{self.sim.government.id}:treasury")

    @money_context
    def service_taxes(self):
        sim = self.sim
        for entity, (due_week, amount) in sorted(list(self.tax_due.items())):
            if due_week > sim.week:
                continue
            source = (
                sim.deposits[entity].asset if entity in sim.deposits else sim.reserves[entity].asset
            )
            paid = min(amount, sim.ledger.available(source))
            if paid > ZERO:
                payable = self._a(f"{entity}:profit_tax_payable")
                receivable = self._a(f"{sim.government.id}:tax_receivable:{entity}")
                self._post(
                    f"tax:pay:{sim.week}:{entity}",
                    "financial_service",
                    "Imposta profitti",
                    [
                        *self._cash_lines(entity, paid, into_treasury=True),
                        change(payable, -paid),
                        change(receivable, -paid),
                    ],
                )
                self.flows["tax"] += paid
                self.flows["profit_tax"] += paid
            remaining = amount - paid
            if remaining:
                self.tax_due[entity] = (sim.week + 1, remaining)
                self.tax_arrears[entity] = remaining
            else:
                del self.tax_due[entity]
                self.tax_arrears.pop(entity, None)

    @money_context
    def accrue_profit_tax(self, opening_profit):
        sim = self.sim
        rate = Decimal(str(sim.config.government.profit_tax_rate))
        if rate == ZERO:
            return
        closing_profit = self.profit_snapshot()
        for entity in [*map(int, sim.firms.ids), *map(int, sim.banks.ids)]:
            if (
                sim.config.execution.profile == "complete_economy"
                and entity in sim.firms.id_to_row
                and entity in sim.crisis.liquidations
            ):
                continue
            taxable = max(ZERO, closing_profit[entity] - opening_profit.get(entity, ZERO))
            due = money(taxable * rate)
            if due <= ZERO:
                continue
            expense = Account(f"{entity}:profit_tax", entity, AccountKind.EXPENSE, "profit_tax")
            payable = Account(
                f"{entity}:profit_tax_payable", entity, AccountKind.LIABILITY, "profit_tax"
            )
            receivable = Account(
                f"{sim.government.id}:tax_receivable:{entity}",
                sim.government.id,
                AccountKind.ASSET,
                "tax_receivable",
            )
            income = Account(
                f"{sim.government.id}:profit_tax_income",
                sim.government.id,
                AccountKind.INCOME,
                "profit_tax",
            )
            self._post(
                f"tax:accrue:{sim.week}:{entity}",
                "distributions",
                "Imposta maturata",
                [
                    change(expense, due),
                    change(payable, due),
                    change(receivable, due),
                    change(income, due),
                ],
                (expense, payable, receivable, income),
            )
            old = self.tax_due.get(entity, (sim.week + 1, ZERO))[1]
            self.tax_due[entity] = (sim.week + 1, old + due)
            self.flows["profit_tax_accrued"] += due

    @money_context
    def accrue_bonds(self):
        sim = self.sim
        for bond in sim.bonds.values():
            if sim.week <= bond.issued_week or sim.week > bond.maturity_week:
                continue
            carrying = sim.ledger.balance(bond.asset_account)
            if carrying == bond.face_value:
                continue
            rate = weekly_rate(float(Decimal(1) / bond.issue_price - 1))
            interest = money(carrying * rate)
            if carrying < bond.face_value:
                interest = min(bond.face_value - carrying, interest)
            else:
                interest = max(bond.face_value - carrying, interest)
            if sim.week == bond.maturity_week:
                interest = bond.face_value - carrying
            if interest == ZERO:
                continue
            holder_income = Account(
                f"{bond.holder_id}:bond_interest",
                bond.holder_id,
                AccountKind.INCOME,
                "bond_interest",
            )
            gov_expense = Account(
                f"{sim.government.id}:bond_interest",
                sim.government.id,
                AccountKind.EXPENSE,
                "bond_interest",
            )
            self._post(
                f"bond:interest:{sim.week}:{bond.id}",
                "financial_service",
                "Accrescimento bond",
                [
                    change(self._a(bond.asset_account), interest),
                    change(holder_income, interest),
                    change(self._a(bond.liability_account), interest),
                    change(gov_expense, interest),
                ],
                (holder_income, gov_expense),
            )
            self.flows["bond_interest"] += interest

    def _bid_budget(self, holder, share):
        sim = self.sim
        source = (
            sim.deposits[holder].asset if holder in sim.deposits else sim.reserves[holder].asset
        )
        return money(sim.ledger.available(source) * Decimal(str(share)))

    def required_yield(self, holder, *, debt=None, held=None):
        sim = self.sim
        if debt is None or held is None:
            outstanding = [
                bond for bond in sim.bonds.values() if sim.ledger.balance(bond.asset_account) > ZERO
            ]
            debt = sum((float(bond.face_value) for bond in outstanding), 0.0)
            held = sum(
                (float(bond.face_value) for bond in outstanding if bond.holder_id == holder), 0.0
            )
        cash = max(float(self.available()), 1.0)
        sovereign_spread = min(0.05, 0.002 * debt / cash)
        concentration_spread = 0.02 * held / max(debt, 1.0)
        if holder in sim.people.id_to_row:
            preference = 0.02 + 0.04 * (
                1 - float(sim.people.column("risk_propensity")[sim.people.id_to_row[holder]])
            )
        else:
            preference = 0.015 + 0.02 * sim.config.banks.expected_outflow_share
        return self.expected_policy_rate + sovereign_spread + concentration_spread + preference

    @money_context
    def auction(self, offered, bids=None):
        sim = self.sim
        cfg = sim.config.government
        reserve_price = price_from_yield(cfg.max_bond_yield)
        if bids is None:
            bids = []
            outstanding = [
                bond for bond in sim.bonds.values() if sim.ledger.balance(bond.asset_account) > ZERO
            ]
            debt = sum((float(bond.face_value) for bond in outstanding), 0.0)
            held = {}
            for bond in outstanding:
                held[bond.holder_id] = held.get(bond.holder_id, 0.0) + float(bond.face_value)
            for person in map(int, sim.people.ids):
                budget = self._bid_budget(person, cfg.household_bond_budget_share)
                p = price_from_yield(
                    self.required_yield(person, debt=debt, held=held.get(person, 0.0))
                )
                bids.append(BondBid(person, int(budget / p), p, budget))
            for bank in map(int, sim.banks.ids):
                budget = self._bid_budget(bank, cfg.bank_bond_budget_share)
                p = price_from_yield(self.required_yield(bank, debt=debt, held=held.get(bank, 0.0)))
                bids.append(BondBid(bank, int(budget / p), p, budget))
            cb = sim.config.central_bank
            one_time = self.pending_cb_orders.pop(sim.week, None)
            if one_time:
                for index, (budget, p) in enumerate(one_time, start=1):
                    bids.append(BondBid(sim.central_bank.id, int(budget / p), p, budget, -index))
            elif cb.primary_bond_purchases_enabled and self.active_bond_purchase_budget > ZERO:
                budget, p = self.active_bond_purchase_budget, cb.bond_max_price
                bids.append(BondBid(sim.central_bank.id, int(budget / p), p, budget))
        # Depositi dei clienti e offerte delle banche insistono sulle stesse riserve.
        # Vincoliamo i budget massimi prima del clearing per non spendere due volte.
        pools = {bank: sim.ledger.available(a.asset) for bank, a in sim.reserves.items()}
        funded_bids = []
        for bid in sorted(bids, key=lambda x: x.holder_id):
            if bid.holder_id == sim.central_bank.id:
                funded_bids.append(bid)
                continue
            bank = (
                sim.deposits[bid.holder_id].bank_id
                if bid.holder_id in sim.deposits
                else bid.holder_id
            )
            cash = (
                sim.ledger.available(sim.deposits[bid.holder_id].asset)
                if bid.holder_id in sim.deposits
                else pools[bank]
            )
            budget = min(bid.budget, cash, pools[bank])
            pools[bank] -= budget
            funded_bids.append(
                BondBid(bid.holder_id, bid.quantity, bid.max_price, budget, bid.bid_id)
            )
        price, bid_allocations, unsold = clear_bond_auction(offered, funded_bids, reserve_price)
        holders = {bid.key: bid.holder_id for bid in funded_bids}
        allocations = {}
        for bid_id, units in bid_allocations.items():
            holder = holders[bid_id]
            allocations[holder] = allocations.get(holder, 0) + units
        self.flows["bond_offered"] += money(offered)
        self.flows["bond_unsold"] += money(unsold)
        if price is None:
            return None, {}, offered
        for holder, units in sorted(allocations.items()):
            cost = money(price * units)
            source = (
                sim.deposits[holder].asset
                if holder in sim.deposits
                else sim.reserves[holder].asset
                if holder in sim.reserves
                else None
            )
            if source and sim.ledger.available(source) < cost:
                raise ValueError("Budget bond non disponibile al settlement")
            bond_id = f"bond:{sim.week}:{holder}"
            asset = Account(
                f"{holder}:bond:{bond_id}",
                holder,
                AccountKind.ASSET,
                "bond",
                True,
                sim.government.id,
                bond_id,
            )
            liability = Account(
                f"{sim.government.id}:bond:{bond_id}",
                sim.government.id,
                AccountKind.LIABILITY,
                "bond",
                True,
                holder,
                bond_id,
            )
            self._post(
                f"bond:issue:{sim.week}:{holder}",
                "treasury",
                "Emissione zero coupon",
                [
                    *self._cash_lines(holder, cost, into_treasury=True),
                    change(asset, cost),
                    change(liability, cost),
                ],
                (asset, liability),
            )
            sim._bonds[bond_id] = Bond(
                id=bond_id,
                issuer_id=sim.government.id,
                holder_id=holder,
                face_value=money(units),
                issue_price=price,
                issued_week=sim.week,
                maturity_week=sim.week + 52,
                asset_account=asset.id,
                liability_account=liability.id,
            )
            self.flows["bonds_issued"] += money(units)
            self.flows["bond_proceeds"] += cost
        self.last_price = price
        sim.events.append(f"bond_auction:{sim.week}:price={price}:sold={offered - unsold}")
        return price, allocations, unsold

    @money_context
    def run(self):
        sim = self.sim
        cfg = sim.config.government
        self.expected_policy_rate = (
            0.8 * self.expected_policy_rate + 0.2 * sim.finance.policy.policy_rate
        )
        maturity = sum(
            (b.face_value for b in sim.bonds.values() if b.maturity_week == sim.week), ZERO
        )
        budget = money(cfg.weekly_budget_per_person * len(sim.people.ids))
        buffer = money(budget * Decimal(str(cfg.cash_buffer_weeks)))
        need = max(ZERO, maturity + budget + buffer - self.available())
        reference = self.last_price or cfg.initial_bond_reference_price
        offered = int((need / reference).to_integral_value(rounding="ROUND_CEILING"))
        if offered:
            self.auction(offered)
        else:
            self.pending_cb_orders.pop(sim.week, None)
        self.flows["funding_shortfall"] = max(ZERO, need - self.flows["bond_proceeds"])
        due_bonds = [
            (bond_id, bond)
            for bond_id, bond in sorted(sim.bonds.items())
            if bond.maturity_week == sim.week
        ]
        for index, (bond_id, bond) in enumerate(due_bonds):
            due = bond.face_value
            if self.available() < due:
                arrears = sum((item.face_value for _, item in due_bonds[index:]), ZERO)
                self.default_arrears += arrears
                sim.events.append(f"sovereign_default:{bond_id}:arrears={arrears}")
                sim.status = "TERMINATED"
                return
            pledged = [
                (loan_id, loan)
                for loan_id, loan in sim.finance.cb_loans.items()
                if loan.status != "closed" and loan.collateral_account == bond.asset_account
            ]
            for loan_id, _ in pledged:
                sim.ledger.release(f"collateral:{loan_id}")
            self._post(
                f"bond:redeem:{bond_id}",
                "treasury",
                "Rimborso nominale",
                [
                    *self._cash_lines(bond.holder_id, due, into_treasury=False),
                    change(self._a(bond.asset_account), -due),
                    change(self._a(bond.liability_account), -due),
                ],
            )
            for loan_id, loan in pledged:
                reserve = sim.reserves[loan.bank_id].asset
                sim.ledger.reserve(f"collateral:{loan_id}", reserve, loan.collateral_amount)
                sim.finance.cb_loans[loan_id] = loan.model_copy(
                    update={"collateral_account": reserve}
                )
            self.flows["bond_repaid"] += due
        affordable = min(budget, self.available())
        self.spending_budget = affordable
        self.flows["spending_rationed"] = budget - affordable

    @money_context
    def purchase(self, tx_id, seller, product, quantity, unit_price):
        sim = self.sim
        amount = money(Decimal(str(quantity)) * unit_price)
        if amount > self.spending_budget or amount > self.available():
            raise ValueError("Budget pubblico insufficiente")
        stock = f"{seller}:inventory:{product}"
        value = sim.ledger.balance(stock)
        total_qty = sim.physical.quantity(seller, product)
        cost = (
            value
            if quantity == total_qty
            else money(value * Decimal(str(quantity)) / Decimal(str(total_qty)))
        )
        revenue = Account(f"{seller}:sales", seller, AccountKind.INCOME, "sales")
        cogs = Account(f"{seller}:cost_of_sales", seller, AccountKind.EXPENSE, "cost_of_sales")
        expense = Account(
            f"{sim.government.id}:purchases",
            sim.government.id,
            AccountKind.EXPENSE,
            "government_consumption",
        )
        entries = (
            PhysicalEntry(
                tx_id, sim.week, "final_goods", "Consumo pubblico", seller, product, -quantity
            ),
        )
        pending = sim.physical.prepare(entries)
        lines = [
            *self._cash_lines(seller, amount, into_treasury=False),
            change(expense, amount),
            change(revenue, amount),
            change(cogs, cost),
            change(self._a(stock), -cost),
        ]
        self._post(tx_id, "final_goods", "Acquisto pubblico", lines, (expense, revenue, cogs))
        sim.physical._commit_prepared(entries, pending)
        self.spending_budget -= amount
        self.flows["spending"] += amount

    @money_context
    def pay_wage(self, tx_id, employer, worker, gross):
        sim = self.sim
        tax = money(gross * Decimal(str(sim.config.government.labor_income_tax_rate)))
        net = gross - tax
        source, target = sim.deposits[employer], sim.deposits[worker]
        if sim.ledger.available(source.asset) < gross:
            raise SettlementError("insufficient_customer_funds")
        src_reserve = sim.reserves[source.bank_id]
        if tax and sim.ledger.available(src_reserve.asset) < tax:
            shortfall = tax - sim.ledger.available(src_reserve.asset)
            if sim.finance.refinance(source.bank_id, shortfall) < shortfall:
                raise SettlementError("bank_settlement_failure")
        lines = [
            change(self._a(source.asset), -gross),
            change(self._a(source.liability), -gross),
            change(self._a(target.asset), net),
            change(self._a(target.liability), net),
        ]
        if source.bank_id != target.bank_id and net:
            if sim.ledger.available(src_reserve.asset) < gross:
                shortfall = gross - sim.ledger.available(src_reserve.asset)
                if sim.finance.refinance(source.bank_id, shortfall) < shortfall:
                    raise SettlementError("bank_settlement_failure")
            dst_reserve = sim.reserves[target.bank_id]
            lines += [
                change(self._a(src_reserve.asset), -net),
                change(self._a(src_reserve.liability), -net),
                change(self._a(dst_reserve.asset), net),
                change(self._a(dst_reserve.liability), net),
            ]
        if tax:
            lines += [
                change(self._a(src_reserve.asset), -tax),
                change(self._a(src_reserve.liability), -tax),
                change(self._a(f"{sim.government.id}:treasury"), tax),
                change(self._a(f"{sim.central_bank.id}:treasury"), tax),
            ]
        work = Account(
            f"{employer}:work_in_progress", employer, AccountKind.ASSET, "work_in_progress", True
        )
        income = Account(f"{worker}:wage_income", worker, AccountKind.INCOME, "wage_income")
        expense = Account(f"{worker}:labor_tax", worker, AccountKind.EXPENSE, "labor_tax")
        tax_income = Account(
            f"{sim.government.id}:labor_tax_income",
            sim.government.id,
            AccountKind.INCOME,
            "labor_tax",
        )
        lines += [change(work, gross), change(income, gross)]
        additions = [work, income]
        if tax:
            lines += [change(expense, tax), change(tax_income, tax)]
            additions += [expense, tax_income]
        self._post(tx_id, "labor_wages", "Salario con trattenuta", lines, additions)
        self.flows["tax"] += tax
        self.flows["labor_tax"] += tax
        return net

    def profit_snapshot(self):
        sim = self.sim
        excluded = (
            {
                "resolution_gain",
                "deposit_conversion_gain",
                "debt_forgiveness",
                "tax_forgiveness",
                "liquidation_gain",
                "liquidation_recovery",
                "in_kind_recovery",
            }
            if sim.config.execution.profile == "complete_economy"
            else set()
        )
        return {
            entity: sum(
                (
                    sim.ledger.balance(a.id) * (1 if a.kind == AccountKind.INCOME else -1)
                    for a in sim.ledger.accounts.values()
                    if a.entity_id == entity
                    and a.kind in (AccountKind.INCOME, AccountKind.EXPENSE)
                    and a.purpose not in excluded
                ),
                ZERO,
            )
            for entity in [*map(int, sim.firms.ids), *map(int, sim.banks.ids)]
        }
