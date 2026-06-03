from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any


ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    if text.endswith("%"):
        text = str(Decimal(text[:-1]) / HUNDRED)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def q(value: Decimal | None, scale: int) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("1").scaleb(-scale), rounding=ROUND_HALF_UP)


def avg(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values, ZERO) / Decimal(len(values))


def dec_to_str(value: Decimal | None, scale: int | None = None) -> str | None:
    if value is None:
        return None
    if scale is not None:
        value = q(value, scale)
    return format(value, "f")
