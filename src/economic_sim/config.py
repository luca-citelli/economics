"""Configurazione rigorosa dei profili di apertura e di economia reale T02."""

from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, get_args, get_origin

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from economic_sim.money import money, money_context

Amount = Annotated[Decimal, BeforeValidator(money), Field(ge=0)]
Price = Annotated[Decimal, BeforeValidator(money), Field(gt=0)]
Fraction = Annotated[float, Field(ge=0, le=1)]
Positive = Annotated[float, Field(gt=0)]
Nonnegative = Annotated[float, Field(ge=0)]
Rate = Annotated[float, Field(gt=-1)]

PRODUCTS = (
    "food",
    "household_energy",
    "mobility",
    "clothing",
    "entertainment",
    "travel",
    "luxury",
    "wholesale_energy",
    "materials",
    "metals",
    "capital",
)
PHASES = (
    "financial_service",
    "treasury",
    "planning_credit",
    "labor_wages",
    "extraction",
    "resources",
    "production",
    "final_goods",
    "investment",
    "operating_close",
    "crisis",
    "distributions",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def strict_literals(cls, value, info):
        if isinstance(value, dict):
            value = value.copy()
            for name, field in cls.model_fields.items():
                if name in value and get_origin(field.annotation) is Literal:
                    options = get_args(field.annotation)
                    if not any(type(value[name]) is type(option) for option in options):
                        raise ValueError(f"{name}: tipo non valido per il valore letterale")
                # Il pre-validator converte il JSON in oggetti Python: ripristina
                # esplicitamente le sequenze immutabili, senza coercizioni sugli scalari.
                if (
                    info.mode == "json"
                    and name in value
                    and get_origin(field.annotation) is tuple
                    and isinstance(value[name], list)
                ):
                    value[name] = tuple(value[name])
        return value


class SimulationConfig(StrictModel):
    seed: Annotated[int, Field(ge=0, lt=2**63)]
    step_unit: Literal["week"]
    weeks_per_year: Literal[52]
    initial_population: Annotated[int, Field(ge=1, le=1_000_000)]
    initial_banks: Annotated[int, Field(ge=2, le=1000)]
    companies_per_product: Annotated[int, Field(ge=1, le=10000)]
    country_count: Literal[1]
    government_count: Literal[1]
    central_bank_count: Literal[1]
    currency: Literal["UM"]


class RuntimeConfig(StrictModel):
    start_paused: Literal[True]
    speed_presets: list[Positive]
    default_steps_per_second: Positive
    max_ui_updates_per_second: Positive
    pause_on_all_clients_disconnected: bool

    @model_validator(mode="after")
    def presets(self):
        if not self.speed_presets or len(set(self.speed_presets)) != len(self.speed_presets):
            raise ValueError("speed_presets deve contenere valori distinti")
        return self


class Features(StrictModel):
    demographics: Literal[False]
    company_entry: Literal[False]
    primary_equity_market: Literal[True]
    secondary_securities_markets: Literal[False]
    monetary_regime: Literal["fiat"]


class ExecutionConfig(StrictModel):
    profile: Literal["initialization_only", "real_economy", "monetary_economy"]
    phases: dict[str, bool]

    @model_validator(mode="after")
    def disabled(self):
        active = (
            set(REAL_PHASES)
            if self.profile == "real_economy"
            else set(MONETARY_PHASES)
            if self.profile == "monetary_economy"
            else set()
        )
        if set(self.phases) != set(PHASES) or {k for k, v in self.phases.items() if v} != active:
            raise ValueError("Fasi esplicite: future disattivate, reali coerenti con il profilo")
        return self


REAL_PHASES = (
    "planning_credit",
    "labor_wages",
    "extraction",
    "resources",
    "production",
    "final_goods",
    "investment",
    "operating_close",
)
MONETARY_PHASES = ("financial_service", *REAL_PHASES)


class RealEconomyConfig(StrictModel):
    price_demand_response: Nonnegative
    price_cost_response: Nonnegative
    price_max_log_change: Fraction
    price_floor: Price
    target_markup: Nonnegative
    cost_smoothing: Annotated[float, Field(gt=0, le=1)]
    inventory_target_weeks: Nonnegative
    input_target_weeks: Annotated[float, Field(ge=1)]
    wage_response: Fraction
    wage_max_log_change: Fraction
    wage_floor: Price
    contract_review_weeks: Annotated[int, Field(ge=1)]
    reservation_primary_multiple: Positive
    reservation_decay: Fraction
    reservation_min_fraction: Fraction
    reputation_smoothing: Fraction
    deprivation_threshold: Fraction
    investment_buffer_weeks: Nonnegative
    investment_max_growth: Fraction
    luxury_utility_scale: Positive
    cpi_basket: dict[str, Positive]

    @model_validator(mode="after")
    def basket(self):
        if set(self.cpi_basket) != set(PRODUCTS[:7]):
            raise ValueError("Paniere CPI: esattamente i sette prodotti finali")
        return self


class CentralBankConfig(StrictModel):
    reserve_rate: Rate
    policy_rate: Rate
    emergency_rate: Rate
    emergency_lending_enabled: bool
    primary_bond_purchases_enabled: bool
    weekly_bond_purchase_budget: Amount
    bond_max_price: Price

    @model_validator(mode="after")
    def corridor(self):
        if not self.reserve_rate <= self.policy_rate <= self.emergency_rate:
            raise ValueError("Richiesto reserve_rate <= policy_rate <= emergency_rate")
        if not self.primary_bond_purchases_enabled and self.weekly_bond_purchase_budget:
            raise ValueError("Budget acquisti BC incompatibile con acquisti disabilitati")
        return self


class GovernmentConfig(StrictModel):
    labor_income_tax_rate: Fraction
    profit_tax_rate: Fraction
    bond_maturity_weeks: Literal[52]
    fiscal_policy_mode: Literal["fixed_nominal_budget"]
    initial_treasury_per_person: Amount
    weekly_budget_per_person: Amount
    spending_weights: dict[str, Fraction]
    initial_bond_reference_price: Price
    max_bond_yield: Rate

    @model_validator(mode="after")
    def weights(self):
        if not self.spending_weights or set(self.spending_weights) - set(PRODUCTS[:6]):
            raise ValueError("Acquisti pubblici: solo prodotti primari/secondari")
        if abs(sum(self.spending_weights.values()) - 1) > 1e-12:
            raise ValueError("I pesi della spesa pubblica devono sommare a 1")
        return self


class BankConfig(StrictModel):
    min_equity_ratio: Annotated[float, Field(gt=0, lt=1)]
    deposit_rate_pass_through: Fraction
    initial_equity_per_person: Price
    resolution_mode: Literal["deposit_conversion"]
    deposit_insurance_enabled: Literal[False]
    funding_spread: Nonnegative = 0.005
    operating_spread: Nonnegative = 0.01
    loss_given_default: Fraction = 0.5
    capital_premium: Nonnegative = 0.005
    max_borrower_share: Annotated[float, Field(gt=0, le=1)] = 0.25
    max_debt_to_income: Positive = 4.0
    min_interest_coverage: Nonnegative = 1.25
    expected_outflow_share: Fraction = 0.1
    max_banks_compared: Annotated[int, Field(ge=1)] = 3
    review_weeks: Annotated[int, Field(ge=1)] = 1
    recall_notice_weeks: Annotated[int, Field(ge=1)] = 4
    ordinary_haircut: Fraction = 0.05
    emergency_haircut: Fraction = 0.35
    facility_cap_share: Fraction = 0.5
    arrears_grace_weeks: Annotated[int, Field(ge=1)] = 4


class PeopleConfig(StrictModel):
    initial_deposit: Price
    deposit_spread: Fraction
    adult_age_min_years: Annotated[int, Field(ge=18)]
    adult_age_max_years: Annotated[int, Field(ge=18, le=120)]
    reservation_wage: Price
    wage_spread: Fraction
    propensity_min: Fraction
    propensity_max: Fraction
    liquidity_buffer_weeks: Nonnegative
    wealth_drawdown_rate: Fraction

    @model_validator(mode="after")
    def ranges(self):
        if self.adult_age_min_years > self.adult_age_max_years:
            raise ValueError("Intervallo età invertito")
        if self.propensity_min > self.propensity_max:
            raise ValueError("Intervallo propensioni invertito")
        return self


class OpeningConfig(StrictModel):
    reference_population: Annotated[int, Field(gt=0)]
    reference_companies_per_product: Annotated[int, Field(gt=0)]
    firm_deposit: Price
    offered_wage: Price
    shares_per_issuer: Price
    initial_reputation: Fraction


class Product(StrictModel):
    id: Annotated[int, Field(ge=1, le=11)]
    name: str
    label: Annotated[str, Field(min_length=1)]
    unit: Annotated[str, Field(min_length=1)]
    kind: Literal["final", "resource", "capital"]
    need_group: Literal["primary", "secondary", "luxury", "none"]
    need_mean: Nonnegative
    need_std: Nonnegative
    unlimited_need: bool
    recipe: dict[str, Positive]
    depreciation: Fraction
    opening_price: Price
    opening_unit_cost: Price
    initial_output: Nonnegative
    initial_inputs: dict[str, Nonnegative]
    initial_capital: Positive
    productivity: Positive
    capacity_per_capital: Positive
    initial_workers: Annotated[int, Field(gt=0)]
    natural_reserve: Nonnegative
    quality: Positive

    @model_validator(mode="after")
    def semantics(self):
        name = PRODUCTS[self.id - 1]
        if self.name != name:
            raise ValueError(f"Il prodotto {self.id} deve essere {name}")
        group = (
            "primary"
            if self.id <= 3
            else "secondary"
            if self.id <= 6
            else "luxury"
            if self.id == 7
            else "none"
        )
        kind = "final" if self.id <= 7 else "resource" if self.id <= 10 else "capital"
        if (self.kind, self.need_group) != (kind, group):
            raise ValueError(f"Categoria/bisogno errati per {name}")
        if self.unlimited_need != (self.id == 7):
            raise ValueError("Solo lusso ha bisogno illimitato; nessun infinito numerico")
        if group in ("none", "luxury") and (self.need_mean or self.need_std):
            raise ValueError("Risorse, capitale e lusso non hanno un fabbisogno fisico finito")
        if group == "primary" and (self.need_mean <= 0 or self.need_std):
            raise ValueError("Bisogni primari positivi e uguali per tutti")
        if set(self.recipe) - set(PRODUCTS[7:10]) or self.name in self.recipe:
            raise ValueError("Ricette: solo risorse prodotte, senza autoconsumo istantaneo")
        if set(self.initial_inputs) != set(self.recipe):
            raise ValueError("initial_inputs deve enumerare esattamente gli input della ricetta")
        if name == "wholesale_energy" and self.recipe:
            raise ValueError("L'energia all'ingrosso non richiede input della settimana corrente")
        if name in ("materials", "metals", "household_energy"):
            if "wholesale_energy" not in self.recipe:
                raise ValueError(f"{name} richiede energia all'ingrosso")
        if name == "luxury" and "metals" not in self.recipe:
            raise ValueError("Il lusso deve usare metalli")
        if name == "capital" and not {"wholesale_energy", "materials"} <= set(self.recipe):
            raise ValueError("Capitale richiede energia e materiali")
        if (kind == "resource") != (self.natural_reserve > 0):
            raise ValueError("Solo le estrattive richiedono giacimenti iniziali positivi")
        output = min(
            self.initial_capital * self.capacity_per_capital,
            self.productivity * self.initial_workers,
        )
        if any(self.initial_inputs[p] < output * coeff for p, coeff in self.recipe.items()):
            raise ValueError("Scorte di input insufficienti per avviare un ciclo produttivo")
        if kind == "resource" and self.natural_reserve < output:
            raise ValueError("Giacimento insufficiente all'avvio")
        return self


class Catalog(StrictModel):
    schema_version: Literal[1]
    products: list[Product]

    @model_validator(mode="after")
    def complete(self):
        if sorted(p.id for p in self.products) != list(range(1, 12)):
            raise ValueError("Il catalogo richiede esattamente gli 11 prodotti, ID unici 1..11")
        return self


class Config(StrictModel):
    schema_version: Literal[1]
    simulation: SimulationConfig
    runtime: RuntimeConfig
    features: Features
    execution: ExecutionConfig
    central_bank: CentralBankConfig
    government: GovernmentConfig
    banks: BankConfig
    people: PeopleConfig
    opening: OpeningConfig
    catalog: Catalog
    real_economy: RealEconomyConfig | None = None

    @property
    def firm_scale(self) -> float:
        return (
            self.simulation.initial_population
            / self.opening.reference_population
            * self.opening.reference_companies_per_product
            / self.simulation.companies_per_product
        )

    @model_validator(mode="after")
    @money_context
    def startup(self):
        import math

        s = self.simulation
        if self.execution.profile == "real_economy":
            if self.real_economy is None:
                raise ValueError("real_economy richiede parametri decisionali espliciti")
            g, cb = self.government, self.central_bank
            if (
                g.labor_income_tax_rate
                or g.profit_tax_rate
                or g.weekly_budget_per_person
                or cb.reserve_rate
                or cb.policy_rate
                or cb.emergency_rate
                or cb.emergency_lending_enabled
                or cb.primary_bond_purchases_enabled
            ):
                raise ValueError(
                    "Profilo T02: fiscalità, interessi e facilities a zero/disabilitati"
                )
        elif self.execution.profile == "monetary_economy":
            if self.real_economy is None:
                raise ValueError("monetary_economy richiede i parametri dell'economia reale")
        if s.initial_banks > s.initial_population:
            raise ValueError("Ogni banca deve avere almeno una persona cliente")
        labor = (
            sum(math.ceil(p.initial_workers * self.firm_scale) for p in self.catalog.products)
            * s.companies_per_product
        )
        if labor > s.initial_population:
            raise ValueError("Forza lavoro insufficiente per i posti iniziali della filiera")
        wage = self.opening.offered_wage
        for p in self.catalog.products:
            if money(self.opening.firm_deposit * Decimal(str(self.firm_scale))) < (
                wage * math.ceil(p.initial_workers * self.firm_scale)
            ):
                raise ValueError("Deposito impresa insufficiente per il primo monte salari")
            output = min(
                p.initial_capital * self.firm_scale * p.capacity_per_capital,
                p.productivity * math.ceil(p.initial_workers * self.firm_scale),
            )
            if any(
                p.initial_inputs[name] * self.firm_scale < output * coefficient
                for name, coefficient in p.recipe.items()
            ):
                raise ValueError("Scorte insufficienti dopo il ridimensionamento della filiera")
            if p.kind == "resource" and p.natural_reserve * self.firm_scale < output:
                raise ValueError("Giacimento insufficiente dopo il ridimensionamento")
        return self


class ScenarioFile(StrictModel):
    schema_version: Literal[1]
    products_file: str
    simulation: SimulationConfig
    runtime: RuntimeConfig
    features: Features
    execution: ExecutionConfig
    central_bank: CentralBankConfig
    government: GovernmentConfig
    banks: BankConfig
    people: PeopleConfig
    opening: OpeningConfig
    real_economy: RealEconomyConfig | None = None


class UniqueKeyLoader(yaml.SafeLoader):
    """Rifiuta duplicati che YAML normalmente sovrascrive silenziosamente."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("Le chiavi della configurazione YAML devono essere stringhe")
        if key in result:
            raise ValueError(f"Chiave YAML duplicata: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_yaml(path: Path):
    with path.open(encoding="utf-8") as source:
        return yaml.load(source, Loader=UniqueKeyLoader)


def load_config(path: str | Path) -> Config:
    path = Path(path)
    scenario = ScenarioFile.model_validate(read_yaml(path))
    catalog_path = path.parent / scenario.products_file
    catalog = Catalog.model_validate(read_yaml(catalog_path))
    return Config(**scenario.model_dump(exclude={"products_file"}), catalog=catalog)
