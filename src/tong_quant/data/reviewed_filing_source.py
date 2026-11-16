"""Shared retained-CNInfo binding for read-only manual filing annotations."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    ProviderArtifact,
    provider_artifact_id,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone


@dataclass(frozen=True, slots=True)
class ReviewedFilingSource:
    artifact: ProviderArtifact
    registry_model_version: str
    batch_receipt: dict[str, Any]


def bind_reviewed_cninfo_filing(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, *, subject: str,
    filing_artifact_id: str, filing_sha256: str, reviewed_at: datetime, as_of: datetime,
    earliest_publication_date: date | None = None,
) -> ReviewedFilingSource:
    require_timezone(reviewed_at, "filing review time")
    require_timezone(as_of, "filing review cutoff")
    cutoff, reviewed = as_of.astimezone(UTC), reviewed_at.astimezone(UTC)
    if reviewed > cutoff:
        raise ValueError("filing review is not visible at cutoff")
    with store.read_snapshot():
        saved = store.provider_artifact(filing_artifact_id)
        if saved is None:
            raise ValueError("filing review requires a registered filing")
        if saved["content_hash"] != filing_sha256:
            raise ValueError("reviewed filing hash does not match registry")
        content = artifacts.read_content(filing_sha256, "application/pdf",
                                         max_bytes=50 * 1024 * 1024)
        source = ProviderArtifact(
            artifact_id=saved["artifact_id"], provider=saved["provider"], dataset=saved["dataset"],
            market=Market(saved["market"]), subject=saved["subject"],
            source_identity=saved["source_identity"], source_reference=saved["source_reference"],
            content_hash=saved["content_hash"], media_type=saved["media_type"],
            published_at=datetime.fromisoformat(saved["published_at"]),
            retrieved_at=datetime.fromisoformat(saved["first_retrieved_at"]),
            availability_precision=AvailabilityPrecision(saved["availability_precision"]),
            trust_level=DataTrustLevel(saved["trust_level"]), content=content,
        )
        identity = provider_artifact_id(
            provider=source.provider, dataset=source.dataset, market=source.market,
            subject=source.subject, source_identity=source.source_identity,
            source_reference=source.source_reference, content_hash=source.content_hash)
        url = urlsplit(source.source_reference)
        published = source.published_at.astimezone(UTC)
        captured = source.retrieved_at.astimezone(UTC)
        if (source.provider != "cninfo_direct" or source.dataset != CNINFO_DISCLOSURES_DATASET
                or source.market is not Market.CHINA_A or source.subject != subject
                or identity != filing_artifact_id or source.content_hash != filing_sha256
                or source.media_type != "application/pdf" or not content.startswith(b"%PDF")
                or saved["byte_size"] != len(content)
                or saved["storage_key"] != f"sha256/{filing_sha256[:2]}/{filing_sha256}.pdf"
                or url.scheme != "https" or url.netloc != "static.cninfo.com.cn"
                or not url.path.startswith("/finalpage/") or not url.path.lower().endswith(".pdf")
                or url.query or url.fragment or not published <= captured <= reviewed <= cutoff
                or (earliest_publication_date is not None
                    and published.astimezone(ZoneInfo("Asia/Shanghai")).date()
                    < earliest_publication_date)):
            raise ValueError("reviewed filing identity, chronology or bytes rejected")
        batch = store.ingestion_batch(saved["first_batch_id"])
        if (batch is None or batch["provider"] != source.provider
                or batch["dataset"] != source.dataset or batch["status"] != "completed"
                or batch["completed_at"] is None):
            raise ValueError("reviewed filing batch ownership rejected")
        parameters = json.loads(batch["parameters_json"])
        if not isinstance(parameters, dict) or parameters.get("subject") != subject:
            raise ValueError("reviewed filing batch subject rejected")
        started, completed = (datetime.fromisoformat(batch[name])
                              for name in ("started_at", "completed_at"))
        require_timezone(started, "filing batch start")
        require_timezone(completed, "filing batch completion")
        if not started.astimezone(UTC) <= captured <= completed.astimezone(UTC) <= reviewed:
            raise ValueError("reviewed filing batch chronology rejected")
        receipt = {name: batch[name] for name in (
            "batch_id", "provider", "dataset", "status", "started_at", "completed_at",
            "raw_response_hash", "parameters_json")}
    return ReviewedFilingSource(source, saved["model_version"], receipt)
