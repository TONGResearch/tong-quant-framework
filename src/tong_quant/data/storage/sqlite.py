import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import cast
from uuid import uuid4

from tong_quant.data.models import (
    DataAvailabilityWarning,
    IngestionBatch,
    PITReadinessAssessment,
    ProviderLimitation,
    RawDatasetFingerprint,
)
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    FundSubtype,
    InstrumentCategory,
    InvestmentAssessmentStatus,
    Market,
    ResearchQueueStatus,
    ResearchRunStatus,
    ScoreType,
    SecurityStatus,
    ValidationRunStatus,
)
from tong_quant.domain.models import (
    Bar,
    CorporateAction,
    FundamentalFact,
    Instrument,
    InstrumentStatus,
    Signal,
    TradingSession,
    UniverseMembership,
)

SCHEMA_VERSION = "0.6.3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'equity',
    fund_subtype TEXT,
    name TEXT NOT NULL,
    currency TEXT NOT NULL,
    lot_size INTEGER NOT NULL,
    exchange TEXT,
    industry TEXT,
    listing_date TEXT,
    delisting_date TEXT,
    available_at TEXT NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (instrument_id, available_at)
);

CREATE INDEX IF NOT EXISTS idx_instruments_lookup
ON instruments (symbol, market, asset_type, available_at);

CREATE TABLE IF NOT EXISTS daily_bars (
    instrument_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    available_at TEXT NOT NULL,
    open TEXT NOT NULL,
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT NOT NULL,
    turnover TEXT,
    adjustment TEXT NOT NULL,
    is_suspended INTEGER NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (instrument_id, trade_date, adjustment, available_at)
);

CREATE INDEX IF NOT EXISTS idx_daily_bars_pit
ON daily_bars (instrument_id, trade_date, adjustment, available_at);

CREATE TABLE IF NOT EXISTS trading_calendar (
    market TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    is_open INTEGER NOT NULL,
    available_at TEXT NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (market, trade_date, available_at)
);

CREATE INDEX IF NOT EXISTS idx_trading_calendar_pit
ON trading_calendar (market, trade_date, available_at);

CREATE TABLE IF NOT EXISTS fundamental_facts (
    instrument_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT NOT NULL,
    fiscal_period TEXT,
    published_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    value TEXT NOT NULL,
    currency TEXT,
    unit TEXT NOT NULL,
    revision INTEGER NOT NULL,
    source TEXT NOT NULL,
    raw_data_hash TEXT NOT NULL DEFAULT '',
    batch_id TEXT NOT NULL DEFAULT '',
    provider_dataset TEXT NOT NULL DEFAULT '',
    availability_precision TEXT NOT NULL DEFAULT 'unknown',
    trust_level TEXT NOT NULL DEFAULT 'unknown',
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (
        instrument_id, metric, period_end, published_at, revision, available_at,
        raw_data_hash
    )
);

CREATE INDEX IF NOT EXISTS idx_fundamental_facts_pit
ON fundamental_facts (instrument_id, metric, period_end, available_at);

CREATE TABLE IF NOT EXISTS instrument_status_history (
    instrument_id TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    status TEXT NOT NULL,
    is_tradable INTEGER NOT NULL,
    industry TEXT,
    available_at TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_data_hash TEXT NOT NULL DEFAULT '',
    batch_id TEXT NOT NULL DEFAULT '',
    provider_dataset TEXT NOT NULL DEFAULT '',
    availability_precision TEXT NOT NULL DEFAULT 'unknown',
    trust_level TEXT NOT NULL DEFAULT 'unknown',
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (instrument_id, effective_from, available_at, raw_data_hash)
);

CREATE INDEX IF NOT EXISTS idx_instrument_status_pit
ON instrument_status_history (instrument_id, effective_from, effective_to, available_at);

CREATE TABLE IF NOT EXISTS universe_memberships (
    universe TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    available_at TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_data_hash TEXT NOT NULL DEFAULT '',
    batch_id TEXT NOT NULL DEFAULT '',
    provider_dataset TEXT NOT NULL DEFAULT '',
    availability_precision TEXT NOT NULL DEFAULT 'unknown',
    trust_level TEXT NOT NULL DEFAULT 'unknown',
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (universe, instrument_id, effective_from, available_at, raw_data_hash)
);

CREATE INDEX IF NOT EXISTS idx_universe_memberships_pit
ON universe_memberships (
    universe, effective_from, effective_to, available_at, instrument_id
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    available_at TEXT NOT NULL,
    value TEXT,
    cash_amount TEXT,
    ratio TEXT,
    currency TEXT,
    source TEXT NOT NULL,
    raw_data_hash TEXT NOT NULL DEFAULT '',
    batch_id TEXT NOT NULL DEFAULT '',
    provider_dataset TEXT NOT NULL DEFAULT '',
    availability_precision TEXT NOT NULL DEFAULT 'unknown',
    trust_level TEXT NOT NULL DEFAULT 'unknown',
    ingested_at TEXT NOT NULL,
    UNIQUE (
        instrument_id, action_type, effective_date, available_at, raw_data_hash
    )
);

CREATE INDEX IF NOT EXISTS idx_corporate_actions_pit
ON corporate_actions (instrument_id, effective_date, available_at);

CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    raw_response_hash TEXT NOT NULL,
    failure_reason TEXT NOT NULL,
    retry_of TEXT,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_dataset_fingerprints (
    raw_data_hash TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    provider TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_availability_warnings (
    warning_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    warning_code TEXT NOT NULL,
    message TEXT NOT NULL,
    trust_level TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_limitations (
    limitation_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    limitation_code TEXT NOT NULL,
    description TEXT NOT NULL,
    trust_level TEXT NOT NULL,
    documented_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    UNIQUE (provider, dataset, limitation_code)
);

CREATE TABLE IF NOT EXISTS pit_readiness_assessments (
    assessment_id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    assessed_at TEXT NOT NULL,
    coverage_ratio REAL NOT NULL,
    trust_level TEXT NOT NULL,
    missing_critical_fields_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    ready_for_historical_replay INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_replay_manifests (
    manifest_id TEXT PRIMARY KEY,
    query_hash TEXT NOT NULL,
    input_hashes_json TEXT NOT NULL,
    dataset_versions_json TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    framework_version TEXT NOT NULL,
    configuration_hash TEXT NOT NULL,
    git_commit TEXT NOT NULL,
    data_trust_summary_json TEXT NOT NULL,
    provider_limitations_json TEXT NOT NULL,
    missing_data_warnings_json TEXT NOT NULL,
    replay_confidence_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_replay_samples (
    sample_id TEXT PRIMARY KEY,
    manifest_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    decision_as_of TEXT NOT NULL,
    outcome_as_of TEXT NOT NULL,
    replay_hash TEXT NOT NULL,
    replay_confidence_json TEXT NOT NULL,
    decision_context_json TEXT NOT NULL,
    outcome_context_json TEXT NOT NULL,
    evidence_references_json TEXT NOT NULL,
    missing_data_flags_json TEXT NOT NULL,
    provider_limitations_json TEXT NOT NULL,
    data_trust_summary_json TEXT NOT NULL,
    validation_sample_json TEXT,
    is_complete INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_historical_replay_samples_manifest
ON historical_replay_samples (manifest_id, instrument_id);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    source TEXT NOT NULL,
    stage TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    action TEXT NOT NULL,
    strength REAL NOT NULL,
    reasons_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    invalidations_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_pit
ON signals (instrument_id, effective_at, generated_at);

CREATE TABLE IF NOT EXISTS screening_results (
    result_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    passed INTEGER NOT NULL,
    score REAL,
    reasons_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    source TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_screening_results_pit
ON screening_results (instrument_id, dimension, available_at);

CREATE TABLE IF NOT EXISTS research_queue (
    queue_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    discovery_source TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    admitted_at TEXT NOT NULL,
    priority_score REAL NOT NULL,
    urgency_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    research_score REAL NOT NULL,
    status TEXT NOT NULL,
    thesis TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    assigned_to TEXT,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_queue_priority
ON research_queue (status, priority_score DESC, admitted_at);

CREATE TABLE IF NOT EXISTS screening_scorecards (
    score_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    score_type TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    components_json TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_screening_scorecards_pit
ON screening_scorecards (instrument_id, score_type, calculated_at);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    queue_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    researcher TEXT,
    modules_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    failure_reason TEXT,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_runs_queue
ON research_runs (queue_id, started_at);

CREATE TABLE IF NOT EXISTS research_evidence (
    run_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    module TEXT NOT NULL,
    name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    source TEXT NOT NULL,
    quality TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    calculation_version TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_research_evidence_pit
ON research_evidence (run_id, module, available_at);

CREATE TABLE IF NOT EXISTS research_assessments (
    assessment_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    module TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    score REAL,
    confidence_json TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    risks_json TEXT NOT NULL,
    limitations_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_assessments_report
ON research_assessments (report_id, module);

CREATE TABLE IF NOT EXISTS research_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    queue_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    status TEXT NOT NULL,
    thesis TEXT NOT NULL,
    counter_thesis TEXT NOT NULL,
    invalidation_conditions_json TEXT NOT NULL,
    confidence_json TEXT NOT NULL,
    key_findings_json TEXT NOT NULL,
    key_risks_json TEXT NOT NULL,
    unresolved_questions_json TEXT NOT NULL,
    policy_assessment_json TEXT,
    market_regime_json TEXT,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_reports_pit
ON research_reports (instrument_id, available_at);

CREATE TABLE IF NOT EXISTS investment_assessments (
    assessment_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    status TEXT NOT NULL,
    assessed_at TEXT NOT NULL,
    score REAL,
    confidence REAL,
    reasons_json TEXT NOT NULL,
    limitations_json TEXT NOT NULL,
    market_regime_json TEXT,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_investment_assessments_pit
ON investment_assessments (instrument_id, assessed_at);

CREATE TABLE IF NOT EXISTS investment_scores (
    score_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    components_json TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_investment_scores_pit
ON investment_scores (instrument_id, calculated_at);

CREATE TABLE IF NOT EXISTS validation_runs (
    run_id TEXT PRIMARY KEY,
    validation_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    framework_snapshot_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    failure_reason TEXT,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_validation_runs_id
ON validation_runs (validation_id, started_at);

CREATE TABLE IF NOT EXISTS validation_oos_usage (
    oos_key TEXT PRIMARY KEY,
    frozen_configuration_hash TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    use_count INTEGER NOT NULL,
    maximum_uses INTEGER NOT NULL,
    last_used_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_splits (
    run_id TEXT NOT NULL,
    split_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    frozen_configuration_hash TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, split_id)
);

CREATE TABLE IF NOT EXISTS validation_observations (
    run_id TEXT NOT NULL,
    sample_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    research_report_id TEXT NOT NULL,
    decision_at TEXT NOT NULL,
    research_expected_success INTEGER NOT NULL,
    market_regime TEXT,
    factor_scores_json TEXT NOT NULL,
    portfolio_position_json TEXT,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, sample_id)
);

CREATE TABLE IF NOT EXISTS validation_outcomes (
    run_id TEXT NOT NULL,
    outcome_id TEXT NOT NULL,
    definition_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    value REAL,
    benchmark_value REAL,
    succeeded INTEGER,
    thesis_status TEXT NOT NULL,
    invalidation_triggered INTEGER,
    metadata_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, outcome_id)
);

CREATE INDEX IF NOT EXISTS idx_validation_outcomes_pit
ON validation_outcomes (subject_id, available_at);

CREATE TABLE IF NOT EXISTS validation_outcome_definitions (
    run_id TEXT NOT NULL,
    outcome_id TEXT NOT NULL,
    target_metric TEXT NOT NULL,
    observation_horizon_days INTEGER NOT NULL,
    success_operator TEXT NOT NULL,
    success_threshold REAL NOT NULL,
    availability_lag_days INTEGER NOT NULL,
    benchmark TEXT,
    version TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, outcome_id)
);

CREATE TABLE IF NOT EXISTS decision_journal (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    research_report_id TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    disposition TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    confidence REAL NOT NULL,
    decision_maker TEXT NOT NULL,
    framework_snapshot_hash TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_assessments (
    assessment_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    module TEXT NOT NULL,
    status TEXT NOT NULL,
    score REAL,
    confidence REAL NOT NULL,
    sample_size INTEGER NOT NULL,
    evaluated_at TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    risks_json TEXT NOT NULL,
    limitations_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    validation_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    aggregate_status TEXT NOT NULL,
    framework_snapshot_json TEXT NOT NULL,
    known_limitations_json TEXT NOT NULL,
    reproducibility_manifest_json TEXT NOT NULL,
    decision_summary_json TEXT,
    portfolio_risk_json TEXT,
    model_version TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_factor_contributions (
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    factor TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    success_score_gap REAL NOT NULL,
    ablation_brier_delta REAL NOT NULL,
    stable INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, report_id, factor)
);

CREATE TABLE IF NOT EXISTS validation_accuracy_history (
    accuracy_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    brier_score REAL NOT NULL,
    calibration_error REAL NOT NULL,
    high_confidence_failure_rate REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_integrity_checks (
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    module TEXT NOT NULL,
    check_id TEXT NOT NULL,
    passed INTEGER NOT NULL,
    checked_at TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, report_id, module, check_id)
);

CREATE TABLE IF NOT EXISTS validation_portfolio_risk (
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    total_weight REAL NOT NULL,
    maximum_weight REAL NOT NULL,
    hhi REAL NOT NULL,
    category_weights_json TEXT NOT NULL,
    breached INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (run_id, report_id, dimension)
);
"""


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute(
                """
                INSERT INTO schema_metadata (key, value, updated_at)
                VALUES ('schema_version', ?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (SCHEMA_VERSION, _datetime_text(datetime.now(UTC))),
            )

    def upsert_instruments(self, instruments: Iterable[Instrument]) -> int:
        rows = []
        ingested_at = _datetime_text(datetime.now(UTC))
        for instrument in instruments:
            if instrument.available_at is None:
                raise ValueError("stored instruments require available_at")
            rows.append(
                (
                    instrument_id(instrument),
                    instrument.symbol,
                    instrument.market.value,
                    instrument.asset_type.value,
                    instrument.category.value,
                    None if instrument.fund_subtype is None else instrument.fund_subtype.value,
                    instrument.name,
                    instrument.currency,
                    instrument.lot_size,
                    instrument.exchange,
                    instrument.industry,
                    _date_text(instrument.listing_date),
                    _date_text(instrument.delisting_date),
                    _datetime_text(instrument.available_at),
                    instrument.source,
                    ingested_at,
                )
            )
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO instruments (
                    instrument_id, symbol, market, asset_type, category,
                    fund_subtype, name, currency, lot_size, exchange, industry,
                    listing_date, delisting_date, available_at, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (instrument_id, available_at) DO UPDATE SET
                    category = excluded.category,
                    fund_subtype = excluded.fund_subtype,
                    name = CASE
                        WHEN excluded.name = excluded.symbol THEN instruments.name
                        ELSE excluded.name
                    END,
                    currency = excluded.currency,
                    lot_size = excluded.lot_size,
                    exchange = COALESCE(excluded.exchange, instruments.exchange),
                    industry = COALESCE(excluded.industry, instruments.industry),
                    listing_date = COALESCE(excluded.listing_date, instruments.listing_date),
                    delisting_date = COALESCE(excluded.delisting_date, instruments.delisting_date),
                    source = CASE
                        WHEN excluded.industry IS NOT NULL THEN excluded.source
                        ELSE instruments.source
                    END,
                    ingested_at = excluded.ingested_at
                """,
                rows,
            )
        return len(rows)

    def upsert_daily_bars(self, bars: Iterable[Bar]) -> int:
        rows = []
        for bar in bars:
            rows.append(
                (
                    instrument_id(bar.instrument),
                    bar.timestamp.date().isoformat(),
                    _datetime_text(bar.timestamp),
                    _datetime_text(bar.available_at),
                    str(bar.open),
                    str(bar.high),
                    str(bar.low),
                    str(bar.close),
                    str(bar.volume),
                    None if bar.turnover is None else str(bar.turnover),
                    bar.adjustment.value,
                    int(bar.is_suspended),
                    bar.source,
                    _datetime_text(bar.ingested_at or datetime.now(UTC)),
                )
            )
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO daily_bars (
                    instrument_id, trade_date, timestamp, available_at,
                    open, high, low, close, volume, turnover, adjustment,
                    is_suspended, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def upsert_trading_sessions(self, sessions: Iterable[TradingSession]) -> int:
        ingested_at = _datetime_text(datetime.now(UTC))
        rows = [
            (
                session.market.value,
                session.trade_date.isoformat(),
                int(session.is_open),
                _datetime_text(session.available_at),
                session.source,
                ingested_at,
            )
            for session in sessions
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO trading_calendar (
                    market, trade_date, is_open, available_at, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def upsert_fundamental_facts(self, facts: Iterable[FundamentalFact]) -> int:
        ingested_at = _datetime_text(datetime.now(UTC))
        rows = [
            (
                instrument_id(fact.instrument),
                fact.metric,
                _date_text(fact.period_start),
                fact.period_end.isoformat(),
                fact.fiscal_period,
                _datetime_text(fact.published_at),
                _datetime_text(fact.available_at),
                str(fact.value),
                fact.currency,
                fact.unit,
                fact.revision,
                fact.source,
                fact.raw_data_hash,
                fact.batch_id,
                fact.provider_dataset,
                fact.availability_precision.value,
                fact.trust_level.value,
                ingested_at,
            )
            for fact in facts
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            for row in rows:
                conflict = connection.execute(
                    """
                    SELECT raw_data_hash
                    FROM fundamental_facts
                    WHERE instrument_id = ?
                      AND metric = ?
                      AND period_end = ?
                      AND published_at = ?
                      AND revision = ?
                      AND available_at = ?
                      AND raw_data_hash <> ?
                    LIMIT 1
                    """,
                    (row[0], row[1], row[3], row[5], row[10], row[6], row[12]),
                ).fetchone()
                if conflict is not None:
                    raise ValueError(
                        "fundamental fact raw hash conflict requires a new revision"
                    )
            connection.executemany(
                """
                INSERT OR IGNORE INTO fundamental_facts (
                    instrument_id, metric, period_start, period_end,
                    fiscal_period, published_at, available_at, value,
                    currency, unit, revision, source, raw_data_hash, batch_id,
                    provider_dataset, availability_precision, trust_level, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def upsert_instrument_statuses(
        self,
        statuses: Iterable[InstrumentStatus],
    ) -> int:
        ingested_at = _datetime_text(datetime.now(UTC))
        rows = [
            (
                instrument_id(status.instrument),
                status.effective_from.isoformat(),
                _date_text(status.effective_to),
                status.status.value,
                int(status.is_tradable),
                status.industry,
                _datetime_text(status.available_at),
                status.source,
                status.raw_data_hash,
                status.batch_id,
                status.provider_dataset,
                status.availability_precision.value,
                status.trust_level.value,
                ingested_at,
            )
            for status in statuses
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            for row in rows:
                conflict = connection.execute(
                    """
                    SELECT raw_data_hash
                    FROM instrument_status_history
                    WHERE instrument_id = ?
                      AND effective_from = ?
                      AND available_at = ?
                      AND raw_data_hash <> ?
                    LIMIT 1
                    """,
                    (row[0], row[1], row[6], row[8]),
                ).fetchone()
                if conflict is not None:
                    raise ValueError(
                        "instrument status raw hash conflict requires a new version"
                    )
            connection.executemany(
                """
                INSERT OR IGNORE INTO instrument_status_history (
                    instrument_id, effective_from, effective_to, status,
                    is_tradable, industry, available_at, source, raw_data_hash,
                    batch_id, provider_dataset, availability_precision, trust_level,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def upsert_universe_memberships(
        self,
        memberships: Iterable[UniverseMembership],
    ) -> int:
        ingested_at = _datetime_text(datetime.now(UTC))
        rows = [
            (
                membership.universe,
                instrument_id(membership.instrument),
                membership.effective_from.isoformat(),
                _date_text(membership.effective_to),
                _datetime_text(membership.available_at),
                membership.source,
                membership.raw_data_hash,
                membership.batch_id,
                membership.provider_dataset,
                membership.availability_precision.value,
                membership.trust_level.value,
                ingested_at,
            )
            for membership in memberships
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            for row in rows:
                conflict = connection.execute(
                    """
                    SELECT raw_data_hash
                    FROM universe_memberships
                    WHERE universe = ?
                      AND instrument_id = ?
                      AND effective_from = ?
                      AND available_at = ?
                      AND raw_data_hash <> ?
                    LIMIT 1
                    """,
                    (row[0], row[1], row[2], row[4], row[6]),
                ).fetchone()
                if conflict is not None:
                    raise ValueError(
                        "universe membership raw hash conflict requires a new version"
                    )
            connection.executemany(
                """
                INSERT OR IGNORE INTO universe_memberships (
                    universe, instrument_id, effective_from, effective_to,
                    available_at, source, raw_data_hash, batch_id,
                    provider_dataset, availability_precision, trust_level,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def upsert_corporate_actions(
        self,
        actions: Iterable[CorporateAction],
    ) -> int:
        ingested_at = _datetime_text(datetime.now(UTC))
        rows = [
            (
                str(uuid4()),
                instrument_id(action.instrument),
                action.action_type.value,
                action.effective_date.isoformat(),
                _datetime_text(action.available_at),
                None if action.value is None else str(action.value),
                None if action.cash_amount is None else str(action.cash_amount),
                None if action.ratio is None else str(action.ratio),
                action.currency,
                action.source,
                action.raw_data_hash,
                action.batch_id,
                action.provider_dataset,
                action.availability_precision.value,
                action.trust_level.value,
                ingested_at,
            )
            for action in actions
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO corporate_actions (
                    action_id, instrument_id, action_type, effective_date,
                    available_at, value, cash_amount, ratio, currency, source,
                    raw_data_hash, batch_id, provider_dataset, availability_precision,
                    trust_level, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def save_ingestion_batch(self, batch: IngestionBatch) -> str:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ingestion_batches (
                    batch_id, provider, dataset, started_at, completed_at, status,
                    parameters_json, raw_response_hash, failure_reason, retry_of,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (batch_id) DO UPDATE SET
                    completed_at = excluded.completed_at,
                    status = excluded.status,
                    failure_reason = excluded.failure_reason,
                    raw_response_hash = excluded.raw_response_hash,
                    ingested_at = excluded.ingested_at
                """,
                (
                    batch.batch_id,
                    batch.provider,
                    batch.dataset,
                    _datetime_text(batch.started_at),
                    None if batch.completed_at is None else _datetime_text(batch.completed_at),
                    batch.status.value,
                    _json_dumps(batch.parameters),
                    batch.raw_response_hash,
                    batch.failure_reason,
                    batch.retry_of,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return batch.batch_id

    def save_raw_dataset_fingerprint(
        self,
        fingerprint: RawDatasetFingerprint,
    ) -> str:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO raw_dataset_fingerprints (
                    raw_data_hash, dataset, provider, retrieved_at, parameters_json,
                    row_count, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint.raw_data_hash,
                    fingerprint.dataset,
                    fingerprint.provider,
                    _datetime_text(fingerprint.retrieved_at),
                    _json_dumps(fingerprint.parameters),
                    fingerprint.row_count,
                    fingerprint.source,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return fingerprint.raw_data_hash

    def save_data_availability_warning(
        self,
        warning: DataAvailabilityWarning,
    ) -> str:
        warning_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO data_availability_warnings (
                    warning_id, batch_id, dataset, instrument_id, warning_code,
                    message, trust_level, created_at, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    warning_id,
                    warning.batch_id,
                    warning.dataset,
                    warning.instrument_id,
                    warning.warning_code,
                    warning.message,
                    warning.trust_level.value,
                    _datetime_text(warning.created_at),
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return warning_id

    def save_provider_limitation(self, limitation: ProviderLimitation) -> str:
        limitation_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_limitations (
                    limitation_id, provider, dataset, limitation_code, description,
                    trust_level, documented_at, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (provider, dataset, limitation_code) DO UPDATE SET
                    description = excluded.description,
                    trust_level = excluded.trust_level,
                    documented_at = excluded.documented_at,
                    ingested_at = excluded.ingested_at
                """,
                (
                    limitation_id,
                    limitation.provider,
                    limitation.dataset,
                    limitation.limitation_code,
                    limitation.description,
                    limitation.trust_level.value,
                    _datetime_text(limitation.documented_at),
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return limitation_id

    def save_pit_readiness_assessment(
        self,
        assessment: PITReadinessAssessment,
    ) -> str:
        assessment_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pit_readiness_assessments (
                    assessment_id, dataset, assessed_at, coverage_ratio, trust_level,
                    missing_critical_fields_json, warnings_json,
                    ready_for_historical_replay, model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    assessment.dataset,
                    _datetime_text(assessment.assessed_at),
                    assessment.coverage_ratio,
                    assessment.trust_level.value,
                    json.dumps(assessment.missing_critical_fields),
                    json.dumps(assessment.warnings),
                    int(assessment.ready_for_historical_replay),
                    assessment.model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return assessment_id

    def provider_limitations(
        self,
        datasets: tuple[str, ...] = (),
    ) -> list[ProviderLimitation]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM provider_limitations
                ORDER BY provider, dataset, limitation_code
                """
            ).fetchall()
        limitations = [_provider_limitation_from_row(row) for row in rows]
        if not datasets:
            return limitations
        allowed = set(datasets)
        return [limitation for limitation in limitations if limitation.dataset in allowed]

    def latest_pit_readiness(
        self,
        dataset: str,
    ) -> PITReadinessAssessment | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM pit_readiness_assessments
                WHERE dataset = ?
                ORDER BY assessed_at DESC, ingested_at DESC
                LIMIT 1
                """,
                (dataset,),
            ).fetchone()
        return None if row is None else _pit_readiness_from_row(row)

    def save_historical_replay_manifest(
        self,
        *,
        manifest_id: str,
        query_hash: str,
        input_hashes: dict[str, str],
        dataset_versions: dict[str, str],
        schema_version: str,
        framework_version: str,
        configuration_hash: str,
        git_commit: str,
        data_trust_summary: dict[str, int],
        provider_limitations: tuple[str, ...],
        missing_data_warnings: tuple[str, ...],
        replay_confidence: dict[str, object],
        generated_at: datetime,
        model_version: str,
    ) -> None:
        self._require_aware(generated_at)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO historical_replay_manifests (
                    manifest_id, query_hash, input_hashes_json,
                    dataset_versions_json, schema_version, framework_version,
                    configuration_hash, git_commit, data_trust_summary_json,
                    provider_limitations_json, missing_data_warnings_json,
                    replay_confidence_json, generated_at, model_version,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest_id,
                    query_hash,
                    _json_dumps(input_hashes),
                    _json_dumps(dataset_versions),
                    schema_version,
                    framework_version,
                    configuration_hash,
                    git_commit,
                    _json_dumps(data_trust_summary),
                    json.dumps(provider_limitations),
                    json.dumps(missing_data_warnings),
                    _json_dumps(replay_confidence),
                    _datetime_text(generated_at),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_historical_replay_sample(
        self,
        *,
        sample_id: str,
        manifest_id: str,
        instrument_id_value: str,
        decision_as_of: datetime,
        outcome_as_of: datetime,
        replay_hash: str,
        replay_confidence: dict[str, object],
        decision_context: dict[str, object],
        outcome_context: dict[str, object],
        evidence_references: tuple[str, ...],
        missing_data_flags: tuple[str, ...],
        provider_limitations: tuple[str, ...],
        data_trust_summary: dict[str, int],
        validation_sample: dict[str, object] | None,
        is_complete: bool,
        model_version: str,
    ) -> None:
        self._require_aware(decision_as_of)
        self._require_aware(outcome_as_of)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO historical_replay_samples (
                    sample_id, manifest_id, instrument_id, decision_as_of,
                    outcome_as_of, replay_hash, replay_confidence_json,
                    decision_context_json, outcome_context_json,
                    evidence_references_json, missing_data_flags_json,
                    provider_limitations_json, data_trust_summary_json,
                    validation_sample_json, is_complete, model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample_id,
                    manifest_id,
                    instrument_id_value,
                    _datetime_text(decision_as_of),
                    _datetime_text(outcome_as_of),
                    replay_hash,
                    _json_dumps(replay_confidence),
                    _json_dumps(decision_context),
                    _json_dumps(outcome_context),
                    json.dumps(evidence_references),
                    json.dumps(missing_data_flags),
                    json.dumps(provider_limitations),
                    _json_dumps(data_trust_summary),
                    None if validation_sample is None else _json_dumps(validation_sample),
                    int(is_complete),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def get_instrument(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        as_of: datetime,
    ) -> Instrument | None:
        self._require_aware(as_of)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM instruments
                WHERE symbol = ? AND market = ? AND asset_type = ?
                  AND available_at <= ?
                ORDER BY available_at DESC
                LIMIT 1
                """,
                (symbol, market.value, asset_type.value, _datetime_text(as_of)),
            ).fetchone()
        return None if row is None else _instrument_from_row(row)

    def daily_bars(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        start: date,
        end: date,
        *,
        as_of: datetime,
        adjustment: Adjustment = Adjustment.NONE,
    ) -> list[Bar]:
        self._require_aware(as_of)
        instrument = self.get_instrument(symbol, market, asset_type, as_of=as_of)
        if instrument is None:
            return []
        identifier = instrument_id(instrument)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT bar.*
                FROM daily_bars AS bar
                WHERE bar.instrument_id = ?
                  AND bar.trade_date BETWEEN ? AND ?
                  AND bar.adjustment = ?
                  AND bar.available_at <= ?
                  AND bar.available_at = (
                      SELECT MAX(version.available_at)
                      FROM daily_bars AS version
                      WHERE version.instrument_id = bar.instrument_id
                        AND version.trade_date = bar.trade_date
                        AND version.adjustment = bar.adjustment
                        AND version.available_at <= ?
                  )
                ORDER BY bar.trade_date
                """,
                (
                    identifier,
                    start.isoformat(),
                    end.isoformat(),
                    adjustment.value,
                    _datetime_text(as_of),
                    _datetime_text(as_of),
                ),
            ).fetchall()
        return [_bar_from_row(row, instrument) for row in rows]

    def trading_days(
        self,
        market: Market,
        start: date,
        end: date,
        *,
        as_of: datetime,
    ) -> list[date]:
        self._require_aware(as_of)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT calendar.trade_date
                FROM trading_calendar AS calendar
                WHERE calendar.market = ?
                  AND calendar.trade_date BETWEEN ? AND ?
                  AND calendar.is_open = 1
                  AND calendar.available_at <= ?
                  AND calendar.available_at = (
                      SELECT MAX(version.available_at)
                      FROM trading_calendar AS version
                      WHERE version.market = calendar.market
                        AND version.trade_date = calendar.trade_date
                        AND version.available_at <= ?
                  )
                ORDER BY calendar.trade_date
                """,
                (
                    market.value,
                    start.isoformat(),
                    end.isoformat(),
                    _datetime_text(as_of),
                    _datetime_text(as_of),
                ),
            ).fetchall()
        return [date.fromisoformat(row["trade_date"]) for row in rows]

    def fundamental_facts(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        metric: str,
        *,
        as_of: datetime,
        period_end_on_or_before: date | None = None,
    ) -> list[FundamentalFact]:
        self._require_aware(as_of)
        instrument = self.get_instrument(symbol, market, asset_type, as_of=as_of)
        if instrument is None:
            return []
        period_limit = period_end_on_or_before or as_of.date()
        identifier = instrument_id(instrument)
        with self._connect() as connection:
            rows = connection.execute(
                """
                WITH visible AS (
                    SELECT fact.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY fact.instrument_id, fact.metric, fact.period_end
                               ORDER BY fact.available_at DESC,
                                        fact.revision DESC,
                                        fact.published_at DESC
                           ) AS version_rank
                    FROM fundamental_facts AS fact
                    WHERE fact.instrument_id = ?
                      AND fact.metric = ?
                      AND fact.period_end <= ?
                      AND fact.available_at <= ?
                )
                SELECT *
                FROM visible
                WHERE version_rank = 1
                ORDER BY period_end
                """,
                (
                    identifier,
                    metric,
                    period_limit.isoformat(),
                    _datetime_text(as_of),
                ),
            ).fetchall()
        return [_fundamental_fact_from_row(row, instrument) for row in rows]

    def fundamental_revision_history(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        metric: str,
        *,
        as_of: datetime,
        period_end_on_or_before: date | None = None,
    ) -> list[FundamentalFact]:
        self._require_aware(as_of)
        instrument = self.get_instrument(symbol, market, asset_type, as_of=as_of)
        if instrument is None:
            return []
        period_limit = period_end_on_or_before or as_of.date()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM fundamental_facts
                WHERE instrument_id = ?
                  AND metric = ?
                  AND period_end <= ?
                  AND available_at <= ?
                ORDER BY period_end, available_at, revision, published_at
                """,
                (
                    instrument_id(instrument),
                    metric,
                    period_limit.isoformat(),
                    _datetime_text(as_of),
                ),
            ).fetchall()
        return [_fundamental_fact_from_row(row, instrument) for row in rows]

    def instrument_status(
        self,
        symbol: str,
        market: Market,
        asset_type: AssetType,
        *,
        on_date: date,
        as_of: datetime,
    ) -> InstrumentStatus | None:
        self._require_aware(as_of)
        instrument = self.get_instrument(symbol, market, asset_type, as_of=as_of)
        if instrument is None:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                WITH versions AS (
                    SELECT status.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY status.instrument_id, status.effective_from
                               ORDER BY status.available_at DESC
                           ) AS version_rank
                    FROM instrument_status_history AS status
                    WHERE status.instrument_id = ?
                      AND status.available_at <= ?
                )
                SELECT *
                FROM versions
                WHERE version_rank = 1
                  AND effective_from <= ?
                  AND (effective_to IS NULL OR effective_to >= ?)
                ORDER BY effective_from DESC
                LIMIT 1
                """,
                (
                    instrument_id(instrument),
                    _datetime_text(as_of),
                    on_date.isoformat(),
                    on_date.isoformat(),
                ),
            ).fetchone()
        return None if row is None else _instrument_status_from_row(row, instrument)

    def universe_as_of(
        self,
        universe: str,
        market: Market,
        *,
        on_date: date,
        as_of: datetime,
        tradable_only: bool = False,
    ) -> list[Instrument]:
        self._require_aware(as_of)
        with self._connect() as connection:
            rows = connection.execute(
                """
                WITH versions AS (
                    SELECT membership.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY membership.universe,
                                            membership.instrument_id,
                                            membership.effective_from
                               ORDER BY membership.available_at DESC
                           ) AS version_rank
                    FROM universe_memberships AS membership
                    WHERE membership.universe = ?
                      AND membership.available_at <= ?
                ),
                applicable AS (
                    SELECT versions.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY versions.instrument_id
                               ORDER BY versions.effective_from DESC
                           ) AS period_rank
                    FROM versions
                    WHERE versions.version_rank = 1
                      AND versions.effective_from <= ?
                      AND (
                          versions.effective_to IS NULL
                          OR versions.effective_to >= ?
                      )
                )
                SELECT instrument_id
                FROM applicable
                WHERE period_rank = 1
                ORDER BY instrument_id
                """,
                (
                    universe,
                    _datetime_text(as_of),
                    on_date.isoformat(),
                    on_date.isoformat(),
                ),
            ).fetchall()
        instruments = []
        for row in rows:
            identifier = str(row["instrument_id"])
            _, asset_type_value, symbol = identifier.split(":", 2)
            instrument = self.get_instrument(
                symbol,
                market,
                AssetType(asset_type_value),
                as_of=as_of,
            )
            if instrument is None:
                continue
            if tradable_only:
                status = self.instrument_status(
                    symbol,
                    market,
                    instrument.asset_type,
                    on_date=on_date,
                    as_of=as_of,
                )
                if status is None or not status.is_tradable:
                    continue
            instruments.append(instrument)
        return instruments

    def save_signal(self, signal: Signal) -> str:
        signal_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO signals (
                    signal_id, instrument_id, source, stage, generated_at,
                    effective_at, action, strength, reasons_json, features_json,
                    invalidations_json, model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    instrument_id(signal.instrument),
                    signal.source,
                    signal.stage.value,
                    _datetime_text(signal.generated_at),
                    _datetime_text(signal.effective_at),
                    signal.action.value,
                    signal.strength,
                    json.dumps(signal.reasons),
                    json.dumps(signal.features, sort_keys=True),
                    json.dumps(signal.invalidations),
                    signal.model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return signal_id

    def save_screening_result(
        self,
        *,
        instrument: Instrument,
        dimension: str,
        evaluated_at: datetime,
        available_at: datetime,
        passed: bool,
        score: float | None,
        reasons: tuple[str, ...],
        features: dict[str, object],
        source: str,
        model_version: str,
    ) -> str:
        self._require_aware(evaluated_at)
        self._require_aware(available_at)
        result_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO screening_results (
                    result_id, instrument_id, dimension, evaluated_at,
                    available_at, passed, score, reasons_json, features_json,
                    source, model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    instrument_id(instrument),
                    dimension,
                    _datetime_text(evaluated_at),
                    _datetime_text(available_at),
                    int(passed),
                    score,
                    json.dumps(reasons),
                    json.dumps(features, sort_keys=True),
                    source,
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return result_id

    def save_research_queue_entry(
        self,
        *,
        instrument: Instrument,
        discovery_source: str,
        discovered_at: datetime,
        admitted_at: datetime,
        priority_score: float,
        urgency_score: float,
        confidence_score: float,
        research_score: float,
        status: ResearchQueueStatus,
        thesis: str,
        evidence: tuple[str, ...],
        assigned_to: str | None,
        model_version: str,
    ) -> str:
        self._require_aware(discovered_at)
        self._require_aware(admitted_at)
        queue_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_queue (
                    queue_id, instrument_id, discovery_source, discovered_at,
                    admitted_at, priority_score, urgency_score, confidence_score,
                    research_score, status, thesis, evidence_json, assigned_to,
                    model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    instrument_id(instrument),
                    discovery_source,
                    _datetime_text(discovered_at),
                    _datetime_text(admitted_at),
                    priority_score,
                    urgency_score,
                    confidence_score,
                    research_score,
                    status.value,
                    thesis,
                    json.dumps(evidence),
                    assigned_to,
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return queue_id

    def save_screening_score(
        self,
        *,
        instrument: Instrument,
        score_type: ScoreType,
        calculated_at: datetime,
        score: float,
        confidence: float,
        components: list[dict[str, object]],
        reasons: tuple[str, ...],
        model_version: str,
    ) -> str:
        self._require_aware(calculated_at)
        score_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO screening_scorecards (
                    score_id, instrument_id, score_type, calculated_at,
                    score, confidence, components_json, reasons_json,
                    model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score_id,
                    instrument_id(instrument),
                    score_type.value,
                    _datetime_text(calculated_at),
                    score,
                    confidence,
                    json.dumps(components, sort_keys=True),
                    json.dumps(reasons),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return score_id

    def research_queue(
        self,
        *,
        status: ResearchQueueStatus = ResearchQueueStatus.PENDING,
        limit: int = 50,
    ) -> list[sqlite3.Row]:
        if limit <= 0:
            raise ValueError("research queue limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM research_queue
                WHERE status = ?
                ORDER BY priority_score DESC, admitted_at
                LIMIT ?
                """,
                (status.value, limit),
            ).fetchall()
        return list(rows)

    def start_research_run(
        self,
        *,
        run_id: str,
        queue_id: str,
        instrument: Instrument,
        started_at: datetime,
        researcher: str | None,
        modules: tuple[str, ...],
        model_version: str,
    ) -> None:
        self._require_aware(started_at)
        with self._connect() as connection:
            claimed = connection.execute(
                """
                UPDATE research_queue
                SET status = ?
                WHERE queue_id = ? AND status = ?
                """,
                (
                    ResearchQueueStatus.IN_RESEARCH.value,
                    queue_id,
                    ResearchQueueStatus.PENDING.value,
                ),
            )
            if claimed.rowcount != 1:
                raise ValueError("research queue entry is unavailable or already claimed")
            connection.execute(
                """
                INSERT INTO research_runs (
                    run_id, queue_id, instrument_id, status, started_at,
                    completed_at, researcher, modules_json, model_version,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    queue_id,
                    instrument_id(instrument),
                    ResearchRunStatus.RUNNING.value,
                    _datetime_text(started_at),
                    researcher,
                    json.dumps(modules),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_research_evidence(
        self,
        *,
        run_id: str,
        evidence_id: str,
        module: str,
        name: str,
        value: object,
        observed_at: datetime,
        available_at: datetime,
        source: str,
        quality: str,
        source_reference: str,
        calculation_version: str,
        input_hash: str,
        metadata: dict[str, object],
    ) -> None:
        self._require_aware(observed_at)
        self._require_aware(available_at)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO research_evidence (
                    run_id, evidence_id, module, name, value_json, observed_at,
                    available_at, source, quality, source_reference,
                    calculation_version, input_hash, metadata_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    evidence_id,
                    module,
                    name,
                    _json_dumps(value),
                    _datetime_text(observed_at),
                    _datetime_text(available_at),
                    source,
                    quality,
                    source_reference,
                    calculation_version,
                    input_hash,
                    _json_dumps(metadata),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_research_assessment(
        self,
        *,
        run_id: str,
        report_id: str,
        module: str,
        conclusion: str,
        score: float | None,
        confidence: dict[str, object],
        evaluated_at: datetime,
        available_at: datetime,
        findings: tuple[str, ...],
        risks: tuple[str, ...],
        limitations: tuple[str, ...],
        evidence_ids: tuple[str, ...],
        features: dict[str, object],
        model_version: str,
    ) -> str:
        assessment_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_assessments (
                    assessment_id, run_id, report_id, module, conclusion, score,
                    confidence_json, evaluated_at, available_at, findings_json,
                    risks_json, limitations_json, evidence_ids_json, features_json,
                    model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    run_id,
                    report_id,
                    module,
                    conclusion,
                    score,
                    _json_dumps(confidence),
                    _datetime_text(evaluated_at),
                    _datetime_text(available_at),
                    json.dumps(findings),
                    json.dumps(risks),
                    json.dumps(limitations),
                    json.dumps(evidence_ids),
                    _json_dumps(features),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return assessment_id

    def save_research_report(
        self,
        *,
        run_id: str,
        report_id: str,
        queue_id: str,
        instrument_id_value: str,
        generated_at: datetime,
        available_at: datetime,
        status: ResearchRunStatus,
        thesis: str,
        counter_thesis: str,
        invalidation_conditions: list[dict[str, object]],
        confidence: dict[str, object],
        key_findings: tuple[str, ...],
        key_risks: tuple[str, ...],
        unresolved_questions: tuple[str, ...],
        policy_assessment: dict[str, object] | None,
        market_regime: dict[str, object] | None,
        model_version: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_reports (
                    report_id, run_id, queue_id, instrument_id, generated_at,
                    available_at, status, thesis, counter_thesis,
                    invalidation_conditions_json, confidence_json,
                    key_findings_json, key_risks_json, unresolved_questions_json,
                    policy_assessment_json, market_regime_json, model_version,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    run_id,
                    queue_id,
                    instrument_id_value,
                    _datetime_text(generated_at),
                    _datetime_text(available_at),
                    status.value,
                    thesis,
                    counter_thesis,
                    _json_dumps(invalidation_conditions),
                    _json_dumps(confidence),
                    json.dumps(key_findings),
                    json.dumps(key_risks),
                    json.dumps(unresolved_questions),
                    None if policy_assessment is None else _json_dumps(policy_assessment),
                    None if market_regime is None else _json_dumps(market_regime),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_investment_assessment(
        self,
        *,
        report_id: str,
        instrument_id_value: str,
        status: InvestmentAssessmentStatus,
        assessed_at: datetime,
        score: float | None,
        confidence: float | None,
        components: list[dict[str, object]],
        reasons: tuple[str, ...],
        limitations: tuple[str, ...],
        market_regime: dict[str, object] | None,
        model_version: str,
    ) -> str:
        self._require_aware(assessed_at)
        if status in {
            InvestmentAssessmentStatus.COMPLETED,
            InvestmentAssessmentStatus.LOW_CONFIDENCE,
        } and (score is None or confidence is None or not components):
            raise ValueError("scored investment assessments require a score record")
        if status in {
            InvestmentAssessmentStatus.INCOMPLETE,
            InvestmentAssessmentStatus.INSUFFICIENT_DATA,
        } and (score is not None or confidence is not None or components):
            raise ValueError("unscored investment assessments must not carry scores")
        assessment_id = str(uuid4())
        ingested_at = _datetime_text(datetime.now(UTC))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO investment_assessments (
                    assessment_id, report_id, instrument_id, status, assessed_at,
                    score, confidence, reasons_json, limitations_json,
                    market_regime_json, model_version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    report_id,
                    instrument_id_value,
                    status.value,
                    _datetime_text(assessed_at),
                    score,
                    confidence,
                    json.dumps(reasons),
                    json.dumps(limitations),
                    None if market_regime is None else _json_dumps(market_regime),
                    model_version,
                    ingested_at,
                ),
            )
            if score is not None and confidence is not None:
                connection.execute(
                    """
                    INSERT INTO investment_scores (
                        score_id, assessment_id, report_id, instrument_id,
                        calculated_at, score, confidence, components_json,
                        reasons_json, model_version, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        assessment_id,
                        report_id,
                        instrument_id_value,
                        _datetime_text(assessed_at),
                        score,
                        confidence,
                        _json_dumps(components),
                        json.dumps(reasons),
                        model_version,
                        ingested_at,
                    ),
                )
        return assessment_id

    def complete_research_run(
        self,
        *,
        run_id: str,
        queue_id: str,
        status: ResearchRunStatus,
        completed_at: datetime,
    ) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE research_runs
                SET status = ?, completed_at = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    status.value,
                    _datetime_text(completed_at),
                    run_id,
                    ResearchRunStatus.RUNNING.value,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("research run is not active")
            queue_updated = connection.execute(
                """
                UPDATE research_queue
                SET status = ?
                WHERE queue_id = ? AND status = ?
                """,
                (
                    ResearchQueueStatus.COMPLETED.value,
                    queue_id,
                    ResearchQueueStatus.IN_RESEARCH.value,
                ),
            )
            if queue_updated.rowcount != 1:
                raise ValueError("research queue entry is not active")

    def fail_research_run(
        self,
        *,
        run_id: str,
        queue_id: str,
        completed_at: datetime,
        reason: str,
    ) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE research_runs
                SET status = ?, completed_at = ?, failure_reason = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    ResearchRunStatus.FAILED.value,
                    _datetime_text(completed_at),
                    reason[:1000],
                    run_id,
                    ResearchRunStatus.RUNNING.value,
                ),
            )
            if updated.rowcount != 1:
                return
            connection.execute(
                """
                UPDATE research_queue
                SET status = ?
                WHERE queue_id = ? AND status = ?
                """,
                (
                    ResearchQueueStatus.PENDING.value,
                    queue_id,
                    ResearchQueueStatus.IN_RESEARCH.value,
                ),
            )

    def start_validation_run(
        self,
        *,
        run_id: str,
        validation_id: str,
        subject_id: str,
        started_at: datetime,
        framework_snapshot: dict[str, object],
        model_version: str,
        oos_key: str,
        oos_configuration_hash: str,
        oos_start_date: date,
        oos_end_date: date,
        oos_maximum_uses: int,
    ) -> None:
        self._require_aware(started_at)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_oos_usage (
                    oos_key, frozen_configuration_hash, start_date, end_date,
                    use_count, maximum_uses, last_used_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT (oos_key) DO NOTHING
                """,
                (
                    oos_key,
                    oos_configuration_hash,
                    oos_start_date.isoformat(),
                    oos_end_date.isoformat(),
                    oos_maximum_uses,
                    _datetime_text(started_at),
                ),
            )
            usage = connection.execute(
                """
                SELECT use_count, maximum_uses
                FROM validation_oos_usage
                WHERE oos_key = ?
                """,
                (oos_key,),
            ).fetchone()
            if usage is None:
                raise ValueError("OOS usage registry is unavailable")
            if int(usage["maximum_uses"]) != oos_maximum_uses:
                raise ValueError("OOS maximum-use policy changed after registration")
            if int(usage["use_count"]) >= int(usage["maximum_uses"]):
                raise ValueError("OOS dataset usage limit has been reached")
            connection.execute(
                """
                UPDATE validation_oos_usage
                SET use_count = use_count + 1, last_used_at = ?
                WHERE oos_key = ?
                """,
                (_datetime_text(started_at), oos_key),
            )
            connection.execute(
                """
                INSERT INTO validation_runs (
                    run_id, validation_id, subject_id, status, started_at,
                    completed_at, framework_snapshot_json, model_version,
                    failure_reason, ingested_at
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL, ?)
                """,
                (
                    run_id,
                    validation_id,
                    subject_id,
                    ValidationRunStatus.RUNNING.value,
                    _datetime_text(started_at),
                    _json_dumps(framework_snapshot),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_split(
        self,
        *,
        run_id: str,
        split_id: str,
        kind: str,
        start_date: date,
        end_date: date,
        frozen_configuration_hash: str,
        sequence: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_splits (
                    run_id, split_id, kind, start_date, end_date,
                    frozen_configuration_hash, sequence, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    split_id,
                    kind,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    frozen_configuration_hash,
                    sequence,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_observation(
        self,
        *,
        run_id: str,
        sample_id: str,
        instrument_id_value: str,
        research_report_id: str,
        decision_at: datetime,
        research_expected_success: bool,
        market_regime: str | None,
        factor_scores: dict[str, float],
        portfolio_position: dict[str, object] | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_observations (
                    run_id, sample_id, instrument_id, research_report_id,
                    decision_at, research_expected_success, market_regime,
                    factor_scores_json, portfolio_position_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    sample_id,
                    instrument_id_value,
                    research_report_id,
                    _datetime_text(decision_at),
                    int(research_expected_success),
                    market_regime,
                    _json_dumps(factor_scores),
                    (
                        None
                        if portfolio_position is None
                        else _json_dumps(portfolio_position)
                    ),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_outcome(
        self,
        *,
        run_id: str,
        outcome_id: str,
        definition_id: str,
        subject_id: str,
        observed_at: datetime,
        available_at: datetime,
        value: float | None,
        benchmark_value: float | None,
        succeeded: bool | None,
        thesis_status: str,
        invalidation_triggered: bool | None,
        metadata: dict[str, object],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_outcomes (
                    run_id, outcome_id, definition_id, subject_id, observed_at,
                    available_at, value, benchmark_value, succeeded,
                    thesis_status, invalidation_triggered, metadata_json,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    outcome_id,
                    definition_id,
                    subject_id,
                    _datetime_text(observed_at),
                    _datetime_text(available_at),
                    value,
                    benchmark_value,
                    None if succeeded is None else int(succeeded),
                    thesis_status,
                    (
                        None
                        if invalidation_triggered is None
                        else int(invalidation_triggered)
                    ),
                    _json_dumps(metadata),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_outcome_definition(
        self,
        *,
        run_id: str,
        outcome_id: str,
        target_metric: str,
        observation_horizon_days: int,
        success_operator: str,
        success_threshold: float,
        availability_lag_days: int,
        benchmark: str | None,
        version: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_outcome_definitions (
                    run_id, outcome_id, target_metric, observation_horizon_days,
                    success_operator, success_threshold, availability_lag_days,
                    benchmark, version, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    outcome_id,
                    target_metric,
                    observation_horizon_days,
                    success_operator,
                    success_threshold,
                    availability_lag_days,
                    benchmark,
                    version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_decision_journal_entry(
        self,
        *,
        decision_id: str,
        run_id: str,
        research_report_id: str,
        decided_at: datetime,
        available_at: datetime,
        disposition: str,
        rationale: tuple[str, ...],
        confidence: float,
        decision_maker: str,
        framework_snapshot_hash: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO decision_journal (
                    decision_id, run_id, research_report_id, decided_at,
                    available_at, disposition, rationale_json, confidence,
                    decision_maker, framework_snapshot_hash, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    run_id,
                    research_report_id,
                    _datetime_text(decided_at),
                    _datetime_text(available_at),
                    disposition,
                    json.dumps(rationale),
                    confidence,
                    decision_maker,
                    framework_snapshot_hash,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_assessment(
        self,
        *,
        run_id: str,
        report_id: str,
        module: str,
        status: str,
        score: float | None,
        confidence: float,
        sample_size: int,
        evaluated_at: datetime,
        metrics: dict[str, object],
        findings: tuple[str, ...],
        risks: tuple[str, ...],
        limitations: tuple[str, ...],
        model_version: str,
    ) -> str:
        assessment_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_assessments (
                    assessment_id, run_id, report_id, module, status, score,
                    confidence, sample_size, evaluated_at, metrics_json,
                    findings_json, risks_json, limitations_json, model_version,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    run_id,
                    report_id,
                    module,
                    status,
                    score,
                    confidence,
                    sample_size,
                    _datetime_text(evaluated_at),
                    _json_dumps(metrics),
                    json.dumps(findings),
                    json.dumps(risks),
                    json.dumps(limitations),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return assessment_id

    def save_validation_report(
        self,
        *,
        run_id: str,
        report_id: str,
        validation_id: str,
        generated_at: datetime,
        status: str,
        aggregate_status: str,
        framework_snapshot: dict[str, object],
        known_limitations: tuple[str, ...],
        reproducibility_manifest: dict[str, str],
        decision_summary: dict[str, object] | None,
        portfolio_risk: dict[str, object] | None,
        model_version: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_reports (
                    report_id, run_id, validation_id, generated_at, status,
                    aggregate_status, framework_snapshot_json,
                    known_limitations_json, reproducibility_manifest_json,
                    decision_summary_json, portfolio_risk_json, model_version,
                    ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    run_id,
                    validation_id,
                    _datetime_text(generated_at),
                    status,
                    aggregate_status,
                    _json_dumps(framework_snapshot),
                    json.dumps(known_limitations),
                    _json_dumps(reproducibility_manifest),
                    (
                        None
                        if decision_summary is None
                        else _json_dumps(decision_summary)
                    ),
                    None if portfolio_risk is None else _json_dumps(portfolio_risk),
                    model_version,
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_factor_contribution(
        self,
        *,
        run_id: str,
        report_id: str,
        factor: str,
        sample_size: int,
        success_score_gap: float,
        ablation_brier_delta: float,
        stable: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_factor_contributions (
                    run_id, report_id, factor, sample_size, success_score_gap,
                    ablation_brier_delta, stable, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    report_id,
                    factor,
                    sample_size,
                    success_score_gap,
                    ablation_brier_delta,
                    int(stable),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_accuracy(
        self,
        *,
        run_id: str,
        report_id: str,
        sample_size: int,
        accuracy: float,
        brier_score: float,
        calibration_error: float,
        high_confidence_failure_rate: float,
        recorded_at: datetime,
    ) -> str:
        accuracy_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_accuracy_history (
                    accuracy_id, run_id, report_id, sample_size, accuracy,
                    brier_score, calibration_error,
                    high_confidence_failure_rate, recorded_at, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accuracy_id,
                    run_id,
                    report_id,
                    sample_size,
                    accuracy,
                    brier_score,
                    calibration_error,
                    high_confidence_failure_rate,
                    _datetime_text(recorded_at),
                    _datetime_text(datetime.now(UTC)),
                ),
            )
        return accuracy_id

    def save_validation_integrity_check(
        self,
        *,
        run_id: str,
        report_id: str,
        module: str,
        check_id: str,
        passed: bool,
        checked_at: datetime,
        reasons: tuple[str, ...],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_integrity_checks (
                    run_id, report_id, module, check_id, passed, checked_at,
                    reasons_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    report_id,
                    module,
                    check_id,
                    int(passed),
                    _datetime_text(checked_at),
                    json.dumps(reasons),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def save_validation_portfolio_risk(
        self,
        *,
        run_id: str,
        report_id: str,
        dimension: str,
        total_weight: float,
        maximum_weight: float,
        hhi: float,
        category_weights: dict[str, float],
        breached: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_portfolio_risk (
                    run_id, report_id, dimension, total_weight, maximum_weight,
                    hhi, category_weights_json, breached, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    report_id,
                    dimension,
                    total_weight,
                    maximum_weight,
                    hhi,
                    _json_dumps(category_weights),
                    int(breached),
                    _datetime_text(datetime.now(UTC)),
                ),
            )

    def complete_validation_run(
        self,
        *,
        run_id: str,
        status: ValidationRunStatus,
        completed_at: datetime,
    ) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE validation_runs
                SET status = ?, completed_at = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    status.value,
                    _datetime_text(completed_at),
                    run_id,
                    ValidationRunStatus.RUNNING.value,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("validation run is not active")

    def fail_validation_run(
        self,
        *,
        run_id: str,
        completed_at: datetime,
        reason: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE validation_runs
                SET status = ?, completed_at = ?, failure_reason = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    ValidationRunStatus.FAILED.value,
                    _datetime_text(completed_at),
                    reason[:1000],
                    run_id,
                    ValidationRunStatus.RUNNING.value,
                ),
            )

    def schema_version(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
        if row is None:
            raise ValueError("database schema version is unavailable")
        return str(row["value"])

    def latest_screening_score(
        self,
        instrument: Instrument,
        score_type: ScoreType,
        *,
        as_of: datetime,
    ) -> sqlite3.Row | None:
        self._require_aware(as_of)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM screening_scorecards
                WHERE instrument_id = ?
                  AND score_type = ?
                  AND calculated_at <= ?
                ORDER BY calculated_at DESC
                LIMIT 1
                """,
                (
                    instrument_id(instrument),
                    score_type.value,
                    _datetime_text(as_of),
                ),
            ).fetchone()
        return cast(sqlite3.Row | None, row)

    def screening_results_for_replay(
        self,
        instrument: Instrument,
        *,
        as_of: datetime,
    ) -> list[sqlite3.Row]:
        self._require_aware(as_of)
        with self._connect() as connection:
            rows = connection.execute(
                """
                WITH visible AS (
                    SELECT result.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY result.instrument_id, result.dimension
                               ORDER BY result.available_at DESC,
                                        result.evaluated_at DESC
                           ) AS version_rank
                    FROM screening_results AS result
                    WHERE result.instrument_id = ?
                      AND result.available_at <= ?
                )
                SELECT *
                FROM visible
                WHERE version_rank = 1
                ORDER BY dimension
                """,
                (instrument_id(instrument), _datetime_text(as_of)),
            ).fetchall()
        return list(rows)

    def fundamental_facts_for_replay(
        self,
        instrument: Instrument,
        *,
        as_of: datetime,
    ) -> list[sqlite3.Row]:
        self._require_aware(as_of)
        with self._connect() as connection:
            rows = connection.execute(
                """
                WITH visible AS (
                    SELECT fact.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY fact.instrument_id,
                                            fact.metric,
                                            fact.period_end
                               ORDER BY fact.available_at DESC,
                                        fact.revision DESC,
                                        fact.published_at DESC
                           ) AS version_rank
                    FROM fundamental_facts AS fact
                    WHERE fact.instrument_id = ?
                      AND fact.available_at <= ?
                      AND fact.period_end <= ?
                )
                SELECT *
                FROM visible
                WHERE version_rank = 1
                ORDER BY metric, period_end
                """,
                (
                    instrument_id(instrument),
                    _datetime_text(as_of),
                    as_of.date().isoformat(),
                ),
            ).fetchall()
        return list(rows)

    def latest_research_report_for_replay(
        self,
        instrument: Instrument,
        *,
        as_of: datetime,
    ) -> sqlite3.Row | None:
        self._require_aware(as_of)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM research_reports
                WHERE instrument_id = ?
                  AND available_at <= ?
                ORDER BY available_at DESC, generated_at DESC
                LIMIT 1
                """,
                (instrument_id(instrument), _datetime_text(as_of)),
            ).fetchone()
        return cast(sqlite3.Row | None, row)

    def research_assessments_for_report(self, report_id: str) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM research_assessments
                WHERE report_id = ?
                ORDER BY module, evaluated_at
                """,
                (report_id,),
            ).fetchall()
        return list(rows)

    def research_evidence_for_run(self, run_id: str) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM research_evidence
                WHERE run_id = ?
                ORDER BY module, evidence_id
                """,
                (run_id,),
            ).fetchall()
        return list(rows)

    def table_count(self, table: str) -> int:
        if table not in {
            "instruments",
            "daily_bars",
            "trading_calendar",
            "fundamental_facts",
            "instrument_status_history",
            "universe_memberships",
            "corporate_actions",
            "ingestion_batches",
            "raw_dataset_fingerprints",
            "data_availability_warnings",
            "provider_limitations",
            "pit_readiness_assessments",
            "historical_replay_manifests",
            "historical_replay_samples",
            "signals",
            "screening_results",
            "research_queue",
            "screening_scorecards",
            "research_runs",
            "research_evidence",
            "research_assessments",
            "research_reports",
            "investment_assessments",
            "investment_scores",
            "schema_metadata",
            "validation_runs",
            "validation_oos_usage",
            "validation_splits",
            "validation_observations",
            "validation_outcomes",
            "validation_outcome_definitions",
            "decision_journal",
            "validation_assessments",
            "validation_reports",
            "validation_factor_contributions",
            "validation_accuracy_history",
            "validation_integrity_checks",
            "validation_portfolio_risk",
        }:
            raise ValueError("unsupported table")
        with self._connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of timestamps must be timezone-aware")


def instrument_id(instrument: Instrument) -> str:
    return f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"


def _instrument_from_row(row: sqlite3.Row) -> Instrument:
    return Instrument(
        symbol=row["symbol"],
        market=Market(row["market"]),
        name=row["name"],
        asset_type=AssetType(row["asset_type"]),
        category=InstrumentCategory(row["category"]),
        fund_subtype=(
            None
            if row["fund_subtype"] is None
            else FundSubtype(row["fund_subtype"])
        ),
        currency=row["currency"],
        lot_size=int(row["lot_size"]),
        exchange=row["exchange"],
        industry=row["industry"],
        listing_date=_optional_date(row["listing_date"]),
        delisting_date=_optional_date(row["delisting_date"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        source=row["source"],
    )


def _bar_from_row(row: sqlite3.Row, instrument: Instrument) -> Bar:
    return Bar(
        instrument=instrument,
        timestamp=datetime.fromisoformat(row["timestamp"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        open=Decimal(row["open"]),
        high=Decimal(row["high"]),
        low=Decimal(row["low"]),
        close=Decimal(row["close"]),
        volume=Decimal(row["volume"]),
        turnover=None if row["turnover"] is None else Decimal(row["turnover"]),
        adjustment=Adjustment(row["adjustment"]),
        is_suspended=bool(row["is_suspended"]),
        source=row["source"],
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
    )


def _fundamental_fact_from_row(
    row: sqlite3.Row,
    instrument: Instrument,
) -> FundamentalFact:
    return FundamentalFact(
        instrument=instrument,
        metric=row["metric"],
        period_start=_optional_date(row["period_start"]),
        period_end=date.fromisoformat(row["period_end"]),
        fiscal_period=row["fiscal_period"],
        published_at=datetime.fromisoformat(row["published_at"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        value=Decimal(row["value"]),
        currency=row["currency"],
        unit=row["unit"],
        revision=int(row["revision"]),
        raw_data_hash=row["raw_data_hash"],
        batch_id=row["batch_id"],
        provider_dataset=row["provider_dataset"],
        availability_precision=AvailabilityPrecision(row["availability_precision"]),
        trust_level=DataTrustLevel(row["trust_level"]),
        source=row["source"],
    )


def _instrument_status_from_row(
    row: sqlite3.Row,
    instrument: Instrument,
) -> InstrumentStatus:
    return InstrumentStatus(
        instrument=instrument,
        effective_from=date.fromisoformat(row["effective_from"]),
        effective_to=_optional_date(row["effective_to"]),
        status=SecurityStatus(row["status"]),
        is_tradable=bool(row["is_tradable"]),
        industry=row["industry"],
        raw_data_hash=row["raw_data_hash"],
        batch_id=row["batch_id"],
        provider_dataset=row["provider_dataset"],
        availability_precision=AvailabilityPrecision(row["availability_precision"]),
        trust_level=DataTrustLevel(row["trust_level"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        source=row["source"],
    )


def _provider_limitation_from_row(row: sqlite3.Row) -> ProviderLimitation:
    return ProviderLimitation(
        provider=row["provider"],
        dataset=row["dataset"],
        limitation_code=row["limitation_code"],
        description=row["description"],
        trust_level=DataTrustLevel(row["trust_level"]),
        documented_at=datetime.fromisoformat(row["documented_at"]),
    )


def _pit_readiness_from_row(row: sqlite3.Row) -> PITReadinessAssessment:
    return PITReadinessAssessment(
        dataset=row["dataset"],
        assessed_at=datetime.fromisoformat(row["assessed_at"]),
        coverage_ratio=float(row["coverage_ratio"]),
        trust_level=DataTrustLevel(row["trust_level"]),
        missing_critical_fields=tuple(json.loads(row["missing_critical_fields_json"])),
        warnings=tuple(json.loads(row["warnings_json"])),
        ready_for_historical_replay=bool(row["ready_for_historical_replay"]),
        model_version=row["model_version"],
    )


def _datetime_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("stored timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _date_text(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _optional_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _json_dumps(value: object) -> str:
    def default(item: object) -> str:
        if isinstance(item, (datetime, date, Decimal)):
            return item.isoformat() if not isinstance(item, Decimal) else str(item)
        if isinstance(item, Enum):
            return str(item.value)
        raise TypeError(f"unsupported JSON value: {type(item).__name__}")

    return json.dumps(value, default=default, sort_keys=True)
