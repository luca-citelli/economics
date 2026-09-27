"""Contratti dati T01. Nessuna asta, runner o trasporto HTTP implementato."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from economic_sim.config import Amount, Nonnegative, Positive, Price, Rate, StrictModel

Identifier = Annotated[str, Field(min_length=1)]
Week = Annotated[int, Field(ge=0)]


class Loan(StrictModel):
    id: Identifier
    borrower_id: int
    bank_id: int
    asset_account: Identifier
    debt_account: Identifier
    annual_rate: Rate
    originated_week: Week
    next_review_week: Week
    interest_from_week: Week
    arrears: Amount
    purpose: str
    collateral_ids: tuple[str, ...]
    status: Literal["performing", "arrears", "closed", "written_down"]
    # Capitale residuo sempre letto dagli account, non duplicato nel contratto.

    @model_validator(mode="after")
    def dates(self):
        if (
            self.interest_from_week != self.originated_week + 1
            or self.next_review_week < self.interest_from_week
        ):
            raise ValueError("Interessi/revisione soltanto dalla settimana successiva")
        return self


class Bond(StrictModel):
    id: Identifier
    issuer_id: int
    holder_id: int
    face_value: Price
    issue_price: Price
    issued_week: Week
    maturity_week: Week
    asset_account: Identifier
    liability_account: Identifier

    @model_validator(mode="after")
    def maturity(self):
        if self.maturity_week != self.issued_week + 52:
            raise ValueError("I bond D1 durano 52 settimane")
        return self


class ShareIssue(StrictModel):
    id: Identifier
    issuer_id: int
    total_shares: Price
    capital_account: Identifier


class ShareHolding(StrictModel):
    issue_id: Identifier
    owner_id: int
    quantity: Price
    asset_account: Identifier


class Offer(StrictModel):
    seller_id: int
    product_id: int
    quantity: Nonnegative
    price: Price
    quality: Positive
    week: Week


class Order(StrictModel):
    buyer_id: int
    product_id: int
    quantity: Nonnegative
    budget: Amount
    max_price: Price
    week: Week


class Trade(StrictModel):
    id: Identifier
    buyer_id: int
    seller_id: int
    product_id: int
    quantity: Positive
    price: Price
    total_cost: Price
    payment_id: Identifier
    instrument_id: str | None


class MarketResult(StrictModel):
    market_id: Identifier
    week: Week
    offers: tuple[Offer, ...]
    financeable_demand: Nonnegative
    unfinanceable_demand: Nonnegative
    trades: tuple[Trade, ...]
    unfilled_demand: Nonnegative
    residual_supply: Nonnegative
    offered_price: Price | None
    transacted_price: Price | None
    failure_reasons: dict[str, Annotated[int, Field(ge=0)]]


class PolicyPatch(StrictModel):
    reserve_rate: Rate | None = None
    policy_rate: Rate | None = None
    emergency_rate: Rate | None = None
    weekly_bond_purchase_budget: Amount | None = None

    @model_validator(mode="after")
    def not_empty(self):
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("Patch monetaria vuota")
        return self


class PolicyCommand(StrictModel):
    schema_version: Literal[1]
    command_id: Identifier
    submitted_at: Identifier  # solo metadato; non entra nel checksum economico
    effective_week: Annotated[int, Field(ge=1)]
    server_sequence: Annotated[int, Field(ge=1)]
    type: Literal["policy"]
    patch: PolicyPatch


class Snapshot(StrictModel):
    schema_version: Literal[1]
    engine_version: str
    run_id: Identifier
    week: Week
    state_version: Annotated[int, Field(ge=0)]
    status: Literal["PAUSED"]
    checksum: Identifier
    metrics: dict[str, Amount]
    markets: tuple[MarketResult, ...]
    events: tuple[str, ...]
    pending_commands: tuple[PolicyCommand, ...]
