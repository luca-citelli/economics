"""Definizioni v1 T02: prezzi osservati/imputati e bridge degli inventari al costo."""

import csv
from pathlib import Path

import numpy as np

from economic_sim.money import ZERO, money, money_context


@money_context
def firm_accounts(sim):
    inventory = revenue = cogs = profit = ZERO
    for account in sim.ledger.accounts.values():
        if account.entity_id not in sim.firms.id_to_row:
            continue
        value = sim.ledger.balance(account.id)
        if account.purpose == "inventory":
            inventory += value
        if account.purpose == "sales":
            revenue += value
        if account.purpose == "cost_of_sales":
            cogs += value
        if account.kind.value == "income":
            profit += value
        elif account.kind.value == "expense":
            profit -= value
    return inventory, revenue, cogs, profit


def initialize_metrics(sim):
    sim.base_prices = np.array([float(p.opening_price) for p in sim.products])
    sim.cpi_prices = sim.base_prices[:7].copy()
    sim.cpi_ages = np.zeros(7, dtype=np.int64)
    sim.cpi_history = [100.0]
    sim.history = []
    sim.weekly_metrics = {}


@money_context
def collect(sim, start_accounts, consumption, investment, depreciation, spoilage, labor):
    result = {"week": sim.week, **sim.monetary_metrics(), **labor}
    employed = int((sim.people.column("employer_id") != -1).sum())
    n = len(sim.people.ids)
    ratios = sim.people.column("satisfaction")
    result.update(
        population=n,
        employed=employed,
        labor_force=n,
        unemployment_rate=1 - employed / n,
        primary_satisfaction=float(ratios[:, :3].min(axis=1).mean()),
        primary_coverage=float(
            np.mean(ratios[:, :3].min(axis=1) >= sim.config.real_economy.deprivation_threshold)
        ),
        deprivation_weeks_mean=float(sim.people.column("deprivation_weeks").mean()),
        income_mean=float(sim.weekly_income.mean()),
        income_median=float(np.median(sim.weekly_income)),
        consumption=consumption,
        investment=investment,
        flow_saving=labor["wages_net"] - consumption,
        government_consumption=sim.treasury.flows["spending"],
        depreciation=depreciation,
        spoilage=spoilage,
    )
    previous_cpi = sim.cpi_history[-1]
    imputed = np.ones(7, dtype=bool)
    sim.cpi_ages += 1
    for market in sim.market_results:
        p = sim.product_by_name[market.market_id]
        prefix = p.name
        quantity = sum(t.quantity for t in market.trades)
        result.update(
            {
                f"{prefix}.transacted_price": market.transacted_price,
                f"{prefix}.offered_price": market.offered_price,
                f"{prefix}.quantity": quantity,
                f"{prefix}.trades": len(market.trades),
                f"{prefix}.desired_demand": market.financeable_demand + market.unfinanceable_demand,
                f"{prefix}.financeable_demand": market.financeable_demand,
                f"{prefix}.unfinanceable_demand": market.unfinanceable_demand,
                f"{prefix}.unfilled_demand": market.unfilled_demand,
                f"{prefix}.residual_supply": market.residual_supply,
                f"{prefix}.coverage": quantity / market.financeable_demand
                if market.financeable_demand
                else None,
            }
        )
        mask = sim.firms.column("product_id") == p.id
        result[f"{prefix}.output"] = float(sim.output[mask].sum())
        result[f"{prefix}.production_cost"] = sum(
            (sim.output_costs[r] for r in np.flatnonzero(mask)), ZERO
        )
        # Capacità misurata prima dell'ammortamento di chiusura.
        capacity = float(sim.opening_capacity[mask].sum())
        result[f"{prefix}.capacity_utilization"] = (
            float(sim.output[mask].sum()) / capacity if capacity else 0.0
        )
        if p.id <= 7:
            col = p.id - 1
            if market.transacted_price is not None:
                sim.cpi_prices[col] = float(market.transacted_price)
                sim.cpi_ages[col] = 0
                imputed[col] = False
            result[f"{prefix}.cpi_price_age"] = int(sim.cpi_ages[col])
            result[f"{prefix}.satisfaction"] = float(ratios[:, col].mean()) if col < 6 else None
            result[f"{prefix}.consumed"] = float(sim.consumed[:, col].sum())
    weights = np.array([sim.config.real_economy.cpi_basket[p.name] for p in sim.products[:7]])
    base_cost = weights * sim.base_prices[:7]
    cpi = 100 * float(np.dot(weights, sim.cpi_prices) / base_cost.sum())
    result.update(
        cpi=cpi,
        inflation_weekly=cpi / previous_cpi - 1,
        inflation_annual=cpi / sim.cpi_history[sim.week - 52] - 1 if sim.week >= 52 else None,
        cpi_imputed_share=float(base_cost[imputed].sum() / base_cost.sum()),
        cpi_max_price_age=int(sim.cpi_ages.max()),
    )
    for category, part in (
        ("primary", slice(0, 3)),
        ("secondary", slice(3, 6)),
        ("luxury", slice(6, 7)),
    ):
        result[f"cpi_{category}"] = 100 * float(
            np.dot(weights[part], sim.cpi_prices[part]) / base_cost[part].sum()
        )
    inventory, revenue, cogs, profit = firm_accounts(sim)
    initial_inventory, initial_revenue, initial_cogs, initial_profit = start_accounts
    output_cost = sum(sim.output_costs, ZERO)
    inputs = sum(sim.input_costs, ZERO)
    result["inventory_change_at_cost"] = inventory - initial_inventory
    result["inventory_change_excluding_losses"] = (
        inventory - initial_inventory + spoilage + sim.crisis.flows["liquidation_inventory_loss"]
    )
    result["gdp_production"] = (
        revenue - initial_revenue + output_cost - (cogs - initial_cogs) - inputs
    )
    result["gdp_expenditure"] = (
        consumption
        + sim.treasury.flows["spending"]
        + investment
        + result["inventory_change_excluding_losses"]
    )
    result["gdp_discrepancy"] = result["gdp_production"] - result["gdp_expenditure"]
    result["gdp_real_base_prices"] = float(
        sum(
            sim.output[r] * sim.base_prices[p - 1]
            for r, p in enumerate(sim.firms.column("product_id"))
        )
        - np.sum(sim.inputs_used * sim.base_prices[7:10])
    )
    result["firm_profit"] = profit - initial_profit
    result["firm_revenue"] = revenue - initial_revenue
    result["production_cost"] = money(output_cost)
    result["intermediate_consumption_cost"] = money(inputs)
    sim.cpi_history.append(cpi)
    return result


def export_csv(sim, path):
    if not sim.history:
        raise ValueError("Nessuna settimana conclusa da esportare")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        fieldnames = list(dict.fromkeys(key for row in sim.history for key in row))
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sim.history)
