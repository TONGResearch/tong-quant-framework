"""Source-pinned, caller-proposed percentage equations; never accounting admission."""

import re
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.data.reviewed_ratio_inputs import ReviewedRatioResearchInput
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_RATIO_ARITHMETIC_VERSION


@dataclass(frozen=True, slots=True)
class ManualRatioIdentity:
    ratio_row_key: str
    numerator_row_key: str
    denominator_row_key: str
    decimal_places: int
    rounding: str
    rationale: str

    def __post_init__(self) -> None:
        if (any(not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) is None
                for key in (self.ratio_row_key, self.numerator_row_key, self.denominator_row_key))
                or self.numerator_row_key == self.denominator_row_key
                or type(self.decimal_places) is not int or not 0 <= self.decimal_places <= 12
                or self.rounding != "half_even" or not isinstance(self.rationale, str)
                or not 1 <= len(self.rationale.strip()) <= 400
                or any(ord(char) < 32 for char in self.rationale)):
            raise ValueError("unsupported explicit ratio arithmetic identity")
        reject_sensitive_structure(asdict(self))


@dataclass(frozen=True, slots=True)
class RatioArithmeticPlan:
    money_evidence_id: str
    money_envelope_sha256: str
    ratio_evidence_id: str
    ratio_envelope_sha256: str
    source_document_sha256: str
    available_at: datetime
    identities: tuple[ManualRatioIdentity, ...]

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "ratio arithmetic plan availability")
        if (any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in (self.money_evidence_id, self.money_envelope_sha256,
                    self.ratio_evidence_id, self.ratio_envelope_sha256,
                    self.source_document_sha256))
                or type(self.identities) is not tuple or not 1 <= len(self.identities) <= 16
                or any(not isinstance(item, ManualRatioIdentity) for item in self.identities)
                or len({item.ratio_row_key for item in self.identities}) != len(self.identities)):
            raise ValueError("unsupported source-pinned ratio arithmetic plan")
        for item in self.identities:
            item.__post_init__()
        reject_sensitive_structure(self.document())

    def document(self) -> dict[str, Any]:
        return {"money_evidence_id": self.money_evidence_id,
            "money_envelope_sha256": self.money_envelope_sha256,
            "ratio_evidence_id": self.ratio_evidence_id,
            "ratio_envelope_sha256": self.ratio_envelope_sha256,
            "source_document_sha256": self.source_document_sha256,
            "available_at": self.available_at.astimezone(UTC),
            "identities": [asdict(item) for item in self.identities],
            "model_version": GLOBAL_RATIO_ARITHMETIC_VERSION, "status": "DRAFT_NOT_ADMITTED"}

    @property
    def plan_hash(self) -> str:
        return sha256(financial_input_json(self.document()).encode()).hexdigest()


