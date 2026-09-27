"""Kernel batch dell'output, applicazione fisica/contabile e chiusura operativa."""

from decimal import Decimal

import numpy as np

from economic_sim.agents.decisions import potential_output
from economic_sim.money import ZERO, money


def produce(sim, *, extraction):
    f = sim.firms
    pids = f.column("product_id")
    capital = np.array([sim.physical.quantity(int(i), 11, "installed_capital") for i in f.ids])
    inputs = np.array([[sim.physical.available(int(i), p) for p in (8, 9, 10)] for i in f.ids])
    recipes = np.array(
        [
            [sim.products[int(p) - 1].recipe.get(sim.products[c - 1].name, 0) for c in (8, 9, 10)]
            for p in pids
        ]
    )
    reserve = np.array(
        [
            sim.physical.quantity(int(i), int(p), "natural_reserve")
            for i, p in zip(f.ids, pids, strict=True)
        ]
    )
    potential = potential_output(
        capital,
        np.array([sim.products[int(p) - 1].capacity_per_capital for p in pids]),
        f.column("productivity"),
        sim.paid_workers,
        inputs,
        recipes,
        reserve,
        f.column("extractive"),
    )
    output = np.minimum(potential, sim.production_targets)
    for row in np.flatnonzero(f.column("extractive") == extraction):
        firm, pid = int(f.ids[row]), int(pids[row])
        quantity = float(output[row])
        # Arrotondamento fisico verso zero solo se il prodotto q*coeff eccede lo stock.
        while np.any(quantity * recipes[row] > inputs[row]):
            quantity = float(np.nextafter(quantity, 0))
        cost, input_cost = sim.inventory.produce(firm, sim.products[pid - 1], quantity)
        sim.output[row] = quantity
        sim.output_costs[row] = cost
        sim.input_costs[row] = input_cost
        sim.inputs_used[row] = quantity * recipes[row]


def operating_close(sim):
    f, cfg = sim.firms, sim.config.real_economy
    costs = f.column("observed_unit_cost").copy()
    depreciation = ZERO
    spoilage = ZERO
    for row, firm_id in enumerate(f.ids):
        firm = int(firm_id)
        for product in sim.products:
            quantity = sim.physical.available(firm, product.id) * product.depreciation
            spoilage += sim.inventory.consume(
                f"w{sim.week}:spoilage:{firm}:{product.id}",
                firm,
                product.id,
                quantity,
                reason="spoilage",
            )
        capital = sim.physical.quantity(firm, 11, "installed_capital")
        dep = sim.inventory.consume(
            f"w{sim.week}:depreciation:{firm}",
            firm,
            11,
            capital * sim.products[10].depreciation,
            reason="depreciation",
            stock="installed_capital",
        )
        depreciation += dep
        if sim.output[row] > 0:
            unit = float((sim.output_costs[row] + dep) / Decimal(str(sim.output[row])))
            costs[row] = (1 - cfg.cost_smoothing) * costs[row] + cfg.cost_smoothing * unit
    f.replace_column("observed_unit_cost", costs)
    sales = np.zeros(len(f.ids))
    orders = np.zeros(len(f.ids))
    unfilled = np.zeros(len(f.ids))
    reputation = f.column("reputation").copy()
    for result in sim.market_results:
        sellers = [sim.firms.id_to_row[o.seller_id] for o in result.offers]
        if not sellers:
            continue
        for trade in result.trades:
            sales[f.id_to_row[trade.seller_id]] += trade.quantity
        # Un ordine non eseguito è osservato dal mercato una volta, ripartito fra venditori.
        for row in sellers:
            unfilled[row] = result.unfilled_demand / len(sellers)
            orders[row] = sales[row] + unfilled[row]
        total = sales[sellers].sum()
        if total > 0:
            reputation[sellers] = (1 - cfg.reputation_smoothing) * reputation[
                sellers
            ] + cfg.reputation_smoothing * sales[sellers] / total
    f.replace_column("previous_sales", sales)
    f.replace_column("previous_orders", orders)
    f.replace_column("previous_unfilled", unfilled)
    f.replace_column("reputation", np.clip(reputation, 0, 1))
    return money(depreciation), money(spoilage)
