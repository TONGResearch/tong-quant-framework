"""Synthetic records exercise usability, not independent provider verification."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.coverage import HistoricalCoverageEvaluator, SecurityTimelineQualityInput
from tong_quant.data.lifecycle_review import (
    LifecycleRecordDisposition as Disposition,
)
from tong_quant.data.lifecycle_review import (
    review_lifecycle_record,
)
from tong_quant.data.models import SecurityLifecycleEvent
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    LifecycleEventType,
    Market,
    PITReadinessClassification,
    SecurityStatus,
)
from tong_quant.domain.models import Instrument, InstrumentStatus
from tong_quant.version import AKSHARE_SUSPENSION_VERSION, LIFECYCLE_REVIEW_VERSION

NOW = datetime(2026, 10, 16, tzinfo=UTC)
DAY = date(2026, 10, 15)


def event(**overrides) -> SecurityLifecycleEvent:
    original = SecurityLifecycleEvent(
        Instrument("600000", Market.CHINA_A, "Synthetic", available_at=NOW),
        LifecycleEventType.SUSPENSION_STARTED,
        DAY,
        NOW,
        "synthetic-reviewed",
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.MEDIUM,
    )
    return replace(original, **overrides)


def review(record):
    return review_lifecycle_record(record, as_of=NOW, effective_on_or_before=DAY)


@pytest.mark.parametrize("version", (None, AKSHARE_SUSPENSION_VERSION))
@pytest.mark.parametrize("trust", (DataTrustLevel.LOW, DataTrustLevel.VERIFIED))
def test_akshare_forecast_resumption_never_clears_by_version_or_trust_label(version, trust):
    record = event(
        source="akshare:stock_tfp_em",
        event_type=LifecycleEventType.TRADING_RESUMED,
        details={} if version is None else {"normalization_version": version},
        trust_level=trust,
    )
    result = review(record)
    assert result.disposition is Disposition.QUARANTINED
    assert "unconfirmed_akshare_resumption" in result.reasons
    assert record.trust_level is trust


@pytest.mark.parametrize(
    "overrides,reason",
    (
        ({"raw_data_hash": "not-a-valid-digest"}, "raw_hash_invalid"),
        ({"source": " "}, "source_missing"),
        ({"available_at": NOW + timedelta(seconds=1)}, "future_availability"),
        ({"effective_date": DAY + timedelta(days=1)}, "future_effective_date"),
        (
            {"source": "akshare", "event_type": LifecycleEventType.TRADING_RESUMED},
            "unconfirmed_akshare_resumption",
        ),
    ),
)
def test_invalid_evidence_is_quarantined_not_deleted(overrides, reason):
    record = event(**overrides)
    result = review(record)
    assert result.disposition is Disposition.QUARANTINED
    assert reason in result.reasons
    assert result.model_version == LIFECYCLE_REVIEW_VERSION
    assert len(result.record_hash) == 64


def test_corrected_low_trust_suspension_remains_an_observation_only():
    result = review(
        event(
            source="akshare:stock_tfp_em",
            trust_level=DataTrustLevel.LOW,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            details={"normalization_version": AKSHARE_SUSPENSION_VERSION},
        )
    )
    assert result.disposition is Disposition.OBSERVATION_ONLY
    assert "partial_suspension_observation" in result.reasons


def test_unknown_provider_and_unknown_trust_do_not_inherit_source_trust():
    assert (
        review(
            event(source="moomoo_manual_observation", trust_level=DataTrustLevel.UNKNOWN)
        ).disposition
        is Disposition.OBSERVATION_ONLY
    )


def test_review_hash_is_deterministic_and_binds_original_content():
    first = event(details={"a": "1", "b": "2"})
    same = event(details={"b": "2", "a": "1"})
    assert review(first) == review(same)
    assert review(first).record_hash != review(replace(first, source="changed")).record_hash


@pytest.mark.parametrize("kind", ["event", "status"])
@pytest.mark.parametrize("field", ["availability", "instrument"])
@pytest.mark.parametrize("utc_cutoff", [False, True])
def test_lifecycle_review_quarantines_future_dst_fold_and_cannot_raise_coverage(
    kind, field, utc_cutoff
):
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    later = first.replace(fold=1)
    cutoff = first.astimezone(UTC) if utc_cutoff else first
    record = event(available_at=first, instrument=replace(event().instrument, available_at=first))
    if field == "availability":
        record = replace(record, available_at=later)
    else:
        record = replace(record, instrument=replace(record.instrument, available_at=later))
    if kind == "status":
        record = InstrumentStatus(
            record.instrument, DAY, SecurityStatus.SUSPENDED, False, record.available_at,
            record.source, raw_data_hash=record.raw_data_hash,
            availability_precision=record.availability_precision, trust_level=record.trust_level,
        )
    result = review_lifecycle_record(record, as_of=cutoff, effective_on_or_before=DAY)
    assert result.disposition is Disposition.QUARANTINED
    assert ("future_availability" if field == "availability" else "future_instrument_snapshot"
            ) in result.reasons
    if kind == "event":
        quality = SecurityTimelineQualityInput(
            "china_a:equity:600000", date(2026, 10, 1), DAY, (record,),
            (LifecycleEventType.SUSPENSION_STARTED,), expected_provider_count=1,
        )
        assessed = HistoricalCoverageEvaluator().security_timeline(quality, assessed_at=cutoff)
        assert assessed.confidence_score == 0
        assert assessed.classification is PITReadinessClassification.UNSUITABLE


def test_lifecycle_review_accepts_equivalent_utc_instants_without_mutating_sources():
    instant = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1)
    record = event(available_at=instant,
                   instrument=replace(event().instrument, available_at=instant))
    result = review_lifecycle_record(record, as_of=instant.astimezone(UTC),
                                    effective_on_or_before=DAY)
    assert result.disposition is Disposition.REVIEWABLE
    assert record.available_at is instant


@pytest.mark.parametrize(
    "dataset,source",
    (
        ("instrument_status_suspended", "akshare"),
        ("", "akshare:stock_zh_a_stop_em"),
    ),
)
def test_legacy_status_mapping_cannot_be_cleared_by_a_high_label(dataset, source):
    row = InstrumentStatus(
        event().instrument,
        DAY,
        SecurityStatus.SUSPENDED,
        False,
        NOW,
        source,
        raw_data_hash="a" * 64,
        provider_dataset=dataset,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.VERIFIED,
    )
    assert "legacy_delisted_quote_status" in review(row).reasons


def test_status_interval_keeps_existing_inclusive_end_semantics():
    row = InstrumentStatus(
        event().instrument,
        DAY - timedelta(days=1),
        SecurityStatus.SPECIAL_TREATMENT,
        True,
        NOW,
        "synthetic-reviewed",
        effective_to=DAY,
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.MEDIUM,
    )
    assert review(row).disposition is Disposition.REVIEWABLE
    assert (
        review(replace(row, effective_to=DAY - timedelta(days=1))).disposition
        is Disposition.QUARANTINED
    )


def coverage(events, **overrides):
    quality = SecurityTimelineQualityInput(
        "china_a:equity:600000",
        date(2026, 10, 1),
        DAY,
        tuple(events),
        (LifecycleEventType.SUSPENSION_STARTED, LifecycleEventType.TRADING_RESUMED),
    )
    return HistoricalCoverageEvaluator().security_timeline(
        replace(quality, **overrides), assessed_at=NOW
    )


def test_false_resumption_cannot_improve_coverage_or_its_trust():
    valid = event()
    invalid = event(
        source="akshare:stock_tfp_em",
        event_type=LifecycleEventType.TRADING_RESUMED,
        trust_level=DataTrustLevel.VERIFIED,
    )
    result = coverage((valid, invalid))
    assert result.score_components["event_type_coverage"] == 50
    assert result.score_components["in_scope_nonquarantined_pct"] == 50
    assert result.classification is PITReadinessClassification.UNSUITABLE
    assert result.trust_level is DataTrustLevel.MEDIUM
    assert "lifecycle_review:unconfirmed_akshare_resumption" in result.warnings


def test_weak_record_cannot_be_hidden_by_averaging_high_trust_records():
    events = tuple(
        event(event_type=kind, trust_level=trust, source=source)
        for kind, trust, source in (
            (LifecycleEventType.SUSPENSION_STARTED, DataTrustLevel.VERIFIED, "synthetic-1"),
            (LifecycleEventType.TRADING_RESUMED, DataTrustLevel.LOW, "synthetic-2"),
        )
    )
    result = coverage(events)
    assert result.trust_level is DataTrustLevel.LOW
    assert result.classification is PITReadinessClassification.CAUTION


def test_legitimate_st_and_delisting_are_not_quarantined_for_being_adverse():
    for kind in (LifecycleEventType.ST_ENTER, LifecycleEventType.DELISTED):
        assert review(event(event_type=kind)).disposition is Disposition.REVIEWABLE


def test_empty_history_never_receives_a_favorable_coverage_score():
    result = coverage(())
    assert result.confidence_score == 0
    assert result.classification is PITReadinessClassification.UNSUITABLE


def test_other_security_and_out_of_period_records_do_not_complete_a_subject_history():
    other = event(instrument=replace(event().instrument, symbol="600001"),
                  event_type=LifecycleEventType.TRADING_RESUMED)
    older = event(effective_date=date(2026, 9, 30))
    result = coverage((event(), other, older))
    assert result.score_components["event_type_coverage"] == 50
    assert "excluded_lifecycle_records:2/3" in result.warnings
    assert result.classification is PITReadinessClassification.UNSUITABLE


def test_large_quarantine_sets_keep_percentage_components_bounded():
    result = coverage(tuple(event(source="") for _ in range(150)))
    assert result.score_components["in_scope_nonquarantined_pct"] == 0
    assert result.confidence_score == 0


@pytest.mark.parametrize(
    "overrides",
    (
        {"period_start": DAY + timedelta(days=1)},
        {"expected_event_types": ()},
        {"expected_provider_count": 0},
        {"contradiction_count": -1},
    ),
)
def test_invalid_coverage_denominators_cannot_be_used_to_claim_completeness(overrides):
    with pytest.raises(ValueError):
        coverage((event(),), **overrides)
