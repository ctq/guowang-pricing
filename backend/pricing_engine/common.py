from decimal import Decimal

from pricing_engine.decimal_utils import HUNDRED, ONE, ZERO, avg, q, to_decimal
from pricing_engine.models import BidInput, BidRow, ProjectInput, TargetResult


NO_OPEN_TEXT = "不开标"


def normalize_rows(bids: list[BidInput]) -> list[BidRow]:
    rows: list[BidRow] = []
    for i, bid in enumerate(bids):
        original = None if bid.bid_price is None else str(bid.bid_price).strip()
        bidder_name = bid.bidder_name.strip() or f"投标人{i + 1}"
        if original in (None, "", NO_OPEN_TEXT):
            rows.append(
                BidRow(
                    bidder_name=bidder_name,
                    original_price=original,
                    bid_price=None,
                    index=i,
                    participated=False,
                    score=ZERO,
                    remark=NO_OPEN_TEXT if original == NO_OPEN_TEXT else "空报价",
                )
            )
            continue
        price = to_decimal(original)
        if price is None or price <= ZERO:
            rows.append(
                BidRow(
                    bidder_name=bidder_name,
                    original_price=original,
                    bid_price=None,
                    index=i,
                    participated=False,
                    score=ZERO,
                    remark="报价无效",
                )
            )
            continue
        rows.append(
            BidRow(
                bidder_name=bidder_name,
                original_price=original,
                bid_price=price,
                index=i,
                participated=True,
            )
        )
    return rows


def participating(rows: list[BidRow]) -> list[BidRow]:
    return [row for row in rows if row.participated and row.bid_price is not None]


def prices(rows: list[BidRow]) -> list[Decimal]:
    return [row.bid_price for row in rows if row.bid_price is not None]


def select_interval(rows: list[BidRow], lower: Decimal, upper: Decimal) -> list[BidRow]:
    return [row for row in rows if row.bid_price is not None and lower <= row.bid_price <= upper]


def select_interval_exclusive(rows: list[BidRow], lower: Decimal, upper: Decimal) -> list[BidRow]:
    """区间筛选，不含临界值（不含本数）。"""
    return [row for row in rows if row.bid_price is not None and lower < row.bid_price < upper]


def trim_extremes(rows: list[BidRow], high_count: int, low_count: int) -> list[BidRow]:
    ordered = sorted(rows, key=lambda row: (row.bid_price, row.index))
    trimmed_low = {id(row) for row in ordered[:low_count]}
    trimmed_high = {id(row) for row in ordered[len(ordered) - high_count :]} if high_count else set()
    remaining: list[BidRow] = []
    for row in rows:
        if id(row) in trimmed_low:
            row.remark = append_remark(row.remark, "剔除最低价")
        elif id(row) in trimmed_high:
            row.remark = append_remark(row.remark, "剔除最高价")
        else:
            remaining.append(row)
    return remaining


def append_remark(current: str, text: str) -> str:
    if not current:
        return text
    if text in current:
        return current
    return f"{current}；{text}"


def mark_used(rows: list[BidRow], used_rows: list[BidRow]) -> None:
    used = {id(row) for row in used_rows}
    for row in rows:
        row.used_for_benchmark = id(row) in used


def linear_score(
    bid_price: Decimal,
    benchmark_price: Decimal,
    n1: Decimal,
    n2: Decimal,
    round_scale: int = 4,
) -> Decimal:
    coefficient = n1 if bid_price >= benchmark_price else n2
    score = HUNDRED - HUNDRED * coefficient * abs(bid_price - benchmark_price) / benchmark_price
    return q(max(score, ZERO), round_scale) or ZERO


def extended_linear_score(
    bid_price: Decimal,
    benchmark_price: Decimal,
    n: Decimal,
    m_high: Decimal,
    m_low: Decimal,
    round_scale: int = 4,
) -> Decimal:
    m = m_high if bid_price >= benchmark_price else m_low
    score = HUNDRED - HUNDRED * n * m * abs(bid_price - benchmark_price) / benchmark_price
    return q(max(score, ZERO), round_scale) or ZERO


def apply_linear_scores(rows: list[BidRow], benchmark: Decimal, params: dict[str, Decimal]) -> None:
    n1 = params["n1"]
    n2 = params["n2"]
    round_scale = int(params.get("round_scale", Decimal("4")))
    for row in participating(rows):
        row.score = linear_score(row.bid_price, benchmark, n1, n2, round_scale)


def assign_ranks(rows: list[BidRow]) -> None:
    ranked = [
        row
        for row in rows
        if row.participated and row.bid_price is not None and row.score is not None
    ]
    ranked.sort(key=lambda row: (-(row.score or ZERO), row.bid_price or Decimal("Infinity"), row.index))
    for rank, row in enumerate(ranked, start=1):
        row.rank = rank


def target_result(rows: list[BidRow], project: ProjectInput) -> TargetResult:
    name = (project.target_company or "").strip()
    if not name:
        return TargetResult()
    target = next((row for row in rows if row.bidder_name == name), None)
    if target is None or target.score is None:
        return TargetResult(found=False)
    first_score = max((row.score for row in rows if row.score is not None), default=ZERO)
    gap = q(first_score - target.score, 4) or ZERO
    weighted = None
    if project.price_weight is not None:
        weight = project.price_weight / HUNDRED if project.price_weight > ONE else project.price_weight
        weighted = q(gap * weight, 4)
    return TargetResult(found=True, score=target.score, rank=target.rank, score_gap=gap, weighted_gap=weighted)


def discount_rate(benchmark: Decimal, ceiling_price: Decimal | None) -> Decimal | None:
    if ceiling_price is None or ceiling_price <= ZERO:
        return None
    return q(benchmark / ceiling_price, 6)


def require_bids(rows: list[BidRow]) -> list[BidRow]:
    active = participating(rows)
    if not active:
        raise ValueError("至少需要 1 条有效报价")
    return active


def average_price(rows: list[BidRow]) -> Decimal:
    return avg(prices(rows))
