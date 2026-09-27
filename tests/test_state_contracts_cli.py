import json
import os
import subprocess
import sys

import numpy as np
import pytest

from economic_sim.cli import main
from economic_sim.contracts import MarketResult, Offer, Order, PolicyCommand, Snapshot, Trade
from economic_sim.random_utils import RandomStreams
from economic_sim.serialization import canonical_json


def test_column_mapping_isolation_and_no_duplicate_balances(sim):
    assert sim.people.id_to_row[int(sim.people.ids[5])] == 5
    assert sim.people.ids.dtype == np.int64
    assert sim.people.ids[5] != 5
    assert sim.people.column("needs").shape == (1000, 11)
    old = sim.people.column("needs")
    with pytest.raises(ValueError):
        old[0, 0] = 1
    with pytest.raises(ValueError):
        old.setflags(write=True)
    updated = old.copy()
    updated[0, 0] = 9.0
    sim.people.replace_column("needs", updated)
    updated[0, 0] = 7.0
    assert old[0, 0] == 10.0
    assert sim.people.column("needs")[0, 0] == 9.0
    for table in (sim.people, sim.firms, sim.banks):
        assert not {"cash", "deposit", "reserves", "debt"}.intersection(table.schema)
    projection = sim.deposit_projection(sim.people.ids)
    with pytest.raises(ValueError):
        projection[0] = 0
    view = sim.agent(int(sim.people.ids[0]))
    original = view.deposit
    sim.settlement.originate_loan("view", view.id, sim.deposits[view.id].bank_id, "100", 0.03)
    assert view.deposit == original + 100
    assert projection[0] == float(original)


def test_rng_named_streams_and_state_round_trip():
    a, b = RandomStreams(42), RandomStreams(42)
    a["ownership"].random(500)
    assert np.array_equal(a["people"].random(10), b["people"].random(10))
    saved = json.loads(canonical_json(a.states()))
    expected = a["people"].random(10)
    a.restore(saved)
    assert np.array_equal(a["people"].random(10), expected)
    before = canonical_json(a.states())
    saved["people"]["bit_generator"] = "invalid"
    with pytest.raises(ValueError):
        a.restore(saved)
    assert canonical_json(a.states()) == before


def test_contract_json_round_trips_and_snapshot_isolation(sim):
    snap = sim.snapshot()
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap
    assert snap.markets == ()
    snap.metrics["private_deposits"] = 0
    assert sim.metrics()["private_deposits"] > 0
    command = PolicyCommand(
        schema_version=1,
        command_id="rate-1",
        submitted_at="2026-09-27T10:00Z",
        effective_week=1,
        server_sequence=1,
        type="policy",
        patch={"policy_rate": 0.04},
    )
    assert PolicyCommand.model_validate_json(command.model_dump_json()) == command
    result = MarketResult(
        market_id="food",
        week=0,
        offers=(),
        financeable_demand=0.0,
        unfinanceable_demand=0.0,
        trades=(),
        unfilled_demand=0.0,
        residual_supply=0.0,
        offered_price=None,
        transacted_price=None,
        failure_reasons={},
    )
    assert MarketResult.model_validate_json(result.model_dump_json()) == result


def test_populated_market_and_instrument_contracts_round_trip(sim):
    seller, buyer = int(sim.firms.ids[0]), int(sim.people.ids[0])
    offer = Offer(seller_id=seller, product_id=1, quantity=1.0, price="2", quality=1.0, week=1)
    order = Order(buyer_id=buyer, product_id=1, quantity=1.0, budget="2", max_price="2", week=1)
    trade = Trade(
        id="test-trade",
        buyer_id=buyer,
        seller_id=seller,
        product_id=1,
        quantity=1.0,
        price="2",
        total_cost="2",
        payment_id="test-payment",
        instrument_id=None,
    )
    result = MarketResult(
        market_id="food",
        week=1,
        offers=(offer,),
        financeable_demand=1.0,
        unfinanceable_demand=0.0,
        trades=(trade,),
        unfilled_demand=0.0,
        residual_supply=0.0,
        offered_price="2",
        transacted_price="2",
        failure_reasons={},
    )
    loan = sim.settlement.originate_loan("json", buyer, sim.deposits[buyer].bank_id, "1", 0.0)
    for contract in (
        offer,
        order,
        trade,
        result,
        loan,
        *sim.bonds.values(),
        *sim.share_issues.values(),
        *sim.share_holdings,
    ):
        assert type(contract).model_validate_json(contract.model_dump_json()) == contract


def test_cli_validates_initializes_and_handles_errors(tmp_path, capsys):
    assert main(["validate", "configs/base.yaml"]) == 0
    output = tmp_path / "run/week0.json"
    assert main(["init", "configs/base.yaml", "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["snapshot"]["week"] == 0
    assert len(report["balance_sheets"]) == 1038
    assert main(["validate", str(tmp_path / "missing.yaml")]) == 2
    assert "Errore:" in capsys.readouterr().err


def test_checksum_independent_of_python_hash_seed(tmp_path):
    code = (
        "from economic_sim import Simulation; from economic_sim.config import load_config; "
        "print(Simulation.from_config(load_config('configs/base.yaml')).economic_checksum())"
    )
    results = []
    for seed in ("1", "773"):
        run = subprocess.run(
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        results.append(run.stdout.strip())
    assert results[0] == results[1]
