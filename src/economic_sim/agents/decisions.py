"""Kernel puri: copie/array in ingresso, intenzioni in uscita, nessun settlement/RNG."""

import numpy as np


def consumption_budgets(needs, prices, free, income, saving, buffer_weeks, drawdown):
    costs = needs[:, :6] * prices[:6]
    primary_cost = costs[:, :3].sum(axis=1)
    primary = np.minimum(free, primary_cost)
    result = np.zeros((len(free), 7))
    result[:, :3] = (
        costs[:, :3]
        * np.divide(primary, primary_cost, out=np.zeros_like(primary), where=primary_cost > 0)[
            :, None
        ]
    )
    saving_target = np.maximum(income, 0) * saving
    buffer = primary_cost * buffer_weeks * (1 + saving)
    from_income = np.maximum(0, income - saving_target - primary)
    from_wealth = drawdown * np.maximum(0, free - np.maximum(income, 0) - buffer - saving_target)
    discretionary = np.minimum(np.maximum(0, free - primary), from_income + from_wealth)
    secondary_cost = costs[:, 3:6].sum(axis=1)
    secondary = np.minimum(discretionary, secondary_cost)
    result[:, 3:6] = (
        costs[:, 3:6]
        * np.divide(
            secondary, secondary_cost, out=np.zeros_like(secondary), where=secondary_cost > 0
        )[:, None]
    )
    result[:, 6] = discretionary - secondary
    return result


def satisfaction(consumed, needs):
    ratios = np.divide(
        consumed[:, :6], needs[:, :6], out=np.ones_like(consumed[:, :6]), where=needs[:, :6] > 0
    )
    ratios = np.clip(ratios, 0, 1)
    # Il lusso non ha denominatore fisico: utilità normalizzata, non bisogno soddisfatto.
    return np.column_stack((ratios, consumed[:, 6] / (1 + consumed[:, 6])))


def potential_output(
    capital, capacity_per_capital, productivity, paid_workers, inputs, recipes, reserve, extractive
):
    limits = np.divide(inputs, recipes, out=np.full_like(inputs, np.inf), where=recipes > 0)
    q = np.minimum(capital * capacity_per_capital, productivity * paid_workers)
    q = np.minimum(q, limits.min(axis=1))
    q = np.where(extractive, np.minimum(q, reserve), q)
    return np.maximum(0, q)


def revised_prices(prices, costs, sales, unfilled, inventory, cfg):
    scale = np.maximum(sales, 1.0)
    excess = np.maximum(0, inventory - cfg.inventory_target_weeks * sales)
    demand_signal = (unfilled - excess) / scale
    cost_gap = ((1 + cfg.target_markup) * costs - prices) / prices
    change = np.clip(
        cfg.price_demand_response * demand_signal + cfg.price_cost_response * cost_gap,
        -cfg.price_max_log_change,
        cfg.price_max_log_change,
    )
    return np.maximum(float(cfg.price_floor), prices * np.exp(change))
