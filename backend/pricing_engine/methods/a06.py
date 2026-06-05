from decimal import Decimal

from pricing_engine.common import apply_linear_scores, assign_ranks, average_price, discount_rate, mark_used, normalize_rows, require_bids, target_result
from pricing_engine.decimal_utils import q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A06"
NAME = "简单算术平均值法"
DEFAULTS = {"n1": Decimal("1.0"), "n2": Decimal("0.8"), "round_scale": Decimal("4")}


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    benchmark = average_price(active)
    mark_used(rows, active)
    apply_linear_scores(rows, benchmark, params)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(rows), len(active), target_result(rows, payload.project), rows, {"A1": q(benchmark, 6), "benchmark_formula": "average(all participating prices)"})
