import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    Market,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    ValidationModuleName,
    ValidationRunStatus,
    ValidationStatus,
)
from tong_quant.domain.models import Instrument
from tong_quant.notifications import (
    RESEARCH_DISCLAIMER,
    DeliveryReceipt,
    NotificationArtifactType,
    NotificationContent,
    NotificationDispatcher,
    NotificationMessage,
    NotificationMode,
    NotificationPriority,
    NotificationService,
    NotificationStatus,
    NotificationTarget,
    SQLiteNotificationRepository,
)
from tong_quant.notifications.security import redact_sensitive_text
from tong_quant.portfolio import PortfolioCandidate, PortfolioProposal, PortfolioProposalEngine
from tong_quant.research.models import (
    ConfidenceBreakdown,
    ResearchAssessment,
    ResearchReport,
    ThesisInvalidationCondition,
)
from tong_quant.validation.models import (
    FrameworkSnapshot,
    ValidationAssessment,
    ValidationReport,
)
from tong_quant.version import (
    DATABASE_SCHEMA_VERSION,
    FRAMEWORK_VERSION,
    NOTIFICATION_ENGINE_VERSION,
    RESEARCH_ENGINE_VERSION,
    VALIDATION_ENGINE_VERSION,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def test_notification_and_schema_versions_are_v08() -> None:
    assert DATABASE_SCHEMA_VERSION == "0.8.0"
    assert FRAMEWORK_VERSION == "0.8.0"
    assert NOTIFICATION_ENGINE_VERSION == "notification-engine-v0.8"


def test_enabled_outbox_separates_generation_from_fake_channel_delivery(
    tmp_path: Path,
) -> None:
    store, repository = _repository(tmp_path)
    channel = _FakeChannel()
    service = NotificationService(
        repository=repository,
        mode=NotificationMode.ENABLED,
        clock=lambda: NOW,
    )

    first = service.generate_research_report(_research_report(), (_target(),))[0]
    second = service.generate_research_report(_research_report(), (_target(),))[0]

    assert channel.messages == []
    assert first.notification_id == second.notification_id
    assert store.table_count("notification_outbox") == 1
    assert first.status is NotificationStatus.PENDING
    assert RESEARCH_DISCLAIMER in first.body

    summary = NotificationDispatcher(
        repository=repository,
        channels={channel.channel_id: channel},
        mode=NotificationMode.ENABLED,
        clock=lambda: NOW,
    ).dispatch_pending()

    assert summary.attempted == 1
    assert summary.delivered == 1
    assert len(channel.messages) == 1
    assert store.table_count("notification_deliveries") == 1
    delivered = repository.get_by_dedup_key(first.dedup_key)
    assert delivered is not None
    assert delivered.status is NotificationStatus.DELIVERED


def test_disabled_and_preview_modes_never_deliver(tmp_path: Path) -> None:
    store, repository = _repository(tmp_path)
    target = (_target(),)

    disabled = NotificationService(repository=repository, mode=NotificationMode.DISABLED)
    assert disabled.generate_research_report(_research_report(), target) == ()
    assert store.table_count("notification_outbox") == 0

    preview = NotificationService(
        repository=repository,
        mode=NotificationMode.PREVIEW,
        clock=lambda: NOW,
    )
    record = preview.generate_research_report(_research_report(), target)[0]
    channel = _FakeChannel()
    summary = NotificationDispatcher(
        repository=repository,
        channels={channel.channel_id: channel},
        mode=NotificationMode.ENABLED,
        clock=lambda: NOW,
    ).dispatch_pending()

    assert record.status is NotificationStatus.PREVIEW
    assert summary.attempted == 0
    assert channel.messages == []


def test_all_supported_research_artifacts_generate_notifications(tmp_path: Path) -> None:
    store, repository = _repository(tmp_path)
    service = NotificationService(
        repository=repository,
        mode=NotificationMode.PREVIEW,
        clock=lambda: NOW,
    )
    proposal = _portfolio_proposal()
    assert proposal.risk_assessment is not None

    records = (
        *service.generate_research_report(_research_report(), (_target(),)),
        *service.generate_validation_report(_validation_report(), (_target(),)),
        *service.generate_portfolio_proposal(proposal, (_target(),)),
        *service.generate_risk_assessment(proposal.risk_assessment, (_target(),)),
    )

    assert {record.reference.artifact_type for record in records} == {
        NotificationArtifactType.RESEARCH_REPORT,
        NotificationArtifactType.VALIDATION_REPORT,
        NotificationArtifactType.PORTFOLIO_PROPOSAL,
        NotificationArtifactType.RISK_ASSESSMENT,
    }
    assert all(RESEARCH_DISCLAIMER in record.body for record in records)
    assert store.table_count("notification_outbox") == 4


def test_failed_delivery_records_safe_error_and_schedules_retry(tmp_path: Path) -> None:
    _, repository = _repository(tmp_path)
    service = NotificationService(
        repository=repository,
        mode=NotificationMode.ENABLED,
        max_attempts=2,
        clock=lambda: NOW,
    )
    record = service.generate_research_report(_research_report(), (_target(),))[0]
    channel = _FakeChannel(fail=True)

    summary = NotificationDispatcher(
        repository=repository,
        channels={channel.channel_id: channel},
        mode=NotificationMode.ENABLED,
        clock=lambda: NOW,
    ).dispatch_pending()

    assert summary.failed == 1
    retriable = repository.get_by_dedup_key(record.dedup_key)
    assert retriable is not None
    assert retriable.status is NotificationStatus.RETRY
    assert retriable.last_error_code == "RuntimeError"
    deliveries = repository.deliveries(record.notification_id)
    assert deliveries[0].error_code == "RuntimeError"


def test_notification_schema_has_no_credential_columns(tmp_path: Path) -> None:
    store, _ = _repository(tmp_path)
    forbidden = ("credential", "password", "secret", "token", "webhook")
    with sqlite3.connect(store.path) as connection:
        columns = {
            str(row[1]).lower()
            for table in ("notification_outbox", "notification_deliveries")
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }

    assert not any(term in column for column in columns for term in forbidden)


def test_unredacted_sensitive_assignment_cannot_enter_notification_record() -> None:
    synthetic_assignment = "api" + "_key=" + "synthetic-value"
    with pytest.raises(ValueError, match="unredacted sensitive value"):
        NotificationContent(
            subject="Research information",
            body=f"{synthetic_assignment}\n\n{RESEARCH_DISCLAIMER}",
            priority=NotificationPriority.NORMAL,
            template_version="test",
        )

    sanitized = redact_sensitive_text(synthetic_assignment)
    assert "synthetic-value" not in sanitized
    assert "[REDACTED]" in sanitized


def test_webhook_url_cannot_be_persisted_as_recipient() -> None:
    with pytest.raises(ValueError, match="logical destination"):
        NotificationTarget(channel="wechat", recipient="https://provider.invalid/hook")


@dataclass(slots=True)
class _FakeChannel:
    channel_id: str = "fake"
    fail: bool = False
    messages: list[NotificationMessage] = field(default_factory=list)

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if self.fail:
            raise RuntimeError
        self.messages.append(message)
        return DeliveryReceipt(provider_message_id="fake-message-1", delivered_at=NOW)


def _repository(tmp_path: Path) -> tuple[SQLiteStore, SQLiteNotificationRepository]:
    store = SQLiteStore(tmp_path / "notifications.sqlite3")
    store.initialize()
    return store, SQLiteNotificationRepository(store)


def _target() -> NotificationTarget:
    return NotificationTarget(channel="fake", recipient="research-review")


def _confidence() -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        evidence_quality=80,
        data_completeness=80,
        module_agreement=80,
        point_in_time_integrity=100,
        confidence=80,
    )


