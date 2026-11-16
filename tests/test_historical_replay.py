import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Adjustment,
    AvailabilityPrecision,
    DataTrustLevel,
    EvidenceQuality,
    Market,
    PITReadinessClassification,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    SecurityStatus,
    ValidationModuleName,
)
from tong_quant.domain.models import (
    Bar,
    FundamentalFact,
    Instrument,
    InstrumentStatus,
    UniverseMembership,
)
from tong_quant.validation.models import (
    OutcomeDefinition,
    OutOfSamplePolicy,
    ValidationRequest,
    WalkForwardPolicy,
)
from tong_quant.validation.replay import (
    HistoricalReplayBuilder,
    HistoricalReplayResult,
    ReplayQuery,
)
from tong_quant.validation.replay.hashing import stable_hash
from tong_quant.validation.replay.outcomes import evaluate_outcome
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository
from tong_quant.validation.replay.request_factory import ValidationRequestFactory
from tong_quant.validation.replay.research_binding import research_snapshot
from tong_quant.version import DATABASE_SCHEMA_VERSION


def test_replay_builds_deterministic_hash_and_request(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    query = _query(symbols=(instrument.symbol,))
    builder = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=True,
    )

    first = builder.build(query, generated_at=datetime(2025, 2, 1, tzinfo=UTC))
    second = builder.build(query, generated_at=datetime(2025, 2, 1, tzinfo=UTC))

    assert first.samples[0].replay_hash == second.samples[0].replay_hash
    assert first.samples[0].validation_sample is not None
    assert first.samples[0].replay_confidence.confidence < 100
    assert first.samples[0].replay_confidence.validation_eligible is True
    assert first.manifest.replay_confidence.confidence < 100
    assert first.manifest.replay_confidence.validation_eligible is True
    assert "readiness_hash:fundamentals" in first.manifest.dataset_versions
    assert first.manifest.provider_limitations
    assert store.table_count("historical_replay_manifests") == 1
    assert store.table_count("historical_replay_samples") == 1

    request = ValidationRequestFactory().build(
        first,
        validation_id="validation-from-replay",
        modules=(ValidationModuleName.HISTORICAL,),
        walk_forward_policy=WalkForwardPolicy(
            training_days=30,
            validation_days=10,
            step_days=10,
            embargo_days=1,
        ),
        out_of_sample_policy=OutOfSamplePolicy(
            development_end=date(2024, 1, 14),
            out_of_sample_start=date(2024, 1, 15),
            out_of_sample_end=date(2024, 1, 15),
            frozen_configuration_hash="c" * 64,
        ),
        requested_at=datetime(2025, 2, 2, tzinfo=UTC),
    )

    assert request.samples[0].sample_id == first.samples[0].sample_id
    assert request.framework_snapshot.database_schema_version == DATABASE_SCHEMA_VERSION


