from decimal import Decimal

import numpy as np
import pytest

from economic_sim.agents.firms import plan
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


def test_household_primary_shortfall_requests_rolling_credit(sim):
    plan(sim)
    person = int(sim.people.ids[0])
    home = sim.deposits[person].bank_id
    firm = next(int(x) for x in sim.firms.ids if sim.deposits[int(x)].bank_id == home)
    deposit = sim.deposits[person]
    cash = sim.ledger.available(deposit.asset)
    sim.settlement.transfer("test:reduce-household-cash", person, firm, cash - money(1), week=0)

    row = sim.people.id_to_row[person]
    primary_cost = money(
        sum(
            (
                Decimal(str(float(quantity))) * Decimal(str(float(price)))
                for quantity, price in zip(
                    sim.people.column("needs")[row, :3], sim.reference_prices[:3], strict=True
                )
            ),
            Decimal(0),
        )
    )
    expected_weekly_income = money(primary_cost / 2)
    expected = sim.people.column("expected_income").copy()
    expected[row] = float(expected_weekly_income)
    sim.people.replace_column("expected_income", expected)

    sim.finance.finance_plans()

    decision = sim.finance.processed_requests[f"primary:{sim.week}:{person}"]
    assert decision.status in {"approved", "partial"}
    assert decision.borrower_id == person
    assert decision.requested == money(primary_cost - money(1) - expected_weekly_income)
    assert sim.loans[decision.request_id].purpose == "primary_needs"
    assert sim.monetary_metrics()["household_credit"] == decision.granted
    assert sim.monetary_metrics()["business_credit"] == money(0)
    sim.ledger.validate(full=True)


def test_no_primary_credit_when_household_cash_covers_needs(sim):
    plan(sim)

    sim.finance.finance_plans()

    assert not any(key.startswith("primary:") for key in sim.finance.processed_requests)


def test_step_rollback_removes_new_household_loan(sim, monkeypatch):
    plan(sim)
    person = int(sim.people.ids[0])
    home = sim.deposits[person].bank_id
    firm = next(int(x) for x in sim.firms.ids if sim.deposits[int(x)].bank_id == home)
    deposit = sim.deposits[person]
    cash = sim.ledger.available(deposit.asset)
    sim.settlement.transfer("test:rollback-household-cash", person, firm, cash - money(1))

    row = sim.people.id_to_row[person]
    primary_cost = money(
        sum(
            (
                Decimal(str(float(quantity))) * Decimal(str(float(price)))
                for quantity, price in zip(
                    sim.people.column("needs")[row, :3], sim.reference_prices[:3], strict=True
                )
            ),
            Decimal(0),
        )
    )
    expected = sim.people.column("expected_income").copy()
    expected[row] = float(money(primary_cost / 2))
    sim.people.replace_column("expected_income", expected)
    balance_before = sim.ledger.balance(deposit.asset)
    finance_plans = sim.finance.finance_plans

    def fail_after_credit():
        finance_plans()
        assert f"primary:{sim.week}:{person}" in sim.finance.processed_requests
        raise RuntimeError("injected failure after household credit")

    monkeypatch.setattr(sim.finance, "finance_plans", fail_after_credit)
    with pytest.raises(RuntimeError, match="injected failure"):
        sim.step()

    assert sim.week == 0
    assert not sim.loans
    assert not sim.finance.processed_requests
    assert sim.ledger.balance(deposit.asset) == balance_before
    assert sim.settlement.loans is sim._loans
    sim.ledger.validate(full=True)


def test_credit_compares_other_banks_and_settles_reserves(sim):
    borrower = int(sim.people.ids[0])
    home = sim.deposits[borrower].bank_id
    home_reserves = sim.reserves[home]
    held = sim.ledger.available(home_reserves.asset)
    sim.ledger.reserve("test:hold-home-reserves", home_reserves.asset, held)
    alternatives = [int(x) for x in sim.banks.ids if int(x) != home]
    first_alternative = alternatives[0]
    first_reserves = sim.reserves[first_alternative]
    first_held = sim.ledger.available(first_reserves.asset)
    sim.ledger.reserve("test:hold-first-alternative", first_reserves.asset, first_held)
    lender = alternatives[1]
    lender_reserves = sim.reserves[lender]
    home_before = sim.ledger.balance(home_reserves.asset)
    lender_before = sim.ledger.balance(lender_reserves.asset)
    deposit_before = sim.ledger.balance(sim.deposits[borrower].asset)
    total_reserves_before = sum(
        (sim.ledger.balance(reserve.asset) for reserve in sim.reserves.values()), money(0)
    )

    decision = sim.finance.request_credit(
        "cross-bank-primary",
        borrower,
        money(100),
        annual_income=money(10_000),
        purpose="primary_needs",
    )

    assert decision.status == "approved"
    assert decision.bank_id == lender
    assert sim.ledger.balance(sim.deposits[borrower].asset) == deposit_before + money(100)
    assert sim.ledger.balance(home_reserves.asset) == home_before + money(100)
    assert sim.ledger.balance(lender_reserves.asset) == lender_before - money(100)
    assert (
        sum((sim.ledger.balance(reserve.asset) for reserve in sim.reserves.values()), money(0))
        == total_reserves_before
    )
    assert sim.loans[decision.request_id].purpose == "primary_needs"

    sim.week = 1
    sim.finance.policy = PolicyState(0, 0, 0)
    sim.finance.service()
    assert (
        sum((sim.ledger.balance(reserve.asset) for reserve in sim.reserves.values()), money(0))
        == total_reserves_before
    )
    assert sim.ledger.balance(f"{lender}:loan_interest") > money(0)
    sim.ledger.validate(full=True)

    sim.settlement.repay_loan(
        "repay:cross-bank-primary", decision.request_id, money(50), week=sim.week
    )
    assert (
        sum((sim.ledger.balance(reserve.asset) for reserve in sim.reserves.values()), money(0))
        == total_reserves_before
    )
    assert sim.ledger.balance(sim.loans[decision.request_id].debt_account) == money(50)
    sim.ledger.validate(full=True)


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
