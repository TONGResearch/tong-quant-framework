"""Explicit original-row questions; not ratio equivalence, policy admission or scores."""

import re
from hashlib import sha256
from typing import Any

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.reviewed_ratio_inputs import ReviewedRatioResearchInput
from tong_quant.version import GLOBAL_RATIO_QUESTIONS_VERSION


def review_ratio_questions(inputs: ReviewedRatioResearchInput,
                          *, row_keys: tuple[str, ...]) -> dict[str, Any]:
    inputs.validate_context()
    if (type(row_keys) is not tuple or not 1 <= len(row_keys) <= 32
            or any(not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) is None
                   for key in row_keys) or len(set(row_keys)) != len(row_keys)):
        raise ValueError("ratio research questions require explicit bounded unique row keys")
    receipt = inputs.document()
    usable = receipt["source_bound"] is True
    output: dict[str, Any] = {"model_version": GLOBAL_RATIO_QUESTIONS_VERSION,
        "input_hash": receipt["input_hash"], "as_of": inputs.as_of,
        "requested_sector": inputs.sector_profile, "sector_policy": "NOT_ADMITTED",
        "status": "ORIGINAL_RATIO_QUESTIONS_ONLY" if usable else "SOURCE_INPUT_UNUSABLE",
        "questions": [], "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "accounting_definition_qualified": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "historical_replay_eligible": False, "validation_authorized": False,
        "execution_authorized": False,
        "limitations": (
            "Questions refer to exact original row keys, not approved metric aliases",
            "Presence or nonempty definition notes do not certify numerator/denominator or scope",
            "A missing review row is not proof of absent issuer disclosure",
            "No thresholds, weights, numeric targets, bank checklist credit or scores",
        )}
    for key in row_keys:
        row = next((row for row in receipt["observations"] if row["row_key"] == key), None)
        status = "BLOCKED_INPUT" if not usable else "MISSING_REVIEWED_ROW" if row is None else (
            "UNRESOLVED_VALUE" if row["value_status"] != "transcribed" else
            "DEFINITION_REVIEW_REQUIRED")
        output["questions"].append({"row_key": key, "status": status, "observation": row,
            "definition_review_required": True, "denominator_review_required": True,
            "regulatory_scope_review_required": True, "period_basis_review_required": True,
            "independent_source_review_required": True})
    output["review_hash"] = sha256(financial_input_json(output).encode()).hexdigest()
    return output
