"""Explicit native/manual questions and signed-line arithmetic, not admitted accounting."""

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.global_document_reviews import parse_global_document_review
from tong_quant.data.providers.yahoo_fundamentals import NATIVE_METRICS
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    GLOBAL_DOCUMENT_REVIEW_VERSION,
    GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION,
    GLOBAL_MANUAL_ARITHMETIC_VERSION,
    GLOBAL_MANUAL_CHANGE_VERSION,
    GLOBAL_NATIVE_PAIR_VERSION,
)


def parse_native_pairs(values: Sequence[str]) -> tuple[tuple[str, str], ...]:
    if not 1 <= len(values) <= 64:
        raise ValueError("supply 1-64 explicit row_key=native_metric candidates")
    pairs = []
    for value in values:
        parts = value.split("=")
        if (len(parts) != 2 or re.fullmatch(r"[a-z][a-z0-9_]{0,95}", parts[0]) is None
                or parts[1] not in NATIVE_METRICS):
            raise ValueError("candidate requires an exact row_key and supported native metric")
        pairs.append((parts[0], parts[1]))
    if len(set(pairs)) != len(pairs):
        raise ValueError("duplicate candidate pair")
    return tuple(pairs)


def _utc(value: object) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("candidate receipt timestamp missing")
    require_timezone(value, "candidate receipt timestamp")
    return value.astimezone(UTC)


def _receipt_ok(receipt: Mapping[str, Any], *, version: str, subject: str,
                market: Market, as_of: datetime) -> bool:
    body = {key: value for key, value in receipt.items() if key != "input_hash"}
    captures = receipt.get("captures")
    if not isinstance(captures, list) or not captures:
        return False
    newest = max(_utc(item["available_at"]) for item in captures)
    selected = [item for item in captures if _utc(item["available_at"]) == newest]
    if (newest > as_of.astimezone(UTC) or len(selected) != 1
            or selected[0]["evidence_id"] != receipt.get("selected_evidence_id")):
        return False
    if version == GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION:
        if (receipt.get("accounting_definitions_admitted") is not False or any(
            _utc(row["available_at"]) != newest for row in receipt["observations"])):
            return False
    elif (receipt.get("accounting_definition_qualified") is not False
          or _utc(receipt.get("recorded_at")) != newest):
        return False
    return (sha256(financial_input_json(body).encode()).hexdigest() == receipt.get("input_hash")
        and receipt.get("model_version") == version and receipt.get("source_bound") is True
        and receipt.get("subject") == subject and receipt.get("market") == market.value
        and _utc(receipt.get("as_of")) == as_of.astimezone(UTC)
        and receipt.get("trust_ceiling") == "LOW"
        and receipt.get("availability_precision") == "retrieval_time"
        and all(receipt.get(name) is False for name in (
            "financial_scoring_authorized", "investment_scoring_authorized",
            "historical_replay_eligible", "validation_authorized", "execution_authorized")))


