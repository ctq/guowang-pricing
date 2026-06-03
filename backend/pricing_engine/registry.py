from decimal import Decimal
from importlib import import_module
from types import ModuleType

from pricing_engine.decimal_utils import to_decimal
from pricing_engine.models import CalculationInput, CalculationResult

_METHOD_MODULES = {
    "A01": "pricing_engine.methods.a01",
    "A02": "pricing_engine.methods.a02",
    "A03": "pricing_engine.methods.a03",
    "A04": "pricing_engine.methods.a04",
    "A05": "pricing_engine.methods.a05",
    "A06": "pricing_engine.methods.a06",
    "A07": "pricing_engine.methods.a07",
    "A08": "pricing_engine.methods.a08",
}


def _module(code: str) -> ModuleType:
    normalized = code.upper()
    if normalized not in _METHOD_MODULES:
        raise ValueError(f"不支持的评分方法: {code}")
    return import_module(_METHOD_MODULES[normalized])


def list_methods() -> list[dict[str, object]]:
    methods = []
    for code in sorted(_METHOD_MODULES):
        mod = _module(code)
        methods.append({"code": code, "name": mod.NAME, "defaults": {k: str(v) for k, v in mod.DEFAULTS.items()}})
    return methods


def get_method_defaults(code: str) -> dict[str, Decimal]:
    return dict(_module(code).DEFAULTS)


def merge_params(code: str, params: dict[str, object]) -> dict[str, Decimal]:
    merged = get_method_defaults(code)
    for key, value in params.items():
        parsed = to_decimal(value)
        if parsed is None:
            raise ValueError(f"参数 {key} 不是有效数字")
        merged[key] = parsed
    return merged


def calculate(payload: CalculationInput) -> CalculationResult:
    mod = _module(payload.method_code)
    params = merge_params(payload.method_code, payload.params)
    normalized = CalculationInput(
        project=payload.project,
        method_code=payload.method_code.upper(),
        params=params,
        bids=payload.bids,
        source=payload.source,
    )
    return mod.calculate(normalized, params)