def test_replay_rejects_future_research_and_keeps_incomplete_visible(
    tmp_path: Path,
) -> None:
    store, instrument = _prepared_store(
        tmp_path,
        research_available_at=datetime(2024, 2, 5, tzinfo=UTC),
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(_query(symbols=(instrument.symbol,)))

    sample = result.samples[0]
    assert sample.validation_sample is None
    assert "research_report_missing" in sample.missing_data_flags
    assert sample.replay_confidence.validation_eligible is False

    with pytest.raises(ValueError, match="not eligible for Validation"):
        _validation_request(result)


def test_replay_preserves_special_status_and_missing_warnings(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path, status=SecurityStatus.SPECIAL_TREATMENT)

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(_query(symbols=(instrument.symbol,)))

    sample = result.samples[0]
    assert "security_status_preserved:special_treatment" in sample.missing_data_flags
    assert sample.validation_sample is not None
    assert sample.is_complete is True
    assert sample.replay_confidence.missing_data_score == 100
    assert sample.replay_confidence.validation_eligible is True


def test_replay_includes_delisted_universe_members(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path, status=SecurityStatus.DELISTED)
    store.upsert_universe_memberships(
        [
            UniverseMembership(
                "china_a_all",
                instrument,
                effective_from=date(2024, 1, 1),
                available_at=datetime(2024, 1, 1, tzinfo=UTC),
                source="test",
                trust_level=DataTrustLevel.HIGH,
                raw_data_hash="d" * 64,
                availability_precision=AvailabilityPrecision.EXACT,
            )
        ]
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(_query(subject_type="universe", universe="china_a_all", symbols=()))

    assert [sample.instrument.symbol for sample in result.samples] == ["600000"]
    assert "security_status_preserved:delisted" in result.samples[0].missing_data_flags


def test_replay_minimum_trust_level_is_enforced(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    query = replace(
        _query(symbols=(instrument.symbol,)),
        minimum_trust_level=DataTrustLevel.VERIFIED,
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(query)

    assert result.manifest.replay_confidence.validation_eligible is False
    assert "below required verified" in " ".join(result.manifest.replay_confidence.blocking_reasons)
    with pytest.raises(ValueError, match="below required verified"):
        _validation_request(result)


def test_replay_unsuitable_dataset_blocks_validation(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    store.save_pit_readiness_assessment(
        _readiness_assessment(
            "daily_bars",
            assessed_at=datetime(2024, 1, 2, tzinfo=UTC),
            classification=PITReadinessClassification.UNSUITABLE,
        )
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(_query(symbols=(instrument.symbol,)))

    assert result.manifest.replay_confidence.validation_eligible is False
    assert "PIT readiness for daily_bars is unsuitable" in (
        result.manifest.replay_confidence.blocking_reasons
    )
    with pytest.raises(ValueError, match="daily_bars is unsuitable"):
        _validation_request(result)


def test_replay_requires_readiness_for_every_declared_dataset(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    query = replace(
        _query(symbols=(instrument.symbol,)),
        readiness_datasets=("fundamentals", "universe_membership"),
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(query)

    assert result.manifest.replay_confidence.validation_eligible is False
    assert "missing PIT readiness assessment for universe_membership" in (
        result.manifest.replay_confidence.blocking_reasons
    )


def test_replay_uses_readiness_visible_at_generation_time(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    store.save_pit_readiness_assessment(
        _readiness_assessment(
            "daily_bars",
            assessed_at=datetime(2026, 1, 1, tzinfo=UTC),
            classification=PITReadinessClassification.UNSUITABLE,
        )
    )

    result = HistoricalReplayBuilder(
        SQLiteHistoricalReplayRepository(store),
        persist=False,
    ).build(
        _query(symbols=(instrument.symbol,)),
        generated_at=datetime(2025, 2, 1, tzinfo=UTC),
    )

    assert result.manifest.replay_confidence.validation_eligible is True
    assert result.manifest.dataset_versions["daily_bars"] == (
        _readiness_assessment("daily_bars").model_version
    )


def test_replay_rejects_hidden_incomplete_sample_filter() -> None:
    with pytest.raises(ValueError, match="must preserve incomplete samples"):
        replace(_query(), include_incomplete_samples=False)


def test_replay_rejects_weak_minimum_trust_policy() -> None:
    with pytest.raises(ValueError, match="at least medium data trust"):
        replace(_query(), minimum_trust_level=DataTrustLevel.LOW)


@pytest.mark.parametrize(
    "overrides",
    (
        {"provider_dataset": "instrument_status_suspended"},
        {"source": "akshare:stock_zh_a_stop_em"},
        {"raw_data_hash": "s" * 64},
        {"availability_precision": AvailabilityPrecision.UNKNOWN},
        {"availability_precision": AvailabilityPrecision.RETRIEVAL_TIME},
        {"trust_level": DataTrustLevel.LOW},
    ),
)
def test_unusable_status_cannot_enter_validation_even_with_usable_dataset_labels(
    tmp_path: Path,
    overrides,
) -> None:
    store, instrument = _prepared_store(tmp_path)
    _add_status_version(store, instrument, **overrides)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query()
    )
    sample = result.samples[0]
    assert sample.decision_context["status"] == "listed"
    assert sample.decision_context["status_record"] is not None
    assert sample.validation_sample is not None  # Preserve research/outcome for diagnosis.
    assert "instrument_status_review_blocked" in sample.missing_data_flags
    assert not sample.is_complete
    assert not sample.replay_confidence.validation_eligible
    assert not result.manifest.replay_confidence.validation_eligible
    with pytest.raises(ValueError, match="not eligible for Validation"):
        _validation_request(result)


def test_optional_status_cannot_hide_a_known_invalid_record(tmp_path: Path) -> None:
    store, instrument = _prepared_store(tmp_path)
    _add_status_version(store, instrument, provider_dataset="instrument_status_suspended")
    query = replace(_query(), required_inputs=("outcome",))
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        query
    )
    assert result.samples[0].replay_confidence.missing_data_score == 100
    assert not result.samples[0].is_complete
    with pytest.raises(ValueError, match="instrument_status_review_blocked"):
        _validation_request(result)


@pytest.mark.parametrize(
    "status",
    (
        SecurityStatus.SPECIAL_TREATMENT,
        SecurityStatus.SUSPENDED,
        SecurityStatus.DELISTED,
    ),
)
def test_valid_adverse_status_is_not_a_missing_or_quarantined_sample(
    tmp_path: Path, status
) -> None:
    store, _ = _prepared_store(tmp_path, status=status)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query(), generated_at=datetime(2025, 2, 1, tzinfo=UTC)
    )
    sample = result.samples[0]
    assert sample.is_complete
    assert sample.replay_confidence.validation_eligible
    assert f"security_status_preserved:{status.value}" in sample.missing_data_flags
    assert _validation_request(result).samples


@pytest.mark.parametrize(
    "tamper",
    (
        "review_missing",
        "hash",
        "source",
        "as_of",
        "version",
        "reason",
        "instrument",
        "status_missing",
    ),
)
def test_request_factory_rechecks_review_even_when_flags_and_confidence_look_valid(
    tmp_path: Path,
    tamper: str,
) -> None:
    store, _ = _prepared_store(tmp_path)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query()
    )
    sample = result.samples[0]
    context = dict(sample.decision_context)
    review = dict(context["status_review"])
    record = dict(context["status_record"])
    if tamper == "review_missing":
        context.pop("status_review")
    elif tamper == "status_missing":
        context.pop("status")
    elif tamper == "hash":
        review["record_hash"] = "f" * 64
    elif tamper == "source":
        record["source"] = "substituted"
    elif tamper == "as_of":
        review["as_of"] = result.query.outcome_as_of.isoformat()
    elif tamper == "version":
        review["model_version"] = "legacy-unreviewed"
    elif tamper == "instrument":
        record["instrument"] = {**record["instrument"], "symbol": "600001"}
        review["record_hash"] = stable_hash(record)
    else:
        review["reasons"] = ["legacy_delisted_quote_status"]
    if tamper != "review_missing":
        context["status_review"] = review
    context["status_record"] = record
    changed = replace(
        result, samples=(replace(sample, decision_context=context, missing_data_flags=()),)
    )
    with pytest.raises(ValueError, match="security status review failed"):
        _validation_request(changed)


def test_status_provenance_changes_replay_identity_without_changing_the_status_label(
    tmp_path: Path,
):
    store, instrument = _prepared_store(tmp_path)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False)
    first = builder.build(_query())
    _add_status_version(store, instrument, raw_data_hash="b" * 64)
    second = builder.build(_query())
    assert (
        first.samples[0].decision_context["status"] == second.samples[0].decision_context["status"]
    )
    assert first.samples[0].replay_hash != second.samples[0].replay_hash


def test_old_replay_version_cannot_silently_acquire_current_approval(tmp_path: Path):
    store, _ = _prepared_store(tmp_path)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query()
    )
    legacy = replace(
        result, manifest=replace(result.manifest, model_version="historical-replay-v0.6.3.1")
    )
    with pytest.raises(ValueError, match="requires reconstruction"):
        _validation_request(legacy)


def test_replay_manifest_and_samples_roll_back_together_on_failure(tmp_path: Path, monkeypatch):
    store, _ = _prepared_store(tmp_path)

    def fail(**kwargs):
        raise RuntimeError("synthetic replay sample failure")

    monkeypatch.setattr(store, "save_historical_replay_sample", fail)
    with pytest.raises(RuntimeError, match="sample failure"):
        HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store)).build(_query())
    assert store.table_count("historical_replay_manifests") == 0
    assert store.table_count("historical_replay_samples") == 0


def test_replay_reconstruction_uses_one_snapshot_across_component_reads(
    tmp_path: Path, monkeypatch
):
    store, instrument = _prepared_store(tmp_path)
    writer = SQLiteStore(store.path)
    original = SQLiteHistoricalReplayRepository.instrument_status
    injected = False

    def concurrent_write(self, *args, **kwargs):
        nonlocal injected
        status = original(self, *args, **kwargs)
        if not injected:
            writer.save_screening_result(
                instrument=instrument,
                dimension="growth",
                evaluated_at=datetime(2024, 1, 13, tzinfo=UTC),
                available_at=datetime(2024, 1, 13, tzinfo=UTC),
                passed=True,
                score=70,
                reasons=("synthetic concurrent write",),
                features={},
                source="test",
                model_version="test",
            )
            injected = True
        return status

    monkeypatch.setattr(SQLiteHistoricalReplayRepository, "instrument_status", concurrent_write)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False)
    first = builder.build(_query())
    second = builder.build(_query())
    assert first.samples[0].decision_context["screening_count"] == 1
    assert second.samples[0].decision_context["screening_count"] == 2


