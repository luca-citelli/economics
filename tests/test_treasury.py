from decimal import Decimal

import pytest

from economic_sim.config import Config, load_config
from economic_sim.money import ZERO, money
from economic_sim.simulation import Simulation
from economic_sim.treasury import BondBid, clear_bond_auction, price_from_yield


@pytest.fixture
def fiscal_sim():
    data = load_config("configs/t04.yaml").model_dump()
    data["simulation"].update(initial_population=100, companies_per_product=2)
    return Simulation.from_config(Config.model_validate(data))


def test_uniform_auction_marginal_ties_and_budgets():
    bids = [
        BondBid(1, 5, money("0.99"), money("4.95")),
        BondBid(2, 6, money("0.95"), money("5.70")),
        BondBid(3, 6, money("0.95"), money("5.70")),
        BondBid(4, 100, money("0.80"), money("80")),
    ]
    price, allocation, unsold = clear_bond_auction(10, bids, money("0.90"))
    assert price == money("0.95")
    assert allocation == {1: 5, 2: 3, 3: 2}
    assert unsold == 0
    assert sum(allocation.values()) * price == money("9.50")
    assert clear_bond_auction(20, bids, money("0.90")) == (money("0.95"), {1: 5, 2: 6, 3: 6}, 3)
    assert clear_bond_auction(10, bids, money("1.00")) == (None, {}, 10)
    assert clear_bond_auction(10, [], money("0.90")) == (None, {}, 10)
    assert clear_bond_auction(10, [BondBid(5, 10, money("0.90"), money("2"))], money("0.90")) == (
        money("0.90"),
        {5: 2},
        8,
    )
    with pytest.raises(ValueError):
        clear_bond_auction(1, [bids[0], bids[0]], money("0.90"))


def test_central_bank_primary_purchase_creates_treasury_without_duplicate_reserves(fiscal_sim):
    sim = fiscal_sim
    cb = sim.central_bank.id
    before_treasury = sim.treasury.available()
    before_reserves = sim.monetary_metrics()["bank_reserves"]
    before_cb_equity = sim.ledger.balance_sheets()[cb]["equity"]
    price, allocations, unsold = sim.treasury.auction(
        10, [BondBid(cb, 10, money("0.95"), money("9.50"))]
    )
    assert (price, allocations, unsold) == (money("0.95"), {cb: 10}, 0)
    assert sim.treasury.available() == before_treasury + money("9.50")
    assert sim.monetary_metrics()["bank_reserves"] == before_reserves
    assert sim.ledger.balance_sheets()[cb]["equity"] == before_cb_equity
    sim.validate()


def test_private_required_yield_uses_adaptive_policy_risk_and_concentration(fiscal_sim):
    sim = fiscal_sim
    person = int(sim.people.ids[0])
    treasury = sim.treasury
    base = treasury.required_yield(person, debt=100, held=0)
    assert treasury.required_yield(person, debt=10_000, held=0) > base
    assert treasury.required_yield(person, debt=100, held=50) > base
    sim.finance.schedule_policy(1, reserve_rate=0.01, policy_rate=0.04, emergency_rate=0.06)
    sim.step()
    assert treasury.expected_policy_rate == pytest.approx(0.024)


def test_one_time_central_bank_order_expires_without_issuance(fiscal_sim):
    sim = fiscal_sim
    sim.treasury.schedule_cb_order(1, money("100"), money("0.95"))
    sim.week = 1
    sim.treasury.run()
    assert sim.treasury.pending_cb_orders == {}
    assert sim.treasury.flows["bonds_issued"] == ZERO
    sim.validate()


def test_public_purchases_and_tax_timing(fiscal_sim):
    sim = fiscal_sim
    first = sim.step()
    assert first["government_consumption"] > ZERO
    assert first["labor_tax"] == first["wages_gross"] - first["wages_net"]
    assert all(week == 2 for week, _ in sim.treasury.tax_due.values())
    accrued = sum((amount for _, amount in sim.treasury.tax_due.values()), ZERO)
    assert accrued > ZERO
    assert sim.ledger.balance_sheets()[sim.government.id]["difference"] == ZERO
    second = sim.step()
    assert second["profit_tax"] > ZERO
    assert second["tax"] >= second["profit_tax"]
    assert second["gdp_discrepancy"] == ZERO
    sim.validate()


def test_discount_amortizes_to_face_and_matures_after_52_weeks(fiscal_sim):
    sim = fiscal_sim
    cb = sim.central_bank.id
    sim.treasury.auction(10, [BondBid(cb, 10, money("0.90"), money("9"))])
    bond = sim.bonds["bond:0:1"]
    assert sim.ledger.balance(bond.asset_account) == money("9")
    for week in range(1, 53):
        sim.week = week
        sim.treasury.accrue_bonds()
        assert sim.ledger.balance(bond.asset_account) <= bond.face_value
    assert sim.ledger.balance(bond.asset_account) == money("10")
    assert sim.ledger.balance(bond.liability_account) == money("10")
    assert price_from_yield(0.25) == money(Decimal(1) / Decimal("1.25"))
    sim.validate()


