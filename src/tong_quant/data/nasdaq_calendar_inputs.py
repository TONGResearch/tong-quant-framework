"""Fixed-cutoff original-body reconstruction of explicit Nasdaq calendar declarations."""

import base64
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.nasdaq_calendar import (
    DATASET,
    LIMITATIONS,
    MAX_ENVELOPE_BYTES,
    PROVIDER,
    SOURCE_URL,
    NasdaqCalendarAdapter,
    NasdaqCalendarCapture,
    calendar_subject,
)
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import NASDAQ_CALENDAR_AGE_VERSION, NASDAQ_CALENDAR_VERSION


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    if envelope["model_version"] != NASDAQ_CALENDAR_VERSION:
        raise ValueError("unsupported Nasdaq calendar version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    capture = NasdaqCalendarCapture(base64.b64decode(envelope["document_base64"], validate=True)
        if envelope["document_base64"] is not None else None, envelope["error_code"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    return NasdaqCalendarAdapter(download=lambda _: capture, clock=lambda: captured).fetch(request)


def read_nasdaq_calendar_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                               year: int, *, as_of: datetime,
                               maximum_source_age_seconds: int | None = None) -> dict[str, Any]:
    if maximum_source_age_seconds is not None and (
        type(maximum_source_age_seconds) is not int or maximum_source_age_seconds <= 0
    ):
        raise ValueError("maximum source age must be a positive integer in seconds")
    require_timezone(as_of, "Nasdaq calendar read cutoff")
    subject = calendar_subject(year)
    verified_capture_at = None
    output: dict[str, Any] = {"subject": subject, "market": Market.US.value,
        "exchange": "NASDAQ", "year": year, "as_of": as_of.astimezone(UTC),
        "status": "missing", "source_bound": False, "captures": [], "declarations": [],
        "model_version": NASDAQ_CALENDAR_VERSION, "source_url": SOURCE_URL,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "published_at_known": False,
        "calendar_complete": False, "actual_session_verified": False,
        "canonical_calendar_authorized": False, "scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "limitations": LIMITATIONS}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER,
            dataset=DATASET, market=Market.US, subject=subject, as_of=as_of)
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
                    verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                        max_bytes=MAX_ENVELOPE_BYTES, rebuild=_rebuild)
                    output.update(record.payload)
                    output.update(source_bound=record.payload["document_sha256"] is not None,
                                  selected_evidence_id=record.evidence_id)
                    if output["source_bound"]:
                        verified_capture_at = record.retrieved_at.astimezone(UTC)
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    pass
    if maximum_source_age_seconds is not None:
        _apply_source_age(output, as_of, verified_capture_at, maximum_source_age_seconds)
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}


def _apply_source_age(output: dict[str, Any], as_of: datetime,
                      captured: datetime | None, maximum_age: int) -> None:
    # Compare exact elapsed UTC microseconds, not wall time or rounded seconds.
    age = None
    if captured is not None:
        elapsed = as_of.astimezone(UTC) - captured
        age = (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds
    output.update(freshness_model_version=NASDAQ_CALENDAR_AGE_VERSION,
        maximum_source_age_seconds=maximum_age, source_status=output["status"],
        source_capture_at=captured, source_capture_age_microseconds=age,
        source_capture_age_seconds=None if age is None else age / 1_000_000,
        observed_declarations=list(output["declarations"]), freshness="BLOCKED_INPUT")
    output["declarations"] = []
    if age is not None and age >= 0 and output["source_status"] == (
        "explicit_declarations_unqualified"
    ):
        if age <= maximum_age * 1_000_000:
            output["freshness"] = "WITHIN_CONFIGURED_LIMIT"
            output["declarations"] = list(output["observed_declarations"])
        else:
            output.update(freshness="STALE", status="stale_source_capture")
