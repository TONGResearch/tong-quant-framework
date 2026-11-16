"""Exploratory native amount changes and sector questions, not financial assessment."""

from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION, GLOBAL_NATIVE_REVIEW_VERSION

# These are review questions, not admitted criteria, hard screens or scoring weights.
_QUESTIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "nonfinancial": {
        "survival": ("restricted_cash", "debt_maturities", "interest_bearing_debt_definition"),
        "cycle": ("industry_supply_demand", "recurring_vs_one_off_earnings"),
        "valuation": ("dated_share_classes_and_actions", "qualified_price_and_earnings_basis"),
        "growth": ("comparable_consolidation_and_periods", "invested_capital_and_roic_definition"),
    },
    "bank": {
        "survival": ("asset_quality", "capital_and_liquidity", "funding_structure"),
        "cycle": ("credit_cycle", "bank_earnings_and_impairment_definitions"),
        "valuation": ("bank_equity_and_earnings_basis", "dated_share_classes_and_actions"),
        "growth": ("credit_quality_of_expansion", "sustainable_bank_earnings"),
    },
    "securities": {
        "survival": ("capital_and_liquidity", "balance_sheet_and_market_risk"),
        "cycle": ("revenue_mix", "market_activity_and_earnings_cycle"),
        "valuation": ("securities_equity_and_earnings_basis", "dated_share_classes_and_actions"),
        "growth": ("recurring_business_growth", "risk_adjusted_expansion"),
    },
    "insurance": {
        "survival": ("insurance_capital_and_liquidity", "liability_and_asset_risks"),
        "cycle": ("underwriting_cycle", "investment_and_insurance_earnings_split"),
        "valuation": ("insurance_accounting_and_valuation_basis",
                      "dated_share_classes_and_actions"),
        "growth": ("underwriting_quality", "insurance_accounting_comparability"),
    },
    "unknown": {name: ("issuer_business_and_sector_classification", "sector_policy_definition")
                for name in ("survival", "cycle", "valuation", "growth")},
}


def _utc(value: object) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("native review timestamp missing")
    require_timezone(value, "native review timestamp")
    return value.astimezone(UTC)


def _receipt_valid(snapshot: Mapping[str, Any], subject: str, market: Market,
                   as_of: datetime) -> bool:
    """Check receipt integrity/context, not independent authentication of a provider."""
    body = {key: value for key, value in snapshot.items() if key != "input_hash"}
    if (sha256(financial_input_json(body).encode()).hexdigest() != snapshot.get("input_hash")
            or snapshot.get("model_version") != GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION
            or snapshot.get("subject") != subject or snapshot.get("market") != market.value
            or _utc(snapshot.get("as_of")) != as_of.astimezone(UTC)
            or snapshot.get("source_bound") is not True
            or any(snapshot.get(name) is not False for name in (
                "financial_scoring_authorized", "investment_scoring_authorized",
                "historical_replay_eligible", "validation_authorized", "execution_authorized",
                "accounting_definitions_admitted"))):
        return False
    captures = snapshot["captures"]
    if not isinstance(captures, list) or not captures:
        return False
    capture_times = [_utc(item["available_at"]) for item in captures]
    selected = [item for item in captures if _utc(item["available_at"]) == max(capture_times)]
    if (max(capture_times) > as_of.astimezone(UTC) or len(selected) != 1
            or selected[0]["evidence_id"] != snapshot.get("selected_evidence_id")):
        return False
    metrics = snapshot["requested_native_metrics"]
    if (not isinstance(metrics, (tuple, list)) or not 1 <= len(metrics) <= 32
            or any(not isinstance(item, str) or not item for item in metrics)
            or len(set(metrics)) != len(metrics)):
        return False
    rows = snapshot["observations"]
    return (isinstance(rows, list) and len(rows) <= 2048 and all(
        isinstance(row, dict) and row.get("native_metric") in metrics
        and _utc(row.get("available_at")) == max(capture_times) for row in rows))


def _amount(row: Mapping[str, Any]) -> Decimal:
    if type(row.get("value")) is not str:
        raise ValueError("native review requires normalized decimal strings")
    value = Decimal(row["value"])
    if (not value.is_finite() or abs(value) > Decimal("1e24")
            or abs(int(value.as_tuple().exponent)) > 64):
        raise ValueError("native review amount outside supported bounds")
    return value


