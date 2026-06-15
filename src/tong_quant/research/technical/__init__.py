from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from tong_quant.domain.enums import EvidenceQuality, ResearchModuleName
from tong_quant.domain.models import Bar
from tong_quant.research.base import assessment_from_scores, insufficient_assessment
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
)

TECHNICAL_FIELDS = frozenset(
    {
        "long_term_trend",
        "weekly_trend",
        "monthly_trend",
        "moving_average_alignment",
        "position_52_week",
    }
)


@dataclass(frozen=True, slots=True)
class TechnicalResearchModule:
    module: ResearchModuleName = ResearchModuleName.TECHNICAL
    dependencies: frozenset[ResearchModuleName] = frozenset()
    model_version: str = "technical-v0.5"
    short_ma_period: int = 50
    long_ma_period: int = 200
    position_period: int = 252

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        del dependencies
        minimum = max(self.long_ma_period, self.position_period)
        bars = _usable_bars(context.bars, context.as_of)
        if len(bars) < minimum:
            return insufficient_assessment(
                module=self.module,
                evidence=(),
                required_names=TECHNICAL_FIELDS,
                as_of=context.as_of,
                limitations=(
                    f"Technical research requires at least {minimum} visible daily bars",
                ),
                model_version=self.model_version,
            )

        close = float(bars[-1].close)
        short_ma = _mean_close(bars[-self.short_ma_period :])
        long_ma = _mean_close(bars[-self.long_ma_period :])
        weekly_return = _return(bars, 5)
        monthly_return = _return(bars, 21)
        long_return = _return(bars, self.long_ma_period)
        recent = bars[-self.position_period :]
        high_52_week = max(float(bar.high) for bar in recent)
        low_52_week = min(float(bar.low) for bar in recent)
        position = _position(close, low_52_week, high_52_week)

        scores = {
            "long_term_trend": _return_score(long_return),
            "weekly_trend": _return_score(weekly_return),
            "monthly_trend": _return_score(monthly_return),
            "moving_average_alignment": _ma_score(close, short_ma, long_ma),
            "position_52_week": position,
        }
        evidence = tuple(
            _derived_evidence(name, value, bars[-1], context.as_of, self.model_version)
            for name, value in scores.items()
        )
        return assessment_from_scores(
            module=self.module,
            scores=tuple(scores.values()),
            evidence=evidence,
            required_names=TECHNICAL_FIELDS,
            as_of=context.as_of,
            findings=(
                f"Latest close {close:.4f}; {self.short_ma_period}-day average {short_ma:.4f}",
                f"{self.long_ma_period}-day average {long_ma:.4f}; "
                f"52-week position {position:.1f}",
            ),
            risks=(
                "Technical relationships can reverse and do not establish business value",
            ),
            limitations=(
                "Daily bars approximate weekly and monthly trend; no intraday evidence is used",
            ),
            model_version=self.model_version,
            features={
                "latest_close": close,
                "short_moving_average": round(short_ma, 6),
                "long_moving_average": round(long_ma, 6),
                "weekly_return": round(weekly_return, 6),
                "monthly_return": round(monthly_return, 6),
                "long_term_return": round(long_return, 6),
                "high_52_week": high_52_week,
                "low_52_week": low_52_week,
                "position_52_week": round(position, 4),
            },
        )


def _usable_bars(bars: Sequence[Bar], as_of: datetime) -> tuple[Bar, ...]:
    return tuple(
        sorted(
            (
                bar
                for bar in bars
                if bar.available_at <= as_of and not bar.is_suspended
            ),
            key=lambda bar: bar.timestamp,
        )
    )


def _mean_close(bars: Sequence[Bar]) -> float:
    return sum(float(bar.close) for bar in bars) / len(bars)


def _return(bars: Sequence[Bar], period: int) -> float:
    earlier = float(bars[-period].close)
    return 0.0 if earlier == 0 else float(bars[-1].close) / earlier - 1


def _return_score(value: float) -> float:
    return min(100.0, max(0.0, 50.0 + value * 250.0))


def _ma_score(close: float, short_ma: float, long_ma: float) -> float:
    if close > short_ma > long_ma:
        return 100.0
    if close > long_ma:
        return 65.0
    if close > short_ma:
        return 45.0
    return 20.0


def _position(close: float, low: float, high: float) -> float:
    if high == low:
        return 50.0
    return min(100.0, max(0.0, 100 * (close - low) / (high - low)))


def _derived_evidence(
    name: str,
    value: float,
    bar: Bar,
    as_of: datetime,
    model_version: str,
) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=f"technical:{name}:{bar.timestamp.date().isoformat()}",
        module=ResearchModuleName.TECHNICAL,
        name=name,
        value=round(value, 6),
        observed_at=bar.timestamp,
        available_at=min(bar.available_at, as_of),
        source="derived:daily_bars",
        quality=EvidenceQuality.PRIMARY,
        calculation_version=model_version,
    )


__all__ = ["TechnicalResearchModule"]