def test_future_status_version_does_not_replace_decision_time_evidence(tmp_path: Path):
    store, instrument = _prepared_store(tmp_path)
    original = store.instrument_status(
        instrument.symbol,
        instrument.market,
        instrument.asset_type,
        on_date=date(2024, 1, 15),
        as_of=_query().decision_as_of,
    )
    assert original is not None
    store.upsert_instrument_statuses(
        (
            replace(
                original,
                available_at=datetime(2024, 1, 16, tzinfo=UTC),
                provider_dataset="instrument_status_suspended",
            ),
        )
    )
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query()
    )
    assert result.samples[0].decision_context["status_record"]["provider_dataset"] == ""
    assert result.samples[0].replay_confidence.validation_eligible


def test_replay_rejects_an_unzoned_generation_clock(tmp_path: Path):
    store, _ = _prepared_store(tmp_path)
    with pytest.raises(ValueError, match="timezone"):
        HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store)).build(
            _query(), generated_at=datetime(2025, 2, 1)
        )


@pytest.mark.parametrize("boundary", ("start", "end", "both"))
def test_replay_never_substitutes_nearby_bars_for_exact_boundaries(tmp_path: Path, boundary):
    store, instrument = _prepared_store(tmp_path)
    query = _query()
    start = datetime(2024, 1, 14, tzinfo=UTC) if boundary != "end" else query.decision_as_of
    end = datetime(2024, 2, 14, tzinfo=UTC) if boundary != "start" else query.outcome_as_of
    definition = replace(query.outcome_definitions[0], observation_horizon_days=(end - start).days)
    query = replace(query, decision_as_of=start, outcome_definitions=(definition,))
    store.upsert_daily_bars((_bar(instrument, date(2024, 2, 13), "11"),))
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store)).build(query)
    sample = result.samples[0]
    reasons = sample.outcome_context["blocking_reasons"]
    if boundary != "end":
        assert "decision_bar_missing" in reasons
    if boundary != "start":
        assert "outcome_bar_missing" in reasons
    assert sample.outcome_context["value"] is None
    assert sample.validation_sample is None
    assert not sample.is_complete
    assert not result.manifest.replay_confidence.validation_eligible
    assert store.table_count("historical_replay_samples") == 1


def test_outcome_does_not_use_a_future_revision_of_the_decision_price(tmp_path: Path):
    store, instrument = _prepared_store(tmp_path)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False)
    first = builder.build(_query())
    store.upsert_daily_bars(
        (
            replace(
                _bar(instrument, date(2024, 1, 15), "6"),
                available_at=datetime(2024, 1, 16, tzinfo=UTC),
            ),
        )
    )
    second = builder.build(_query())
    assert first.samples[0].replay_hash == second.samples[0].replay_hash
    assert second.samples[0].outcome_context["value"] == 20
    assert second.samples[0].outcome_context["decision_bar"]["content"]["close"] == "10"


def test_outcome_revision_changes_identity_but_never_overwrites_an_old_run(tmp_path: Path):
    store, instrument = _prepared_store(tmp_path)
    query = replace(_query(), outcome_as_of=datetime(2024, 2, 17, tzinfo=UTC))
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store))
    generated = datetime(2025, 2, 1, tzinfo=UTC)
    first = builder.build(query, generated_at=generated)
    store.upsert_daily_bars(
        (
            replace(
                _bar(instrument, date(2024, 2, 15), "13"),
                available_at=datetime(2024, 2, 16, tzinfo=UTC),
            ),
        )
    )
    second = builder.build(query, generated_at=generated)
    assert first.samples[0].outcome_context["value"] == 20
    assert second.samples[0].outcome_context["value"] == 30
    assert first.manifest.manifest_id != second.manifest.manifest_id
    assert first.samples[0].sample_id != second.samples[0].sample_id
    assert store.table_count("historical_replay_manifests") == 2
    with sqlite3.connect(store.path) as connection:
        rows = connection.execute(
            "SELECT sample_id, manifest_id, outcome_context_json FROM historical_replay_samples"
        ).fetchall()
    assert {row[0]: row[1] for row in rows} == {
        first.samples[0].sample_id: first.manifest.manifest_id,
        second.samples[0].sample_id: second.manifest.manifest_id,
    }
    assert sorted(json.loads(row[2])["value"] for row in rows) == [20, 30]


