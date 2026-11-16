"""Synthetic receipts test denominator semantics, not issuer/source qualification."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.financial.valuation import (
    ValuationBasisStatus as Status,
)
from tong_quant.research.financial.valuation import valuation_basis_diagnostics

NOW = datetime(2026, 10, 23, tzinfo=UTC)
BOOK = "equity_attributable_to_parent"
PROFIT = "profit_attributable_to_parent"


def _snapshot(end=date(2026, 6, 30), **values):
    defaults = {BOOK: "80", PROFIT: "-10", "revenue": "200"}
    defaults.update(values)
    instrument = Instrument("002624", Market.CHINA_A, "Synthetic fixture", available_at=NOW)
    entries = []
    for metric, value in sorted(defaults.items()):
        balance = metric in {BOOK, "total_assets"}
        fact = FundamentalFact(
            instrument, metric, end, NOW, NOW, Decimal(value), "Synthetic source",
            period_start=None if balance else date(end.year, 1, 1),
            currency="CNY", unit="absolute", raw_data_hash="e" * 64,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.LOW,
        )
        entries.append(FinancialFactInspection(
            fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic receipt only",),
            reporting_scope="group", sector_profile="nonfinancial",
            evidence_id=sha256(metric.encode()).hexdigest(), review_artifact_id="a" * 64,
            filing_artifact_id="b" * 64, filing_sha256="c" * 64,
            source_pages=(43,), source_unit="CNY", source_column="group_current_period",
            audit_status="unaudited", statement="balance" if balance else "income",
            filing_period_end=end,
        ))
    return FinancialInputSnapshot("002624", Market.CHINA_A, NOW, tuple(sorted(defaults)),
                                  "nonfinancial", "group", tuple(entries))


def _results(snapshot):
    return {item.metric: item for item in valuation_basis_diagnostics(snapshot)}


@pytest.mark.parametrize("end", [date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)])
@pytest.mark.parametrize("profit", ["-10", "0", "10"])
def test_interim_profit_is_neither_annual_nor_ttm_even_when_negative(end, profit):
    snapshot = _snapshot(end, **{PROFIT: profit})
    result = _results(snapshot)
    assert result[PROFIT].status is result["revenue"].status is Status.PARTIAL_YEAR
    assert result[PROFIT].reported_value == Decimal(profit)
    assert result[BOOK].status is Status.OBSERVED
    assert valuation_basis_diagnostics(snapshot) == valuation_basis_diagnostics(snapshot)
    for item in result.values():
        body = item.document()
        assert body["valuation_multiple"] is None
        assert not body["investment_scoring_authorized"] and not body["execution_authorized"]
        assert not body["validation_authorized"] and not body["historical_replay_eligible"]
        assert len(body["diagnostic_hash"]) == 64
        assert item.trust_level == "low" and item.availability_precision == "retrieval_time"
        assert item.evidence_id and item.snapshot_hash == snapshot.input_hash


@pytest.mark.parametrize("value,status", [("10", Status.OBSERVED), ("0", Status.NONPOSITIVE),
                                         ("-10", Status.NONPOSITIVE)])
def test_full_year_and_signed_parent_book_denominators(value, status):
    results = _results(_snapshot(date(2025, 12, 31), **{PROFIT: value, BOOK: value}))
    assert results[PROFIT].status is results[BOOK].status is status
    assert results[PROFIT].reported_value == results[BOOK].reported_value == Decimal(value)
    assert results["revenue"].status is Status.OBSERVED


def test_no_assets_proxy_and_missing_is_distinct_from_not_requested():
    original = _snapshot(total_assets="999")
    absent = replace(original, inspections=tuple(
        e for e in original.inspections if e.fact.metric != BOOK))
    assert _results(absent)[BOOK].status is Status.MISSING
    not_requested = replace(absent, requested_metrics=tuple(
        metric for metric in absent.requested_metrics if metric != BOOK))
    assert _results(not_requested)[BOOK].status is Status.NOT_REQUESTED
    assert _results(not_requested)[BOOK].reported_value is None


@pytest.mark.parametrize("defect", ["duplicate", "rejected", "unsupported", "income_period",
                                  "statement", "comparative"])
def test_latest_incompatible_input_cannot_fall_back_to_good_prior_year(defect):
    annual = _snapshot(date(2025, 12, 31), **{PROFIT: "50"})
    latest = _snapshot()
    entry = next(e for e in latest.inspections if e.fact.metric == PROFIT)
    if defect in {"rejected", "unsupported"}:
        entry = replace(entry, status=(FinancialBindingStatus.REJECTED if defect == "rejected"
                                      else FinancialBindingStatus.UNSUPPORTED))
    elif defect == "income_period":
        entry = replace(entry, fact=replace(entry.fact, period_start=date(2026, 4, 1)))
    elif defect == "statement":
        entry = replace(entry, statement="balance")
    elif defect == "comparative":
        entry = replace(entry, source_column="group_prior_year_period",
                        filing_period_end=date(2026, 9, 30),
                        comparability="as_presented_same_filing",
                        issuer_revision_status="unverified")
    inspected = (*annual.inspections, entry, *((entry,) if defect == "duplicate" else ()))
    result = _results(replace(latest, inspections=inspected))[PROFIT]
    assert result.status is Status.INCOMPATIBLE and result.reported_value is None


def test_latest_interim_is_not_replaced_with_positive_annual_data():
    latest = _snapshot()
    annual = _snapshot(date(2025, 12, 31), **{PROFIT: "50"})
    result = _results(replace(latest, inspections=(*annual.inspections, *latest.inspections)))
    assert result[PROFIT].status is Status.PARTIAL_YEAR
    assert result[PROFIT].reported_value == Decimal("-10")


def test_future_input_rejected_and_hash_changes_with_cutoff():
    snapshot = _snapshot()
    later = replace(snapshot, as_of=NOW + timedelta(seconds=1))
    assert _results(snapshot)[BOOK].document()["diagnostic_hash"] != (
        _results(later)[BOOK].document()["diagnostic_hash"])
    entry = snapshot.inspections[0]
    with pytest.raises(ValueError):
        replace(snapshot, inspections=(replace(entry, fact=replace(
            entry.fact, available_at=NOW + timedelta(seconds=1))),))


def test_dst_fold_cannot_hide_a_future_valuation_input():
    zone = ZoneInfo("America/New_York")
    decision = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    future = decision.replace(fold=1)
    original = _snapshot()
    entry = original.inspections[0]
    entry = replace(entry, fact=replace(entry.fact, published_at=decision, available_at=future))
    with pytest.raises(ValueError, match="financial snapshot"):
        replace(original, as_of=decision, inspections=(entry,))
    snapshot = replace(original, as_of=decision)
    object.__setattr__(snapshot, "inspections", (entry,))
    with pytest.raises(ValueError, match="financial snapshot"):
        valuation_basis_diagnostics(snapshot)


@pytest.mark.parametrize("change", [{"market": Market.US}, {"sector_profile": "bank"}])
def test_unsupported_scope_does_not_acquire_valuation_diagnostics(change):
    snapshot = replace(_snapshot(), inspections=(), **change)
    with pytest.raises(ValueError):
        valuation_basis_diagnostics(snapshot)
