"""Candidature a turni, contratti persistenti e lavoro soltanto dopo la paga."""

from collections import defaultdict
from dataclasses import dataclass, replace
from decimal import Decimal

import numpy as np

from economic_sim.accounting.settlement import SettlementError
from economic_sim.agents.firms import affordable_jobs
from economic_sim.agents.state import NO_ID
from economic_sim.money import ZERO, money, money_context


@dataclass(frozen=True)
class Employment:
    person_id: int
    employer_id: int
    wage: Decimal
    start_week: int
    review_week: int
    last_paid_week: int = 0


@money_context
def match_and_pay(sim):
    people, firms, cfg = sim.people, sim.firms, sim.config.real_economy
    needs = people.column("needs")
    unemployment = people.column("unemployment_weeks")
    active = people.column("active")
    reservation = np.maximum(
        float(cfg.wage_floor),
        (needs[:, :3] * sim.reference_prices[:3]).sum(axis=1)
        * cfg.reservation_primary_multiple
        * np.maximum(cfg.reservation_min_fraction, (1 - cfg.reservation_decay) ** unemployment),
    )
    people.replace_column("reservation_wage", reservation)
    offered = [money(str(x)) for x in firms.column("offered_wage")]
    reservation_money = [money(str(x)) for x in reservation]
    planned = firms.column("planned_workers").copy()
    contracts = sim.employment
    by_firm = defaultdict(list)
    for person, contract in sorted(contracts.items()):
        by_firm[contract.employer_id].append(person)
    # Prima riduzioni/revisioni; nessuno lascia spontaneamente un contratto non in revisione.
    for row, firm_id in enumerate(firms.ids):
        firm = int(firm_id)
        retained = []
        for person in by_firm[firm]:
            contract = contracts[person]
            if sim.week >= contract.review_week:
                if offered[row] < reservation_money[people.id_to_row[person]]:
                    del contracts[person]
                    continue
                contracts[person] = replace(
                    contract, wage=offered[row], review_week=sim.week + cfg.contract_review_weeks
                )
            retained.append(person)
        retained_wages = [contracts[p].wage for p in retained[: planned[row]]]
        desired_wages = retained_wages + [offered[row]] * max(0, planned[row] - len(retained_wages))
        count = affordable_jobs(sim, row, desired_wages)
        planned[row] = count
        for person in retained[count:]:
            del contracts[person]
    firms.replace_column("planned_workers", planned)
    vacancies = planned.copy()
    for contract in contracts.values():
        vacancies[firms.id_to_row[contract.employer_id]] -= 1
    applications = np.zeros(len(firms.ids), dtype=np.int64)
    tried = defaultdict(set)
    new_wages = []
    while True:
        candidates = defaultdict(list)
        for row, person_id in enumerate(people.ids):
            person = int(person_id)
            if person in contracts or not active[row]:
                continue
            eligible = [
                r
                for r in np.flatnonzero(vacancies > 0)
                if int(r) not in tried[person] and offered[r] >= reservation_money[row]
            ]
            if eligible:
                best = min(eligible, key=lambda r: (-offered[r], int(firms.ids[r])))
                tried[person].add(int(best))
                candidates[int(best)].append(person)
        if not candidates:
            break
        for row in sorted(candidates):
            applicants = candidates[row]
            applications[row] += len(applicants)
            for person in sim.rng["labor"].permutation(applicants)[: vacancies[row]]:
                person = int(person)
                contracts[person] = Employment(
                    person,
                    int(firms.ids[row]),
                    offered[row],
                    sim.week,
                    sim.week + cfg.contract_review_weeks,
                )
                new_wages.append(offered[row])
                vacancies[row] -= 1
    income = np.zeros(len(people.ids))
    employers = np.full(len(people.ids), NO_ID, dtype=np.int64)
    paid = np.zeros(len(firms.ids), dtype=np.int64)
    wage_bill = ZERO
    net_wage_bill = ZERO
    for person, contract in sorted(list(contracts.items())):
        if contract.last_paid_week >= sim.week:
            raise ValueError("Salario già pagato nella settimana")
        try:
            if sim.config.execution.profile == "fiscal_economy":
                net = sim.treasury.pay_wage(
                    f"w{sim.week}:wage:{person}", contract.employer_id, person, contract.wage
                )
            else:
                sim.settlement.pay_wage(
                    f"w{sim.week}:wage:{person}",
                    contract.employer_id,
                    person,
                    contract.wage,
                    week=sim.week,
                )
                net = contract.wage
        except SettlementError as exc:
            if exc.code not in {"bank_settlement_failure", "insufficient_customer_funds"}:
                raise
            del contracts[person]
            sim.events.append(f"labor_suspended:{person}:{exc.code}")
            continue
        contracts[person] = replace(contract, last_paid_week=sim.week)
        row = people.id_to_row[person]
        income[row] = float(net)
        employers[row] = contract.employer_id
        paid[firms.id_to_row[contract.employer_id]] += 1
        wage_bill += contract.wage
        net_wage_bill += net
    people.replace_column("employer_id", employers)
    people.replace_column("expected_income", 0.5 * people.column("expected_income") + 0.5 * income)
    people.replace_column("unemployment_weeks", np.where(employers == NO_ID, unemployment + 1, 0))
    firms.replace_column("previous_vacancies", planned - paid)
    firms.replace_column("previous_applications", applications)
    sim.paid_workers, sim.weekly_income = paid, income
    return {
        "wages_gross": wage_bill,
        "wages_net": net_wage_bill,
        "offered_wage_mean": float(sum(offered, ZERO) / len(offered)),
        "new_contract_wage_mean": float(sum(new_wages, ZERO) / len(new_wages))
        if new_wages
        else None,
        "employed_wage_mean": float(wage_bill / len(contracts)) if contracts else None,
        "labor_applications": int(applications.sum()),
        "vacancies": int((planned - paid).sum()),
    }
