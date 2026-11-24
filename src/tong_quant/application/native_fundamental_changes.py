"""Compare retained provider records, not verified business performance or accounting."""

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.native_financial_inputs import read_native_financial_research_input
from tong_quant.data.providers.yahoo_fundamentals import NATIVE_METRICS
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import NATIVE_FUNDAMENTAL_CHANGE_VERSION

_FIELDS = ("period_end", "period_start", "period_type", "currency", "value", "unit",
           "accounting_scope", "published_at", "issuer_revision", "status")
_OBSERVED = {"observed_unqualified", "partial_unqualified"}


def _read(store: SQLiteStore, artifacts: FileSystemArtifactStore, subject: str, market: Market,
          cutoff: datetime, maximum_age: int) -> tuple[dict[str, Any], dict[str, Any]]:
    bound = read_native_financial_research_input(store, artifacts, subject, market,
                                               as_of=cutoff, sector_profile="unknown")
    bound.validate_context(symbol=subject, market=market, as_of=cutoff)
    document = bound.document()
    selected = [row for row in document["captures"]
                if row["evidence_id"] == document.get("selected_evidence_id")]
    if len(selected) > 1 or (document["source_bound"] and len(selected) != 1):
        raise ValueError("native change selected capture mismatch")
    capture = selected[0] if selected else None
    age = (cutoff - datetime.fromisoformat(capture["available_at"]).astimezone(UTC)
           ).total_seconds() if capture else None
    if age is not None and age < 0:
        raise ValueError("native change contains future capture")
    freshness = "UNASSESSED" if age is None else "WITHIN_LIMIT" if age <= maximum_age else "STALE"
    inspected = document["source_bound"] and document["status"] in (
        _OBSERVED | {"no_observations", "insufficient_native_data"})
    summary = {"as_of": cutoff, "status": document["status"],
        "native_input_hash": document["input_hash"], "source_bound": document["source_bound"],
        "selected_evidence_id": document.get("selected_evidence_id"),
        "raw_data_hash": capture["raw_data_hash"] if capture else None,
        "capture_available_at": capture["available_at"] if capture else None,
        "capture_age_seconds": age, "maximum_capture_age_seconds": maximum_age,
        "capture_freshness": freshness, "observation_inventory_evaluated": inspected,
        "retained_observation_count": len(document["observations"]) if inspected else None,
        "period_age_days": document.get("period_age_days"),
        "missing_metrics": document["missing_metrics"],
        "reporting_currencies": document["reporting_currencies"],
        "latest": {metric: {name: document["latest"].get(metric, {}).get(name)
                            for name in _FIELDS} for metric in NATIVE_METRICS}}
    return document, summary


def _rows(document: dict[str, Any]) -> Counter[str]:
    # Capture time and row order are provenance, not changed native financial content.
    return Counter(financial_input_json({"native_metric": row["native_metric"],
        **{name: row.get(name) for name in _FIELDS}}) for row in document["observations"])


