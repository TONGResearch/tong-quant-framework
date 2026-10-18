"""Deterministic fixtures are not independent provider-quality evidence."""

import gzip
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.price_evidence import daily_bar_content_hash, matches_daily_bar
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, DataTrustLevel, Market
from tong_quant.domain.models import TradingSession
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE

NOW = datetime(2026, 10, 16, 4, tzinfo=UTC)
REQUEST = DailyBarRequest("600000", "20261014", "20261016")
QUERY = MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 10, 16), NOW)


class Client:
    def __init__(self) -> None:
        self.calls = 0
        self.frame = pd.DataFrame(
            {
                "日期": ["2026-10-14", "2026-10-15"],
                "股票代码": ["600000", "600000"],
                "开盘": [10.0, 10.5],
                "收盘": [10.5, 10.8],
                "最高": [11.0, 11.0],
                "最低": [9.0, 10.0],
                "成交量": [1000, 1200],
                "成交额": [None, None],
            }
        )

    def stock_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.calls += 1
        return self.frame.copy()


@pytest.fixture
def foundation(tmp_path: Path):
    client = Client()
    cache = DataFrameCache(tmp_path / "cache", timedelta(days=1), clock=lambda: NOW)
    store = SQLiteStore(tmp_path / "prices.sqlite3")
    pipeline = DataIngestionPipeline(
        AkShareAdapter(client=client, cache=cache, clock=lambda: NOW),
        store,
        artifact_store=FileSystemArtifactStore(tmp_path / "artifacts"),
    )
    pipeline.initialize()
    return client, pipeline, store


def inventory(store: SQLiteStore):
    store.upsert_trading_sessions(
        TradingSession(Market.CHINA_A, date(2026, 10, 14) + timedelta(days=i), True, NOW, "fixture")
        for i in range(3)
    )
    return SSERuntimeInputReader(MarketDataService(store)).read(
        "600000", QUERY, calendar_start=date(2026, 10, 14)
    )


def test_price_rows_snapshot_and_source_binding_commit_together_and_replay_idempotently(
    tmp_path: Path,
    foundation,
) -> None:
    client, pipeline, store = foundation
    first = pipeline.ingest_daily_bars(REQUEST)
    second = pipeline.ingest_daily_bars(REQUEST)
    assert first.accepted == second.accepted == 2
    assert not first.cached and second.cached and client.calls == 1
    assert store.table_count("daily_bars") == 2
    assert store.table_count("provider_evidence_records") == 2
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("provider_artifact_observations") == 1
    history = store.provider_artifact_history(
        provider="akshare", dataset="a_share_daily", subject="600000"
    )
    content = (tmp_path / "artifacts" / history[0]["storage_key"]).read_bytes()
    assert sha256(content).hexdigest() == history[0]["content_hash"]
    assert json.loads(content)["parameters"]["adjustment"] == "none"
    snapshot = inventory(store)
    assert len(snapshot.price_evidence) == 2
    assert len(snapshot.previous_close_evidence) == 1
    record = snapshot.previous_close_evidence[0]
    assert record.trust_level is DataTrustLevel.LOW
    assert record.raw_data_hash == history[0]["content_hash"]
    assert record.available_at == NOW
    assert snapshot.previous_close.turnover is None
    assert record.payload["bar_hash"] == daily_bar_content_hash(snapshot.previous_close)
    assert record.payload["artifact_id"] == history[0]["artifact_id"]
    assert snapshot.to_record()["previous_close_evidence_ids"] == [record.evidence_id]
    assert "price_provenance_unavailable" not in {gap.code for gap in snapshot.gaps}
    assert {"price_evidence_trust_insufficient", "price_artifact_review_required"} <= {
        gap.code for gap in snapshot.gaps
    }
    assert snapshot.input_hash == inventory(store).input_hash
    reader = SSERuntimeInputReader(MarketDataService(store))
    before = reader.read(
        "600000",
        replace(QUERY, as_of=NOW - timedelta(seconds=1)),
        calendar_start=date(2026, 10, 14),
    )
    assert before.price_evidence == () and before.previous_close is None


@pytest.mark.parametrize(
    "field,value",
    (
        ("open", "10.6"),
        ("volume", "999"),
        ("turnover", "0"),
        ("source", "akshare:other"),
        ("adjustment", "forward"),
    ),
)
def test_similar_prices_cannot_launder_different_rows_or_sources(foundation, field, value) -> None:
    _, pipeline, store = foundation
    pipeline.ingest_daily_bars(REQUEST)
    snapshot = inventory(store)
    record = snapshot.previous_close_evidence[0]
    changed = replace(
        record, payload={**record.payload, "bar": {**record.payload["bar"], field: value}}
    )
    assert not matches_daily_bar(changed, snapshot.previous_close)
    shifted = replace(record, available_at=NOW - timedelta(seconds=1))
    assert not matches_daily_bar(shifted, snapshot.previous_close)


def test_conflicting_evidence_is_visible_without_overwriting_the_price(foundation) -> None:
    _, pipeline, store = foundation
    result = pipeline.ingest_daily_bars(REQUEST)
    before = inventory(store)
    record = before.previous_close_evidence[0]
    changed = replace(
        record,
        evidence_id=sha256(b"conflicting fixture").hexdigest(),
        payload={**record.payload, "bar_hash": "a" * 64},
    )
    store.save_provider_evidence_records((changed,), batch_id=result.batch_id)
    after = inventory(store)
    assert after.previous_close == before.previous_close
    assert changed in after.price_evidence
    assert "price_evidence_conflict" in {gap.code for gap in after.gaps}
    assert after.input_hash != before.input_hash


