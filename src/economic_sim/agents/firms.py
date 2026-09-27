"""Piani basati sulle informazioni disponibili prima del lavoro e degli scambi."""

import math
from decimal import Decimal

import numpy as np

from economic_sim.agents.decisions import revised_prices
from economic_sim.money import money, money_context


def resource_requirements(sim, row, output, *, replenish=False):
    firm = int(sim.firms.ids[row])
    product = sim.products[int(sim.firms.column("product_id")[row]) - 1]
    multiplier = sim.config.real_economy.input_target_weeks if replenish else 1.0
    return {
        sim.product_by_name[name].id: max(
            0.0,
            coefficient * output * multiplier
            - sim.physical.available(firm, sim.product_by_name[name].id),
        )
        for name, coefficient in product.recipe.items()
    }


def plan(sim):
    f, cfg = sim.firms, sim.config.real_economy
    products = f.column("product_id")
    inventory = np.array(
        [sim.physical.quantity(int(i), int(p)) for i, p in zip(f.ids, products, strict=True)]
    )
    if sim.week > 1:
        prices = revised_prices(
            f.column("offered_price"),
            f.column("observed_unit_cost"),
            f.column("previous_sales"),
            f.column("previous_unfilled"),
            inventory,
            cfg,
        )
        f.replace_column("offered_price", [float(money(str(p))) for p in prices])
        vacancy = f.column("previous_vacancies")
        applicants = f.column("previous_applications")
        slots = np.maximum(1, f.column("planned_workers"))
        pressure = (vacancy - np.maximum(0, applicants - slots)) / slots
        margin = (f.column("offered_price") - f.column("observed_unit_cost")) / np.maximum(
            f.column("offered_price"), float(cfg.price_floor)
        )
        changes = np.clip(
            cfg.wage_response * (pressure + 0.1 * margin),
            -cfg.wage_max_log_change,
            cfg.wage_max_log_change,
        )
        f.replace_column(
            "offered_wage",
            [
                float(money(str(x)))
                for x in np.maximum(
                    float(cfg.wage_floor), f.column("offered_wage") * np.exp(changes)
                )
            ],
        )
    sim.reference_prices = np.array(
        [np.mean(f.column("offered_price")[products == p.id]) for p in sim.products]
    )
    targets = np.zeros(len(f.ids))
    workers = np.zeros(len(f.ids), dtype=np.int64)
    productivity = f.column("productivity")
    for row, entity in enumerate(f.ids):
        if not f.column("active")[row]:
            continue
        product = sim.products[int(products[row]) - 1]
        capacity = (
            sim.physical.quantity(int(entity), 11, "installed_capital")
            * product.capacity_per_capital
        )
        if sim.week == 1:
            desired = min(capacity, productivity[row] * f.column("planned_workers")[row])
        else:
            demand = f.column("previous_orders")[row]
            desired = max(0, demand * (1 + cfg.inventory_target_weeks) - inventory[row])
        desired = min(desired, capacity)
        if product.kind == "resource":
            desired = min(
                desired, sim.physical.quantity(int(entity), product.id, "natural_reserve")
            )
        targets[row] = desired
        if product.kind == "resource":
            # Non si assume energia futura: le estrattive usano solo scorte già disponibili.
            for name, coefficient in product.recipe.items():
                desired = min(
                    desired,
                    sim.physical.available(int(entity), sim.product_by_name[name].id) / coefficient,
                )
        workers[row] = math.ceil(desired / productivity[row])
    f.replace_column("planned_workers", workers)
    sim.production_targets = targets


@money_context
def affordable_jobs(sim, row, wages):
    """Riduce i posti finché salari contrattuali e input minimi sono prefinanziati."""
    firm = int(sim.firms.ids[row])
    cash = sim.ledger.available(sim.deposits[firm].asset)
    productivity = sim.firms.column("productivity")[row]
    product = sim.products[int(sim.firms.column("product_id")[row]) - 1]
    wages = list(wages)
    while wages:
        output = min(sim.production_targets[row], len(wages) * productivity)
        requirements = {} if product.kind == "resource" else resource_requirements(sim, row, output)
        inputs = sum(
            (
                money(Decimal(str(q)) * Decimal(str(sim.reference_prices[p - 1])))
                for p, q in requirements.items()
            ),
            money(0),
        )
        if sum(wages, money(0)) + inputs <= cash:
            break
        wages.pop()
    return len(wages)
