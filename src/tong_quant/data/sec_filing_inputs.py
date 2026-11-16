"""Reconstruct retained SEC metadata at retrieval-time availability, without fallback."""

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.sec_submissions import (
    DATASET,
    LEGACY_VERSION,
    LIMITATIONS,
    MAX_BYTES,
    PROVIDER,
    SECSubmissionsAdapter,
    SECSubmissionsCapture,
    validate_request,
)
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_ISSUER_CLAIMS_VERSION, SEC_SUBMISSIONS_VERSION


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    version = envelope["model_version"]
    if version not in {SEC_SUBMISSIONS_VERSION, LEGACY_VERSION}:
        raise ValueError("unsupported SEC normalization version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    capture = SECSubmissionsCapture(envelope["decoded_payload"], envelope["error_code"])
    return SECSubmissionsAdapter(download=lambda _: capture, clock=lambda: captured,
                                 model_version=version).fetch(request)


def read_sec_filing_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str,
                           *, as_of: datetime) -> dict[str, Any]:
    require_timezone(as_of, "SEC metadata read cutoff")
    validate_request(ProviderDatasetRequest(DATASET, Market.US, cik, as_of))
    output: dict[str, Any] = {"subject": cik, "market": Market.US.value,
        "as_of": as_of.astimezone(UTC), "status": "missing", "source_bound": False,
        "captures": [], "filings": [], "older_pages": [], "trust_ceiling": "LOW",
        "availability_precision": "retrieval_time", "freshness": "UNASSESSED",
        "issuer_to_instrument_verified": False, "historical_continuity_verified": False,
        "published_at_known": False, "financial_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "limitations": LIMITATIONS,
        "model_version": SEC_SUBMISSIONS_VERSION}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
            market=Market.US, subject=cik, as_of=as_of)
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
                    envelope = verify_retained_snapshot(
                        store, artifacts, record, as_of=as_of,
                        max_bytes=MAX_BYTES + 4096, rebuild=_rebuild)
                    output.update(record.payload)
                    output.update(source_bound=True, selected_evidence_id=record.evidence_id,
                                  model_version=envelope["model_version"])
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    pass
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}


def _declared_strings(payload: dict[str, Any], field: str) -> tuple[str, list[str] | None]:
    if field not in payload:
        return "MISSING", None
    values = payload[field]
    if values is None:
        return "NULL", None
    pattern = r"[A-Za-z0-9.-]+" if field == "tickers" else r"[A-Za-z0-9 .-]+"
    if (not isinstance(values, list) or len(values) > 256
            or any(not isinstance(value, str) or not 1 <= len(value) <= 64
                   or re.fullmatch(pattern, value, flags=re.ASCII) is None
                   or value != value.strip() for value in values)):
        return "INVALID_OR_UNSUPPORTED", None
    if not values:
        return "EMPTY", []
    if len(set(values)) != len(values):
        return "DUPLICATE", values
    return "OBSERVED_UNQUALIFIED", values


def read_sec_issuer_claims(store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str,
                          *, symbol: str, as_of: datetime) -> dict[str, Any]:
    """Compare exact retained issuer declarations, not historical listing or share-class truth."""
    require_timezone(as_of, "SEC issuer-claims cutoff")
    validate_yahoo_equity_subject(Market.US, symbol)
    output: dict[str, Any] = {
        "model_version": SEC_ISSUER_CLAIMS_VERSION, "subject": cik, "requested_symbol": symbol,
        "market": Market.US.value, "as_of": as_of.astimezone(UTC),
        "status": "CATALOG_UNAVAILABLE", "source_bound": False,
        "catalog_input_hash": None, "catalog_status": None, "catalog_evidence_id": None,
        "catalog_raw_data_hash": None, "catalog_model_version": None,
        "capture_available_at": None, "issuer_name": None,
        "ticker_field_status": "NOT_READ", "exchange_field_status": "NOT_READ",
        "declared_tickers": None, "declared_exchanges": None,
        "exact_ticker_match_indices": [], "exchange_association_status": "NOT_INFERRED",
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "issuer_to_instrument_verified": False,
        "historical_identity_verified": False, "share_class_verified": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "warnings": [],
        "limitations": (
            "A captured SEC ticker declaration is issuer-level, retrieval-time evidence only",
            "Exact text agreement does not establish share class, listing status or price truth",
            "No case/punctuation aliases, exchange-array pairing or name-based joins are inferred",
            "Empty or absent declarations do not prove delisting or historical ticker absence",
            "Matching SEC statements are same-origin, not independent provider corroboration",
            "No source, sector, score, validation, replay or trading permission is granted",
        ),
    }
    with store.read_snapshot():
        catalog = read_sec_filing_inputs(store, artifacts, cik, as_of=as_of)
        output.update(catalog_input_hash=catalog["input_hash"], catalog_status=catalog["status"])
        if catalog["source_bound"] and catalog["status"] in {
            "observed_metadata_unqualified", "partial_metadata", "insufficient_metadata",
        }:
            try:
                records = MarketDataService(store).provider_evidence(provider=PROVIDER,
                    dataset=DATASET, market=Market.US, subject=cik, as_of=as_of)
                matches = [record for record in records
                           if record.evidence_id == catalog["selected_evidence_id"]]
                if len(matches) != 1:
                    raise ValueError("unique retained SEC parent is required")
                record = matches[0]
                envelope = verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                    max_bytes=MAX_BYTES + 4096, rebuild=_rebuild)
                payload = envelope["decoded_payload"]
                if not isinstance(payload, dict):
                    raise ValueError("retained issuer payload is required")
                ticker_state, tickers = _declared_strings(payload, "tickers")
                exchange_state, exchanges = _declared_strings(payload, "exchanges")
                name = payload.get("name")
                name = (name if isinstance(name, str) and 0 < len(name) <= 512
                        and all(char.isprintable() for char in name) else None)
                indices = [index for index, value in enumerate(tickers or []) if value == symbol]
                status = {"MISSING": "TICKER_DECLARATION_MISSING",
                    "NULL": "TICKER_DECLARATION_NULL", "EMPTY": "NO_DECLARED_TICKERS",
                    "INVALID_OR_UNSUPPORTED": "INVALID_TICKER_DECLARATIONS",
                    "DUPLICATE": "AMBIGUOUS_TICKER_DECLARATIONS"}.get(ticker_state)
                if status is None:
                    status = "TICKER_DECLARED_UNVERIFIED" if indices else "TICKER_NOT_DECLARED"
                output.update(status=status, source_bound=True, issuer_name=name,
                    catalog_evidence_id=record.evidence_id,
                    catalog_raw_data_hash=record.raw_data_hash,
                    catalog_model_version=envelope["model_version"],
                    capture_available_at=record.available_at.astimezone(UTC),
                    ticker_field_status=ticker_state, declared_tickers=tickers,
                    exchange_field_status=exchange_state, declared_exchanges=exchanges,
                    exact_ticker_match_indices=indices)
                if exchange_state != "OBSERVED_UNQUALIFIED":
                    output["warnings"].append("Exchange declarations are missing or unqualified")
                if name is None:
                    output["warnings"].append("Issuer name is missing or unsupported")
            except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                output.update(status="REJECTED_OR_AMBIGUOUS", source_bound=False)
                output["warnings"].append("Issuer claims require intact current retained evidence")
    reject_sensitive_structure(output)
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
