from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from tong_quant.data.financial_inputs import FinancialInputSnapshot
from tong_quant.data.market_value_inputs import MarketValueInputSnapshot
from tong_quant.data.native_financial_inputs import NativeFinancialResearchInput
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.data.reviewed_ratio_inputs import ReviewedRatioResearchInput
from tong_quant.data.sec_period_inputs import SECPeriodResearchInput
from tong_quant.domain.enums import (
    AssetType,
    EvidenceQuality,
    InvestmentAssessmentStatus,
    Market,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    ScoreType,
)
from tong_quant.domain.models import Bar, FundamentalFact, Signal, require_timezone
from tong_quant.market_regime.models import MarketRegime
from tong_quant.screening.models import ResearchQueueEntry, screening_instrument_id
from tong_quant.version import RESEARCH_CONFIDENCE_VERSION

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
        if self.available_at.astimezone(UTC) < self.observed_at.astimezone(UTC):
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
    method: str = f"weighted_geometric_with_weakest_link_cap:{RESEARCH_CONFIDENCE_VERSION}"

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
        if self.available_at.astimezone(UTC) > self.evaluated_at.astimezone(UTC):
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
    financial_inputs: FinancialInputSnapshot | None = None
    market_value_inputs: MarketValueInputSnapshot | None = None
    native_financial_inputs: NativeFinancialResearchInput | None = None
    reviewed_document_inputs: ReviewedDocumentResearchInput | None = None
    reviewed_ratio_inputs: ReviewedRatioResearchInput | None = None
    supplemental_ratio_inputs: tuple[ReviewedRatioResearchInput, ...] = ()
    sec_period_inputs: SECPeriodResearchInput | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        require_timezone(self.as_of, "as_of")
        cutoff = self.as_of.astimezone(UTC)
        if not self.queue_id.strip():
            raise ValueError("research context requires queue_id")
        if self.queue_entry.status.value not in {"pending", "in_research"}:
            raise ValueError("research requires a pending or active queue entry")
        entry = self.queue_entry
        queue_times = (
            entry.admitted_at, entry.candidate.available_at, entry.research_score.calculated_at,
            entry.candidate.discovered_at,
            *(result.available_at for result in entry.hard_screen_results),
            *(result.evaluated_at for result in entry.hard_screen_results),
        )
        if any(timestamp.astimezone(UTC) > cutoff for timestamp in queue_times):
            raise ValueError("research context contains future queue data")
        future_evidence = [
            item.evidence_id for item in self.evidence
            if item.available_at.astimezone(UTC) > cutoff
            or item.observed_at.astimezone(UTC) > cutoff
        ]
        future_bars = [
            bar.timestamp.isoformat() for bar in self.bars
            if bar.available_at.astimezone(UTC) > cutoff or bar.timestamp.astimezone(UTC) > cutoff
        ]
        future_facts = [
            fact.metric
            for facts in self.fundamentals.values()
            for fact in facts
            if fact.available_at.astimezone(UTC) > cutoff
            or fact.published_at.astimezone(UTC) > cutoff or fact.period_end > cutoff.date()
        ]
        if future_evidence or future_bars or future_facts:
            raise ValueError("research context contains future data")
        expected_instrument = screening_instrument_id(entry.candidate.instrument)
        instruments = (
            entry.candidate.instrument,
            *(bar.instrument for bar in self.bars),
            *(fact.instrument for facts in self.fundamentals.values() for fact in facts),
        )
        if any(
            instrument.available_at is not None
            and instrument.available_at.astimezone(UTC) > cutoff
            for instrument in instruments
        ):
            raise ValueError("research context contains future instrument metadata")
        if any(
            screening_instrument_id(bar.instrument) != expected_instrument for bar in self.bars
        ):
            raise ValueError("research context bar instrument mismatch")
        versions: dict[tuple[object, ...], tuple[object, ...]] = {}
        for metric, facts in self.fundamentals.items():
            for fact in facts:
                if screening_instrument_id(fact.instrument) != expected_instrument:
                    raise ValueError("research context fundamental instrument mismatch")
                if metric != fact.metric:
                    raise ValueError("research context fundamental metric mismatch")
                if not fact.value.is_finite():
                    raise ValueError("research context fundamental value must be finite")
                identity = (
                    metric, fact.period_end, fact.available_at.astimezone(UTC), fact.revision,
                    fact.published_at.astimezone(UTC),
                )
                content = (
                    fact.period_start, fact.fiscal_period, fact.value, fact.currency, fact.unit,
                    fact.source, fact.raw_data_hash, fact.provider_dataset,
                    fact.availability_precision, fact.trust_level,
                )
                if identity in versions and versions[identity] != content:
                    raise ValueError("research context contains conflicting fundamental versions")
                versions[identity] = content
        if self.market_regime is not None and self.market_regime.as_of.astimezone(UTC) > cutoff:
            raise ValueError("research context contains a future Market Regime")
        if self.financial_inputs is not None:
            self.financial_inputs.validate_context(
                tuple(fact for facts in self.fundamentals.values() for fact in facts),
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of,
            )
        if self.market_value_inputs is not None:
            if entry.candidate.instrument.asset_type is not AssetType.EQUITY:
                raise ValueError("current market-value research inputs require equity instruments")
            self.market_value_inputs.validate_context(
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of,
            )
        if self.native_financial_inputs is not None:
            if (entry.candidate.instrument.asset_type is not AssetType.EQUITY
                    or self.financial_inputs is not None):
                raise ValueError("native financial inputs require equities and no parallel receipt")
            self.native_financial_inputs.validate_context(
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of,
            )
        if self.reviewed_document_inputs is not None:
            if (entry.candidate.instrument.asset_type is not AssetType.EQUITY
                    or self.financial_inputs is not None):
                raise ValueError("reviewed-document input requires equity and no canonical receipt")
            self.reviewed_document_inputs.validate_context(
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of,
            )
            if (self.native_financial_inputs is not None
                    and self.native_financial_inputs.sector_profile
                    != self.reviewed_document_inputs.sector_profile):
                raise ValueError("native/manual requested sector contexts disagree")
        if (type(self.supplemental_ratio_inputs) is not tuple
                or len(self.supplemental_ratio_inputs) > 3
                or self.supplemental_ratio_inputs and self.reviewed_ratio_inputs is None):
            raise ValueError("supplemental ratios require a primary receipt and at most 3 items")
        ratio_inputs = (
            *((self.reviewed_ratio_inputs,) if self.reviewed_ratio_inputs is not None else ()),
            *self.supplemental_ratio_inputs,
        )
        document_urls: set[str] = set()
        for ratio_input in ratio_inputs:
            if not isinstance(ratio_input, ReviewedRatioResearchInput):
                raise ValueError("reviewed ratio inputs require immutable ratio receipts")
            if (entry.candidate.instrument.asset_type is not AssetType.EQUITY
                    or self.financial_inputs is not None):
                raise ValueError("reviewed-ratio input requires equity and no canonical receipt")
            ratio_input.validate_context(
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of,
            )
            document_url = str(ratio_input.document()["document_url"])
            if document_url in document_urls:
                raise ValueError("reviewed ratio documents must be unique; no duplicate editions")
            document_urls.add(document_url)
            for other in (self.native_financial_inputs, self.reviewed_document_inputs,
                          self.reviewed_ratio_inputs):
                if other is not None and other.sector_profile != (
                    ratio_input.sector_profile
                ):
                    raise ValueError("ratio/native/monetary requested sector contexts disagree")
        if self.sec_period_inputs is not None:
            if (not isinstance(self.sec_period_inputs, SECPeriodResearchInput)
                    or entry.candidate.instrument.asset_type is not AssetType.EQUITY
                    or entry.candidate.instrument.market is not Market.US
                    or self.financial_inputs is not None):
                raise ValueError("SEC period inputs require US equity and no canonical receipt")
            self.sec_period_inputs.validate_context(
                symbol=entry.candidate.instrument.symbol, market=entry.candidate.instrument.market,
                as_of=self.as_of)
            for other in (self.native_financial_inputs, self.reviewed_document_inputs,
                          *ratio_inputs):
                if (other is not None
                        and other.sector_profile != self.sec_period_inputs.sector_profile):
                    raise ValueError("SEC and other financial requested sector contexts disagree")

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
    condition_style: str | None = None

    def __post_init__(self) -> None:
        if self.condition_style not in {None, "long_term_confirmation", "improved_turtle"}:
            raise ValueError("unsupported research condition style")
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


