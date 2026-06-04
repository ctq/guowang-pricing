import json
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import CalculationRecord
from app.db.session import Base
from app.schemas.calculation import BidPayload, CalculateRequest, ProjectPayload
from app.schemas.mappers import request_to_engine
from app.services.records import _ceiling_eq, request_log_json, result_log_json, save_summary
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


def test_ceiling_compare_accepts_decimal_from_sqlite() -> None:
    assert _ceiling_eq(Decimal("200.000000"), 200.0) is True


@pytest.mark.anyio
async def test_save_summary_updates_existing_unique_record() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
        method_code="A01",
        params={
            "w1": Decimal("-0.15"),
            "w2": Decimal("0.10"),
            "n1": Decimal("1.0"),
            "n2": Decimal("0.5"),
            "c": Decimal("0.01"),
            "round_scale": Decimal("4"),
        },
        bids=[
            BidPayload(bidder_name="投标人1", bid_price="180"),
            BidPayload(bidder_name="投标人2", bid_price="190"),
            BidPayload(bidder_name="投标人3", bid_price="200"),
            BidPayload(bidder_name="投标人4", bid_price="210"),
        ],
        source="manual",
    )
    result = calculate(request_to_engine(payload))

    async with session_factory() as session:
        await save_summary(session, payload, result)
        await save_summary(session, payload, result)
        records = (await session.execute(select(CalculationRecord))).scalars().all()

    await engine.dispose()

    assert len(records) == 1
    assert records[0].use_count == 2
    assert float(records[0].ceiling_price) == 200.0
