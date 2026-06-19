class EmailChannel:
    channel_id = "email"

    def send_research_report(self, report: object) -> str:
        del report
        raise NotImplementedError("Email integration is not enabled")

    def send_validation_report(self, report: object) -> str:
        del report
        raise NotImplementedError("Email integration is not enabled")

    def send_portfolio_proposal(self, proposal: object) -> str:
        del proposal
        raise NotImplementedError("Email integration is not enabled")

    def send_risk_assessment(self, assessment: object) -> str:
        del assessment
        raise NotImplementedError("Email integration is not enabled")

    def send_message(self, subject: str, body: str) -> str:
        del subject, body
        raise NotImplementedError("Email integration is not enabled")
