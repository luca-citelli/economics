"""Apertura per stock ereditati: nessuna transazione della settimana 1."""

import math
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from economic_sim.accounting.ledger import Account, AccountKind, Ledger, Transaction, change
from economic_sim.accounting.physical import PhysicalEntry, PhysicalRegister
from economic_sim.accounting.settlement import DepositAccount, ReserveAccount
from economic_sim.agents.state import NO_ID, BankState, FirmState, HouseholdState, Institution
from economic_sim.config import Config
from economic_sim.contracts import Bond, ShareHolding, ShareIssue
from economic_sim.money import QUANTUM, ZERO, money, money_context
from economic_sim.random_utils import RandomStreams, truncated_nonnegative_normal

CB_ID = 1
GOVERNMENT_ID = 2


@dataclass
class InitialState:
    people: HouseholdState
    firms: FirmState
    banks: BankState
    government: Institution
    central_bank: Institution
    ledger: Ledger
    physical: PhysicalRegister
    rng: RandomStreams
    deposits: dict[int, DepositAccount]
    reserves: dict[int, ReserveAccount]
    bonds: dict[str, Bond]
    share_issues: dict[str, ShareIssue]
    share_holdings: tuple[ShareHolding, ...]


@money_context
def split_amount(total, count):
    units = int(money(total) / QUANTUM)
    base, remainder = divmod(units, count)
    return [money((base + (i < remainder)) * QUANTUM) for i in range(count)]


