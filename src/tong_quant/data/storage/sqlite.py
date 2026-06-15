import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import cast
from uuid import uuid4

from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    Market,
    ResearchQueueStatus,
    ResearchRunStatus,
    ScoreType,
    SecurityStatus,
)
from tong_quant.domain.models import (
    Bar,
    FundamentalFact,
    Instrument,
    InstrumentStatus,
    Signal,
    TradingSession,
    UniverseMembership,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    asset_type TEXT NOT NULL,
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
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (
        instrument_id, metric, period_end, published_at, revision, available_at
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
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (instrument_id, effective_from, available_at)
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
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (universe, instrument_id, effective_from, available_at)
);

CREATE INDEX IF NOT EXISTS idx_universe_memberships_pit
ON universe_memberships (
    universe, effective_from, effective_to, available_at, instrument_id
);

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
"""


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

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
                    instrument_id, symbol, market, asset_type, name, currency,
                    lot_size, exchange, industry, listing_date, delisting_date,
                    available_at, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (instrument_id, available_at) DO UPDATE SET
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
                ingested_at,
            )
            for fact in facts
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO fundamental_facts (
                    instrument_id, metric, period_start, period_end,
                    fiscal_period, published_at, available_at, value,
                    currency, unit, revision, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ingested_at,
            )
            for status in statuses
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO instrument_status_history (
                    instrument_id, effective_from, effective_to, status,
                    is_tradable, industry, available_at, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ingested_at,
            )
            for membership in memberships
        ]
        if not rows:
            return 0
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO universe_memberships (
                    universe, instrument_id, effective_from, effective_to,
                    available_at, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

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

    def table_count(self, table: str) -> int:
        if table not in {
            "instruments",
            "daily_bars",
            "trading_calendar",
            "fundamental_facts",
            "instrument_status_history",
            "universe_memberships",
            "signals",
            "screening_results",
            "research_queue",
            "screening_scorecards",
            "research_runs",
            "research_evidence",
            "research_assessments",
            "research_reports",
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
        available_at=datetime.fromisoformat(row["available_at"]),
        source=row["source"],
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
