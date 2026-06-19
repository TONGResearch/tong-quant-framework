import os
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import make_msgid

from tong_quant.notifications.models import DeliveryReceipt, NotificationMessage


class EmailChannel:
    channel_id = "email"

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if message.channel != self.channel_id:
            raise ValueError("notification message channel mismatch")
        host = os.getenv("TONG_QUANT_SMTP_HOST")
        username = os.getenv("TONG_QUANT_SMTP_USERNAME")
        password = os.getenv("TONG_QUANT_SMTP_PASSWORD")
        sender = os.getenv("TONG_QUANT_SMTP_FROM")
        port_text = os.getenv("TONG_QUANT_SMTP_PORT", "587")
        if not all((host, username, password, sender)):
            raise RuntimeError("Email credentials are unavailable")
        assert host is not None
        assert username is not None
        assert password is not None
        assert sender is not None
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = sender
        email["To"] = message.recipient
        email["Message-ID"] = make_msgid()
        email.set_content(message.body)
        try:
            with smtplib.SMTP(host, int(port_text), timeout=15) as client:
                client.starttls()
                client.login(username, password)
                client.send_message(email)
        except Exception:
            raise RuntimeError("Email delivery failed") from None
        return DeliveryReceipt(
            provider_message_id=str(email["Message-ID"]),
            delivered_at=datetime.now(UTC),
        )


__all__ = ["EmailChannel"]
