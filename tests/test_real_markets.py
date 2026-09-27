from decimal import Decimal

import numpy as np
import pytest

from economic_sim.accounting.ledger import AccountingError
from economic_sim.contracts import Order
from economic_sim.markets.goods import affordable_quantity, clear_market
from economic_sim.money import money


def order(sim, buyer, quantity, budget, product=1):
    return Order(
        buyer_id=buyer,
        product_id=product,
        quantity=float(quantity),
        budget=money(budget),
        max_price=money(1000),
        week=sim.week,
    )


def leave_stock(sim, firm, product, quantity):
    current = sim.physical.quantity(firm, product)
    sim.inventory.consume(
        f"fixture:{firm}:{product}", firm, product, current - quantity, reason="fixture_loss"
    )


def test_exhausted_seller_fallback_and_no_duplicate_demand(real_sim):
    sim = real_sim
    sellers = [int(x) for x in sim.firms.ids[:2]]
    buyer = int(sim.people.ids[0])
    leave_stock(sim, sellers[0], 1, 2)
    leave_stock(sim, sellers[1], 1, 3)
    before = sim.agent(buyer).deposit
    result = clear_market(sim, 1, [order(sim, buyer, 7, 14)])
    assert [t.seller_id for t in result.trades] == sellers
    assert [t.quantity for t in result.trades] == [2, 3]
    assert result.financeable_demand == 7
    assert result.unfilled_demand == 2
    assert result.unfinanceable_demand == 0
    assert result.failure_reasons == {"supply_or_budget": 1}
    assert result.residual_supply == 0
    assert sim.agent(buyer).deposit == before - 10
    assert sim.physical.quantity(buyer, 1) == 5
    assert not sim.ledger.holds
    sim.validate()


def test_financeable_and_unfinanceable_demands_are_separate(real_sim):
    buyer = int(real_sim.people.ids[0])
    result = clear_market(real_sim, 1, [order(real_sim, buyer, 10, 3)])
    assert result.financeable_demand == 1.5
    assert result.unfinanceable_demand == 8.5
    assert result.unfilled_demand == 0
    assert sum(t.total_cost for t in result.trades) == money(3)


def test_held_funds_and_inventory_cannot_be_spent_twice(real_sim):
    sim = real_sim
    buyer = int(sim.people.ids[0])
    seller = int(sim.firms.ids[0])
    available = sim.agent(buyer).deposit
    sim.ledger.reserve("external", sim.deposits[buyer].asset, available - 2)
    sim.physical.reserve("stock", seller, 1, sim.physical.quantity(seller, 1))
    result = clear_market(sim, 1, [order(sim, buyer, 1, 2)])
    assert result.trades[0].seller_id != seller
    assert sim.agent(buyer).deposit == available - 2
    before = sim.economic_checksum()
    with pytest.raises(AccountingError):
        clear_market(sim, 1, [order(sim, buyer, 1, 2)])
    assert sim.economic_checksum() == before
    assert set(sim.ledger.holds) == {"external"}


def test_no_sales_null_price_and_quality_choice(real_sim):
    sim = real_sim
    buyer = int(sim.people.ids[0])
    result = clear_market(sim, 2, [order(sim, buyer, 5, 15, 2)])
    assert result.transacted_price is None
    assert result.offered_price == 3
    assert result.unfilled_demand == 5
    q = sim.firms.column("quality").copy()
    q[1] = 10
    sim.firms.replace_column("quality", q)
    result = clear_market(sim, 1, [order(sim, buyer, 1, 2)], quality_preferences={buyer: 1.0})
    assert result.trades[0].seller_id == int(sim.firms.ids[1])


def test_quantized_budget_never_creates_free_goods():
    for price in (money("0.01"), money("1.333333"), money("99999999")):
        for budget in (money(0), money("0.000001"), money("1.000001")):
            q = affordable_quantity(1000, price, budget)
            payment = money(Decimal(str(q)) * price)
            assert payment <= budget
            assert q == 0 or payment > 0


def test_failed_interbank_settlement_tries_next_supplier(real_sim):
    sim = real_sim
    buyer = int(sim.people.ids[1])
    bank = sim.deposits[buyer].bank_id
    reserves = sim.reserves[bank].asset
    sim.ledger.reserve("blocked_reserves", reserves, sim.ledger.available(reserves))
    result = clear_market(sim, 1, [order(sim, buyer, 1, 2)])
    assert len(result.trades) == 1
    assert result.trades[0].seller_id == int(sim.firms.ids[1])
    assert result.unfilled_demand == 0
    sim.validate()


def test_buyers_use_reproducible_random_order(real_config):
    from economic_sim import Simulation

    winners = []
    for _ in range(2):
        sim = Simulation.from_config(real_config)
        leave_stock(sim, int(sim.firms.ids[0]), 1, 1)
        leave_stock(sim, int(sim.firms.ids[1]), 1, 0)
        orders = [order(sim, int(b), 1, 2) for b in sim.people.ids]
        result = clear_market(sim, 1, orders)
        winners.append(result.trades[0].buyer_id)
    assert winners[0] == winners[1]
    assert winners[0] != int(sim.people.ids[0])
    assert np.isfinite(result.unfilled_demand)
