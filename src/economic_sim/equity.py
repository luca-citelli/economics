"""Aste primarie di quote e distribuzioni su bilanci autorevoli."""

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.contracts import ShareHolding
from economic_sim.money import QUANTUM, ZERO, money, money_context


@dataclass(frozen=True)
class EquityOffer:
    issuer_id: int
    max_shares: Decimal
    min_price: Decimal
    min_raise: Decimal
    use: str = "capital_goods"


@dataclass(frozen=True)
class EquityBid:
    buyer_id: int
    quantity: Decimal
    max_price: Decimal
    budget: Decimal
    required_return: float


def _shares(value):
    return max(ZERO, Decimal(value).quantize(QUANTUM, rounding=ROUND_DOWN))


class EquityMarket:
    def __init__(self, sim):
        self.sim = sim
        self.last_results = {}
        self.flows = {"equity_proceeds": ZERO, "equity_shares_issued": ZERO, "dividends": ZERO}
        self.profit_history = {}

    def open_week(self):
        self.flows = dict.fromkeys(self.flows, ZERO)
        self.last_results = {}

    def distributable_profit_snapshot(self):
        return self.sim.treasury.profit_snapshot()

    @money_context
    def offer_for(self, issuer):
        sim = self.sim
        cfg = sim.config.crisis_investment
        row = sim.firms.id_to_row[issuer]
        if not sim.firms.column("active")[row] or sim.investment_targets[row] <= 0:
            return None
        issue = sim.share_issues[f"shares:{issuer}"]
        max_shares = _shares(issue.total_shares * Decimal(str(cfg.max_new_share_fraction)))
        if not max_shares:
            return None
        equity = sim.ledger.balance_sheets()[issuer]["equity"]
        book_price = max(
            sim.config.real_economy.price_floor,
            money(max(ZERO, equity) / issue.total_shares * Decimal(str(cfg.book_price_fraction))),
        )
        capital_price = max(
            money(str(x))
            for x in sim.firms.column("offered_price")[sim.firms.column("product_id") == 11]
        )
        planned_cost = money(Decimal(str(sim.investment_targets[row])) * capital_price)
        buffer = money(
            Decimal(
                str(
                    sim.firms.column("planned_workers")[row] * sim.firms.column("offered_wage")[row]
                )
            )
            * Decimal(str(sim.config.real_economy.investment_buffer_weeks))
        )
        gap = planned_cost + buffer - sim.ledger.available(sim.deposits[issuer].asset)
        if gap <= ZERO:
            return None
        return EquityOffer(
            issuer,
            max_shares,
            book_price,
            money(min(gap, max_shares * book_price) * Decimal(str(cfg.minimum_raise_fraction))),
        )

    @money_context
    def bids_for(self, offer):
        sim, cfg = self.sim, self.sim.config.crisis_investment
        issue = sim.share_issues[f"shares:{offer.issuer_id}"]
        history = self.profit_history.get(offer.issuer_id, ())
        expected_profit = (
            max(ZERO, sum(history[-52:], ZERO)) * Decimal(str(52 / max(len(history[-52:]), 1)))
            if history
            else ZERO
        )
        expected_dividend = money(expected_profit * Decimal(str(cfg.expected_payout)))
        shares_after = issue.total_shares + offer.max_shares
        expected_per_share = expected_dividend / shares_after
        bids = []
        for person in map(int, sim.people.ids):
            row = sim.people.id_to_row[person]
            if not sim.people.column("active")[row]:
                continue
            required = cfg.required_return + 0.04 * (
                1 - float(sim.people.column("risk_propensity")[row])
            )
            max_price = money(expected_per_share / Decimal(str(required)))
            if max_price < offer.min_price:
                continue
            primary = sum(
                Decimal(str(sim.people.column("needs")[row, col]))
                * money(str(sim.reference_prices[col]))
                for col in range(3)
            )
            buffer = money(primary * Decimal(str(sim.config.people.liquidity_buffer_weeks)))
            arrears = sum((x.arrears for x in sim.loans.values() if x.borrower_id == person), ZERO)
            cash = sim.ledger.available(sim.deposits[person].asset)
            budget = money(
                max(ZERO, cash - buffer - arrears) * Decimal(str(cfg.household_surplus_fraction))
            )
            quantity = _shares(min(offer.max_shares, budget / max_price)) if max_price else ZERO
            if quantity and money(quantity * max_price) > ZERO:
                bids.append(EquityBid(person, quantity, max_price, budget, required))
        return bids

    @money_context
    def auction(self, offer, bids):
        sim = self.sim
        if (
            offer.issuer_id not in sim.firms.id_to_row
            or offer.max_shares <= ZERO
            or offer.min_price <= ZERO
        ):
            raise ValueError("Offerta azionaria invalida")
        issue_id = f"shares:{offer.issuer_id}"
        issue = sim.share_issues[issue_id]
        if offer.use != "capital_goods" or len({b.buyer_id for b in bids}) != len(bids):
            raise ValueError("Destinazione o offerte duplicate")
        issuer_bank = sim.deposits[offer.issuer_id].bank_id
        pools = {bank: sim.ledger.available(a.asset) for bank, a in sim.reserves.items()}
        funded = []
        holds = []
        try:
            for bid in sorted(bids, key=lambda x: x.buyer_id):
                if (
                    bid.buyer_id not in sim.people.id_to_row
                    or bid.quantity <= ZERO
                    or bid.max_price <= ZERO
                    or bid.budget < ZERO
                    or bid.required_return <= 0
                ):
                    raise ValueError("Offerta investitore invalida")
                dep = sim.deposits[bid.buyer_id]
                limit = min(bid.budget, sim.ledger.available(dep.asset))
                if dep.bank_id != issuer_bank:
                    limit = min(limit, pools[dep.bank_id])
                limit = money(max(ZERO, limit))
                if limit:
                    hold = f"equity:{sim.week}:{offer.issuer_id}:{bid.buyer_id}"
                    sim.ledger.reserve(hold, dep.asset, limit)
                    holds.append(hold)
                    if dep.bank_id != issuer_bank:
                        pools[dep.bank_id] -= limit
                quantity = min(bid.quantity, _shares(limit / bid.max_price))
                if quantity and bid.max_price >= offer.min_price:
                    funded.append((bid, quantity))
            ranked = sorted(funded, key=lambda x: (-x[0].max_price, x[0].buyer_id))
            remaining = offer.max_shares
            allocations = {}
            clearing_price = None
            for bid, quantity in ranked:
                if remaining <= ZERO:
                    break
                allocated = min(remaining, quantity)
                allocations[bid.buyer_id] = allocated
                remaining -= allocated
                clearing_price = bid.max_price
            if clearing_price is None:
                result = {
                    "price": None,
                    "allocated": {},
                    "proceeds": ZERO,
                    "reason": "no_valid_bids",
                }
                self.last_results[offer.issuer_id] = result
                sim.events.append(
                    f"equity_auction_failed:{sim.week}:{offer.issuer_id}:no_valid_bids"
                )
                return result
            # Pareggi al prezzo marginale: pro rata in micro-quote, residui per ID.
            high = {b.buyer_id: q for b, q in ranked if b.max_price > clearing_price}
            marginal = [(b.buyer_id, q) for b, q in ranked if b.max_price == clearing_price]
            available = offer.max_shares - sum(high.values(), ZERO)
            total = sum((q for _, q in marginal), ZERO)
            allocations = high.copy()
            for owner, quantity in marginal:
                allocations[owner] = _shares(min(quantity, available * quantity / total))
            residual = _shares(available - sum((allocations[o] for o, _ in marginal), ZERO))
            for owner, quantity in marginal:
                if residual < QUANTUM:
                    break
                if allocations[owner] + QUANTUM <= quantity:
                    allocations[owner] += QUANTUM
                    residual -= QUANTUM
            allocations = {owner: qty for owner, qty in allocations.items() if qty}
            proceeds = sum((money(q * clearing_price) for q in allocations.values()), ZERO)
            if proceeds < offer.min_raise:
                result = {
                    "price": clearing_price,
                    "allocated": {},
                    "proceeds": ZERO,
                    "reason": "minimum_raise",
                }
                self.last_results[offer.issuer_id] = result
                sim.events.append(
                    f"equity_auction_failed:{sim.week}:{offer.issuer_id}:minimum_raise:price={clearing_price}"
                )
                return result
            for owner, quantity in sorted(allocations.items()):
                sim.ledger.release(f"equity:{sim.week}:{offer.issuer_id}:{owner}")
                holds.remove(f"equity:{sim.week}:{offer.issuer_id}:{owner}")
                cost = money(quantity * clearing_price)
                dep = sim.deposits[owner]
                asset_id = f"{owner}:shares:{offer.issuer_id}"
                asset = Account(
                    asset_id, owner, AccountKind.ASSET, "shares", True, offer.issuer_id, issue_id
                )
                lines = sim.settlement._payment_lines(owner, offer.issuer_id, cost)
                lines.extend(
                    (change(asset, cost), change(sim.ledger.accounts[issue.capital_account], cost))
                )
                sim.ledger.post(
                    Transaction(
                        f"equity:{sim.week}:{offer.issuer_id}:{owner}",
                        sim.week,
                        "investment",
                        "Sottoscrizione quote",
                        tuple(lines),
                    ),
                    new_accounts=(asset,) if asset_id not in sim.ledger.accounts else (),
                )
                holdings = list(sim.share_holdings)
                for index, existing in enumerate(holdings):
                    if existing.issue_id == issue_id and existing.owner_id == owner:
                        holdings[index] = existing.model_copy(
                            update={"quantity": existing.quantity + quantity}
                        )
                        break
                else:
                    holdings.append(
                        ShareHolding(
                            issue_id=issue_id,
                            owner_id=owner,
                            quantity=quantity,
                            asset_account=asset_id,
                        )
                    )
                sim.share_holdings = tuple(holdings)
            sim._share_issues[issue_id] = issue.model_copy(
                update={
                    "total_shares": issue.total_shares + sum(allocations.values(), ZERO),
                    "last_issue_price": clearing_price,
                }
            )
            self.flows["equity_proceeds"] += proceeds
            self.flows["equity_shares_issued"] += sum(allocations.values(), ZERO)
            sim.events.append(
                f"equity_auction:{offer.issuer_id}:price={clearing_price}:proceeds={proceeds}"
            )
            result = {
                "price": clearing_price,
                "allocated": allocations,
                "proceeds": proceeds,
                "reason": "settled",
            }
            self.last_results[offer.issuer_id] = result
            return result
        finally:
            for hold in holds:
                sim.ledger.release(hold)

    def run(self):
        self.open_week()
        for issuer in map(int, self.sim.firms.ids):
            offer = self.offer_for(issuer)
            if offer is not None:
                self.auction(offer, self.bids_for(offer))

    @money_context
    def distribute(self, opening_profit):
        sim, cfg = self.sim, self.sim.config.crisis_investment
        closing_profit = self.distributable_profit_snapshot()
        for issuer, cumulative in sorted(closing_profit.items()):
            weekly = cumulative - opening_profit.get(issuer, ZERO)
            history = self.profit_history.setdefault(issuer, [])
            history.append(weekly)
            if len(history) > 52:
                del history[0]
            if weekly <= ZERO or cumulative <= ZERO:
                continue
            if issuer in sim.firms.id_to_row:
                if not sim.firms.column("active")[sim.firms.id_to_row[issuer]]:
                    continue
                cash_account = sim.deposits[issuer].asset
                wage_buffer = money(
                    str(
                        sim.firms.column("planned_workers")[sim.firms.id_to_row[issuer]]
                        * sim.firms.column("offered_wage")[sim.firms.id_to_row[issuer]]
                        * sim.config.real_economy.investment_buffer_weeks
                    )
                )
                available = max(ZERO, sim.ledger.available(cash_account) - wage_buffer)
            else:
                bank = issuer
                if bank in sim.crisis.resolved_this_week:
                    continue
                sheet = sim.ledger.balance_sheets()[bank]
                own_shares = sim.crisis.own_share_value(bank)
                required = money(
                    (sheet["assets"] - own_shares) * Decimal(str(sim.config.banks.min_equity_ratio))
                )
                if sheet["equity"] - own_shares <= required:
                    continue
                available = min(
                    max(ZERO, sheet["equity"] - own_shares - required),
                    max(
                        ZERO,
                        sim.ledger.available(sim.reserves[bank].asset)
                        - money(
                            sheet["liabilities"]
                            * Decimal(str(sim.config.banks.expected_outflow_share))
                        ),
                    ),
                )
            issue = sim.share_issues[f"shares:{issuer}"]
            if not issue.total_shares:
                continue
            total = min(
                available, money(min(weekly, cumulative) * Decimal(str(cfg.dividend_payout)))
            )
            if total <= ZERO:
                continue
            eligible = [
                h
                for h in sim.share_holdings
                if h.issue_id == issue.id
                and h.quantity > ZERO
                and (h.owner_id in sim.deposits or h.owner_id in sim.reserves)
                and (
                    h.owner_id not in sim.firms.id_to_row
                    or sim.firms.column("active")[sim.firms.id_to_row[h.owner_id]]
                )
                and (
                    h.owner_id not in sim.people.id_to_row
                    or sim.people.column("active")[sim.people.id_to_row[h.owner_id]]
                )
                and (
                    h.owner_id not in sim.banks.id_to_row
                    or sim.banks.column("active")[sim.banks.id_to_row[h.owner_id]]
                )
            ]
            for holding in sorted(eligible, key=lambda h: h.owner_id):
                amount = money(total * holding.quantity / issue.total_shares)
                if amount <= ZERO:
                    continue
                owner = holding.owner_id
                expense = Account(f"{issuer}:dividends", issuer, AccountKind.EXPENSE, "dividends")
                income = Account(f"{owner}:dividends", owner, AccountKind.INCOME, "dividends")
                if issuer in sim.deposits:
                    if owner in sim.deposits:
                        lines = sim.settlement._payment_lines(issuer, owner, amount)
                    else:
                        source = sim.deposits[issuer]
                        lines = [
                            change(sim.ledger.accounts[source.asset], -amount),
                            change(sim.ledger.accounts[source.liability], -amount),
                        ]
                        if source.bank_id != owner:
                            lines.extend(
                                sim.settlement._reserve_transfer_lines(
                                    source.bank_id, owner, amount
                                )
                            )
                else:
                    if owner in sim.deposits:
                        receiver = sim.deposits[owner]
                        lines = [
                            change(sim.ledger.accounts[receiver.asset], amount),
                            change(sim.ledger.accounts[receiver.liability], amount),
                        ]
                        if receiver.bank_id != issuer:
                            lines.extend(
                                sim.settlement._reserve_transfer_lines(
                                    issuer, receiver.bank_id, amount
                                )
                            )
                    elif owner != issuer:
                        lines = sim.settlement._reserve_transfer_lines(issuer, owner, amount)
                    else:
                        continue  # Quote proprie ricevute in natura: nessun auto-dividendo.
                lines.extend((change(expense, amount), change(income, amount)))
                sim.ledger.post(
                    Transaction(
                        f"w{sim.week}:dividend:{issuer}:{owner}",
                        sim.week,
                        "distributions",
                        "Dividendo da utile distribuibile",
                        tuple(lines),
                    ),
                    new_accounts=tuple(
                        a for a in (expense, income) if a.id not in sim.ledger.accounts
                    ),
                )
                self.flows["dividends"] += amount
