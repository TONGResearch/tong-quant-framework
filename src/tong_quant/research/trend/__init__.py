from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tong_quant.domain.enums import EvidenceQuality, ResearchModuleName
from tong_quant.domain.models import Bar
from tong_quant.research.base import assessment_from_scores, insufficient_assessment
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
)

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
    model_version: str = "trend-v0.5"
    breakout_period: int = 20
    volume_period: int = 20
    atr_period: int = 14
    confirmation_threshold: float = 60.0

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        required_bars = max(self.breakout_period, self.volume_period, self.atr_period) + 1
        bars = tuple(
            sorted(
                (
                    bar
                    for bar in context.bars
                    if bar.available_at <= context.as_of and not bar.is_suspended
                ),
                key=lambda bar: bar.timestamp,
            )
        )
        supplied = {
            name: context.evidence_named(self.module, name)
            for name in (
                "market_sentiment_confirmation",
                "industry_heat_confirmation",
            )
        }
        if len(bars) < required_bars or any(item is None for item in supplied.values()):
            available = tuple(item for item in supplied.values() if item is not None)
            return insufficient_assessment(
                module=self.module,
                evidence=available,
                required_names=TREND_FIELDS,
                as_of=context.as_of,
                limitations=(
                    f"Trend research requires {required_bars} visible daily bars",
                    "Point-in-time market sentiment and industry heat evidence are mandatory",
                ),
                model_version=self.model_version,
            )

        current = bars[-1]
        prior_breakout_bars = bars[-self.breakout_period - 1 : -1]
        prior_volume_bars = bars[-self.volume_period - 1 : -1]
        donchian_high = max(float(bar.high) for bar in prior_breakout_bars)
        breakout_score = _ratio_score(float(current.close), donchian_high)
        average_volume = sum(float(bar.volume) for bar in prior_volume_bars) / len(
            prior_volume_bars
        )
        volume_ratio = 0.0 if average_volume == 0 else float(current.volume) / average_volume
        volume_score = min(100.0, max(0.0, volume_ratio * 50.0))
        atr = _atr(bars, self.atr_period)
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
        return assessment_from_scores(
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
            ),
            model_version=self.model_version,
            features={
                **dependency_features,
                **{f"{name}_confirmed": value for name, value in confirmations.items()},
                "all_confirmations_present": all(confirmations.values()),
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


def _ratio_score(value: float, reference: float) -> float:
    if reference <= 0:
        return 0.0
    ratio = value / reference
    return min(100.0, max(0.0, 50.0 + (ratio - 1) * 1000.0))


def _atr(bars: Sequence[Bar], period: int) -> float:
    ranges: list[float] = []
    for previous, current in zip(bars[-period - 1 : -1], bars[-period:], strict=True):
        previous_close = float(previous.close)
        ranges.append(
            max(
                float(current.high) - float(current.low),
                abs(float(current.high) - previous_close),
                abs(float(current.low) - previous_close),
            )
        )
    return sum(ranges) / len(ranges)


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
