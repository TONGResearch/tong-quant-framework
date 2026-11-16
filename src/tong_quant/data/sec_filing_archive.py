"""Read explicitly captured older SEC pages without rewriting recent-catalog receipts."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.sec_filing_page import (
    DATASET,
    LIMITATIONS,
    SECFilingPageAdapter,
    page_subject,
)
from tong_quant.data.providers.sec_submissions import MAX_BYTES, PROVIDER, SECSubmissionsCapture
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    SEC_FILING_ARCHIVE_VERSION,
    SEC_FILING_PAGE_LEGACY_VERSION,
    SEC_FILING_PAGE_VERSION,
    SEC_SUBMISSIONS_VERSION,
)

_CATALOG_STATUSES = {"observed_metadata_unqualified", "partial_metadata", "insufficient_metadata"}


def _parameters(catalog: dict[str, Any], descriptor: dict[str, Any]) -> dict[str, str]:
    selected = next(row for row in catalog["captures"]
                    if row["evidence_id"] == catalog["selected_evidence_id"])
    captured = selected["available_at"]
    if isinstance(captured, str):
        captured = datetime.fromisoformat(captured)
    require_timezone(captured, "SEC parent timestamp")
    return {"parent_evidence_id": selected["evidence_id"],
        "parent_raw_data_hash": selected["raw_data_hash"],
        "parent_available_at": captured.astimezone(UTC).isoformat(),
        "filing_count": str(descriptor["filingCount"]), "filing_from": descriptor["filingFrom"],
        "filing_to": descriptor["filingTo"]}


def build_sec_page_request(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                           cik: str, page: str, *, as_of: datetime) -> ProviderDatasetRequest:
    subject = page_subject(cik, page)
    catalog = read_sec_filing_inputs(store, artifacts, cik, as_of=as_of)
    if catalog["source_bound"] is not True or catalog["status"] not in _CATALOG_STATUSES:
        raise ValueError("SEC page capture requires a verified usable parent catalog")
    descriptors = [row for row in catalog["older_pages"] if row["name"] == page]
    if len(descriptors) != 1:
        raise ValueError("SEC page must be uniquely referenced by the retained parent")
    return ProviderDatasetRequest(DATASET, Market.US, subject, as_of,
                                  _parameters(catalog, descriptors[0]))


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    version = envelope["model_version"]
    if (version not in {SEC_FILING_PAGE_VERSION, SEC_FILING_PAGE_LEGACY_VERSION}
            or envelope["metadata_version"] != SEC_SUBMISSIONS_VERSION):
        raise ValueError("unsupported SEC page or metadata version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    capture = SECSubmissionsCapture(envelope["decoded_payload"], envelope["error_code"])
    return SECFilingPageAdapter(download=lambda _: capture, clock=lambda: captured,
                                model_version=version).fetch(request)


def _page(store: SQLiteStore, artifacts: FileSystemArtifactStore, catalog: dict[str, Any],
          descriptor: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    name = descriptor["name"]
    output: dict[str, Any] = {"name": name, "status": "missing", "use_status": "MISSING",
        "filings": [], "usable": False, "source_bound": False, "captures": []}
    records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
        market=Market.US, subject=page_subject(catalog["subject"], name), as_of=as_of)
    ordered = sorted(records, key=lambda row: (row.available_at.astimezone(UTC), row.evidence_id))
    output["captures"] = [{"evidence_id": row.evidence_id, "raw_data_hash": row.raw_data_hash,
        "available_at": row.available_at, "status": row.payload.get("status")} for row in ordered]
    if ordered:
        newest = ordered[-1].available_at.astimezone(UTC)
        selected = [row for row in ordered if row.available_at.astimezone(UTC) == newest]
        output.update(status="rejected_or_ambiguous", use_status="REJECTED_OR_AMBIGUOUS")
        if len(selected) == 1:
            record = selected[0]
            try:
                envelope = verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                    max_bytes=MAX_BYTES + 4096, rebuild=_rebuild)
                output.update(record.payload)
                output.update(source_bound=True, selected_evidence_id=record.evidence_id,
                    use_status="SOURCE_UNUSABLE")
                if envelope["parameters"] != _parameters(catalog, descriptor):
                    output["use_status"] = "PARENT_MISMATCH"
                elif output["descriptor_consistent"] is not True:
                    output["use_status"] = "DESCRIPTOR_MISMATCH"
                elif output["status"] in _CATALOG_STATUSES:
                    output.update(usable=True, use_status="OBSERVED_UNQUALIFIED")
            except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                pass
    return output


def read_sec_filing_archive_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                                   cik: str, *, as_of: datetime) -> dict[str, Any]:
    require_timezone(as_of, "SEC archive read cutoff")
    with store.read_snapshot():
        catalog = read_sec_filing_inputs(store, artifacts, cik, as_of=as_of)
        valid = catalog["source_bound"] is True and catalog["status"] in _CATALOG_STATUSES
        output = {**catalog, "model_version": SEC_FILING_ARCHIVE_VERSION,
            "recent_catalog_input_hash": catalog["input_hash"], "pages": [],
            "archive_coverage_gaps": [], "limitations": (*catalog["limitations"], *LIMITATIONS)}
        output.pop("input_hash")
        if valid:
            merged = [{**row, "archive_reference_source": {
                "evidence_id": catalog["selected_evidence_id"], "page": "recent"}}
                for row in catalog["filings"]]
            for index, descriptor in enumerate(catalog["older_pages"]):
                page = (_page(store, artifacts, catalog, descriptor, as_of) if index < 16 else {
                    "name": descriptor["name"], "status": "not_read_limit",
                    "use_status": "PAGE_LIMIT", "usable": False, "filings": [], "captures": []})
                if len(merged) + len(page["filings"]) > 50000:
                    page.update(usable=False, use_status="ROW_LIMIT")
                if page["usable"]:
                    merged.extend({**row, "archive_reference_source": {
                        "evidence_id": page["selected_evidence_id"], "page": descriptor["name"]}}
                        for row in page["filings"])
                else:
                    output["archive_coverage_gaps"].append({"name": descriptor["name"],
                        "status": page["use_status"], "filing_from": descriptor["filingFrom"],
                        "filing_to": descriptor["filingTo"]})
                output["pages"].append({key: value for key, value in page.items()
                                        if key != "filings"})
            # Cross-page duplicates stay ambiguous at the existing reference matcher.
            output["filings"] = merged
            incomplete = output["archive_coverage_gaps"] or any(
                row["status"] != "OBSERVED_METADATA_UNQUALIFIED" for row in merged)
            output["status"] = "partial_metadata" if incomplete else "observed_metadata_unqualified"
        else:
            output["filings"] = []
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
