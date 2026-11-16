"""Draft source-defined bank input coverage, never a financial scoring policy."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import BANK_DOCUMENT_INPUT_VERSION

_FIELDS = frozenset({"native_label", "statement", "reporting_scope", "period_start", "period_end",
    "column_kind", "column_label", "currency", "source_unit", "source_unit_label", "pdf_page",
    "printed_page", "restatement_label"})
_KINDS = {"monetary", "ratio_contract_required", "external_evidence_required"}


@dataclass(frozen=True, slots=True)
class BankDocumentRequirement:
    requirement_id: str
    dimension: str
    kind: str
    description: str
    row_key: str = ""
    expected: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if (re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.requirement_id) is None
                or self.dimension not in {"survival", "cycle", "valuation", "growth"}
                or self.kind not in _KINDS or not 1 <= len(self.description.strip()) <= 400
                or type(self.expected) is not tuple):
            raise ValueError("unsupported bank document requirement")
        if self.kind == "monetary":
            expected = dict(self.expected)
            if (re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.row_key) is None
                    or len(self.expected) != len(expected) or set(expected) != _FIELDS
                    or any(not isinstance(value, str) or len(value) > 200
                           for value in expected.values())):
                raise ValueError("monetary requirement needs exact original row annotations")
        elif self.row_key or self.expected:
            raise ValueError("unsupported contracts must not invent a monetary row mapping")
        reject_sensitive_structure(self.document())

    def document(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, "dimension": self.dimension,
                "kind": self.kind, "description": self.description,
                "row_key": self.row_key, "expected": dict(self.expected)}


@dataclass(frozen=True, slots=True)
class BankDocumentInputPlan:
    plan_id: str
    market: Market
    subject: str
    document_url: str
    review_evidence_id: str
    review_envelope_sha256: str
    source_document_sha256: str
    available_at: datetime
    requirements: tuple[BankDocumentRequirement, ...]

    def __post_init__(self) -> None:
        validate_yahoo_equity_subject(self.market, self.subject)
        validate_document_url(self.market, self.document_url)
        require_timezone(self.available_at, "bank document plan availability")
        if (not 1 <= len(self.plan_id.strip()) <= 100
                or any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in (
                    self.review_evidence_id, self.review_envelope_sha256,
                    self.source_document_sha256))
                or type(self.requirements) is not tuple or not 1 <= len(self.requirements) <= 64
                or any(not isinstance(item, BankDocumentRequirement) for item in self.requirements)
                or len({item.requirement_id for item in self.requirements})
                != len(self.requirements)):
            raise ValueError("unsupported bank document plan")
        for item in self.requirements:
            item.__post_init__()
        reject_sensitive_structure(self.document())

    def document(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "market": self.market.value, "subject": self.subject,
            "document_url": self.document_url, "review_evidence_id": self.review_evidence_id,
            "review_envelope_sha256": self.review_envelope_sha256,
            "source_document_sha256": self.source_document_sha256,
            "available_at": self.available_at.astimezone(UTC),
            "requirements": [item.document() for item in self.requirements],
            "model_version": BANK_DOCUMENT_INPUT_VERSION, "status": "DRAFT_NOT_ADMITTED"}

    @property
    def plan_hash(self) -> str:
        return sha256(financial_input_json(self.document()).encode()).hexdigest()


def parse_bank_document_plan(document: dict[str, Any]) -> BankDocumentInputPlan:
    reject_sensitive_structure(document)
    if set(document) != {"plan", "requirements"} or not isinstance(document["plan"], dict):
        raise ValueError("bank document plan schema mismatch")
    metadata = dict(document["plan"])
    if set(metadata) != {"plan_id", "market", "subject", "document_url", "review_evidence_id",
                         "review_envelope_sha256", "source_document_sha256", "available_at"}:
        raise ValueError("bank document plan metadata mismatch")
    metadata["market"] = Market(metadata["market"])
    metadata["available_at"] = datetime.fromisoformat(metadata["available_at"])
    requirements = document["requirements"]
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 64:
        raise ValueError("bank document plan requires bounded requirements")
    items = []
    for raw in requirements:
        if not isinstance(raw, dict):
            raise ValueError("bank document requirement must be an object")
        values = dict(raw)
        expected = values.pop("expected", {})
        if (not {"requirement_id", "dimension", "kind", "description"} <= set(values)
                or set(values) - {"requirement_id", "dimension", "kind", "description", "row_key"}):
            raise ValueError("bank document requirement schema mismatch")
        if not isinstance(expected, dict):
            raise ValueError("bank expected annotations must be an object")
        items.append(BankDocumentRequirement(**values, expected=tuple(sorted(expected.items()))))
    return BankDocumentInputPlan(**metadata, requirements=tuple(items))


def bank_document_input_coverage(inputs: ReviewedDocumentResearchInput,
    plan: BankDocumentInputPlan,
) -> dict[str, Any]:
    inputs.validate_context()
    plan.__post_init__()
    if plan.available_at.astimezone(UTC) > inputs.as_of:
        raise ValueError("bank document plan was not available at the research cutoff")
    receipt = inputs.document()
    output: dict[str, Any] = {"status": "PLAN_CONTEXT_MISMATCH", "checks": [],
        "model_version": BANK_DOCUMENT_INPUT_VERSION, "plan_hash": plan.plan_hash,
        "plan_status": "DRAFT_NOT_ADMITTED", "input_hash": receipt["input_hash"],
        "as_of": inputs.as_of, "financial_scoring_authorized": False,
        "investment_scoring_authorized": False, "validation_authorized": False,
        "historical_replay_eligible": False, "execution_authorized": False,
        "issuer_and_sector_verified": False, "freshness": "UNASSESSED",
        "latest_issuer_filing_verified": False, "annotated_report_period_end": None,
        "annotated_report_age_days": None, "review_capture_age_seconds": None,
        "trust_ceiling": receipt["trust_ceiling"],
        "availability_precision": receipt["availability_precision"],
        "limitations": (
            "Exact annotation matches are not PDF, issuer, accounting or sector-policy approval",
            "Unsupported ratio/external contracts are not claims of absent issuer disclosure",
            "No weights, thresholds, ratios, valuation, Yahoo aliases or completeness score",
            "A local plan availability annotation is not authenticated historical publication",
        )}
    context = (receipt["subject"], receipt["market"], receipt["document_url"])
    if inputs.sector_profile == "bank" and context == (
        plan.subject, plan.market.value, plan.document_url
    ):
        output["status"] = "SOURCE_INPUT_UNUSABLE"
        if receipt["status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED":
            period = date.fromisoformat(receipt["review"]["report_period_end"])
            recorded = datetime.fromisoformat(receipt["recorded_at"]).astimezone(UTC)
            output.update(annotated_report_period_end=period.isoformat(),
                annotated_report_age_days=(inputs.as_of.date() - period).days,
                review_capture_age_seconds=(inputs.as_of - recorded).total_seconds())
            output["status"] = "SOURCE_PLAN_BINDING_MISMATCH"
            capture = next(row for row in receipt["captures"]
                           if row["evidence_id"] == receipt["selected_evidence_id"])
            if (receipt["selected_evidence_id"] == plan.review_evidence_id
                    and capture["raw_data_hash"] == plan.review_envelope_sha256
                    and receipt["review"]["source_document_sha256"] == plan.source_document_sha256):
                if plan.available_at.astimezone(UTC) < recorded:
                    raise ValueError("bank document plan predates its pinned manual evidence")
                output["status"] = "INPUT_COVERAGE_ONLY"
    for requirement in plan.requirements:
        check: dict[str, Any] = {**requirement.document(), "status": "BLOCKED_INPUT",
            "observation": None, "mismatched_fields": [], "missing_row_key": None}
        if output["status"] == "INPUT_COVERAGE_ONLY":
            if requirement.kind != "monetary":
                check["status"] = requirement.kind.upper()
            else:
                selected = [row for row in receipt["observations"]
                            if row["row_key"] == requirement.row_key]
                check["status"] = "MISSING_REVIEWED_ROW"
                if not selected:
                    check["missing_row_key"] = requirement.row_key
                else:
                    row = selected[0]
                    check["observation"] = row
                    mismatches = sorted(key for key, value in requirement.expected
                        if str(row[key] if row[key] is not None else "") != value)
                    check["mismatched_fields"] = mismatches
                    check["status"] = ("ANNOTATION_MISMATCH" if mismatches else
                        "UNRESOLVED_VALUE" if row["value_status"] != "transcribed" else
                        "MATCHED_UNQUALIFIED_ANNOTATIONS")
        output["checks"].append(check)
    output["assessment_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output
