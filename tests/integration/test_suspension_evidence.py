"""Synthetic lifecycle evidence checks safety, not real provider continuity."""

import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.calibration.models import CalibrationDataset, CalibrationQuery
from tong_quant.data.models import ProviderResponse, RawDataset, SecurityLifecycleEvent
from tong_quant.data.normalization import normalize_suspension_lifecycle
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.calibration import AkShareCalibrationAdapter
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    LifecycleEventType,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import Instrument, InstrumentStatus
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE

NOW = datetime(2026, 10, 16, tzinfo=UTC)


class SuspensionClient:
    def __init__(self) -> None:
        self.calls = 0
        self.frame = pd.DataFrame(
            {
                "代码": ["600000"],
                "名称": ["Synthetic"],
                "停牌时间": [date(2026, 10, 12)],
                "停牌截止时间": [date(2026, 10, 13)],
                "预计复牌时间": [date(2026, 10, 14)],
                "停牌原因": ["Synthetic event"],
                "停牌期限": ["one day"],
            }
        )

    def stock_tfp_em(self, **kwargs) -> pd.DataFrame:
        assert kwargs["date"] == "20261015"
        self.calls += 1
        return self.frame.copy()

    def stock_zh_a_stop_em(self) -> pd.DataFrame:
        raise AssertionError("Delisted quote endpoint must never be fetched")


@pytest.fixture
def foundation(tmp_path: Path):
    client = SuspensionClient()
    adapter = AkShareAdapter(client=client, clock=lambda: NOW, max_attempts=1)
    store = SQLiteStore(tmp_path / "lifecycle.sqlite3")
    pipeline = DataIngestionPipeline(adapter, store)
    pipeline.initialize()
    return client, adapter, pipeline, store


def runtime(store: SQLiteStore, *, as_of: datetime = NOW):
    return SSERuntimeInputReader(MarketDataService(store)).read(
        "600000",
        MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 10, 16), as_of),
        calendar_start=date(2026, 10, 1),
    )


def test_delisted_quotes_cannot_be_requested_as_a_suspension_snapshot(foundation) -> None:
    client, adapter, pipeline, store = foundation
    with pytest.raises(DataProviderError, match="delisted-market quote"):
        adapter.suspended_stocks()
    with pytest.raises(DataProviderError, match="partial event evidence"):
        pipeline.ingest_suspended_status()
    assert client.calls == 0
    assert store.table_count("instrument_status_history") == 0
    assert store.table_count("ingestion_batches") == 0


@pytest.mark.parametrize("resumption", ("2026-10-13", "2026-10-20", None))
def test_end_or_expected_date_never_confirms_resumption(foundation, resumption) -> None:
    client, _, pipeline, store = foundation
    client.frame["预计复牌时间"] = resumption
    result = pipeline.ingest_suspension_lifecycle("20261015")
    assert (result.received, result.accepted, result.rejected) == (1, 1, 0)
    snapshot = runtime(store)
    assert [event.event_type for event in snapshot.lifecycle_events] == [
        LifecycleEventType.SUSPENSION_STARTED
    ]
    assert snapshot.lifecycle_events[0].trust_level is DataTrustLevel.LOW
    assert snapshot.lifecycle_events[0].available_at == NOW
    assert snapshot.lifecycle_events[0].details["reported_end_date"] == "2026-10-13"
    assert snapshot.lifecycle_events[0].details["resumption_confirmation"] == "unverified"
    assert len(snapshot.lifecycle_evidence) == 1
    assert len(snapshot.lifecycle_reviews) == 1
    assert snapshot.lifecycle_reviews[0].disposition.value == "observation_only"
    assert snapshot.status is None
    assert {
        "status_missing",
        "lifecycle_coverage_unverified",
        "lifecycle_source_review_required",
    } <= {gap.code for gap in snapshot.gaps}
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("instrument_status_history") == 0
    assert runtime(store, as_of=NOW - timedelta(seconds=1)).lifecycle_events == ()
    assert runtime(store, as_of=NOW - timedelta(seconds=1)).lifecycle_evidence == ()


