"""Actual-instant financial visibility; synthetic receipts do not qualify sources."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.financial.comparisons import financial_comparisons
from tong_quant.research.financial.inputs import (
    BankInputPolicy,
    BankInputStatus,
    assess_bank_inputs,
)
from tong_quant.research.financial.nonfinancial import (
    NonfinancialDiagnosticStatus,
    nonfinancial_diagnostics,
)
from tong_quant.research.financial.nonfinancial_inputs import (
    NonfinancialInputPolicy,
    assess_nonfinancial_inputs,
)
from tong_quant.research.financial.trailing import trailing_financial_diagnostics
from tong_quant.research.financial.valuation import valuation_basis_diagnostics

EARLY = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
LATE = EARLY.replace(fold=1)


def _entry(metric="revenue", *, sector="nonfinancial", at=EARLY, value="100", revision=0):
    balance = metric == "total_assets"
    statement = ("balance" if balance else "cash_flow"
                 if metric == "operating_cash_flow" else "income")
    fact = FundamentalFact(
        Instrument("002624", Market.CHINA_A, "Synthetic fixture"),
        metric, date(2026, 6, 30), datetime(2026, 8, 20, tzinfo=UTC), at,
        Decimal(value), "Synthetic only", period_start=None if balance else date(2026, 1, 1),
        currency="CNY", unit="absolute", revision=revision,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        trust_level=DataTrustLevel.LOW)
    return FinancialFactInspection(
        fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic receipt, not authentication",),
        reporting_scope="group", sector_profile=sector, evidence_id="a" * 64,
        review_artifact_id="b" * 64, filing_artifact_id="c" * 64, filing_sha256="d" * 64,
        source_pages=(1,), source_unit="CNY", source_column="group_current_period",
        audit_status="unaudited", statement=statement,
        filing_period_end=fact.period_end)


def _snapshot(*entries, as_of=LATE, sector="nonfinancial"):
    return FinancialInputSnapshot("002624", Market.CHINA_A, as_of,
        tuple(sorted({entry.fact.metric for entry in entries})), sector, "group", entries)


@pytest.mark.parametrize("field", ["available_at", "published_at", "instrument_available_at"])
def test_snapshot_rejects_future_fold_input(field):
    entry = _entry()
    changes = {field: LATE} if field != "instrument_available_at" else {
        "instrument": replace(entry.fact.instrument, available_at=LATE)}
    with pytest.raises(ValueError):
        _snapshot(replace(entry, fact=replace(entry.fact, **changes)), as_of=EARLY)


def test_snapshot_rejects_reversed_fold_publication_availability():
    entry = _entry()
    with pytest.raises(ValueError):
        _snapshot(replace(entry, fact=replace(entry.fact, published_at=LATE, available_at=EARLY)))


def test_fact_allows_actual_forward_chronology_when_wall_clock_moves_back():
    published = EARLY.replace(minute=55)
    available = LATE.replace(minute=5)
    entry = _entry(at=available)
    fact = replace(entry.fact, published_at=published)
    snapshot = _snapshot(replace(entry, fact=fact))
    assert snapshot.inspections[0].fact.published_at == published
    assert snapshot.inspections[0].fact.available_at == available


@pytest.mark.parametrize("cutoff", [
    datetime(2026, 6, 30, 23, tzinfo=UTC),
    datetime(2026, 7, 1, 7, tzinfo=ZoneInfo("Asia/Shanghai")),
])
@pytest.mark.parametrize("field", ["period_end", "filing_period_end"])
def test_snapshot_period_date_guard_uses_pinned_utc_date_not_caller_label(cutoff, field):
    entry = replace(_entry(), status=FinancialBindingStatus.UNSUPPORTED)
    entry = replace(entry, fact=replace(entry.fact,
        available_at=cutoff, published_at=cutoff))
    if field == "period_end":
        entry = replace(entry, fact=replace(entry.fact, period_end=date(2026, 7, 1)))
    else:
        entry = replace(entry, filing_period_end=date(2026, 7, 1))
    with pytest.raises(ValueError, match="subject/time/semantics"):
        _snapshot(entry, as_of=cutoff)


@pytest.mark.parametrize("field", ["available_at", "published_at", "instrument_available_at"])
def test_mutated_naive_fact_times_fail_revalidation(field):
    entry = _entry()
    snapshot = _snapshot(entry)
    target = entry.fact.instrument if field == "instrument_available_at" else entry.fact
    object.__setattr__(target, "available_at" if field == "instrument_available_at" else field,
                       EARLY.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        snapshot.__post_init__()


def test_context_cutoff_binding_does_not_alias_repeated_local_labels():
    entry = _entry()
    snapshot = _snapshot(entry, as_of=EARLY)
    with pytest.raises(ValueError, match="does not match"):
        snapshot.validate_context((entry.fact,), symbol=snapshot.symbol,
                                  market=snapshot.market, as_of=LATE)


def test_context_accepts_equivalent_actual_instant_despite_fold_timezone_spelling():
    entry = _entry()
    snapshot = _snapshot(entry, as_of=EARLY)
    snapshot.validate_context((entry.fact,), symbol=snapshot.symbol,
                              market=snapshot.market, as_of=EARLY.astimezone(UTC))
    same = replace(snapshot, as_of=EARLY.astimezone(ZoneInfo("Asia/Shanghai")))
    assert snapshot.input_hash == same.input_hash


def test_snapshot_hash_and_document_revalidate_mutated_visibility():
    snapshot = _snapshot(_entry(), as_of=EARLY)
    object.__setattr__(snapshot.inspections[0].fact, "available_at", LATE)
    with pytest.raises(ValueError):
        _ = snapshot.input_hash
    with pytest.raises(ValueError):
        snapshot.document()


@pytest.mark.parametrize("consumer", [financial_comparisons, nonfinancial_diagnostics,
                                      trailing_financial_diagnostics, valuation_basis_diagnostics])
def test_direct_financial_consumers_reject_mutated_future_inputs(consumer):
    snapshot = _snapshot(_entry(), as_of=EARLY)
    object.__setattr__(snapshot.inspections[0].fact, "available_at", LATE)
    with pytest.raises(ValueError):
        consumer(snapshot)


@pytest.mark.parametrize("status", [FinancialBindingStatus.REJECTED,
                                   FinancialBindingStatus.UNSUPPORTED])
@pytest.mark.parametrize("reverse", [False, True])
def test_bank_uses_later_actual_input_even_if_older_has_higher_revision(status, reverse):
    old = _entry(sector="bank", revision=9)
    new = replace(_entry(sector="bank", at=LATE), status=status)
    entries = (new, old) if reverse else (old, new)
    result = assess_bank_inputs(_snapshot(*entries, sector="bank"), BankInputPolicy())
    row = next(item for item in result.checks if item.metric == "revenue")
    assert row.status is (BankInputStatus.REJECTED if status is FinancialBindingStatus.REJECTED
                          else BankInputStatus.UNSUPPORTED)
    assert len(row.observation_hashes) == 1
    assert result.document()["investment_scoring_authorized"] is False


@pytest.mark.parametrize("reverse", [False, True])
def test_bank_equal_actual_instant_stays_ambiguous_across_timezone_spellings(reverse):
    first = _entry(sector="bank")
    second = replace(first, fact=replace(first.fact, available_at=EARLY.astimezone(UTC)))
    entries = (second, first) if reverse else (first, second)
    result = assess_bank_inputs(_snapshot(*entries, sector="bank"), BankInputPolicy())
    row = next(item for item in result.checks if item.metric == "revenue")
    assert row.status is BankInputStatus.AMBIGUOUS
    assert len(row.observation_hashes) == 2


@pytest.mark.parametrize("rejected", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_nonfinancial_latest_actual_version_cannot_fall_back_to_favorable_old_value(
    rejected, reverse,
):
    old = _entry(value="100", revision=9)
    new = _entry(at=LATE, value="200")
    if rejected:
        new = replace(new, status=FinancialBindingStatus.REJECTED)
    cash = replace(_entry("operating_cash_flow", value="50"), statement="cash_flow")
    entries = (new, old, cash) if reverse else (old, new, cash)
    result = nonfinancial_diagnostics(_snapshot(*entries))
    ratio = next(item for item in result if item.name == "operating_cash_flow_to_revenue_percent")
    if rejected:
        assert ratio.status is NonfinancialDiagnosticStatus.INCOMPATIBLE
        assert ratio.value is None
    else:
        assert ratio.status is NonfinancialDiagnosticStatus.DESCRIPTIVE
        assert ratio.value == Decimal("25.0000")
    assert ratio.document()["investment_scoring_authorized"] is False


def test_nonfinancial_equal_actual_instant_stays_ambiguous():
    first = _entry()
    second = replace(first, fact=replace(first.fact, available_at=EARLY.astimezone(UTC)))
    cash = replace(_entry("operating_cash_flow", value="50"), statement="cash_flow")
    result = nonfinancial_diagnostics(_snapshot(first, second, cash))
    ratio = next(item for item in result if item.name == "operating_cash_flow_to_revenue_percent")
    assert ratio.status is NonfinancialDiagnosticStatus.INCOMPATIBLE and ratio.value is None


def test_nonfinancial_checklist_keeps_latest_actual_rejection_and_equivalent_instant_ties():
    old = _entry(revision=9)
    new = replace(_entry(at=LATE), status=FinancialBindingStatus.REJECTED)
    result = assess_nonfinancial_inputs(_snapshot(old, new), NonfinancialInputPolicy())
    row = next(item for item in result["checks"] if item["metric"] == "revenue")
    assert row["status"] == "rejected" and len(row["observation_hashes"]) == 1
    duplicate = replace(old, fact=replace(old.fact, available_at=EARLY.astimezone(UTC)))
    result = assess_nonfinancial_inputs(_snapshot(old, duplicate), NonfinancialInputPolicy())
    row = next(item for item in result["checks"] if item["metric"] == "revenue")
    assert row["status"] == "ambiguous" and len(row["observation_hashes"]) == 2
