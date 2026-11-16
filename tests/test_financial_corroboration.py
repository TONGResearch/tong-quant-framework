"""A source-bound numeric match cannot authorize canonical facts or research."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calibration.financial_review import FilingRowReview, corroborate_financial_row
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import RawDataset
from tong_quant.data.providers.akshare_financials import AkShareFinancialSnapshotAdapter
from tong_quant.data.providers.cninfo_direct import (
    CnInfoArtifactDownload,
    CnInfoDirectEvidenceAdapter,
    CnInfoQueryResult,
)
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    FINANCIAL_SNAPSHOT_DATASET,
    ProviderArtifact,
    ProviderArtifactStatus,
    ProviderDatasetRequest,
    provider_artifact_id,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 10, 18, 16, tzinfo=UTC)
CAPTURED = NOW - timedelta(minutes=1)
PUBLISHED = datetime(2026, 4, 30, tzinfo=UTC)
PDF = b"%PDF-1.4\nsynthetic-source-not-a-real-filing"
URL = "https://static.cninfo.com.cn/finalpage/2026-04-30/1234567890.PDF"


def _inputs(value="123000000.0000"):
    raw = RawDataset(
        "fundamental_facts",
        pd.DataFrame([{"report_date": "2026-03-31", "metric_name": "operating_income_total",
                       "value": value}]),
        CAPTURED, "akshare:financial:income", {"symbol": "600000", "statement": "income"},
    )
    raw = replace(raw, raw_data_hash=raw.content_hash())
    adapter = AkShareFinancialSnapshotAdapter(raw)
    request = ProviderDatasetRequest(
        FINANCIAL_SNAPSHOT_DATASET, Market.CHINA_A, "600000", NOW, {"statement": "income"},
    )
    batch = adapter.fetch(request)
    digest = sha256(PDF).hexdigest()
    filing = ProviderArtifact(
        provider_artifact_id(
            provider="cninfo_direct", dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A, subject="600000", source_identity="1234567890",
            source_reference=URL, content_hash=digest,
        ),
        "cninfo_direct", CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "600000",
        "1234567890", URL, PUBLISHED, CAPTURED, digest, "application/pdf",
        AvailabilityPrecision.EXACT, DataTrustLevel.MEDIUM, PDF,
    )
    review = FilingRowReview(
        "600000", "revenue", "income", "operating_income_total", batch.records[0].evidence_id,
        date(2026, 3, 31), date(2026, 1, 1), "flow", "group", "CNY", Decimal("123"),
        Decimal("1000000"), Decimal("1"), digest, (17,), "group current period; unaudited",
        "bank", NOW,
    )
    return review, batch.records[0], batch.artifacts[0].content, filing, adapter, request


def test_decimal_match_is_deterministic_partial_and_not_an_authorization():
    review, native, content, filing, _, _ = _inputs()
    first = corroborate_financial_row(review, native, content, filing, as_of=NOW)
    assert first == corroborate_financial_row(review, native, content, filing, as_of=NOW)
    assert first["status"] == "NUMERIC_MATCH_REVIEW_REQUIRED"
    assert first["issuer_value_cny"] == first["native_value_under_hypothesis"] == "123000000"
    assert first["available_at"] == NOW.isoformat()
    assert first["trust_level"] == "low"
    assert first["availability_precision"] == "retrieval_time"
    assert first["native_limitations"] == list(native.limitations)
    assert first["filing_trust_level"] == "medium"
    assert all(first[key] is False for key in (
        "canonical_population_authorized", "historical_replay_eligible",
        "investment_scoring_authorized", "validation_authorized", "independent_provider_validation",
    ))
    digest = first.pop("report_hash")
    assert digest == sha256(json.dumps(
        first, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


@pytest.mark.parametrize(("value", "filing_value", "status"), [
    ("", "123", "MISSING_NATIVE_VALUE"),
    (None, "123", "MISSING_NATIVE_VALUE"),
    ("0", "0", "NUMERIC_MATCH_REVIEW_REQUIRED"),
    ("-1200000", "-1.2", "NUMERIC_MATCH_REVIEW_REQUIRED"),
    ("123000001", "123", "VALUE_CONFLICT"),
    ("1234567890123456789000000", "1234567890123456789", "NUMERIC_MATCH_REVIEW_REQUIRED"),
])
def test_missing_zero_negative_conflict_and_exact_large_values(value, filing_value, status):
    review, native, content, filing, _, _ = _inputs(value)
    review = replace(review, filing_value=Decimal(filing_value))
    result = corroborate_financial_row(review, native, content, filing, as_of=NOW)
    assert result["status"] == status
    assert result["canonical_population_authorized"] is False


@pytest.mark.parametrize("defect", [
    "as_of", "review_time", "native_time", "publication_time", "filing_time", "period",
    "row", "row_index", "metric", "statement", "subject", "market", "provider",
    "native_bytes", "filing_digest", "artifact_id", "source_reference",
])
def test_rejects_future_mismatched_or_tampered_inputs(defect):
    review, native, content, filing, _, _ = _inputs()
    as_of = NOW
    future = NOW + timedelta(days=1)
    if defect == "as_of":
        as_of = CAPTURED
    elif defect == "review_time":
        review = replace(review, reviewed_at=future)
    elif defect == "native_time":
        native = replace(native, retrieved_at=future)
    elif defect == "publication_time":
        native = replace(native, published_at=future, available_at=future, retrieved_at=future)
    elif defect == "filing_time":
        filing = replace(filing, retrieved_at=future)
    elif defect == "period":
        review = replace(review, period_end=date(2027, 3, 31))
    elif defect == "row":
        native = replace(native, payload={**native.payload, "native_row": {"value": "999"}})
    elif defect == "row_index":
        native = replace(native, payload={**native.payload, "row_number": True})
    elif defect == "metric":
        review = replace(review, native_metric="net_profit")
    elif defect == "statement":
        review = replace(review, statement="balance")
    elif defect == "subject":
        review = replace(review, subject="600001")
    elif defect == "market":
        native = replace(native, market=Market.US)
    elif defect == "provider":
        native = replace(native, provider="another_provider")
    elif defect == "native_bytes":
        content += b" "
    elif defect == "filing_digest":
        review = replace(review, filing_sha256="a" * 64)
    elif defect == "artifact_id":
        filing = replace(filing, artifact_id="a" * 64)
    elif defect == "source_reference":
        native = replace(native, source_reference="akshare:financial:balance")
    with pytest.raises(ValueError):
        corroborate_financial_row(review, native, content, filing, as_of=as_of)


@pytest.mark.parametrize("fields", [
    {"filing_scale": Decimal("0")}, {"native_scale_hypothesis": Decimal("-1")},
    {"filing_value": Decimal("NaN")}, {"filing_value": Decimal("Infinity")},
    {"filing_value": Decimal("1e1001")}, {"filing_value": 123.0}, {"filing_value": True},
    {"source_pages": (True,)}, {"source_pages": (0,)}, {"source_pages": (17, 17)},
    {"filing_sha256": "Z" * 64}, {"period_start": None},
    {"value_kind": "stock"}, {"currency": "USD"}, {"reporting_scope": "unknown"},
    {"reviewed_at": NOW.replace(tzinfo=None)},
])
def test_requires_explicit_bounded_semantics(fields):
    review, _, _, _, _, _ = _inputs()
    with pytest.raises(ValueError):
        replace(review, **fields)


def test_unknown_native_trust_is_not_raised_and_annotations_are_screened():
    review, native, content, filing, _, _ = _inputs()
    result = corroborate_financial_row(
        review, replace(native, trust_level=DataTrustLevel.UNKNOWN), content, filing, as_of=NOW,
    )
    assert result["trust_level"] == "unknown"
    with pytest.raises(ValueError, match="credential-like"):
        corroborate_financial_row(
            replace(review, value_column="api_key=fixture-not-a-real-key"),
            native, content, filing, as_of=NOW,
        )


class _FilingClient:
    def search(self, *args, **kwargs):
        return CnInfoQueryResult(({
            "secCode": "600000", "secName": "Fixture", "orgId": "fixture",
            "announcementId": "1234567890", "announcementTitle": "Quarterly report",
            "announcementTime": int(PUBLISHED.timestamp() * 1000),
            "adjunctUrl": "finalpage/2026-04-30/1234567890.PDF",
        },), "f" * 64, 1, 1, 1, False)

    def download_artifact(self, url):
        return CnInfoArtifactDownload(
            ProviderArtifactStatus.CAPTURED, url, url, "application/pdf", PDF, "",
        )


def test_cli_reads_snapshot_without_writes_and_keeps_rejected_rows(tmp_path: Path):
    review, _, _, _, adapter, request = _inputs()
    database = tmp_path / "research.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    artifacts = tmp_path / "artifacts"
    ingestion = ProviderNeutralIngestionService(
        store=store, artifact_store=FileSystemArtifactStore(artifacts), clock=lambda: CAPTURED,
    )
    ingestion.ingest(adapter, request)
    ingestion.ingest(
        CnInfoDirectEvidenceAdapter(client=_FilingClient(), clock=lambda: CAPTURED),
        ProviderDatasetRequest(CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "600000", NOW, {
            "start_date": "2026-04-30", "end_date": "2026-04-30",
            "capture_artifacts": "true", "max_artifacts": "1",
        }),
    )
    plan = tmp_path / "review.toml"
    plan.write_text(f'''[common]
subject = "600000"
statement = "income"
native_metric = "operating_income_total"
native_evidence_id = "{review.native_evidence_id}"
period_end = "2026-03-31"
period_start = "2026-01-01"
value_kind = "flow"
reporting_scope = "group"
currency = "CNY"
filing_value = "123"
filing_scale = "1000000"
native_scale_hypothesis = "1"
filing_sha256 = "{review.filing_sha256}"
source_pages = [17]
value_column = "group current period"
sector_profile = "bank"
reviewed_at = "{NOW.isoformat()}"
[[rows]]
canonical_metric = "revenue"
[[rows]]
canonical_metric = "missing_profit"
native_evidence_id = "{'a' * 64}"
''', encoding="utf-8")
    output = tmp_path / "review.json"
    args = [sys.executable, "scripts/review_financial_observations.py", "--database", str(database),
            "--artifact-root", str(artifacts), "--review-plan", str(plan),
            "--as-of", NOW.isoformat(), "--output", str(output)]
    before = database.read_bytes()
    process = subprocess.run(args, capture_output=True, text=True, check=False)
    assert process.returncode == 2, process.stderr
    result = json.loads(output.read_text())
    assert [row["status"] for row in result["results"]] == [
        "NUMERIC_MATCH_REVIEW_REQUIRED", "INPUT_REJECTED",
    ]
    assert result["review_plan_sha256"] == sha256(plan.read_bytes()).hexdigest()
    assert result["canonical_population_authorized"] is False
    assert output.stat().st_mode & 0o777 == 0o600
    assert database.read_bytes() == before
    assert store.table_count("fundamental_facts") == store.table_count("research_reports") == 0
    assert subprocess.run(args, capture_output=True, check=False).returncode == 2
    assert json.loads(output.read_text()) == result
