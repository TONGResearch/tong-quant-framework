"""Read retained daily changes; descriptive research, never holding instructions."""

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.application.native_fundamental_changes import read_native_fundamental_change_digest
from tong_quant.application.technical_binding import build_technical_binding
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs, read_global_price_inputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.research.technical.long_horizon import (
    LongHorizonParameters,
    long_horizon_diagnostics,
)
from tong_quant.version import (
    EQUITY_CHANGE_DIGEST_VERSION,
    EQUITY_NATIVE_CHANGE_DIGEST_VERSION,
    EQUITY_PERIOD_CHANGE_DIGEST_VERSION,
)

_FIELDS = (
    "macd_dif", "macd_dea", "macd_histogram", "kdj_k", "kdj_d", "kdj_j",
    "technical_atr", "macd_cross", "kdj_cross", "trend_structure_family",
    "momentum_family", "technical_confluence", "setup_state", "setup_direction",
    "triple_average_events", "granville_events",
)
_UNAVAILABLE = (None, "unavailable", "INSUFFICIENT_DATA")


def _frame(snapshot: GlobalPriceInputs, parameters: TechnicalParameters) -> dict[str, Any]:
    diagnostics = technical_diagnostics(snapshot.bars, parameters, as_of=snapshot.as_of)
    document = {"research_only": True, "research_report_created": False,
        "readiness_promoted": False, "inputs": snapshot.document(), "diagnostics": diagnostics}
    binding = build_technical_binding(snapshot, parameters, document)
    return {"binding": binding, "diagnostics": diagnostics, "inputs": document["inputs"]}


def _context(snapshot: GlobalPriceInputs) -> list[tuple[str, str | None, str, str]]:
    return sorted({(bar.instrument.currency, bar.instrument.exchange, bar.source,
                    bar.adjustment.value) for bar in snapshot.bars}, key=financial_input_json)


def _history(snapshot: GlobalPriceInputs) -> dict[datetime, tuple[object, ...]]:
    # Recapture availability changes are provenance, not changes to market prices.
    return {bar.timestamp.astimezone(UTC): (bar.open, bar.high, bar.low, bar.close,
        bar.volume, bar.turnover, bar.is_suspended) for bar in snapshot.bars}


def _summary(snapshot: GlobalPriceInputs, frame: dict[str, Any]) -> dict[str, Any]:
    inputs = frame["inputs"]
    return {"as_of": snapshot.as_of.astimezone(UTC), "status": snapshot.status,
        "freshness": snapshot.freshness,
        "observation_age_seconds": snapshot.observation_age_seconds,
        "maximum_age_seconds": snapshot.maximum_age_seconds,
        "selected_evidence_id": snapshot.selected_evidence_id,
        "observed_bar_count": len(snapshot.bars),
        "first_observed_at": inputs["first_observed_at"],
        "last_observed_at": inputs["last_observed_at"],
        "price_input_hash": inputs["input_hash"], "source_context": _context(snapshot),
        "technical_binding": frame["binding"],
        "technical_missing_inputs": frame["diagnostics"]["technical_missing_inputs"]}