def _research_report() -> ResearchReport:
    assessment = ResearchAssessment(
        module=ResearchModuleName.VALUE,
        conclusion=ResearchConclusion.SUPPORTIVE,
        score=75,
        confidence=_confidence(),
        evaluated_at=NOW,
        available_at=NOW,
        findings=("Evidence supports continued research",),
        risks=("Evidence may weaken",),
        limitations=(),
        evidence_ids=("evidence-1",),
        model_version="value-v0.5",
    )
    return ResearchReport(
        report_id="research-report-1",
        queue_id="queue-1",
        instrument_id="china_a:equity:600000",
        generated_at=NOW,
        available_at=NOW,
        status=ResearchRunStatus.COMPLETED,
        thesis="Fundamentals may improve",
        counter_thesis="Demand may weaken",
        invalidation_conditions=(
            ThesisInvalidationCondition(
                condition_id="growth",
                description="Revenue growth falls below zero",
                metric="revenue_growth",
                operator="<",
                threshold=0,
                observation_window="two quarters",
                rationale="Growth is required",
            ),
        ),
        assessments=(assessment,),
        policy_assessment=None,
        confidence=_confidence(),
        key_findings=("Evidence supports continued research",),
        key_risks=("Demand may weaken",),
        unresolved_questions=("Can margins remain durable?",),
        market_regime=None,
        model_version="research-engine-v0.5",
    )


