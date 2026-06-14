from dataclasses import dataclass, field
from datetime import datetime

from tong_quant.domain.enums import ScreeningDimensionName
from tong_quant.domain.models import require_timezone
from tong_quant.screening.models import DimensionAssessment


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    dimension: ScreeningDimensionName
    score: float
    confidence: float
    evaluated_at: datetime
    available_at: datetime
    reasons: tuple[str, ...]
    features: dict[str, float | int | str | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.evaluated_at, "evaluated_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at > self.evaluated_at:
            raise ValueError("dimension evidence cannot use future data")


@dataclass(frozen=True, slots=True)
class EvidenceDimensionEvaluator:
    dimension: ScreeningDimensionName
    source_id: str
    model_version: str = "v0.4"

    def evaluate(self, evidence: DimensionEvidence) -> DimensionAssessment:
        if evidence.dimension is not self.dimension:
            raise ValueError("evidence dimension does not match evaluator")
        return DimensionAssessment(
            dimension=self.dimension,
            score=evidence.score,
            confidence=evidence.confidence,
            evaluated_at=evidence.evaluated_at,
            available_at=evidence.available_at,
            reasons=evidence.reasons,
            source=self.source_id,
            model_version=self.model_version,
            features=evidence.features,
        )