def test_identical_sample_content_has_distinct_immutable_run_ownership(tmp_path: Path):
    store, _ = _prepared_store(tmp_path)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store))
    first = builder.build(_query(), generated_at=datetime(2025, 2, 1, tzinfo=UTC))
    second = builder.build(_query(), generated_at=datetime(2025, 2, 2, tzinfo=UTC))
    assert first.samples[0].replay_hash == second.samples[0].replay_hash
    assert first.manifest.manifest_id != second.manifest.manifest_id
    assert first.samples[0].sample_id != second.samples[0].sample_id
    assert store.table_count("historical_replay_samples") == 2


@pytest.mark.parametrize("target", ("manifest", "sample", "sample_owner", "orphan"))
def test_replay_repository_rejects_overwrite_and_relink_atomically(tmp_path: Path, target):
    store, _ = _prepared_store(tmp_path)
    repository = SQLiteHistoricalReplayRepository(store)
    result = HistoricalReplayBuilder(repository).build(_query())
    sample = result.samples[0]
    if target == "manifest":
        changed = replace(result, manifest=replace(result.manifest, git_commit="changed"))
        message = "manifest identity conflict"
    elif target == "sample":
        changed = replace(result, samples=(replace(sample, evidence_references=("changed",)),))
        message = "sample identity conflict"
    else:
        changed = replace(
            result,
            manifest=replace(
                result.manifest,
                manifest_id="new-manifest",
                input_hashes={} if target == "orphan" else result.manifest.input_hashes,
            ),
        )
        message = "not bound to its manifest" if target == "orphan" else "sample identity conflict"
    with pytest.raises(ValueError, match=message):
        repository.save_result(changed)
    assert store.table_count("historical_replay_manifests") == 1
    assert store.table_count("historical_replay_samples") == 1
    repository.save_result(result)  # Exact retries still succeed after conflict rollback.


@pytest.mark.parametrize("lag", (0, 2))
def test_outcome_horizon_and_availability_lag_are_enforced(tmp_path: Path, lag: int):
    store, _ = _prepared_store(tmp_path)
    query = _query()
    definition = replace(query.outcome_definitions[0], availability_lag_days=lag)
    ready_at = query.outcome_as_of + timedelta(days=lag)
    early = replace(
        query, outcome_as_of=ready_at - timedelta(seconds=1), outcome_definitions=(definition,)
    )
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False)
    sample = builder.build(early).samples[0]
    assert "outcome_not_matured" in sample.outcome_context["blocking_reasons"]
    assert sample.outcome_context["value"] is None
    ready = builder.build(replace(early, outcome_as_of=ready_at)).samples[0]
    assert ready.outcome_context["value"] == 20
    assert ready.validation_sample.outcome.observed_at == query.outcome_as_of
    assert ready.validation_sample.outcome.available_at == ready_at


@pytest.mark.parametrize("unsupported", ("benchmark", "metric"))
def test_unsupported_outcome_semantics_cannot_silently_produce_returns(tmp_path: Path, unsupported):
    store, _ = _prepared_store(tmp_path)
    query = _query()
    definition = replace(
        query.outcome_definitions[0],
        **(
            {"benchmark": "CSI300"}
            if unsupported == "benchmark"
            else {"target_metric": "total_return"}
        ),
    )
    query = replace(query, required_inputs=("fundamentals",), outcome_definitions=(definition,))
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        query
    )
    assert "outcome_review_blocked" in result.samples[0].missing_data_flags
    assert not result.samples[0].replay_confidence.validation_eligible
    assert not result.manifest.replay_confidence.validation_eligible


@pytest.mark.parametrize("tamper", ("price", "date", "hash", "value", "definition", "missing"))
def test_validation_request_independently_rechecks_bound_outcome(tmp_path: Path, tamper):
    store, _ = _prepared_store(tmp_path)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query(), generated_at=datetime(2025, 2, 1, tzinfo=UTC)
    )
    sample = result.samples[0]
    context = json.loads(json.dumps(sample.outcome_context))
    if tamper == "price":
        context["decision_bar"]["content"]["close"] = "5"
    elif tamper == "date":
        context["expected_end_date"] = "2024-02-14"
    elif tamper == "hash":
        context["outcome_bar"]["content_hash"] = "f" * 64
    elif tamper == "value":
        context["value"] = 100
    elif tamper == "definition":
        context["definition"]["observation_horizon_days"] = 30
    else:
        context["decision_bar"] = None
    changed = replace(
        result, samples=(replace(sample, outcome_context=context, missing_data_flags=()),)
    )
    with pytest.raises(ValueError, match="outcome review failed"):
        _validation_request(changed)


