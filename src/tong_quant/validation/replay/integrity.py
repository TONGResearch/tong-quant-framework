from tong_quant.validation.replay.hashing import stable_hash
from tong_quant.validation.replay.models import ReplayQuery, ReplayValidationSample
from tong_quant.version import (
    HISTORICAL_REPLAY_VERSION,
    LIFECYCLE_REVIEW_VERSION,
    REPLAY_CONFIDENCE_VERSION,
    REPLAY_OUTCOME_VERSION,
    REPLAY_RESEARCH_BINDING_VERSION,
)


def replay_query_hash(query: ReplayQuery) -> str:
    return stable_hash(
        {
            "query": query,
            "replay_version": HISTORICAL_REPLAY_VERSION,
            "confidence_version": REPLAY_CONFIDENCE_VERSION,
            "lifecycle_review_version": LIFECYCLE_REVIEW_VERSION,
            "outcome_version": REPLAY_OUTCOME_VERSION,
            "research_binding_version": REPLAY_RESEARCH_BINDING_VERSION,
        }
    )


def require_sample_content_hash(sample: ReplayValidationSample, query_hash: str) -> None:
    snapshot = sample.decision_context.get("research_snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("research snapshot missing")
    expected = stable_hash(
        {
            "query_hash": query_hash,
            "instrument": (
                f"{sample.instrument.market.value}:{sample.instrument.asset_type.value}:"
                f"{sample.instrument.symbol}"
            ),
            "definition": sample.outcome_context.get("definition"),
            "decision_context": sample.decision_context,
            "outcome_context": sample.outcome_context,
            "report_id": None if snapshot.get("blocking_reasons") else snapshot.get("report_id"),
            "missing_flags": sample.missing_data_flags,
            "replay_confidence": sample.replay_confidence,
        }
    )
    if expected != sample.replay_hash:
        raise ValueError("replay sample content hash mismatch")


def validate_replay_sample(sample: ReplayValidationSample) -> None:
    validation_sample = sample.validation_sample
    if validation_sample is None:
        return
    if validation_sample.research_report.available_at > sample.decision_as_of:
        raise ValueError("replay sample contains future research data")
    if validation_sample.outcome.available_at > sample.outcome_as_of:
        raise ValueError("replay sample contains future outcome data")
    if validation_sample.outcome.observed_at < sample.decision_as_of:
        raise ValueError("replay outcome precedes decision context")


__all__ = ["validate_replay_sample"]
