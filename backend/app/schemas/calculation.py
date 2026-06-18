from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tender_no: str = Field(..., max_length=100)
    tender_name: str | None = Field(default=None, max_length=200)
    section_no: str = Field(..., max_length=100)
    package_no: str = Field(..., max_length=100)
    province: str
    ceiling_price: Decimal | None = None
    price_weight: Decimal | None = None
    target_company: str | None = None

    @field_validator("ceiling_price")
    @classmethod
    def validate_ceiling(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("最高限价必须大于 0")
        return value

    @field_validator("price_weight")
    @classmethod
    def validate_weight(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("价格分占比不能小于 0")
        return value


class BidPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    bidder_name: str
    bid_price: str | Decimal | int | float | None = None


class CalculateRequest(BaseModel):
    project: ProjectPayload
    method_code: str
    params: dict[str, Decimal] = Field(default_factory=dict)
    bids: list[BidPayload]
    source: str = "manual"

    @field_validator("bids")
    @classmethod
    def validate_bids(cls, value: list[BidPayload]) -> list[BidPayload]:
        if not value:
            raise ValueError("至少需要 1 条报价")
        if len(value) > 500:
            raise ValueError("单次最多支持 500 家投标人")
        return value


class TargetResponse(BaseModel):
    found: bool
    score: str | None = None
    rank: int | None = None
    score_gap: str | None = None
    weighted_gap: str | None = None


class BidRowResponse(BaseModel):
    rank: int | None
    bidder_name: str
    bid_price: str | None
    participated: bool
    used_for_benchmark: bool
    score: str | None
    remark: str


class CalculateResponse(BaseModel):
    method_code: str
    method_name: str
    benchmark_price: str
    discount_rate: str | None
    bidder_count: int
    effective_count: int
    target: TargetResponse
    rows: list[BidRowResponse]
    debug: dict[str, Any]


class ImportResponse(BaseModel):
    rows: list[BidPayload]
    mapping: dict[str, str]
    warnings: list[str] = Field(default_factory=list)
    requires_mapping: bool = False
    columns: list[str] = Field(default_factory=list)
    preview: list[dict[str, str]] = Field(default_factory=list)


class SheetData(BaseModel):
    name: str
    rows: list[BidPayload]
    columns: list[str] = Field(default_factory=list)


class MultiSheetImportResponse(BaseModel):
    sheets: list[SheetData]


class SheetCalculatePayload(BaseModel):
    name: str
    project: ProjectPayload
    method_code: str
    params: dict[str, str] = Field(default_factory=dict)
    bids: list[BidPayload]
    source: str = "manual"


class MultiCalculateRequest(BaseModel):
    sheets: list[SheetCalculatePayload]


class SheetResult(BaseModel):
    name: str
    method_code: str
    method_name: str
    benchmark_price: str
    discount_rate: str | None
    bidder_count: int
    effective_count: int
    target: TargetResponse
    rows: list[BidRowResponse]
    debug: dict[str, Any]


class MultiCalculateResponse(BaseModel):
    results: list[SheetResult]