@pytest.mark.parametrize(
    "invalid", ("adjustment", "source", "zero", "future", "wrong_date", "instrument", "infinity")
)
def test_outcome_rejects_invalid_price_inputs(tmp_path: Path, invalid):
    _, instrument = _prepared_store(tmp_path)
    decision = _bar(instrument, date(2024, 1, 15), "0" if invalid == "zero" else "10")
    if invalid == "adjustment":
        decision = replace(decision, adjustment=Adjustment.FORWARD)
    elif invalid == "source":
        decision = replace(decision, source="")
    elif invalid == "future":
        decision = replace(decision, available_at=datetime(2024, 1, 16, tzinfo=UTC))
    elif invalid == "wrong_date":
        decision = _bar(instrument, date(2024, 1, 14), "10")
    elif invalid == "instrument":
        decision = replace(decision, instrument=replace(instrument, symbol="600001"))
    elif invalid == "infinity":
        decision = replace(decision, volume=Decimal("Infinity"))
    outcome, context = evaluate_outcome(
        _query(),
        instrument,
        _query().outcome_definitions[0],
        decision,
        _bar(instrument, date(2024, 2, 15), "12"),
    )
    assert outcome.value is None
    assert context["blocking_reasons"]


@pytest.mark.parametrize("duplicate", ("symbols", "outcome_ids"))
def test_replay_rejects_ambiguous_duplicate_sample_identities(duplicate):
    query = _query()
    with pytest.raises(ValueError, match="must be unique"):
        replace(
            query,
            **(
                {"symbols": ("600000", "600000")}
                if duplicate == "symbols"
                else {"outcome_definitions": query.outcome_definitions * 2}
            ),
        )


@pytest.mark.parametrize(
    "table,column,value",
    (
        ("research_reports", "thesis", "A changed thesis under the same id"),
        ("research_reports", "counter_thesis", "A changed counter thesis"),
        ("research_reports", "model_version", "research-test-v2"),
        ("research_reports", "key_findings_json", '["changed finding"]'),
        ("research_reports", "unresolved_questions_json", '["new uncertainty"]'),
        ("research_evidence", "value_json", "101"),
        ("research_evidence", "input_hash", "d" * 64),
        ("research_evidence", "source_reference", "changed-source-document"),
        ("research_evidence", "quality", EvidenceQuality.SECONDARY.value),
        ("research_evidence", "calculation_version", "calculation-v2"),
        ("research_evidence", "metadata_json", '{"revision":2}'),
        ("research_assessments", "score", 65),
        ("research_assessments", "features_json", '{"value":65}'),
        ("research_assessments", "findings_json", '["changed assessment finding"]'),
        ("research_assessments", "model_version", "value-test-v2"),
        ("fundamental_facts", "value", "101"),
        ("fundamental_facts", "raw_data_hash", "b" * 64),
        ("screening_results", "score", 65),
        ("screening_results", "features_json", '{"debt":"changed"}'),
    ),
)
def test_same_id_content_changes_create_new_replay_without_replacing_the_snapshot(
    tmp_path: Path, table, column, value
):
    store, _ = _prepared_store(tmp_path)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store))
    generated = datetime(2025, 2, 1, tzinfo=UTC)
    first = builder.build(_query(), generated_at=generated)
    # Simulate an upstream legacy overwrite in this isolated fixture database only.
    with sqlite3.connect(store.path) as connection:
        connection.execute(f"UPDATE {table} SET {column} = ?", (value,))
    second = builder.build(_query(), generated_at=generated)
    assert first.samples[0].replay_hash != second.samples[0].replay_hash
    assert first.manifest.manifest_id != second.manifest.manifest_id
    assert store.table_count("historical_replay_samples") == 2
    with sqlite3.connect(store.path) as connection:
        saved = connection.execute(
            "SELECT decision_context_json FROM historical_replay_samples WHERE sample_id = ?",
            (first.samples[0].sample_id,),
        ).fetchone()
    assert json.loads(saved[0]) == json.loads(json.dumps(first.samples[0].decision_context))
    assert _validation_request(first).samples  # Frozen report remains usable without a DB reread.
    assert _validation_request(second).samples


@pytest.mark.parametrize(
    "defect", ("missing_reference", "future_evidence", "late_assessment", "duplicate")
)
def test_bad_nested_research_stays_visible_but_cannot_be_validated(tmp_path: Path, defect):
    store, _ = _prepared_store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        if defect == "missing_reference":
            connection.execute(
                "UPDATE research_assessments SET evidence_ids_json = ?", ('["missing"]',)
            )
        elif defect == "future_evidence":
            connection.execute(
                "UPDATE research_evidence SET available_at = ?", ("2024-01-16T00:00:00+00:00",)
            )
        elif defect == "late_assessment":
            connection.execute(
                "UPDATE research_assessments SET evaluated_at = ?, available_at = ?",
                ("2024-01-16T00:00:00+00:00", "2024-01-16T00:00:00+00:00"),
            )
        else:
            connection.execute("""
                INSERT INTO research_assessments
                SELECT 'duplicate-assessment', run_id, report_id, module, conclusion,
                       score, confidence_json, evaluated_at, available_at, findings_json,
                       risks_json, limitations_json, evidence_ids_json, features_json,
                       model_version, ingested_at FROM research_assessments
            """)
    query = replace(_query(), required_inputs=("outcome",))
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store)).build(query)
    sample = result.samples[0]
    snapshot = sample.decision_context["research_snapshot"]
    assert snapshot["blocking_reasons"]
    assert snapshot["report_hash"]
    assert snapshot["report"] is None  # Rejected/future child content is not a decision input.
    assert "research_review_blocked" in sample.missing_data_flags
    assert not sample.is_complete
    assert not sample.replay_confidence.validation_eligible
    assert not result.manifest.replay_confidence.validation_eligible
    assert sample.validation_sample is None
    assert store.table_count("historical_replay_samples") == 1
    with pytest.raises(ValueError, match="research content review failed"):
        _validation_request(result)


