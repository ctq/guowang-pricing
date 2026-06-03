from decimal import Decimal

import pytest

from pricing_engine.models import BidInput, CalculationInput, ProjectInput
from pricing_engine.registry import calculate, list_methods


def payload(method_code: str, prices: list[str], params: dict[str, Decimal] | None = None) -> CalculationInput:
    return CalculationInput(
        project=ProjectInput(
            tender_no="T001",
            tender_name=None,
            section_no="S001",
            package_no="P001",
            province="浙江",
            ceiling_price=Decimal("200"),
            price_weight=Decimal("0.4"),
            target_company="投标人3",
        ),
        method_code=method_code,
        params=params or {},
        bids=[BidInput(f"投标人{i + 1}", price, i) for i, price in enumerate(prices)],
    )


def test_all_methods_are_registered() -> None:
    assert [item["code"] for item in list_methods()] == ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"]


@pytest.mark.parametrize("method", ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"])
def test_methods_calculate_scores_and_ranks(method: str) -> None:
    result = calculate(payload(method, ["180", "190", "不开标", "200", "210", "220"]))
    assert result.benchmark_price > 0
    assert result.bidder_count == 5
    assert result.rows[2].participated is False
    assert result.rows[2].score == Decimal("0")
    assert sorted(row.rank for row in result.rows if row.participated) == [1, 2, 3, 4, 5]


def test_a05_lowest_price_formula() -> None:
    result = calculate(payload("A05", ["100", "120", "150"]))
    assert result.benchmark_price == Decimal("100.000000")
    assert result.rows[0].score == Decimal("100.0000")
    assert result.rows[1].score == Decimal("83.3333")


def test_negative_linear_score_is_clamped() -> None:
    result = calculate(payload("A02", ["1", "1000"], {"c": Decimal("0"), "n1": Decimal("10"), "n2": Decimal("10")}))
    assert all((row.score or Decimal("0")) >= 0 for row in result.rows)


def test_target_gap_uses_weight() -> None:
    result = calculate(payload("A05", ["100", "120", "150"]))
    assert result.target.found is True
    assert result.target.rank == 3
    assert result.target.score_gap == Decimal("33.3333")
    assert result.target.weighted_gap == Decimal("13.3333")


def test_a07_uses_v12_template_one_minus_a_formula() -> None:
    result = calculate(payload("A07", ["100", "200"], {"F1": Decimal("0"), "F2": Decimal("2"), "a": Decimal("-0.1")}))
    assert result.benchmark_price == Decimal("165.000000")
    assert result.debug["benchmark_formula"] == "A2 * (1 - a)"
