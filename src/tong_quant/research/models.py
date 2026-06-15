from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from tong_quant.domain.enums import (
    EvidenceQuality,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
)
from tong_quant.domain.models import Bar, FundamentalFact, Signal, require_timezone
from tong_quant.market_regime.models import MarketRegime
from tong_quant.screening.models import ResearchQueueEntry

ResearchValue = float | int | str | bool | Decimal | None


def _require_percentage(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class ResearchEvidence:
    evidence_id: str
    module: ResearchModuleName
    name: str
    value: ResearchValue
    observed_at: datetime
    available_at: datetime
    source: str
    quality: EvidenceQuality
    source_reference: str = ""
    calculation_version: str = "raw"
    input_hash: str = ""
    metadata: dict[str, ResearchValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.observed_at, "observed_at")
        require_timezone(self.available_at, "available_at")
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be empty")
        if not self.name.strip():
            raise ValueError("evidence name must not be empty")
        if not self.source.strip():
            raise ValueError("evidence source must not be empty")
        if self.available_at < self.observed_at:
            raise ValueError("evidence available_at cannot precede observed_at")


@dataclass(frozen=True, slots=True)
class ThesisInvalidationCondition:
    condition_id: str
    description: str
    metric: str
    operator: str
    threshold: ResearchValue
    observation_window: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.condition_id.strip() or not self.description.strip():
            raise ValueError("invalidation condition requires id and description")
        if self.operator not in {"<", "<=", ">", ">=", "==", "!="}:
            raise ValueError("unsupported invalidation operator")
        if not self.metric.strip() or not self.observation_window.strip():
            raise ValueError("invalidation condition requires metric and window")
        if not self.rationale.strip():
            raise ValueError("invalidation condition requires rationale")


@dataclass(frozen=True, slots=True)
class ConfidenceBreakdown:
    evidence_quality: float
    data_completeness: float
    module_agreement: float
    point_in_time_integrity: float
    confidence: float
    method: str = "weighted_geometric_with_weakest_link_cap"

    def __post_init__(self) -> None:
        for name, value in (
            ("evidence_quality", self.evidence_quality),
            ("data_completeness", self.data_completeness),
            ("module_agreement", self.module_agreement),
            ("point_in_time_integrity", self.point_in_time_integrity),
            ("confidence", self.confidence),
        ):
            _require_percentage(name, value)


@dataclass(frozen=True, slots=True)
class ResearchAssessment:
    module: ResearchModuleName
    conclusion: ResearchConclusion
    score: float | None
    confidence: ConfidenceBreakdown
    evaluated_at: datetime
    available_at: datetime
    findings: tuple[str, ...]
    risks: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    model_version: str
    features: dict[str, ResearchValue] = field(default_factory=dict)
    evidence: tuple[ResearchEvidence, ...] = ()

    def __post_init__(self) -> None:
        require_timezone(self.evaluated_at, "evaluated_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at > self.evaluated_at:
            raise ValueError("research assessment cannot use future data")
        if self.score is not None:
            _require_percentage("research assessment score", self.score)
        if not self.findings:
            raise ValueError("research assessment must contain findings")
        if self.conclusion in {
            ResearchConclusion.INSUFFICIENT_DATA,
            ResearchConclusion.NOT_APPLICABLE,
        } and self.score is not None:
            raise ValueError("unscored conclusions must not carry a score")


@dataclass(frozen=True, slots=True)
class PolicyAssessment:
    assessment: ResearchAssessment
    regulatory_environment: str
    industrial_policy: str
    fiscal_policy: str
    monetary_policy: str
    geopolitical_factors: str

    def __post_init__(self) -> None:
        if self.assessment.module is not ResearchModuleName.POLICY:
            raise ValueError("PolicyAssessment requires the policy module")


@dataclass(frozen=True, slots=True)
class ResearchContext:
    queue_id: str
    queue_entry: ResearchQueueEntry
    as_of: datetime
    bars: tuple[Bar, ...]
    fundamentals: dict[str, tuple[FundamentalFact, ...]]
    evidence: tuple[ResearchEvidence, ...]
    market_regime: MarketRegime | None = None

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if not self.queue_id.strip():
            raise ValueError("research context requires queue_id")
        if self.queue_entry.status.value not in {"pending", "in_research"}:
            raise ValueError("research requires a pending or active queue entry")
        future_evidence = [
            item.evidence_id for item in self.evidence if item.available_at > self.as_of
        ]
        future_bars = [
            bar.timestamp.isoformat() for bar in self.bars if bar.available_at > self.as_of
        ]
        future_facts = [
            fact.metric
            for facts in self.fundamentals.values()
            for fact in facts
            if fact.available_at > self.as_of
        ]
        if future_evidence or future_bars or future_facts:
            raise ValueError("research context contains future data")
        if self.market_regime is not None and self.market_regime.as_of > self.as_of:
            raise ValueError("research context contains a future Market Regime")

    def evidence_for(self, module: ResearchModuleName) -> tuple[ResearchEvidence, ...]:
        return tuple(item for item in self.evidence if item.module is module)

    def evidence_named(
        self,
        module: ResearchModuleName,
        name: str,
    ) -> ResearchEvidence | None:
        matches = [
            item
            for item in self.evidence
            if item.module is module and item.name == name
        ]
        if len(matches) > 1:
            raise ValueError(f"duplicate research evidence: {module.value}.{name}")
        return None if not matches else matches[0]


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    context: ResearchContext
    modules: tuple[ResearchModuleName, ...]
    thesis: str
    counter_thesis: str
    invalidation_conditions: tuple[ThesisInvalidationCondition, ...]
    unresolved_questions: tuple[str, ...] = ()
    researcher: str | None = None

    def __post_init__(self) -> None:
        if not self.modules:
            raise ValueError("research request requires modules")
        if len(set(self.modules)) != len(self.modules):
            raise ValueError("research modules must be unique")
        if not self.thesis.strip() or not self.counter_thesis.strip():
            raise ValueError("research request requires thesis and counter thesis")
        if not self.invalidation_conditions:
            raise ValueError("research request requires invalidation conditions")


@dataclass(frozen=True, slots=True)
class ResearchReport:
    report_id: str
    queue_id: str
    instrument_id: str
    generated_at: datetime
    available_at: datetime
    status: ResearchRunStatus
    thesis: str
    counter_thesis: str
    invalidation_conditions: tuple[ThesisInvalidationCondition, ...]
    assessments: tuple[ResearchAssessment, ...]
    policy_assessment: PolicyAssessment | None
    confidence: ConfidenceBreakdown
    key_findings: tuple[str, ...]
    key_risks: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    market_regime: MarketRegime | None
    model_version: str

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "generated_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.generated_at:
            raise ValueError("report available_at cannot precede generated_at")
        if not self.thesis.strip() or not self.counter_thesis.strip():
            raise ValueError("every report requires thesis and counter thesis")
        if not self.invalidation_conditions:
            raise ValueError("every report requires thesis invalidation conditions")
        if not self.assessments:
            raise ValueError("research report requires assessments")
        if not self.key_findings or not self.key_risks:
            raise ValueError("research report requires findings and risks")


@dataclass(frozen=True, slots=True)
class ResearchRun:
    run_id: str
    request: ResearchRequest
    status: ResearchRunStatus
    started_at: datetime
    completed_at: datetime
    report: ResearchReport
    signal: Signal

    def __post_init__(self) -> None:
        require_timezone(self.started_at, "started_at")
        require_timezone(self.completed_at, "completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("research completion cannot precede start")
