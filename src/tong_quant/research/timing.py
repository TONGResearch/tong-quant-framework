"""Bind module evaluation snapshots to one logical decision instant, not input age."""

from datetime import UTC, datetime

from tong_quant.domain.models import require_timezone
from tong_quant.research.models import ResearchAssessment


def require_assessment_cutoff(
    assessments: tuple[ResearchAssessment, ...], *, as_of: datetime,
) -> None:
    require_timezone(as_of, "research decision cutoff")
    cutoff = as_of.astimezone(UTC)
    if any(item.available_at.astimezone(UTC) > cutoff or item.evaluated_at.astimezone(UTC) > cutoff
           for item in assessments):
        raise ValueError("research review rejects future assessments")
    if any(item.evaluated_at.astimezone(UTC) != cutoff for item in assessments):
        raise ValueError("research assessments must share the request decision cutoff")
    if any(item.available_at.astimezone(UTC) > cutoff or item.observed_at.astimezone(UTC) > cutoff
           for assessment in assessments for item in assessment.evidence):
        raise ValueError("research review rejects future child evidence")
