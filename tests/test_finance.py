from decimal import Decimal

import numpy as np
import pytest

from economic_sim.config import load_config
from economic_sim.finance import PolicyState, default_probabilities, weekly_rate
from economic_sim.money import money
from economic_sim.simulation import Simulation


@pytest.fixture
def sim():
    return Simulation.from_config(load_config("configs/t03.yaml"))


def test_effective_annual_rate_conversion_accepts_zero_and_negative():
    assert weekly_rate(0) == Decimal("0.0")
    assert (Decimal(1) + weekly_rate(0.08)) ** 52 == pytest.approx(Decimal("1.08"))
    assert weekly_rate(-0.01) < 0
    with pytest.raises(ValueError):
        weekly_rate(-1)


def test_default_score_is_finite_for_zero_income_and_uses_annual_horizon():
    result = default_probabilities([0, 100, 100], [0, 100, 100], [0, 0, 2])
    assert np.isfinite(result).all()
    assert (result >= 0).all() and (result <= 1).all()
    assert result[2] > result[1]


def test_policy_corridor_and_future_application(sim):
    with pytest.raises(ValueError):
        PolicyState(0.03, 0.02, 0.04)
    old = sim.finance.loan_rate(0.02)
    sim.finance.schedule_policy(1, reserve_rate=0.01, policy_rate=0.04, emergency_rate=0.06)
    assert sim.finance.policy.policy_rate == 0.02
    sim.week = 1
    sim.finance.open_week()
    assert sim.finance.loan_rate(0.02) == pytest.approx(old + 0.02)


def test_origination_creates_deposit_not_reserves_and_is_idempotent(sim):
    borrower = int(sim.firms.ids[0])
    bank = sim.deposits[borrower].bank_id
    before_deposit = sim.agent(borrower).deposit
    before_reserves = sim.ledger.balance(sim.reserves[bank].asset)
    result = sim.finance.request_credit(
        "request-1", borrower, money(100), annual_income=money(10_000)
    )
    assert result.status in {"approved", "partial"}
    assert sim.agent(borrower).deposit == before_deposit + result.granted
    assert sim.ledger.balance(sim.reserves[bank].asset) == before_reserves
    duplicate = sim.finance.request_credit(
        "request-1", borrower, money(100), annual_income=money(10_000)
    )
    assert duplicate.status == "duplicate"
    assert len(sim.loans) == 1


def test_emergency_facility_preserves_equity_and_locks_collateral(sim):
    borrower = int(sim.firms.ids[0])
    bank = sim.deposits[borrower].bank_id
    decision = sim.finance.request_credit(
        "collateral-loan", borrower, money(1000), annual_income=money(100_000)
    )
    assert decision.granted > 0
    equity = sim.ledger.balance_sheets()[bank]["equity"]
    granted = sim.finance.refinance(bank, money(100))
    assert granted == money(100)
    assert sim.ledger.balance_sheets()[bank]["equity"] == equity
    facility = next(iter(sim.finance.cb_loans.values()))
    assert sim.ledger.available(facility.collateral_account) < sim.ledger.balance(
        facility.collateral_account
    )
    assert sim.finance.refinance(bank, money(10_000_000)) < money(10_000_000)


def test_rejection_reason_is_distinct_from_settlement_failure(sim):
    borrower = int(sim.people.ids[0])
    decision = sim.finance.request_credit(
        "no-income", borrower, money(10), annual_income=money(0), purpose="primary_needs"
    )
    assert decision.reason == "zero_income"
    assert sim.finance.rejections == {"zero_income": 1}
