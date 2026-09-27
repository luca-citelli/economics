import csv
import json
from dataclasses import replace

import numpy as np
import pytest

from economic_sim import Simulation
from economic_sim.agents.firms import plan
from economic_sim.cli import main
from economic_sim.config import Config, load_config
from economic_sim.contracts import Snapshot
from economic_sim.markets.labor import match_and_pay
from economic_sim.money import ZERO, money


def drain(sim, entity, product, *, stock="inventory"):
    sim.inventory.consume(
        f"fixture:{entity}:{stock}:{product}",
        entity,
        product,
        sim.physical.quantity(entity, product, stock),
        stock=stock,
        reason="fixture_loss",
    )


@pytest.mark.parametrize("constraint", ["labor", "input", "capital", "reserve"])
def test_production_requires_all_factors(real_sim, constraint):
    sim = real_sim
    # Materiali: lavoro, energia pregressa, capitale e giacimento tutti necessari.
    row = int(np.flatnonzero(sim.firms.column("product_id") == 9)[0])
    firm = int(sim.firms.ids[row])
    if constraint == "labor":
        cash = sim.ledger.available(sim.deposits[firm].asset)
        sim.ledger.reserve("no_funding", sim.deposits[firm].asset, cash)
    elif constraint == "input":
        drain(sim, firm, 8)
    elif constraint == "capital":
        drain(sim, firm, 11, stock="installed_capital")
    else:
        drain(sim, firm, 9, stock="natural_reserve")
    sim.step()
    assert sim.output[row] == 0
    assert sim.paid_workers[row] == 0
    assert all(np.min(a) >= 0 for a in sim.physical._stocks.values())
    sim.validate()


def test_extraction_uses_old_energy_and_replenishes_for_next_week(real_sim):
    sim = real_sim
    rows = np.flatnonzero(sim.firms.column("product_id") == 9)
    for row in rows:
        drain(sim, int(sim.firms.ids[row]), 8)
    sim.step()
    assert np.all(sim.output[rows] == 0)
    assert all(sim.physical.quantity(int(sim.firms.ids[r]), 8) > 0 for r in rows)
    # Stimolo osservabile della domanda al confine, nessuna anticipazione di ordini futuri.
    orders = sim.firms.column("previous_orders").copy()
    orders[rows] = 10
    sim.firms.replace_column("previous_orders", orders)
    for row in rows:
        drain(sim, int(sim.firms.ids[row]), 9)
    sim.step()
    assert np.all(sim.output[rows] > 0)
    sim.validate()


def test_wages_once_contracts_unique_and_net_equals_gross(real_sim):
    sim = real_sim
    sim.step()
    wages = [t for t in sim.ledger.journal if t.week == 1 and t.phase == "labor_wages"]
    assert len(wages) == len(sim.employment) == sim.metrics()["employed"]
    assert len({t.id for t in wages}) == len(wages)
    total = sum((sim.ledger.balance(f"{person}:wage_income") for person in sim.employment), ZERO)
    assert total == sim.metrics()["wages_net"] == sim.metrics()["wages_gross"]
    for person, contract in sim.employment.items():
        assert (
            sim.people.column("employer_id")[sim.people.id_to_row[person]] == contract.employer_id
        )
        assert contract.last_paid_week == 1
    assert sim.metrics()["labor_applications"] > sim.metrics()["employed"]


def test_existing_contract_wage_retained_until_revision(real_sim):
    sim = real_sim
    sim.week = 1
    plan(sim)
    match_and_pay(sim)
    old = dict(sim.employment)
    sim.week = 2
    sim.firms.replace_column("offered_wage", np.full(len(sim.firms.ids), 130.0))
    match_and_pay(sim)
    assert all(sim.employment[p].wage == c.wage for p, c in old.items())
    assert all(sim.employment[p].employer_id == c.employer_id for p, c in old.items())
    # Revisione dovuta al confine successivo: accettazione di salario pubblicato.
    sim.employment = {p: replace(c, review_week=3) for p, c in sim.employment.items()}
    sim.week = 3
    match_and_pay(sim)
    assert sim.employment
    assert all(c.wage == money(130) for c in sim.employment.values())


