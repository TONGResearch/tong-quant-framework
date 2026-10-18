import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import pandas as pd
import pytest

from tong_quant.data.artifacts import (
    FileSystemArtifactStore,
    StoredProviderArtifact,
)
from tong_quant.data.calibration.engine import ProviderCalibrationEngine
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import ProviderResponse, RawDataset
from tong_quant.data.providers import cninfo_direct
from tong_quant.data.providers.cninfo import (
    CNINFO_DISCLOSURES_DATASET,
    CnInfoEvidenceAdapter,
)
from tong_quant.data.providers.cninfo_direct import (
    CnInfoArtifactDownload,
    CnInfoDirectEvidenceAdapter,
    CnInfoHttpClient,
    CnInfoQueryResult,
    cninfo_calibration_snapshot,
)
from tong_quant.data.providers.contracts import (
    ProviderArtifact,
    ProviderArtifactStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    provider_artifact_id,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 6, 20, 12, tzinfo=UTC)
PUBLISHED = datetime(2026, 6, 19, 7, 30, tzinfo=UTC)
PDF = b"%PDF-1.7\nsynthetic-cninfo-document"


def _announcement(
    *,
    announcement_id: str = "1222207866",
    adjunct_url: str = "finalpage/2026-06-19/1222207866.pdf",
    title: str = "2025 annual report",
) -> dict[str, object]:
    return {
        "secCode": "600000",
        "secName": "Pudong Development Bank",
        "orgId": "gssh0600000",
        "announcementId": announcement_id,
        "announcementTitle": title,
        "announcementTime": int(PUBLISHED.timestamp() * 1000),
        "adjunctUrl": adjunct_url,
        "associateAnnouncement": [{"announcementId": "1222207000"}],
    }