@pytest.mark.parametrize("field", [
    "report_generated", "report_available", "assessment_evaluated", "assessment_available",
    "evidence_observed", "evidence_available",
])
@pytest.mark.parametrize("utc_cutoff", [False, True])
def test_replay_research_snapshot_rejects_future_repeated_hour_evidence(
    tmp_path, field, utc_cutoff
):
    store, instrument = _prepared_store(tmp_path)
    original = SQLiteHistoricalReplayRepository(store).research_report(
        instrument, _query().decision_as_of
    )
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    later = first.replace(fold=1)
    evidence = replace(original.assessments[0].evidence[0], observed_at=first, available_at=first)
    assessment = replace(original.assessments[0], evaluated_at=first, available_at=first,
                         evidence=(evidence,))
    report = replace(original, generated_at=first, available_at=first, assessments=(assessment,))
    # Replay must revalidate retained models, even if nested legacy values bypass constructors.
    target, name = {
        "report_generated": (report, "generated_at"),
        "report_available": (report, "available_at"),
        "assessment_evaluated": (assessment, "evaluated_at"),
        "assessment_available": (assessment, "available_at"),
        "evidence_observed": (evidence, "observed_at"),
        "evidence_available": (evidence, "available_at"),
    }[field]
    object.__setattr__(target, name, later)
    snapshot = research_snapshot(report, decision_at=first.astimezone(UTC) if utc_cutoff
                                 else first, instrument_id=report.instrument_id)
    assert snapshot["blocking_reasons"]
    assert snapshot["report"] is None
    assert snapshot["report_hash"]
    assert getattr(target, name) is later


def test_replay_research_snapshot_accepts_equivalent_cutoff_instants(tmp_path):
    store, instrument = _prepared_store(tmp_path)
    report = SQLiteHistoricalReplayRepository(store).research_report(
        instrument, _query().decision_as_of
    )
    cutoff = _query().decision_as_of.astimezone(ZoneInfo("America/New_York"))
    snapshot = research_snapshot(report, decision_at=cutoff, instrument_id=report.instrument_id)
    assert snapshot["blocking_reasons"] == []
    assert snapshot["report"] is not None


def test_replay_research_snapshot_rejects_naive_decision_cutoff():
    with pytest.raises(ValueError, match="timezone"):
        research_snapshot(None, decision_at=datetime(2026, 11, 1), instrument_id="synthetic")


@pytest.mark.parametrize(
    "tamper",
    (
        "thesis",
        "evidence",
        "snapshot",
        "snapshot_and_report",
        "factor_scores",
        "expected_success",
        "evidence_references",
        "input_hash",
        "manifest",
        "query",
        "instrument",
    ),
)
def test_request_rechecks_full_research_content_and_derived_values(tmp_path: Path, tamper):
    store, _ = _prepared_store(tmp_path)
    result = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False).build(
        _query(), generated_at=datetime(2025, 2, 1, tzinfo=UTC)
    )
    sample = result.samples[0]
    validation = sample.validation_sample
    context = deepcopy(sample.decision_context)
    report = validation.research_report
    if tamper in {"thesis", "snapshot_and_report"}:
        report = replace(report, thesis="substituted thesis")
        validation = replace(validation, research_report=report)
        if tamper == "snapshot_and_report":
            context["research_snapshot"] = research_snapshot(
                report, decision_at=sample.decision_as_of, instrument_id=report.instrument_id
            )
    elif tamper == "evidence":
        assessment = report.assessments[0]
        assessment = replace(assessment, evidence=(replace(assessment.evidence[0], value=999),))
        validation = replace(validation, research_report=replace(report, assessments=(assessment,)))
    elif tamper == "snapshot":
        context["research_snapshot"]["report"]["thesis"] = "substituted snapshot"
    elif tamper == "factor_scores":
        validation = replace(validation, factor_scores={"value": 100})
    elif tamper == "instrument":
        validation = replace(validation, instrument=replace(sample.instrument, symbol="600001"))
    elif tamper == "expected_success":
        validation = replace(validation, research_expected_success=False)
    elif tamper == "input_hash":
        context["fundamental_inputs"][0]["value"] = "999"
    elif tamper == "manifest":
        result = replace(result, manifest=replace(result.manifest, input_hashes={}))
    elif tamper == "query":
        result = replace(result, query=replace(result.query, configuration_hash="d" * 64))
    sample = replace(
        sample,
        validation_sample=validation,
        decision_context=context,
        evidence_references=() if tamper == "evidence_references" else sample.evidence_references,
    )
    with pytest.raises(ValueError, match="research content review failed|sample binding mismatch"):
        _validation_request(replace(result, samples=(sample,)))


@pytest.mark.parametrize(
    "policy_mode", ("embedded", "referenced", "missing", "conflicting", "future")
)
def test_policy_research_evidence_is_reconstructed_and_bound(tmp_path: Path, policy_mode):
    store, instrument = _prepared_store(tmp_path)
    repository = SQLiteHistoricalReplayRepository(store)
    report = repository.research_report(instrument, _query().decision_as_of)
    assessment = report.assessments[0]
    evidence = assessment.evidence[0]
    record = json.loads(
        json.dumps(
            research_snapshot(
                report, decision_at=_query().decision_as_of, instrument_id=report.instrument_id
            )["report"]["assessments"][0]
        )
    )
    record["module"] = ResearchModuleName.POLICY.value
    if policy_mode == "referenced":
        record.pop("evidence")
    elif policy_mode == "missing":
        record["evidence_ids"] = ["absent-policy-evidence"]
        record["evidence"] = []
    elif policy_mode == "conflicting":
        record["evidence"][0]["value"] = 999
    elif policy_mode == "future":
        record["evidence"][0]["available_at"] = "2024-01-16T00:00:00+00:00"
    policy = {
        "assessment": record,
        "regulatory_environment": "test",
        "industrial_policy": "test",
        "fiscal_policy": "test",
        "monetary_policy": "test",
        "geopolitical_factors": "test",
    }
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE research_reports SET policy_assessment_json = ?", (json.dumps(policy),)
        )
    result = HistoricalReplayBuilder(repository, persist=False).build(
        _query(), generated_at=datetime(2025, 2, 1, tzinfo=UTC)
    )
    sample = result.samples[0]
    if policy_mode in {"missing", "conflicting", "future"}:
        assert "research_review_blocked" in sample.missing_data_flags
        assert not sample.is_complete
    else:
        restored = sample.validation_sample.research_report.policy_assessment
        assert restored.assessment.evidence == (evidence,)
        assert _validation_request(result).samples


