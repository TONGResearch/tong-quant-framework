from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from tong_quant.portfolio.models import PortfolioProposal
    from tong_quant.research.models import ResearchReport
    from tong_quant.risk.models import RiskAssessment
    from tong_quant.validation.models import ValidationReport


class NotificationChannel(Protocol):
    channel_id: str

    def send_research_report(self, report: ResearchReport) -> str: ...

    def send_validation_report(self, report: ValidationReport) -> str: ...

    def send_portfolio_proposal(self, proposal: PortfolioProposal) -> str: ...

    def send_risk_assessment(self, assessment: RiskAssessment) -> str: ...

    def send_message(self, subject: str, body: str) -> str: ...
