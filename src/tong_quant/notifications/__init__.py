"""Research-artifact notification generation and deferred delivery."""

from tong_quant.notifications.base import NotificationChannel, NotificationOutboxRepository
from tong_quant.notifications.dispatcher import NotificationDispatcher
from tong_quant.notifications.models import (
    RESEARCH_DISCLAIMER,
    ArtifactReference,
    DeadLetterRecord,
    DeliveryReceipt,
    DeliveryRecord,
    DeliveryStatus,
    DispatchSummary,
    NotificationArtifactType,
    NotificationContent,
    NotificationMessage,
    NotificationMode,
    NotificationPriority,
    NotificationRecord,
    NotificationStatus,
    NotificationTarget,
    OutboxRecoverySummary,
)
from tong_quant.notifications.repository import SQLiteNotificationRepository
from tong_quant.notifications.service import NotificationService

__all__ = [
    "ArtifactReference",
    "DeadLetterRecord",
    "DeliveryReceipt",
    "DeliveryRecord",
    "DeliveryStatus",
    "DispatchSummary",
    "NotificationArtifactType",
    "NotificationChannel",
    "NotificationContent",
    "NotificationDispatcher",
    "NotificationMessage",
    "NotificationMode",
    "NotificationOutboxRepository",
    "NotificationPriority",
    "NotificationRecord",
    "NotificationService",
    "NotificationStatus",
    "NotificationTarget",
    "OutboxRecoverySummary",
    "RESEARCH_DISCLAIMER",
    "SQLiteNotificationRepository",
]
