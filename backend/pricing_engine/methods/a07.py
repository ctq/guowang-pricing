from decimal import Decimal

from pricing_engine.common import assign_ranks, average_price, discount_rate, mark_used, normalize_rows, require_bids, select_interval, target_result
from pricing_engine.decimal_utils import HUNDRED, ONE, ZERO, avg, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A07"
NAME = "区间平均下浮双边曲线算法"
DEFAULTS = {"F1": Decimal("0.8"), "F2": Decimal("1.1"), "n": Decimal("1.0"), "m": Decimal("0.9"), "a": Decimal("-0.0025"), "round_scale": Decimal("4")}


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    a1 = average_price(active)
    lower = params["F1"] * a1
    upper = params["F2"] * a1
    interval_rows = select_interval(active, lower, upper)
    used_rows = interval_rows or active
    a2 = avg([row.bid_price for row in used_rows if row.bid_price is not None])
    benchmark = a2 * (ONE - params["a"])
    mark_used(rows, used_rows)
    scale = int(params.get("round_scale", Decimal("4")))
    for row in active:
        if row.bid_price >= benchmark:
            score = (benchmark / row.bid_price) * params["n"] * HUNDRED
        else:
            score = (row.bid_price / benchmark) * params["m"] * HUNDRED
        row.score = q(max(score, ZERO), scale)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(rows), len(active), target_result(rows, payload.project), rows, {"A1": q(a1, 6), "A2": q(a2, 6), "lower": q(lower, 6), "upper": q(upper, 6), "fallback": not bool(interval_rows), "benchmark_formula": "A2 * (1 - a)"})