def review_native_pairs(native: Mapping[str, Any], reviewed: Mapping[str, Any], *,
    candidates: Sequence[str], subject: str, market: Market, as_of: datetime,
) -> dict[str, Any]:
    """Consume exact-reader receipts; checksums check context, not source truth."""
    require_timezone(as_of, "native pair cutoff")
    if market not in {Market.HONG_KONG, Market.MALAYSIA}:
        raise ValueError("native/manual candidates currently require HK/MY review evidence")
    pairs = parse_native_pairs(candidates)
    reject_sensitive_structure(native, path="native_pair_input")
    reject_sensitive_structure(reviewed, path="manual_pair_input")
    output: dict[str, Any] = {"subject": subject, "market": market.value,
        "as_of": as_of.astimezone(UTC), "model_version": GLOBAL_NATIVE_PAIR_VERSION,
        "status": "INPUT_REJECTED", "requested_candidates": pairs, "pairs": [],
        "native_input_hash": native.get("input_hash"),
        "review_input_hash": reviewed.get("input_hash"),
        "native_status": native.get("status"), "review_status": reviewed.get("status"),
        "accounting_mapping_admitted": False, "numeric_consistency_assessed": False,
        "independent_provider_consistency_assessed": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "research_report_created": False,
        "limitations": (
            "Candidates are explicit questions, not mappings inferred from names or amounts",
            "Exact-reader receipts and checksums do not authenticate issuer or accounting truth",
            "Yahoo raw units, flow starts, scope, attribution and revision identity are unverified",
            "Scaled manual values have unverified source precision; no inferred tolerance or FX",
            "No amount difference, equality vote, favorable selection or scoring admission",
        )}
    try:
        valid = (_receipt_ok(native, version=GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION,
            subject=subject, market=market, as_of=as_of)
            and _receipt_ok(reviewed, version=GLOBAL_DOCUMENT_REVIEW_VERSION,
                subject=subject, market=market, as_of=as_of)
            and native.get("status") in {"observed_unqualified", "partial_unqualified"}
            and reviewed.get("status") == "MANUAL_TRANSCRIPTION_UNQUALIFIED")
        if valid:
            output["pairs"] = [_pair(row_key, metric, native["observations"],
                                      reviewed["observations"], pairs, native["latest"])
                               for row_key, metric in pairs]
            output["status"] = "CANDIDATE_REVIEW_ONLY"
    except (ValueError, KeyError, TypeError, ArithmeticError):
        output["pairs"] = []
        output["status"] = "INPUT_REJECTED"
    output["review_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output


def _pair(row_key: str, metric: str, native: list[dict[str, Any]],
    manual: list[dict[str, Any]], pairs: tuple[tuple[str, str], ...],
    latest: Mapping[str, Any],
) -> dict[str, Any]:
    selected = [row for row in manual if row["row_key"] == row_key]
    result: dict[str, Any] = {"row_key": row_key, "native_metric": metric,
        "status": "MISSING_MANUAL_ROW", "manual_row": None, "native_rows": [],
        "blockers": [], "amount_difference": None, "numeric_agreement": None,
        "mapping_admitted": False}
    if len(selected) != 1:
        result["status"] = "AMBIGUOUS_MANUAL_ROW" if selected else "MISSING_MANUAL_ROW"
        return result
    row = selected[0]
    # Exact end-label matching is descriptive only; never select by amount or another year.
    matches = [item for item in native if item["native_metric"] == metric
               and item["period_end"] == row["period_end"]]
    blockers = ["ISSUER_BINDING_UNVERIFIED", "ACCOUNTING_DEFINITION_NOT_ADMITTED",
        "NATIVE_UNIT_UNVERIFIED", "NATIVE_CONSOLIDATION_SCOPE_UNKNOWN",
        "ATTRIBUTION_BASIS_UNVERIFIED", "SOURCE_PRECISION_NOT_VERIFIED",
        "PUBLICATION_AND_REVISION_HISTORY_UNKNOWN", "INDEPENDENT_CORROBORATION_MISSING"]
    if row["statement"] != "balance":
        blockers.append("NATIVE_FLOW_START_UNKNOWN")
    if row["reporting_scope"] != "group":
        blockers.append("STANDALONE_SCOPE_NOT_GROUP")
    if row["column_kind"] == "comparative":
        blockers.append("COMPARATIVE_EDITION_NOT_RECONCILED")
    competing = [key for key, name in pairs if name == metric and key != row_key and any(
        item["row_key"] == key and item["period_end"] == row["period_end"] for item in manual)]
    if competing:
        blockers.append("MULTIPLE_CANDIDATES_FOR_NATIVE_CONTEXT")
    status = "CONTEXT_UNQUALIFIED"
    if row["value_status"] != "transcribed":
        status = "UNRESOLVED_MANUAL_VALUE"
    elif not matches:
        status = "MISSING_NATIVE_PERIOD"
    elif len(matches) > 1 or any(item["period_end"] is None for item in native
                               if item["native_metric"] == metric):
        status = "AMBIGUOUS_NATIVE_PERIOD"
    elif latest.get(metric, {}).get("status") != "OBSERVED_UNQUALIFIED":
        status = "LATEST_NATIVE_UNUSABLE"
    elif matches[0]["status"] != "OBSERVED_UNQUALIFIED":
        status = "UNUSABLE_NATIVE_ROW"
    elif matches[0]["currency"] != row["currency"]:
        status = "CURRENCY_CONFLICT"
    result.update(status=status, manual_row=dict(row), native_rows=[dict(item) for item in matches],
                  blockers=blockers, competing_row_keys=competing)
    return result


def parse_income_sums(values: Sequence[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not 1 <= len(values) <= 16:
        raise ValueError("supply 1-16 explicit result=component+component income sums")
    sums = []
    for value in values:
        parts = value.split("=")
        names = parts[1].split("+") if len(parts) == 2 else []
        if (not 2 <= len(names) <= 8 or any(
            re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) is None for name in [parts[0], *names]
        ) or len(set(names)) != len(names) or parts[0] in names):
            raise ValueError("income sums require distinct exact row keys and signed source values")
        sums.append((parts[0], tuple(names)))
    if len({name for name, _ in sums}) != len(sums):
        raise ValueError("duplicate income-sum result")
    return tuple(sums)


def review_income_sums(reviewed: Mapping[str, Any], *, identities: Sequence[str],
    subject: str, market: Market, as_of: datetime,
) -> dict[str, Any]:
    """Check explicitly declared same-column signed sums, never select accounting definitions."""
    require_timezone(as_of, "manual income arithmetic cutoff")
    if market not in {Market.HONG_KONG, Market.MALAYSIA}:
        raise ValueError("manual income arithmetic requires HK/MY evidence")
    sums = parse_income_sums(identities)
    reject_sensitive_structure(reviewed, path="income_arithmetic_input")
    output: dict[str, Any] = {"status": "INPUT_REJECTED", "subject": subject,
        "market": market.value, "as_of": as_of.astimezone(UTC), "requested_sums": sums,
        "review_input_hash": reviewed.get("input_hash"), "checks": [],
        "model_version": GLOBAL_MANUAL_ARITHMETIC_VERSION,
        "accounting_definition_qualified": False, "source_location_verified": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "independent_review": False,
        "limitations": (
            "Signed sums test manual transcription only; not PDF, accounting or source truth",
            "Exact same statement/scope/period/column/currency/unit labels are mandatory",
            "No inferred missing zero, expense sign, coefficient, rounding tolerance or FX",
            "Arithmetic agreement cannot select a Yahoo alias, admit scores or validate a strategy",
        )}
    try:
        if (_receipt_ok(reviewed, version=GLOBAL_DOCUMENT_REVIEW_VERSION, subject=subject,
                        market=market, as_of=as_of)
                and reviewed.get("status") == "MANUAL_TRANSCRIPTION_UNQUALIFIED"):
            raw = reviewed["review"]
            metadata = {key: value for key, value in raw.items() if key != "rows"}
            review = parse_global_document_review({"review": metadata, "rows": raw["rows"]})
            if ([row.observation() for row in review.rows] != reviewed["observations"]
                    or review.subject != subject or review.market != market
                    or review.reviewed_at.astimezone(UTC) > _utc(reviewed["recorded_at"])):
                raise ValueError("manual arithmetic receipt/model mismatch")
            observations = {row.row_key: row.document() for row in review.rows}
            output["checks"] = [_income_sum(result, components, observations)
                                for result, components in sums]
            output["status"] = "TRANSCRIPTION_ARITHMETIC_ONLY"
    except (ValueError, KeyError, TypeError, ArithmeticError):
        output["status"] = "INPUT_REJECTED"
        output["checks"] = []
    output["review_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output


def _income_sum(result: str, components: tuple[str, ...],
    observations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    names = (result, *components)
    missing = [name for name in names if name not in observations]
    rows = [observations[name] for name in names if name in observations]
    output: dict[str, Any] = {"result_row": result, "component_rows": components,
        "observations": rows, "missing_row_keys": missing, "status": "MISSING_ROW",
        "result_source_value": None, "signed_component_sum": None,
        "residual_source_units": None, "currency": None, "source_unit": None,
        "accounting_verified": False}
    if missing:
        return output
    if any(row["value_status"] != "transcribed" for row in rows):
        output["status"] = "UNRESOLVED_VALUE"
        return output
    keys = ("statement", "reporting_scope", "period_start", "period_end", "column_kind",
            "column_label", "currency", "source_unit", "source_unit_label", "restatement_label")
    if any(row["statement"] != "income" or any(row[key] != rows[0][key] for key in keys)
           for row in rows):
        output["status"] = "CONTEXT_MISMATCH"
        return output
    with localcontext() as context:
        context.prec = 100
        result_value = Decimal(rows[0]["source_value"])
        component_sum = sum((Decimal(row["source_value"]) for row in rows[1:]), Decimal(0))
        residual = result_value - component_sum
    output.update(status="ARITHMETIC_AGREES_AS_TRANSCRIBED" if residual == 0 else
                  "ARITHMETIC_RESIDUAL_AS_TRANSCRIBED",
        result_source_value=format(result_value, "f"),
        signed_component_sum=format(component_sum, "f"),
        residual_source_units=format(residual, "f"),
        currency=rows[0]["currency"], source_unit=rows[0]["source_unit"])
    return output


def parse_income_changes(values: Sequence[str]) -> tuple[tuple[str, str], ...]:
    if not 1 <= len(values) <= 16:
        raise ValueError("supply 1-16 explicit current_row=prior_row income changes")
    pairs = []
    for value in values:
        parts = value.split("=")
        if (len(parts) != 2 or parts[0] == parts[1] or any(
            re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) is None for key in parts)):
            raise ValueError("income changes require two distinct exact row keys")
        pairs.append((parts[0], parts[1]))
    if len({current for current, _ in pairs}) != len(pairs):
        raise ValueError("each current income row requires one explicit prior row")
    return tuple(pairs)


def review_income_changes(inputs: ReviewedDocumentResearchInput, *,
    pairs: Sequence[str],
) -> dict[str, Any]:
    inputs.validate_context()
    requested = parse_income_changes(pairs)
    receipt = inputs.document()
    usable = receipt["status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED"
    rows = {row["row_key"]: row for row in receipt["observations"]}
    output: dict[str, Any] = {"status": "DESCRIPTIVE_REVIEW_ONLY" if usable
        else "SOURCE_INPUT_UNUSABLE", "subject": receipt["subject"], "market": receipt["market"],
        "as_of": inputs.as_of, "requested_pairs": requested,
        "input_hash": receipt["input_hash"], "model_version": GLOBAL_MANUAL_CHANGE_VERSION,
        "comparisons": [_income_change(current, prior, rows, usable)
                        for current, prior in requested],
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "accounting_comparability_verified": False,
        "original_historical_vintages_verified": False,
        "limitations": (
            "Same-filing column changes are descriptive, not verified business growth or scores",
            "Comparatives are as presented in this filing, not original historical vintages",
            "No inferred original publication, revision reconciliation, independent review or FX",
            "Unsupported windows, missing/conflicting values and nonpositive bases remain explicit",
        )}
    output["review_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output


def _income_change(current: str, prior: str, rows: dict[str, Any], usable: bool) -> dict[str, Any]:
    left, right = rows.get(current), rows.get(prior)
    output: dict[str, Any] = {"current_row_key": current, "prior_row_key": prior,
        "status": "SOURCE_INPUT_UNUSABLE", "current_observation": left, "prior_observation": right,
        "amount_change_source_units": None, "change_percent": None,
        "currency": None, "source_unit": None}
    if not usable:
        return output
    if left is None or right is None:
        output["status"] = "MISSING_ROW"
    elif any(row["value_status"] != "transcribed" for row in (left, right)):
        output["status"] = "UNRESOLVED_VALUE"
    elif left["column_kind"] != "current" or right["column_kind"] != "comparative":
        output["status"] = "COLUMN_KIND_MISMATCH"
    elif (left["statement"] != "income" or any(left[key] != right[key] for key in (
        "native_label", "statement", "reporting_scope", "currency", "source_unit",
        "source_unit_label", "restatement_label"))):
        output["status"] = "CONTEXT_MISMATCH"
    else:
        start, end, old_start, old_end = (date.fromisoformat(value) for value in (
            left["period_start"], left["period_end"], right["period_start"], right["period_end"]))
        annual = all((last + timedelta(days=1)).year == first.year + 1
            and ((last + timedelta(days=1)).month, (last + timedelta(days=1)).day)
            == (first.month, first.day) for first, last in ((start, end), (old_start, old_end)))
        aligned = all(new.year == old.year + 1 and (new.month, new.day) == (old.month, old.day)
                      for new, old in ((start, old_start), (end, old_end)))
        if not annual or not aligned:
            output["status"] = "UNSUPPORTED_ANNUAL_WINDOWS"
            return output
        with localcontext() as context:
            context.prec = 100
            current_value = Decimal(left["source_value"])
            prior_value = Decimal(right["source_value"])
            change = current_value - prior_value
            percent = ((change / prior_value * 100).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN) if prior_value > 0 else None)
        output.update(status="DESCRIPTIVE_UNQUALIFIED" if percent is not None else
            "NONPOSITIVE_BASE", amount_change_source_units=format(change, "f"),
            change_percent=format(percent, "f") if percent is not None else None,
            currency=left["currency"], source_unit=left["source_unit"])
    return output
