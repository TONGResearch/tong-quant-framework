from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar, Instrument, TradingSession

NOW = datetime(2026, 1, 5, 8, tzinfo=UTC)


def _bar() -> Bar:
    return Bar(
        instrument=Instrument("600000", Market.CHINA_A, "Example", available_at=NOW),
        timestamp=NOW, available_at=NOW, open=Decimal("10"), high=Decimal("12"),
        low=Decimal("9"), close=Decimal("11"), volume=Decimal("100"), source="fixture",
    )


def _store(tmp_path: Path) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "revisions.sqlite3")
    store.initialize()
    store.upsert_instruments((_bar().instrument,))
    return store


def test_bar_ingestion_is_idempotent_without_rewriting_observed_content(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_daily_bars((_bar(),))
    store.upsert_daily_bars((replace(_bar(), close=Decimal("11.00")),))
    assert store.table_count("daily_bars") == 1


def test_conflicting_bar_rolls_back_batch_and_new_version_preserves_pit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    original = _bar()
    store.upsert_daily_bars((original,))
    conflict = replace(original, close=Decimal("12"))
    another = replace(
        original, timestamp=NOW + timedelta(days=1), available_at=NOW + timedelta(days=1),
    )
    with pytest.raises(ValueError, match="new available_at version"):
        store.upsert_daily_bars((another, conflict))
    assert store.table_count("daily_bars") == 1
    store.upsert_daily_bars((replace(conflict, available_at=NOW + timedelta(days=2)),))
    def visible(as_of: datetime) -> list[Bar]:
        return store.daily_bars(
            "600000", Market.CHINA_A, AssetType.EQUITY, NOW.date(), NOW.date(), as_of=as_of,
        )
    assert visible(NOW)[0].close == Decimal("11")
    assert visible(NOW + timedelta(days=2))[0].close == Decimal("12")


def test_calendar_conflict_does_not_replace_history(tmp_path: Path) -> None:
    store = _store(tmp_path)
    session = TradingSession(Market.CHINA_A, date(2026, 1, 5), True, NOW, "fixture")
    store.upsert_trading_sessions((session, session))
    with pytest.raises(ValueError, match="new available_at version"):
        store.upsert_trading_sessions((replace(session, is_open=False),))
    assert store.table_count("trading_calendar") == 1
    store.upsert_trading_sessions((
        replace(session, is_open=False, available_at=NOW + timedelta(days=1)),
    ))
    assert store.trading_days(
        Market.CHINA_A, session.trade_date, session.trade_date, as_of=NOW,
    ) == [session.trade_date]
    assert store.trading_days(
        Market.CHINA_A, session.trade_date, session.trade_date, as_of=NOW + timedelta(days=1),
    ) == []