def _validation_report() -> ValidationReport:
    assessment = ValidationAssessment(
        module=ValidationModuleName.HISTORICAL,
        status=ValidationStatus.RELIABLE,
        score=80,
        confidence=75,
        sample_size=500,
        evaluated_at=NOW,
        metrics={"accuracy": 70},
        findings=("Historical evidence is stable",),
        risks=("Regime coverage remains limited",),
        limitations=("Limited market history",),
        integrity_checks=(),
        model_version="historical-v0.6",
    )
    snapshot = FrameworkSnapshot(
        git_commit="533c9a4fbed7d80b2837ea83d1a5fb1b5c716b78",
        framework_version=FRAMEWORK_VERSION,
        configuration_hash="0" * 64,
        research_version=RESEARCH_ENGINE_VERSION,
        validation_version=VALIDATION_ENGINE_VERSION,
        database_schema_version=DATABASE_SCHEMA_VERSION,
        captured_at=NOW,
    )
    return ValidationReport(
        report_id="validation-report-1",
        validation_id="validation-1",
        generated_at=NOW,
        status=ValidationRunStatus.COMPLETED,
        aggregate_status=ValidationStatus.RELIABLE,
        assessments=(assessment,),
        framework_snapshot=snapshot,
        splits=(),
        factor_contributions=(),
        accuracy=None,
        decision_summary=None,
        portfolio_risk=None,
        known_limitations=("Limited market history",),
        reproducibility_manifest={"configuration_hash": "0" * 64},
        model_version="validation-engine-v0.6",
    )


def _portfolio_proposal() -> PortfolioProposal:
    candidate = PortfolioCandidate(
        instrument=Instrument(
            symbol="600000",
            market=Market.CHINA_A,
            name="Example",
            industry="Banks",
            available_at=NOW,
            source="test",
        ),
        investment_assessment_id="investment-assessment-1",
        investment_score_id="investment-score-1",
        validation_report_id="validation-report-1",
        score=80,
        confidence=75,
        assessment_status=InvestmentAssessmentStatus.COMPLETED,
        validation_status="reliable",
        expected_role="value",
        sector="Banks",
        country="China",
        theme="Value",
        volatility=0.18,
        liquidity_score=85,
        average_correlation=0.3,
        max_drawdown=0.2,
        reasons=("Research and validation completed",),
    )
    return PortfolioProposalEngine().build((candidate,), as_of=NOW)
