from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.price_evidence import daily_bar_content
from tong_quant.domain.enums import EvidenceQuality, ResearchConclusion, ResearchModuleName
from tong_quant.domain.models import Bar
from tong_quant.research.bar_inputs import checked_daily_bars, require_period, research_daily_bars
from tong_quant.research.base import (
    assessment_from_scores,
    conclusion_for_score,
    evidence_score,
    insufficient_assessment,
)
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
    ResearchValue,
)
from tong_quant.research.technical.indicators import atr as calculate_atr
from tong_quant.version import TREND_PRICE_OBSERVATIONS_VERSION, TREND_RESEARCH_VERSION

TREND_FIELDS = frozenset(
    {
        "breakout_confirmation",
        "volume_confirmation",
        "market_sentiment_confirmation",
        "industry_heat_confirmation",
    }
)


@dataclass(frozen=True, slots=True)
class TrendResearchModule:
    module: ResearchModuleName = ResearchModuleName.TREND
    dependencies: frozenset[ResearchModuleName] = frozenset(
        {
            ResearchModuleName.POLICY,
            ResearchModuleName.INDUSTRY,
            ResearchModuleName.TECHNICAL,
        }
    )
    model_version: str = TREND_RESEARCH_VERSION
    breakout_period: int = 20
    volume_period: int = 20
    atr_period: int = 14
    confirmation_threshold: float = 60.0

    def __post_init__(self) -> None:
        for name in ("breakout_period", "volume_period", "atr_period"):
            require_period(name, getattr(self, name))
        if (
            type(self.confirmation_threshold) not in {float, int}
            or not isfinite(self.confirmation_threshold)
            or not 0 <= self.confirmation_threshold <= 100
        ):
            raise ValueError("confirmation threshold must be finite and between 0 and 100")

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        required_bars = max(self.breakout_period, self.volume_period, self.atr_period) + 1
        bars = research_daily_bars(context, require_latest_active=True)
        supplied = {
            name: context.evidence_named(self.module, name)
            for name in (
                "market_sentiment_confirmation",
                "industry_heat_confirmation",
            )
        }
        if (len(bars) < required_bars
                or any(evidence_score(item) is None for item in supplied.values())):
            available = tuple(item for item in supplied.values() if item is not None)
            return insufficient_assessment(
                module=self.module,
                evidence=available,
                required_names=TREND_FIELDS,
                as_of=context.as_of,
                limitations=(
                    f"Trend research requires {required_bars} visible daily bars",
                    "Numeric point-in-time market sentiment and industry heat are mandatory",
                    "The latest supplied observation must be active; no pre-suspension fallback",
                ),
                model_version=self.model_version,
            )

        current = bars[-1]
        geometry = _price_geometry(bars, self.breakout_period, self.volume_period, self.atr_period)
        donchian_high, breakout = geometry.donchian_high, geometry.breakout
        breakout_score = geometry.breakout_score
        volume_ratio, volume_score, atr = geometry.volume_ratio, geometry.volume_score, geometry.atr
        if volume_ratio is None or volume_score is None or atr is None:
            return insufficient_assessment(
                module=self.module, evidence=tuple(item for item in supplied.values()
                                                  if item is not None),
                required_names=TREND_FIELDS, as_of=context.as_of,
                limitations=("Positive prior volume is required for volume confirmation",),
                model_version=self.model_version,
            )
        derived = (
            _evidence("breakout_confirmation", breakout_score, current, self.model_version),
            _evidence("volume_confirmation", volume_score, current, self.model_version),
        )
        external = tuple(item for item in supplied.values() if item is not None)
        evidence = derived + external
        scores = tuple(
            float(item.value)
            for item in evidence
            if isinstance(item.value, (int, float))
        )
        confirmations = {
            item.name: bool(
                isinstance(item.value, (int, float))
                and float(item.value) >= self.confirmation_threshold
            )
            for item in evidence
        }
        dependency_features = {
            f"{name.value}_conclusion": assessment.conclusion.value
            for name, assessment in dependencies.items()
        }
        latest_close = float(current.close)
        result = assessment_from_scores(
            module=self.module,
            scores=scores,
            evidence=evidence,
            required_names=TREND_FIELDS,
            as_of=context.as_of,
            findings=(
                f"{sum(confirmations.values())} of 4 research confirmations meet the threshold",
                f"Donchian reference {donchian_high:.4f}; volume ratio {volume_ratio:.2f}",
            ),
            risks=(
                "Breakouts can fail even when all research confirmations agree",
                "ATR scenarios describe risk geometry and are not position instructions",
            ),
            limitations=(
                "No order, entry decision, or live position sizing is produced",
                "Observed dates are not verified sessions or authenticated PIT price coverage",
                "Four confirmations are conjunctive; strong components cannot offset a failure",
                "External quality labels do not authenticate sentiment or industry sources",
            ),
            model_version=self.model_version,
            features={
                **dependency_features,
                **{f"{name}_confirmed": value for name, value in confirmations.items()},
                "all_confirmations_present": all(confirmations.values()) and breakout,
                "all_confirmations_satisfied": all(confirmations.values()) and breakout,
                "trend_setup_valid": all(confirmations.values()) and breakout,
                "strict_donchian_breakout": breakout,
                "donchian_high": round(donchian_high, 6),
                "volume_ratio": round(volume_ratio, 6),
                "atr": round(atr, 6),
                "atr_stop_reference": round(latest_close - 2 * atr, 6),
                "trailing_reference": round(
                    max(float(bar.close) for bar in bars[-self.breakout_period :]) - 2 * atr,
                    6,
                ),
                "pyramid_scenario_levels": ",".join(
                    f"{latest_close + atr * step:.6f}" for step in (0.5, 1.0, 1.5)
                ),
                "framework_only": True,
            },
        )
        if not result.features["trend_setup_valid"]:
            return replace(result, conclusion=ResearchConclusion.CAUTION, score=None)
        return replace(result, score=round(min(scores), 4),
                       conclusion=conclusion_for_score(min(scores)))

    def price_observations(self, supplied: tuple[Bar, ...], *,
                           as_of: datetime) -> dict[str, ResearchValue]:
        """Expose existing price geometry only; no external confirmations or setup approval."""
        self.__post_init__()
        bars = checked_daily_bars(supplied, as_of=as_of, require_latest_active=True)
        latest = max(supplied, key=lambda bar: (
            bar.timestamp.astimezone(UTC), bar.available_at.astimezone(UTC)), default=None)
        required = max(self.breakout_period, self.volume_period, self.atr_period) + 1
        parameters = {"breakout_period": self.breakout_period, "volume_period": self.volume_period,
            "atr_period": self.atr_period, "confirmation_threshold": self.confirmation_threshold}
        output: dict[str, ResearchValue] = {
            "model_version": TREND_PRICE_OBSERVATIONS_VERSION,
            "as_of": as_of.astimezone(UTC).isoformat(),
            "subject": latest.instrument.symbol if latest else None,
            "market": latest.instrument.market.value if latest else None,
            "last_supplied_observed_at": latest.timestamp.astimezone(UTC).isoformat()
            if latest else None,
            "last_supplied_available_at": latest.available_at.astimezone(UTC).isoformat()
            if latest else None,
            "parameters_json": financial_input_json(parameters), "required_observations": required,
            "usable_observations": len(bars),
            "status": "SUSPENDED_LATEST" if latest and latest.is_suspended else
            "INSUFFICIENT_DATA" if bars else "MISSING",
            "latest_close": None, "prior_channel_high": None,
            "strict_breakout_observed": None, "breakout_threshold_observed": None,
            "prior_average_volume": None, "latest_volume": None, "volume_ratio": None,
            "volume_threshold_observed": None, "atr": None,
            "market_sentiment_confirmation": None, "industry_heat_confirmation": None,
            "four_confirmations_complete": False, "research_only": True,
            "scoring_authorized": False, "validation_authorized": False,
            "historical_replay_eligible": False, "execution_authorized": False,
            "source_qualification": "NOT_ASSESSED", "freshness": "UNASSESSED",
            "bar_input_hash": sha256(financial_input_json(
                [daily_bar_content(bar) for bar in supplied]).encode()).hexdigest(),
        }
        if len(bars) >= required:
            geometry = _price_geometry(bars, self.breakout_period, self.volume_period,
                                       self.atr_period)
            output.update(status="OBSERVED_UNQUALIFIED" if geometry.volume_ratio is not None
                          else "ZERO_PRIOR_VOLUME",
                latest_close=float(bars[-1].close), prior_channel_high=geometry.donchian_high,
                strict_breakout_observed=geometry.breakout,
                breakout_threshold_observed=geometry.breakout and (
                    geometry.breakout_score >= self.confirmation_threshold),
                prior_average_volume=geometry.average_volume, latest_volume=float(bars[-1].volume),
                volume_ratio=geometry.volume_ratio, volume_threshold_observed=(
                    geometry.volume_score >= self.confirmation_threshold
                    if geometry.volume_score is not None else None), atr=geometry.atr)
        return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}


