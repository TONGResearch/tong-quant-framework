from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime

from tong_quant.domain.enums import (
    ResearchConclusion,
    ResearchModuleName,
)
from tong_quant.research.confidence import confidence_from_evidence
from tong_quant.research.models import (
    ResearchAssessment,
    ResearchContext,
    ResearchEvidence,
    ResearchValue,
)
from tong_quant.version import EVIDENCE_SCORE_ADMISSION_VERSION


def evidence_score(
    evidence: ResearchEvidence | None,
) -> float | None:
    if (evidence is None or isinstance(evidence.value, bool)
            or not isinstance(evidence.value, (int, float))):
        return None
    value = float(evidence.value)
    if not 0 <= value <= 100:
        raise ValueError(f"research evidence score out of range: {evidence.evidence_id}")
    return value


def assessment_from_scores(
    *,
    module: ResearchModuleName,
    scores: Sequence[float],
    evidence: Sequence[ResearchEvidence],
    required_names: frozenset[str],
    as_of: datetime,
    findings: tuple[str, ...],
    risks: tuple[str, ...],
    limitations: tuple[str, ...],
    model_version: str,
    features: dict[str, ResearchValue] | None = None,
) -> ResearchAssessment:
    if not scores:
        return insufficient_assessment(
            module=module,
            evidence=evidence,
            required_names=required_names,
            as_of=as_of,
            limitations=limitations or ("Required research evidence is unavailable",),
            model_version=model_version,
        )
    score = sum(scores) / len(scores)
    confidence = confidence_from_evidence(
        evidence,
        required_names=required_names,
        as_of=as_of,
        agreement_scores=scores,
    )
    return ResearchAssessment(
        module=module,
        conclusion=conclusion_for_score(score),
        score=round(score, 4),
        confidence=confidence,
        evaluated_at=as_of,
        available_at=max((item.available_at for item in evidence), default=as_of,
                         key=lambda value: value.astimezone(UTC)),
        findings=findings or (f"{module.value} evidence produced score {score:.1f}",),
        risks=risks,
        limitations=limitations,
        evidence_ids=tuple(item.evidence_id for item in evidence),
        model_version=model_version,
        features=features or {},
        evidence=tuple(evidence),
    )


def evidence_driven_assessment(
    *,
    module: ResearchModuleName,
    context: ResearchContext,
    required_names: frozenset[str],
    model_version: str,
    dependencies: Mapping[ResearchModuleName, ResearchAssessment] | None = None,
) -> ResearchAssessment:
    context.validate()
    evidence = context.evidence_for(module)
    declared = {name: tuple(item for item in evidence if item.name == name)
                for name in sorted(required_names)}
    missing = tuple(name for name, items in declared.items() if not items)
    ambiguous = tuple(name for name, items in declared.items() if len(items) > 1)
    matched = tuple(items[0] for items in declared.values() if len(items) == 1)
    numeric = {item.name: evidence_score(item) for item in matched}
    unscorable = tuple(name for name, score in numeric.items() if score is None)
    ignored = tuple(sorted({item.name for item in evidence if item.name not in required_names}))
    findings = tuple(
        str(item.metadata.get("finding", f"{item.name} was evaluated"))
        for item in matched
    )
    risks = tuple(
        str(item.metadata["risk"])
        for item in evidence
        if item.metadata.get("risk")
    )
    limitations = tuple(
        str(item.metadata["limitation"])
        for item in evidence
        if item.metadata.get("limitation")
    )
    dependency_features: dict[str, ResearchValue] = {}
    for name, assessment in (dependencies or {}).items():
        dependency_features[f"{name.value}_conclusion"] = assessment.conclusion.value
        dependency_features[f"{name.value}_score"] = assessment.score
    admission_features: dict[str, ResearchValue] = {
        "evidence_score_admission_version": EVIDENCE_SCORE_ADMISSION_VERSION,
        "ignored_evidence_names": ",".join(ignored),
        "missing_evidence_names": ",".join(missing),
        "ambiguous_evidence_names": ",".join(ambiguous),
        "unscorable_evidence_names": ",".join(unscorable),
    }
    if not required_names or missing or ambiguous or unscorable:
        result = insufficient_assessment(
            module=module, evidence=(), required_names=required_names, as_of=context.as_of,
            limitations=(*limitations,
                         "Every declared scoring input must have exactly one numeric observation; "
                         "missing, duplicate, boolean or text inputs cannot yield a partial score"),
            model_version=model_version,
        )
        result = replace(result, confidence=replace(result.confidence, confidence=0.0), risks=risks)
    else:
        result = assessment_from_scores(
            module=module, scores=tuple(score for score in numeric.values() if score is not None),
            evidence=matched, required_names=required_names, as_of=context.as_of,
            findings=findings, risks=risks, limitations=limitations, model_version=model_version,
        )
    # Keep all original annotations for audit without letting extras influence confidence.
    return replace(
        result, evidence=evidence, evidence_ids=tuple(item.evidence_id for item in evidence),
        available_at=max((item.available_at for item in evidence), default=context.as_of,
                         key=lambda value: value.astimezone(UTC)),
        features={**result.features, **dependency_features, **admission_features},
    )


def insufficient_assessment(
    *,
    module: ResearchModuleName,
    evidence: Sequence[ResearchEvidence],
    required_names: frozenset[str],
    as_of: datetime,
    limitations: tuple[str, ...],
    model_version: str,
) -> ResearchAssessment:
    return ResearchAssessment(
        module=module,
        conclusion=ResearchConclusion.INSUFFICIENT_DATA,
        score=None,
        confidence=confidence_from_evidence(
            evidence,
            required_names=required_names,
            as_of=as_of,
            agreement_scores=(),
        ),
        evaluated_at=as_of,
        available_at=max((item.available_at for item in evidence), default=as_of,
                         key=lambda value: value.astimezone(UTC)),
        findings=(f"{module.value} research could not reach a scored conclusion",),
        risks=(),
        limitations=limitations,
        evidence_ids=tuple(item.evidence_id for item in evidence),
        model_version=model_version,
        evidence=tuple(evidence),
    )


def not_applicable_assessment(
    *,
    module: ResearchModuleName,
    as_of: datetime,
    reason: str,
    model_version: str,
) -> ResearchAssessment:
    return ResearchAssessment(
        module=module,
        conclusion=ResearchConclusion.NOT_APPLICABLE,
        score=None,
        confidence=confidence_from_evidence(
            (),
            required_names=frozenset(),
            as_of=as_of,
        ),
        evaluated_at=as_of,
        available_at=as_of,
        findings=(reason,),
        risks=(),
        limitations=(reason,),
        evidence_ids=(),
        model_version=model_version,
    )


def conclusion_for_score(score: float) -> ResearchConclusion:
    if score >= 65:
        return ResearchConclusion.SUPPORTIVE
    if score >= 45:
        return ResearchConclusion.MIXED
    if score >= 30:
        return ResearchConclusion.CAUTION
    return ResearchConclusion.ADVERSE
