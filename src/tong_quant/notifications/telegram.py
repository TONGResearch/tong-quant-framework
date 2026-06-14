class TelegramChannel:
    channel_id = "telegram"

    def send_signal(self, signal: object) -> str:
        del signal
        raise NotImplementedError("Telegram integration is not enabled")

    def send_message(self, subject: str, body: str) -> str:
        del subject, body
        raise NotImplementedError("Telegram integration is not enabled")