@dataclass
class _DirectClient:
    rows: tuple[dict[str, object], ...]
    download_status: ProviderArtifactStatus = ProviderArtifactStatus.CAPTURED

    def search(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category_code: str = "",
    ) -> CnInfoQueryResult:
        assert symbol == "600000"
        assert (start_date, end_date, category_code) == (
            "2026-06-01",
            "2026-06-20",
            "",
        )
        raw_hash = sha256(
            json.dumps(self.rows, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return CnInfoQueryResult(
            announcements=self.rows,
            raw_data_hash=raw_hash,
            total_announcements=len(self.rows),
            total_pages=1,
            pages_fetched=1,
            truncated=False,
        )

    def download_artifact(self, url: str) -> CnInfoArtifactDownload:
        if self.download_status is ProviderArtifactStatus.CAPTURED:
            return CnInfoArtifactDownload(
                status=self.download_status,
                requested_url=url,
                resolved_url=url,
                media_type="application/pdf",
                content=PDF,
                error_code="",
            )
        return CnInfoArtifactDownload(
            status=self.download_status,
            requested_url=url,
            resolved_url=url,
            media_type="application/octet-stream",
            content=b"",
            error_code="http_404",
        )


@dataclass
class _BatchAdapter:
    source: CnInfoDirectEvidenceAdapter
    batch: ProviderEvidenceBatch

    @property
    def provider_id(self) -> str:
        return self.source.provider_id

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return self.source.capabilities()

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        del request
        return self.batch


def _request(*, capture: bool = True) -> ProviderDatasetRequest:
    return ProviderDatasetRequest(
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=NOW,
        parameters={
            "start_date": "2026-06-01",
            "end_date": "2026-06-20",
            "capture_artifacts": str(capture).lower(),
            "max_artifacts": "10",
        },
    )


def test_direct_cninfo_ingestion_persists_content_addressed_artifact(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    artifact_store = FileSystemArtifactStore(tmp_path / "artifacts")
    service = ProviderNeutralIngestionService(
        store=store,
        artifact_store=artifact_store,
        clock=lambda: NOW,
    )
    adapter = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    )

    first = service.ingest(adapter, _request())
    second = service.ingest(adapter, _request())

    assert first.accepted == second.accepted == 1
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("provider_artifact_observations") == 1
    history = store.provider_artifact_history(
        provider="cninfo_direct",
        dataset=CNINFO_DISCLOSURES_DATASET,
        subject="600000",
    )
    assert len(history) == 1
    artifact_path = tmp_path / "artifacts" / str(history[0]["storage_key"])
    assert artifact_path.read_bytes() == PDF
    assert artifact_path.stat().st_mode & 0o777 == 0o600
    assert history[0]["content_hash"] == sha256(PDF).hexdigest()
    assert history[0]["trust_level"] == DataTrustLevel.MEDIUM.value
    assert history[0]["availability_precision"] == AvailabilityPrecision.EXACT.value
    assert json.loads(history[0]["related_source_identities_json"]) == [
        "1222207000"
    ]


def test_direct_cninfo_missing_artifact_and_url_change_remain_visible(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    artifact_store = FileSystemArtifactStore(tmp_path / "artifacts")
    first_service = ProviderNeutralIngestionService(
        store=store,
        artifact_store=artifact_store,
        clock=lambda: NOW,
    )
    missing = CnInfoDirectEvidenceAdapter(
        client=_DirectClient(
            (_announcement(adjunct_url="finalpage/old.pdf"),),
            download_status=ProviderArtifactStatus.MISSING,
        ),
        clock=lambda: NOW,
    )
    first_service.ingest(missing, _request())

    later = NOW + timedelta(days=1)
    captured = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(adjunct_url="finalpage/new.pdf"),)),
        clock=lambda: later,
    )
    ProviderNeutralIngestionService(
        store=store,
        artifact_store=artifact_store,
        clock=lambda: later,
    ).ingest(captured, _request())

    history = store.provider_artifact_history(
        provider="cninfo_direct",
        dataset=CNINFO_DISCLOSURES_DATASET,
        subject="600000",
        source_identity="1222207866",
    )
    assert [row["status"] for row in history] == ["missing", "captured"]
    assert {row["source_reference"] for row in history} == {
        "https://static.cninfo.com.cn/finalpage/old.pdf",
        "https://static.cninfo.com.cn/finalpage/new.pdf",
    }


def test_artifact_file_is_removed_when_database_transaction_fails(
    tmp_path: Path,
) -> None:
    class _FailingStore(SQLiteStore):
        def save_provider_artifacts(self, *args: Any, **kwargs: Any) -> int:
            del args, kwargs
            raise RuntimeError("simulated database failure")

    store = _FailingStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    artifact_root = tmp_path / "artifacts"
    service = ProviderNeutralIngestionService(
        store=store,
        artifact_store=FileSystemArtifactStore(artifact_root),
        clock=lambda: NOW,
    )
    adapter = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    )

    with pytest.raises(RuntimeError, match="simulated database failure"):
        service.ingest(adapter, _request())

    assert store.table_count("ingestion_batches") == 0
    assert list(artifact_root.rglob("*.pdf")) == []


def test_invalid_ingestion_clock_does_not_write_artifact(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    artifact_root = tmp_path / "artifacts"
    service = ProviderNeutralIngestionService(
        store=store,
        artifact_store=FileSystemArtifactStore(artifact_root),
        clock=lambda: NOW - timedelta(seconds=1),
    )
    adapter = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    )

    with pytest.raises(
        ValueError,
        match="ingestion completion cannot precede provider retrieval",
    ):
        service.ingest(adapter, _request())

    assert not artifact_root.exists()
    assert store.table_count("ingestion_batches") == 0


