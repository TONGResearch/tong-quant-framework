"""Bind reconstructed research content, not independently attested source truth."""

from datetime import UTC, datetime

from tong_quant.domain.enums import ResearchRunStatus
from tong_quant.domain.models import require_timezone
from tong_quant.research.models import ResearchAssessment, ResearchReport
from tong_quant.validation.replay.hashing import stable_hash, stable_json
from tong_quant.validation.replay.models import ReplayValidationSample
from tong_quant.version import REPLAY_RESEARCH_BINDING_VERSION


def research_snapshot(
    report: ResearchReport | None, *, decision_at: datetime, instrument_id: str
) -> dict[str, object]:
    require_timezone(decision_at, "research replay decision_at")
    cutoff = decision_at.astimezone(UTC)
    reasons: list[str] = []
    if report is not None:
        generated_at = report.generated_at.astimezone(UTC)
        if report.instrument_id != instrument_id:
            reasons.append("research_instrument_mismatch")
        if report.available_at.astimezone(UTC) > cutoff or generated_at > cutoff:
            reasons.append("future_research_report")
        if (report.market_regime is not None
                and report.market_regime.as_of.astimezone(UTC) > generated_at):
            reasons.append("future_research_market_regime")
        if len({item.module for item in report.assessments}) != len(report.assessments):
            reasons.append("duplicate_research_module")
        evidence_hashes: dict[str, str] = {}
        for assessment in _assessments(report):
            if (
                assessment.evaluated_at.astimezone(UTC) > generated_at
                or assessment.available_at.astimezone(UTC) > generated_at
            ):
                reasons.append("research_assessment_after_report")
            ids = tuple(item.evidence_id for item in assessment.evidence)
            if (
                len(set(assessment.evidence_ids)) != len(assessment.evidence_ids)
                or len(set(ids)) != len(ids)
                or set(ids) != set(assessment.evidence_ids)
            ):
                reasons.append("research_evidence_reference_mismatch")
            for evidence in assessment.evidence:
                if (
                    evidence.available_at.astimezone(UTC)
                    > assessment.available_at.astimezone(UTC)
                    or evidence.observed_at.astimezone(UTC)
                    > assessment.evaluated_at.astimezone(UTC)
                    or evidence.available_at.astimezone(UTC) > cutoff
                ):
                    reasons.append("research_evidence_after_cutoff")
                content_hash = stable_hash(evidence)
                previous = evidence_hashes.setdefault(evidence.evidence_id, content_hash)
                if previous != content_hash:
                    reasons.append("conflicting_research_evidence_identity")
    return {
        "model_version": REPLAY_RESEARCH_BINDING_VERSION,
        "decision_at": decision_at.isoformat(),
        "instrument_id": instrument_id,
        "report_id": None if report is None else report.report_id,
        "report_hash": None if report is None else stable_hash(report),
        # Rejected source content stays in its source tables, not usable decision inputs.
        "report": None if report is None or reasons else stable_json(report),
        "blocking_reasons": sorted(set(reasons)),
    }


def _assessments(report: ResearchReport) -> tuple[ResearchAssessment, ...]:
    return report.assessments + (
        () if report.policy_assessment is None else (report.policy_assessment.assessment,)
    )


def research_expected_success(report: ResearchReport) -> bool:
    return report.status is ResearchRunStatus.COMPLETED and report.confidence.confidence >= 50


def research_factor_scores(
    report: ResearchReport, decision_context: dict[str, object]
) -> dict[str, float]:
    scores = {
        item.module.value: item.score for item in report.assessments if item.score is not None
    }
    screening_count = decision_context.get("screening_count")
    if isinstance(screening_count, int | float):
        scores["screening_coverage"] = min(100.0, float(screening_count) * 10)
    return scores


def research_evidence_ids(report: ResearchReport) -> tuple[str, ...]:
    return tuple(sorted({key for item in _assessments(report) for key in item.evidence_ids}))


def require_bound_research(sample: ReplayValidationSample) -> None:
    validation = sample.validation_sample
    if validation is None:
        raise ValueError("research validation sample missing")
    context = sample.decision_context
    report = validation.research_report
    instrument_id = (
        f"{sample.instrument.market.value}:{sample.instrument.asset_type.value}:"
        f"{sample.instrument.symbol}"
    )
    expected = research_snapshot(
        report, decision_at=sample.decision_as_of, instrument_id=instrument_id
    )
    if (
        stable_json(context.get("research_snapshot")) != stable_json(expected)
        or expected["blocking_reasons"]
        or validation.instrument != sample.instrument
        or validation.decision is not None
        or validation.portfolio_position is not None
        or sample.evidence_references != research_evidence_ids(report)
        or validation.research_expected_success != research_expected_success(report)
        or validation.factor_scores != research_factor_scores(report, context)
        or validation.market_regime
        != (None if report.market_regime is None else report.market_regime.state)
    ):
        raise ValueError("research content or derived validation fields differ from snapshot")
    for key, count_key in (
        ("fundamental_inputs", "fundamental_count"),
        ("screening_inputs", "screening_count"),
    ):
        inputs = context.get(key)
        if not isinstance(inputs, list) or len(inputs) != context.get(count_key):
            raise ValueError("research input snapshot is incomplete")
        if context.get(f"{key}_hash") != stable_hash(inputs):
            raise ValueError("research input content hash mismatch")