def _period_frame(snapshot: GlobalPriceInputs, parameters: TechnicalParameters) -> dict[str, Any]:
    diagnostic = long_horizon_diagnostics(snapshot.bars, market=snapshot.market,
        as_of=snapshot.as_of, parameters=LongHorizonParameters(indicators=parameters),
        weekly_sma_periods=(13, 26, 52))
    inventory_evaluated = diagnostic["status"] == "OBSERVED_UNQUALIFIED"
    frequencies = {}
    for frequency in ("weekly", "monthly"):
        source = diagnostic[frequency]
        ended = [row for row in source["periods"] if row["calendar_period_ended"]]
        latest = ended[-1] if ended else None
        alignment = next(row for row in diagnostic["timeframe_alignment"]["periods"]
                         if row["frequency"] == frequency)
        frequencies[frequency] = {name: source[name] for name in (
            "status", "ended_period_count", "calculation_period_count",
            "last_ended_period_start", "last_ended_close", "moving_averages", "macd", "kdj")}
        frequencies[frequency].update(
            period_inventory_evaluated=inventory_evaluated,
            blocking_period_count=(len(source["blocking_period_starts"])
                                   if inventory_evaluated else None),
            blocking_period_examples=source["blocking_period_starts"][:10],
            open_period_starts=source["open_period_starts"],
            latest_period_alignment=alignment,
            latest_ended_observed_date_count=latest["observed_date_count"] if latest else None,
            session_coverage="UNVERIFIED")
        if not inventory_evaluated:
            frequencies[frequency].update(ended_period_count=None, calculation_period_count=None,
                                          open_period_starts=None)
    return {"model_version": diagnostic["model_version"], "as_of": diagnostic["as_of"],
        "diagnostics_input_hash": diagnostic["input_hash"],
        "calendar_input_hash": diagnostic["calendar_input_hash"],
        "source_bars_content_hash": diagnostic["source_bars_content_hash"],
        "supplied_daily_row_count": diagnostic["supplied_daily_row_count"],
        "parameters": diagnostic["parameters"],
        "weekly_sma_periods": diagnostic["weekly_sma_periods"], "frequencies": frequencies}


def _period_context(previous: GlobalPriceInputs, current: GlobalPriceInputs,
                    old_parameters: TechnicalParameters, new_parameters: TechnicalParameters,
                    inherited_reasons: list[str]) -> dict[str, Any]:
    before, after = _period_frame(previous, old_parameters), _period_frame(current, new_parameters)
    comparisons = []
    for frequency in ("weekly", "monthly"):
        old, new = before["frequencies"][frequency], after["frequencies"][frequency]
        reasons = list(inherited_reasons)
        for name, frame in (("previous", old), ("current", new)):
            if frame["status"] != "OBSERVED_UNQUALIFIED":
                reasons.append(f"{name}_{frequency}_context_unavailable:{frame['status']}")
        old_end, new_end = old["last_ended_period_start"], new["last_ended_period_start"]
        if old_end is not None and new_end is not None and new_end < old_end:
            reasons.append("ended_calendar_period_regressed")
        comparable = not reasons
        aligned = comparable and old_end == new_end
        indicators = []
        if comparable:
            values = [(f"sma_{a['periods']}", a["value"], b["value"],
                       a["status"], b["status"])
                      for a, b in zip(old["moving_averages"], new["moving_averages"], strict=True)]
            values.extend((name, old[name]["values"], new[name]["values"],
                           old[name]["status"], new[name]["status"]) for name in ("macd", "kdj"))
            for name, a, b, old_status, new_status in values:
                available = (old_status == new_status == "OBSERVED_UNQUALIFIED"
                             and a is not None and b is not None)
                indicators.append({"field": name, "previous": a, "current": b,
                    "previous_status": old_status, "current_status": new_status,
                    "comparison": ("NOT_EVALUATED" if not available else
                        "NOT_ALIGNED" if not aligned else "UNCHANGED" if a == b else "CHANGED")})
        comparisons.append({"frequency": frequency,
            "comparison_status": ("NOT_COMPARABLE" if not comparable else
                "SAME_ENDED_PERIOD" if aligned else "PERIOD_END_ADVANCED"),
            "blocking_reasons": reasons,
            "new_calendar_ended_period_count": (
                new["ended_period_count"] - old["ended_period_count"] if comparable else None),
            "same_ended_period": aligned if comparable else None,
            "indicator_changes": indicators})
    return {"previous": before, "current": after, "comparisons": comparisons,
        "calendar_end_is_exchange_close": False, "cross_timeframe_decision": "NOT_EVALUATED",
        "calendar_verified": False, "source_qualified": False, "pit_qualified": False,
        "holding_management_authorized": False, "execution_authorized": False,
        "limitations": ["calendar_rollover_is_not_a_new_price_observation",
            "different_period_ends_are_not_aligned_indicator_changes",
            "first_period_truncation_and_within_period_session_coverage_are_unverified",
            "open_missing_or_suspended_periods_are_never_filled_or_finalized",
            "weekly_monthly_contexts_are_correlated_not_independent_votes"]}


