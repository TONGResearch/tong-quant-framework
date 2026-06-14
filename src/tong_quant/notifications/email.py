class EmailChannel:
    channel_id = "email"

    def send_signal(self, signal: object) -> str:
        del signal
        raise NotImplementedError("Email integration is not enabled")

    def send_message(self, subject: str, body: str) -> str:
        del subject, body
        raise NotImplementedError("Email integration is not enabled")
