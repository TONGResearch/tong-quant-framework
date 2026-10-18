from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from tong_quant.data.models import RawDataset
from tong_quant.data.normalization.akshare import normalize_financial_statement
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument

NOW = datetime(2026, 10, 16, 5, tzinfo=UTC)


def _normalize(values: dict[str, object]) -> list[FundamentalFact]:
    dataset = RawDataset(
        dataset="fundamental_facts",
        frame=pd.DataFrame(
            [{"report_date": "2025-12-31", "metric_name": "test_metric", **values}],
            dtype=object,
        ),
        retrieved_at=NOW,
        source="akshare:financial:income",
        parameters={"symbol": "600000", "statement": "income"},
    )
    return normalize_financial_statement(
        dataset,
        Instrument("600000", Market.CHINA_A, "test"),
        batch_id="numeric-regression",
    )


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"value": 0}, "0"),
        ({"value": Decimal("0.000")}, "0.000"),
        ({"value": "0", "金额": 0}, "0"),
        ({"value": 0, "金额": None}, "0"),
        ({"value": None, "金额": -12}, "-12"),
        ({"value": pd.NA, "金额": 0}, "0"),
        ({"value": "  ", "金额": "1.25"}, "1.25"),
        ({"value": "-0.25"}, "-0.25"),
        ({"value": "1.2500", "金额": "1.25"}, "1.2500"),
    ],
)
def test_financial_values_preserve_zero_and_compare_aliases(
    values: dict[str, object], expected: str,
) -> None:
    facts = _normalize(values)
    assert len(facts) == 1
    fact = facts[0]
    assert fact.value == Decimal(expected)
    assert fact.available_at == NOW
    assert fact.trust_level is DataTrustLevel.LOW
    assert fact.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME


@pytest.mark.parametrize("value", [None, "", "  ", pd.NA, float("nan")])
def test_missing_financial_value_is_not_fabricated_as_zero(value: object) -> None:
    assert _normalize({"value": value}) == []


@pytest.mark.parametrize("value", ["not-numeric", float("inf"), "-Infinity", True])
def test_invalid_financial_value_fails_without_echoing_payload(value: object) -> None:
    with pytest.raises(ValueError) as caught:
        _normalize({"value": value})
    assert str(caught.value) == "financial value must be a finite decimal"


def test_conflicting_numeric_aliases_are_not_silently_selected() -> None:
    with pytest.raises(ValueError, match="financial value aliases disagree"):
        _normalize({"value": 0, "金额": 10})
