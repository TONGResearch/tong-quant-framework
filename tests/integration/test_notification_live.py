import os
from datetime import UTC, datetime

import pytest

from tong_quant.notifications.base import NotificationChannel
from tong_quant.notifications.email import EmailChannel
from tong_quant.notifications.models import RESEARCH_DISCLAIMER, NotificationMessage
from tong_quant.notifications.telegram import TelegramChannel
from tong_quant.notifications.wechat import WeChatChannel

pytestmark = [
    pytest.mark.live_notification,
    pytest.mark.skipif(
        os.getenv("TONG_QUANT_RUN_LIVE_NOTIFICATION_TESTS") != "1",
        reason="set TONG_QUANT_RUN_LIVE_NOTIFICATION_TESTS=1 for live notification tests",
    ),
]


@pytest.mark.parametrize(
    ("channel", "recipient_environment"),
    (
        (TelegramChannel(), "TONG_QUANT_TELEGRAM_TEST_RECIPIENT"),
        (WeChatChannel(), "TONG_QUANT_WECHAT_TEST_RECIPIENT"),
        (EmailChannel(), "TONG_QUANT_EMAIL_TEST_RECIPIENT"),
    ),
)
def test_live_notification_channel(
    channel: NotificationChannel,
    recipient_environment: str,
) -> None:
    recipient = os.getenv(recipient_environment)
    if not recipient:
        pytest.skip(f"set {recipient_environment} to run this provider test")
    message = NotificationMessage(
        notification_id=f"live-{datetime.now(UTC).isoformat()}",
        channel=channel.channel_id,
        recipient=recipient,
        subject="Tong Quant live notification test",
        body=RESEARCH_DISCLAIMER,
    )

    receipt = channel.send(message)

    assert receipt.provider_message_id
