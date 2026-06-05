from decimal import Decimal

from pricing_engine.common import apply_linear_scores, assign_ranks, average_price, discount_rate, mark_used, normalize_rows, require_bids, select_interval, target_result
from pricing_engine.decimal_utils import ONE, avg, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A03"
NAME = "区间复合平均价浮动法"
DEFAULTS = {"a": Decimal("-0.20"), "b": Decimal("0.15"), "n1": Decimal("1.0"), "n2": Decimal("0.5"), "c": Decimal("0"), "round_scale": Decimal("4")}


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    full_avg = average_price(active)
    if len(active) <= 5:
        used_rows = active
        selected_avg = full_avg
        lower = upper = None
        fallback = False
    else:
        lower = full_avg * (ONE + params["a"])
        upper = full_avg * (ONE + params["b"])
        interval_rows = select_interval(active, lower, upper)
        used_rows = interval_rows or active
        selected_avg = avg([row.bid_price for row in used_rows if row.bid_price is not None])
        fallback = not bool(interval_rows)
    benchmark = selected_avg * (ONE + params["c"])
    mark_used(rows, used_rows)
    apply_linear_scores(rows, benchmark, params)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(rows), len(active), target_result(rows, payload.project), rows, {"A_full": q(full_avg, 6), "selected_average": q(selected_avg, 6), "lower": q(lower, 6) if lower is not None else None, "upper": q(upper, 6) if upper is not None else None, "fallback": fallback, "benchmark_formula": "selected_average * (1 + c)"})
