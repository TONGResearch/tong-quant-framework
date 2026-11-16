"""Parent-pinned filing bytes and same-origin, same-accession numeric diagnostics."""

import base64
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.sec_body import (
    DATASET,
    LIMITATIONS,
    MAX_ENVELOPE_BYTES,
    SECBodyAdapter,
    SECBodyCapture,
    body_subject,
    validate_request,
)
from tong_quant.data.providers.sec_submissions import PROVIDER
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.sec_concept_inputs import read_sec_concept_inputs
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs
from tong_quant.data.sec_inline_review import DEFAULT_TAGS, review_inline_body
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    SEC_BODY_VERSION,
    SEC_INLINE_EXCLUSION_VERSION,
    SEC_INLINE_REVIEW_VERSION,
)


def build_sec_body_request(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                           cik: str, accession: str, *, as_of: datetime) -> ProviderDatasetRequest:
    subject = body_subject(cik, accession)
    with store.read_snapshot():
        catalog = read_sec_filing_inputs(store, artifacts, cik, as_of=as_of)
        if not catalog["source_bound"] or catalog["status"] not in {
            "observed_metadata_unqualified", "partial_metadata", "insufficient_metadata"}:
            raise ValueError("verified retained SEC catalog is required")
        matches = [row for row in catalog["filings"] if row["accessionNumber"] == accession]
        if len(matches) != 1 or matches[0]["status"] != "OBSERVED_METADATA_UNQUALIFIED":
            raise ValueError("unique usable retained accession is required; no guessed URL")
        parent = next(row for row in catalog["captures"]
                      if row["evidence_id"] == catalog["selected_evidence_id"])
        filing = matches[0]
        request = ProviderDatasetRequest(DATASET, Market.US, subject, as_of, {
            "parent_evidence_id": parent["evidence_id"],
            "parent_raw_data_hash": parent["raw_data_hash"],
            "parent_available_at": parent["available_at"].astimezone(UTC).isoformat(),
            "primary_document": filing["primaryDocument"], "form": filing["form"],
            "filed": filing["filingDate"], "report_date": filing["reportDate"]})
        validate_request(request)
        return request


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    if envelope["model_version"] != SEC_BODY_VERSION:
        raise ValueError("unsupported SEC body version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    content = (base64.b64decode(envelope["body_base64"], validate=True)
               if envelope["body_base64"] is not None else None)
    capture = SECBodyCapture(content, envelope["error_code"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    return SECBodyAdapter(download=lambda _: capture, clock=lambda: captured).fetch(request)


def _compare(concept: dict[str, Any], facts: list[dict[str, Any]],
             request: ProviderDatasetRequest) -> list[dict[str, Any]]:
    accession = request.subject.split(":")[1]
    results = []
    tag_facts = [fact for fact in facts if fact["tag"] == concept["tag"]]
    for row in concept["observations"]:
        native = row.get("native")
        if not isinstance(native, dict) or native.get("accn") != accession:
            continue
        result: dict[str, Any] = {"concept_row_id": row["row_id"], "tag": concept["tag"],
            "period_start": row["period_start"], "period_end": row["period_end"],
            "unit": row["unit"], "concept_value": row["value"],
            "status": "UNUSABLE_CONCEPT_OR_METADATA", "body_occurrences": [],
            "unsupported_tag_fact_count": sum(fact["status"] != "OBSERVED_UNQUALIFIED"
                                               for fact in tag_facts),
            "complete_numeric_validation": False, "independent_numeric_corroboration": False}
        results.append(result)
        if (concept["source_bound"] is not True or row["status"] != "OBSERVED_NATIVE_UNQUALIFIED"
                or native.get("form") != request.parameters["form"]
                or native.get("filed") != request.parameters["filed"]):
            continue
        matching = [fact for fact in tag_facts if (fact["period_start"], fact["period_end"],
            fact["unit"]) == (row["period_start"], row["period_end"], row["unit"])]
        result["body_occurrences"] = matching
        if not matching:
            result["status"] = "NO_SUPPORTED_BODY_CONTEXT"
        elif any(fact["status"] != "OBSERVED_UNQUALIFIED" for fact in matching):
            result["status"] = "UNSUPPORTED_MATCHING_BODY_OCCURRENCE"
        elif any(Decimal(fact["value"]) != Decimal(row["value"]) for fact in matching):
            result["status"] = "NUMERIC_CONFLICT"
        else:
            result["status"] = "SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED"
    return results or [{"tag": concept["tag"], "status": "NO_VISIBLE_TARGET_ACCESSION_FACTS",
        "body_occurrences": [], "complete_numeric_validation": False,
        "independent_numeric_corroboration": False}]


def read_sec_body_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                         cik: str, accession: str, *, as_of: datetime,
                         tags: tuple[str, ...] = DEFAULT_TAGS,
                         explain_exclusions: bool = False) -> dict[str, Any]:
    require_timezone(as_of, "SEC body cutoff")
    # Validate tag scope even when there is no retained body.
    review_inline_body(b"<html/>", cik, as_of=as_of, tags=tags,
                       explain_exclusions=explain_exclusions)
    subject = body_subject(cik, accession)
    output: dict[str, Any] = {"subject": subject, "as_of": as_of.astimezone(UTC),
        "status": "missing", "source_bound": False, "captures": [], "body_review": None,
        "comparisons": [], "concept_inputs": [], "warnings": [], "limitations": LIMITATIONS,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "financial_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "issuer_to_instrument_verified": False, "independent_numeric_corroboration": False,
        "model_version": SEC_BODY_VERSION, "review_version": SEC_INLINE_REVIEW_VERSION}
    if explain_exclusions:
        output["exclusion_review_version"] = SEC_INLINE_EXCLUSION_VERSION
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
            market=Market.US, subject=subject, as_of=as_of)
        ordered = sorted(records, key=lambda row: (
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
                    request = build_sec_body_request(store, artifacts, cik, accession, as_of=as_of)
                    envelope = verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                        max_bytes=MAX_ENVELOPE_BYTES, rebuild=_rebuild)
                    if envelope["parameters"] != request.parameters:
                        raise ValueError("changed parent requires explicit body recapture")
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id)
                    if envelope["body_base64"] is not None:
                        content = base64.b64decode(envelope["body_base64"], validate=True)
                        review = review_inline_body(content, cik, as_of=as_of, tags=tags,
                                                   explain_exclusions=explain_exclusions)
                        output["body_review"] = review
                        for tag in tags:
                            concept = read_sec_concept_inputs(store, artifacts, cik, "us-gaap", tag,
                                                              as_of=as_of)
                            output["concept_inputs"].append({key: concept[key] for key in (
                                "tag", "input_hash", "status", "source_bound", "captures")})
                            output["comparisons"].extend(
                                _compare(concept, review["facts"], request))
                        output["warnings"].extend(review["warnings"])
                        output["warnings"].append(
                            "Only supported occurrences compared; excluded facts stay visible. "
                            "Same origin, not independent corroboration or full accounting review.")
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    output.update(status="rejected_or_ambiguous", source_bound=False,
                                  body_review=None, comparisons=[], concept_inputs=[])
                    output["warnings"].append("Body/parent/artifact/batch integrity rejected")
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
