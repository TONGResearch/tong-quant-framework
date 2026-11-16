"""Typed evidence declarations for existing thesis conditions, never qualification.

Declarations do not read facts, verify source bytes or compare thresholds.
Optional report features retain these limits; structural completeness is not admission.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel
from tong_quant.domain.models import require_timezone
from tong_quant.research.models import (
    ResearchRequest,
    ResearchValue,
    ThesisInvalidationCondition,
)
from tong_quant.screening.models import screening_instrument_id
from tong_quant.version import THESIS_BINDING_VERSION, THESIS_REPORT_BINDING_VERSION


def _text(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError("thesis binding requires bounded explicit text")
    reject_sensitive_structure(value)


@dataclass(frozen=True, slots=True)
class ThesisPeriod:
    start: date | None
    end: date

    def __post_init__(self) -> None:
        if (type(self.end) is not date or self.start is not None
                and (type(self.start) is not date or self.start > self.end)):
            raise ValueError("thesis period requires exact ordered dates")


@dataclass(frozen=True, slots=True)
class ThesisMetricBinding:
    instrument_id: str
    metric: str
    native_tag: str
    namespace: str
    definition_version: str
    statement_scope: str
    sector_profile: str
    unit: str
    currency: str

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            _text(value)


@dataclass(frozen=True, slots=True)
class ThesisEvidenceReference:
    binding: ThesisMetricBinding
    period: ThesisPeriod
    evidence_id: str
    batch_id: str
    provider: str
    document_id: str
    document_sha256: str
    input_sha256: str
    revision: str
    published_at: datetime
    available_at: datetime
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision

    def __post_init__(self) -> None:
        if type(self.binding) is not ThesisMetricBinding or type(self.period) is not ThesisPeriod:
            raise ValueError("thesis evidence requires typed metric and period")
        self.binding.__post_init__()
        self.period.__post_init__()
        for value in (self.evidence_id, self.batch_id, self.provider, self.document_id,
                      self.revision):
            _text(value)
        for value in (self.document_sha256, self.input_sha256):
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError("thesis evidence requires explicit lowercase SHA256 references")
        for name in ("published_at", "available_at"):
            value = getattr(self, name)
            if type(value) is not datetime:
                raise ValueError("thesis evidence requires explicit timestamps")
            require_timezone(value, name)
        if self.available_at.astimezone(UTC) < self.published_at.astimezone(UTC):
            raise ValueError("thesis availability cannot precede publication")
        if (type(self.trust_level) is not DataTrustLevel
                or type(self.availability_precision) is not AvailabilityPrecision):
            raise ValueError("thesis trust and availability precision are separate typed labels")


def _canonical(value: object) -> str:
    def encode(item: object) -> str:
        if isinstance(item, datetime):
            return item.astimezone(UTC).isoformat()
        if type(item) is date:
            return item.isoformat()
        if isinstance(item, Decimal) and item.is_finite():
            return str(item)
        raise ValueError("unsupported or nonfinite thesis declaration value")
    return json.dumps(value, default=encode, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def describe_thesis_binding(
    condition: ThesisInvalidationCondition, binding: ThesisMetricBinding, *,
    periods: tuple[ThesisPeriod, ...], evidence: tuple[ThesisEvidenceReference, ...],
    decision_as_of: datetime,
) -> dict[str, Any]:
    """Retain missing/mismatched/future declarations; never evaluate a business thesis."""
    if (type(condition) is not ThesisInvalidationCondition
            or type(binding) is not ThesisMetricBinding):
        raise ValueError("thesis binding requires the existing condition and a typed metric")
    condition.__post_init__()
    binding.__post_init__()
    if condition.metric != binding.metric:
        raise ValueError("thesis condition and bound metric disagree")
    if type(decision_as_of) is not datetime:
        raise ValueError("thesis binding requires an explicit decision cutoff")
    require_timezone(decision_as_of, "decision_as_of")
    cutoff = decision_as_of.astimezone(UTC)
    if (type(periods) is not tuple or not 1 <= len(periods) <= 32
            or any(type(item) is not ThesisPeriod for item in periods)):
        raise ValueError("thesis window requires one to thirty-two explicit periods")
    for period in periods:
        period.__post_init__()
    if (len(set(periods)) != len(periods)
            or tuple(sorted(periods, key=lambda item: item.end)) != periods
            or any(period.end > cutoff.date() for period in periods)
            or any((left.start is None) != (right.start is None)
                   or (right.start is not None and right.start <= left.end)
                   or right.end <= left.end
                   for left, right in zip(periods, periods[1:], strict=False))):
        raise ValueError("thesis periods must be unique, historical and nonoverlapping in order")
    if (type(evidence) is not tuple or len(evidence) > 128
            or any(type(item) is not ThesisEvidenceReference for item in evidence)):
        raise ValueError("thesis evidence requires a bounded immutable reference tuple")
    for item in evidence:
        item.__post_init__()
    if len({item.evidence_id for item in evidence}) != len(evidence):
        raise ValueError("thesis evidence ids must be unique")
    checks = []
    covered: dict[ThesisPeriod, int] = dict.fromkeys(periods, 0)
    for item in sorted(evidence, key=lambda value: value.evidence_id):
        reasons = []
        if item.binding != binding:
            reasons.append("METRIC_DEFINITION_OR_IDENTITY_MISMATCH")
        if item.period not in periods:
            reasons.append("UNREQUESTED_PERIOD")
        if max(item.available_at.astimezone(UTC), item.published_at.astimezone(UTC)) > cutoff:
            reasons.append("FUTURE_EVIDENCE_REFERENCE")
        if not reasons:
            covered[item.period] += 1
        checks.append({"reference": asdict(item), "binding_issues": reasons})
    missing = [asdict(period) for period, count in covered.items() if count == 0]
    ambiguous = [asdict(period) for period, count in covered.items() if count > 1]
    document = {
        "version": THESIS_BINDING_VERSION, "decision_as_of": cutoff,
        "condition": asdict(condition), "metric_binding": asdict(binding),
        "declared_periods": [asdict(period) for period in periods], "references": checks,
        "missing_period_bindings": missing, "ambiguous_period_bindings": ambiguous,
        "binding_status": "INCOMPLETE_OR_CONFLICTED" if missing or ambiguous
        or any(item["binding_issues"] for item in checks) else "DECLARED_ONLY",
        "evaluation": "NOT_EVALUATED", "holding_horizon": "NOT_ESTIMATED",
        "source_verification": "NOT_PERFORMED", "source_qualification": "NOT_ADMITTED",
        "window_continuity": "NOT_VERIFIED", "freshness": "UNASSESSED",
        "financial_scoring_authorized": False, "validation_authorized": False,
        "execution_authorized": False,
        "limitations": (
            "Caller declarations and hashes are not authenticated evidence or source admission",
            "Explicit dates do not prove fiscal continuity, comparability or complete coverage",
            "All revisions remain visible; no latest-good fallback or threshold comparison",
            "No fact values, outcome labels, score, report creation or holding instruction",
        ),
    }
    reject_sensitive_structure(document)
    # Return only canonical JSON types, so the hash can be verified after a round trip.
    result = json.loads(_canonical(document))
    return {**result, "binding_hash": sha256(_canonical(result).encode()).hexdigest()}


@dataclass(frozen=True, slots=True)
class ThesisConditionBinding:
    condition: ThesisInvalidationCondition
    metric: ThesisMetricBinding
    periods: tuple[ThesisPeriod, ...]
    evidence: tuple[ThesisEvidenceReference, ...]


@dataclass(frozen=True, slots=True)
class ThesisReportBindingPlan:
    queue_id: str
    instrument_id: str
    decision_as_of: datetime
    conditions: tuple[ThesisConditionBinding, ...]

    def __post_init__(self) -> None:
        _text(self.queue_id)
        _text(self.instrument_id)
        if type(self.decision_as_of) is not datetime:
            raise ValueError("thesis report plan requires an explicit cutoff")
        require_timezone(self.decision_as_of, "decision_as_of")
        if (type(self.conditions) is not tuple or not 1 <= len(self.conditions) <= 32
                or any(type(item) is not ThesisConditionBinding for item in self.conditions)):
            raise ValueError("thesis report plan requires bounded typed condition bindings")


def thesis_report_binding_features(
    plan: ThesisReportBindingPlan, request: ResearchRequest,
) -> dict[str, ResearchValue]:
    """Bind declarations to one real request; future references cannot enter a report."""
    if type(plan) is not ThesisReportBindingPlan:
        raise ValueError("thesis report requires a typed binding plan")
    plan.__post_init__()
    request.context.validate()
    context = request.context
    cutoff = context.as_of.astimezone(UTC)
    instrument_id = screening_instrument_id(context.queue_entry.candidate.instrument)
    if (plan.queue_id != context.queue_id or plan.instrument_id != instrument_id
            or plan.decision_as_of.astimezone(UTC) != cutoff):
        raise ValueError("thesis report plan queue, instrument or cutoff mismatch")
    expected = {item.condition_id: item for item in request.invalidation_conditions}
    if len(expected) != len(request.invalidation_conditions):
        raise ValueError("thesis report rejects duplicate request condition ids")
    documents = []
    seen = set()
    reference_count = 0
    for declaration in plan.conditions:
        if (type(declaration.condition) is not ThesisInvalidationCondition
                or type(declaration.metric) is not ThesisMetricBinding):
            raise ValueError("thesis report declaration requires typed condition and metric")
        condition_id = declaration.condition.condition_id
        if condition_id in seen or condition_id not in expected:
            raise ValueError("thesis report requires unique, known condition ids")
        if _canonical(asdict(declaration.condition)) != _canonical(asdict(expected[condition_id])):
            raise ValueError("thesis report condition definition mismatch")
        if declaration.metric.instrument_id != instrument_id:
            raise ValueError("thesis report metric instrument mismatch")
        document = describe_thesis_binding(declaration.condition, declaration.metric,
            periods=declaration.periods, evidence=declaration.evidence, decision_as_of=cutoff)
        reference_count += len(declaration.evidence)
        if reference_count > 128:
            raise ValueError("thesis report plan exceeds the evidence reference bound")
        # The standalone diagnostic may retain excluded future metadata, but an
        # official decision report must never persist that metadata as research input.
        if any(max(item.available_at.astimezone(UTC), item.published_at.astimezone(UTC)) > cutoff
               or item.period.end > cutoff.date() for item in declaration.evidence):
            raise ValueError("thesis report rejects future evidence references")
        seen.add(condition_id)
        documents.append(document)
    if seen != set(expected):
        raise ValueError("thesis report plan must explicitly cover every request condition")
    body = {
        "version": THESIS_REPORT_BINDING_VERSION, "queue_id": plan.queue_id,
        "instrument_id": instrument_id, "decision_as_of": cutoff,
        "thesis": request.thesis, "counter_thesis": request.counter_thesis,
        "conditions": sorted(documents, key=lambda item: item["condition"]["condition_id"]),
        "evaluation": "NOT_EVALUATED", "source_qualification": "NOT_ADMITTED",
        "holding_horizon": "NOT_ESTIMATED", "validation_authorized": False,
        "investment_scoring_authorized": False, "execution_authorized": False,
    }
    reject_sensitive_structure(body)
    serialized = _canonical(body)
    return {
        "thesis_binding_version": THESIS_REPORT_BINDING_VERSION,
        "thesis_binding_json": serialized,
        "thesis_binding_hash": sha256(serialized.encode()).hexdigest(),
        "thesis_binding_evaluation": "NOT_EVALUATED",
        "thesis_binding_validation_authorized": False,
        "thesis_binding_investment_scoring_authorized": False,
        "thesis_binding_execution_authorized": False,
    }
