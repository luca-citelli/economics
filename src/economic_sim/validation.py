from collections import defaultdict

import numpy as np

from economic_sim.accounting.ledger import AccountingError, AccountKind
from economic_sim.money import ZERO, money_context


def require(condition, message):
    if not condition:
        raise AccountingError(message)


@money_context
def validate_state(sim, *, full=True):
    ledger = sim.ledger
    ledger.validate(full=full)
    sim.physical.validate(full=full)
    entity_ids = {sim.government.id, sim.central_bank.id}
    for table in (sim.people, sim.firms, sim.banks):
        require(not entity_ids.intersection(table.ids.tolist()), "ID globali duplicati")
        entity_ids.update(table.ids.tolist())
        require(
            table.id_to_row == {int(i): row for row, i in enumerate(table.ids)},
            "Mapping ID/row incoerente",
        )
        for name, dtype in table.schema.items():
            column = table.column(name)
            require(
                column.shape == (len(table.ids), *table.trailing_shapes.get(name, ()))
                and column.dtype == dtype,
                f"Layout errato: {name}",
            )
            require(np.isfinite(column).all(), f"Colonna non finita: {name}")
    require(set(ledger.balance_sheets()) == entity_ids, "Conti/entità orfani")
    require(
        set(sim.deposits) == set(sim.people.ids) | set(sim.firms.ids), "Depositi mancanti o orfani"
    )
    require(set(sim.reserves) == set(sim.banks.ids), "Conti di riserva mancanti")
    require(
        set(sim.physical.entity_ids) == set(sim.people.ids) | set(sim.firms.ids),
        "Registro fisico con entità mancanti o orfane",
    )
    require(set(sim.physical.product_ids) == set(range(1, 12)), "Registro prodotti errato")

    # Ogni strumento finanziario ha una coppia identificabile, mai solo un totale globale.
    mirrors = defaultdict(list)
    for account in ledger.accounts.values():
        require(account.entity_id in entity_ids, "Entità contabile inesistente")
        if account.purpose in {"deposit", "reserve", "treasury", "loan", "bond"}:
            require(account.instrument_id is not None, "Strumento finanziario senza ID")
            mirrors[account.purpose, account.instrument_id].append(account)
    for key, pair in mirrors.items():
        assets = [a for a in pair if a.kind == AccountKind.ASSET]
        liabilities = [a for a in pair if a.kind == AccountKind.LIABILITY]
        require(len(assets) == len(liabilities) == 1, f"Controparti mancanti: {key}")
        a, liability = assets[0], liabilities[0]
        require(
            a.entity_id == liability.counterparty_id and liability.entity_id == a.counterparty_id,
            f"Controparti errate: {key}",
        )
        require(
            ledger.balance(a.id) == ledger.balance(liability.id),
            f"Strumento non riconciliato: {key}",
        )
    for table in (sim.people, sim.firms):
        for entity, bank in zip(table.ids, table.column("bank_id"), strict=True):
            account = sim.deposits[int(entity)]
            require(
                account.owner_id == entity and account.bank_id == bank,
                "Collegamento deposito/cliente errato",
            )
            require(
                ledger.accounts[account.asset].entity_id == entity
                and ledger.accounts[account.liability].entity_id == bank,
                "Conti deposito intestati a entità errate",
            )
    for loan in sim.loans.values():
        require(
            loan.borrower_id in sim.deposits and loan.bank_id in sim.reserves, "Prestito orfano"
        )
        require(
            ledger.balance(loan.asset_account) == ledger.balance(loan.debt_account),
            "Prestito non riconciliato",
        )
        require(
            ledger.accounts[loan.asset_account].entity_id == loan.bank_id
            and ledger.accounts[loan.asset_account].instrument_id == loan.id
            and ledger.accounts[loan.debt_account].entity_id == loan.borrower_id
            and ledger.accounts[loan.debt_account].instrument_id == loan.id,
            "Conti/contratto di prestito non collegati",
        )
    require(
        len([k for k in mirrors if k[0] == "loan"]) == len(sim.loans), "Prestito senza contratto"
    )
    for bond in sim.bonds.values():
        require(bond.issuer_id == sim.government.id, "Emittente bond errato")
        require(bond.holder_id in entity_ids, "Detentore bond inesistente")
        require(
            ledger.balance(bond.asset_account) == ledger.balance(bond.liability_account),
            "Bond non riconciliato",
        )
        require(
            ledger.accounts[bond.asset_account].entity_id == bond.holder_id
            and ledger.accounts[bond.asset_account].instrument_id == bond.id
            and ledger.accounts[bond.liability_account].entity_id == bond.issuer_id
            and ledger.accounts[bond.liability_account].instrument_id == bond.id,
            "Conti/contratto bond non collegati",
        )
    require(len([k for k in mirrors if k[0] == "bond"]) == len(sim.bonds), "Bond senza contratto")
    if hasattr(sim, "treasury"):
        for entity in [*map(int, sim.firms.ids), *map(int, sim.banks.ids)]:
            due = sim.treasury.tax_due.get(entity, (0, ZERO))[1]
            payable = f"{entity}:profit_tax_payable"
            receivable = f"{sim.government.id}:tax_receivable:{entity}"
            require(
                (ledger.balance(payable) if payable in ledger.accounts else ZERO) == due
                and (ledger.balance(receivable) if receivable in ledger.accounts else ZERO) == due,
                "Debito e credito tributario non riconciliati",
            )
    for holding in sim.share_holdings:
        require(
            holding.issue_id in sim.share_issues and holding.owner_id in entity_ids,
            "Quota orfana",
        )
        require(
            ledger.accounts[holding.asset_account].entity_id == holding.owner_id,
            "Proprietario quote errato",
        )
        require(
            ledger.accounts[holding.asset_account].purpose == "shares"
            and ledger.accounts[holding.asset_account].instrument_id == holding.issue_id,
            "Conto quote non collegato all'emissione",
        )
    require(
        {h.asset_account for h in sim.share_holdings}
        == {a.id for a in ledger.accounts.values() if a.purpose == "shares"},
        "Conto di partecipazione orfano",
    )
    require(
        {issue.issuer_id for issue in sim.share_issues.values()}
        == set(sim.firms.ids) | set(sim.banks.ids),
        "Emittente senza quote iniziali",
    )
    for issue in sim.share_issues.values():
        require(
            ledger.accounts[issue.capital_account].entity_id == issue.issuer_id
            and ledger.accounts[issue.capital_account].instrument_id == issue.id,
            "Capitale emittente non collegato",
        )
        holdings = [h for h in sim.share_holdings if h.issue_id == issue.id]
        require(
            len({h.owner_id for h in holdings}) == len(holdings), "Quote duplicate per proprietario"
        )
        require(
            sum((h.quantity for h in holdings), ZERO) == issue.total_shares,
            "Totale quote non riconciliato",
        )
        # Costo storico di sottoscrizione, distinto da patrimonio corrente e prezzo di mercato.
        require(
            sum((ledger.balance(h.asset_account) for h in holdings), ZERO)
            == ledger.balance(issue.capital_account),
            "Capitale sottoscritto non riconciliato",
        )
    for entity in sim.physical.entity_ids:
        for product in sim.physical.product_ids:
            quantity = sim.physical.quantity(int(entity), int(product))
            aid = f"{entity}:inventory:{product}"
            value = ledger.balance(aid) if aid in ledger.accounts else ZERO
            require(quantity > 0 or value == ZERO, "Valore di inventario senza quantità")
            require(quantity == 0 or aid in ledger.accounts, "Inventario senza conto di costo")
    for firm in sim.firms.ids:
        capital = sim.physical.quantity(int(firm), 11, "installed_capital")
        capital_value = ledger.balance(f"{firm}:installed_capital")
        require(capital > 0 or capital_value == ZERO, "Valore di capitale senza quantità")
    require(sim.people.column("needs").shape == (len(sim.people.ids), 11), "Shape bisogni errata")
    require((sim.people.column("needs") >= 0).all(), "Bisogni negativi")
    require(set(sim.firms.column("product_id")) == set(range(1, 12)), "Filiera incompleta")
    require(set(sim.people.column("employer_id")) <= {-1, *sim.firms.ids}, "Datore inesistente")
    require((sim.people.column("age_weeks") >= 18 * 52).all(), "Popolazione non adulta")
    for name in ("saving_propensity", "risk_propensity", "quality_propensity"):
        values = sim.people.column(name)
        require(((values >= 0) & (values <= 1)).all(), "Propensione fuori range")
    for values in (sim.people.column("satisfaction"), sim.firms.column("reputation")):
        require(((values >= 0) & (values <= 1)).all(), "Soddisfazione/reputazione fuori range")
    employers = sim.people.column("employer_id")
    for row, person in enumerate(sim.people.ids):
        contract = sim.employment.get(int(person))
        employer = employers[row]
        require(
            employer == (contract.employer_id if contract else -1), "Contratto/impiego incoerente"
        )
        if contract:
            require(
                contract.person_id == person
                and (contract.last_paid_week == sim.week or sim.status == "TERMINATED"),
                "Lavoro non pagato nella settimana",
            )
    for firm in sim.firms.ids:
        pending = sim.physical.quantity(int(firm), 11, "pending_capital")
        pending_account = f"{firm}:pending_capital"
        pending_value = (
            ledger.balance(pending_account) if pending_account in ledger.accounts else ZERO
        )
        require(pending > 0 or pending_value == ZERO, "Capitale pendente senza quantità")
        require(pending == 0 or pending_account in ledger.accounts, "Capitale pendente senza costo")
        work = f"{firm}:work_in_progress"
        require(work not in ledger.accounts or ledger.balance(work) == ZERO, "Salari non allocati")