@dataclass(frozen=True, slots=True)
class _PriceGeometry:
    donchian_high: float
    breakout: bool
    breakout_score: float
    average_volume: float
    volume_ratio: float | None
    volume_score: float | None
    atr: float | None


def _price_geometry(bars: Sequence[Bar], breakout_period: int, volume_period: int,
                    atr_period: int) -> _PriceGeometry:
    current = bars[-1]
    high = max(float(bar.high) for bar in bars[-breakout_period - 1:-1])
    breakout = float(current.close) > high
    breakout_score = _ratio_score(float(current.close), high) if breakout else 0.0
    prior_volume = bars[-volume_period - 1:-1]
    average = sum(float(bar.volume) for bar in prior_volume) / len(prior_volume)
    ratio = float(current.volume) / average if average > 0 else None
    return _PriceGeometry(high, breakout, breakout_score, average, ratio,
        min(100.0, max(0.0, ratio * 50.0)) if ratio is not None else None,
        _atr(bars, atr_period) if ratio is not None else None)


def _ratio_score(value: float, reference: float) -> float:
    if reference <= 0:
        return 0.0
    ratio = value / reference
    return min(100.0, max(0.0, 50.0 + (ratio - 1) * 1000.0))


def _atr(bars: Sequence[Bar], period: int) -> float:
    value = calculate_atr(bars, period)
    if value is None:
        raise ValueError("ATR requires a previous close for every true range")
    return value


def _evidence(
    name: str,
    value: float,
    bar: Bar,
    model_version: str,
) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=f"trend:{name}:{bar.timestamp.date().isoformat()}",
        module=ResearchModuleName.TREND,
        name=name,
        value=round(value, 6),
        observed_at=bar.timestamp,
        available_at=bar.available_at,
        source="derived:daily_bars",
        quality=EvidenceQuality.PRIMARY,
        calculation_version=model_version,
    )


__all__ = ["TrendResearchModule"]
