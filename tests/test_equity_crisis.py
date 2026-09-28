import numpy as np
import pytest

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.config import Config, load_config
from economic_sim.equity import EquityBid, EquityOffer
from economic_sim.money import ZERO, money
from economic_sim.simulation import Simulation


@pytest.fixture
def complete_sim():
    data = load_config("configs/t05.yaml").model_dump()
    data["simulation"].update(initial_population=100, companies_per_product=2)
    return Simulation.from_config(Config.model_validate(data))


def _bank_loss(sim, bank, desired_equity):
    current = sim.ledger.balance_sheets()[bank]["equity"]
    amount = current - desired_equity
    reserve = sim.reserves[bank]
    expense = Account(f"{bank}:test_loss", bank, AccountKind.EXPENSE, "test_loss")
    income = Account(
        f"{sim.central_bank.id}:test_gain", sim.central_bank.id, AccountKind.INCOME, "test_gain"
    )
    sim.ledger.post(
        Transaction(
            f"test-loss:{bank}",
            sim.week,
            "crisis",
            "Perdita costruita",
            (
                change(sim.ledger.accounts[reserve.asset], -amount),
                change(expense, amount),
                change(sim.ledger.accounts[reserve.liability], -amount),
                change(income, amount),
            ),
        ),
        new_accounts=(expense, income),
    )


def test_equity_minimum_raise_cancels_and_releases_all_funds(complete_sim):
    sim = complete_sim
    sim.week = 1
    issuer = int(sim.firms.ids[0])
    buyers = list(map(int, sim.people.ids[:2]))
    offer = EquityOffer(issuer, money(10), money(2), money(25))
    bids = [EquityBid(buyer, money(5), money(2), money(10), 0.08) for buyer in buyers]
    before = sim.economic_checksum()
    result = sim.equity.auction(offer, bids)
    assert result["reason"] == "minimum_raise"
    assert not sim.ledger.holds
    assert sim.economic_checksum() != before  # solo evento/risultato, nessuna scrittura
    assert all(not tx.id.startswith("equity:") for tx in sim.ledger.journal)
    sim.validate()


def test_equity_auction_dilution_and_cross_bank_payment(complete_sim):
    sim = complete_sim
    sim.week = 1
    issuer = int(sim.firms.ids[0])
    buyers = list(map(int, sim.people.ids[:2]))
    issue_id = f"shares:{issuer}"
    old = sim.share_issues[issue_id].total_shares
    reserves = sim.monetary_metrics()["bank_reserves"]
    offer = EquityOffer(issuer, money(10), money(2), money(15))
    bids = [EquityBid(buyer, money(5), money(2), money(10), 0.08) for buyer in buyers]
    result = sim.equity.auction(offer, bids)
    assert result["proceeds"] == money(20)
    assert result["price"] == money(2)
    assert sim.share_issues[issue_id].total_shares == old + money(10)
    assert sum(
        (h.quantity for h in sim.share_holdings if h.issue_id == issue_id), ZERO
    ) == old + money(10)
    assert sim.monetary_metrics()["bank_reserves"] == reserves
    assert not sim.ledger.holds
    sim.validate()


def test_equity_tie_is_pro_rata_at_marginal_price(complete_sim):
    sim = complete_sim
    sim.week = 1
    issuer = int(sim.firms.ids[0])
    buyers = list(map(int, sim.people.ids[:2]))
    result = sim.equity.auction(
        EquityOffer(issuer, money(5), money(2), ZERO),
        [EquityBid(buyer, money(5), money(2), money(10), 0.08) for buyer in buyers],
    )
    assert result["allocated"] == {buyers[0]: money("2.5"), buyers[1]: money("2.5")}
    assert result["price"] == money(2)
    assert result["proceeds"] == money(10)
    sim.validate()


