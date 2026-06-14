from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market, SignalAction, SignalStage
from tong_quant.domain.models import Instrument, Signal


def test_sqlite_initializes_required_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()

    assert store.table_count("instruments") == 0
    assert store.table_count("daily_bars") == 0
    assert store.table_count("trading_calendar") == 0
    assert store.table_count("signals") == 0
    assert store.table_count("screening_results") == 0


def test_point_in_time_queries_require_aware_timestamp(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()

    try:
        store.trading_days(
            market="china_a",  # type: ignore[arg-type]
            start=datetime(2024, 1, 1, tzinfo=UTC).date(),
            end=datetime(2024, 1, 2, tzinfo=UTC).date(),
            as_of=datetime(2024, 1, 2),
        )
    except ValueError as error:
        assert "timezone-aware" in str(error)
    else:
        raise AssertionError("naive point-in-time query should fail")


def test_signal_and_screening_result_tables_accept_future_engine_outputs(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "test.sqlite3")
    store.initialize()
    now = datetime(2024, 1, 2, tzinfo=UTC)
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=now,
        source="test",
    )
    store.upsert_instruments([instrument])
    signal = Signal(
        source="screening.survival",
        stage=SignalStage.SCREENING,
        instrument=instrument,
        generated_at=now,
        effective_at=now,
        action=SignalAction.INCLUDE,
        strength=0.8,
        reasons=("passed",),
    )

    store.save_signal(signal)
    store.save_screening_result(
        instrument=instrument,
        dimension="survival",
        evaluated_at=now,
        available_at=now,
        passed=True,
        score=0.8,
        reasons=("passed",),
        features={"cash_flow_quality": 0.9},
        source="screening.survival",
        model_version="v0",
    )

    assert store.table_count("signals") == 1
    assert store.table_count("screening_results") == 1
