from collections.abc import Mapping
from dataclasses import dataclass, replace

from tong_quant.domain.enums import (
    EvidenceQuality,
    Market,
    ResearchConclusion,
    ResearchModuleName,
)
from tong_quant.domain.models import Bar
from tong_quant.research.bar_inputs import require_period, research_daily_bars
from tong_quant.research.base import (
    assessment_from_scores,
    evidence_score,
    insufficient_assessment,
    not_applicable_assessment,
)
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
)
from tong_quant.version import PATTERN_RESEARCH_VERSION

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
    model_version: str = PATTERN_RESEARCH_VERSION
    rising_stocks_threshold: int = 3000
    volume_period: int = 20

    def __post_init__(self) -> None:
        require_period("volume_period", self.volume_period)
        require_period("rising_stocks_threshold", self.rising_stocks_threshold)

    def evaluate(
        self,
        context: ResearchContext,
        dependencies: Mapping[ResearchModuleName, ResearchAssessment],
    ) -> ResearchAssessment:
        context.validate()
        instrument = context.queue_entry.candidate.instrument
        if instrument.market is not Market.CHINA_A:
            return not_applicable_assessment(
                module=self.module,
                as_of=context.as_of,
                reason="The V0.5 pattern framework is specific to China A-shares",
                model_version=self.model_version,
            )

        bars = research_daily_bars(context, require_latest_active=True)
        supplied_names = PATTERN_FIELDS - {"high_volume_long_upper_shadow"}
        supplied = tuple(
            item
            for name in supplied_names
            if (item := context.evidence_named(self.module, name)) is not None
        )
        rising = context.evidence_named(self.module, "rising_stocks_environment")
        rising_count = None if rising is None else rising.metadata.get("rising_stocks")
        if (len(bars) < self.volume_period + 1 or len(supplied) != len(supplied_names)
                or any(evidence_score(item) is None for item in supplied)
                or type(rising_count) is not int or rising_count < 0):
            return insufficient_assessment(
                module=self.module,
                evidence=supplied,
                required_names=PATTERN_FIELDS,
                as_of=context.as_of,
                limitations=(
                    "A-share pattern research requires complete point-in-time market "
                    "breadth and intraday pattern evidence",
                    "An explicit nonnegative integer rising-stock count is required",
                    f"At least {self.volume_period + 1} visible daily bars are required",
                    "The latest supplied observation must be active; no pre-suspension fallback",
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
        dependency_features = {
            f"{name.value}_conclusion": assessment.conclusion.value
            for name, assessment in dependencies.items()
        }
        result = assessment_from_scores(
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
                "Observed dates are not verified sessions or authenticated PIT price coverage",
            ),
            model_version=self.model_version,
            features={
                **dependency_features,
                "rising_stocks": rising_count,
                "rising_stocks_threshold": self.rising_stocks_threshold,
                "rising_stocks_environment_satisfied": rising_count > self.rising_stocks_threshold,
                "china_a_specific": True,
            },
        )
        if rising_count <= self.rising_stocks_threshold:
            return replace(result, score=None, conclusion=ResearchConclusion.CAUTION,
                           limitations=(*result.limitations,
                                        "Rising-stock count must strictly exceed the threshold"))
        return result


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
