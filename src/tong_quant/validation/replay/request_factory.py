from dataclasses import dataclass
from datetime import UTC, datetime

from tong_quant.data.lifecycle_review import LifecycleRecordDisposition
from tong_quant.domain.enums import ValidationModuleName
from tong_quant.validation.models import (
    FrameworkSnapshot,
    OutOfSamplePolicy,
    ValidationRequest,
    WalkForwardPolicy,
)
from tong_quant.validation.replay.hashing import stable_hash
from tong_quant.validation.replay.integrity import replay_query_hash, require_sample_content_hash
from tong_quant.validation.replay.models import HistoricalReplayResult
from tong_quant.validation.replay.outcomes import require_verified_outcome
from tong_quant.validation.replay.research_binding import require_bound_research
from tong_quant.version import (
    HISTORICAL_REPLAY_VERSION,
    LIFECYCLE_REVIEW_VERSION,
    REPLAY_CONFIDENCE_VERSION,
    REPLAY_OUTCOME_VERSION,
    REPLAY_RESEARCH_BINDING_VERSION,
    RESEARCH_ENGINE_VERSION,
    VALIDATION_ENGINE_VERSION,
)


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
        _require_validation_eligible(result)
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


def _require_validation_eligible(result: HistoricalReplayResult) -> None:
    blockers = list(result.manifest.replay_confidence.blocking_reasons)
    if (
        result.manifest.query_hash != replay_query_hash(result.query)
        or result.manifest.input_hashes
        != {sample.sample_id: sample.replay_hash for sample in result.samples}
        or len({sample.sample_id for sample in result.samples}) != len(result.samples)
    ):
        blockers.append("replay query or manifest sample binding mismatch")
    if (
        result.manifest.model_version != HISTORICAL_REPLAY_VERSION
        or result.manifest.dataset_versions.get("lifecycle_review") != LIFECYCLE_REVIEW_VERSION
        or result.manifest.replay_confidence.model_version != REPLAY_CONFIDENCE_VERSION
        or result.manifest.dataset_versions.get("outcome_contract") != REPLAY_OUTCOME_VERSION
        or result.manifest.dataset_versions.get("research_binding")
        != REPLAY_RESEARCH_BINDING_VERSION
    ):
        blockers.append("replay/review model version requires reconstruction")
    for sample in result.samples:
        try:
            require_bound_research(sample)
            require_sample_content_hash(sample, result.manifest.query_hash)
            if (
                sample.decision_as_of != result.query.decision_as_of
                or sample.outcome_as_of != result.query.outcome_as_of
            ):
                raise ValueError("sample cutoff differs from replay query")
        except (ValueError, TypeError, KeyError):
            blockers.append(f"research content review failed for {sample.sample_id}")
        try:
            require_verified_outcome(sample, result.query)
        except (ValueError, TypeError, KeyError, ArithmeticError):
            blockers.append(f"outcome review failed for {sample.sample_id}")
        context = sample.decision_context
        if context.get("status") is None:
            if "instrument_status" in result.query.required_inputs:
                blockers.append(f"security status review failed for {sample.sample_id}")
            continue
        review, record = context.get("status_review"), context.get("status_record")
        record_instrument = record.get("instrument") if isinstance(record, dict) else None
        expected_instrument = {
            "symbol": sample.instrument.symbol,
            "market": sample.instrument.market.value,
            "asset_type": sample.instrument.asset_type.value,
        }
        if (
            not isinstance(review, dict)
            or not isinstance(record, dict)
            or review.get("model_version") != LIFECYCLE_REVIEW_VERSION
            or review.get("disposition") != LifecycleRecordDisposition.REVIEWABLE.value
            or review.get("reasons") != []
            or review.get("record_hash") != stable_hash(record)
            or review.get("as_of") != sample.decision_as_of.isoformat()
            or record.get("status") != context.get("status")
            or record.get("is_tradable") != context.get("status_tradable")
            or record.get("trust_level") != context.get("status_trust_level")
            or not isinstance(record_instrument, dict)
            or any(
                record_instrument.get(key) != value for key, value in expected_instrument.items()
            )
            or sample.replay_confidence.model_version != REPLAY_CONFIDENCE_VERSION
        ):
            blockers.append(f"security status review failed for {sample.sample_id}")
    ineligible_samples = tuple(
        sample
        for sample in result.samples
        if not sample.is_complete or not sample.replay_confidence.validation_eligible
    )
    if ineligible_samples:
        blockers.append(
            "incomplete or data-quality-ineligible replay samples: "
            + ", ".join(sample.sample_id for sample in ineligible_samples[:5])
        )
    if blockers:
        raise ValueError(
            "Historical Replay is not eligible for Validation: "
            + "; ".join(dict.fromkeys(blockers))
        )


__all__ = ["ValidationRequestFactory"]
