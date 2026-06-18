from decimal import Decimal
from typing import Any

from app.schemas.calculation import BidRowResponse, CalculateRequest, CalculateResponse, TargetResponse
from pricing_engine.decimal_utils import dec_to_str
from pricing_engine.models import BidInput, CalculationInput, CalculationResult, ProjectInput


def request_to_engine(payload: CalculateRequest) -> CalculationInput:
    return CalculationInput(
        project=ProjectInput(
            tender_no=payload.project.tender_no,
            tender_name=payload.project.tender_name,
            section_no=payload.project.section_no,
            package_no=payload.project.package_no,
            province=payload.project.province,
            ceiling_price=payload.project.ceiling_price,
            price_weight=payload.project.price_weight,
            target_company=payload.project.target_company,
        ),
        method_code=payload.method_code,
        params=dict(payload.params),
        bids=[
            BidInput(bidder_name=bid.bidder_name, bid_price=bid.bid_price, index=index)
            for index, bid in enumerate(payload.bids)
        ],
        source=payload.source,
    )


def _json_debug(value: Any) -> Any:
    if isinstance(value, Decimal):
        return dec_to_str(value)
    if isinstance(value, dict):
        return {key: _json_debug(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_debug(item) for item in value]
    return value


def result_to_response(result: CalculationResult) -> CalculateResponse:
    return CalculateResponse(
        method_code=result.method_code,
        method_name=result.method_name,
        benchmark_price=dec_to_str(result.benchmark_price, 6) or "0",
        discount_rate=dec_to_str(result.discount_rate, 6),
        bidder_count=result.bidder_count,
        effective_count=result.effective_count,
        target=TargetResponse(
            found=result.target.found,
            score=dec_to_str(result.target.score, 4),
            rank=result.target.rank,
            score_gap=dec_to_str(result.target.score_gap, 5),
            weighted_gap=dec_to_str(result.target.weighted_gap, 5),
        ),
        rows=[
            BidRowResponse(
                rank=row.rank,
                bidder_name=row.bidder_name,
                bid_price=dec_to_str(row.bid_price, 6),
                participated=row.participated,
                used_for_benchmark=row.used_for_benchmark,
                score=dec_to_str(row.score, 4),
                remark=row.remark,
            )
            for row in result.rows
        ],
        debug=_json_debug(result.debug),
    )
