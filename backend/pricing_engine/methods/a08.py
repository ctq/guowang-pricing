from decimal import Decimal

from pricing_engine.common import apply_linear_scores, assign_ranks, average_price, discount_rate, mark_used, normalize_rows, require_bids, select_interval, target_result
from pricing_engine.decimal_utils import ONE, avg, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A08"
NAME = "区间复合一次平均价法"
DEFAULTS = {"w1": Decimal("-0.20"), "w2": Decimal("0.15"), "n1": Decimal("1.0"), "n2": Decimal("0.5"), "c": Decimal("0"), "round_scale": Decimal("4")}


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    a1 = average_price(active)
    lower = a1 * (ONE + params["w1"])
    upper = a1 * (ONE + params["w2"])
    interval_rows = select_interval(active, lower, upper)
    used_rows = interval_rows or active
    a2 = avg([row.bid_price for row in used_rows if row.bid_price is not None])
    benchmark = a2 * (ONE + params["c"])
    mark_used(rows, used_rows)
    apply_linear_scores(rows, benchmark, params)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(active), len(used_rows), target_result(rows, payload.project), rows, {"A1": q(a1, 6), "A2": q(a2, 6), "lower": q(lower, 6), "upper": q(upper, 6), "fallback": not bool(interval_rows), "benchmark_formula": "A2 * (1 + c)"})
