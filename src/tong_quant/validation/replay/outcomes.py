"""Exact UTC calendar-day price observations, not simulated investment returns."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import isfinite
from typing import cast

from tong_quant.data.price_evidence import daily_bar_content, daily_bar_content_hash
from tong_quant.domain.enums import Adjustment, ThesisOutcomeStatus
from tong_quant.domain.models import Bar, Instrument
from tong_quant.validation.models import OutcomeDefinition, ValidationOutcome
from tong_quant.validation.replay.hashing import stable_json
from tong_quant.validation.replay.models import ReplayQuery, ReplayValidationSample
from tong_quant.version import REPLAY_OUTCOME_VERSION


def evaluate_outcome(
    query: ReplayQuery,
    instrument: Instrument,
    definition: OutcomeDefinition,
    decision_bar: Bar | None,
    outcome_bar: Bar | None,
) -> tuple[ValidationOutcome, dict[str, object]]:
    start = query.decision_as_of.astimezone(UTC)
    target = start + timedelta(days=definition.observation_horizon_days)
    earliest = target + timedelta(days=definition.availability_lag_days)
    blockers: list[str] = []
    if definition.target_metric != "close_return_pct":
        blockers.append("unsupported_target_metric")
    if definition.benchmark is not None:
        blockers.append("benchmark_not_supported")
    if not isfinite(definition.success_threshold):
        blockers.append("invalid_success_threshold")
    if query.outcome_as_of < earliest:
        blockers.append("outcome_not_matured")
    for name, bar, expected, cutoff in (
        ("decision", decision_bar, start, query.decision_as_of),
        ("outcome", outcome_bar, target, query.outcome_as_of),
    ):
        if bar is None:
            blockers.append(f"{name}_bar_missing")
            continue
        if bar.timestamp.astimezone(UTC).date() != expected.date():
            blockers.append(f"{name}_bar_date_mismatch")
        if bar.timestamp > expected or bar.available_at > cutoff:
            blockers.append(f"{name}_bar_not_visible")
        if bar.adjustment is not Adjustment.NONE:
            blockers.append(f"{name}_bar_adjusted")
        if (
            bar.instrument.symbol != instrument.symbol
            or bar.instrument.market is not instrument.market
            or bar.instrument.asset_type is not instrument.asset_type
            or bar.instrument.currency != instrument.currency
        ):
            blockers.append(f"{name}_bar_instrument_mismatch")
        if not bar.source.strip():
            blockers.append(f"{name}_bar_source_missing")
        if (
            any(
                number is not None and not number.is_finite()
                for number in (bar.open, bar.high, bar.low, bar.close, bar.volume, bar.turnover)
            )
            or bar.close <= 0
        ):
            blockers.append(f"{name}_bar_invalid_price")
    value = None
    succeeded = None
    if not blockers and decision_bar is not None and outcome_bar is not None:
        value = float((outcome_bar.close / decision_bar.close - Decimal("1")) * 100)
        if not isfinite(value):
            blockers.append("outcome_value_not_finite")
            value = None
        else:
            succeeded = _compare(value, definition.success_operator, definition.success_threshold)
    subject = f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"
    outcome = ValidationOutcome(
        outcome_id=f"{definition.outcome_id}:{subject}",
        definition_id=definition.outcome_id,
        subject_id=subject,
        observed_at=min(target, query.outcome_as_of),
        available_at=query.outcome_as_of,
        value=value,
        benchmark_value=None,
        succeeded=succeeded,
        thesis_status=(
            ThesisOutcomeStatus.NOT_OBSERVABLE
            if value is None
            else ThesisOutcomeStatus.SUPPORTED
            if succeeded
            else ThesisOutcomeStatus.INVALIDATED
        ),
        invalidation_triggered=None if value is None else not bool(succeeded),
        metadata={
            "target_metric": definition.target_metric,
            "outcome_contract": REPLAY_OUTCOME_VERSION,
            "price_basis": "unadjusted_price_only_excludes_distributions_and_costs",
        },
    )
    return outcome, {
        "outcome_contract": REPLAY_OUTCOME_VERSION,
        "date_basis": "exact_utc_calendar_days_no_session_fallback",
        "definition": stable_json(definition),
        "expected_start_date": start.date().isoformat(),
        "expected_end_date": target.date().isoformat(),
        "expected_observed_at": target.isoformat(),
        "earliest_available_at": earliest.isoformat(),
        "decision_bar": _binding(decision_bar),
        "outcome_bar": _binding(outcome_bar),
        "blocking_reasons": blockers,
        "target_metric": definition.target_metric,
        "value": value,
        "outcome_available_at": outcome.available_at.isoformat(),
        "price_basis": outcome.metadata["price_basis"],
        "limitations": [
            "bar_hash_is_content_identity_not_independent_source_verification",
            "corporate_actions_total_return_and_trading_costs_not_evaluated",
            "calendar_dates_do_not_establish_exchange_sessions_or_executable_prices",
        ],
    }


def require_verified_outcome(sample: ReplayValidationSample, query: ReplayQuery) -> None:
    """Re-evaluate bound observations; confidence labels cannot authorize a bad window."""
    context = sample.outcome_context
    definition = next(
        (
            item
            for item in query.outcome_definitions
            if stable_json(item) == context.get("definition")
        ),
        None,
    )
    if definition is None:
        raise ValueError("unknown replay outcome definition")
    outcome, expected = evaluate_outcome(
        query,
        sample.instrument,
        definition,
        _decode_binding(context.get("decision_bar"), sample.instrument),
        _decode_binding(context.get("outcome_bar"), sample.instrument),
    )
    if (
        stable_json(expected) != stable_json(context)
        or expected["blocking_reasons"]
        or sample.validation_sample is None
        or stable_json(sample.validation_sample.outcome) != stable_json(outcome)
    ):
        raise ValueError("replay outcome evidence or window mismatch")


def _binding(bar: Bar | None) -> dict[str, object] | None:
    if bar is None:
        return None
    if any(
        number is not None and not number.is_finite()
        for number in (bar.open, bar.high, bar.low, bar.close, bar.volume, bar.turnover)
    ):
        return {"invalid_content": stable_json(bar)}
    return {"content": daily_bar_content(bar), "content_hash": daily_bar_content_hash(bar)}


def _decode_binding(value: object, instrument: Instrument) -> Bar | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("content"), dict):
        raise ValueError("missing replay bar content")
    content = value["content"]
    bar = Bar(
        instrument=instrument,
        timestamp=datetime.fromisoformat(content["timestamp"]),
        available_at=datetime.fromisoformat(content["available_at"]),
        open=Decimal(content["open"]),
        high=Decimal(content["high"]),
        low=Decimal(content["low"]),
        close=Decimal(content["close"]),
        volume=Decimal(content["volume"]),
        turnover=None if content["turnover"] is None else Decimal(content["turnover"]),
        adjustment=Adjustment(content["adjustment"]),
        is_suspended=cast(bool, content["is_suspended"]),
        source=content["source"],
    )
    if _binding(bar) != value:
        raise ValueError("replay bar content hash or instrument mismatch")
    return bar


def _compare(value: float, operator: str, threshold: float) -> bool:
    return {
        ">": value > threshold,
        ">=": value >= threshold,
        "<": value < threshold,
        "<=": value <= threshold,
        "==": value == threshold,
        "!=": value != threshold,
    }[operator]
