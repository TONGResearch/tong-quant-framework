from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from tong_quant.domain.enums import (
    DecisionDisposition,
    Regime,
    ThesisOutcomeStatus,
    ValidationModuleName,
    ValidationRunStatus,
    ValidationSplitKind,
    ValidationStatus,
)
from tong_quant.domain.models import Instrument, Signal, require_timezone
from tong_quant.research.models import ResearchReport

ValidationValue = float | int | str | bool | Decimal | None


def _require_percentage(name: str, value: float) -> None:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class FrameworkSnapshot:
    git_commit: str
    framework_version: str
    configuration_hash: str
    research_version: str
    validation_version: str
    database_schema_version: str
    captured_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.captured_at, "captured_at")
        values = (
            self.git_commit,
            self.framework_version,
            self.configuration_hash,
            self.research_version,
            self.validation_version,
            self.database_schema_version,
        )
        if any(not value.strip() for value in values):
            raise ValueError("framework snapshot fields must not be empty")
        if len(self.git_commit) < 7:
            raise ValueError("git_commit must contain at least seven characters")
        if len(self.configuration_hash) < 16:
            raise ValueError("configuration_hash must be a stable content hash")


@dataclass(frozen=True, slots=True)
class OutcomeDefinition:
    outcome_id: str
    target_metric: str
    observation_horizon_days: int
    success_operator: str
    success_threshold: float
    availability_lag_days: int
    benchmark: str | None = None
    version: str = "v0.6"

    def __post_init__(self) -> None:
        if not self.outcome_id.strip() or not self.target_metric.strip():
            raise ValueError("outcome definition requires id and target metric")
        if self.observation_horizon_days <= 0:
            raise ValueError("outcome horizon must be positive")
        if self.availability_lag_days < 0:
            raise ValueError("outcome availability lag cannot be negative")
        if self.success_operator not in {"<", "<=", ">", ">=", "==", "!="}:
            raise ValueError("unsupported outcome comparison operator")


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    outcome_id: str
    definition_id: str
    subject_id: str
    observed_at: datetime
    available_at: datetime
    value: float | None
    benchmark_value: float | None
    succeeded: bool | None
    thesis_status: ThesisOutcomeStatus
    invalidation_triggered: bool | None
    metadata: dict[str, ValidationValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_timezone(self.observed_at, "observed_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.observed_at:
            raise ValueError("outcome available_at cannot precede observed_at")
        if not self.outcome_id.strip() or not self.definition_id.strip():
            raise ValueError("validation outcome requires identifiers")


@dataclass(frozen=True, slots=True)
class DecisionJournalEntry:
    decision_id: str
    research_report_id: str
    decided_at: datetime
    available_at: datetime
    disposition: DecisionDisposition
    rationale: tuple[str, ...]
    confidence: float
    decision_maker: str
    framework_snapshot_hash: str

    def __post_init__(self) -> None:
        require_timezone(self.decided_at, "decided_at")
        require_timezone(self.available_at, "available_at")
        if self.available_at < self.decided_at:
            raise ValueError("decision availability cannot precede the decision")
        if not self.decision_id.strip() or not self.research_report_id.strip():
            raise ValueError("decision journal entry requires identifiers")
        if not self.rationale:
            raise ValueError("decision journal entry requires rationale")
        _require_percentage("decision confidence", self.confidence)


@dataclass(frozen=True, slots=True)
class PortfolioResearchPosition:
    subject_id: str
    research_weight: float
    country: str
    industry: str
    theme: str
    style: str

    def __post_init__(self) -> None:
        if not 0 < self.research_weight <= 1:
            raise ValueError("portfolio research weight must be between zero and one")
        if any(
            not value.strip()
            for value in (self.subject_id, self.country, self.industry, self.theme, self.style)
        ):
            raise ValueError("portfolio research position categories must not be empty")


@dataclass(frozen=True, slots=True)
class ValidationSample:
    sample_id: str
    instrument: Instrument
    research_report: ResearchReport
    decision_at: datetime
    research_expected_success: bool
    outcome: ValidationOutcome
    factor_scores: dict[str, float]
    market_regime: Regime | None = None
    decision: DecisionJournalEntry | None = None
    portfolio_position: PortfolioResearchPosition | None = None

    def __post_init__(self) -> None:
        require_timezone(self.decision_at, "decision_at")
        if not self.sample_id.strip():
            raise ValueError("validation sample requires sample_id")
        if self.research_report.available_at > self.decision_at:
            raise ValueError("validation sample uses a future research report")
        if self.outcome.observed_at < self.decision_at:
            raise ValueError("validation outcome cannot precede the decision")
        if any(not 0 <= score <= 100 for score in self.factor_scores.values()):
            raise ValueError("factor scores must be between 0 and 100")
        if self.decision is not None:
            if self.decision.research_report_id != self.research_report.report_id:
                raise ValueError("decision journal entry does not match the research report")
            if self.decision.available_at > self.outcome.observed_at:
                raise ValueError("decision journal entry was unavailable before the outcome")
        if (
            self.portfolio_position is not None
            and self.portfolio_position.subject_id != self.sample_id
        ):
            raise ValueError("portfolio position does not match validation sample")


@dataclass(frozen=True, slots=True)
class ValidationSplit:
    split_id: str
    kind: ValidationSplitKind
    start_date: date
    end_date: date
    frozen_configuration_hash: str
    sequence: int

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("validation split end cannot precede start")
        if self.sequence < 0:
            raise ValueError("validation split sequence cannot be negative")
        if not self.split_id.strip() or not self.frozen_configuration_hash.strip():
            raise ValueError("validation split requires id and configuration hash")


@dataclass(frozen=True, slots=True)
class WalkForwardPolicy:
    training_days: int
    validation_days: int
    step_days: int
    embargo_days: int

    def __post_init__(self) -> None:
        if min(self.training_days, self.validation_days, self.step_days) <= 0:
            raise ValueError("walk-forward windows and step must be positive")
        if self.embargo_days < 0:
            raise ValueError("embargo days cannot be negative")


@dataclass(frozen=True, slots=True)
class OutOfSamplePolicy:
    development_end: date
    out_of_sample_start: date
    out_of_sample_end: date
    frozen_configuration_hash: str
    maximum_uses: int = 1
    previous_uses: int = 0

    def __post_init__(self) -> None:
        if not self.development_end < self.out_of_sample_start <= self.out_of_sample_end:
            raise ValueError("out-of-sample dates must follow development data")
        if not self.frozen_configuration_hash.strip():
            raise ValueError("out-of-sample policy requires a frozen configuration hash")
        if self.maximum_uses <= 0 or not 0 <= self.previous_uses < self.maximum_uses:
            raise ValueError("out-of-sample usage policy is exhausted or invalid")


@dataclass(frozen=True, slots=True)
class ValidationRequest:
    validation_id: str
    subject: Instrument
    start_at: datetime
    end_at: datetime
    as_of: datetime
    requested_at: datetime
    modules: tuple[ValidationModuleName, ...]
    samples: tuple[ValidationSample, ...]
    outcome_definitions: tuple[OutcomeDefinition, ...]
    framework_snapshot: FrameworkSnapshot
    walk_forward_policy: WalkForwardPolicy
    out_of_sample_policy: OutOfSamplePolicy
    minimum_observations: int

    def __post_init__(self) -> None:
        for name, value in (
            ("start_at", self.start_at),
            ("end_at", self.end_at),
            ("as_of", self.as_of),
            ("requested_at", self.requested_at),
        ):
            require_timezone(value, name)
        if not self.start_at <= self.end_at <= self.as_of <= self.requested_at:
            raise ValueError("validation request time range is invalid")
        if not self.validation_id.strip() or not self.modules:
            raise ValueError("validation request requires id and modules")
        if len(set(self.modules)) != len(self.modules):
            raise ValueError("validation modules must be unique")
        if self.minimum_observations <= 0:
            raise ValueError("minimum observations must be positive")
        if not (
            self.start_at.date()
            <= self.out_of_sample_policy.out_of_sample_start
            <= self.out_of_sample_policy.out_of_sample_end
            <= self.end_at.date()
        ):
            raise ValueError("out-of-sample period must fall inside the request")
        definitions = {definition.outcome_id for definition in self.outcome_definitions}
        if len(definitions) != len(self.outcome_definitions):
            raise ValueError("outcome definition ids must be unique")
        if self.framework_snapshot.captured_at > self.requested_at:
            raise ValueError("framework snapshot is from the future")
        for sample in self.samples:
            if not self.start_at <= sample.decision_at <= self.end_at:
                raise ValueError("validation sample falls outside the requested period")
            if sample.outcome.available_at > self.as_of:
                raise ValueError("validation request contains a future outcome")
            if sample.outcome.definition_id not in definitions:
                raise ValueError("validation sample references an unknown outcome definition")


@dataclass(frozen=True, slots=True)
class IntegrityCheck:
    check_id: str
    passed: bool
    checked_at: datetime
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        require_timezone(self.checked_at, "checked_at")
        if not self.check_id.strip() or not self.reasons:
            raise ValueError("integrity check requires id and reasons")


@dataclass(frozen=True, slots=True)
class FactorContribution:
    factor: str
    sample_size: int
    success_score_gap: float
    ablation_brier_delta: float
    stable: bool


@dataclass(frozen=True, slots=True)
class AccuracyMetrics:
    sample_size: int
    accuracy: float
    brier_score: float
    calibration_error: float
    high_confidence_failure_rate: float

    def __post_init__(self) -> None:
        for name, value in (
            ("accuracy", self.accuracy),
            ("calibration_error", self.calibration_error),
            ("high_confidence_failure_rate", self.high_confidence_failure_rate),
        ):
            _require_percentage(name, value)
        if not 0 <= self.brier_score <= 1:
            raise ValueError("brier score must be between zero and one")


@dataclass(frozen=True, slots=True)
class DecisionValidationSummary:
    research_correct_decision_correct: int
    research_correct_decision_wrong: int
    research_wrong_decision_correct: int
    research_wrong_decision_wrong: int
    unresolved_decisions: int


@dataclass(frozen=True, slots=True)
class ConcentrationMetric:
    dimension: str
    maximum_weight: float
    hhi: float
    category_weights: dict[str, float]
    breached: bool


@dataclass(frozen=True, slots=True)
class PortfolioRiskSummary:
    total_weight: float
    concentrations: tuple[ConcentrationMetric, ...]


@dataclass(frozen=True, slots=True)
class ValidationAssessment:
    module: ValidationModuleName
    status: ValidationStatus
    score: float | None
    confidence: float
    sample_size: int
    evaluated_at: datetime
    metrics: dict[str, ValidationValue]
    findings: tuple[str, ...]
    risks: tuple[str, ...]
    limitations: tuple[str, ...]
    integrity_checks: tuple[IntegrityCheck, ...]
    model_version: str

    def __post_init__(self) -> None:
        require_timezone(self.evaluated_at, "evaluated_at")
        if self.score is not None:
            _require_percentage("validation score", self.score)
        _require_percentage("validation confidence", self.confidence)
        if self.sample_size < 0 or not self.findings:
            raise ValueError("validation assessment requires valid sample size and findings")


@dataclass(frozen=True, slots=True)
class ValidationModuleResult:
    assessment: ValidationAssessment
    factor_contributions: tuple[FactorContribution, ...] = ()
    accuracy: AccuracyMetrics | None = None
    decision_summary: DecisionValidationSummary | None = None
    portfolio_risk: PortfolioRiskSummary | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    report_id: str
    validation_id: str
    generated_at: datetime
    status: ValidationRunStatus
    aggregate_status: ValidationStatus
    assessments: tuple[ValidationAssessment, ...]
    framework_snapshot: FrameworkSnapshot
    splits: tuple[ValidationSplit, ...]
    factor_contributions: tuple[FactorContribution, ...]
    accuracy: AccuracyMetrics | None
    decision_summary: DecisionValidationSummary | None
    portfolio_risk: PortfolioRiskSummary | None
    known_limitations: tuple[str, ...]
    reproducibility_manifest: dict[str, str]
    model_version: str

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "generated_at")
        if not self.assessments:
            raise ValueError("validation report requires assessments")
        if not self.reproducibility_manifest:
            raise ValueError("validation report requires reproducibility manifest")


@dataclass(frozen=True, slots=True)
class ValidationRun:
    run_id: str
    request: ValidationRequest
    report: ValidationReport
    signal: Signal
    started_at: datetime
    completed_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.started_at, "started_at")
        require_timezone(self.completed_at, "completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("validation completion cannot precede start")