def test_no_free_work_when_bank_cannot_settle(real_sim):
    sim = real_sim
    # Ogni banca vincola tutte le riserve: solo i pagamenti intrabancari sono possibili.
    for bank, account in sim.reserves.items():
        sim.ledger.reserve(f"blocked:{bank}", account.asset, sim.ledger.available(account.asset))
    sim.step()
    assert any(e.startswith("labor_suspended:") for e in sim.events)
    for contract in sim.employment.values():
        assert (
            sim.deposits[contract.person_id].bank_id == sim.deposits[contract.employer_id].bank_id
        )
    for row, product in enumerate(sim.firms.column("product_id")):
        assert sim.output[row] <= sim.paid_workers[row] * sim.products[product - 1].productivity
    sim.validate()


def test_capital_bought_in_t_only_used_from_t_plus_one(real_sim):
    sim = real_sim
    firm = int(sim.firms.ids[0])
    before = sim.physical.quantity(firm, 11, "installed_capital")
    sim.step()
    purchased = sim.physical.quantity(firm, 11, "pending_capital")
    assert purchased > 0
    assert sim.opening_capacity[0] == before * sim.products[0].capacity_per_capital
    assert sim.physical.quantity(firm, 11, "installed_capital") == pytest.approx(before * 0.999)
    installed = sim.physical.quantity(firm, 11, "installed_capital")
    sim.step()
    assert sim.opening_capacity[0] == pytest.approx(
        (installed + purchased) * sim.products[0].capacity_per_capital
    )
    sim.validate()


def test_capital_producer_purchase_keeps_acquisition_cost(real_sim):
    sim = real_sim
    sim.step()
    result = next(m for m in sim.market_results if m.market_id == "capital")
    capital_firms = set(map(int, sim.firms.ids[sim.firms.column("product_id") == 11]))
    buyers = capital_firms.intersection(t.buyer_id for t in result.trades)
    assert buyers
    for buyer in buyers:
        paid = sum((t.total_cost for t in result.trades if t.buyer_id == buyer), ZERO)
        assert sim.ledger.balance(f"{buyer}:pending_capital") == paid
    assert sim.metrics()["gdp_discrepancy"] == ZERO


def test_production_cost_and_weighted_average_sales(real_sim):
    from decimal import Decimal

    sim = real_sim
    sim.week = 1
    firm, person = int(sim.firms.ids[0]), int(sim.people.ids[0])
    before_qty = sim.physical.quantity(firm, 1)
    before_value = sim.ledger.balance(f"{firm}:inventory:1")
    sim.settlement.pay_wage("fixture:wage", firm, person, "120", week=1)
    cost, inputs = sim.inventory.produce(firm, sim.products[0], 10.0)
    assert inputs == money("1.5")
    assert cost == money("121.5")
    assert sim.ledger.balance(f"{firm}:work_in_progress") == ZERO
    assert sim.ledger.balance(f"{firm}:inventory:1") == before_value + cost
    expected_cost = money((before_value + cost) * Decimal(2) / Decimal(str(before_qty + 10)))
    sim.settlement.purchase("fixture:sale", person, firm, 1, 2.0, "2", sim.physical, week=1)
    assert sim.ledger.balance(f"{firm}:cost_of_sales") == expected_cost
    assert sim.ledger.balance(f"{person}:inventory:1") == money(4)
    assert sim.ledger.balance(f"{firm}:inventory:1") == before_value + cost - expected_cost
    sim.validate()


def test_final_goods_priorities_and_no_secondary_need_resampling(real_sim):
    sim = real_sim
    needs = sim.people.column("needs")
    sim.step()
    transactions = [
        t
        for t in sim.ledger.journal
        if t.week == 1 and ":market:" in t.id and int(t.id.split(":")[2]) <= 7
    ]
    products = [int(t.id.split(":")[2]) for t in transactions]
    assert products == sorted(products)
    np.testing.assert_array_equal(needs, sim.people.column("needs"))
    assert np.all(sim.consumed[:, :6] <= needs[:, :6] + 1e-9)
    assert np.isfinite(sim.consumed).all()


def test_no_trade_cpi_imputation_and_expiring_services(real_sim):
    sim = real_sim
    sim.firms.replace_column("active", np.zeros(len(sim.firms.ids), dtype=bool))
    initial_needs = sim.people.column("needs")
    for _ in range(2):
        metrics = sim.step()
    assert metrics["cpi"] == 100
    assert metrics["cpi_imputed_share"] == 1
    assert metrics["cpi_max_price_age"] == 2
    assert metrics["inflation_annual"] is None
    assert all(m.transacted_price is None for m in sim.market_results)
    assert np.array_equal(initial_needs, sim.people.column("needs"))
    assert np.isfinite(sim.firms.column("reputation")).all()
    assert all(sim.physical.quantity(int(f), 2) == 0 for f in sim.firms.ids)


