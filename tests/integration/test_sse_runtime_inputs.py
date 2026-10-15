"""Synthetic database fixtures exercise contracts, not real provider readiness."""

import json
import sqlite3
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    AvailabilityPrecision,
    CorporateActionType,
    DataTrustLevel,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import (
    Bar,
    CorporateAction,
    Instrument,
    InstrumentStatus,
    TradingSession,
)
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE

VISIBLE = datetime(2026, 10, 14, tzinfo=UTC)
AS_OF = datetime(2026, 10, 16, 2, tzinfo=UTC)
DAY = date(2026, 10, 16)
START = date(2026, 10, 14)
QUERY = MarketRuleQuery(SSE_PILOT_SCOPE, DAY, AS_OF)


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStore:
    result = SQLiteStore(tmp_path / "runtime.sqlite3")
    result.initialize()
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Synthetic",
        exchange="SSE",
        available_at=VISIBLE,
        listing_date=date(2010, 1, 1),
        source="fixture",
    )
    result.upsert_instruments((instrument,))
    result.upsert_instrument_statuses(
        (
            InstrumentStatus(
                instrument,
                START,
                SecurityStatus.LISTED,
                True,
                VISIBLE,
                "fixture",
                raw_data_hash="a" * 64,
                trust_level=DataTrustLevel.LOW,
                availability_precision=AvailabilityPrecision.DATE_ONLY,
            ),
        )
    )
    result.upsert_trading_sessions(
        TradingSession(Market.CHINA_A, START + timedelta(days=index), True, VISIBLE, "fixture")
        for index in range(3)
    )
    result.upsert_daily_bars(
        (
            Bar(
                instrument,
                datetime(2026, 10, 15, 7, tzinfo=UTC),
                datetime(2026, 10, 15, 8, tzinfo=UTC),
                Decimal("10"),
                Decimal("11"),
                Decimal("9"),
                Decimal("10"),
                Decimal("100"),
                source="fixture",
            ),
        )
    )
    return result


def reader(store: SQLiteStore) -> SSERuntimeInputReader:
    return SSERuntimeInputReader(MarketDataService(store))


def codes(store: SQLiteStore) -> set[str]:
    return {gap.code for gap in reader(store).read("600000", QUERY, calendar_start=START).gaps}


def test_snapshot_preserves_trust_and_does_not_infer_favorable_flags(store: SQLiteStore) -> None:
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert snapshot.status is not None
    assert snapshot.status.trust_level is DataTrustLevel.LOW
    assert snapshot.status.availability_precision is AvailabilityPrecision.DATE_ONLY
    assert snapshot.previous_close is not None
    assert snapshot.previous_session == date(2026, 10, 15)
    assert snapshot.missing_calendar_dates == ()
    assert {
        "status_trust_insufficient",
        "status_precision_insufficient",
        "listing_phase_unverified",
        "corporate_action_coverage_unverified",
        "calendar_provenance_unavailable",
        "price_provenance_unavailable",
        "account_lots_not_integrated",
    } <= {gap.code for gap in snapshot.gaps}
    assert (
        snapshot.input_hash == reader(store).read("600000", QUERY, calendar_start=START).input_hash
    )
    assert snapshot.to_record()["input_hash"] == snapshot.input_hash


def test_closed_calendar_is_retained_and_future_revision_is_excluded(store: SQLiteStore) -> None:
    closed = TradingSession(Market.CHINA_A, date(2026, 10, 15), False, AS_OF, "fixture")
    store.upsert_trading_sessions(
        (closed, replace(closed, is_open=True, available_at=AS_OF + timedelta(hours=1)))
    )
    service = MarketDataService(store)
    sessions = service.trading_sessions(Market.CHINA_A, START, DAY, as_of=AS_OF)
    assert sessions[1] == closed
    assert service.trading_days(Market.CHINA_A, START, DAY, as_of=AS_OF) == [START, DAY]
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert snapshot.missing_calendar_dates == ()
    assert snapshot.previous_session == START
    assert snapshot.previous_close is None


