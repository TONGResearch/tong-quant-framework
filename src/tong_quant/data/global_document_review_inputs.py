"""Source-pinned overseas transcription preparation and deterministic read side."""

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
from tong_quant.data.providers.global_document_reviews import (
    DATASET,
    LIMITATIONS,
    MAX_REVIEW_BYTES,
    PROVIDER,
    GlobalDocumentReview,
    GlobalDocumentReviewAdapter,
    parse_global_document_review,
)
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_DOCUMENT_REVIEW_VERSION


def _parse_envelope(envelope: dict[str, Any]) -> GlobalDocumentReview:
    if envelope["model_version"] != GLOBAL_DOCUMENT_REVIEW_VERSION:
        raise ValueError("unsupported overseas review version")
    values = envelope["review"]
    return parse_global_document_review({"review": {key: value for key, value in values.items()
        if key != "rows"}, "rows": values["rows"]})


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    review = _parse_envelope(envelope)
    recorded = datetime.fromisoformat(envelope["recorded_at"])
    return GlobalDocumentReviewAdapter(review, recorded).fetch(ProviderDatasetRequest(
        DATASET, review.market, review.subject, recorded))


def prepare_global_document_review(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    review: GlobalDocumentReview, *, as_of: datetime) -> ProviderEvidenceBatch:
    require_timezone(as_of, "overseas review cutoff")
    review.__post_init__()
    with store.read_snapshot():
        source = read_global_document_inputs(store, artifacts, review.market, review.subject,
                                             review.document_url, as_of=as_of)
        if (source["source_bound"] is not True or source["status"] != "captured_pdf_unqualified"
                or source["selected_evidence_id"] != review.source_evidence_id
                or source["document_sha256"] != review.source_document_sha256
                or source["annotations"]["period_end"] != review.report_period_end.isoformat()):
            raise ValueError("manual review requires its exact current retained source")
        parent = next(row for row in source["captures"]
                      if row["evidence_id"] == review.source_evidence_id)
        if (parent["raw_data_hash"] != review.source_envelope_sha256
                or parent["available_at"].astimezone(UTC) != (
                    review.source_available_at.astimezone(UTC))):
            raise ValueError("manual review source hash/availability mismatch")
        return GlobalDocumentReviewAdapter(review, as_of).fetch(ProviderDatasetRequest(
            DATASET, review.market, review.subject, as_of))


def ingest_global_document_review(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    review: GlobalDocumentReview, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IngestionResult:
    recorded = clock()
    prepare_global_document_review(store, artifacts, review, as_of=recorded)
    # A concurrent source recapture may invalidate this review; every read rechecks its pins.
    return ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=clock).ingest(
        GlobalDocumentReviewAdapter(review, recorded), ProviderDatasetRequest(
            DATASET, review.market, review.subject, recorded))


def read_global_document_review_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    market: Market, subject: str, document_url: str, *, as_of: datetime) -> dict[str, Any]:
    require_timezone(as_of, "overseas review read cutoff")
    validate_yahoo_equity_subject(market, subject)
    validate_document_url(market, document_url)
    output: dict[str, Any] = {"market": market.value, "subject": subject,
        "document_url": document_url, "as_of": as_of.astimezone(UTC), "status": "missing",
        "source_bound": False, "captures": [], "observations": [], "limitations": LIMITATIONS,
        "warnings": [],
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "accounting_definition_qualified": False,
        "source_location_verified": False, "canonical_population_authorized": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "independent_review": False, "issuer_to_instrument_verified": False,
        "execution_authorized": False, "model_version": GLOBAL_DOCUMENT_REVIEW_VERSION}
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
                    prepare_global_document_review(store, artifacts, review, as_of=as_of)
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id)
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    output["warnings"].append("review_or_current_source_integrity_rejected")
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
