"""Default, realizzi di liquidazione e conversione bancaria D1."""

from decimal import ROUND_DOWN, Decimal

from economic_sim.accounting.ledger import Account, AccountKind, Transaction, change
from economic_sim.accounting.physical import PhysicalEntry
from economic_sim.accounting.settlement import SettlementError
from economic_sim.contracts import ShareHolding
from economic_sim.money import QUANTUM, ZERO, money, money_context


class Crisis:
    def __init__(self, sim):
        self.sim = sim
        self.liquidations = {}  # ID -> settimana di avvio; ID stabili
        self.resolved_banks = set()
        self.resolved_this_week = set()
        self.defaulted_people = set()
        self.closed_liquidations = set()
        self.loss_exposed_firms = set()
        self.tax_arrears_weeks = {}
        self.asset_proceeds = {}
        self.flows = {
            "loan_writeoffs": ZERO,
            "deposit_haircuts": ZERO,
            "liquidation_recoveries": ZERO,
            "liquidation_inventory_loss": ZERO,
            "liquidation_capital_investment": ZERO,
        }

    def open_week(self):
        self.flows = dict.fromkeys(self.flows, ZERO)
        self.resolved_this_week = set()

    def own_share_value(self, bank):
        sim = self.sim
        return sum(
            (
                sim.ledger.balance(holding.asset_account)
                for holding in sim.share_holdings
                if holding.issue_id == f"shares:{bank}" and holding.owner_id == bank
            ),
            ZERO,
        )

    def _post(self, tx_id, reason, changes):
        sim = self.sim
        accounts = []
        lines = []
        for entity, name, kind, amount in changes:
            aid = f"{entity}:{name}"
            account = sim.ledger.accounts.get(aid)
            if account is None:
                account = Account(aid, entity, kind, name)
                accounts.append(account)
            lines.append(change(account, amount))
        sim.ledger.post(
            Transaction(tx_id, sim.week, "crisis", reason, tuple(lines)),
            new_accounts=tuple(accounts),
        )

    @money_context
    def write_down_loan(self, loan_id):
        sim = self.sim
        loan = sim.loans[loan_id]
        amount = sim.ledger.balance(loan.asset_account)
        if amount <= ZERO:
            sim._loans[loan_id] = loan.model_copy(
                update={"status": "written_down", "arrears": ZERO}
            )
            return
        bank_expense = Account(
            f"{loan.bank_id}:credit_loss", loan.bank_id, AccountKind.EXPENSE, "credit_loss"
        )
        debtor_income = Account(
            f"{loan.borrower_id}:debt_forgiveness",
            loan.borrower_id,
            AccountKind.INCOME,
            "debt_forgiveness",
        )
        sim.ledger.post(
            Transaction(
                f"w{sim.week}:writeoff:{loan_id}",
                sim.week,
                "crisis",
                "Perdita su credito",
                (
                    change(sim.ledger.accounts[loan.asset_account], -amount),
                    change(bank_expense, amount),
                    change(sim.ledger.accounts[loan.debt_account], -amount),
                    change(debtor_income, amount),
                ),
            ),
            new_accounts=tuple(
                a for a in (bank_expense, debtor_income) if a.id not in sim.ledger.accounts
            ),
        )
        sim._loans[loan_id] = loan.model_copy(update={"status": "written_down", "arrears": ZERO})
        self.flows["loan_writeoffs"] += amount
        sim.events.append(f"loan_writeoff:{loan_id}:amount={amount}")

    @money_context
    def resolve_bank(self, bank, target=None):
        sim = self.sim
        if bank in self.resolved_this_week:
            return False
        sheet = sim.ledger.balance_sheets()[bank]
        issue_id = f"shares:{bank}"
        own_shares = self.own_share_value(bank)
        equity = sheet["equity"] - own_shares
        if equity >= ZERO:
            return True
        target = money(
            target
            if target is not None
            else max(
                sim.config.opening.shares_per_issuer * Decimal("0.001"),
                (sheet["assets"] - own_shares)
                * Decimal(str(sim.config.crisis_investment.bank_target_ratio)),
            )
        )
        if target <= ZERO:
            raise ValueError("Target patrimoniale non positivo")
        haircut = money(target - equity)
        depositors = [
            (entity, dep)
            for entity, dep in sorted(sim.deposits.items())
            if dep.bank_id == bank and sim.ledger.available(dep.asset) > ZERO
        ]
        available = sum((sim.ledger.available(dep.asset) for _, dep in depositors), ZERO)
        if available < haircut:
            sim.events.append(
                f"bank_resolution_unfunded:{bank}:needed={haircut}:available={available}"
            )
            sim.status = "TERMINATED"
            return False
        issue = sim.share_issues[issue_id]
        old_holdings = [h for h in sim.share_holdings if h.issue_id == issue_id]
        old_cost = sim.ledger.balance(issue.capital_account)
        # Le vecchie partecipazioni perdono il costo storico; l'emittente stornando
        # il capitale registra una contropartita di risultato di pari importo.
        for holding in old_holdings:
            carrying = sim.ledger.balance(holding.asset_account)
            if carrying:
                if holding.owner_id in sim.firms.id_to_row:
                    self.loss_exposed_firms.add(holding.owner_id)
                self._post(
                    f"w{sim.week}:old-bank-share:{bank}:{holding.owner_id}",
                    "Azzeramento vecchie quote",
                    [
                        (holding.owner_id, f"shares:{bank}", AccountKind.ASSET, -carrying),
                        (holding.owner_id, "share_loss", AccountKind.EXPENSE, carrying),
                    ],
                )
        if old_cost:
            self._post(
                f"w{sim.week}:old-bank-capital:{bank}",
                "Storno capitale precedente",
                [
                    (bank, "share_capital", AccountKind.EQUITY, -old_cost),
                    (bank, "resolution_gain", AccountKind.INCOME, old_cost),
                ],
            )
        holdings = [
            h.model_copy(update={"quantity": ZERO}) if h.issue_id == issue_id else h
            for h in sim.share_holdings
        ]
        remaining_haircut = haircut
        remaining_target = target
        new_shares = issue.total_shares
        remaining_shares = new_shares
        for index, (owner, dep) in enumerate(depositors):
            amount = min(remaining_haircut, sim.ledger.available(dep.asset))
            if index == len(depositors) - 1:
                amount = remaining_haircut
                value, quantity = remaining_target, remaining_shares
            else:
                value = min(
                    remaining_target,
                    (target * amount / haircut).quantize(QUANTUM, rounding=ROUND_DOWN),
                )
                quantity = min(
                    remaining_shares,
                    (new_shares * amount / haircut).quantize(QUANTUM, rounding=ROUND_DOWN),
                )
            remaining_haircut -= amount
            remaining_target -= value
            remaining_shares -= quantity
            loss = amount - value
            if loss and owner in sim.firms.id_to_row:
                self.loss_exposed_firms.add(owner)
            asset_id = f"{owner}:shares:{bank}"
            asset = sim.ledger.accounts.get(asset_id) or Account(
                asset_id, owner, AccountKind.ASSET, "shares", True, bank, issue_id
            )
            expense = Account(
                f"{owner}:deposit_conversion_loss",
                owner,
                AccountKind.EXPENSE,
                "deposit_conversion_loss",
            )
            gain = Account(
                f"{bank}:deposit_conversion_gain",
                bank,
                AccountKind.INCOME,
                "deposit_conversion_gain",
            )
            sim.ledger.post(
                Transaction(
                    f"w{sim.week}:convert:{bank}:{owner}",
                    sim.week,
                    "crisis",
                    "Conversione deposito in quote",
                    (
                        change(sim.ledger.accounts[dep.asset], -amount),
                        change(asset, value),
                        change(expense, loss),
                        change(sim.ledger.accounts[dep.liability], -amount),
                        change(sim.ledger.accounts[issue.capital_account], value),
                        change(gain, loss),
                    ),
                ),
                new_accounts=tuple(
                    a for a in (asset, expense, gain) if a.id not in sim.ledger.accounts
                ),
            )
            for position, existing in enumerate(holdings):
                if existing.issue_id == issue_id and existing.owner_id == owner:
                    holdings[position] = existing.model_copy(update={"quantity": quantity})
                    break
            else:
                holdings.append(
                    ShareHolding(
                        issue_id=issue_id, owner_id=owner, quantity=quantity, asset_account=asset_id
                    )
                )
        sim.share_holdings = tuple(holdings)
        sim._share_issues[issue_id] = issue.model_copy(
            update={"total_shares": new_shares, "last_issue_price": money(target / new_shares)}
        )
        self.flows["deposit_haircuts"] += haircut - target
        self.resolved_banks.add(bank)
        self.resolved_this_week.add(bank)
        sim.events.append(f"bank_resolved:{bank}:converted={haircut}:new_equity={target}")
        if sim.ledger.balance_sheets()[bank]["equity"] != target:
            raise ValueError("Patrimonio della banca non riconciliato dopo conversione")
        remaining_deposits = sum(
            (
                sim.ledger.balance(dep.liability)
                for dep in sim.deposits.values()
                if dep.bank_id == bank
            ),
            ZERO,
        )
        required_liquidity = money(
            remaining_deposits * Decimal(str(sim.config.banks.expected_outflow_share))
        )
        reserve = sim.reserves[bank].asset
        shortfall = required_liquidity - sim.ledger.available(reserve)
        if shortfall > ZERO:
            sim.finance.refinance(bank, shortfall)
        if sim.ledger.available(reserve) < required_liquidity:
            sim.events.append(f"bank_liquidity_unresolved:{bank}")
            sim.status = "TERMINATED"
            return False
        return True

    def start_liquidation(self, entity):
        sim = self.sim
        if entity in self.liquidations:
            return
        self.liquidations[entity] = sim.week
        if entity in sim.firms.id_to_row:
            active = sim.firms.column("active").copy()
            active[sim.firms.id_to_row[entity]] = False
            sim.firms.replace_column("active", active)
            employers = sim.people.column("employer_id").copy()
            for person, contract in list(sim.employment.items()):
                if contract.employer_id == entity:
                    del sim.employment[person]
                    employers[sim.people.id_to_row[person]] = -1
            sim.people.replace_column("employer_id", employers)
        else:
            self.defaulted_people.add(entity)
        sim.events.append(f"liquidation_started:{entity}")

    @money_context
    def _cure_arrears(self, loan_id):
        sim = self.sim
        loan = sim.loans[loan_id]
        due = loan.arrears
        if due <= ZERO:
            return
        dep = sim.deposits[loan.borrower_id]
        if sim.ledger.available(dep.asset) < due:
            return
        try:
            reserve_lines = sim.settlement._reserve_transfer_lines(dep.bank_id, loan.bank_id, due)
        except SettlementError as exc:
            if exc.code == "bank_settlement_failure":
                return
            raise
        expense = Account(
            f"{loan.borrower_id}:loan_interest",
            loan.borrower_id,
            AccountKind.EXPENSE,
            "loan_interest",
        )
        income = Account(
            f"{loan.bank_id}:loan_interest", loan.bank_id, AccountKind.INCOME, "loan_interest"
        )
        sim.ledger.post(
            Transaction(
                f"w{sim.week}:arrears-cure:{loan_id}",
                sim.week,
                "crisis",
                "Arretrati sanati entro la chiusura",
                (
                    change(sim.ledger.accounts[dep.asset], -due),
                    change(expense, due),
                    change(sim.ledger.accounts[dep.liability], -due),
                    change(income, due),
                    *reserve_lines,
                ),
            ),
            new_accounts=tuple(a for a in (expense, income) if a.id not in sim.ledger.accounts),
        )
        sim._loans[loan_id] = loan.model_copy(
            update={"arrears": ZERO, "arrears_weeks": 0, "status": "performing"}
        )
        sim.finance.flows["loan_interest"] += due
        sim.events.append(f"arrears_cured:{loan_id}")

    @money_context
    def _sell_installed_capital(self, seller, buyer, quantity, price):
        sim = self.sim
        tx_id = f"w{sim.week}:liquidation:installed:{seller}:{buyer}"
        value = sim.inventory.carrying(seller, 11, quantity, "installed_capital")
        total = money(Decimal(str(quantity)) * price)
        pending = Account(
            f"{buyer}:pending_capital",
            buyer,
            AccountKind.ASSET,
            "pending_capital",
            True,
            instrument_id="11",
        )
        revenue = Account(
            f"{seller}:liquidation_revenue", seller, AccountKind.INCOME, "liquidation_revenue"
        )
        cost = Account(
            f"{seller}:liquidation_cost", seller, AccountKind.EXPENSE, "liquidation_cost"
        )
        lines = sim.settlement._payment_lines(buyer, seller, total)
        lines.extend(
            (
                change(pending, total),
                change(revenue, total),
                change(cost, value),
                change(sim.ledger.accounts[f"{seller}:installed_capital"], -value),
            )
        )
        entries = (
            PhysicalEntry(
                tx_id,
                sim.week,
                "crisis",
                "Liquidazione capitale",
                seller,
                11,
                -quantity,
                "installed_capital",
            ),
            PhysicalEntry(
                tx_id,
                sim.week,
                "crisis",
                "Liquidazione capitale",
                buyer,
                11,
                quantity,
                "pending_capital",
            ),
        )
        physical = sim.physical.prepare(entries)
        sim.ledger.post(
            Transaction(tx_id, sim.week, "crisis", "Realizzo di capitale installato", tuple(lines)),
            new_accounts=tuple(
                a for a in (pending, revenue, cost) if a.id not in sim.ledger.accounts
            ),
        )
        sim.physical._commit_prepared(entries, physical)
        return total

    @money_context
    def _liquidate_assets(self, firm):
        sim = self.sim
        cfg = sim.config.crisis_investment
        # Una sessione distinta: solo imprese che usano l'input o il bene capitale.
        # Il prezzo scontato è pagato con depositi e regolamento di riserve reale.
        from economic_sim.markets.goods import affordable_quantity

        for product, stock in [
            *((p, "inventory") for p in range(8, 12)),
            (11, "installed_capital"),
        ]:
            quantity = sim.physical.quantity(firm, product, stock)
            if quantity <= 0 or product <= 7:
                continue
            buyers = []
            for buyer in map(int, sim.firms.ids):
                if buyer == firm or not sim.firms.column("active")[sim.firms.id_to_row[buyer]]:
                    continue
                output_product = sim.products[
                    int(sim.firms.column("product_id")[sim.firms.id_to_row[buyer]]) - 1
                ]
                row = sim.firms.id_to_row[buyer]
                if product == 11:
                    demand = max(
                        0.0,
                        sim.investment_targets[row]
                        - sim.physical.quantity(buyer, 11, "pending_capital"),
                    )
                else:
                    coefficient = output_product.recipe.get(sim.products[product - 1].name, 0.0)
                    demand = max(
                        0.0,
                        coefficient
                        * sim.production_targets[row]
                        * sim.config.real_economy.input_target_weeks
                        - sim.physical.available(buyer, product),
                    )
                if demand > 0:
                    buyers.append((buyer, demand))
            price = money(
                max(
                    sim.config.real_economy.price_floor,
                    money(str(sim.reference_prices[product - 1]))
                    * Decimal(str(cfg.liquidation_discount)),
                )
            )
            for buyer, demand in buyers:
                budget = sim.ledger.available(sim.deposits[buyer].asset)
                take = min(quantity, demand, float(budget / price))
                if take <= 0:
                    continue
                take = affordable_quantity(take, price, budget)
                if take <= 0:
                    continue
                try:
                    if stock == "installed_capital":
                        realized = self._sell_installed_capital(firm, buyer, take, price)
                    else:
                        sim.settlement.purchase(
                            f"w{sim.week}:liquidation:{firm}:{product}:{buyer}",
                            buyer,
                            firm,
                            product,
                            take,
                            price,
                            sim.physical,
                            week=sim.week,
                            destination="pending_capital" if product == 11 else "inventory",
                        )
                        realized = money(Decimal(str(take)) * price)
                except SettlementError as exc:
                    if exc.code not in {"bank_settlement_failure", "insufficient_customer_funds"}:
                        raise
                    continue
                self.flows["liquidation_recoveries"] += realized
                self.asset_proceeds[firm] = self.asset_proceeds.get(firm, ZERO) + realized
                if product == 11 and stock == "inventory":
                    self.flows["liquidation_capital_investment"] += realized
                sim.events.append(
                    f"liquidation_sale:{firm}:{product}:{stock}:{buyer}:quantity={take}:price={price}:paid={realized}"
                )
                quantity = sim.physical.quantity(firm, product, stock)
                if quantity <= 0:
                    break

    @money_context
    def _transfer_share_in_kind(
        self, estate, issue_id, recipient, quantity, value, *, loan_id=None
    ):
        sim = self.sim
        issuer = sim.share_issues[issue_id].issuer_id
        source_id = f"{estate}:shares:{issuer}"
        target_id = f"{recipient}:shares:{issuer}"
        target = sim.ledger.accounts.get(target_id) or Account(
            target_id, recipient, AccountKind.ASSET, "shares", True, issuer, issue_id
        )
        lines = [change(sim.ledger.accounts[source_id], -value), change(target, value)]
        additions = [target] if target_id not in sim.ledger.accounts else []
        if loan_id is not None:
            loan = sim.loans[loan_id]
            if loan.bank_id != recipient or value > sim.ledger.balance(loan.debt_account):
                raise ValueError("Recupero in natura oltre il credito")
            lines.extend(
                (
                    change(sim.ledger.accounts[loan.debt_account], -value),
                    change(sim.ledger.accounts[loan.asset_account], -value),
                )
            )
        else:
            expense = Account(
                f"{estate}:in_kind_distribution",
                estate,
                AccountKind.EXPENSE,
                "in_kind_distribution",
            )
            income = Account(
                f"{recipient}:in_kind_recovery", recipient, AccountKind.INCOME, "in_kind_recovery"
            )
            lines.extend((change(expense, value), change(income, value)))
            additions.extend(a for a in (expense, income) if a.id not in sim.ledger.accounts)
        tx_id = f"w{sim.week}:in-kind:{estate}:{issue_id}:{recipient}:{len(sim.ledger._journal)}"
        sim.ledger.post(
            Transaction(tx_id, sim.week, "crisis", "Trasferimento quote in natura", tuple(lines)),
            new_accounts=tuple(additions),
        )
        holdings = list(sim.share_holdings)
        found_recipient = False
        for index, holding in enumerate(holdings):
            if holding.issue_id == issue_id and holding.owner_id == estate:
                holdings[index] = holding.model_copy(
                    update={"quantity": holding.quantity - quantity}
                )
            if holding.issue_id == issue_id and holding.owner_id == recipient:
                holdings[index] = holding.model_copy(
                    update={"quantity": holding.quantity + quantity}
                )
                found_recipient = True
        if not found_recipient:
            holdings.append(
                ShareHolding(
                    issue_id=issue_id,
                    owner_id=recipient,
                    quantity=quantity,
                    asset_account=target_id,
                )
            )
        sim.share_holdings = tuple(holdings)
        if loan_id is not None and sim.ledger.balance(sim.loans[loan_id].debt_account) == ZERO:
            sim._loans[loan_id] = sim.loans[loan_id].model_copy(update={"status": "closed"})
        sim.events.append(
            f"in_kind_share_transfer:{estate}:{issue_id}:{recipient}:quantity={quantity}:value={value}"
        )

    @money_context
    def _distribute_share_assets(self, estate, loan_ids):
        sim = self.sim
        estate_issue = sim.share_issues[f"shares:{estate}"]
        owners = sorted(
            (h for h in sim.share_holdings if h.issue_id == estate_issue.id and h.quantity),
            key=lambda h: h.owner_id,
        )
        for initial in list(sim.share_holdings):
            if (
                initial.owner_id != estate
                or initial.issue_id == estate_issue.id
                or not initial.quantity
            ):
                continue
            issue_id = initial.issue_id
            for loan_id in loan_ids:
                holding = next(
                    h for h in sim.share_holdings if h.issue_id == issue_id and h.owner_id == estate
                )
                if not holding.quantity:
                    break
                debt = sim.ledger.balance(sim.loans[loan_id].debt_account)
                if not debt:
                    continue
                carrying = sim.ledger.balance(holding.asset_account)
                if carrying:
                    desired = min(carrying, debt)
                    quantity = min(
                        holding.quantity,
                        (holding.quantity * desired / carrying).quantize(
                            QUANTUM, rounding=ROUND_DOWN
                        ),
                    )
                    if not quantity:
                        continue
                    value = (
                        carrying
                        if quantity == holding.quantity
                        else (carrying * quantity / holding.quantity).quantize(
                            QUANTUM, rounding=ROUND_DOWN
                        )
                    )
                else:
                    quantity, value = holding.quantity, ZERO
                self._transfer_share_in_kind(
                    estate, issue_id, sim.loans[loan_id].bank_id, quantity, value, loan_id=loan_id
                )
            holding = next(
                h for h in sim.share_holdings if h.issue_id == issue_id and h.owner_id == estate
            )
            if not holding.quantity or not owners:
                continue
            total_quantity = holding.quantity
            total_value = sim.ledger.balance(holding.asset_account)
            remaining_quantity, remaining_value = total_quantity, total_value
            for index, owner in enumerate(owners):
                if index == len(owners) - 1:
                    quantity, value = remaining_quantity, remaining_value
                else:
                    quantity = min(
                        remaining_quantity,
                        (total_quantity * owner.quantity / estate_issue.total_shares).quantize(
                            QUANTUM, rounding=ROUND_DOWN
                        ),
                    )
                    value = min(
                        remaining_value,
                        (total_value * owner.quantity / estate_issue.total_shares).quantize(
                            QUANTUM, rounding=ROUND_DOWN
                        ),
                    )
                remaining_quantity -= quantity
                remaining_value -= value
                if quantity:
                    self._transfer_share_in_kind(estate, issue_id, owner.owner_id, quantity, value)

    @money_context
    def _close_liquidation(self, entity):
        sim = self.sim
        # La cassa estingue prima imposte arretrate e poi crediti, senza recupero virtuale.
        due = sim.treasury.tax_due.get(entity, (0, ZERO))[1]
        if due:
            paid = min(due, sim.ledger.available(sim.deposits[entity].asset))
            if paid:
                treasury = sim.treasury
                treasury._post(
                    f"tax:liquidation:{sim.week}:{entity}",
                    "crisis",
                    "Imposta in liquidazione",
                    [
                        *treasury._cash_lines(entity, paid, into_treasury=True),
                        change(sim.ledger.accounts[f"{entity}:profit_tax_payable"], -paid),
                        change(
                            sim.ledger.accounts[f"{sim.government.id}:tax_receivable:{entity}"],
                            -paid,
                        ),
                    ],
                )
                treasury.tax_due[entity] = (sim.week + 1, due - paid)
                if due == paid:
                    del treasury.tax_due[entity]
                    treasury.tax_arrears.pop(entity, None)
                else:
                    treasury.tax_arrears[entity] = due - paid
                self.flows["liquidation_recoveries"] += paid
            unpaid = sim.treasury.tax_due.get(entity, (0, ZERO))[1]
            if unpaid:
                gov = sim.government.id
                self._post(
                    f"w{sim.week}:tax-writeoff:{entity}",
                    "Imposta inesigibile",
                    [
                        (entity, "profit_tax_payable", AccountKind.LIABILITY, -unpaid),
                        (entity, "tax_forgiveness", AccountKind.INCOME, unpaid),
                        (gov, f"tax_receivable:{entity}", AccountKind.ASSET, -unpaid),
                        (gov, "tax_loss", AccountKind.EXPENSE, unpaid),
                    ],
                )
                sim.treasury.tax_due.pop(entity, None)
                sim.treasury.tax_arrears.pop(entity, None)
        loans = {
            loan_id: loan
            for loan_id, loan in sorted(sim.loans.items())
            if loan.borrower_id == entity and sim.ledger.balance(loan.debt_account) > ZERO
        }

        def distribute(claims, budget):
            total = sum(claims.values(), ZERO)
            budget = min(budget, total)
            if not total or not budget:
                return {}
            result = {
                key: min(claim, (budget * claim / total).quantize(QUANTUM, rounding=ROUND_DOWN))
                for key, claim in claims.items()
            }
            residual = budget - sum(result.values(), ZERO)
            for key in sorted(claims):
                if residual <= ZERO:
                    break
                extra = min(residual, claims[key] - result[key])
                result[key] += extra
                residual -= extra
            return result

        cash = sim.ledger.available(sim.deposits[entity].asset)
        secured_claims = {
            loan_id: min(sim.ledger.balance(loan.debt_account), loan.collateral_value)
            for loan_id, loan in loans.items()
            if loan.collateral_value > ZERO
        }
        secured = distribute(secured_claims, min(cash, self.asset_proceeds.get(entity, ZERO)))
        unsecured_claims = {
            loan_id: sim.ledger.balance(loan.debt_account) - secured.get(loan_id, ZERO)
            for loan_id, loan in loans.items()
        }
        unsecured = distribute(unsecured_claims, cash - sum(secured.values(), ZERO))
        for loan_id in loans:
            payment = secured.get(loan_id, ZERO) + unsecured.get(loan_id, ZERO)
            if payment:
                try:
                    sim.settlement.repay_loan(
                        f"w{sim.week}:liquidation-repay:{loan_id}", loan_id, payment, week=sim.week
                    )
                except SettlementError as exc:
                    if exc.code not in {"bank_settlement_failure", "insufficient_customer_funds"}:
                        raise
                    sim.status = "TERMINATED"
                    sim.events.append(f"liquidation_settlement_failed:{entity}:{loan_id}")
                    return
                self.flows["liquidation_recoveries"] += payment
        if entity in sim.firms.id_to_row:
            self._distribute_share_assets(entity, loans)
        for loan_id in loans:
            if sim.ledger.balance(sim.loans[loan_id].debt_account) > ZERO:
                self.write_down_loan(loan_id)
        if entity in sim.firms.id_to_row:
            for stock in ("inventory", "pending_capital", "installed_capital"):
                products = range(1, 12) if stock == "inventory" else (11,)
                for product in products:
                    quantity = sim.physical.quantity(entity, product, stock)
                    if quantity:
                        loss = sim.inventory.consume(
                            f"w{sim.week}:liquidation-discard:{entity}:{stock}:{product}",
                            entity,
                            product,
                            quantity,
                            reason="liquidation_loss",
                            stock=stock,
                        )
                        if stock == "inventory":
                            self.flows["liquidation_inventory_loss"] += loss
            issue = sim.share_issues[f"shares:{entity}"]
            residual = sim.ledger.available(sim.deposits[entity].asset)
            if residual and issue.total_shares:
                holders = sorted(
                    (h for h in sim.share_holdings if h.issue_id == issue.id and h.quantity),
                    key=lambda h: h.owner_id,
                )
                remaining = residual
                for index, holding in enumerate(holders):
                    amount = (
                        remaining
                        if index == len(holders) - 1
                        else money(residual * holding.quantity / issue.total_shares)
                    )
                    remaining -= amount
                    if amount <= ZERO:
                        continue
                    try:
                        lines = sim.settlement._payment_lines(entity, holding.owner_id, amount)
                    except SettlementError as exc:
                        if exc.code == "bank_settlement_failure":
                            sim.status = "TERMINATED"
                            sim.events.append(f"liquidation_settlement_failed:{entity}")
                            return
                        raise
                    expense = Account(
                        f"{entity}:liquidation_distribution",
                        entity,
                        AccountKind.EXPENSE,
                        "liquidation_distribution",
                    )
                    income = Account(
                        f"{holding.owner_id}:liquidation_recovery",
                        holding.owner_id,
                        AccountKind.INCOME,
                        "liquidation_recovery",
                    )
                    sim.ledger.post(
                        Transaction(
                            f"w{sim.week}:liquidation-share-payout:{entity}:{holding.owner_id}",
                            sim.week,
                            "crisis",
                            "Residuo ai soci",
                            tuple([*lines, change(expense, amount), change(income, amount)]),
                        ),
                        new_accounts=tuple(
                            a for a in (expense, income) if a.id not in sim.ledger.accounts
                        ),
                    )
            for holding in (h for h in sim.share_holdings if h.issue_id == issue.id):
                value = sim.ledger.balance(holding.asset_account)
                if value:
                    self._post(
                        f"w{sim.week}:firm-share-loss:{entity}:{holding.owner_id}",
                        "Svalutazione quote",
                        [
                            (holding.owner_id, f"shares:{entity}", AccountKind.ASSET, -value),
                            (holding.owner_id, "share_loss", AccountKind.EXPENSE, value),
                        ],
                    )
            capital = sim.ledger.balance(issue.capital_account)
            if capital:
                self._post(
                    f"w{sim.week}:firm-capital-close:{entity}",
                    "Storno capitale liquidato",
                    [
                        (entity, "share_capital", AccountKind.EQUITY, -capital),
                        (entity, "liquidation_gain", AccountKind.INCOME, capital),
                    ],
                )
            sim.share_holdings = tuple(
                h.model_copy(update={"quantity": ZERO}) if h.issue_id == issue.id else h
                for h in sim.share_holdings
            )
            sim._share_issues[issue.id] = issue.model_copy(update={"total_shares": ZERO})
        sim.events.append(f"liquidation_closed:{entity}")
        self.closed_liquidations.add(entity)

    @money_context
    def run(self):
        sim = self.sim
        self.open_week()
        # Un arretrato saldato durante la settimana non incrementa il contatore.
        for loan_id, loan in sorted(sim.loans.items()):
            if loan.status not in {"performing", "arrears"}:
                continue
            self._cure_arrears(loan_id)
            loan = sim.loans[loan_id]
            weeks = loan.arrears_weeks + 1 if loan.arrears > ZERO else 0
            sim._loans[loan_id] = loan.model_copy(update={"arrears_weeks": weeks})
            if weeks >= sim.config.banks.arrears_grace_weeks:
                self.start_liquidation(loan.borrower_id)
        for entity in [*map(int, sim.firms.ids), *map(int, sim.banks.ids)]:
            weeks = (
                self.tax_arrears_weeks.get(entity, 0) + 1
                if sim.treasury.tax_arrears.get(entity, ZERO)
                else 0
            )
            self.tax_arrears_weeks[entity] = weeks
            if weeks >= sim.config.banks.arrears_grace_weeks and entity in sim.firms.id_to_row:
                self.start_liquidation(entity)
        for entity, start in sorted(self.liquidations.items()):
            if entity in self.closed_liquidations:
                continue
            if entity in sim.firms.id_to_row:
                self._liquidate_assets(entity)
            if sim.week - start + 1 >= sim.config.crisis_investment.liquidation_weeks:
                self._close_liquidation(entity)
                if sim.status == "TERMINATED":
                    return
        # Le perdite possono propagarsi da crediti a banche e da depositi a imprese.
        for _ in range(len(sim.banks.ids) + len(sim.firms.ids) + 1):
            changed = False
            sheets = sim.ledger.balance_sheets()
            for bank in map(int, sim.banks.ids):
                own_shares = self.own_share_value(bank)
                if (
                    sheets[bank]["equity"] - own_shares < ZERO
                    and bank not in self.resolved_this_week
                ):
                    if not self.resolve_bank(bank):
                        return
                    changed = True
            for firm in sorted(self.loss_exposed_firms):
                if (
                    firm not in self.liquidations
                    and sim.ledger.balance_sheets()[firm]["equity"] < ZERO
                ):
                    self.start_liquidation(firm)
                    changed = True
            if not changed:
                return
        raise ValueError("Risoluzione bancaria senza punto fisso")