def test_future_instrument_status_calendar_and_bar_do_not_enter_snapshot(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "future.sqlite3")
    store.initialize()
    future = AS_OF + timedelta(hours=1)
    instrument = Instrument("600000", Market.CHINA_A, "Future", available_at=future)
    store.upsert_instruments((instrument,))
    store.upsert_trading_sessions((TradingSession(Market.CHINA_A, DAY, True, future, "fixture"),))
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert snapshot.instrument is None and snapshot.status is None
    assert snapshot.sessions == () and snapshot.previous_close is None
    assert snapshot.missing_calendar_dates == (START, date(2026, 10, 15), DAY)


@pytest.mark.parametrize(
    "status", [SecurityStatus.SUSPENDED, SecurityStatus.SPECIAL_TREATMENT, SecurityStatus.DELISTED]
)
def test_exceptional_status_is_retained_not_filtered(
    store: SQLiteStore, status: SecurityStatus
) -> None:
    original = reader(store).read("600000", QUERY, calendar_start=START).status
    assert original is not None
    store.upsert_instrument_statuses(
        (replace(original, status=status, is_tradable=False, available_at=AS_OF),)
    )
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert snapshot.status is not None and snapshot.status.status is status
    assert "status_not_ordinary" in {gap.code for gap in snapshot.gaps}


def test_corporate_action_versions_remain_visible_without_no_action_inference(
    store: SQLiteStore,
) -> None:
    instrument = MarketDataService(store).instrument(
        "600000", Market.CHINA_A, AssetType.EQUITY, as_of=AS_OF
    )
    assert instrument is not None
    action = CorporateAction(
        instrument,
        CorporateActionType.DIVIDEND,
        DAY,
        VISIBLE,
        "fixture",
        cash_amount=Decimal("0.1"),
        raw_data_hash="b" * 64,
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
    )
    store.upsert_corporate_actions(
        (
            action,
            replace(action, available_at=AS_OF, cash_amount=Decimal("0.2")),
            replace(action, available_at=AS_OF + timedelta(hours=1), cash_amount=Decimal("0.3")),
        )
    )
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert [item.cash_amount for item in snapshot.corporate_actions] == [
        Decimal("0.1"),
        Decimal("0.2"),
    ]
    assert all(item.trust_level is DataTrustLevel.LOW for item in snapshot.corporate_actions)
    assert "decision_date_action_present" in {gap.code for gap in snapshot.gaps}
    assert "corporate_action_coverage_unverified" in codes(store)


