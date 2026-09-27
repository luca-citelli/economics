"""Investimenti con cassa disponibile: pianificazione anticipata, installazione differita."""

from decimal import Decimal

import numpy as np

from economic_sim.contracts import Order
from economic_sim.markets.goods import clear_market
from economic_sim.money import ZERO, money, money_context


def plan_investment(sim):
    cfg = sim.config.real_economy
    targets = np.zeros(len(sim.firms.ids))
    for row, firm_id in enumerate(sim.firms.ids):
        if not sim.firms.column("active")[row]:
            continue
        firm = int(firm_id)
        capital = sim.physical.quantity(firm, 11, "installed_capital")
        pid = int(sim.firms.column("product_id")[row])
        demand = sim.firms.column("previous_orders")[row]
        desired_capital = demand / sim.products[pid - 1].capacity_per_capital
        expansion = min(capital * cfg.investment_max_growth, max(0, desired_capital - capital))
        targets[row] = capital * sim.products[10].depreciation + expansion
    sim.investment_targets = targets


@money_context
def buy_capital(sim):
    orders = []
    max_price = money(
        str(max(sim.firms.column("offered_price")[sim.firms.column("product_id") == 11]))
    )
    for row, firm_id in enumerate(sim.firms.ids):
        firm = int(firm_id)
        if sim.investment_targets[row] <= 0:
            continue
        wage_buffer = (
            sim.firms.column("planned_workers")[row] * sim.firms.column("offered_wage")[row]
        )
        input_buffer = float(sim.input_costs[row])
        buffer = money(
            str((wage_buffer + input_buffer) * sim.config.real_economy.investment_buffer_weeks)
        )
        available = max(ZERO, sim.ledger.available(sim.deposits[firm].asset) - buffer)
        budget = min(available, money(Decimal(str(sim.investment_targets[row])) * max_price))
        orders.append(
            Order(
                buyer_id=firm,
                product_id=11,
                quantity=float(sim.investment_targets[row]),
                budget=budget,
                max_price=max_price,
                week=sim.week,
            )
        )
    result = clear_market(sim, 11, orders, stream="resources", destination="pending_capital")
    sim.market_results.append(result)
    return sum((t.total_cost for t in result.trades), ZERO)