def test_bank_resolution_numeric_case_and_no_reserve_creation(complete_sim):
    sim = complete_sim
    bank = int(sim.banks.ids[0])
    _bank_loss(sim, bank, money(-20))
    opening_profit = sim.treasury.profit_snapshot()
    before = sim.monetary_metrics()["bank_reserves"]
    deposits = {
        owner: sim.ledger.balance(dep.asset)
        for owner, dep in sim.deposits.items()
        if dep.bank_id == bank
    }
    assert sim.crisis.resolve_bank(bank, money(10))
    assert sim.ledger.balance_sheets()[bank]["equity"] == money(10)
    assert sim.crisis.flows["deposit_haircuts"] == money(20)
    assert sum(
        (deposits[owner] - sim.ledger.balance(sim.deposits[owner].asset) for owner in deposits),
        ZERO,
    ) == money(30)
    assert sim.ledger.balance(sim.share_issues[f"shares:{bank}"].capital_account) == money(10)
    assert sim.monetary_metrics()["bank_reserves"] == before
    sim.treasury.accrue_profit_tax(opening_profit)
    assert bank not in sim.treasury.tax_due
    sim.validate()


def test_bank_resolution_keeps_customer_loans(complete_sim):
    sim = complete_sim
    bank = int(sim.banks.ids[0])
    borrower = next(owner for owner, dep in sim.deposits.items() if dep.bank_id == bank)
    loan = sim.settlement.originate_loan("test-surviving-loan", borrower, bank, money(100), 0.04)
    _bank_loss(sim, bank, money(-20))
    assert sim.crisis.resolve_bank(bank, money(10))
    assert sim.ledger.balance(loan.asset_account) == money(100)
    assert sim.ledger.balance(loan.debt_account) == money(100)
    assert sim.loans[loan.id].status == "performing"
    sim.validate()


def test_arrears_paid_before_close_do_not_advance_default_counter(complete_sim):
    sim = complete_sim
    sim.week = 1
    borrower = int(sim.people.ids[0])
    bank = sim.deposits[borrower].bank_id
    loan = sim.settlement.originate_loan("test-arrears-cure", borrower, bank, money(100), 0.04)
    sim._loans[loan.id] = loan.model_copy(
        update={"arrears": money(7), "arrears_weeks": 3, "status": "arrears"}
    )
    sim.crisis.run()
    assert sim.loans[loan.id].arrears == ZERO
    assert sim.loans[loan.id].arrears_weeks == 0
    assert borrower not in sim.crisis.liquidations
    sim.validate()


def test_dividend_follows_real_profit_and_debit_of_firm_cash(complete_sim):
    sim = complete_sim
    sim.week = 1
    firm = int(sim.firms.ids[0])
    owner = next(h.owner_id for h in sim.share_holdings if h.issue_id == f"shares:{firm}")
    payer = next(int(p) for p in sim.people.ids if int(p) != owner)
    planned = sim.firms.column("planned_workers").copy()
    planned[sim.firms.id_to_row[firm]] = 0
    sim.firms.replace_column("planned_workers", planned)
    opening = sim.treasury.profit_snapshot()
    sim.settlement.transfer("test-profit-transfer", payer, firm, money(100), week=1)
    before_cash = sim.ledger.balance(sim.deposits[firm].asset)
    sim.equity.distribute(opening)
    assert sim.equity.flows["dividends"] == money(20)
    assert sim.ledger.balance(sim.deposits[firm].asset) == before_cash - money(20)
    assert sim.ledger.balance(f"{owner}:dividends") == money(20)
    sim.validate()


def test_insufficient_deposits_leave_resolution_unfunded(complete_sim):
    sim = complete_sim
    bank = int(sim.banks.ids[0])
    _bank_loss(sim, bank, money(-20))
    convertible = sum(
        (sim.ledger.available(dep.asset) for dep in sim.deposits.values() if dep.bank_id == bank),
        ZERO,
    )
    before = sim.economic_checksum()
    assert not sim.crisis.resolve_bank(bank, convertible + money(30))
    assert sim.status == "TERMINATED"
    assert sim.ledger.balance_sheets()[bank]["equity"] == money(-20)
    assert sim.economic_checksum() == before  # evento controllato, bilanci invariati
    sim.validate()


