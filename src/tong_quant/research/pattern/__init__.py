from collections.abc import Mapping
from dataclasses import dataclass

from tong_quant.domain.enums import (
    EvidenceQuality,
    Market,
    ResearchModuleName,
)
from tong_quant.domain.models import Bar
from tong_quant.research.base import (
    assessment_from_scores,
    insufficient_assessment,
    not_applicable_assessment,
)
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
)

PATTERN_FIELDS = frozenset(
    {
        "rising_stocks_environment",
        "high_volume_long_upper_shadow",
        "first_board_second_board",
        "strong_stock_pullback",
        "vwap_support",
        "opening_price_support",
        "low_volume_pullback",
    }
)


@dataclass(frozen=True, slots=True)
class PatternResearchModule:
    module: ResearchModuleName = ResearchModuleName.PATTERN
    dependencies: frozenset[ResearchModuleName] = frozenset(
        {ResearchModuleName.INDUSTRY, ResearchModuleName.TECHNICAL}
    )
    model_version: str = "pattern-china-a-v0.5"
    rising_stocks_threshold: int = 3000
    volume_period: int = 20

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        instrument = context.queue_entry.candidate.instrument
        if instrument.market is not Market.CHINA_A:
            return not_applicable_assessment(
                module=self.module,
                as_of=context.as_of,
                reason="The V0.5 pattern framework is specific to China A-shares",
                model_version=self.model_version,
            )

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
        supplied_names = PATTERN_FIELDS - {"high_volume_long_upper_shadow"}
        supplied = tuple(
            item
            for name in supplied_names
            if (item := context.evidence_named(self.module, name)) is not None
        )
        if len(bars) < self.volume_period + 1 or len(supplied) != len(supplied_names):
            return insufficient_assessment(
                module=self.module,
                evidence=supplied,
                required_names=PATTERN_FIELDS,
                as_of=context.as_of,
                limitations=(
                    "A-share pattern research requires complete point-in-time market "
                    "breadth and intraday pattern evidence",
                    f"At least {self.volume_period + 1} visible daily bars are required",
                ),
                model_version=self.model_version,
            )

        derived = _upper_shadow_evidence(bars, self.volume_period, self.model_version)
        evidence = (derived, *supplied)
        scores = tuple(
            float(item.value)
            for item in evidence
            if isinstance(item.value, (int, float))
        )
        rising = context.evidence_named(self.module, "rising_stocks_environment")
        rising_count = None if rising is None else rising.metadata.get("rising_stocks")
        dependency_features = {
            f"{name.value}_conclusion": assessment.conclusion.value
            for name, assessment in dependencies.items()
        }
        return assessment_from_scores(
            module=self.module,
            scores=scores,
            evidence=evidence,
            required_names=PATTERN_FIELDS,
            as_of=context.as_of,
            findings=(
                "A-share-specific pattern evidence was evaluated without creating a trade decision",
                f"Rising-stock reference threshold is {self.rising_stocks_threshold}",
            ),
            risks=(
                "Short-term patterns are sensitive to microstructure and policy changes",
                "Intraday evidence can become stale quickly",
            ),
            limitations=(
                "Entry timing windows remain research annotations, not execution rules",
            ),
            model_version=self.model_version,
            features={
                **dependency_features,
                "rising_stocks": rising_count,
                "rising_stocks_threshold": self.rising_stocks_threshold,
                "china_a_specific": True,
            },
        )


def _upper_shadow_evidence(
    bars: tuple[Bar, ...],
    volume_period: int,
    model_version: str,
) -> ResearchEvidence:
    current = bars[-1]
    average_volume = sum(float(bar.volume) for bar in bars[-volume_period - 1 : -1]) / (
        volume_period
    )
    body_top = max(float(current.open), float(current.close))
    full_range = float(current.high) - float(current.low)
    upper_shadow_ratio = (
        0.0 if full_range == 0 else (float(current.high) - body_top) / full_range
    )
    volume_ratio = 0.0 if average_volume == 0 else float(current.volume) / average_volume
    score = min(100.0, upper_shadow_ratio * 100 * min(volume_ratio, 2.0) / 2.0)
    return ResearchEvidence(
        evidence_id=f"pattern:upper-shadow:{current.timestamp.date().isoformat()}",
        module=ResearchModuleName.PATTERN,
        name="high_volume_long_upper_shadow",
        value=round(score, 6),
        observed_at=current.timestamp,
        available_at=current.available_at,
        source="derived:daily_bars",
        quality=EvidenceQuality.PRIMARY,
        calculation_version=model_version,
        metadata={
            "upper_shadow_ratio": round(upper_shadow_ratio, 6),
            "volume_ratio": round(volume_ratio, 6),
        },
    )


__all__ = ["PatternResearchModule"]
