from dataclasses import dataclass
from datetime import UTC, datetime

from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.models import (
    FrameworkSnapshot,
    OutOfSamplePolicy,
    ValidationRequest,
    WalkForwardPolicy,
)
from tong_quant.validation.replay.models import HistoricalReplayResult
from tong_quant.version import RESEARCH_ENGINE_VERSION, VALIDATION_ENGINE_VERSION


@dataclass(frozen=True, slots=True)
class ValidationRequestFactory:
    validation_version: str = VALIDATION_ENGINE_VERSION

    def build(
        self,
        result: HistoricalReplayResult,
        *,
        validation_id: str,
        modules: tuple[ValidationModuleName, ...],
        walk_forward_policy: WalkForwardPolicy,
        out_of_sample_policy: OutOfSamplePolicy,
        requested_at: datetime | None = None,
        minimum_observations: int = 1,
    ) -> ValidationRequest:
        samples = result.complete_validation_samples
        if not samples:
            raise ValueError("cannot build ValidationRequest without complete replay samples")
        requested = requested_at or datetime.now(UTC)
        snapshot = FrameworkSnapshot(
            git_commit=result.manifest.git_commit,
            framework_version=result.manifest.framework_version,
            configuration_hash=result.manifest.configuration_hash,
            research_version=RESEARCH_ENGINE_VERSION,
            validation_version=self.validation_version,
            database_schema_version=result.manifest.schema_version,
            captured_at=result.manifest.generated_at,
        )
        return ValidationRequest(
            validation_id=validation_id,
            subject=samples[0].instrument,
            start_at=min(sample.decision_at for sample in samples),
            end_at=max(sample.decision_at for sample in samples),
            as_of=result.query.outcome_as_of,
            requested_at=requested,
            modules=modules,
            samples=samples,
            outcome_definitions=result.query.outcome_definitions,
            framework_snapshot=snapshot,
            walk_forward_policy=walk_forward_policy,
            out_of_sample_policy=out_of_sample_policy,
            minimum_observations=minimum_observations,
        )


__all__ = ["ValidationRequestFactory"]
