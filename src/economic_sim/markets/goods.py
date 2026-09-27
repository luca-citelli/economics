"""Sessione comune per beni finali, risorse e capitale; ordini a budget vincolato."""

from collections import Counter
from decimal import Decimal

import numpy as np

from economic_sim.accounting.settlement import SettlementError
from economic_sim.contracts import MarketResult, Offer, Trade
from economic_sim.money import ZERO, money, money_context


@money_context
def affordable_quantity(quantity, price, budget):
    """Il float è intenzione fisica; il pagamento quantizzato deve stare nel budget esatto."""
    q = min(quantity, float(budget / price))
    while q > 0 and money(Decimal(str(q)) * price) > budget:
        q = float(np.nextafter(q, 0))
    if q <= 0 or money(Decimal(str(q)) * price) <= ZERO:
        return 0.0
    return q


def published_offers(sim, product):
    f = sim.firms
    prices, qualities = f.column("offered_price"), f.column("quality")
    return tuple(
        Offer(
            seller_id=int(f.ids[r]),
            product_id=product,
            quantity=sim.physical.available(int(f.ids[r]), product),
            price=money(str(prices[r])),
            quality=float(qualities[r]),
            week=sim.week,
        )
        for r in np.flatnonzero((f.column("product_id") == product) & f.column("active"))
    )


@money_context
def clear_market(
    sim, product, orders, *, stream="goods", quality_preferences=None, destination="inventory"
):
    """Una domanda per compratore/prodotto. Il residuo è contato solo dopo tutti i tentativi."""
    orders = sorted(orders, key=lambda order: order.buyer_id)
    if len({o.buyer_id for o in orders}) != len(orders):
        raise ValueError("Ordine duplicato per compratore/prodotto")
    if any(o.product_id != product or o.week != sim.week for o in orders):
        raise ValueError("Ordine fuori sessione")
    offers = published_offers(sim, product)
    remaining_supply = {o.seller_id: o.quantity for o in offers}
    references = [o.price for o in offers]
    reference = sum(references, ZERO) / len(references) if references else None
    reputations = sim.firms.column("reputation")
    max_quality = max((o.quality for o in offers), default=1.0)
    preferences = quality_preferences or {}
    trades, reasons, holds = [], Counter(), []
    funded_total = unfunded_total = unfilled_total = 0.0
    prefix = f"w{sim.week}:market:{product}"
    try:
        # Tutti i budget della sessione sono vincolati prima di qualsiasi vendita.
        for order in orders:
            if order.budget:
                hold = f"{prefix}:hold:{order.buyer_id}"
                sim.ledger.reserve(hold, sim.deposits[order.buyer_id].asset, order.budget)
                holds.append(hold)
        for i in sim.rng[stream].permutation(len(orders)):
            order = orders[int(i)]
            buyer, budget = order.buyer_id, order.budget
            hold = f"{prefix}:hold:{buyer}"
            if budget:
                sim.ledger.release(hold)
                holds.remove(hold)
            eligible = [o for o in offers if o.seller_id != buyer and o.price <= order.max_price]
            cheapest = min((o.price for o in eligible), default=order.max_price)
            funded = affordable_quantity(order.quantity, cheapest, budget)
            funded_total += funded
            unfunded_total += max(0, order.quantity - funded)
            remaining = funded
            quality = preferences.get(buyer, 0.0)

            def score(offer, cheapest=cheapest, quality=quality):
                reputation = reputations[sim.firms.id_to_row[offer.seller_id]]
                utility = (
                    -float(offer.price / (reference or cheapest))
                    + quality * offer.quality / max_quality
                    + 0.25 * reputation
                )
                return (-utility, offer.seller_id)

            failure = "no_supply" if not eligible else "supply_or_budget"
            for offer in sorted(eligible, key=score):
                if remaining <= 0 or budget <= ZERO:
                    break
                quantity = affordable_quantity(
                    min(
                        remaining,
                        remaining_supply[offer.seller_id],
                        sim.physical.available(offer.seller_id, product),
                    ),
                    offer.price,
                    budget,
                )
                if quantity <= 0:
                    continue
                total = money(offer.price * Decimal(str(quantity)))
                tx_id = f"{prefix}:trade:{len(trades)}"
                try:
                    sim.settlement.purchase(
                        tx_id,
                        buyer,
                        offer.seller_id,
                        product,
                        quantity,
                        offer.price,
                        sim.physical,
                        week=sim.week,
                        destination=destination,
                    )
                except SettlementError as exc:
                    if exc.code not in {"bank_settlement_failure", "insufficient_customer_funds"}:
                        raise
                    failure = exc.code
                    continue
                trades.append(
                    Trade(
                        id=tx_id,
                        buyer_id=buyer,
                        seller_id=offer.seller_id,
                        product_id=product,
                        quantity=quantity,
                        price=offer.price,
                        total_cost=total,
                        payment_id=tx_id,
                        instrument_id=None,
                    )
                )
                remaining = max(0.0, remaining - quantity)
                remaining_supply[offer.seller_id] -= quantity
                budget -= total
            unfilled_total += remaining
            if remaining > 1e-9:
                reasons[failure] += 1
            if order.quantity - funded > 1e-9:
                reasons["unfinanceable"] += 1
    finally:
        for hold in holds:
            sim.ledger.release(hold)
    quantity = sum(t.quantity for t in trades)
    total = sum((t.total_cost for t in trades), ZERO)
    return MarketResult(
        market_id=sim.products[product - 1].name,
        week=sim.week,
        offers=offers,
        financeable_demand=funded_total,
        unfinanceable_demand=unfunded_total,
        trades=tuple(trades),
        unfilled_demand=unfilled_total,
        residual_supply=sum(remaining_supply.values()),
        offered_price=money(reference) if reference is not None else None,
        transacted_price=money(total / Decimal(str(quantity))) if quantity else None,
        failure_reasons=dict(reasons),
    )