def read_equity_change_digest(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, subject: str, market: Market,
    *, previous_as_of: datetime, as_of: datetime, maximum_age_seconds: int,
    previous_parameters: TechnicalParameters | None = None,
    current_parameters: TechnicalParameters | None = None,
    include_period_context: bool = False,
    maximum_native_capture_age_seconds: int | None = None,
) -> dict[str, Any]:
    """Read both cutoffs in one DB snapshot; retain current failures without fallback."""
    require_timezone(previous_as_of, "previous change cutoff")
    require_timezone(as_of, "current change cutoff")
    try:
        start, end = previous_as_of.astimezone(UTC), as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("change comparison cutoff outside UTC bounds") from None
    if start >= end:
        raise ValueError("change cutoffs must be strictly increasing in actual UTC")
    if type(maximum_age_seconds) is not int or maximum_age_seconds <= 0:
        raise ValueError("change comparison requires an explicit positive observation-age limit")
    if type(include_period_context) is not bool:
        raise ValueError("period context opt-in must be boolean")
    if maximum_native_capture_age_seconds is not None and (
        type(maximum_native_capture_age_seconds) is not int
        or maximum_native_capture_age_seconds <= 0
    ):
        raise ValueError("native change requires a positive integer capture-age limit")
    if type(market) is not Market:
        raise ValueError("change comparison requires an explicit market")
    validate_yahoo_equity_subject(market, subject)
    if not store.read_only:
        raise ValueError("change comparison requires a read-only existing store")
    old_parameters = TechnicalParameters() if previous_parameters is None else previous_parameters
    new_parameters = TechnicalParameters() if current_parameters is None else current_parameters
    for parameters in (old_parameters, new_parameters):
        if type(parameters) is not TechnicalParameters:
            raise ValueError("change comparison requires typed technical parameters")
        parameters.__post_init__()
    with store.read_snapshot():
        previous = read_global_price_inputs(store, artifacts, subject, market, as_of=start,
                                           maximum_age_seconds=maximum_age_seconds)
        current = read_global_price_inputs(store, artifacts, subject, market, as_of=end,
                                          maximum_age_seconds=maximum_age_seconds)
        for snapshot, cutoff in ((previous, start), (current, end)):
            if (snapshot.subject != subject or snapshot.market is not market
                    or snapshot.as_of.astimezone(UTC) != cutoff):
                raise ValueError("change snapshot identity or cutoff mismatch")
        old_frame = _frame(previous, old_parameters)
        new_frame = _frame(current, new_parameters)
        native_context = (read_native_fundamental_change_digest(store, artifacts, subject, market,
            previous_as_of=start, as_of=end,
            maximum_capture_age_seconds=maximum_native_capture_age_seconds)
            if maximum_native_capture_age_seconds is not None else None)
    reasons = []
    for name, snapshot in (("previous", previous), ("current", current)):
        if snapshot.status != "observed_unqualified" or not snapshot.bars:
            reasons.append(f"{name}_price_inputs_unavailable:{snapshot.status}")
        if snapshot.freshness != "WITHIN_LIMIT":
            reasons.append(f"{name}_observation_age_not_within_configured_limit")
    if asdict(old_parameters) != asdict(new_parameters):
        reasons.append("technical_parameters_changed")
    previous_context, current_context = _context(previous), _context(current)
    same_context = previous_context == current_context
    if previous.bars and current.bars and not same_context:
        reasons.append("source_currency_exchange_or_price_basis_changed")
    if len(previous_context) > 1 or len(current_context) > 1:
        reasons.append("source_context_not_uniform")
    inspected = bool(previous.bars and current.bars and same_context)
    old_history = _history(previous) if inspected else {}
    new_history = _history(current) if inspected else {}
    last_previous = max(old_history, default=None)
    revised = sorted(key for key in old_history.keys() & new_history.keys()
                     if old_history[key] != new_history[key])
    missing = old_history.keys() - new_history.keys()
    historical_additions = sorted(key for key in new_history.keys() - old_history.keys()
                                 if last_previous is not None and key <= last_previous)
    if revised:
        reasons.append("overlapping_source_observations_revised")
    if previous.bars and current.bars and (missing or historical_additions):
        reasons.append("historical_coverage_changed")
    added = sorted(key for key in new_history.keys() - old_history.keys()
                   if last_previous is not None and key > last_previous)
    changes: list[dict[str, Any]] = []
    price_change = None
    status = "NOT_COMPARABLE"
    if not reasons:
        status = "NEW_PRICE_OBSERVATIONS" if added else "NO_NEW_PRICE_OBSERVATIONS"
        for field in _FIELDS:
            before, after = old_frame["diagnostics"][field], new_frame["diagnostics"][field]
            available = before not in _UNAVAILABLE and after not in _UNAVAILABLE
            for frame in (old_frame, new_frame):
                if field == "triple_average_events":
                    available &= "triple_average_warmup" not in frame["diagnostics"][
                        "technical_missing_inputs"].split(",")
                elif field == "granville_events":
                    available &= frame["diagnostics"]["granville_available"] is True
            changes.append({"field": field, "previous": before, "current": after,
                "comparison": ("NOT_EVALUATED" if not available else
                               "UNCHANGED" if before == after else "CHANGED")})
        if added:
            before, after = previous.bars[-1].close, current.bars[-1].close
            price_change = {"previous_close": str(before), "current_close": str(after),
                "absolute": str(after - before), "percent": float((after / before - 1) * 100),
                "meaning": "native_close_change_not_investment_or_total_return"}
    output = {"model_version": EQUITY_CHANGE_DIGEST_VERSION, "subject": subject,
        "market": market.value, "snapshot_scope": "single_read_only_database_snapshot",
        "comparison_status": status, "blocking_reasons": reasons,
        "previous": _summary(previous, old_frame), "current": _summary(current, new_frame),
        "same_selected_capture": (previous.selected_evidence_id == current.selected_evidence_id
                                  if previous.selected_evidence_id is not None else None),
        "series_comparison_evaluated": inspected,
        "new_observation_count": len(added) if inspected else None,
        "revised_overlap_count": len(revised) if inspected else None,
        "removed_observation_count": len(missing) if inspected else None,
        "historical_addition_count": len(historical_additions) if inspected else None,
        "revision_timestamp_examples": revised[:10], "price_change": price_change,
        "technical_changes": changes, "fundamental_comparison": "NOT_ASSESSED",
        "multi_timeframe_comparison": "NOT_ASSESSED", "holding_method": "NOT_VALIDATED",
        "research_only": True, "source_qualified": False, "pit_qualified": False,
        "scoring_authorized": False, "validation_authorized": False,
        "holding_management_authorized": False, "execution_authorized": False,
        "historical_replay_eligible": False, "research_report_created": False,
        "limitations": ["configured_age_is_not_verified_session_completion_or_production_freshness",
            "same_provider_snapshots_are_not_independent_confirmation",
            "source_adjustments_and_corporate_actions_remain_unverified",
            "no_new_observations_does_not_mean_business_unchanged_or_position_safe",
            "technical_changes_are_correlated_observations_not_votes_or_trade_signals"]}
    if include_period_context:
        output.update(model_version=EQUITY_PERIOD_CHANGE_DIGEST_VERSION,
            multi_timeframe_comparison="DESCRIPTIVE_WEEKLY_MONTHLY_CONTEXT",
            period_context=_period_context(previous, current, old_parameters, new_parameters,
                                           reasons))
    if native_context is not None:
        output.update(model_version=EQUITY_NATIVE_CHANGE_DIGEST_VERSION,
                      native_fundamental_context=native_context)
    reject_sensitive_structure(output)
    return {**output, "digest_hash": sha256(financial_input_json(output).encode()).hexdigest()}
