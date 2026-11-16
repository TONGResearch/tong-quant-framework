"""Explicit retained Nasdaq source co-review, never canonical calendar population."""

from datetime import UTC, date
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.nasdaq_calendar_inputs import read_nasdaq_calendar_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.version import NASDAQ_PRICE_REVIEW_VERSION


def read_nasdaq_price_review(
    prices: GlobalPriceInputs, store: SQLiteStore, artifacts: FileSystemArtifactStore,
    year: int, *, maximum_source_age_seconds: int, shared_database: bool,
) -> dict[str, Any]:
    """Use retained-source readers; a hash alone cannot authenticate arbitrary caller JSON."""
    if prices.market is not Market.US or type(shared_database) is not bool:
        raise ValueError("Nasdaq co-review requires explicit US price and snapshot scope")
    if type(maximum_source_age_seconds) is not int or maximum_source_age_seconds <= 0:
        raise ValueError("Nasdaq co-review requires a positive explicit source age limit")
    if any(bar.instrument.market is not prices.market or bar.instrument.symbol != prices.subject
           for bar in prices.bars):
        raise ValueError("Nasdaq co-review price identity mismatch")
    bars = checked_daily_bars(prices.bars, as_of=prices.as_of, require_latest_active=True)
    source = read_nasdaq_calendar_inputs(store, artifacts, year, as_of=prices.as_of,
        maximum_source_age_seconds=maximum_source_age_seconds)
    zone = ZoneInfo("America/New_York")
    observed = {bar.timestamp.astimezone(zone).date() for bar in bars}
    cutoff_date = prices.as_of.astimezone(zone).date()
    comparisons = []
    for declaration in source["declarations"]:
        day = date.fromisoformat(declaration["trade_date"])
        future = day > cutoff_date
        in_span = bool(observed) and min(observed) <= day <= max(observed)
        comparisons.append({**declaration, "future_schedule_date": future,
            "within_price_observation_span": in_span,
            "price_date_observed": day in observed if not future and observed else None,
            "closed_date_observation_conflict": (
                day in observed and declaration["is_open"] is False and not future),
            "missing_open_observation_assessed": False,
            "actual_session_verified": False})
    document = {"model_version": NASDAQ_PRICE_REVIEW_VERSION,
        "subject": prices.subject, "market": prices.market.value,
        "as_of": prices.as_of.astimezone(UTC),
        "price_input_hash": prices.document()["input_hash"], "source": source,
        "snapshot_scope": ("single_database_snapshot" if shared_database else
                           "separate_database_snapshots_shared_cutoff"),
        "status": "SOURCE_OBSERVATION_ONLY", "declaration_comparisons": comparisons,
        "exchange_pairing_status": "NASDAQ_SOURCE_PRICE_VENUE_UNVERIFIED",
        "cross_store_atomicity_verified": False, "exchange_binding_verified": False,
        "calendar_complete": False, "canonical_calendar_authorized": False,
        "session_completeness_verified": False, "scoring_authorized": False,
        "investment_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "limitations": (
            "Explicit source selection does not verify instrument venue or session semantics",
            "Only current declarations under the caller source-age limit are compared",
            "Stale/failed/future/ambiguous source observations remain retained, never fallback",
            "Future early-close dates retain native times, not observed session completion",
            "Missing early-close price dates are not classified without price/lifecycle review",
            "No weekday inference, TradingSession conversion, coverage repair or PIT promotion",
            "Shared cutoff is not cross-database atomicity, source truth or provider calibration",
        )}
    reject_sensitive_structure(document)
    return {**document, "input_hash": sha256(financial_input_json(document).encode()).hexdigest()}