@money_context
def initialize(config: Config) -> InitialState:
    n = config.simulation.initial_population
    b = config.simulation.initial_banks
    cpp = config.simulation.companies_per_product
    catalog = sorted(config.catalog.products, key=lambda p: p.id)
    products = [p for p in catalog for _ in range(cpp)]
    f = len(products)
    scale = config.firm_scale
    rng = RandomStreams(config.simulation.seed)
    bank_ids = np.arange(100, 100 + b, dtype=np.int64)
    firm_ids = np.arange(1_000_000, 1_000_000 + f, dtype=np.int64)
    person_ids = np.arange(10_000_000, 10_000_000 + n, dtype=np.int64)
    person_banks = bank_ids[np.arange(n) % b]
    firm_banks = bank_ids[np.arange(f) % b]
    r = rng["people"]
    pc = config.people
    needs = np.zeros((n, 11), dtype=np.float64)
    for product in catalog:
        needs[:, product.id - 1] = truncated_nonnegative_normal(
            r, product.need_mean, product.need_std, n
        )
    people = HouseholdState(
        person_ids,
        bank_id=person_banks,
        employer_id=np.full(n, NO_ID),
        age_weeks=r.integers(pc.adult_age_min_years * 52, pc.adult_age_max_years * 52 + 1, n),
        active=np.ones(n, dtype=bool),
        saving_propensity=r.uniform(pc.propensity_min, pc.propensity_max, n),
        risk_propensity=r.uniform(pc.propensity_min, pc.propensity_max, n),
        quality_propensity=r.uniform(pc.propensity_min, pc.propensity_max, n),
        reservation_wage=float(pc.reservation_wage)
        * r.uniform(1 - pc.wage_spread, 1 + pc.wage_spread, n),
        expected_income=np.zeros(n),
        unemployment_weeks=np.zeros(n, dtype=np.int64),
        deprivation_weeks=np.zeros(n, dtype=np.int64),
        needs=needs,
        satisfaction=np.zeros((n, 7)),
    )
    firms = FirmState(
        firm_ids,
        bank_id=firm_banks,
        product_id=[p.id for p in products],
        active=np.ones(f, dtype=bool),
        extractive=[p.kind == "resource" for p in products],
        productivity=[p.productivity for p in products],
        offered_wage=np.full(f, float(config.opening.offered_wage)),
        offered_price=[float(p.opening_price) for p in products],
        quality=[p.quality for p in products],
        reputation=np.full(f, config.opening.initial_reputation),
        planned_workers=[math.ceil(p.initial_workers * scale) for p in products],
        previous_sales=np.zeros(f),
        previous_orders=np.zeros(f),
        previous_unfilled=np.zeros(f),
        observed_unit_cost=[float(p.opening_unit_cost) for p in products],
        previous_vacancies=np.zeros(f, dtype=np.int64),
        previous_applications=np.zeros(f, dtype=np.int64),
    )
    banks = BankState(
        bank_ids,
        active=np.ones(b, dtype=bool),
        deposit_rate=np.full(
            b, config.banks.deposit_rate_pass_through * config.central_bank.reserve_rate
        ),
    )
    ledger = Ledger()
    physical = PhysicalRegister(np.concatenate((person_ids, firm_ids)), np.arange(1, 12))
    accounts, lines, physical_entries = [], [], []

    def opening(
        entity, suffix, kind, value, purpose, nonnegative=False, counterparty=None, instrument=None
    ):
        account = Account(
            f"{entity}:{suffix}", int(entity), kind, purpose, nonnegative, counterparty, instrument
        )
        accounts.append(account)
        lines.append(change(account, value))
        return account.id

    def stock(entity, product, quantity, stock_type="inventory"):
        physical_entries.append(
            PhysicalEntry(
                "opening",
                0,
                "opening",
                "Dotazione ereditata",
                entity,
                product,
                quantity,
                stock_type,
            )
        )

    deposits, reserves = {}, {}
    bank_deposits = {int(i): ZERO for i in bank_ids}
    person_wealth = {int(i): ZERO for i in person_ids}
    person_amounts = [
        money(pc.initial_deposit * Decimal(str(factor)))
        for factor in rng["endowments"].uniform(1 - pc.deposit_spread, 1 + pc.deposit_spread, n)
    ]
    firm_amount = money(config.opening.firm_deposit * Decimal(str(scale)))
    for entity, bank, amount in zip(
        [*person_ids, *firm_ids],
        [*person_banks, *firm_banks],
        [*person_amounts, *([firm_amount] * f)],
        strict=True,
    ):
        entity, bank = int(entity), int(bank)
        aid = opening(
            entity, "deposit", AccountKind.ASSET, amount, "deposit", True, bank, f"deposit:{entity}"
        )
        lid = opening(
            bank,
            f"deposit:{entity}",
            AccountKind.LIABILITY,
            amount,
            "deposit",
            True,
            entity,
            f"deposit:{entity}",
        )
        deposits[entity] = DepositAccount(entity, bank, aid, lid)
        bank_deposits[bank] += amount
        if entity in person_wealth:
            person_wealth[entity] += amount

    equities = {}
    for entity, product in zip(firm_ids, products, strict=True):
        entity = int(entity)
        values = {p.id: ZERO for p in catalog}
        stock(entity, product.id, product.initial_output * scale)
        values[product.id] = money(
            Decimal(str(product.initial_output * scale)) * product.opening_unit_cost
        )
        for name, quantity in product.initial_inputs.items():
            input_product = next(p for p in catalog if p.name == name)
            stock(entity, input_product.id, quantity * scale)
            values[input_product.id] += money(
                Decimal(str(quantity * scale)) * input_product.opening_unit_cost
            )
        for pid, value in values.items():
            opening(
                entity,
                f"inventory:{pid}",
                AccountKind.ASSET,
                value,
                "inventory",
                True,
                instrument=str(pid),
            )
        capital = product.initial_capital * scale
        stock(entity, 11, capital, "installed_capital")
        capital_value = money(Decimal(str(capital)) * catalog[10].opening_unit_cost)
        opening(
            entity,
            "installed_capital",
            AccountKind.ASSET,
            capital_value,
            "installed_capital",
            True,
            instrument="11",
        )
        if product.kind == "resource":
            stock(entity, product.id, product.natural_reserve * scale, "natural_reserve")
        equities[entity] = firm_amount + sum(values.values(), ZERO) + capital_value

    total_reserves = ZERO
    bank_equities = split_amount(config.banks.initial_equity_per_person * n, b)
    for bank_id, equity in zip(bank_ids, bank_equities, strict=True):
        bank_id = int(bank_id)
        amount = bank_deposits[bank_id] + equity
        aid = opening(
            bank_id,
            "reserves",
            AccountKind.ASSET,
            amount,
            "reserve",
            True,
            CB_ID,
            f"reserve:{bank_id}",
        )
        lid = opening(
            CB_ID,
            f"reserve:{bank_id}",
            AccountKind.LIABILITY,
            amount,
            "reserve",
            True,
            bank_id,
            f"reserve:{bank_id}",
        )
        reserves[bank_id] = ReserveAccount(bank_id, aid, lid)
        equities[bank_id] = equity
        total_reserves += amount

    treasury = config.government.initial_treasury_per_person * n
    opening(
        GOVERNMENT_ID, "treasury", AccountKind.ASSET, treasury, "treasury", True, CB_ID, "treasury"
    )
    opening(
        CB_ID,
        "treasury",
        AccountKind.LIABILITY,
        treasury,
        "treasury",
        True,
        GOVERNMENT_ID,
        "treasury",
    )
    public_debt = total_reserves + treasury
    bond_asset = opening(
        CB_ID,
        "bond:opening",
        AccountKind.ASSET,
        public_debt,
        "bond",
        True,
        GOVERNMENT_ID,
        "opening-bond",
    )
    bond_debt = opening(
        GOVERNMENT_ID,
        "bond:opening",
        AccountKind.LIABILITY,
        public_debt,
        "bond",
        True,
        CB_ID,
        "opening-bond",
    )
    opening(
        GOVERNMENT_ID, "inherited_equity", AccountKind.EQUITY, -total_reserves, "inherited_equity"
    )
    opening(CB_ID, "inherited_equity", AccountKind.EQUITY, ZERO, "inherited_equity")
    bond = Bond(
        id="opening-bond",
        issuer_id=GOVERNMENT_ID,
        holder_id=CB_ID,
        face_value=public_debt,
        issue_price=money(1),
        issued_week=0,
        maturity_week=52,
        asset_account=bond_asset,
        liability_account=bond_debt,
    )

    owners = rng["ownership"].permutation(person_ids)
    issues, holdings = {}, []
    for i, (issuer, equity) in enumerate(sorted(equities.items())):
        owner = int(owners[i % n])
        issue_id = f"shares:{issuer}"
        capital_account = opening(
            issuer,
            "share_capital",
            AccountKind.EQUITY,
            equity,
            "share_capital",
            True,
            instrument=issue_id,
        )
        asset = opening(
            owner, f"shares:{issuer}", AccountKind.ASSET, equity, "shares", True, issuer, issue_id
        )
        issues[issue_id] = ShareIssue(
            id=issue_id,
            issuer_id=issuer,
            total_shares=config.opening.shares_per_issuer,
            capital_account=capital_account,
        )
        holdings.append(
            ShareHolding(
                issue_id=issue_id,
                owner_id=owner,
                quantity=config.opening.shares_per_issuer,
                asset_account=asset,
            )
        )
        person_wealth[owner] += equity
    for person, wealth in person_wealth.items():
        opening(person, "inherited_equity", AccountKind.EQUITY, wealth, "inherited_equity")
    ledger.post(
        Transaction("opening", 0, "opening", "Stock ereditati di settimana 0", tuple(lines)),
        new_accounts=tuple(accounts),
    )
    physical.post(tuple(physical_entries))
    return InitialState(
        people,
        firms,
        banks,
        Institution(GOVERNMENT_ID, "government", "Tesoro"),
        Institution(CB_ID, "central_bank", "Banca centrale"),
        ledger,
        physical,
        rng,
        deposits,
        reserves,
        {bond.id: bond},
        issues,
        tuple(holdings),
    )
