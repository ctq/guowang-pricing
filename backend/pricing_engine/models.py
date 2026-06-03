from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BidInput:
    bidder_name: str
    bid_price: str | Decimal | int | float | None
    index: int = 0


@dataclass
class BidRow:
    bidder_name: str
    original_price: str | None
    bid_price: Decimal | None
    index: int
    participated: bool
    used_for_benchmark: bool = False
    score: Decimal | None = None
    rank: int | None = None
    remark: str = ""


@dataclass(frozen=True)
class ProjectInput:
    tender_no: str
    tender_name: str | None
    section_no: str
    package_no: str
    province: str
    ceiling_price: Decimal | None = None
    price_weight: Decimal | None = None
    target_company: str | None = None


@dataclass(frozen=True)
class CalculationInput:
    project: ProjectInput
    method_code: str
    params: dict[str, Decimal]
    bids: list[BidInput]
    source: str = "manual"


@dataclass
class TargetResult:
    found: bool = False
    score: Decimal | None = None
    rank: int | None = None
    score_gap: Decimal | None = None
    weighted_gap: Decimal | None = None


@dataclass
class CalculationResult:
    method_code: str
    method_name: str
    benchmark_price: Decimal
    discount_rate: Decimal | None
    bidder_count: int
    effective_count: int
    target: TargetResult
    rows: list[BidRow]
    debug: dict[str, Any] = field(default_factory=dict)