@pytest.mark.parametrize(
    "column,value",
    (
        ("代码", "invalid"),
        ("代码", "1.2"),
        ("代码", None),
        ("停牌时间", "20260230"),
        ("停牌时间", None),
        ("停牌时间", "2026-10-17"),
    ),
)
def test_rejected_rows_remain_in_artifact_and_never_imply_normal_status(
    foundation,
    column,
    value,
) -> None:
    client, _, pipeline, store = foundation
    client.frame[column] = value
    result = pipeline.ingest_suspension_lifecycle("20261015")
    assert (result.accepted, result.rejected) == (0, 1)
    assert "Malformed identifiers" in " ".join(result.warnings)
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("security_lifecycle_events") == 0
    assert "lifecycle_coverage_unverified" in {gap.code for gap in runtime(store).gaps}


@pytest.mark.parametrize("query", ("20261017", "20260230", "2026-10-15", "invalid"))
def test_bad_or_future_query_is_rejected_before_fetch(foundation, query) -> None:
    client, adapter, _, store = foundation
    with pytest.raises(ValueError):
        adapter.suspension_events(query)
    assert client.calls == 0
    assert store.table_count("ingestion_batches") == 0


def test_empty_capture_is_not_a_normal_status_or_proof_of_no_suspensions(foundation) -> None:
    client, _, pipeline, store = foundation
    client.frame = pd.DataFrame()
    result = pipeline.ingest_suspension_lifecycle("20261015")
    assert result.accepted == result.received == 0
    assert "no normalized evidence" in " ".join(result.warnings)
    assert store.table_count("provider_artifacts") == 1
    assert runtime(store).status is None


def test_snapshot_cache_version_isolated_from_pre_repair_data(foundation, tmp_path: Path) -> None:
    client, _, _, store = foundation
    cache = DataFrameCache(tmp_path / "cache", timedelta(days=1), clock=lambda: NOW)
    cache.put(
        RawDataset(
            "security_lifecycle_suspension", client.frame, NOW, "legacy", {"date": "20261015"}
        )
    )
    pipeline = DataIngestionPipeline(
        AkShareAdapter(client=client, clock=lambda: NOW, cache=cache), store
    )
    first = pipeline.ingest_suspension_lifecycle("20261015")
    second = pipeline.ingest_suspension_lifecycle("20261015")
    assert not first.cached and second.cached
    assert client.calls == 1
    assert store.table_count("security_lifecycle_events") == 1
    assert store.table_count("provider_evidence_records") == 1
    assert store.table_count("provider_artifacts") == 1


def test_canonical_write_failure_rolls_back_source_evidence_and_files(
    foundation,
    monkeypatch,
) -> None:
    _, _, pipeline, store = foundation

    def fail(*args):
        raise RuntimeError("synthetic canonical failure")

    monkeypatch.setattr(store, "upsert_security_lifecycle_events", fail)
    with pytest.raises(RuntimeError, match="canonical failure"):
        pipeline.ingest_suspension_lifecycle("20261015")
    for table in (
        "ingestion_batches",
        "provider_evidence_records",
        "provider_artifacts",
        "provider_artifact_observations",
        "instruments",
    ):
        assert store.table_count(table) == 0
    assert not list((store.path.parent / "raw/provider-artifacts").rglob("*.json"))


def test_suspension_capture_preserves_existing_company_metadata(foundation) -> None:
    _, _, pipeline, store = foundation
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Prior name",
        exchange="SSE",
        industry="Research industry",
        available_at=NOW - timedelta(days=2),
        source="fixture",
    )
    store.upsert_instruments((instrument,))
    pipeline.ingest_suspension_lifecycle("20261015")
    assert store.get_instrument("600000", Market.CHINA_A, AssetType.EQUITY, as_of=NOW) == instrument


