import hashlib
import json
from datetime import timedelta

from app.utils import now
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CalculationLog, CalculationRecord
from app.schemas.calculation import CalculateRequest
from app.schemas.mappers import result_to_response
from pricing_engine.decimal_utils import dec_to_str
from pricing_engine.models import CalculationResult


def _stable_decimal(value: Decimal | None) -> str | None:
    return dec_to_str(value, 6)


def param_hash(payload: CalculateRequest) -> str:
    serializable = {
        "method_code": payload.method_code.upper(),
        "params": {key: str(value) for key, value in sorted(payload.params.items())},
        "province": payload.project.province,
    }
    return hashlib.sha256(json.dumps(serializable, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def request_log_json(payload: CalculateRequest) -> str:
    return json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)


def result_log_json(result: CalculationResult | None) -> str | None:
    if result is None:
        return None
    return json.dumps(result_to_response(result).model_dump(mode="json"), ensure_ascii=False, sort_keys=True)


def _ceiling_eq(a: float | None, b: float | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < 0.000001


async def save_summary(db: AsyncSession, payload: CalculateRequest, result: CalculationResult, openid: str | None = None) -> None:
    digest = param_hash(payload)
    ten_minutes_ago = now() - timedelta(minutes=10)
    bm = float(result.benchmark_price)
    cp = float(payload.project.ceiling_price) if payload.project.ceiling_price is not None else None

    exact_stmt = select(CalculationRecord).where(
        CalculationRecord.param_hash == digest,
        CalculationRecord.method_code == result.method_code,
        CalculationRecord.benchmark_price == result.benchmark_price,
    )
    existing = (await db.execute(exact_stmt)).scalars().first()
    if existing is not None:
        existing.updated_at = now()
        existing.use_count += 1
        if openid and not existing.openid:
            existing.openid = openid
        await db.commit()
        return

    stmt = select(CalculationRecord).where(
        CalculationRecord.province == payload.project.province,
        CalculationRecord.method_code == result.method_code,
        CalculationRecord.created_at >= ten_minutes_ago,
    )
    for record in (await db.execute(stmt)).scalars():
        if not _ceiling_eq(record.ceiling_price, cp):
            continue
        if abs(float(record.benchmark_price) - bm) >= 0.000001:
            continue
        record.updated_at = now()
        record.use_count += 1
        if openid and not record.openid:
            record.openid = openid
        await db.commit()
        return

    db.add(
        CalculationRecord(
            province=payload.project.province,
            method_code=result.method_code,
            ceiling_price=cp,
            benchmark_price=result.benchmark_price,
            discount_rate=result.discount_rate,
            bidder_count=result.bidder_count,
            effective_count=result.effective_count,
            param_hash=digest,
            source=payload.source,
            openid=openid,
        )
    )
    await db.commit()


async def save_calculation_log(
    db: AsyncSession,
    payload: CalculateRequest,
    status: str,
    openid: str | None = None,
    result: CalculationResult | None = None,
    error_message: str | None = None,
) -> None:
    digest = param_hash(payload)
    db.add(
        CalculationLog(
            status=status,
            province=payload.project.province,
            method_code=payload.method_code.upper(),
            bidder_count=len(payload.bids),
            effective_count=result.effective_count if result else None,
            benchmark_price=result.benchmark_price if result else None,
            source=payload.source,
            param_hash=digest,
            error_message=error_message,
            request_json=request_log_json(payload),
            result_json=result_log_json(result),
            openid=openid,
        )
    )
    await db.commit()