def test_multi_query_snapshot_does_not_mix_concurrent_instrument_versions(
    store: SQLiteStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = MarketDataService(store)
    original_read = service.instrument
    writer = SQLiteStore(store.path)

    def changing_read(*args: object, **kwargs: object) -> Instrument | None:
        instrument = original_read("600000", Market.CHINA_A, AssetType.EQUITY, as_of=AS_OF)
        assert instrument is not None
        writer.upsert_instruments((replace(instrument, exchange="OTHER", available_at=AS_OF),))
        return instrument

    monkeypatch.setattr(service, "instrument", changing_read)
    snapshot = SSERuntimeInputReader(service).read("600000", QUERY, calendar_start=START)
    assert snapshot.instrument is not None and snapshot.status is not None
    assert snapshot.instrument.exchange == snapshot.status.instrument.exchange == "SSE"
    assert (
        reader(store).read("600000", QUERY, calendar_start=START).instrument != snapshot.instrument
    )


def test_read_only_store_never_creates_initializes_or_updates_database(
    store: SQLiteStore, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.sqlite3"
    absent = SQLiteStore(missing, read_only=True)
    with pytest.raises(RuntimeError, match="read-only"):
        absent.initialize()
    with pytest.raises(sqlite3.OperationalError):
        absent.table_count("instruments")
    assert not missing.exists()
    readonly = SQLiteStore(store.path, read_only=True)
    assert reader(readonly).read("600000", QUERY, calendar_start=START).instrument is not None
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        readonly.upsert_trading_sessions(
            (TradingSession(Market.CHINA_A, DAY, False, AS_OF, "fixture"),)
        )


def test_cli_missing_database_fails_closed_without_creating_file(tmp_path: Path) -> None:
    missing = tmp_path / "absent.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_sse_runtime_inputs.py",
            "--database",
            str(missing),
            "--symbol",
            "600000",
            "--trade-date",
            DAY.isoformat(),
            "--as-of",
            AS_OF.isoformat(),
            "--calendar-start",
            START.isoformat(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "database_missing"
    assert not missing.exists()


@pytest.mark.parametrize("start", [DAY, DAY + timedelta(days=1), DAY - timedelta(days=367)])
def test_invalid_calendar_window_rejected(store: SQLiteStore, start: date) -> None:
    with pytest.raises(ValueError, match="window"):
        reader(store).read("600000", QUERY, calendar_start=start)


def test_hash_changes_with_visible_calendar_revision(store: SQLiteStore) -> None:
    before = reader(store).read("600000", QUERY, calendar_start=START)
    store.upsert_trading_sessions((TradingSession(Market.CHINA_A, DAY, False, AS_OF, "fixture"),))
    after = reader(store).read("600000", QUERY, calendar_start=START)
    assert before.input_hash != after.input_hash
    assert "decision_session_not_open" in {gap.code for gap in after.gaps}


def test_future_status_and_close_correction_stay_out_of_visible_inputs(store: SQLiteStore) -> None:
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert snapshot.status is not None and snapshot.previous_close is not None
    future = AS_OF + timedelta(hours=1)
    store.upsert_instrument_statuses(
        (
            replace(
                snapshot.status,
                available_at=future,
                status=SecurityStatus.SUSPENDED,
                is_tradable=False,
            ),
        )
    )
    store.upsert_daily_bars(
        (
            replace(snapshot.previous_close, available_at=future, close=Decimal("11")),
            replace(snapshot.previous_close, adjustment=Adjustment.FORWARD, close=Decimal("9")),
        )
    )
    visible = reader(store).read("600000", QUERY, calendar_start=START)
    assert visible.status == snapshot.status
    assert visible.previous_close == snapshot.previous_close
    assert visible.input_hash == snapshot.input_hash


def test_missing_calendar_date_is_not_inferred_closed(store: SQLiteStore) -> None:
    snapshot = reader(store).read("600000", QUERY, calendar_start=START - timedelta(days=1))
    assert snapshot.missing_calendar_dates == (START - timedelta(days=1),)
    assert "calendar_incomplete" in {gap.code for gap in snapshot.gaps}


def test_canonical_exchange_identifier_does_not_create_a_false_scope_failure(
    store: SQLiteStore,
) -> None:
    original = reader(store).read("600000", QUERY, calendar_start=START).instrument
    assert original is not None
    store.upsert_instruments((replace(original, exchange="XSHG", available_at=AS_OF),))
    snapshot = reader(store).read("600000", QUERY, calendar_start=START)
    assert "instrument_scope_unverified" not in {gap.code for gap in snapshot.gaps}
    assert "listing_phase_unverified" in {gap.code for gap in snapshot.gaps}


def test_read_apis_require_explicit_aware_cutoff(store: SQLiteStore) -> None:
    service = MarketDataService(store)
    with pytest.raises(ValueError, match="timezone-aware"):
        service.trading_sessions(Market.CHINA_A, START, DAY, as_of=AS_OF.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        service.corporate_actions(
            "600000",
            Market.CHINA_A,
            AssetType.EQUITY,
            START,
            DAY,
            as_of=AS_OF.replace(tzinfo=None),
        )


def test_cli_existing_database_reports_gaps_without_source_writes(store: SQLiteStore) -> None:
    before = store.path.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_sse_runtime_inputs.py",
            "--database",
            str(store.path),
            "--symbol",
            "600000",
            "--trade-date",
            DAY.isoformat(),
            "--as-of",
            AS_OF.isoformat(),
            "--calendar-start",
            START.isoformat(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["status"]["trust_level"] == "low"
    assert report["previous_close"]["adjustment"] == "none"
    assert len(report["input_hash"]) == 64
    assert store.path.read_bytes() == before
