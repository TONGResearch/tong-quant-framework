"""Source-pinned original percentages with independent, fail-closed retained reads."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import IngestionResult
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.global_ratio_reviews import (
    AUTHORITY_FLAGS,
    DATASET,
    LIMITATIONS,
    MAX_REVIEW_BYTES,
    PROVIDER,
    GlobalRatioReview,
    GlobalRatioReviewAdapter,
    parse_global_ratio_review,
)
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_RATIO_REVIEW_VERSION


def _parse_envelope(envelope: dict[str, Any]) -> GlobalRatioReview:
    if envelope["model_version"] != GLOBAL_RATIO_REVIEW_VERSION:
        raise ValueError("unsupported overseas ratio version")
    values = envelope["review"]
    if not isinstance(values, dict):
        raise ValueError("ratio review envelope requires an object")
    return parse_global_ratio_review({"review": {key: value for key, value in values.items()
        if key != "rows"}, "rows": values["rows"]})


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    review = _parse_envelope(envelope)
    recorded = datetime.fromisoformat(envelope["recorded_at"])
    return GlobalRatioReviewAdapter(review, recorded).fetch(ProviderDatasetRequest(
        DATASET, review.market, review.subject, recorded))


def prepare_global_ratio_review(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    review: GlobalRatioReview, *, as_of: datetime) -> ProviderEvidenceBatch:
    require_timezone(as_of, "overseas ratio cutoff")
    review.__post_init__()
    with store.read_snapshot():
        source = read_global_document_inputs(store, artifacts, review.market, review.subject,
                                             review.document_url, as_of=as_of)
        if (source["source_bound"] is not True or source["status"] != "captured_pdf_unqualified"
                or source["selected_evidence_id"] != review.source_evidence_id
                or source["document_sha256"] != review.source_document_sha256
                or source["annotations"]["period_end"] != review.report_period_end.isoformat()):
            raise ValueError("ratio review requires its exact current retained source")
        parent = next(row for row in source["captures"]
                      if row["evidence_id"] == review.source_evidence_id)
        if (parent["raw_data_hash"] != review.source_envelope_sha256
                or parent["available_at"].astimezone(UTC) != (
                    review.source_available_at.astimezone(UTC))):
            raise ValueError("ratio source hash/availability mismatch")
        return GlobalRatioReviewAdapter(review, as_of).fetch(ProviderDatasetRequest(
            DATASET, review.market, review.subject, as_of))


def ingest_global_ratio_review(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    review: GlobalRatioReview, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IngestionResult:
    recorded = clock()
    prepare_global_ratio_review(store, artifacts, review, as_of=recorded)
    # Parent recapture races invalidate later reads, never grant stale-source authority.
    return ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=clock).ingest(
        GlobalRatioReviewAdapter(review, recorded), ProviderDatasetRequest(
            DATASET, review.market, review.subject, recorded))


def read_global_ratio_review_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    market: Market, subject: str, document_url: str, *, as_of: datetime) -> dict[str, Any]:
    require_timezone(as_of, "overseas ratio read cutoff")
    validate_yahoo_equity_subject(market, subject)
    validate_document_url(market, document_url)
    output: dict[str, Any] = {"market": market.value, "subject": subject,
        "document_url": document_url, "as_of": as_of.astimezone(UTC), "status": "missing",
        "source_bound": False, "captures": [], "observations": [], "limitations": LIMITATIONS,
        "warnings": [], "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "model_version": GLOBAL_RATIO_REVIEW_VERSION,
        **{key: False for key in AUTHORITY_FLAGS}}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
            market=market, subject=subject, as_of=as_of)
        matching = []
        for row in records:
            annotations = row.payload.get("review")
            if row.source_reference == document_url or (
                isinstance(annotations, dict) and annotations.get("document_url") == document_url
            ):
                matching.append(row)
        ordered = sorted(matching, key=lambda row: (
            row.available_at.astimezone(UTC), row.evidence_id))
        output["captures"] = [{"evidence_id": row.evidence_id, "raw_data_hash": row.raw_data_hash,
            "available_at": row.available_at, "status": row.payload.get("status")}
            for row in ordered]
        if ordered:
            newest = ordered[-1].available_at.astimezone(UTC)
            selected = [row for row in ordered if row.available_at.astimezone(UTC) == newest]
            output["status"] = "rejected_or_ambiguous"
            if len(selected) == 1:
                record = selected[0]
                try:
                    envelope = verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                        max_bytes=MAX_REVIEW_BYTES + 4096, rebuild=_rebuild)
                    review = _parse_envelope(envelope)
                    prepare_global_ratio_review(store, artifacts, review, as_of=as_of)
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id)
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    output["warnings"].append("ratio_review_or_current_source_integrity_rejected")
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
