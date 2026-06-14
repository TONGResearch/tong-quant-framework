from typing import Protocol

from tong_quant.domain.models import Signal


class NotificationChannel(Protocol):
    channel_id: str

    def send_signal(self, signal: Signal) -> str: ...

    def send_message(self, subject: str, body: str) -> str: ...
