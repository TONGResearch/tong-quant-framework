import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument


@pytest.fixture
def fact_store(tmp_path: Path) -> tuple[SQLiteStore, FundamentalFact]:
    store = SQLiteStore(tmp_path / "facts.sqlite3")
    store.initialize()
    instrument = Instrument(
        "600000", Market.CHINA_A, "fixture",
        available_at=datetime(2024, 1, 1, tzinfo=UTC), source="fixture",
    )
    store.upsert_instruments([instrument])
    fact = FundamentalFact(
        instrument=instrument,
        metric="revenue",
        period_end=date(2023, 12, 31),
        published_at=datetime(2024, 3, 20, tzinfo=UTC),
        available_at=datetime(2024, 3, 21, tzinfo=UTC),
        value=Decimal("100"),
        source="fixture",
        currency="CNY",
        raw_data_hash="a" * 64,
        batch_id="original-batch",
        provider_dataset="fixture-fundamentals",
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        trust_level=DataTrustLevel.LOW,
    )
    return store, fact


def _rows(store: SQLiteStore) -> list[tuple[object, ...]]:
    with sqlite3.connect(f"{store.path.as_uri()}?mode=ro", uri=True) as connection:
        return connection.execute(
            "SELECT * FROM fundamental_facts ORDER BY metric, revision, available_at"
        ).fetchall()


@pytest.mark.parametrize(
    "changes",
    [
        {"value": Decimal("0")},
        {"period_start": date(2023, 1, 1)},
        {"fiscal_period": "FY"},
        {"currency": "USD"},
        {"unit": "millions"},
        {"source": "different-source"},
        {"provider_dataset": "different-dataset"},
        {"availability_precision": AvailabilityPrecision.EXACT},
        {"trust_level": DataTrustLevel.HIGH},
    ],
)
def test_same_raw_hash_cannot_hide_a_material_fact_conflict(
    fact_store: tuple[SQLiteStore, FundamentalFact], changes: dict[str, object],
) -> None:
    store, fact = fact_store
    store.upsert_fundamental_facts([fact])
    before = _rows(store)
    with pytest.raises(ValueError, match="fundamental fact content conflict"):
        store.upsert_fundamental_facts([replace(fact, **changes)])
    assert _rows(store) == before


