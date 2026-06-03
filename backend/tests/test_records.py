import json
from decimal import Decimal

from app.schemas.calculation import BidPayload, CalculateRequest, ProjectPayload
from app.schemas.mappers import request_to_engine
from app.services.records import request_log_json, result_log_json
from pricing_engine.registry import calculate


def test_detailed_log_json_keeps_bidder_names_and_prices() -> None:
    payload = CalculateRequest(
        project=ProjectPayload(
            tender_no="T001",
            tender_name="测试项目",
            section_no="S001",
            package_no="P001",
            province="浙江",
            ceiling_price=Decimal("200"),
            price_weight=Decimal("0.4"),
            target_company="投标人1",
        ),
        method_code="A05",
        params={},
        bids=[
            BidPayload(bidder_name="投标人1", bid_price="100"),
            BidPayload(bidder_name="投标人2", bid_price="不开标"),
        ],
        source="manual",
    )

    request_data = json.loads(request_log_json(payload))
    assert request_data["project"]["tender_no"] == "T001"
    assert request_data["bids"][0] == {"bidder_name": "投标人1", "bid_price": "100"}

    result_data = json.loads(result_log_json(calculate(request_to_engine(payload))) or "{}")
    assert result_data["rows"][0]["bidder_name"] == "投标人1"
    assert result_data["rows"][0]["bid_price"] == "100.000000"
