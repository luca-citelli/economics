from decimal import Decimal

import numpy as np
import pytest

from economic_sim import Simulation
from economic_sim.accounting.ledger import AccountingError, AccountKind
from economic_sim.config import Config
from economic_sim.money import ZERO, money
from economic_sim.serialization import canonical_json


def test_opening_accounts_and_ownership(sim):
    sim.validate()
    assert len(sim.people.ids) == 1000
    assert len(sim.firms.ids) == 33
    assert sim.firms.column("extractive").sum() == 9
    assert len(sim.banks.ids) == 3
    assert len(sim.share_issues) == len(sim.share_holdings) == 36
    assert sim.week == 0
    assert len(sim.ledger.journal) == 1
    assert all(
        a.kind not in (AccountKind.INCOME, AccountKind.EXPENSE)
        for a in sim.ledger.accounts.values()
    )
    m = sim.metrics()
    assert m["private_credit"] == ZERO
    assert m["treasury_balance"] == money(100000)
    assert m["bank_reserves"] == m["private_deposits"] + money(150000)
    assert m["public_debt_face"] == m["public_debt_carrying"]
    assert m["public_debt_face"] == m["bank_reserves"] + m["treasury_balance"]
    assert m["central_bank_liabilities"] == m["public_debt_face"]
    sheets = sim.ledger.balance_sheets()
    assert sheets[sim.government.id]["equity"] == -m["bank_reserves"]
    assert sheets[sim.central_bank.id]["equity"] == ZERO
    assert all(s["difference"] == ZERO for s in sheets.values())
    # Ogni detenzione ha sia il capitale sottoscritto sia un proprietario reale.
    for h in sim.share_holdings:
        issue = sim.share_issues[h.issue_id]
        assert h.owner_id in sim.people.id_to_row
        assert h.quantity == issue.total_shares
        assert sim.ledger.balance(h.asset_account) == sim.ledger.balance(issue.capital_account)
    assert not hasattr(sim, "step")


def test_initial_costs_reconcile_with_physical_stocks(sim):
    costs = {p.id: p.opening_unit_cost for p in sim.config.catalog.products}
    for firm in sim.firms.ids:
        for product in range(1, 12):
            quantity = sim.physical.quantity(int(firm), product)
            assert sim.ledger.balance(f"{firm}:inventory:{product}") == money(
                Decimal(str(quantity)) * costs[product]
            )
        capital = sim.physical.quantity(int(firm), 11, "installed_capital")
        assert sim.ledger.balance(f"{firm}:installed_capital") == money(
            Decimal(str(capital)) * costs[11]
        )


def test_same_seed_speed_and_catalog_order_do_not_change_economy(config, sim):
    other = Simulation.from_config(config)
    assert other.run_id != sim.run_id
    assert other.economic_checksum() == sim.economic_checksum()
    data = config.model_dump()
    data["runtime"]["default_steps_per_second"] = 10.0
    data["catalog"]["products"].reverse()
    assert (
        Simulation.from_config(Config.model_validate(data)).economic_checksum()
        == sim.economic_checksum()
    )


@pytest.mark.parametrize("seed", [1, 7, 99])
def test_seed_variation_remains_balanced(config, seed):
    data = config.model_dump()
    data["simulation"]["seed"] = seed
    a = Simulation.from_config(Config.model_validate(data))
    data["simulation"]["seed"] = seed + 1
    b = Simulation.from_config(Config.model_validate(data))
    assert not np.array_equal(a.people.column("needs"), b.people.column("needs"))
    assert a.economic_checksum() != b.economic_checksum()
    a.validate()
    b.validate()


@pytest.mark.parametrize("population,banks,companies", [(100, 2, 1), (123, 4, 2), (2000, 5, 4)])
def test_scaled_initialization(config, population, banks, companies):
    data = config.model_dump()
    data["simulation"].update(
        initial_population=population, initial_banks=banks, companies_per_product=companies
    )
    sim = Simulation.from_config(Config.model_validate(data))
    assert sim.metrics()["treasury_balance"] == money(population * 100)
    assert len(sim.firms.ids) == 11 * companies
    assert sim.firms.column("planned_workers").sum() <= population


def test_validator_catches_corrupted_accounts_and_registry(sim):
    # Fault injection: nessuna scrittura di compensazione per nascondere il guasto.
    account = next(iter(sim.deposits.values())).asset
    sim.ledger._balances[account] += money(1)
    with pytest.raises(AccountingError, match="attività"):
        sim.validate()


def test_canonical_json_rejects_nonfinite_and_key_collisions():
    assert canonical_json({"b": money(1), "a": 2}) == '{"a":2,"b":"1.000000"}'
    for value in ({"a": float("nan")}, {1: "a", "1": "b"}):
        with pytest.raises(ValueError):
            canonical_json(value)
