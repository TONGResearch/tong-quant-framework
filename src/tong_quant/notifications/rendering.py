from collections.abc import Iterable

from tong_quant.domain.enums import (
    PortfolioProposalStatus,
    RiskAssessmentStatus,
    ValidationStatus,
)
from tong_quant.notifications.models import (
    RESEARCH_DISCLAIMER,
    NotificationContent,
    NotificationPriority,
)
from tong_quant.notifications.security import redact_sensitive_text
from tong_quant.portfolio.models import PortfolioProposal
from tong_quant.research.models import ResearchReport
from tong_quant.risk.models import RiskAssessment
from tong_quant.validation.models import ValidationReport
from tong_quant.version import NOTIFICATION_ENGINE_VERSION


def render_research_report(report: ResearchReport) -> NotificationContent:
    invalidations = tuple(item.description for item in report.invalidation_conditions)
    body = _body(
        (
            f"Research report: {report.report_id}",
            f"Instrument: {report.instrument_id}",
            f"Status: {report.status.value}",
            f"Confidence: {report.confidence.confidence:.1f}",
            f"Thesis: {report.thesis}",
            f"Counter thesis: {report.counter_thesis}",
            _section("Key findings", report.key_findings),
            _section("Key risks", report.key_risks),
            _section("Thesis invalidation conditions", invalidations),
            _section("Unresolved questions", report.unresolved_questions),
        )
    )
    return NotificationContent(
        subject=f"ResearchReport {report.report_id}",
        body=body,
        priority=NotificationPriority.NORMAL,
        template_version=f"{NOTIFICATION_ENGINE_VERSION}:research-report-v1",
    )


def render_validation_report(report: ValidationReport) -> NotificationContent:
    priority = NotificationPriority.NORMAL
    if report.aggregate_status in {
        ValidationStatus.UNRELIABLE,
        ValidationStatus.FAILED_INTEGRITY_CHECK,
    }:
        priority = NotificationPriority.HIGH
    findings = tuple(
        finding
        for assessment in report.assessments
        for finding in assessment.findings[:2]
    )
    risks = tuple(
        risk for assessment in report.assessments for risk in assessment.risks[:2]
    )
    body = _body(
        (
            f"Validation report: {report.report_id}",
            f"Validation run: {report.validation_id}",
            f"Status: {report.status.value}",
            f"Aggregate status: {report.aggregate_status.value}",
            f"Assessment count: {len(report.assessments)}",
            f"Framework version: {report.framework_snapshot.framework_version}",
            f"Database schema version: {report.framework_snapshot.database_schema_version}",
            _section("Findings", findings),
            _section("Risks", risks),
            _section("Known limitations", report.known_limitations),
        )
    )
    return NotificationContent(
        subject=f"ValidationReport {report.report_id}",
        body=body,
        priority=priority,
        template_version=f"{NOTIFICATION_ENGINE_VERSION}:validation-report-v1",
    )


def render_portfolio_proposal(proposal: PortfolioProposal) -> NotificationContent:
    priority = NotificationPriority.NORMAL
    if proposal.status in {
        PortfolioProposalStatus.CONDITIONAL,
        PortfolioProposalStatus.REJECTED,
        PortfolioProposalStatus.INCOMPLETE,
    }:
        priority = NotificationPriority.HIGH
    body = _body(
        (
            f"Portfolio proposal: {proposal.proposal_id}",
            f"Status: {proposal.status.value}",
            f"As of: {proposal.as_of.isoformat()}",
            f"Base currency: {proposal.base_currency}",
            f"Position count: {len(proposal.positions)}",
            f"Cash weight: {proposal.cash_weight:.2%}",
            f"Expected volatility: {proposal.expected_portfolio_volatility:.2%}",
            f"Expected maximum drawdown: {proposal.expected_max_drawdown:.2%}",
            _section("Reasons", proposal.reasons),
            _section("Limitations", proposal.limitations),
        )
    )
    return NotificationContent(
        subject=f"PortfolioProposal {proposal.proposal_id}",
        body=body,
        priority=priority,
        template_version=f"{NOTIFICATION_ENGINE_VERSION}:portfolio-proposal-v1",
    )


def render_risk_assessment(assessment: RiskAssessment) -> NotificationContent:
    priority = NotificationPriority.NORMAL
    if assessment.status in {
        RiskAssessmentStatus.CONDITIONAL,
        RiskAssessmentStatus.REJECTED,
        RiskAssessmentStatus.INCOMPLETE,
    }:
        priority = NotificationPriority.HIGH
    scenarios = tuple(
        f"{result.scenario.name}: estimated loss {result.estimated_loss:.2%}"
        for result in assessment.scenario_results
    )
    body = _body(
        (
            f"Risk assessment: {assessment.assessment_id}",
            f"Portfolio proposal: {assessment.proposal_id}",
            f"Status: {assessment.status.value}",
            f"Risk score: {assessment.score:.1f}",
            f"Confidence: {assessment.confidence:.1f}",
            f"Concentration risk: {assessment.concentration_risk:.1f}",
            f"Correlation risk: {assessment.correlation_risk:.1f}",
            f"Liquidity risk: {assessment.liquidity_risk:.1f}",
            _section("Scenario stress results", scenarios),
            _section("Required adjustments", assessment.required_adjustments),
            _section("Reasons", assessment.reasons),
            _section("Limitations", assessment.limitations),
        )
    )
    return NotificationContent(
        subject=f"RiskAssessment {assessment.assessment_id}",
        body=body,
        priority=priority,
        template_version=f"{NOTIFICATION_ENGINE_VERSION}:risk-assessment-v1",
    )


def _body(lines: Iterable[str]) -> str:
    content = "\n\n".join(line for line in lines if line.strip())
    return redact_sensitive_text(f"{content}\n\n{RESEARCH_DISCLAIMER}")


def _section(title: str, values: Iterable[str]) -> str:
    selected = tuple(value for value in values if value.strip())[:5]
    if not selected:
        return ""
    return "\n".join((f"{title}:", *(f"- {value}" for value in selected)))


__all__ = [
    "render_portfolio_proposal",
    "render_research_report",
    "render_risk_assessment",
    "render_validation_report",
]