def _change(metric: str, rows: list[dict[str, Any]], cutoff: datetime) -> dict[str, Any]:
    result: dict[str, Any] = {"native_metric": metric, "status": "MISSING",
        "current_period_end": None, "prior_period_end": None, "currency": None,
        "current_value": None, "prior_value": None, "native_amount_change": None,
        "native_change_percent": None, "kind": "unqualified_native_amount_change",
        "accounting_comparability_verified": False}
    if not rows:
        return result
    try:
        if any(not isinstance(row.get("period_end"), str) for row in rows):
            result["status"] = "AMBIGUOUS_PERIOD"
            return result
        periods = sorted({date.fromisoformat(row["period_end"]) for row in rows}, reverse=True)
        current = [row for row in rows if date.fromisoformat(row["period_end"]) == periods[0]]
        result["current_period_end"] = periods[0].isoformat()
        if periods[0] > cutoff.astimezone(UTC).date():
            result["status"] = "FUTURE_PERIOD"
            return result
        if len(current) != 1:
            result["status"] = "AMBIGUOUS_CURRENT"
            return result
        if current[0].get("status") != "OBSERVED_UNQUALIFIED":
            result["status"] = "LATEST_UNUSABLE"
            return result
        current_value = _amount(current[0])
        result.update(current_value=str(current_value), currency=current[0].get("currency"))
        if len(periods) < 2:
            result["status"] = "MISSING_PREVIOUS"
            return result
        result["prior_period_end"] = periods[1].isoformat()
        prior = [row for row in rows if date.fromisoformat(row["period_end"]) == periods[1]]
        if len(prior) != 1:
            result["status"] = "AMBIGUOUS_PREVIOUS"
            return result
        left, right = current[0], prior[0]
        if right.get("status") != "OBSERVED_UNQUALIFIED":
            result["status"] = "PREVIOUS_UNUSABLE"
            return result
        if (periods[0].year != periods[1].year + 1
                or (periods[0].month, periods[0].day) != (periods[1].month, periods[1].day)
                or left.get("period_type") != "12M" or right.get("period_type") != "12M"):
            result["status"] = "NONMATCHING_ANNUAL_LABELS"
            return result
        currency = left.get("currency")
        if (not isinstance(currency, str) or len(currency) != 3
                or not currency.isascii() or not currency.isalpha() or not currency.isupper()
                or currency != right.get("currency")
                or left.get("unit") != "provider_reported_raw"
                or right.get("unit") != "provider_reported_raw"):
            result["status"] = "INCOMPATIBLE_CURRENCY_OR_UNIT"
            return result
        prior_value = _amount(right)
        with localcontext() as context:
            context.prec = 100
            change = current_value - prior_value
            percentage = ((change / prior_value * 100).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN) if prior_value > 0 else None)
        result.update(status="DESCRIPTIVE_UNQUALIFIED" if percentage is not None
                      else "NONPOSITIVE_BASE", currency=left["currency"],
            current_value=str(current_value), prior_value=str(prior_value),
            native_amount_change=str(change),
            native_change_percent=str(percentage) if percentage is not None else None)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        result["status"] = "INVALID_OBSERVATION"
    return result


def review_native_financials(
    snapshot: Mapping[str, Any], *, subject: str, market: Market, as_of: datetime,
    sector_profile: str,
) -> dict[str, Any]:
    require_timezone(as_of, "native financial review cutoff")
    if market not in {Market.US, Market.HONG_KONG, Market.MALAYSIA}:
        raise ValueError("native financial review requires an overseas equity market")
    if sector_profile not in _QUESTIONS:
        raise ValueError("unsupported native financial review sector")
    reject_sensitive_structure(snapshot, path="native_financial_review_input")
    output: dict[str, Any] = {"subject": subject, "market": market.value,
        "as_of": as_of.astimezone(UTC), "requested_sector_profile": sector_profile,
        "sector_classification_verified": False, "sector_policy_status": "NOT_ADMITTED",
        "status": "INPUT_REJECTED", "comparisons": [], "observations_to_review": [],
        "financial_condition_state": "EVIDENCE_INSUFFICIENT", "receipt_integrity_valid": False,
        "source_input_hash": snapshot.get("input_hash"),
        "source_status": snapshot.get("status", "unknown"),
        "value_research_prerequisites": {name: {"status": "UNASSESSED", "questions": questions}
                                         for name, questions in _QUESTIONS[sector_profile].items()},
        "data_gaps": ("source_and_accounting_qualification", "publication_and_revision_history",
                      "consolidation_and_period_start", "latest_interim_disclosures",
                      "independent_consistency_and_continuity", "approved_sector_scoring_policy"),
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "research_report_created": False,
        "model_version": GLOBAL_NATIVE_REVIEW_VERSION,
        "limitations": (
            "Receipt/hash checks are not independent source authentication or quality promotion",
            "Native amount changes are not verified business growth, investment returns or scores",
            "Matching end-date/12M labels do not prove comparable accounting or exact flow periods",
            "Sector questions and negative observations never reject an issuer or instruct a trade",
            "No FX, valuation multiples, ROE/ROIC, qualified TTM or regime switch is introduced",
        )}
    try:
        valid = _receipt_valid(snapshot, subject, market, as_of)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        valid = False
    if valid:
        changes = [_change(metric, [row for row in snapshot["observations"]
                                   if row["native_metric"] == metric], as_of)
                   for metric in snapshot["requested_native_metrics"]]
        output.update(status="EXPLORATORY_REVIEW", receipt_integrity_valid=True,
                      comparisons=changes)
        if sector_profile == "nonfinancial":
            output["observations_to_review"] = [
                f"{item['native_metric']}:negative_native_amount_requires_business_context"
                for item in changes if item["native_metric"] in {
                    "annualOperatingCashFlow", "annualNetIncome"}
                and item["current_value"] is not None and Decimal(item["current_value"]) < 0]
    return {**output, "review_hash": sha256(financial_input_json(output).encode()).hexdigest()}