def test_firm_liquidation_without_buyer_has_no_cash_recovery(complete_sim):
    sim = complete_sim
    sim.week = 1
    firm = int(sim.firms.ids[0])
    before = sim.ledger.balance(sim.deposits[firm].asset)
    total_before = sim.monetary_metrics()["private_deposits"]
    sim.crisis.start_liquidation(firm)
    sim.crisis._close_liquidation(firm)
    assert sim.crisis.flows["liquidation_recoveries"] == ZERO
    assert sim.ledger.balance(sim.deposits[firm].asset) == ZERO
    assert sim.monetary_metrics()["private_deposits"] == total_before
    assert before > ZERO
    assert sim.share_issues[f"shares:{firm}"].total_shares == ZERO
    assert all(sim.physical.quantity(firm, p) == 0 for p in range(1, 12))
    sim.validate()


def test_installed_capital_liquidation_requires_real_buyer_payment(complete_sim):
    sim = complete_sim
    sim.week = 1
    seller, buyer = map(int, sim.firms.ids[:2])
    sim.reference_prices = np.array([float(p.opening_price) for p in sim.products])
    sim.investment_targets = np.zeros(len(sim.firms.ids))
    sim.investment_targets[sim.firms.id_to_row[buyer]] = 1.0
    sim.production_targets = np.zeros(len(sim.firms.ids))
    old_seller_capital = sim.physical.quantity(seller, 11, "installed_capital")
    old_buyer_pending = sim.physical.quantity(buyer, 11, "pending_capital")
    old_cash = sim.ledger.balance(sim.deposits[seller].asset)
    sim.crisis.start_liquidation(seller)
    sim.crisis._liquidate_assets(seller)
    assert sim.physical.quantity(seller, 11, "installed_capital") == old_seller_capital - 1
    assert sim.physical.quantity(buyer, 11, "pending_capital") == old_buyer_pending + 1
    assert sim.ledger.balance(sim.deposits[seller].asset) > old_cash
    assert sim.crisis.flows["liquidation_capital_investment"] == ZERO
    sim.validate()


def test_unsecured_creditors_share_realized_cash_pro_rata(complete_sim):
    sim = complete_sim
    sim.week = 1
    firm = int(sim.firms.ids[0])
    banks = list(map(int, sim.banks.ids[:2]))
    loans = [
        sim.settlement.originate_loan(f"test-pro-rata-{i}", firm, bank, money(100), 0.04, week=1)
        for i, bank in enumerate(banks)
    ]
    cash = sim.ledger.balance(sim.deposits[firm].asset)
    person = int(sim.people.ids[0])
    sim.settlement.transfer("test-drain-cash", firm, person, cash - money(100), week=1)
    sim.crisis.start_liquidation(firm)
    sim.crisis._close_liquidation(firm)
    assert sim.crisis.flows["liquidation_recoveries"] == money(100)
    assert all(loan.status == "written_down" for loan in sim.loans.values())
    assert all(sim.ledger.balance(loan.asset_account) == ZERO for loan in loans)
    assert sim.crisis.flows["loan_writeoffs"] == money(100)
    sim.validate()


