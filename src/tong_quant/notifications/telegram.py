import json
import os
from datetime import UTC, datetime
from urllib.request import Request, urlopen

from tong_quant.notifications.models import DeliveryReceipt, NotificationMessage


class TelegramChannel:
    channel_id = "telegram"

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if message.channel != self.channel_id:
            raise ValueError("notification message channel mismatch")
        token = os.getenv("TONG_QUANT_TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("Telegram credentials are unavailable")
        payload = json.dumps(
            {
                "chat_id": message.recipient,
                "text": f"{message.subject}\n\n{message.body}",
            }
        ).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                result = json.loads(response.read().decode("utf-8"))
        except Exception:
            raise RuntimeError("Telegram delivery failed") from None
        message_id = result.get("result", {}).get("message_id")
        if not result.get("ok") or message_id is None:
            raise RuntimeError("Telegram delivery failed")
        return DeliveryReceipt(
            provider_message_id=str(message_id),
            delivered_at=datetime.now(UTC),
        )


__all__ = ["TelegramChannel"]
