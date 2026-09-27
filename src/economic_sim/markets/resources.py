"""Input acquistati dopo l'estrazione; le estrattive li useranno in t+1."""

import numpy as np

from economic_sim.agents.firms import resource_requirements
from economic_sim.agents.households import allocate_budgets
from economic_sim.contracts import Order
from economic_sim.markets.goods import clear_market
from economic_sim.money import money


def buy_resources(sim):
    orders = {p: [] for p in (8, 9, 10)}
    for row, firm_id in enumerate(sim.firms.ids):
        firm = int(firm_id)
        if not sim.firms.column("active")[row]:
            continue
        output = min(
            sim.production_targets[row],
            sim.paid_workers[row] * sim.firms.column("productivity")[row],
        )
        # Senza scorte le estrattive devono poter riavviare il ciclo successivo con cassa reale.
        if sim.firms.column("extractive")[row]:
            product = sim.products[int(sim.firms.column("product_id")[row]) - 1]
            output = min(
                sim.physical.quantity(firm, 11, "installed_capital") * product.capacity_per_capital,
                sim.production_targets[row],
            )
        requirements = resource_requirements(sim, row, output, replenish=True)
        quantities = np.array([requirements.get(p, 0.0) for p in (8, 9, 10)])
        costs = quantities * sim.reference_prices[7:10]
        free = sim.ledger.available(sim.deposits[firm].asset)
        if costs.sum() > float(free):
            costs *= float(free) / costs.sum()
        budgets = allocate_budgets(costs, free)
        for col, p in enumerate((8, 9, 10)):
            max_price = max(sim.firms.column("offered_price")[sim.firms.column("product_id") == p])
            orders[p].append(
                Order(
                    buyer_id=firm,
                    product_id=p,
                    quantity=float(quantities[col]),
                    budget=budgets[col],
                    max_price=money(str(max_price)),
                    week=sim.week,
                )
            )
    for p in (8, 9, 10):
        sim.market_results.append(clear_market(sim, p, orders[p], stream="resources"))
