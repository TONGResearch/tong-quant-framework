"""Read-side checks for portfolio research evidence, not trade authorization."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Protocol

from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    PortfolioProposalStatus,
    RiskAssessmentStatus,
    ValidationStatus,
)
from tong_quant.domain.models import require_timezone
from tong_quant.portfolio.models import PortfolioProposal


class PortfolioEvidenceReader(Protocol):
    def get_verified_proposal(self, proposal_id: str) -> PortfolioProposal | None: ...


@dataclass(frozen=True, slots=True)
class PortfolioEvidencePolicy:
    policy_version: str
    maximum_proposal_age: timedelta
    maximum_validation_age: timedelta
    maximum_risk_age: timedelta
    validation_configuration_hash: str
    validation_model_version: str
    portfolio_model_version: str
    risk_model_version: str

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("portfolio evidence policy requires a version")
        for name, age in (
            ("maximum_proposal_age", self.maximum_proposal_age),
            ("maximum_validation_age", self.maximum_validation_age),
            ("maximum_risk_age", self.maximum_risk_age),
        ):
            if age <= timedelta(0):
                raise ValueError(f"{name} must be positive")
        if len(self.validation_configuration_hash) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.validation_configuration_hash.lower()
        ):
            raise ValueError("portfolio evidence policy requires a SHA-256 config hash")
        if not all(
            version.strip()
            for version in (
                self.validation_model_version,
                self.portfolio_model_version,
                self.risk_model_version,
            )
        ):
            raise ValueError("portfolio evidence policy requires model versions")

    @property
    def policy_hash(self) -> str:
        payload = {
            **asdict(self),
            "maximum_proposal_age": self.maximum_proposal_age.total_seconds(),
            "maximum_validation_age": self.maximum_validation_age.total_seconds(),
            "maximum_risk_age": self.maximum_risk_age.total_seconds(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PortfolioEvidenceCheck:
    proposal_id: str
    checked_at: datetime
    policy_hash: str
    verified: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        require_timezone(self.checked_at, "checked_at")
        if self.verified == bool(self.reasons):
            raise ValueError("portfolio evidence check must explain a failed result")


@dataclass(frozen=True, slots=True)
class PortfolioEvidenceGate:
    reader: PortfolioEvidenceReader
    policy: PortfolioEvidencePolicy

    def check(self, proposal_id: str, *, as_of: datetime) -> PortfolioEvidenceCheck:
        require_timezone(as_of, "as_of")
        if not proposal_id.strip():
            raise ValueError("portfolio evidence check requires a proposal id")
        try:
            proposal = self.reader.get_verified_proposal(proposal_id)
        except (KeyError, ValueError):
            return self._result(proposal_id, as_of, ("lineage_unverified",))
        if proposal is None:
            return self._result(proposal_id, as_of, ("proposal_missing",))

        reasons: list[str] = []
        if proposal.status is not PortfolioProposalStatus.PROPOSED:
            reasons.append("proposal_not_proposed")
        if proposal.model_version != self.policy.portfolio_model_version:
            reasons.append("portfolio_version_mismatch")
        if proposal.as_of > as_of:
            reasons.append("proposal_from_future")
        elif as_of - proposal.as_of > self.policy.maximum_proposal_age:
            reasons.append("proposal_stale")

        risk = proposal.risk_assessment
        if risk is None:
            reasons.append("risk_missing")
        else:
            if risk.status is not RiskAssessmentStatus.ACCEPTABLE:
                reasons.append("risk_not_acceptable")
            if risk.model_version != self.policy.risk_model_version:
                reasons.append("risk_version_mismatch")
            if risk.assessed_at > as_of:
                reasons.append("risk_from_future")
            elif as_of - risk.assessed_at > self.policy.maximum_risk_age:
                reasons.append("risk_stale")

        for reference in proposal.evidence_references:
            if reference.investment_assessment_status is not InvestmentAssessmentStatus.COMPLETED:
                reasons.append("assessment_not_completed")
            if reference.validation_status is not ValidationStatus.RELIABLE:
                reasons.append("validation_not_reliable")
            if reference.validation_configuration_hash != (
                self.policy.validation_configuration_hash
            ):
                reasons.append("validation_config_mismatch")
            if reference.validation_model_version != self.policy.validation_model_version:
                reasons.append("validation_version_mismatch")
            if reference.validation_generated_at > as_of:
                reasons.append("validation_from_future")
            elif as_of - reference.validation_generated_at > (
                self.policy.maximum_validation_age
            ):
                reasons.append("validation_stale")

        return self._result(proposal_id, as_of, tuple(dict.fromkeys(reasons)))

    def _result(
        self,
        proposal_id: str,
        as_of: datetime,
        reasons: tuple[str, ...],
    ) -> PortfolioEvidenceCheck:
        return PortfolioEvidenceCheck(
            proposal_id=proposal_id,
            checked_at=as_of,
            policy_hash=self.policy.policy_hash,
            verified=not reasons,
            reasons=reasons,
        )


__all__ = [
    "PortfolioEvidenceCheck",
    "PortfolioEvidenceGate",
    "PortfolioEvidencePolicy",
    "PortfolioEvidenceReader",
]
