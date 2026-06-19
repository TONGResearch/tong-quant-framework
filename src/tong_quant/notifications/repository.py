import sqlite3
from dataclasses import dataclass
from datetime import datetime

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.notifications.models import (
    ArtifactReference,
    DeliveryReceipt,
    DeliveryRecord,
    DeliveryStatus,
    NotificationArtifactType,
    NotificationPriority,
    NotificationRecord,
    NotificationStatus,
)


@dataclass(slots=True)
class SQLiteNotificationRepository:
    store: SQLiteStore

    def enqueue(self, record: NotificationRecord) -> NotificationRecord:
        self.store.save_notification_outbox(
            notification_id=record.notification_id,
            artifact_type=record.reference.artifact_type.value,
            artifact_id=record.reference.artifact_id,
            artifact_hash=record.reference.artifact_hash,
            artifact_version=record.reference.artifact_version,
            artifact_occurred_at=record.reference.occurred_at,
            channel=record.channel,
            recipient=record.recipient,
            subject=record.subject,
            body=record.body,
            priority=record.priority.value,
            template_version=record.template_version,
            dedup_key=record.dedup_key,
            status=record.status.value,
            attempt_count=record.attempt_count,
            max_attempts=record.max_attempts,
            next_attempt_at=record.next_attempt_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_error_code=record.last_error_code,
        )
        stored = self.get_by_dedup_key(record.dedup_key)
        if stored is None:
            raise ValueError("notification outbox insert did not persist")
        return stored

    def get_by_dedup_key(self, dedup_key: str) -> NotificationRecord | None:
        row = self.store.notification_outbox_by_dedup_key(dedup_key)
        return None if row is None else _notification_from_row(row)

    def pending(self, *, as_of: datetime, limit: int) -> tuple[NotificationRecord, ...]:
        rows = self.store.pending_notification_outbox(as_of=as_of, limit=limit)
        return tuple(_notification_from_row(row) for row in rows)

    def claim(
        self,
        notification_id: str,
        *,
        claimed_at: datetime,
    ) -> NotificationRecord | None:
        row = self.store.claim_notification_outbox(
            notification_id,
            claimed_at=claimed_at,
        )
        return None if row is None else _notification_from_row(row)

    def mark_delivered(
        self,
        record: NotificationRecord,
        receipt: DeliveryReceipt,
    ) -> DeliveryRecord:
        row = self.store.complete_notification_delivery(
            notification_id=record.notification_id,
            channel=record.channel,
            recipient=record.recipient,
            attempt_number=record.attempt_count,
            attempted_at=receipt.delivered_at,
            delivered_at=receipt.delivered_at,
            provider_message_id=receipt.provider_message_id,
        )
        return _delivery_from_row(row)

    def mark_failed(
        self,
        record: NotificationRecord,
        *,
        attempted_at: datetime,
        error_code: str,
        retry_at: datetime | None,
    ) -> DeliveryRecord:
        row = self.store.fail_notification_delivery(
            notification_id=record.notification_id,
            channel=record.channel,
            recipient=record.recipient,
            attempt_number=record.attempt_count,
            attempted_at=attempted_at,
            error_code=error_code,
            retry_at=retry_at,
        )
        return _delivery_from_row(row)

    def deliveries(self, notification_id: str) -> tuple[DeliveryRecord, ...]:
        rows = self.store.notification_delivery_rows(notification_id)
        return tuple(_delivery_from_row(row) for row in rows)


def _notification_from_row(row: sqlite3.Row) -> NotificationRecord:
    return NotificationRecord(
        notification_id=row["notification_id"],
        reference=ArtifactReference(
            artifact_type=NotificationArtifactType(row["artifact_type"]),
            artifact_id=row["artifact_id"],
            artifact_hash=row["artifact_hash"],
            artifact_version=row["artifact_version"],
            occurred_at=datetime.fromisoformat(row["artifact_occurred_at"]),
        ),
        channel=row["channel"],
        recipient=row["recipient"],
        subject=row["subject"],
        body=row["body"],
        priority=NotificationPriority(row["priority"]),
        template_version=row["template_version"],
        dedup_key=row["dedup_key"],
        status=NotificationStatus(row["status"]),
        attempt_count=int(row["attempt_count"]),
        max_attempts=int(row["max_attempts"]),
        next_attempt_at=(
            None
            if row["next_attempt_at"] is None
            else datetime.fromisoformat(row["next_attempt_at"])
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_error_code=row["last_error_code"],
    )


def _delivery_from_row(row: sqlite3.Row) -> DeliveryRecord:
    return DeliveryRecord(
        delivery_id=row["delivery_id"],
        notification_id=row["notification_id"],
        channel=row["channel"],
        recipient=row["recipient"],
        status=DeliveryStatus(row["status"]),
        attempt_number=int(row["attempt_number"]),
        attempted_at=datetime.fromisoformat(row["attempted_at"]),
        delivered_at=(
            None
            if row["delivered_at"] is None
            else datetime.fromisoformat(row["delivered_at"])
        ),
        provider_message_id=row["provider_message_id"],
        error_code=row["error_code"],
    )


__all__ = ["SQLiteNotificationRepository"]