@pytest.mark.parametrize("field", ("value", "input_hash", "source_reference", "metadata"))
def test_research_evidence_write_is_idempotent_but_never_replaces_content(tmp_path: Path, field):
    store, instrument = _prepared_store(tmp_path)
    repository = SQLiteHistoricalReplayRepository(store)
    report = repository.research_report(instrument, _query().decision_as_of)
    evidence = report.assessments[0].evidence[0]
    values = {
        "run_id": "run-1",
        "evidence_id": evidence.evidence_id,
        "module": evidence.module.value,
        "name": evidence.name,
        "value": evidence.value,
        "observed_at": evidence.observed_at,
        "available_at": evidence.available_at,
        "source": evidence.source,
        "quality": evidence.quality.value,
        "source_reference": evidence.source_reference,
        "calculation_version": evidence.calculation_version,
        "input_hash": evidence.input_hash,
        "metadata": evidence.metadata,
    }
    store.save_research_evidence(**values)
    altered = {
        **values,
        field: {
            "value": 999,
            "input_hash": "d" * 64,
            "source_reference": "substituted",
            "metadata": {"revision": 2},
        }[field],
    }
    with pytest.raises(ValueError, match="new evidence identity"):
        store.save_research_evidence(**altered)
    restored = repository.research_report(instrument, _query().decision_as_of)
    assert restored == report
    assert store.table_count("research_evidence") == 1
    store.save_research_evidence(**values)


@pytest.mark.parametrize("dataset", ("fundamentals", "screening"))
def test_future_input_revisions_do_not_change_the_decision_snapshot(tmp_path: Path, dataset):
    store, instrument = _prepared_store(tmp_path)
    builder = HistoricalReplayBuilder(SQLiteHistoricalReplayRepository(store), persist=False)
    generated = datetime(2025, 2, 1, tzinfo=UTC)
    first = builder.build(_query(), generated_at=generated)
    future = datetime(2024, 1, 16, tzinfo=UTC)
    if dataset == "fundamentals":
        store.upsert_fundamental_facts(
            (
                FundamentalFact(
                    instrument=instrument,
                    metric="revenue",
                    period_end=date(2023, 12, 31),
                    published_at=future,
                    available_at=future,
                    value=Decimal("999"),
                    source="test",
                    revision=1,
                    raw_data_hash="b" * 64,
                ),
            )
        )
    else:
        store.save_screening_result(
            instrument=instrument,
            dimension="survival",
            evaluated_at=future,
            available_at=future,
            passed=False,
            score=0,
            reasons=("future change",),
            features={},
            source="test",
            model_version="screening-test-v2",
        )
    second = builder.build(_query(), generated_at=generated)
    assert first.samples[0].replay_hash == second.samples[0].replay_hash
    assert first.manifest.manifest_id == second.manifest.manifest_id
    assert _validation_request(second).samples


def _add_status_version(store: SQLiteStore, instrument: Instrument, **overrides) -> None:
    current = store.instrument_status(
        instrument.symbol,
        instrument.market,
        instrument.asset_type,
        on_date=date(2024, 1, 15),
        as_of=_query().decision_as_of,
    )
    assert current is not None
    store.upsert_instrument_statuses(
        (replace(current, available_at=datetime(2024, 1, 2, tzinfo=UTC), **overrides),)
    )


