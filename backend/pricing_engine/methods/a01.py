from decimal import Decimal

from pricing_engine.common import (
    apply_linear_scores,
    assign_ranks,
    average_price,
    discount_rate,
    mark_used,
    normalize_rows,
    require_bids,
    select_interval,
    target_result,
    trim_extremes,
)
from pricing_engine.decimal_utils import ONE, avg, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A01"
NAME = "区间平均价浮动法"
DEFAULTS = {"w1": Decimal("-0.15"), "w2": Decimal("0.10"), "n1": Decimal("1.0"), "n2": Decimal("0.5"), "c": Decimal("0.01"), "round_scale": Decimal("4")}


def _trim_counts(m: int) -> tuple[int, int]:
    if m <= 5:
        return 0, 0
    if m <= 10:
        return 1, 1
    if m <= 20:
        return 2, 1
    if m <= 30:
        return 3, 2
    return 4, 3


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    high, low = _trim_counts(len(active))
    base_rows = trim_extremes(active, high, low)
    a1 = average_price(base_rows)
    lower = a1 * (ONE + params["w1"])
    upper = a1 * (ONE + params["w2"])
    interval_rows = select_interval(base_rows, lower, upper)
    used_rows = interval_rows or base_rows
    a2 = avg([row.bid_price for row in used_rows if row.bid_price is not None])
    float_direction = params.get("float_direction", Decimal("1"))
    if float_direction == Decimal("-1"):
        benchmark = a2 * (ONE - params["c"])
        benchmark_formula = "A2 * (1 - c)"
    else:
        benchmark = a2 * (ONE + params["c"])
        benchmark_formula = "A2 * (1 + c)"
    mark_used(rows, used_rows)
    apply_linear_scores(rows, benchmark, params)
    assign_ranks(rows)
    return CalculationResult(
        method_code=CODE,
        method_name=NAME,
        benchmark_price=q(benchmark, 6) or benchmark,
        discount_rate=discount_rate(benchmark, payload.project.ceiling_price),
        bidder_count=len(active),
        effective_count=len(used_rows),
        target=target_result(rows, payload.project),
        rows=rows,
        debug={"A1": q(a1, 6), "A2": q(a2, 6), "lower": q(lower, 6), "upper": q(upper, 6), "trim_high": high, "trim_low": low, "fallback": not bool(interval_rows), "benchmark_formula": benchmark_formula},
    )
