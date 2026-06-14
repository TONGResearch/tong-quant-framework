import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from tong_quant.domain.enums import Adjustment, AssetType, Market, SecurityStatus
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
