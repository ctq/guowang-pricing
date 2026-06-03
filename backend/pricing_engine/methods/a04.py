from decimal import Decimal

from pricing_engine.common import assign_ranks, average_price, discount_rate, extended_linear_score, mark_used, normalize_rows, require_bids, select_interval_exclusive, target_result, trim_extremes
from pricing_engine.decimal_utils import ONE, avg, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A04"
NAME = "区间复合平均价法（次低价平均）"
DEFAULTS = {"lower_limit": Decimal("-0.20"), "upper_limit": Decimal("0.10"), "m_high": Decimal("1.0"), "m_low": Decimal("0.6"), "n": Decimal("1.0"), "round_scale": Decimal("4")}


def _trim_counts(m: int) -> tuple[int, int]:
    if m < 10:
        return 0, 0
    if m < 20:
        return 1, 1
    if m < 30:
        return 2, 1
    return 3, 2


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    high, low = _trim_counts(len(active))
    base_rows = trim_extremes(active, high, low)
    a1 = average_price(base_rows)
    lower = a1 * (ONE + params["lower_limit"])
    upper = a1 * (ONE + params["upper_limit"])
    interval_rows = select_interval_exclusive(base_rows, lower, upper)
    if interval_rows:
        a2 = avg([row.bid_price for row in interval_rows if row.bid_price is not None])
        p_min = min(row.bid_price for row in interval_rows if row.bid_price is not None)
        benchmark = (a2 + p_min) / Decimal("2")
        used_rows = interval_rows
        fallback = False
    else:
        a2 = None
        p_min = None
        benchmark = average_price(active)
        used_rows = active
        fallback = True
    mark_used(rows, used_rows)
    round_scale = int(params.get("round_scale", Decimal("4")))
    for row in active:
        row.score = extended_linear_score(row.bid_price, benchmark, params["n"], params["m_high"], params["m_low"], round_scale)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(active), len(used_rows), target_result(rows, payload.project), rows, {"A1": q(a1, 6), "A2": q(a2, 6) if a2 is not None else None, "P_min": q(p_min, 6) if p_min is not None else None, "lower": q(lower, 6), "upper": q(upper, 6), "trim_high": high, "trim_low": low, "fallback": fallback, "benchmark_formula": "(A2 + P_min) / 2 or full average"})