def test_liquidated_firm_transfers_bank_shares_in_kind_to_creditor(complete_sim):
    sim = complete_sim
    sim.week = 1
    firm = int(sim.firms.ids[0])
    home = sim.deposits[firm].bank_id
    lender = next(int(bank) for bank in sim.banks.ids if int(bank) != home)
    _bank_loss(sim, home, money(-20))
    assert sim.crisis.resolve_bank(home, money(10))
    issue_id = f"shares:{home}"
    assert (
        next(
            h.quantity for h in sim.share_holdings if h.owner_id == firm and h.issue_id == issue_id
        )
        > ZERO
    )
    loan = sim.settlement.originate_loan(
        "test-in-kind-loan", firm, lender, money(100), 0.04, week=1
    )
    recipient = next(int(p) for p in sim.people.ids if sim.deposits[int(p)].bank_id == home)
    sim.settlement.transfer(
        "test-in-kind-drain", firm, recipient, sim.ledger.balance(sim.deposits[firm].asset), week=1
    )
    sim.crisis.start_liquidation(firm)
    sim.crisis._close_liquidation(firm)
    assert (
        next(
            h.quantity for h in sim.share_holdings if h.owner_id == firm and h.issue_id == issue_id
        )
        == ZERO
    )
    assert (
        next(
            h.quantity
            for h in sim.share_holdings
            if h.owner_id == lender and h.issue_id == issue_id
        )
        > ZERO
    )
    assert sim.loans[loan.id].status == "written_down"
    assert any(event.startswith("in_kind_share_transfer") for event in sim.events)
    sim.validate()


def test_repeat_resolution_accounts_for_bank_own_shares(complete_sim):
    sim = complete_sim
    sim.week = 1
    firm = int(sim.firms.ids[0])
    bank = sim.deposits[firm].bank_id
    _bank_loss(sim, bank, money(-20))
    assert sim.crisis.resolve_bank(bank, money(10))
    sim.settlement.originate_loan("test-own-share-loan", firm, bank, money(100), 0.04, week=1)
    recipient = next(int(p) for p in sim.people.ids if sim.deposits[int(p)].bank_id == bank)
    sim.settlement.transfer(
        "test-own-share-drain",
        firm,
        recipient,
        sim.ledger.balance(sim.deposits[firm].asset),
        week=1,
    )
    sim.crisis.start_liquidation(firm)
    sim.crisis._close_liquidation(firm)
    assert sim.crisis.own_share_value(bank) > ZERO
    assert sim.ledger.balance_sheets()[bank]["equity"] - sim.crisis.own_share_value(bank) < ZERO
    sim.week = 2
    sim.crisis.open_week()
    assert sim.crisis.resolve_bank(bank, money(10))
    assert sim.ledger.balance_sheets()[bank]["equity"] == money(10)
    assert sim.crisis.own_share_value(bank) == ZERO
    sim.validate()


def test_integrated_profile_executes_all_phases(complete_sim):
    sim = complete_sim
    result = sim.step()
    assert "crisis" in sim.phase_trace
    assert "distributions" in sim.phase_trace
    assert result["gdp_discrepancy"] == ZERO
    assert len(sim.market_results) == 11
    sim.validate()


def test_scenario_equity_proceeds_buy_capital_effective_next_week():
    sim = Simulation.from_config(load_config("configs/t05-investment.yaml"))
    for _ in range(3):
        sim.step()
    assert sim.metrics()["equity_proceeds"] > ZERO
    candidates = [
        firm
        for firm in sim.equity.last_results
        if sim.physical.quantity(firm, 11, "pending_capital") > 0
    ]
    assert candidates
    firm = candidates[0]
    row = sim.firms.id_to_row[firm]
    old_installed = sim.physical.quantity(firm, 11, "installed_capital")
    pending = sim.physical.quantity(firm, 11, "pending_capital")
    product = sim.products[int(sim.firms.column("product_id")[row]) - 1]
    sim.step()
    assert sim.opening_capacity[row] == pytest.approx(
        (old_installed + pending) * product.capacity_per_capital
    )
    sim.validate()


def test_crisis_phase_error_restores_equity_and_crisis_state(complete_sim, monkeypatch):
    sim = complete_sim
    before = sim.economic_checksum()

    def fail():
        raise RuntimeError("errore costruito nella crisi")

    monkeypatch.setattr(sim.crisis, "run", fail)
    with pytest.raises(RuntimeError):
        sim.step()
    assert sim.status == "ERROR"
    assert sim.economic_checksum() == before
    sim.validate()
