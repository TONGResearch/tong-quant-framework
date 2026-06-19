import json
import os
from datetime import UTC, datetime
from urllib.request import Request, urlopen
from uuid import uuid4

from tong_quant.notifications.models import DeliveryReceipt, NotificationMessage


class WeChatChannel:
    channel_id = "wechat"

    def send(self, message: NotificationMessage) -> DeliveryReceipt:
        if message.channel != self.channel_id:
            raise ValueError("notification message channel mismatch")
        webhook_url = os.getenv("TONG_QUANT_WECHAT_WEBHOOK_URL")
        if not webhook_url:
            raise RuntimeError("WeChat credentials are unavailable")
        payload = json.dumps(
            {
                "msgtype": "text",
                "text": {"content": f"{message.subject}\n\n{message.body}"},
            }
        ).encode("utf-8")
        request = Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                result = json.loads(response.read().decode("utf-8"))
        except Exception:
            raise RuntimeError("WeChat delivery failed") from None
        if int(result.get("errcode", -1)) != 0:
            raise RuntimeError("WeChat delivery failed")
        return DeliveryReceipt(
            provider_message_id=f"wechat-{uuid4()}",
            delivered_at=datetime.now(UTC),
        )


__all__ = ["WeChatChannel"]
