from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from economic_sim.accounting.ledger import (
    Account,
    AccountingError,
    AccountKind,
    Posting,
    Transaction,
)
from economic_sim.accounting.settlement import SettlementError
from economic_sim.money import ZERO, money


def parties(sim, same_bank=False):
    payer = int(sim.people.ids[0])
    bank = sim.deposits[payer].bank_id
    payee = next(
        int(p) for p in sim.people.ids[1:] if (sim.deposits[int(p)].bank_id == bank) == same_bank
    )
    return payer, payee


def test_loan_100_repay_40_does_not_create_reserves(sim):
    firm = int(sim.firms.ids[0])
    deposit = sim.deposits[firm]
    original_deposit = sim.agent(firm).deposit
    reserves = sim.metrics()["bank_reserves"]
    loan = sim.settlement.originate_loan("L1", firm, deposit.bank_id, money(100), 0.04, week=3)
    assert loan.interest_from_week == 4
    assert sim.agent(firm).deposit == original_deposit + money(100)
    assert (
        sim.ledger.balance(loan.asset_account)
        == sim.ledger.balance(loan.debt_account)
        == money(100)
    )
    sim.settlement.repay_loan("repay:1", loan.id, money(40), week=3)
    assert sim.agent(firm).deposit == original_deposit + money(60)
    assert (
        sim.ledger.balance(loan.asset_account) == sim.ledger.balance(loan.debt_account) == money(60)
    )
    assert sim.metrics()["bank_reserves"] == reserves
    sim.validate()
    before = sim.economic_checksum()
    with pytest.raises(SettlementError, match="exceeds_principal"):
        sim.settlement.repay_loan("repay:too_much", loan.id, money(61), week=4)
    assert sim.economic_checksum() == before
    sim.settlement.repay_loan("repay:final", loan.id, money(60), week=4)
    assert sim.loans[loan.id].status == "closed"
    assert sim.agent(firm).deposit == original_deposit
    assert sim.metrics()["private_credit"] == ZERO


@pytest.mark.parametrize("same_bank", [True, False])
def test_transfer_and_reserve_counterparts(sim, same_bank):
    payer, payee = parties(sim, same_bank)
    p, q = sim.deposits[payer], sim.deposits[payee]
    p_res, q_res = sim.reserves[p.bank_id], sim.reserves[q.bank_id]
    balances = {a: sim.ledger.balance(a) for a in [p.asset, q.asset, p_res.asset, q_res.asset]}
    sim.settlement.transfer("transfer:1", payer, payee, money(10))
    assert sim.ledger.balance(p.asset) == balances[p.asset] - money(10)
    assert sim.ledger.balance(q.asset) == balances[q.asset] + money(10)
    assert sim.ledger.balance(p_res.asset) == balances[p_res.asset] - (
        ZERO if same_bank else money(10)
    )
    assert sim.ledger.balance(q_res.asset) == balances[q_res.asset] + (
        ZERO if same_bank else money(10)
    )
    sim.validate()
    before = sim.economic_checksum()
    with pytest.raises(AccountingError, match="duplicato"):
        sim.settlement.transfer("transfer:1", payer, payee, money(10))
    assert before == sim.economic_checksum()


def test_failed_payment_and_failed_bank_settlement_are_atomic(sim):
    payer, payee = parties(sim)
    before = sim.economic_checksum()
    with pytest.raises(SettlementError) as failure:
        sim.settlement.transfer("no_funds", payer, payee, money(1_000_000))
    assert failure.value.code == "insufficient_customer_funds"
    assert before == sim.economic_checksum()
    # Erogazione reale: deposito cresce, riserve invariate, nessun saldo fittizio.
    bank = sim.deposits[payer].bank_id
    available_reserves = sim.ledger.balance(sim.reserves[bank].asset)
    sim.settlement.originate_loan("large", payer, bank, available_reserves + money(1), 0.03)
    before = sim.economic_checksum()
    with pytest.raises(SettlementError) as failure:
        sim.settlement.transfer("no_reserves", payer, payee, available_reserves + money(1))
    assert failure.value.code == "bank_settlement_failure"
    assert before == sim.economic_checksum()
    sim.validate()


def test_posting_atomicity_includes_new_accounts_and_journal(sim):
    entity = int(sim.people.ids[0])
    new = Account(f"{entity}:bad", entity, AccountKind.ASSET, "test")
    for amount in (money(1), Decimal("0.0000001")):
        before = sim.economic_checksum()
        with pytest.raises(AccountingError):
            sim.ledger.post(
                Transaction("bad", 0, "test", "Deliberato", (Posting(new.id, amount),)),
                new_accounts=(new,),
            )
        assert before == sim.economic_checksum()
        assert new.id not in sim.ledger.accounts


