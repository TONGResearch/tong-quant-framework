from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tong_quant.notifications.base import NotificationChannel, NotificationOutboxRepository
from tong_quant.notifications.models import DispatchSummary, NotificationMode
from tong_quant.notifications.security import safe_error_code


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class NotificationDispatcher:
    repository: NotificationOutboxRepository
    channels: Mapping[str, NotificationChannel]
    mode: NotificationMode = NotificationMode.DISABLED
    retry_delay: timedelta = timedelta(minutes=5)
    lease_timeout: timedelta = timedelta(minutes=5)
    clock: Callable[[], datetime] = _utc_now

    def dispatch_pending(self, *, limit: int = 100) -> DispatchSummary:
        if limit <= 0:
            raise ValueError("notification dispatch limit must be positive")
        if self.lease_timeout <= timedelta(0):
            raise ValueError("notification lease timeout must be positive")
        if self.mode is not NotificationMode.ENABLED:
            return DispatchSummary(attempted=0, delivered=0, failed=0, deferred=0)
        now = self.clock()
        recovery = self.repository.recover_orphaned(as_of=now)
        pending = self.repository.pending(as_of=now, limit=limit)
        attempted = delivered = failed = deferred = 0
        dead_lettered = recovery.dead_lettered
        for candidate in pending:
            record = self.repository.claim(
                candidate.notification_id,
                claimed_at=now,
                lease_expires_at=now + self.lease_timeout,
            )
            if record is None:
                deferred += 1
                continue
            attempted += 1
            channel = self.channels.get(record.channel)
            if channel is None or channel.channel_id != record.channel:
                self.repository.mark_failed(
                    record,
                    attempted_at=now,
                    error_code="ChannelUnavailable",
                    retry_at=None,
                )
                failed += 1
                dead_lettered += 1
                continue
            try:
                receipt = channel.send(record.message())
            except Exception as error:
                retry_at = None
                if record.attempt_count < record.max_attempts:
                    retry_at = now + self.retry_delay
                self.repository.mark_failed(
                    record,
                    attempted_at=now,
                    error_code=safe_error_code(error),
                    retry_at=retry_at,
                )
                failed += 1
                if retry_at is None:
                    dead_lettered += 1
                continue
            self.repository.mark_delivered(record, receipt)
            delivered += 1
        return DispatchSummary(
            attempted=attempted,
            delivered=delivered,
            failed=failed,
            deferred=deferred,
            recovered=recovery.recovered,
            dead_lettered=dead_lettered,
        )


__all__ = ["NotificationDispatcher"]
