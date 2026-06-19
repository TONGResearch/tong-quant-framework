from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from tong_quant.notifications.base import NotificationOutboxRepository
from tong_quant.notifications.hashing import artifact_hash, notification_dedup_key
from tong_quant.notifications.models import (
    ArtifactReference,
    NotificationArtifactType,
    NotificationContent,
    NotificationMode,
    NotificationRecord,
    NotificationStatus,
    NotificationTarget,
)
from tong_quant.notifications.rendering import (
    render_portfolio_proposal,
    render_research_report,
    render_risk_assessment,
    render_validation_report,
)
from tong_quant.portfolio.models import PortfolioProposal
from tong_quant.research.models import ResearchReport
from tong_quant.risk.models import RiskAssessment
from tong_quant.validation.models import ValidationReport


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class NotificationService:
    repository: NotificationOutboxRepository
    mode: NotificationMode = NotificationMode.DISABLED
    max_attempts: int = 3
    clock: Callable[[], datetime] = _utc_now

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("notification max_attempts must be positive")

    def generate_research_report(
        self,
        report: ResearchReport,
        targets: tuple[NotificationTarget, ...],
    ) -> tuple[NotificationRecord, ...]:
        return self._generate(
            artifact=report,
            artifact_type=NotificationArtifactType.RESEARCH_REPORT,
            artifact_id=report.report_id,
            artifact_version=report.model_version,
            occurred_at=report.available_at,
            content=render_research_report(report),
            targets=targets,
        )

    def generate_validation_report(
        self,
        report: ValidationReport,
        targets: tuple[NotificationTarget, ...],
    ) -> tuple[NotificationRecord, ...]:
        return self._generate(
            artifact=report,
            artifact_type=NotificationArtifactType.VALIDATION_REPORT,
            artifact_id=report.report_id,
            artifact_version=report.model_version,
            occurred_at=report.generated_at,
            content=render_validation_report(report),
            targets=targets,
        )

    def generate_portfolio_proposal(
        self,
        proposal: PortfolioProposal,
        targets: tuple[NotificationTarget, ...],
    ) -> tuple[NotificationRecord, ...]:
        return self._generate(
            artifact=proposal,
            artifact_type=NotificationArtifactType.PORTFOLIO_PROPOSAL,
            artifact_id=proposal.proposal_id,
            artifact_version=proposal.model_version,
            occurred_at=proposal.as_of,
            content=render_portfolio_proposal(proposal),
            targets=targets,
        )

    def generate_risk_assessment(
        self,
        assessment: RiskAssessment,
        targets: tuple[NotificationTarget, ...],
    ) -> tuple[NotificationRecord, ...]:
        return self._generate(
            artifact=assessment,
            artifact_type=NotificationArtifactType.RISK_ASSESSMENT,
            artifact_id=assessment.assessment_id,
            artifact_version=assessment.model_version,
            occurred_at=assessment.assessed_at,
            content=render_risk_assessment(assessment),
            targets=targets,
        )

    def _generate(
        self,
        *,
        artifact: ResearchReport | ValidationReport | PortfolioProposal | RiskAssessment,
        artifact_type: NotificationArtifactType,
        artifact_id: str,
        artifact_version: str,
        occurred_at: datetime,
        content: NotificationContent,
        targets: tuple[NotificationTarget, ...],
    ) -> tuple[NotificationRecord, ...]:
        if self.mode is NotificationMode.DISABLED:
            return ()
        if not targets:
            raise ValueError("notification generation requires at least one target")
        now = self.clock()
        digest = artifact_hash(artifact)
        reference = ArtifactReference(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_hash=digest,
            artifact_version=artifact_version,
            occurred_at=occurred_at,
        )
        status = (
            NotificationStatus.PREVIEW
            if self.mode is NotificationMode.PREVIEW
            else NotificationStatus.PENDING
        )
        records = []
        for target in targets:
            record = NotificationRecord(
                notification_id=str(uuid4()),
                reference=reference,
                channel=target.channel,
                recipient=target.recipient,
                subject=content.subject,
                body=content.body,
                priority=content.priority,
                template_version=content.template_version,
                dedup_key=notification_dedup_key(
                    digest,
                    target.channel,
                    target.recipient,
                ),
                status=status,
                attempt_count=0,
                max_attempts=self.max_attempts,
                created_at=now,
                updated_at=now,
            )
            records.append(self.repository.enqueue(record))
        return tuple(records)


__all__ = ["NotificationService"]