def _prepared_store(
    tmp_path: Path,
    *,
    status: SecurityStatus = SecurityStatus.LISTED,
    research_available_at: datetime = datetime(2024, 1, 14, tzinfo=UTC),
) -> tuple[SQLiteStore, Instrument]:
    store = SQLiteStore(tmp_path / "replay.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=datetime(2024, 1, 1, tzinfo=UTC),
        source="test",
    )
    store.upsert_instruments([instrument])
    store.upsert_instrument_statuses(
        [
            InstrumentStatus(
                instrument,
                effective_from=date(2024, 1, 1),
                status=status,
                is_tradable=status is SecurityStatus.LISTED,
                available_at=datetime(2024, 1, 1, tzinfo=UTC),
                source="test",
                raw_data_hash="a" * 64,
                availability_precision=AvailabilityPrecision.EXACT,
                trust_level=DataTrustLevel.HIGH,
            )
        ]
    )
    store.upsert_fundamental_facts(
        [
            FundamentalFact(
                instrument=instrument,
                metric="revenue",
                period_end=date(2023, 12, 31),
                published_at=datetime(2024, 1, 10, tzinfo=UTC),
                available_at=datetime(2024, 1, 10, tzinfo=UTC),
                value=Decimal("100"),
                source="test",
                raw_data_hash="f" * 64,
                availability_precision=AvailabilityPrecision.EXACT,
                trust_level=DataTrustLevel.HIGH,
            )
        ]
    )
    store.save_screening_result(
        instrument=instrument,
        dimension="survival",
        evaluated_at=datetime(2024, 1, 12, tzinfo=UTC),
        available_at=datetime(2024, 1, 12, tzinfo=UTC),
        passed=True,
        score=80,
        reasons=("passed survival",),
        features={"debt": "manageable"},
        source="test",
        model_version="screening-test",
    )
    store.upsert_daily_bars(
        [
            _bar(instrument, date(2024, 1, 15), "10"),
            _bar(instrument, date(2024, 2, 15), "12"),
        ]
    )
    _save_research_report(store, instrument, research_available_at)
    store.save_provider_limitation(
        ProviderLimitation(
            provider="akshare",
            dataset="fundamentals",
            limitation_code="retrieval_time_publication",
            description="Publication timestamp is provider-limited",
            trust_level=DataTrustLevel.LOW,
            documented_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    for dataset in ("instrument_status", "fundamentals", "daily_bars"):
        store.save_pit_readiness_assessment(_readiness_assessment(dataset))
    return store, instrument


def _readiness_assessment(
    dataset: str,
    *,
    assessed_at: datetime = datetime(2024, 1, 1, tzinfo=UTC),
    classification: PITReadinessClassification = PITReadinessClassification.USABLE,
) -> PITReadinessAssessment:
    usable = classification is PITReadinessClassification.USABLE
    return PITReadinessAssessment(
        dataset=dataset,
        assessed_at=assessed_at,
        coverage_ratio=0.90 if usable else 0.50,
        trust_level=DataTrustLevel.HIGH if usable else DataTrustLevel.LOW,
        missing_critical_fields=() if usable else ("historical_continuity",),
        warnings=("test fixture",),
        ready_for_historical_replay=usable,
        readiness_score=85 if usable else 35,
        classification=classification,
        score_components={
            "coverage": 90 if usable else 50,
            "trust": 75 if usable else 25,
        },
        assumptions=("test fixture",),
    )


def _validation_request(result: HistoricalReplayResult) -> ValidationRequest:
    return ValidationRequestFactory().build(
        result,
        validation_id="validation-from-replay",
        modules=(ValidationModuleName.HISTORICAL,),
        walk_forward_policy=WalkForwardPolicy(
            training_days=30,
            validation_days=10,
            step_days=10,
            embargo_days=1,
        ),
        out_of_sample_policy=OutOfSamplePolicy(
            development_end=date(2024, 1, 14),
            out_of_sample_start=date(2024, 1, 15),
            out_of_sample_end=date(2024, 1, 15),
            frozen_configuration_hash="c" * 64,
        ),
        requested_at=datetime(2025, 2, 2, tzinfo=UTC),
    )


def _save_research_report(
    store: SQLiteStore,
    instrument: Instrument,
    available_at: datetime,
) -> None:
    confidence = {
        "evidence_quality": 80,
        "data_completeness": 80,
        "module_agreement": 80,
        "point_in_time_integrity": 100,
        "confidence": 80,
        "method": "test",
    }
    store.save_research_evidence(
        run_id="run-1",
        evidence_id="evidence-1",
        module=ResearchModuleName.VALUE.value,
        name="revenue",
        value=100,
        observed_at=datetime(2024, 1, 10, tzinfo=UTC),
        available_at=datetime(2024, 1, 10, tzinfo=UTC),
        source="test",
        quality=EvidenceQuality.PRIMARY.value,
        source_reference="test",
        calculation_version="test",
        input_hash="e" * 64,
        metadata={},
    )
    store.save_research_assessment(
        run_id="run-1",
        report_id="report-1",
        module=ResearchModuleName.VALUE.value,
        conclusion=ResearchConclusion.SUPPORTIVE.value,
        score=75,
        confidence=confidence,
        evaluated_at=available_at,
        available_at=available_at,
        findings=("value supportive",),
        risks=("valuation risk",),
        limitations=(),
        evidence_ids=("evidence-1",),
        features={"value": 75},
        model_version="value-test",
    )
    store.save_research_report(
        run_id="run-1",
        report_id="report-1",
        queue_id="queue-1",
        instrument_id_value=(
            f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"
        ),
        generated_at=available_at,
        available_at=available_at,
        status=ResearchRunStatus.COMPLETED,
        thesis="Revenue can grow",
        counter_thesis="Revenue can disappoint",
        invalidation_conditions=[
            {
                "condition_id": "revenue",
                "description": "Revenue declines",
                "metric": "revenue",
                "operator": "<",
                "threshold": 0,
                "observation_window": "annual",
                "rationale": "Growth thesis requires revenue resilience",
            }
        ],
        confidence=confidence,
        key_findings=("good",),
        key_risks=("risk",),
        unresolved_questions=(),
        policy_assessment=None,
        market_regime=None,
        model_version="research-test",
    )


def _bar(instrument: Instrument, trade_date: date, close: str) -> Bar:
    timestamp = datetime.combine(trade_date, datetime.min.time(), tzinfo=UTC)
    price = Decimal(close)
    return Bar(
        instrument=instrument,
        timestamp=timestamp,
        available_at=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1000"),
        source="test",
    )


def _query(
    *,
    subject_type: str = "instrument",
    universe: str | None = None,
    symbols: tuple[str, ...] = ("600000",),
) -> ReplayQuery:
    return ReplayQuery(
        subject_type=subject_type,
        market=Market.CHINA_A,
        universe=universe,
        decision_as_of=datetime(2024, 1, 15, tzinfo=UTC),
        outcome_as_of=datetime(2024, 2, 15, tzinfo=UTC),
        required_inputs=(
            "instrument_status",
            "fundamentals",
            "screening_results",
            "research_report",
            "outcome",
        ),
        readiness_datasets=("instrument_status", "fundamentals", "daily_bars"),
        outcome_definitions=(
            OutcomeDefinition(
                outcome_id="return-31d",
                target_metric="close_return_pct",
                observation_horizon_days=31,
                success_operator=">",
                success_threshold=0,
                availability_lag_days=0,
            ),
        ),
        symbols=symbols,
        provider_limitation_datasets=("fundamentals",),
        configuration_hash="c" * 64,
        git_commit="f7e9f903019688bcc874e7c913dcd99fb852365a",
    )
