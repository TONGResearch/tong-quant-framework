from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AvailabilityPrecision,
    DataTrustLevel,
    EvidenceQuality,
    Market,
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
    WalkForwardPolicy,
)
from tong_quant.validation.replay import HistoricalReplayBuilder, ReplayQuery
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository
from tong_quant.validation.replay.request_factory import ValidationRequestFactory
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
    assert first.manifest.replay_confidence.confidence < 100
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
                raw_data_hash="s" * 64,
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
    store.save_pit_readiness_assessment(
        PITReadinessAssessment(
            dataset="fundamentals",
            assessed_at=datetime(2024, 1, 1, tzinfo=UTC),
            coverage_ratio=0.90,
            trust_level=DataTrustLevel.HIGH,
            missing_critical_fields=(),
            warnings=("partial coverage",),
            ready_for_historical_replay=True,
        )
    )
    return store, instrument


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
            f"{instrument.market.value}:{instrument.asset_type.value}:"
            f"{instrument.symbol}"
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
        outcome_definitions=(
            OutcomeDefinition(
                outcome_id="return-30d",
                target_metric="close_return_pct",
                observation_horizon_days=30,
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