def test_purchase_settles_goods_costs_and_money_together(sim):
    seller = int(sim.firms.ids[0])
    buyer = int(sim.people.ids[1])
    before_cash = sim.agent(buyer).deposit
    before_qty = sim.physical.quantity(seller, 1)
    sim.settlement.purchase("food", buyer, seller, 1, 3.0, money(2), sim.physical)
    assert sim.agent(buyer).deposit == before_cash - money(6)
    assert sim.physical.quantity(buyer, 1) == 3.0
    assert sim.physical.quantity(seller, 1) == before_qty - 3.0
    assert sim.ledger.balance(f"{buyer}:inventory:1") == money(6)
    assert sim.ledger.balance(f"{seller}:cost_of_sales") == money(3)
    assert sim.ledger.balance(f"{seller}:sales") == money(6)
    sim.validate()
    before = sim.economic_checksum()
    with pytest.raises(SettlementError, match="insufficient_inventory"):
        sim.settlement.purchase(
            "too_many", buyer, seller, 1, before_qty * 2, money(2), sim.physical
        )
    assert before == sim.economic_checksum()
    # Duplicate transaction reaches the staged physical validation; nothing else commits.
    with pytest.raises(ValueError, match="duplicata"):
        sim.settlement.purchase("food", buyer, seller, 1, 3.0, money(2), sim.physical)
    assert before == sim.economic_checksum()


def test_failed_delivery_after_staging_preserves_everything(sim):
    seller, buyer = int(sim.firms.ids[0]), int(sim.people.ids[1])
    payer = int(sim.people.ids[2])
    sim.settlement.transfer("collision", payer, buyer, money(1))
    before = sim.economic_checksum()
    with pytest.raises(AccountingError, match="duplicato"):
        sim.settlement.purchase("collision", buyer, seller, 1, 1.0, money(2), sim.physical)
    assert before == sim.economic_checksum()


def test_reserved_funds_and_goods_cannot_be_spent_twice(sim):
    payer, payee = parties(sim)
    source = sim.deposits[payer].asset
    sim.ledger.reserve("hold", source, sim.agent(payer).deposit)
    before = sim.economic_checksum()
    with pytest.raises(SettlementError, match="insufficient_customer_funds"):
        sim.settlement.transfer("held", payer, payee, money(1))
    assert before == sim.economic_checksum()
    with pytest.raises(AccountingError):
        sim.ledger.reserve("second", source, money(1))
    sim.ledger.release("hold")
    sim.settlement.transfer("released", payer, payee, money(1))
    seller = int(sim.firms.ids[0])
    sim.physical.reserve("goods", seller, 1, sim.physical.quantity(seller, 1))
    before = sim.economic_checksum()
    with pytest.raises(SettlementError, match="insufficient_inventory"):
        sim.settlement.purchase("held_goods", payer, seller, 1, 1.0, money(2), sim.physical)
    assert before == sim.economic_checksum()
    sim.physical.release("goods")
    sim.settlement.purchase("released_goods", payer, seller, 1, 1.0, money(2), sim.physical)
    sim.validate()


def test_share_totals_and_mirrors_are_validated(sim):
    holding = sim.share_holdings[0]
    sim.share_holdings = (
        holding.model_copy(update={"quantity": money(1)}),
        *sim.share_holdings[1:],
    )
    with pytest.raises(AccountingError, match="Totale quote"):
        sim.validate()


def test_counterparty_ids_are_not_just_global_totals(sim):
    account = sim.deposits[int(sim.people.ids[0])].asset
    sim.ledger._accounts[account] = replace(sim.ledger.accounts[account], counterparty_id=999)
    with pytest.raises(AccountingError, match="Controparti errate"):
        sim.validate()


def test_precision_near_budget_and_external_decimal_context(sim):
    payer, payee = parties(sim)
    balance = sim.agent(payer).deposit
    before = sim.economic_checksum()
    with localcontext() as ctx:
        ctx.prec = 6
        assert sim.agent(payer).deposit == balance
        with pytest.raises(SettlementError, match="insufficient_customer_funds"):
            # Stringa precalcolata fuori dal contesto a bassa precisione.
            sim.settlement.transfer("too_much", payer, payee, "999999.000001")
        assert sim.economic_checksum() == before
        sim.settlement.transfer("exact", payer, payee, balance)
        assert sim.agent(payer).deposit == ZERO
        sim.validate()


def test_purchase_with_uncovered_reserves_does_not_deliver(sim):
    buyer, seller = int(sim.people.ids[1]), int(sim.firms.ids[0])
    bank = sim.deposits[buyer].bank_id
    reserve = sim.ledger.balance(sim.reserves[bank].asset)
    sim.settlement.originate_loan("uncovered", buyer, bank, reserve + money(1), 0.03)
    before = sim.economic_checksum()
    with pytest.raises(SettlementError, match="bank_settlement_failure"):
        sim.settlement.purchase(
            "no_delivery", buyer, seller, 1, 1.0, reserve + money(1), sim.physical
        )
    assert before == sim.economic_checksum()


def test_public_journal_is_not_aliased_to_caller_list(sim):
    aid = sim.deposits[int(sim.people.ids[0])].asset
    postings = [Posting(aid, ZERO)]
    sim.ledger.post(Transaction("zero", 0, "test", "Operazione nulla esplicita", postings))
    postings.append(Posting(aid, money(1)))
    assert len(sim.ledger.journal[-1].postings) == 1
    sim.validate()
