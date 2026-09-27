import math

import numpy as np
import pytest

from economic_sim.agents.decisions import (
    consumption_budgets,
    potential_output,
    revised_prices,
    satisfaction,
)


@pytest.mark.parametrize("size", [1, 257, 5000])
def test_batch_needs_and_satisfaction_match_scalar(size):
    rng = np.random.default_rng(73)
    needs = rng.uniform(0, 10, (size, 11))
    needs[0, :6] = 0
    consumed = rng.uniform(0, 10, (size, 7))
    prices = rng.uniform(1, 10, 11)
    free, income = rng.uniform(0, 200, (2, size))
    saving = rng.uniform(0, 1, size)
    state = rng.bit_generator.state
    actual = consumption_budgets(needs, prices, free, income, saving, 2, 0.05)
    expected = np.zeros((size, 7))
    ratios = np.zeros((size, 7))
    for r in range(size):
        costs = [needs[r, p] * prices[p] for p in range(6)]
        primaries = sum(costs[:3])
        primary_budget = min(free[r], primaries)
        target_saving = income[r] * saving[r]
        buffer = 2 * primaries * (1 + saving[r])
        surplus_income = max(0, income[r] - target_saving - primary_budget)
        surplus_wealth = 0.05 * max(0, free[r] - income[r] - buffer - target_saving)
        discretionary = min(free[r] - primary_budget, surplus_income + surplus_wealth)
        secondaries = sum(costs[3:])
        secondary_budget = min(discretionary, secondaries)
        for p in range(3):
            expected[r, p] = primary_budget * costs[p] / primaries if primaries else 0
            expected[r, p + 3] = secondary_budget * costs[p + 3] / secondaries if secondaries else 0
        expected[r, 6] = discretionary - secondary_budget
        for p in range(6):
            ratios[r, p] = min(1, consumed[r, p] / needs[r, p]) if needs[r, p] else 1
        ratios[r, 6] = consumed[r, 6] / (1 + consumed[r, 6])
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(satisfaction(consumed, needs), ratios, rtol=1e-12, atol=1e-9)
    assert (actual.sum(axis=1) <= free + 1e-9).all()
    assert rng.bit_generator.state == state


@pytest.mark.parametrize("size", [1, 257, 5000])
def test_batch_output_matches_scalar_physical_limits(size):
    rng = np.random.default_rng(6)
    capital, capacity, productivity, workers, reserve = rng.uniform(0, 100, (5, size))
    recipes = rng.uniform(0, 2, (size, 3))
    recipes[rng.random((size, 3)) < 0.5] = 0
    inputs = rng.uniform(0, 100, (size, 3))
    extractive = rng.random(size) > 0.5
    workers[0] = 0
    result = potential_output(
        capital, capacity, productivity, workers, inputs, recipes, reserve, extractive
    )
    expected = []
    for row in range(size):
        limits = [capital[row] * capacity[row], productivity[row] * workers[row]]
        limits += [inputs[row, c] / recipes[row, c] for c in range(3) if recipes[row, c] > 0]
        if extractive[row]:
            limits.append(reserve[row])
        expected.append(max(0, min(limits)))
    np.testing.assert_allclose(result, expected, atol=1e-9, rtol=1e-12)
    assert result[0] == 0


def test_primary_budget_proportional_and_savings_separate():
    needs = np.array([[10, 5, 3, 2, 2, 2, 0, 0, 0, 0, 0]], dtype=float)
    prices = np.array([2, 3, 4, 10, 10, 10, 100, 1, 1, 1, 1], dtype=float)
    budget = consumption_budgets(
        needs, prices, np.array([23.5]), np.array([0.0]), np.array([0.5]), 2, 0.05
    )
    np.testing.assert_array_equal(budget[0], [10, 7.5, 6, 0, 0, 0, 0])
    # Patrimonio sopra il buffer consumabile soltanto quando il parametro lo consente.
    no_drawdown = consumption_budgets(
        needs, prices, np.array([1000.0]), np.array([0.0]), np.array([0.5]), 2, 0
    )
    assert no_drawdown[0, 3:].sum() == 0
    drawdown = consumption_budgets(
        needs, prices, np.array([1000.0]), np.array([0.0]), np.array([0.5]), 2, 1
    )
    assert drawdown[0, 3:6].sum() == 60
    assert drawdown[0, 6] > 0


def test_prices_unchanged_bounded_and_may_be_below_cost(real_config):
    cfg = real_config.real_economy.model_copy(update={"target_markup": 0.0})
    prices = np.array([10.0, 10.0, 10.0])
    result = revised_prices(
        prices,
        np.array([10.0, 1000.0, 10.0]),
        np.ones(3),
        np.array([0.0, 1000.0, 0.0]),
        np.array([0.0, 0.0, 1000.0]),
        cfg,
    )
    assert result[0] == 10
    assert result[1] == pytest.approx(10 * math.exp(cfg.price_max_log_change))
    assert result[1] < 1000
    assert result[2] == pytest.approx(10 * math.exp(-cfg.price_max_log_change))