def parse_ratio_arithmetic_plan(document: dict[str, Any]) -> RatioArithmeticPlan:
    reject_sensitive_structure(document)
    if set(document) != {"plan", "identities"} or not isinstance(document["plan"], dict):
        raise ValueError("ratio arithmetic plan schema mismatch")
    metadata = dict(document["plan"])
    if set(metadata) != {field.name for field in fields(RatioArithmeticPlan)} - {"identities"}:
        raise ValueError("ratio arithmetic plan metadata mismatch")
    metadata["available_at"] = datetime.fromisoformat(metadata["available_at"])
    raw = document["identities"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 16:
        raise ValueError("ratio arithmetic plan needs bounded explicit identities")
    identities = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {
            field.name for field in fields(ManualRatioIdentity)
        }:
            raise ValueError("ratio arithmetic identity schema mismatch")
        identities.append(ManualRatioIdentity(**item))
    return RatioArithmeticPlan(**metadata, identities=tuple(identities))


def _fraction(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _check(identity: ManualRatioIdentity, money: dict[str, Any], ratios: dict[str, Any],
           usable: bool) -> dict[str, Any]:
    output: dict[str, Any] = {**asdict(identity), "status": "BLOCKED_INPUT",
        "ratio_observation": None, "numerator_observation": None, "denominator_observation": None,
        "exact_percent_fraction": None, "rounded_percent": None,
        "exact_residual_percent_fraction": None, "rounded_residual_percent": None,
        "mismatched_fields": [], "missing_row_keys": []}
    if not usable:
        return output
    ratio = next((row for row in ratios["observations"]
                  if row["row_key"] == identity.ratio_row_key), None)
    numerator = next((row for row in money["observations"]
                      if row["row_key"] == identity.numerator_row_key), None)
    denominator = next((row for row in money["observations"]
                        if row["row_key"] == identity.denominator_row_key), None)
    output.update(ratio_observation=ratio, numerator_observation=numerator,
                  denominator_observation=denominator)
    output["missing_row_keys"] = [key for key, row in (
        (identity.ratio_row_key, ratio), (identity.numerator_row_key, numerator),
        (identity.denominator_row_key, denominator)) if row is None]
    if ratio is None or numerator is None or denominator is None:
        output["status"] = "MISSING_REVIEWED_ROW"
    elif (ratio["period_basis"] != "instant" or numerator["statement"] != "balance"
          or denominator["statement"] != "balance"):
        output["status"] = "UNSUPPORTED_PERIOD_BASIS"
    else:
        mismatches = [key for key in ("reporting_scope", "period_end", "column_kind",
                                      "restatement_label")
                      if not ratio[key] == numerator[key] == denominator[key]]
        mismatches.extend(key for key in ("currency", "source_unit", "source_unit_label")
                          if numerator[key] != denominator[key])
        output["mismatched_fields"] = sorted(mismatches)
        if mismatches:
            output["status"] = "ROW_CONTEXT_MISMATCH"
        elif any(row["value_status"] != "transcribed" for row in (ratio, numerator, denominator)):
            output["status"] = "UNRESOLVED_VALUE"
        else:
            displayed = Decimal(ratio["source_value"])
            bottom = Fraction(denominator["source_value"])
            if displayed.as_tuple().exponent != -identity.decimal_places:
                output["status"] = "DISPLAY_PRECISION_MISMATCH"
            elif bottom <= 0:
                output["status"] = "NONPOSITIVE_DENOMINATOR"
            else:
                exact = Fraction(numerator["source_value"]) / bottom * 100
                # Fraction.__round__ uses exact ties-to-even; avoid decimal double rounding.
                rounded = round(exact, identity.decimal_places)
                with localcontext() as context:
                    context.prec = 128
                    result = Decimal(rounded.numerator) / Decimal(rounded.denominator)
                    residual = result - displayed
                    output.update(rounded_percent=format(result, f".{identity.decimal_places}f"),
                        rounded_residual_percent=format(residual, f".{identity.decimal_places}f"))
                output.update(exact_percent_fraction=_fraction(exact),
                    exact_residual_percent_fraction=_fraction(exact - Fraction(displayed)),
                    status="ARITHMETIC_AGREES_AS_TRANSCRIBED" if result == displayed else
                    "ARITHMETIC_RESIDUAL_AS_TRANSCRIBED")
    return output


def review_ratio_arithmetic(money_inputs: ReviewedDocumentResearchInput,
    ratio_inputs: ReviewedRatioResearchInput, plan: RatioArithmeticPlan,
) -> dict[str, Any]:
    money_inputs.validate_context()
    ratio_inputs.validate_context()
    plan.__post_init__()
    money, ratios = money_inputs.document(), ratio_inputs.document()
    if (money_inputs.as_of != ratio_inputs.as_of
            or money_inputs.sector_profile != ratio_inputs.sector_profile
            or any(money[key] != ratios[key] for key in ("market", "subject", "document_url"))):
        raise ValueError("ratio arithmetic input context mismatch")
    if plan.available_at.astimezone(UTC) > money_inputs.as_of:
        raise ValueError("ratio arithmetic plan was not available at cutoff")
    output: dict[str, Any] = {"status": "SOURCE_INPUT_UNUSABLE",
        "model_version": GLOBAL_RATIO_ARITHMETIC_VERSION, "plan_hash": plan.plan_hash,
        "plan_status": "DRAFT_NOT_ADMITTED", "money_input_hash": money["input_hash"],
        "ratio_input_hash": ratios["input_hash"], "as_of": money_inputs.as_of,
        "requested_sector": money_inputs.sector_profile, "sector_policy": "NOT_ADMITTED",
        "checks": [], "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "accounting_definition_qualified": False,
        "formula_mapping_verified": False, "issuer_rounding_verified": False,
        "regulatory_scope_verified": False, "independent_review": False,
        "canonical_population_authorized": False, "financial_scoring_authorized": False,
        "investment_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "limitations": (
            "Equations and half-even rounding are proposals, not approved issuer definitions",
            "Same PDF and Group/date labels do not prove matching regulatory consolidation",
            "Arithmetic agreement cannot qualify source truth, policy or investment decisions",
            "Only instant percentages over same-unit/currency balance amounts are supported",
            "No ROE averaging, tolerance, FX, aliases, favorable alternatives or bank-plan credit",
            "Copies do not requery sources; reread both at one snapshot/cutoff for a new run",
        )}
    if money["source_bound"] is True and ratios["source_bound"] is True:
        output["status"] = "SOURCE_PARENT_MISMATCH"
        source_fields = ("source_evidence_id", "source_envelope_sha256", "source_document_sha256",
                         "report_period_end")
        same_available_instant = datetime.fromisoformat(
            money["review"]["source_available_at"]).astimezone(UTC) == datetime.fromisoformat(
            ratios["review"]["source_available_at"]).astimezone(UTC)
        if same_available_instant and all(money["review"][key] == ratios["review"][key]
                                         for key in source_fields):
            output["status"] = "SOURCE_PLAN_BINDING_MISMATCH"
            money_capture = next(row for row in money["captures"]
                                 if row["evidence_id"] == money["selected_evidence_id"])
            ratio_capture = next(row for row in ratios["captures"]
                                 if row["evidence_id"] == ratios["selected_evidence_id"])
            if (money["selected_evidence_id"] == plan.money_evidence_id
                    and ratios["selected_evidence_id"] == plan.ratio_evidence_id
                    and money_capture["raw_data_hash"] == plan.money_envelope_sha256
                    and ratio_capture["raw_data_hash"] == plan.ratio_envelope_sha256
                    and money["review"]["source_document_sha256"] == plan.source_document_sha256):
                recorded = max(datetime.fromisoformat(receipt["recorded_at"]).astimezone(UTC)
                               for receipt in (money, ratios))
                if plan.available_at.astimezone(UTC) < recorded:
                    raise ValueError("ratio arithmetic plan predates pinned evidence")
                output["status"] = "TRANSCRIPTION_ARITHMETIC_ONLY"
    output["checks"] = [_check(identity, money, ratios,
        output["status"] == "TRANSCRIPTION_ARITHMETIC_ONLY") for identity in plan.identities]
    output["review_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output
