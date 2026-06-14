class WeChatChannel:
    channel_id = "wechat"

    def send_signal(self, signal: object) -> str:
        del signal
        raise NotImplementedError("WeChat integration is not enabled")

    def send_message(self, subject: str, body: str) -> str:
        del subject, body
        raise NotImplementedError("WeChat integration is not enabled")