def read_native_fundamental_change_digest(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, subject: str, market: Market,
    *, previous_as_of: datetime, as_of: datetime, maximum_capture_age_seconds: int,
) -> dict[str, Any]:
    """Reconstruct source-bound receipts together; never accept caller-supplied JSON."""
    require_timezone(previous_as_of, "previous native change cutoff")
    require_timezone(as_of, "current native change cutoff")
    try:
        start, end = previous_as_of.astimezone(UTC), as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("native change cutoff outside UTC bounds") from None
    if start >= end:
        raise ValueError("native change cutoffs must increase in actual UTC")
    if type(maximum_capture_age_seconds) is not int or maximum_capture_age_seconds <= 0:
        raise ValueError("native change requires a positive integer capture-age limit")
    if type(market) is not Market or not store.read_only:
        raise ValueError("native change requires a typed market and read-only existing store")
    validate_yahoo_equity_subject(market, subject)
    with store.read_snapshot():
        old, before = _read(store, artifacts, subject, market, start, maximum_capture_age_seconds)
        new, after = _read(store, artifacts, subject, market, end, maximum_capture_age_seconds)
    reasons = []
    for name, frame in (("previous", before), ("current", after)):
        if not frame["source_bound"] or frame["status"] not in _OBSERVED:
            reasons.append(f"{name}_native_inputs_unavailable:{frame['status']}")
        if frame["capture_freshness"] != "WITHIN_LIMIT":
            reasons.append(f"{name}_native_capture_not_within_configured_limit")
    changes = []
    for metric in NATIVE_METRICS:
        left, right = before["latest"][metric], after["latest"][metric]
        blockers = list(reasons)
        for name, row in (("previous", left), ("current", right)):
            if row["status"] != "OBSERVED_UNQUALIFIED":
                blockers.append(f"{name}_native_metric_unavailable:{row['status'] or 'MISSING'}")
        status = "NOT_COMPARABLE"
        if not blockers:
            if any(left[name] != right[name] for name in (
                "period_type", "currency", "unit", "accounting_scope", "period_start")):
                status = "INCOMPATIBLE_NATIVE_LABELS"
            elif left["period_end"] != right["period_end"]:
                status = ("PERIOD_LABEL_ADVANCED" if right["period_end"] > left["period_end"]
                          else "PERIOD_LABEL_REGRESSED")
            elif Decimal(left["value"]) != Decimal(right["value"]):
                status = "SAME_PERIOD_NATIVE_VALUE_CHANGED"
            elif left["value"] != right["value"]:
                status = "SAME_PERIOD_NATIVE_REPRESENTATION_CHANGED"
            else:
                status = "SAME_PERIOD_NATIVE_VALUE_IDENTICAL"
        changes.append({"native_metric": metric, "comparison_status": status,
            "blocking_reasons": blockers, "issuer_revision_verified": False,
            "accounting_comparability_verified": False})
    inspected = not reasons
    old_rows, new_rows = (_rows(old), _rows(new)) if inspected else (Counter(), Counter())
    output = {"model_version": NATIVE_FUNDAMENTAL_CHANGE_VERSION, "subject": subject,
        "market": market.value, "snapshot_scope": "single_read_only_database_snapshot",
        "previous": before, "current": after, "blocking_reasons": reasons,
        "comparison_status": ("NOT_COMPARABLE" if reasons else
            "RETAINED_NATIVE_CONTENT_IDENTICAL" if old_rows == new_rows else
            "RETAINED_NATIVE_CONTENT_DIFFERENT"),
        "source_series_comparison_evaluated": inspected,
        "source_row_addition_count": sum((new_rows - old_rows).values()) if inspected else None,
        "source_row_removal_count": sum((old_rows - new_rows).values()) if inspected else None,
        "same_selected_capture": (before["selected_evidence_id"] == after["selected_evidence_id"]
                                  if before["selected_evidence_id"] is not None else None),
        "metric_comparisons": changes, "fundamental_assessment": "NOT_ASSESSED",
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "research_only": True, "source_qualified": False, "pit_qualified": False,
        "accounting_definitions_admitted": False, "publication_dates_verified": False,
        "issuer_revision_history_verified": False, "financial_scoring_authorized": False,
        "investment_scoring_authorized": False, "validation_authorized": False,
        "historical_replay_eligible": False, "holding_management_authorized": False,
        "execution_authorized": False, "research_report_created": False,
        "limitations": [
            "source_bound_means_retained_content_verified_not_independent_source_quality",
            "capture_age_is_not_filing_age_publication_time_or_approved_production_freshness",
            "native_record_changes_are_not_business_growth_or_verified_issuer_restatements",
            "identical_native_records_do_not_mean_business_unchanged_or_holding_safe",
            "matching_annual_labels_do_not_verify_accounting_scope_units_or_flow_periods",
            "no_arithmetic_growth_returns_valuation_scores_or_trade_instructions"]}
    reject_sensitive_structure(output)
    return {**output, "digest_hash": sha256(financial_input_json(output).encode()).hexdigest()}
