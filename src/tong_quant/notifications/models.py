from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from tong_quant.domain.models import require_timezone
from tong_quant.notifications.security import contains_sensitive_assignment

RESEARCH_DISCLAIMER = "\n".join(
    (
        "This is research information only.",
        "It is not investment advice.",
        "It is not an execution instruction.",
    )
)


class NotificationMode(StrEnum):
    DISABLED = "disabled"
    PREVIEW = "preview"
    ENABLED = "enabled"


class NotificationArtifactType(StrEnum):
    RESEARCH_REPORT = "research_report"
    VALIDATION_REPORT = "validation_report"
    PORTFOLIO_PROPOSAL = "portfolio_proposal"
    RISK_ASSESSMENT = "risk_assessment"


class NotificationPriority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class NotificationStatus(StrEnum):
    PREVIEW = "preview"
    PENDING = "pending"
    DISPATCHING = "dispatching"
    RETRY = "retry"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryStatus(StrEnum):
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class NotificationTarget:
    channel: str
    recipient: str

    def __post_init__(self) -> None:
        if not self.channel.strip() or not self.recipient.strip():
            raise ValueError("notification target requires channel and recipient")
        if "://" in self.recipient or contains_sensitive_assignment(self.recipient):
            raise ValueError("notification recipient must be a logical destination")


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    artifact_type: NotificationArtifactType
    artifact_id: str
    artifact_hash: str
    artifact_version: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.occurred_at, "artifact occurred_at")
        values = (
            self.artifact_id,
            self.artifact_hash,
            self.artifact_version,
        )
        if any(not value.strip() for value in values):
            raise ValueError("artifact reference fields must not be empty")
        if len(self.artifact_hash) != 64:
            raise ValueError("artifact_hash must be a SHA-256 digest")


@dataclass(frozen=True, slots=True)
class NotificationContent:
    subject: str
    body: str
    priority: NotificationPriority
    template_version: str

    def __post_init__(self) -> None:
        if not self.subject.strip() or not self.template_version.strip():
            raise ValueError("notification content requires subject and template version")
        if RESEARCH_DISCLAIMER not in self.body:
            raise ValueError("notification body must contain the research disclaimer")
        if contains_sensitive_assignment(f"{self.subject}\n{self.body}"):
            raise ValueError("notification content contains an unredacted sensitive value")


@dataclass(frozen=True, slots=True)
class NotificationRecord:
    notification_id: str
    reference: ArtifactReference
    channel: str
    recipient: str
    subject: str
    body: str
    priority: NotificationPriority
    template_version: str
    dedup_key: str
    status: NotificationStatus
    attempt_count: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    next_attempt_at: datetime | None = None
    last_error_code: str = ""

    def __post_init__(self) -> None:
        require_timezone(self.created_at, "notification created_at")
        require_timezone(self.updated_at, "notification updated_at")
        if self.next_attempt_at is not None:
            require_timezone(self.next_attempt_at, "notification next_attempt_at")
        values = (
            self.notification_id,
            self.channel,
            self.recipient,
            self.subject,
            self.template_version,
            self.dedup_key,
        )
        if any(not value.strip() for value in values):
            raise ValueError("notification record fields must not be empty")
        if "://" in self.recipient or contains_sensitive_assignment(self.recipient):
            raise ValueError("notification recipient must be a logical destination")
        if RESEARCH_DISCLAIMER not in self.body:
            raise ValueError("notification record must contain the research disclaimer")
        if contains_sensitive_assignment(f"{self.subject}\n{self.body}"):
            raise ValueError("notification record contains an unredacted sensitive value")
        if len(self.dedup_key) != 64:
            raise ValueError("dedup_key must be a SHA-256 digest")
        if self.max_attempts <= 0 or not 0 <= self.attempt_count <= self.max_attempts:
            raise ValueError("notification attempt counters are invalid")

    def message(self) -> "NotificationMessage":
        return NotificationMessage(
            notification_id=self.notification_id,
            channel=self.channel,
            recipient=self.recipient,
            subject=self.subject,
            body=self.body,
        )


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    notification_id: str
    channel: str
    recipient: str
    subject: str
    body: str

    def __post_init__(self) -> None:
        values = (self.notification_id, self.channel, self.recipient, self.subject)
        if any(not value.strip() for value in values):
            raise ValueError("notification message fields must not be empty")
        if "://" in self.recipient or contains_sensitive_assignment(self.recipient):
            raise ValueError("notification recipient must be a logical destination")
        if RESEARCH_DISCLAIMER not in self.body:
            raise ValueError("notification message must contain the research disclaimer")
        if contains_sensitive_assignment(f"{self.subject}\n{self.body}"):
            raise ValueError("notification message contains an unredacted sensitive value")


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    provider_message_id: str
    delivered_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.delivered_at, "notification delivered_at")
        if not self.provider_message_id.strip():
            raise ValueError("delivery receipt requires provider_message_id")


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    delivery_id: str
    notification_id: str
    channel: str
    recipient: str
    status: DeliveryStatus
    attempt_number: int
    attempted_at: datetime
    delivered_at: datetime | None
    provider_message_id: str
    error_code: str

    def __post_init__(self) -> None:
        require_timezone(self.attempted_at, "delivery attempted_at")
        if self.delivered_at is not None:
            require_timezone(self.delivered_at, "delivery delivered_at")
        if self.attempt_number <= 0:
            raise ValueError("delivery attempt number must be positive")
        if self.status is DeliveryStatus.DELIVERED and not self.provider_message_id:
            raise ValueError("delivered notification requires provider message id")
        if self.status is DeliveryStatus.FAILED and not self.error_code:
            raise ValueError("failed notification requires error code")


@dataclass(frozen=True, slots=True)
class DispatchSummary:
    attempted: int
    delivered: int
    failed: int
    deferred: int


__all__ = [
    "ArtifactReference",
    "DeliveryReceipt",
    "DeliveryRecord",
    "DeliveryStatus",
    "DispatchSummary",
    "NotificationArtifactType",
    "NotificationContent",
    "NotificationMessage",
    "NotificationMode",
    "NotificationPriority",
    "NotificationRecord",
    "NotificationStatus",
    "NotificationTarget",
    "RESEARCH_DISCLAIMER",
]