@dataclass(frozen=True, slots=True)
class InvestmentScoreComponent:
    name: str
    score: float
    confidence: float
    weight: float
    contribution: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("investment score component requires a name")
        _require_percentage("investment component score", self.score)
        _require_percentage("investment component confidence", self.confidence)
        if not 0 < self.weight <= 1:
            raise ValueError("investment component weight must be between 0 and 1")
        if not self.reasons:
            raise ValueError("investment score component must be explainable")


@dataclass(frozen=True, slots=True)
class InvestmentScore:
    score: float
    confidence: float
    calculated_at: datetime
    components: tuple[InvestmentScoreComponent, ...]
    reasons: tuple[str, ...]
    model_version: str
    score_type: ScoreType = ScoreType.INVESTMENT

    def __post_init__(self) -> None:
        _require_percentage("investment score", self.score)
        _require_percentage("investment score confidence", self.confidence)
        require_timezone(self.calculated_at, "calculated_at")
        if self.score_type is not ScoreType.INVESTMENT:
            raise ValueError("InvestmentScore must use investment score type")
        if not self.components:
            raise ValueError("InvestmentScore requires components")
        if not self.reasons:
            raise ValueError("InvestmentScore must be explainable")


@dataclass(frozen=True, slots=True)
class InvestmentAssessment:
    report: ResearchReport
    status: InvestmentAssessmentStatus
    assessed_at: datetime
    investment_score: InvestmentScore | None
    market_regime: MarketRegime | None
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    model_version: str

    def __post_init__(self) -> None:
        require_timezone(self.assessed_at, "assessed_at")
        if self.assessed_at < self.report.available_at:
            raise ValueError("investment assessment cannot precede report availability")
        if self.report.status is not ResearchRunStatus.COMPLETED:
            if self.status is not InvestmentAssessmentStatus.INCOMPLETE:
                raise ValueError("non-completed reports can only produce incomplete assessments")
            if self.investment_score is not None:
                raise ValueError("incomplete investment assessments must not carry a score")
        elif self.status in {
            InvestmentAssessmentStatus.COMPLETED,
            InvestmentAssessmentStatus.LOW_CONFIDENCE,
        }:
            if self.investment_score is None:
                raise ValueError("scored investment assessments require InvestmentScore")
        elif self.investment_score is not None:
            raise ValueError("unscored investment assessments must not carry InvestmentScore")
        if not self.reasons:
            raise ValueError("investment assessment must be explainable")