@pytest.mark.parametrize("failure_point", ["resources", "commit"])
def test_step_rollback_restores_rng_buffers_and_journal(real_sim, monkeypatch, failure_point):
    import economic_sim.simulation as module

    sim = real_sim
    sim.step()
    before = sim.economic_checksum()
    rng = sim.rng.states()
    ledger_history = sim.ledger._journal
    physical_history = sim.physical._journal
    saved_snapshot = sim.snapshot()
    original = module.buy_resources if failure_point == "resources" else module.collect

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected")

    monkeypatch.setattr(
        module, "buy_resources" if failure_point == "resources" else "collect", fail
    )
    with pytest.raises(RuntimeError, match="injected"):
        sim.step()
    assert sim.status == "ERROR" and sim.week == 1
    assert sim.economic_checksum() == before
    assert sim.rng.states() == rng
    assert sim.ledger._journal is ledger_history
    assert sim.physical._journal is physical_history
    assert saved_snapshot.week == 1
    assert len(sim.history) == 1
    assert not sim.ledger.holds
    sim.validate()
    with pytest.raises(ValueError, match="ERROR"):
        sim.step()


def test_reproducible_real_steps_and_snapshot_round_trip(real_config):
    a = Simulation.from_config(real_config)
    data = real_config.model_dump()
    data["runtime"]["default_steps_per_second"] = 10.0
    b = Simulation.from_config(Config.model_validate(data))
    old = a.people.column("satisfaction")
    for _ in range(3):
        assert a.step() == b.step()
    assert a.economic_checksum() == b.economic_checksum()
    assert np.all(old == 0)
    snapshot = a.snapshot()
    assert Snapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
    snapshot.metrics["employed"] = 100000
    snapshot.markets[0].failure_reasons["mutated"] = 1
    assert a.metrics()["employed"] < 100000
    assert "mutated" not in a.market_results[0].failure_reasons


def test_52_weeks_invariants_and_complete_csv(real_sim, tmp_path):
    sim = real_sim
    deposits = sim.monetary_metrics()["private_deposits"]
    reserves = sim.monetary_metrics()["bank_reserves"]
    needs = sim.people.column("needs")
    for week in range(1, 53):
        metrics = sim.step()
        assert metrics["week"] == week
        assert metrics["private_deposits"] == deposits
        assert metrics["bank_reserves"] == reserves
        assert metrics["gdp_discrepancy"] == ZERO
        assert np.isfinite([float(x) for x in metrics.values() if x is not None]).all()
        assert sim.phase_trace[0] == "opening" and sim.phase_trace[-1] == "commit"
    sim.validate()
    assert np.array_equal(needs, sim.people.column("needs"))
    assert metrics["inflation_annual"] == pytest.approx(metrics["cpi"] / 100 - 1)
    sim.export_csv(tmp_path / "all.csv")
    with (tmp_path / "all.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 52
    assert [int(r["week"]) for r in rows] == list(range(1, 53))
    assert all(len(r) == len(rows[0]) for r in rows)
    assert rows[0]["inflation_annual"] == ""
    assert rows[-1]["inflation_annual"] != ""


def test_profile_rejects_implicit_future_phases(real_config):
    for section, key, value in [
        ("government", "profit_tax_rate", 0.1),
        ("central_bank", "emergency_lending_enabled", True),
        ("execution", "phases", {}),
    ]:
        data = real_config.model_dump()
        data[section][key] = value
        with pytest.raises(ValueError):
            Config.model_validate(data)
    data = real_config.model_dump()
    data["real_economy"] = None
    with pytest.raises(ValueError):
        Config.model_validate(data)


def test_cli_real_execution(tmp_path):
    import yaml

    config = load_config("configs/t02.yaml")
    data = config.model_dump(mode="json", exclude={"catalog"})
    data["products_file"] = str((tmp_path / "products.yaml").resolve())
    data["simulation"].update(initial_population=100, companies_per_product=2)
    (tmp_path / "products.yaml").write_text(
        yaml.safe_dump(config.catalog.model_dump(mode="json")), encoding="utf-8"
    )
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    output, csv_path = tmp_path / "out.json", tmp_path / "weeks.csv"
    assert (
        main(["run", str(path), "--steps", "2", "--csv", str(csv_path), "--output", str(output)])
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["snapshot"]["week"] == 2
    assert main(["run", str(path), "--steps", "0", "--csv", str(csv_path)]) == 2
    assert main(["run", "configs/base.yaml", "--steps", "1", "--csv", str(csv_path)]) == 2
