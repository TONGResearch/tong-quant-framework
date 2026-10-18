"""Native financial observations are not canonical facts or historical PIT proof."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.application.sse_pilot_coverage import SSEPilotCoverageReader
from tong_quant.config.settings import load_settings
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import RawDataset, dataframe_sha256
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.akshare_financials import (
    FINANCIAL_SNAPSHOT_DATASET,
    AkShareFinancialSnapshotAdapter,
)
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE

NOW = datetime(2026, 10, 16, 5, tzinfo=UTC)


class Client:
    def stock_financial_benefit_new_ths(self, **kwargs):
        return pd.DataFrame(
            {
                "report_date": ["2026-06-30"] * 5,
                "metric_name": ["native_metric"] * 5,
                "value": ["0", "", None, "-1", "1.25"],
                "single": [None] * 5,
            }
        )


@pytest.fixture
def foundation(tmp_path: Path):
    store = SQLiteStore(tmp_path / "native.sqlite3")
    pipeline = DataIngestionPipeline(
        AkShareAdapter(
            client=Client(),
            clock=lambda: NOW,
            cache=DataFrameCache(tmp_path / "cache", timedelta(days=1), clock=lambda: NOW),
        ),
        store,
        artifact_store=FileSystemArtifactStore(tmp_path / "artifacts"),
    )
    pipeline.initialize()
    return store, pipeline


def test_capture_preserves_all_native_rows_without_creating_facts(foundation, tmp_path: Path):
    store, pipeline = foundation
    first = pipeline.capture_financial_statement("600000", "income")
    second = pipeline.capture_financial_statement("600000", "income")
    assert first.accepted == first.received == 5
    assert second.cached
    assert store.table_count("fundamental_facts") == 0
    assert store.table_count("research_reports") == 0
    assert store.table_count("provider_evidence_records") == 5
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("provider_artifact_observations") == 1
    records = store.provider_evidence(
        provider="akshare",
        dataset=FINANCIAL_SNAPSHOT_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=NOW,
    )
    records.sort(key=lambda row: row.payload["row_number"])
    assert [row.payload["native_row"]["value"] for row in records] == ["0", "", None, "-1", "1.25"]
    assert all(row.available_at == NOW and row.published_at is None for row in records)
    assert all(row.payload["canonical_metric"] is None for row in records)
    assert all(row.payload["accounting_unit"] is None for row in records)
    assert all(row.trust_level.value == "low" for row in records)
    assert all(row.availability_precision.value == "retrieval_time" for row in records)
    assert not store.provider_evidence(
        provider="akshare",
        dataset=FINANCIAL_SNAPSHOT_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=NOW - timedelta(seconds=1),
    )
    history = store.provider_artifact_history(
        provider="akshare", dataset=FINANCIAL_SNAPSHOT_DATASET, subject="600000"
    )
    content = (tmp_path / "artifacts" / history[0]["storage_key"]).read_bytes()
    assert sha256(content).hexdigest() == records[0].raw_data_hash
    assert len(json.loads(json.loads(content)["frame"])["data"]) == 5


@pytest.mark.parametrize("defect", ("source", "symbol", "schema", "hash", "raw_frame"))
def test_snapshot_rejects_mismatched_identity_schema_and_content(defect):
    frame = Client().stock_financial_benefit_new_ths()
    params = {"symbol": "600000", "statement": "income"}
    dataset = RawDataset(
        "fundamental_facts",
        frame,
        NOW,
        "akshare:financial:income",
        params,
        dataframe_sha256(frame, params),
    )
    request = ProviderDatasetRequest(
        FINANCIAL_SNAPSHOT_DATASET, Market.CHINA_A, "600000", NOW, {"statement": "income"}
    )
    if defect == "source":
        dataset = replace(dataset, source="unverified-other-source")
    elif defect == "symbol":
        request = replace(request, subject="600001")
    elif defect == "schema":
        dataset = replace(dataset, frame=frame.drop(columns="value"))
    elif defect == "hash":
        dataset = replace(dataset, raw_data_hash="f" * 64)
    else:
        original = frame.to_json(orient="table", date_format="iso", force_ascii=True)
        modified = frame.copy()
        modified.loc[0, "value"] = "999"
        dataset = replace(dataset, frame=modified, raw_frame_json=original)
    with pytest.raises(ValueError):
        AkShareFinancialSnapshotAdapter(dataset).fetch(request)


def test_financial_snapshot_and_audit_roll_back_on_repository_failure(foundation, monkeypatch):
    store, pipeline = foundation

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic persistence failure")

    monkeypatch.setattr(store, "save_provider_evidence_records", fail)
    with pytest.raises(RuntimeError, match="synthetic persistence failure"):
        pipeline.capture_financial_statement("600000", "income")
    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("provider_evidence_records") == 0
    assert store.table_count("provider_artifacts") == 0


def test_native_snapshot_inventory_does_not_clear_canonical_financial_gaps(foundation):
    store, pipeline = foundation
    pipeline.capture_financial_statement("600000", "income")
    record = SSEPilotCoverageReader(store, load_settings(Path("config/default.toml"))).read(
        "600000",
        MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 10, 16), NOW),
        calendar_start=date(2026, 10, 1),
        universe="china_a_all",
    )
    assert record["datasets"]["native_financial_snapshots"]["observations"] == 5
    assert record["datasets"]["fundamentals"]["observations"] == 0
    assert "fundamental_metrics_missing" in record["blocking_requirements"]
    assert record["strict_validation_authorized"] is False


def test_native_snapshot_rejects_credential_like_fields_before_publication():
    frame = Client().stock_financial_benefit_new_ths()
    frame["secret"] = "fixture-only-not-a-real-credential"
    params = {"symbol": "600000", "statement": "income"}
    dataset = RawDataset(
        "fundamental_facts",
        frame,
        NOW,
        "akshare:financial:income",
        params,
        dataframe_sha256(frame, params),
    )
    with pytest.raises(ValueError, match="credential-like"):
        AkShareFinancialSnapshotAdapter(dataset).fetch(
            ProviderDatasetRequest(
                FINANCIAL_SNAPSHOT_DATASET, Market.CHINA_A, "600000", NOW, {"statement": "income"}
            )
        )