def test_premium_amortizes_down_to_face(fiscal_sim):
    sim = fiscal_sim
    cb = sim.central_bank.id
    sim.treasury.auction(10, [BondBid(cb, 10, money("1.02"), money("10.20"))])
    bond = sim.bonds["bond:0:1"]
    assert sim.ledger.balance(bond.asset_account) == money("10.20")
    for week in range(1, 53):
        sim.week = week
        sim.treasury.accrue_bonds()
    assert sim.ledger.balance(bond.asset_account) == money("10")
    sim.validate()


def test_pledged_bond_redemption_moves_hold_to_proceeds(fiscal_sim):
    sim = fiscal_sim
    bank = int(sim.banks.ids[0])
    sim.treasury.auction(100, [BondBid(bank, 100, money("0.95"), money("95"))])
    bond = sim.bonds[f"bond:0:{bank}"]
    assert sim.finance.refinance(bank, money("10")) == money("10")
    loan_id, facility = next(iter(sim.finance.cb_loans.items()))
    assert facility.collateral_account == bond.asset_account
    sim.week = 52
    sim.treasury.accrue_bonds()
    sim.treasury.run()
    assert sim.status == "PAUSED"
    assert sim.ledger.balance(bond.asset_account) == ZERO
    assert sim.finance.cb_loans[loan_id].collateral_account == sim.reserves[bank].asset
    assert f"collateral:{loan_id}" in sim.ledger.holds
    sim.validate()


def test_unfunded_maturity_terminates_without_negative_treasury(fiscal_sim):
    sim = fiscal_sim
    sim.week = 52
    sim.treasury.auction = lambda offered: (None, {}, offered)
    before = sim.treasury.available()
    sim.treasury.run()
    assert sim.status == "TERMINATED"
    assert sim.treasury.default_arrears > ZERO
    assert sim.treasury.available() == before
    assert any(e.startswith("sovereign_default") for e in sim.events)
    sim.validate()


def test_default_arrears_include_all_unpaid_maturities(fiscal_sim):
    data = fiscal_sim.config.model_dump()
    data["government"]["initial_treasury_per_person"] = "0"
    sim = Simulation.from_config(Config.model_validate(data))
    cb = sim.central_bank.id
    sim.treasury.auction(10, [BondBid(cb, 10, money("0.95"), money("9.50"))])
    expected = sum((bond.face_value for bond in sim.bonds.values()), ZERO)
    sim.week = 52
    sim.treasury.auction = lambda offered: (None, {}, offered)
    sim.treasury.run()
    assert sim.status == "TERMINATED"
    assert sim.treasury.default_arrears == expected
    sim.validate()


def test_integrated_issue_spending_taxes_and_redemption(fiscal_sim):
    sim = fiscal_sim
    for _ in range(53):
        sim.step()
        assert sim.status == "PAUSED"
    maturity = sim.history[51]
    assert maturity["bond_repaid"] > ZERO
    assert maturity["bond_proceeds"] > ZERO
    assert maturity["sovereign_arrears"] == ZERO
    assert maturity["gdp_discrepancy"] == ZERO
    assert sim.history[0]["government_consumption"] > ZERO
    assert sim.history[1]["profit_tax"] > ZERO
    assert sim.history[52]["public_debt_carrying"] > maturity["public_debt_carrying"]
    sim.validate()


def test_fiscal_step_rollback_restores_taxes_and_ledger(fiscal_sim, monkeypatch):
    sim = fiscal_sim
    before = sim.economic_checksum()

    def fail(_sim):
        raise RuntimeError("injected after payroll")

    monkeypatch.setattr("economic_sim.simulation.consume_households", fail)
    with pytest.raises(RuntimeError, match="injected"):
        sim.step()
    assert sim.status == "ERROR"
    assert sim.week == 0
    assert sim.economic_checksum() == before
    assert sim.treasury.flows["labor_tax"] == ZERO
    sim.validate()


def test_full_step_reports_sovereign_default_as_termination(fiscal_sim):
    data = fiscal_sim.config.model_dump()
    data["central_bank"].update(
        primary_bond_purchases_enabled=False, weekly_bond_purchase_budget="0"
    )
    data["government"].update(household_bond_budget_share=0, bank_bond_budget_share=0)
    sim = Simulation.from_config(Config.model_validate(data))
    for _ in range(52):
        sim.step()
        if sim.status == "TERMINATED":
            break
    assert sim.week == 52
    assert sim.status == sim.snapshot().status == "TERMINATED"
    assert sim.history[-1]["bond_unsold"] > ZERO
    assert sim.history[-1]["sovereign_arrears"] > ZERO
    assert sim.last_error is None
    assert sim.ledger.balance(f"{sim.government.id}:treasury") >= ZERO
    sim.validate()
