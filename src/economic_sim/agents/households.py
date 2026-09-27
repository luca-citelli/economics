"""Budget distinti per bisogni, risparmio desiderato e prelievo dal patrimonio."""

import numpy as np

from economic_sim.agents.decisions import consumption_budgets, satisfaction
from economic_sim.contracts import Order
from economic_sim.markets.goods import clear_market
from economic_sim.money import ZERO, money, money_context


@money_context
def allocate_budgets(intents, available):
    """Quantizza intenzioni disgiunte senza impegnare due volte l'ultimo micro-UM."""
    result = []
    for intended in intents:
        amount = min(available, max(ZERO, money(str(float(intended)))))
        result.append(amount)
        available -= amount
    return result


def consume_households(sim):
    people, pc = sim.people, sim.config.people
    needs = people.column("needs")
    available = [sim.ledger.available(sim.deposits[int(p)].asset) for p in people.ids]
    intents = consumption_budgets(
        needs,
        sim.reference_prices,
        np.array(available, dtype=float),
        sim.weekly_income,
        people.column("saving_propensity"),
        pc.liquidity_buffer_weeks,
        pc.wealth_drawdown_rate,
    )
    budgets = [
        allocate_budgets(row, amount) for row, amount in zip(intents, available, strict=True)
    ]
    preferences = dict(zip(map(int, people.ids), people.column("quality_propensity"), strict=True))
    consumed = np.zeros((len(people.ids), 7))
    cost = ZERO
    for col in range(7):
        orders = []
        product_prices = sim.firms.column("offered_price")[
            sim.firms.column("product_id") == col + 1
        ]
        for row, person_id in enumerate(people.ids):
            budget = budgets[row][col]
            quantity = float(needs[row, col])
            if col == 6:
                scale = sim.config.real_economy.luxury_utility_scale
                quantity = scale * np.log1p(float(budget) / (sim.reference_prices[col] * scale))
            orders.append(
                Order(
                    buyer_id=int(person_id),
                    product_id=col + 1,
                    quantity=float(quantity),
                    budget=budget,
                    max_price=money(str(float(product_prices.max()))),
                    week=sim.week,
                )
            )
        result = clear_market(sim, col + 1, orders, quality_preferences=preferences)
        sim.market_results.append(result)
        for trade in result.trades:
            consumed[people.id_to_row[trade.buyer_id], col] += trade.quantity
            cost += trade.total_cost
        for person_id in people.ids:
            person = int(person_id)
            quantity = sim.physical.quantity(person, col + 1)
            sim.inventory.consume(
                f"w{sim.week}:consume:{person}:{col + 1}", person, col + 1, quantity
            )
    ratios = satisfaction(consumed, needs)
    people.replace_column("satisfaction", ratios)
    deprived = ratios[:, :3].min(axis=1) < sim.config.real_economy.deprivation_threshold
    people.replace_column(
        "deprivation_weeks", np.where(deprived, people.column("deprivation_weeks") + 1, 0)
    )
    sim.consumed = consumed
    return cost