def test_ingestion_rejects_future_artifact_observation(tmp_path: Path) -> None:
    source = CnInfoDirectEvidenceAdapter(
        client=_DirectClient(
            (_announcement(),),
            download_status=ProviderArtifactStatus.MISSING,
        ),
        clock=lambda: NOW,
    )
    batch = source.fetch(_request())
    observation = replace(
        batch.artifact_observations[0],
        published_at=NOW + timedelta(seconds=1),
        retrieved_at=NOW + timedelta(seconds=2),
    )
    future_batch = replace(
        batch,
        retrieved_at=NOW + timedelta(seconds=2),
        records=(),
        artifact_observations=(observation,),
    )
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()

    with pytest.raises(ValueError, match="future publication data"):
        ProviderNeutralIngestionService(
            store=store,
            clock=lambda: NOW + timedelta(seconds=3),
        ).ingest(_BatchAdapter(source, future_batch), _request())

    assert store.table_count("ingestion_batches") == 0


def test_ingestion_rejects_artifact_trust_promotion(tmp_path: Path) -> None:
    source = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    )
    batch = source.fetch(_request())
    promoted = replace(batch.artifacts[0], trust_level=DataTrustLevel.VERIFIED)
    promoted_batch = replace(batch, artifacts=(promoted,))
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()

    with pytest.raises(ValueError, match="above its capability trust"):
        ProviderNeutralIngestionService(
            store=store,
            artifact_store=FileSystemArtifactStore(tmp_path / "artifacts"),
            clock=lambda: NOW,
        ).ingest(_BatchAdapter(source, promoted_batch), _request())

    assert not (tmp_path / "artifacts").exists()
    assert store.table_count("ingestion_batches") == 0


def test_direct_cninfo_metadata_only_does_not_create_false_missing_artifact() -> None:
    batch = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    ).fetch(_request(capture=False))

    assert len(batch.records) == 1
    assert batch.artifacts == ()
    assert batch.artifact_observations == ()
    assert batch.records[0].payload["artifact_status"] == "not_requested"
    assert "metadata was captured" in " ".join(
        limitation.description.lower() for limitation in batch.limitations
    )


def test_direct_cninfo_rejects_future_announcement_with_visible_warning() -> None:
    future_row = _announcement()
    future_row["announcementTime"] = int((NOW + timedelta(days=1)).timestamp() * 1000)

    batch = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((future_row,)),
        clock=lambda: NOW,
    ).fetch(_request(capture=False))

    assert batch.records == ()
    assert "cninfo_direct_future_rows_rejected" in {
        limitation.code for limitation in batch.limitations
    }


