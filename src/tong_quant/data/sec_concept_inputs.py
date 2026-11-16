"""Retained XBRL observations plus same-cutoff filing-reference diagnostics."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.sec_concept import (
    DATASET,
    LIMITATIONS,
    SECConceptAdapter,
    concept_subject,
)
from tong_quant.data.providers.sec_submissions import MAX_BYTES, PROVIDER, SECSubmissionsCapture
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.sec_filing_archive import read_sec_filing_archive_inputs
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_CONCEPT_VERSION


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    if envelope["model_version"] != SEC_CONCEPT_VERSION:
        raise ValueError("unsupported SEC concept normalization version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    capture = SECSubmissionsCapture(envelope["decoded_payload"], envelope["error_code"])
    return SECConceptAdapter(download=lambda _: capture, clock=lambda: captured).fetch(request)


def _reference(row: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"row_id": row["row_id"], "row_index": row["row_index"],
        "unit": row["unit"], "status": "NATIVE_ROW_UNUSABLE", "accession": None,
        "filing_report_date": None, "period_relation": "UNKNOWN",
        "independent_numeric_corroboration": False, "accounting_definition_qualified": False}
    if row["status"] != "OBSERVED_NATIVE_UNQUALIFIED":
        return result
    native = row["native"]
    result["accession"] = native["accn"]
    if (catalog["source_bound"] is not True or catalog["status"] not in {
        "observed_metadata_unqualified", "partial_metadata", "insufficient_metadata",
    }):
        result["status"] = "CATALOG_UNAVAILABLE"
        return result
    if any(gap["filing_from"] <= native["filed"] <= gap["filing_to"]
           for gap in catalog.get("archive_coverage_gaps", ())):
        result["status"] = "ARCHIVE_PAGE_UNAVAILABLE"
        return result
    matching = [entry for entry in catalog["filings"]
                if entry["accessionNumber"] == native["accn"]]
    if not matching:
        result["status"] = "FILING_REFERENCE_MISSING"
    elif len(matching) != 1:
        result["status"] = "AMBIGUOUS_FILING_REFERENCE"
    else:
        entry = matching[0]
        if entry["status"] != "OBSERVED_METADATA_UNQUALIFIED":
            result["status"] = "FILING_METADATA_UNUSABLE"
        elif entry["form"] != native["form"] or entry["filingDate"] != native["filed"]:
            result["status"] = "FILING_METADATA_CONFLICT"
        else:
            periodic = entry["form"].removesuffix("/A") in {"10-K", "10-Q", "20-F", "40-F"}
            period = entry["reportDate"] if periodic else None
            result.update(status="METADATA_REFERENCE_MATCH", filing_report_date=period,
                period_relation=("SAME_END_LABEL" if period == row["period_end"]
                    else "COMPARATIVE_OR_OTHER_PERIOD" if period else "UNKNOWN"))
            if "archive_reference_source" in entry:
                result["reference_source"] = entry["archive_reference_source"]
    return result


def read_sec_concept_inputs(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str, taxonomy: str, tag: str,
    *, as_of: datetime, include_older_pages: bool = False,
) -> dict[str, Any]:
    require_timezone(as_of, "SEC concept read cutoff")
    if type(include_older_pages) is not bool:
        raise ValueError("older-page research requires an explicit boolean opt-in")
    subject = concept_subject(cik, taxonomy, tag)
    output: dict[str, Any] = {"subject": subject, "cik": cik, "taxonomy": taxonomy, "tag": tag,
        "market": Market.US.value, "as_of": as_of.astimezone(UTC), "status": "missing",
        "source_bound": False, "captures": [], "observations": [], "units": [],
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "financial_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "issuer_to_instrument_verified": False,
        "accounting_definition_qualified": False, "historical_continuity_verified": False,
        "limitations": LIMITATIONS, "model_version": SEC_CONCEPT_VERSION}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
            market=Market.US, subject=subject, as_of=as_of)
        ordered = sorted(records, key=lambda item: (item.available_at.astimezone(UTC),
                                                    item.evidence_id))
        output["captures"] = [{"evidence_id": item.evidence_id, "raw_data_hash": item.raw_data_hash,
            "available_at": item.available_at, "status": item.payload.get("status")}
            for item in ordered]
        if ordered:
            newest = ordered[-1].available_at.astimezone(UTC)
            selected = [item for item in ordered if item.available_at.astimezone(UTC) == newest]
            output["status"] = "rejected_or_ambiguous"
            if len(selected) == 1:
                record = selected[0]
                try:
                    verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                                             max_bytes=MAX_BYTES + 4096, rebuild=_rebuild)
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id)
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    pass
        catalog = (read_sec_filing_archive_inputs(store, artifacts, cik, as_of=as_of)
            if include_older_pages else read_sec_filing_inputs(store, artifacts, cik, as_of=as_of))
        if include_older_pages:
            output["older_pages_included"] = True
            output["archive_pages"] = catalog["pages"]
            output["archive_coverage_gaps"] = catalog["archive_coverage_gaps"]
        output["filing_catalog"] = {key: catalog[key] for key in (
            "input_hash", "status", "source_bound", "captures", "limitations", "model_version")}
        output["filing_references"] = [_reference(row, catalog) for row in output["observations"]]
        output["metadata_reference_match_count"] = sum(
            row["status"] == "METADATA_REFERENCE_MATCH" for row in output["filing_references"])
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