@pytest.mark.parametrize("method", ("upsert_daily_bars", "save_data_availability_warning"))
def test_failed_canonical_or_warning_write_rolls_back_evidence_and_new_artifact(
    tmp_path: Path,
    foundation,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
) -> None:
    _, pipeline, store = foundation

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(store, method, fail)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        pipeline.ingest_daily_bars(REQUEST)
    for table in (
        "instruments",
        "daily_bars",
        "ingestion_batches",
        "raw_dataset_fingerprints",
        "provider_evidence_records",
        "provider_artifacts",
        "provider_artifact_observations",
    ):
        assert store.table_count(table) == 0
    assert list((tmp_path / "artifacts").rglob("*.bin")) == []


def test_cache_tampering_is_rejected_without_creating_a_new_evidence_batch(
    tmp_path: Path, foundation
) -> None:
    _, pipeline, store = foundation
    pipeline.ingest_daily_bars(REQUEST)
    path = next((tmp_path / "cache").glob("*.json.gz"))
    with gzip.open(path, "rt") as handle:
        cached = json.load(handle)
    frame = json.loads(cached["frame"])
    frame["data"][0]["收盘"] = 10.6
    cached["frame"] = json.dumps(frame)
    with gzip.open(path, "wt") as handle:
        json.dump(cached, handle)
    with pytest.raises(ValueError, match="cached dataset fingerprint"):
        pipeline.ingest_daily_bars(REQUEST)
    assert store.table_count("ingestion_batches") == 1
    assert store.table_count("provider_evidence_records") == 2


def test_wrong_security_is_rejected_before_database_or_artifact_writes(
    tmp_path: Path, foundation
) -> None:
    client, pipeline, store = foundation
    client.frame["股票代码"] = "600001"
    with pytest.raises(ValueError, match="identifiers do not match"):
        pipeline.ingest_daily_bars(REQUEST)
    assert store.table_count("daily_bars") == store.table_count("ingestion_batches") == 0
    assert not (tmp_path / "artifacts").exists()


def test_unfinished_same_day_bar_stays_partial_and_never_enters_price_evidence(foundation) -> None:
    client, pipeline, store = foundation
    today = client.frame.iloc[[1]].copy()
    today["日期"] = "2026-10-16"
    client.frame = pd.concat((client.frame, today), ignore_index=True)
    result = pipeline.ingest_daily_bars(REQUEST)
    assert (result.received, result.accepted, result.rejected) == (3, 2, 1)
    assert len(inventory(store).price_evidence) == 2


def test_relaxed_adjusted_ingestion_does_not_acquire_unadjusted_evidence(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "adjusted.sqlite3")
    pipeline = DataIngestionPipeline(
        AkShareAdapter(client=Client(), clock=lambda: NOW), store, strict_point_in_time=False
    )
    pipeline.initialize()
    result = pipeline.ingest_daily_bars(replace(REQUEST, adjustment=Adjustment.FORWARD))
    assert result.accepted == 2
    assert store.table_count("provider_evidence_records") == 0


def test_serialization_precision_loss_cannot_be_mistaken_for_exact_evidence(foundation) -> None:
    client, pipeline, store = foundation
    client.frame.loc[0, "开盘"] = 10.1234567890123
    with pytest.raises(ValueError, match="cannot reproduce"):
        pipeline.ingest_daily_bars(REQUEST)
    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("daily_bars") == 0


def test_out_of_window_prices_are_rejected_before_any_evidence_write(foundation) -> None:
    _, pipeline, store = foundation
    with pytest.raises(ValueError, match="does not match its captured query"):
        pipeline.ingest_daily_bars(replace(REQUEST, start_date="20261015"))
    assert store.table_count("provider_evidence_records") == 0
    assert store.table_count("daily_bars") == 0


def test_credential_like_columns_are_rejected_before_cache_or_artifact_publication(
    tmp_path: Path,
    foundation,
) -> None:
    client, pipeline, store = foundation
    client.frame["token"] = "synthetic rejected field"
    with pytest.raises(ValueError, match="credential-like field"):
        pipeline.ingest_daily_bars(REQUEST)
    assert list((tmp_path / "cache").glob("*.json.gz")) == []
    assert not (tmp_path / "artifacts").exists()
    assert store.table_count("ingestion_batches") == 0


def test_cache_write_rejects_a_contradictory_declared_fingerprint(tmp_path: Path) -> None:
    dataset = AkShareAdapter(client=Client(), clock=lambda: NOW).daily_bars(REQUEST).dataset
    cache = DataFrameCache(tmp_path / "unused", timedelta(days=1), clock=lambda: NOW)
    with pytest.raises(ValueError, match="fingerprint integrity"):
        cache.put(replace(dataset, raw_data_hash="a" * 64))
    assert not (tmp_path / "unused").exists()


def test_artifact_and_observation_metadata_cannot_be_substituted(foundation) -> None:
    _, pipeline, store = foundation
    pipeline.ingest_daily_bars(REQUEST)
    snapshot = inventory(store)
    record = snapshot.previous_close_evidence[0]
    for changed in (
        replace(record, raw_data_hash="a" * 64),
        replace(record, payload={**record.payload, "artifact_id": "a" * 64}),
        replace(record, observed_at=record.observed_at - timedelta(seconds=1)),
    ):
        assert not matches_daily_bar(changed, snapshot.previous_close)
