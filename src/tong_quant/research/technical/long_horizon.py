"""Unscored indicators on ended calendar observations, not verified exchange candles."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics
from tong_quant.research.technical.indicators import (
    KDJPoint,
    MACDPoint,
    TechnicalParameters,
    kdj,
    macd,
    sma,
)
from tong_quant.version import (
    LONG_HORIZON_DIAGNOSTICS_VERSION,
    MULTI_TIMEFRAME_DIAGNOSTICS_VERSION,
)


def _average_periods(periods: tuple[int, ...]) -> None:
    if (type(periods) is not tuple or not 1 <= len(periods) <= 8
            or any(type(value) is not int or not 1 <= value <= 1000 for value in periods)
            or len(set(periods)) != len(periods)):
        raise ValueError("long-horizon averages require bounded unique integer periods")


@dataclass(frozen=True, slots=True)
class LongHorizonParameters:
    monthly_sma_periods: tuple[int, ...] = (6, 12, 24)
    yearly_sma_periods: tuple[int, ...] = (3, 5, 10)
    indicators: TechnicalParameters = field(default_factory=TechnicalParameters)

    def __post_init__(self) -> None:
        for periods in (self.monthly_sma_periods, self.yearly_sma_periods):
            _average_periods(periods)
        if type(self.indicators) is not TechnicalParameters:
            raise ValueError("long-horizon indicators require typed technical parameters")
        self.indicators.__post_init__()
        if any(getattr(self.indicators, name) > 1000 for name in (
            "macd_fast", "macd_slow", "macd_signal", "kdj_period", "kdj_k", "kdj_d",
        )):
            raise ValueError("long-horizon indicator periods exceed calculation bounds")


@dataclass(frozen=True, slots=True)
class _PeriodPrices:
    high: Decimal
    low: Decimal
    close: Decimal


def _observations(frames: list[dict[str, Any]], *, frequency: str,
                  periods: tuple[int, ...], parameters: TechnicalParameters,
                  source_status: str) -> dict[str, Any]:
    closed = [item for item in frames if item["calendar_period_ended"]]
    blockers = [item["period_start_date"] for item in closed
                if item["status"] != "CALENDAR_PERIOD_ENDED_COVERAGE_UNVERIFIED"
                or item.get("underlying_month_gap_starts")]
    status = (source_status if source_status in {"MISSING", "SUSPENDED_LATEST"}
              else "BLOCKED_PERIOD_GAPS_OR_SUSPENSIONS" if blockers
              else "NO_ENDED_PERIODS" if not closed else "OBSERVED_UNQUALIFIED")
    # Never compact around a missing/suspended ended period, or use an open period.
    prices = tuple(_PeriodPrices(Decimal(item["ohlcv"]["high"]),
        Decimal(item["ohlcv"]["low"]), Decimal(item["ohlcv"]["close"]))
        for item in closed) if status == "OBSERVED_UNQUALIFIED" else ()
    closes = tuple(float(item.close) for item in prices)
    moving_averages = []
    for period in periods:
        value = sma(closes, period)[-1] if len(closes) >= period else None
        relation = (None if value is None else "ABOVE" if closes[-1] > value else
                    "BELOW" if closes[-1] < value else "EQUAL")
        moving_averages.append({"periods": period, "value": value,
            "close_relation": relation, "status": "OBSERVED_UNQUALIFIED" if value is not None
            else "INSUFFICIENT_HISTORY" if status == "OBSERVED_UNQUALIFIED" else status})
    macd_point = macd(closes, parameters)
    kdj_point = kdj(prices, parameters)
    def indicator(point: MACDPoint | KDJPoint | None, required: int) -> dict[str, Any]:
        return {"required_periods": required, "available_periods": len(prices),
            "status": "OBSERVED_UNQUALIFIED" if point is not None else
            "INSUFFICIENT_HISTORY" if status == "OBSERVED_UNQUALIFIED" else status,
            "values": asdict(point) if point is not None else None}
    return {
        "frequency": frequency, "status": status, "periods": frames,
        "ended_period_count": len(closed), "calculation_period_count": len(prices),
        "blocking_period_starts": blockers,
        "open_period_starts": [item["period_start_date"] for item in frames
                               if not item["calendar_period_ended"]],
        "last_ended_period_start": closed[-1]["period_start_date"] if closed else None,
        "last_ended_close": str(prices[-1].close) if prices else None,
        "moving_averages": moving_averages,
        "macd": indicator(macd_point, parameters.macd_slow + parameters.macd_signal),
        "kdj": indicator(kdj_point, parameters.kdj_period + 1),
        "session_coverage": "UNVERIFIED", "source_qualification": "NOT_ADMITTED",
    }


def long_horizon_diagnostics(
    bars: tuple[Bar, ...], *, market: Market, as_of: datetime,
    parameters: LongHorizonParameters | None = None,
    weekly_sma_periods: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    parameters = LongHorizonParameters() if parameters is None else parameters
    if type(parameters) is not LongHorizonParameters or type(market) is not Market:
        raise ValueError("long-horizon diagnostics require typed parameters and market")
    parameters.__post_init__()
    if weekly_sma_periods is not None:
        _average_periods(weekly_sma_periods)
    calendar = calendar_period_diagnostics(bars, market=market, as_of=as_of, include_yearly=True)
    month_gaps = [item["period_start_date"] for item in calendar["monthly"]
                  if item["calendar_period_ended"]
                  and item["status"] != "CALENDAR_PERIOD_ENDED_COVERAGE_UNVERIFIED"]
    if calendar["monthly"]:
        first_month = date.fromisoformat(calendar["monthly"][0]["period_start_date"])
        month_gaps.extend(date(first_month.year, month, 1).isoformat()
                          for month in range(1, first_month.month))
    yearly = [{**item, "underlying_month_gap_starts": sorted(
        value for value in month_gaps if value[:4] == item["period_start_date"][:4])}
        for item in calendar["yearly"]]
    document: dict[str, Any] = {
        "model_version": LONG_HORIZON_DIAGNOSTICS_VERSION,
        "subject": calendar["subject"], "market": market.value, "as_of": as_of.astimezone(UTC),
        "parameters": asdict(parameters), "calendar_input_hash": calendar["input_hash"],
        "source_bars_content_hash": sha256(financial_input_json(
            [asdict(bar) for bar in bars]).encode()).hexdigest(),
        "supplied_daily_row_count": len(bars),
        "status": calendar["status"], "computed_indicators": ("SMA", "MACD", "KDJ"),
        "monthly": _observations(calendar["monthly"], frequency="monthly",
            periods=parameters.monthly_sma_periods, parameters=parameters.indicators,
            source_status=calendar["status"]),
        "yearly": _observations(yearly, frequency="yearly",
            periods=parameters.yearly_sma_periods, parameters=parameters.indicators,
            source_status=calendar["status"]),
        "research_only": True, "calendar_verified": False,
        "source_adjustment_basis_verified": False, "source_freshness": "UNASSESSED",
        "source_trust": "NOT_ASSESSED", "scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False, "holding_management_authorized": False,
        "investment_scoring_authorized": False,
        "holding_horizon": "NOT_ESTIMATED", "cross_timeframe_decision": "NOT_EVALUATED",
        "limitations": (
            "Ended calendar observations are not verified complete exchange candles",
            "Unknown within-period coverage, adjustment basis and first-period truncation remain",
            "Missing or suspended ended periods block calculations without favorable fallback",
            "Open periods never enter indicators; samples count months/years, not daily rows",
            "Shared indicator formulas and research defaults are not approved trading rules",
            "Different timeframes are correlated, not independent votes or extra confidence",
            "No Granville/Turtle/setup migration, score, holding duration or trade instruction",
        ),
    }
    if weekly_sma_periods is not None:
        daily_reference = max((bar.timestamp for bar in bars), default=None,
                              key=lambda value: value.astimezone(UTC))
        alignment = []
        for frequency, frames in (("weekly", calendar["weekly"]),
                                  ("monthly", calendar["monthly"]), ("yearly", yearly)):
            ended = [frame for frame in frames if frame["calendar_period_ended"]]
            latest = ended[-1] if ended else None
            source_at = latest["last_observed_at"] if latest else None
            alignment.append({
                "frequency": frequency,
                "last_ended_period_start": latest["period_start_date"] if latest else None,
                "calendar_end_at": latest["calendar_end_at"] if latest else None,
                "last_source_observed_at": source_at,
                "latest_source_available_at": latest["latest_available_at"] if latest else None,
                "lag_to_daily_observation_seconds": (
                    daily_reference.astimezone(UTC) - source_at.astimezone(UTC)
                ).total_seconds() if daily_reference is not None and source_at is not None
                else None,
                "period_status": latest["status"] if latest else (
                    calendar["status"] if calendar["status"] != "OBSERVED_UNQUALIFIED"
                    else "NO_ENDED_PERIODS"),
            })
        document.update(
            model_version=MULTI_TIMEFRAME_DIAGNOSTICS_VERSION,
            weekly_sma_periods=weekly_sma_periods,
            weekly=_observations(calendar["weekly"], frequency="weekly",
                periods=weekly_sma_periods, parameters=parameters.indicators,
                source_status=calendar["status"]),
            timeframe_alignment={
                "as_of": as_of.astimezone(UTC), "daily_reference_observed_at": daily_reference,
                "periods": alignment, "calendar_end_is_exchange_close": False,
                "freshness": "UNASSESSED", "comparison_eligible": False,
                "interpretation": "SAME_CUTOFF_DOES_NOT_MEAN_SAME_PERIOD_OR_INDEPENDENT_VOTES",
            },
        )
    reject_sensitive_structure(document)
    return {**document, "input_hash": sha256(financial_input_json(document).encode()).hexdigest()}
