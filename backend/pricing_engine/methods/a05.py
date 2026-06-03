from decimal import Decimal

from pricing_engine.common import assign_ranks, discount_rate, mark_used, normalize_rows, require_bids, target_result
from pricing_engine.decimal_utils import HUNDRED, ZERO, q
from pricing_engine.models import CalculationInput, CalculationResult

CODE = "A05"
NAME = "最低价法"
DEFAULTS = {"round_scale": Decimal("4")}


def calculate(payload: CalculationInput, params: dict[str, Decimal]) -> CalculationResult:
    rows = normalize_rows(payload.bids)
    active = require_bids(rows)
    benchmark = min(row.bid_price for row in active if row.bid_price is not None)
    used_rows = [row for row in active if row.bid_price == benchmark]
    mark_used(rows, used_rows)
    scale = int(params.get("round_scale", Decimal("4")))
    for row in active:
        row.score = q(max(HUNDRED * benchmark / row.bid_price, ZERO), scale)
    assign_ranks(rows)
    return CalculationResult(CODE, NAME, q(benchmark, 6) or benchmark, discount_rate(benchmark, payload.project.ceiling_price), len(active), len(used_rows), target_result(rows, payload.project), rows, {"benchmark_formula": "min(bid_price)"})