def test_legacy_false_resumption_is_visible_but_flagged_without_rewriting(foundation) -> None:
    _, _, pipeline, store = foundation
    pipeline.ingest_suspension_lifecycle("20261015")
    instrument = runtime(store).instrument
    assert instrument is not None
    store.upsert_security_lifecycle_events(
        (
            SecurityLifecycleEvent(
                instrument,
                LifecycleEventType.TRADING_RESUMED,
                date(2026, 10, 13),
                NOW,
                "akshare",
                provider_dataset="security_lifecycle_suspension",
                trust_level=DataTrustLevel.MEDIUM,
            ),
        )
    )
    store.upsert_instrument_statuses(
        (
            InstrumentStatus(
                instrument,
                date(2026, 10, 16),
                SecurityStatus.SUSPENDED,
                False,
                NOW,
                "akshare",
                provider_dataset="instrument_status_suspended",
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.HIGH,
                raw_data_hash="a" * 64,
            ),
        )
    )
    snapshot = runtime(store)
    assert len(snapshot.lifecycle_events) == 2
    assert sum(review.disposition.value == "quarantined"
               for review in snapshot.lifecycle_reviews) == 1
    assert snapshot.status_review.disposition.value == "quarantined"
    assert {"legacy_suspension_history_unverified", "legacy_suspension_status_unverified"} <= {
        gap.code for gap in snapshot.gaps
    }
    assert store.table_count("security_lifecycle_events") == 2


def test_duplicate_source_keys_cannot_silently_collapse_conflicting_events(foundation) -> None:
    client, _, pipeline, store = foundation
    client.frame = pd.concat((client.frame, client.frame), ignore_index=True)
    with pytest.raises(ValueError, match="duplicate suspension"):
        pipeline.ingest_suspension_lifecycle("20261015")
    assert store.table_count("provider_artifacts") == 0


def test_frame_credentials_are_rejected_before_any_publication(foundation) -> None:
    client, _, pipeline, store = foundation
    client.frame["password"] = "synthetic-value-not-a-real-credential"
    with pytest.raises(ValueError):
        pipeline.ingest_suspension_lifecycle("20261015")
    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("provider_artifacts") == 0


def test_normalizer_keeps_non_start_metadata_but_does_not_raise_trust(foundation) -> None:
    _, adapter, _, _ = foundation
    dataset = adapter.suspension_events("20261015").dataset
    event = normalize_suspension_lifecycle(dataset, batch_id="fixture")[0]
    assert event.trust_level is DataTrustLevel.LOW
    assert event.details["expected_resumption_date"] == "2026-10-14"
    assert (
        normalize_suspension_lifecycle(
            replace(dataset, frame=dataset.frame.assign(停牌时间="2026-10-20")), batch_id="fixture"
        )
        == []
    )


def test_calibration_cannot_reintroduce_forecast_resumption_as_confirmed_event(foundation) -> None:
    _, adapter, _, _ = foundation
    snapshot = AkShareCalibrationAdapter(adapter).calibration_snapshot(CalibrationQuery(
        CalibrationDataset.SUSPENSION_STATUS, NOW, {"trade_date": "20261015"}
    ))
    assert len(snapshot.records) == 1
    assert snapshot.records[0].fields["event_type"] == "suspension_started"
    assert snapshot.records[0].fields["resumption_confirmation"] == "unverified"
    assert "never confirm resumption" in " ".join(snapshot.limitations)


@pytest.mark.parametrize("field", ("source", "fingerprint", "version", "query_date"))
def test_substituted_capture_is_rejected_before_persistence(foundation, monkeypatch, field) -> None:
    _, adapter, pipeline, store = foundation
    dataset = adapter.suspension_events("20261015").dataset
    if field == "source":
        dataset = replace(dataset, source="akshare:stock_zh_a_stop_em")
    elif field == "fingerprint":
        dataset = replace(dataset, raw_data_hash="f" * 64)
    elif field == "version":
        dataset = replace(dataset, parameters={"date": "20261015"})
    else:
        dataset = replace(dataset, parameters={**dataset.parameters, "date": "20261014"})
    monkeypatch.setattr(adapter, "suspension_events", lambda _: ProviderResponse(dataset, False))
    with pytest.raises(ValueError):
        pipeline.ingest_suspension_lifecycle("20261015")
    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("provider_artifacts") == 0


def test_invalid_cli_query_does_not_create_a_database(tmp_path: Path) -> None:
    database = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run(
        [sys.executable, "scripts/ingest_data.py", "--database", str(database),
         "suspension-events", "20990101"], capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "cannot be in the future" in result.stderr
    assert not database.exists()
