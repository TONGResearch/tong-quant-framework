"""Annotated document age diagnostics, not publication, latest-filing or source approval."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.data.reviewed_ratio_inputs import ReviewedRatioResearchInput
from tong_quant.domain.models import require_timezone
from tong_quant.version import DOCUMENT_FRESHNESS_VERSION


@dataclass(frozen=True, slots=True)
class DocumentFreshnessPolicy:
    maximum_report_age_days: int = 0
    maximum_source_age_seconds: int = 0
    model_version: str = DOCUMENT_FRESHNESS_VERSION

    def __post_init__(self) -> None:
        if (any(type(value) is not int or value < 0 for value in (
                self.maximum_report_age_days, self.maximum_source_age_seconds))
                or self.model_version != DOCUMENT_FRESHNESS_VERSION):
            raise ValueError(
                "document freshness needs nonnegative integer ages and a pinned version")

    @property
    def policy_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()


def _instant(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    require_timezone(timestamp, "document freshness timestamp")
    return timestamp.astimezone(UTC)


def review_document_freshness(
    inputs: ReviewedDocumentResearchInput | ReviewedRatioResearchInput,
    policy: DocumentFreshnessPolicy,
) -> dict[str, Any]:
    if not isinstance(inputs, (ReviewedDocumentResearchInput, ReviewedRatioResearchInput)):
        raise ValueError("document freshness requires an immutable original-review receipt")
    inputs.validate_context()
    policy.__post_init__()
    receipt = inputs.document()
    cutoff = inputs.as_of
    timezone = {"hong_kong": "Asia/Hong_Kong", "malaysia": "Asia/Kuala_Lumpur"}[
        receipt["market"]]
    output: dict[str, Any] = {
        "model_version": DOCUMENT_FRESHNESS_VERSION, "policy_hash": policy.policy_hash,
        "policy": asdict(policy), "input_hash": receipt["input_hash"], "as_of": cutoff,
        "input_model_version": receipt["model_version"],
        "subject": receipt["subject"], "market": receipt["market"],
        "document_url": receipt["document_url"], "source_status": receipt["status"],
        "requested_sector": inputs.sector_profile, "calendar_timezone": timezone,
        "decision_date": cutoff.astimezone(ZoneInfo(timezone)).date(),
        "status": "BLOCKED_INPUT", "report_freshness": "UNASSESSED",
        "source_freshness": "UNASSESSED", "annotated_report_period_end": None,
        "annotated_report_age_days": None, "source_available_at": None,
        "source_capture_age_seconds": None, "review_recorded_at": None,
        "review_recording_age_seconds": None, "trust_ceiling": "LOW",
        "availability_precision": "retrieval_time", "published_at_known": False,
        "latest_issuer_filing_verified": False, "source_qualified": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False,
        "limitations": (
            "Age limits are declared diagnostics, not admitted source or sector policy",
            "A new manual review does not refresh original source capture or report period",
            "Report end is an annotation, not publication or proof of the latest issuer filing",
            "Within configured limits does not establish accuracy, completeness or PIT readiness",
        ),
    }
    if receipt["source_bound"] is True:
        period = date.fromisoformat(receipt["review"]["report_period_end"])
        source_at = _instant(receipt["review"]["source_available_at"])
        recorded = _instant(receipt["recorded_at"])
        decision_date = cutoff.astimezone(ZoneInfo(timezone)).date()
        if not source_at <= recorded <= cutoff or period > decision_date:
            raise ValueError("document freshness rejects future or reversed chronology")
        report_age = (decision_date - period).days
        source_age = (cutoff - source_at).total_seconds()
        report_state = ("UNASSESSED" if policy.maximum_report_age_days == 0 else
            "STALE" if report_age > policy.maximum_report_age_days else "WITHIN_CONFIGURED_LIMIT")
        source_state = ("UNASSESSED" if policy.maximum_source_age_seconds == 0 else
            "STALE" if source_age > policy.maximum_source_age_seconds
            else "WITHIN_CONFIGURED_LIMIT")
        states = (report_state, source_state)
        output.update(
            status="STALE" if "STALE" in states else "UNASSESSED" if "UNASSESSED" in states
                else "WITHIN_CONFIGURED_LIMITS",
            report_freshness=report_state, source_freshness=source_state,
            annotated_report_period_end=period, annotated_report_age_days=report_age,
            source_available_at=source_at, source_capture_age_seconds=source_age,
            review_recorded_at=recorded,
            review_recording_age_seconds=(cutoff - recorded).total_seconds())
    output["assessment_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output
