"""Explicit-document, fixed-cutoff reconstruction without parsing PDF content."""

import base64
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.global_documents import (
    DATASET,
    LIMITATIONS,
    MAX_ENVELOPE_BYTES,
    PROVIDERS,
    DocumentCapture,
    GlobalDocumentAdapter,
    validate_document_url,
)
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_DOCUMENT_VERSION


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    if envelope["model_version"] != GLOBAL_DOCUMENT_VERSION:
        raise ValueError("unsupported primary-document version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    capture = DocumentCapture(base64.b64decode(envelope["document_base64"], validate=True)
        if envelope["document_base64"] is not None else None, envelope["error_code"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    return GlobalDocumentAdapter(request.market, download=lambda _: capture,
                                  clock=lambda: captured).fetch(request)


def read_global_document_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    market: Market, subject: str, document_url: str, *, as_of: datetime) -> dict[str, Any]:
    require_timezone(as_of, "primary-document cutoff")
    validate_yahoo_equity_subject(market, subject)
    validate_document_url(market, document_url)
    output: dict[str, Any] = {"subject": subject, "market": market.value,
        "document_url": document_url, "as_of": as_of.astimezone(UTC), "status": "missing",
        "source_bound": False, "captures": [], "model_version": GLOBAL_DOCUMENT_VERSION,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED",
        "issuer_to_instrument_verified": False, "landing_link_verified": False,
        "published_at_known": False, "numeric_extraction_authorized": False,
        "financial_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False, "limitations": LIMITATIONS}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDERS[market],
            dataset=DATASET, market=market, subject=subject, as_of=as_of)
        matching = []
        for row in records:
            annotations = row.payload.get("annotations")
            if row.source_reference == document_url or (
                isinstance(annotations, dict) and annotations.get("document_url") == document_url
            ):
                matching.append(row)
        ordered = sorted(matching,
            key=lambda row: (row.available_at.astimezone(UTC), row.evidence_id))
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
                    verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                        max_bytes=MAX_ENVELOPE_BYTES, rebuild=_rebuild)
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id)
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    pass
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