def test_artifact_repository_rejects_credential_bearing_source_url(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    content_hash = sha256(PDF).hexdigest()
    source_reference = (
        "https://static.cninfo.com.cn/finalpage/document.pdf?token=must-not-persist"
    )
    artifact = ProviderArtifact(
        artifact_id=provider_artifact_id(
            provider="synthetic",
            dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A,
            subject="600000",
            source_identity="announcement-1",
            source_reference=source_reference,
            content_hash=content_hash,
        ),
        provider="synthetic",
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        source_identity="announcement-1",
        source_reference=source_reference,
        published_at=PUBLISHED,
        retrieved_at=NOW,
        content_hash=content_hash,
        media_type="application/pdf",
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.MEDIUM,
        content=PDF,
    )

    with pytest.raises(ValueError, match="credential-like data"):
        store.save_provider_artifacts(
            (StoredProviderArtifact(artifact, "sha256/aa/artifact.pdf", False),),
            batch_id="not-written",
        )

    assert store.table_count("provider_artifacts") == 0


class _Transport:
    def fundamental_disclosures(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category: str = "",
    ) -> ProviderResponse:
        del symbol, start_date, end_date, category
        frame = pd.DataFrame(
            [
                {
                    "代码": "600000",
                    "简称": "Pudong Development Bank",
                    "公告标题": "2025 annual report",
                    "公告时间": PUBLISHED.isoformat(),
                    "公告链接": (
                        "https://www.cninfo.com.cn/new/disclosure/detail?"
                        "announcementId=1222207866"
                    ),
                }
            ]
        )
        return ProviderResponse(
            dataset=RawDataset(
                dataset="fundamental_publications_disclosure",
                frame=frame,
                retrieved_at=NOW,
                source="akshare:stock_zh_a_disclosure_report_cninfo",
                parameters={},
            ),
            cache_hit=False,
        )


def test_direct_and_akshare_transport_can_use_existing_calibration_engine() -> None:
    request = _request(capture=False)
    direct = CnInfoDirectEvidenceAdapter(
        client=_DirectClient((_announcement(),)),
        clock=lambda: NOW,
    ).fetch(request)
    transported = CnInfoEvidenceAdapter(_Transport()).fetch(request)
    direct_snapshot = cninfo_calibration_snapshot(direct, as_of=NOW)
    transported_snapshot = cninfo_calibration_snapshot(transported, as_of=NOW)

    report = ProviderCalibrationEngine().compare(
        direct_snapshot,
        transported_snapshot,
        fields=("symbol", "title", "published_at"),
        compared_at=NOW,
    )

    assert report.matched_count == 1
    assert report.consistency_score == 100
    assert report.primary_provider == "cninfo_direct"
    assert report.secondary_provider == "cninfo_via_akshare"


def test_cninfo_calibration_snapshot_excludes_future_evidence_visibly() -> None:
    transported = CnInfoEvidenceAdapter(_Transport()).fetch(_request(capture=False))

    snapshot = cninfo_calibration_snapshot(
        transported,
        as_of=PUBLISHED - timedelta(seconds=1),
    )

    assert snapshot.records == ()
    assert any("after calibration as_of" in item for item in snapshot.limitations)


class _HttpResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        url: str,
        content_type: str = "application/json",
    ) -> None:
        self._payload = payload
        self._url = url
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(payload)),
        }

    def __enter__(self) -> "_HttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, size: int = -1) -> bytes:
        return self._payload if size < 0 else self._payload[:size]

    def geturl(self) -> str:
        return self._url


def test_cninfo_http_client_maps_current_public_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_form: dict[str, list[str]] = {}

    def _urlopen(request: Any, **kwargs: Any) -> _HttpResponse:
        del kwargs
        if request.full_url.endswith("szse_stock.json"):
            payload = {"stockList": [{"code": "600000", "orgId": "gssh0600000"}]}
            return _HttpResponse(json.dumps(payload).encode(), url=request.full_url)
        if request.full_url == cninfo_direct.CNINFO_QUERY_URL:
            captured_form.update(parse_qs(request.data.decode()))
            payload = {
                "totalAnnouncement": 1,
                "totalpages": 1,
                "announcements": [_announcement()],
            }
            return _HttpResponse(json.dumps(payload).encode(), url=request.full_url)
        return _HttpResponse(
            PDF,
            url=request.full_url,
            content_type="application/pdf",
        )

    monkeypatch.setattr(cninfo_direct, "urlopen", _urlopen)
    client = CnInfoHttpClient(
        max_attempts=1,
        min_interval_seconds=0.2,
        sleeper=lambda _seconds: None,
        timer=lambda: 1.0,
    )

    result = client.search(
        "600000",
        start_date="2026-06-01",
        end_date="2026-06-20",
    )
    download = client.download_artifact(
        "https://static.cninfo.com.cn/finalpage/2026-06-19/1222207866.pdf"
    )

    assert result.total_announcements == 1
    assert captured_form["stock"] == ["600000,gssh0600000"]
    assert captured_form["seDate"] == ["2026-06-01~2026-06-20"]
    assert download.status is ProviderArtifactStatus.CAPTURED
    assert download.content == PDF


def test_cninfo_http_client_rejects_nonofficial_artifact_url() -> None:
    client = CnInfoHttpClient()

    with pytest.raises(ValueError, match="approved official scope"):
        client.download_artifact("https://example.test/finalpage/document.pdf")
