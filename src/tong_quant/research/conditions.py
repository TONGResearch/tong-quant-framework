"""Explicit research hypotheses joining financial review and technical observations.

Meeting a candidate specification means validation is needed, never authorization.
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.domain.enums import ResearchConclusion, ResearchModuleName
from tong_quant.research.models import ResearchAssessment, ResearchRequest, ResearchValue
from tong_quant.research.timing import require_assessment_cutoff
from tong_quant.version import RESEARCH_CONDITIONS_VERSION


@dataclass(frozen=True, slots=True)
class ResearchCondition:
    name: str
    state: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResearchConditionPolicy:
    minimum_research_confidence: float = 60.0

    def __post_init__(self) -> None:
        value = self.minimum_research_confidence
        if type(value) not in {float, int} or not isfinite(value) or not 0 <= value <= 100:
            raise ValueError("minimum research confidence must be finite and between 0 and 100")


def research_condition_features(
    request: ResearchRequest, assessments: tuple[ResearchAssessment, ...],
    *, policy: ResearchConditionPolicy | None = None,
) -> dict[str, ResearchValue]:
    policy = policy if policy is not None else ResearchConditionPolicy()
    request.context.validate()
    if request.condition_style not in {"long_term_confirmation", "improved_turtle"}:
        raise ValueError("research condition style must be explicitly selected")
    by_module = {assessment.module: assessment for assessment in assessments}
    if len(by_module) != len(assessments):
        raise ValueError("condition review rejects duplicate assessments")
    if any("condition_review_version" in item.features for item in assessments):
        raise ValueError("condition review requires raw module assessments, not report annotations")
    require_assessment_cutoff(assessments, as_of=request.context.as_of)
    screens = request.context.queue_entry.hard_screen_results
    screen_state = "SATISFIED" if screens and all(item.passed is True for item in screens) else (
        "NOT_SATISFIED" if any(item.passed is False for item in screens) else "INSUFFICIENT_DATA"
    )
    conditions = [ResearchCondition("hard_screen", screen_state,
                                     "Use actual queue screening results; absence is not a pass")]
    required_research = (ResearchModuleName.FINANCIAL, ResearchModuleName.VALUE) if (
        request.condition_style == "long_term_confirmation"
    ) else (ResearchModuleName.FINANCIAL,)
    for module in required_research:
        assessment = by_module.get(module)
        numeric = None if assessment is None else assessment.score
        if (assessment is None or numeric is None or isinstance(numeric, bool)
                or not isfinite(numeric) or assessment.conclusion in {
                    ResearchConclusion.INSUFFICIENT_DATA, ResearchConclusion.NOT_APPLICABLE,
                } or (module is ResearchModuleName.FINANCIAL
                      and assessment.features.get("financial_scoring_authorized") is not True)):
            state = "INSUFFICIENT_DATA"
            reason = "Required scored research is absent/unqualified; raw values are not approval"
        elif (assessment.confidence.confidence >= policy.minimum_research_confidence
              and (request.condition_style == "improved_turtle"
                   or assessment.conclusion is ResearchConclusion.SUPPORTIVE)):
            state = "SATISFIED"
            reason = (f"Research reviewed with confidence >= {policy.minimum_research_confidence}; "
                      "long-term style also requires supportive conclusions. "
                      "Trend style retains contrary fundamentals as context, not approval")
        else:
            state = "NOT_SATISFIED"
            reason = "Research support/confidence does not meet this candidate specification"
        conditions.append(ResearchCondition(f"{module.value}_research", state, reason))
    technical = by_module.get(ResearchModuleName.TECHNICAL)
    if request.condition_style == "long_term_confirmation":
        for name in ("trend_structure_family", "momentum_family"):
            value = None if technical is None else technical.features.get(name)
            state = "INSUFFICIENT_DATA" if value in {None, "INSUFFICIENT_DATA"} else (
                "SATISFIED" if value == "BULLISH" else "NOT_SATISFIED"
            )
            conditions.append(ResearchCondition(name, state,
                                                f"Observed {value}; conflict is not a rejection "
                                                "of the company or a sell instruction"))
    else:
        trend = by_module.get(ResearchModuleName.TREND)
        for name in ("breakout_confirmation", "volume_confirmation",
                     "market_sentiment_confirmation", "industry_heat_confirmation"):
            value = None if trend is None else trend.features.get(f"{name}_confirmed")
            state = "INSUFFICIENT_DATA" if type(value) is not bool else (
                "SATISFIED" if value else "NOT_SATISFIED"
            )
            conditions.append(ResearchCondition(name, state,
                                                "All four confirmations are required; "
                                                "missing data is not a failed forecast"))
        strict_breakout = None if trend is None else trend.features.get("strict_donchian_breakout")
        conditions.append(ResearchCondition(
            "strict_donchian_breakout",
            "INSUFFICIENT_DATA" if type(strict_breakout) is not bool else (
                "SATISFIED" if strict_breakout else "NOT_SATISFIED"),
            "Close must exceed the prior channel; equality is not a breakout",
        ))
    if screen_state == "NOT_SATISFIED":
        state = "SCREEN_REJECTED"
    elif any(item.state == "INSUFFICIENT_DATA" for item in conditions):
        state = "DATA_BLOCKED"
    elif all(item.state == "SATISFIED" for item in conditions):
        state = "VALIDATION_REQUIRED"
    else:
        state = "WAIT_CONFIRMATION"
    features = {} if technical is None else technical.features
    invalidated = features.get("setup_direction") == "bullish" and features.get(
        "setup_state"
    ) == "INVALIDATED"
    ordered = tuple(sorted(assessments, key=lambda item: item.module.value))
    input_documents = [asdict(item) for item in ordered]
    reject_sensitive_structure(input_documents)
    document = {
        "version": RESEARCH_CONDITIONS_VERSION, "style": request.condition_style,
        "policy": asdict(policy),
        "as_of": request.context.as_of.astimezone(UTC).isoformat(),
        "queue_id": request.context.queue_id,
        "symbol": request.context.queue_entry.candidate.instrument.symbol,
        "market": request.context.queue_entry.candidate.instrument.market.value,
        "thesis": request.thesis, "counter_thesis": request.counter_thesis,
        "hard_screen_results": [asdict(item) for item in screens],
        "state": state, "entry_conditions": [asdict(item) for item in conditions],
        "long_candidate_invalidation_observed": invalidated,
        "long_invalidation_reference": features.get("dynamic_invalidation_reference")
        if features.get("setup_direction") == "bullish" else None,
        "thesis_invalidation_definitions": [asdict(item)
                                            for item in request.invalidation_conditions],
        "thesis_invalidation_evaluation": "NOT_EVALUATED",
        "validation_status": "NOT_EVALUATED", "execution_authorized": False,
        "limitations": [
            "Candidate specification is not an admitted or profitable investment strategy",
            "No source/PIT qualification, validation, sizing or execution approval is implied",
            "No positions supplied; invalidation references are not sell instructions or fills",
            "Thesis windows require source-qualified observations, not a single unqualified value",
            "Market regime remains a research variable, not a switch",
        ],
        "input_assessment_hashes": [
            {"module": item.module.value,
             "hash": sha256(_canonical(body).encode()).hexdigest()}
            for item, body in zip(ordered, input_documents, strict=True)
        ],
    }
    reject_sensitive_structure(document)
    # Include full consumed assessments, not report ids or caller-supplied authorization flags.
    serialized = _canonical(document)
    return {
        "condition_review_version": RESEARCH_CONDITIONS_VERSION,
        "condition_review_style": request.condition_style,
        "condition_review_state": state,
        "condition_review_hash": sha256(serialized.encode()).hexdigest(),
        "condition_review_json": serialized,
        "long_candidate_invalidation_observed": invalidated,
        "condition_review_execution_authorized": False,
    }


def _canonical(value: object) -> str:
    def encode(item: object) -> str:
        return item.astimezone(UTC).isoformat() if isinstance(item, datetime) else str(item)
    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"), allow_nan=False)
