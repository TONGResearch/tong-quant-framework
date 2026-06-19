from datetime import datetime
from typing import Protocol

from tong_quant.notifications.models import (
    DeadLetterRecord,
    DeliveryReceipt,
    DeliveryRecord,
    NotificationMessage,
    NotificationRecord,
    OutboxRecoverySummary,
)


class NotificationChannel(Protocol):
    channel_id: str

    def send(self, message: NotificationMessage) -> DeliveryReceipt: ...


class NotificationOutboxRepository(Protocol):
    def enqueue(self, record: NotificationRecord) -> NotificationRecord: ...

    def get_by_dedup_key(self, dedup_key: str) -> NotificationRecord | None: ...

    def pending(self, *, as_of: datetime, limit: int) -> tuple[NotificationRecord, ...]: ...

    def claim(
        self,
        notification_id: str,
        *,
        claimed_at: datetime,
        lease_expires_at: datetime,
    ) -> NotificationRecord | None: ...

    def recover_orphaned(self, *, as_of: datetime) -> OutboxRecoverySummary: ...

    def mark_delivered(
        self,
        record: NotificationRecord,
        receipt: DeliveryReceipt,
    ) -> DeliveryRecord: ...

    def mark_failed(
        self,
        record: NotificationRecord,
        *,
        attempted_at: datetime,
        error_code: str,
        retry_at: datetime | None,
    ) -> DeliveryRecord: ...

    def deliveries(self, notification_id: str) -> tuple[DeliveryRecord, ...]: ...

    def dead_letters(self, notification_id: str) -> tuple[DeadLetterRecord, ...]: ...


__all__ = ["NotificationChannel", "NotificationOutboxRepository"]