def test_exact_reingestion_preserves_first_capture_and_numeric_representation(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    store.upsert_fundamental_facts([fact])
    before = _rows(store)
    assert store.upsert_fundamental_facts([
        replace(fact, batch_id="repeat-batch", value=Decimal("100.00")), fact,
    ]) == 2  # Existing API counts accepted input rows, not new inserts.
    assert _rows(store) == before


@pytest.mark.parametrize("different_hash", [False, True])
def test_conflicting_rows_in_one_call_roll_back_the_entire_call(
    fact_store: tuple[SQLiteStore, FundamentalFact], different_hash: bool,
) -> None:
    store, fact = fact_store
    conflicting = replace(
        fact, value=Decimal("101"),
        raw_data_hash="b" * 64 if different_hash else fact.raw_data_hash,
    )
    with pytest.raises(ValueError, match="fundamental fact .* conflict"):
        store.upsert_fundamental_facts([
            replace(fact, metric="unrelated"), fact, conflicting,
        ])
    assert _rows(store) == []


def test_caught_conflict_does_not_leave_partial_rows_in_a_callers_transaction(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    with store.transaction():
        store.upsert_fundamental_facts([replace(fact, metric="before")])
        with pytest.raises(ValueError, match="fundamental fact content conflict"):
            store.upsert_fundamental_facts([fact, replace(fact, value=Decimal("2"))])
        store.upsert_fundamental_facts([replace(fact, metric="after")])
    assert store.table_count("fundamental_facts") == 2
    assert {row[1] for row in _rows(store)} == {"before", "after"}


def test_uncaught_conflict_rolls_back_the_callers_transaction(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    with (
        pytest.raises(ValueError, match="fundamental fact content conflict"),
        store.transaction(),
    ):
        store.upsert_fundamental_facts([fact])
        store.upsert_fundamental_facts([replace(fact, value=Decimal("2"))])
    assert _rows(store) == []


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_nonfinite_facts_are_rejected_at_the_storage_boundary(
    fact_store: tuple[SQLiteStore, FundamentalFact], value: str,
) -> None:
    store, fact = fact_store
    with pytest.raises(ValueError, match="fundamental fact value must be finite"):
        store.upsert_fundamental_facts([replace(fact, value=Decimal(value))])
    assert _rows(store) == []


def test_an_explicit_later_revision_preserves_the_original_pit_view(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    revision = replace(
        fact, revision=1, available_at=fact.available_at + timedelta(days=1),
        value=Decimal("90"), raw_data_hash="b" * 64, batch_id="revision-batch",
    )
    store.upsert_fundamental_facts([fact, revision])
    earlier = store.fundamental_revision_history(
        "600000", Market.CHINA_A, AssetType.EQUITY, "revenue", as_of=fact.available_at,
    )
    later = store.fundamental_revision_history(
        "600000", Market.CHINA_A, AssetType.EQUITY, "revenue", as_of=revision.available_at,
    )
    assert [item.value for item in earlier] == [Decimal("100")]
    assert [item.value for item in later] == [Decimal("100"), Decimal("90")]


@pytest.mark.parametrize("value", ["not-a-number", "NaN", "sNaN", "Infinity"])
def test_invalid_legacy_storage_is_flagged_not_repaired_by_reingestion(
    fact_store: tuple[SQLiteStore, FundamentalFact], value: str,
) -> None:
    store, fact = fact_store
    store.upsert_fundamental_facts([fact])
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE fundamental_facts SET value = ?", (value,))
    before = _rows(store)
    with pytest.raises(ValueError, match="fundamental fact stored value is invalid"):
        store.upsert_fundamental_facts([fact])
    assert _rows(store) == before


def test_legacy_multiple_hashes_under_one_version_remain_a_visible_conflict(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    store.upsert_fundamental_facts([fact])
    store.upsert_fundamental_facts([replace(fact, revision=1, raw_data_hash="b" * 64)])
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE fundamental_facts SET revision = 0 WHERE revision = 1")
    before = _rows(store)
    with pytest.raises(ValueError, match="fundamental fact raw hash conflict"):
        store.upsert_fundamental_facts([fact])
    assert _rows(store) == before


def test_database_rejection_rolls_back_the_call_not_the_callers_prior_work(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    with sqlite3.connect(store.path) as connection:
        connection.execute("""
            CREATE TRIGGER reject_fixture BEFORE INSERT ON fundamental_facts
            WHEN NEW.metric = 'rejected'
            BEGIN SELECT RAISE(ABORT, 'synthetic write rejection'); END
        """)
    with store.transaction():
        store.upsert_fundamental_facts([replace(fact, metric="before")])
        with pytest.raises(sqlite3.IntegrityError, match="synthetic write rejection"):
            store.upsert_fundamental_facts([fact, replace(fact, metric="rejected")])
        store.upsert_fundamental_facts([replace(fact, metric="after")])
    assert {row[1] for row in _rows(store)} == {"before", "after"}


def test_concurrent_writers_cannot_silently_accept_conflicting_facts(
    fact_store: tuple[SQLiteStore, FundamentalFact],
) -> None:
    store, fact = fact_store
    barrier = Barrier(2)

    def write(value: str) -> str:
        independent_store = SQLiteStore(store.path)
        barrier.wait(timeout=5)
        try:
            independent_store.upsert_fundamental_facts([
                replace(fact, value=Decimal(value)),
            ])
        except ValueError as error:
            assert "fundamental fact content conflict" in str(error)
            return "conflict"
        return "accepted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["100", "101"]))
    assert sorted(results) == ["accepted", "conflict"]
    assert len(_rows(store)) == 1
