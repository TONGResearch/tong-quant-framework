"""Candidate mappings cannot infer accounting comparability from matching amounts."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market
from tong_quant.research.financial.native_pairs import parse_native_pairs, review_native_pairs
from tong_quant.version import GLOBAL_DOCUMENT_REVIEW_VERSION, GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION

NOW = datetime(2026, 10, 28, tzinfo=UTC)
PAIRS = ["group_total=annualNetIncome", "group_parent=annualNetIncome",
         "bank_parent=annualNetIncome"]


def _seal(receipt):
    receipt.pop("input_hash", None)
    receipt["input_hash"] = sha256(financial_input_json(receipt).encode()).hexdigest()
    return receipt


def _receipts():
    common = {"subject": "1155.KL", "market": "malaysia", "as_of": NOW,
        "source_bound": True, "financial_scoring_authorized": False,
        "investment_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "captures": [{"evidence_id": "synthetic", "available_at": NOW}],
        "selected_evidence_id": "synthetic"}
    native_row = {"native_metric": "annualNetIncome", "period_end": "2025-12-31",
        "period_start": None, "period_type": "12M", "currency": "MYR", "value": "10514000000",
        "unit": "provider_reported_raw", "accounting_scope": "UNVERIFIED",
        "available_at": NOW, "status": "OBSERVED_UNQUALIFIED"}
    native = {**deepcopy(common), "model_version": GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION,
        "status": "partial_unqualified", "accounting_definitions_admitted": False,
        "observations": [native_row], "latest": {"annualNetIncome": native_row}}
    manual = {**deepcopy(common), "model_version": GLOBAL_DOCUMENT_REVIEW_VERSION,
        "status": "MANUAL_TRANSCRIPTION_UNQUALIFIED", "accounting_definition_qualified": False,
        "recorded_at": NOW, "observations": [
            {"row_key": name, "native_label": label, "statement": "income",
             "reporting_scope": scope, "period_start": "2025-01-01", "period_end": "2025-12-31",
             "column_kind": "current", "currency": "MYR", "source_unit": "million",
             "source_value": "10514", "unqualified_scaled_amount": "10514000000",
             "value_status": "transcribed"} for name, label, scope in (
                ("group_total", "Total profit", "group"),
                ("group_parent", "Profit attributable to equity holders", "group"),
                ("bank_parent", "Profit attributable to equity holders", "bank"))]}
    return _seal(native), _seal(manual)


def _review(receipts, candidates=PAIRS, at=NOW):
    return review_native_pairs(*receipts, candidates=candidates,
                               subject="1155.KL", market=Market.MALAYSIA, as_of=at)


def test_equal_numbers_and_competing_profit_definitions_never_select_a_winner():
    inputs = _receipts()
    before = deepcopy(inputs)
    result = _review(inputs)
    assert result == _review(inputs)
    assert result == _review(inputs, at=NOW.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert inputs == before
    assert result["status"] == "CANDIDATE_REVIEW_ONLY"
    assert len(result["pairs"]) == 3
    for pair in result["pairs"]:
        assert pair["status"] == "CONTEXT_UNQUALIFIED"
        assert pair["numeric_agreement"] is None and pair["amount_difference"] is None
        assert "MULTIPLE_CANDIDATES_FOR_NATIVE_CONTEXT" in pair["blockers"]
        assert len(pair["competing_row_keys"]) == 2
        assert "NATIVE_FLOW_START_UNKNOWN" in pair["blockers"]
        assert not pair["mapping_admitted"]
    assert "STANDALONE_SCOPE_NOT_GROUP" in result["pairs"][2]["blockers"]
    assert all(result[key] is False for key in (
        "accounting_mapping_admitted", "numeric_consistency_assessed",
        "independent_provider_consistency_assessed", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized", "research_report_created"))
    digest = result.pop("review_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()


@pytest.mark.parametrize("defect", ["currency", "period", "duplicate", "bad", "unknown_period",
    "missing_manual", "unresolved", "comparative", "latest_bad"])
def test_incompatible_and_missing_pairs_remain_visible_without_fallback(defect):
    native, manual = _receipts()
    expected = "CONTEXT_UNQUALIFIED"
    if defect == "currency":
        native["observations"][0]["currency"] = "USD"
        expected = "CURRENCY_CONFLICT"
    elif defect == "period":
        native["observations"][0]["period_end"] = "2024-12-31"
        expected = "MISSING_NATIVE_PERIOD"
    elif defect == "duplicate":
        native["observations"].append(deepcopy(native["observations"][0]))
        expected = "AMBIGUOUS_NATIVE_PERIOD"
    elif defect == "unknown_period":
        native["observations"].append({**native["observations"][0], "period_end": None})
        expected = "AMBIGUOUS_NATIVE_PERIOD"
    elif defect == "bad":
        native["observations"][0]["status"] = "INVALID_NATIVE_ROW"
        expected = "LATEST_NATIVE_UNUSABLE"
    elif defect == "latest_bad":
        native["latest"]["annualNetIncome"] = {"status": "AMBIGUOUS_PERIOD"}
        expected = "LATEST_NATIVE_UNUSABLE"
    elif defect == "missing_manual":
        manual["observations"] = []
        expected = "MISSING_MANUAL_ROW"
    elif defect == "unresolved":
        manual["observations"][0].update(value_status="conflicting", source_value=None,
                                         unqualified_scaled_amount=None)
        expected = "UNRESOLVED_MANUAL_VALUE"
    else:
        manual["observations"][0]["column_kind"] = "comparative"
    pair = _review((_seal(native), _seal(manual)))["pairs"][0]
    assert pair["status"] == expected
    assert pair["numeric_agreement"] is None
    if defect == "comparative":
        assert "COMPARATIVE_EDITION_NOT_RECONCILED" in pair["blockers"]


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("defect", ["checksum", "subject", "cutoff", "version", "authority",
    "unbound", "failed", "future", "tie", "trust", "precision"])
def test_receipt_mutation_context_chronology_and_failed_source_reject(side, defect):
    inputs = _receipts()
    receipt = inputs[side]
    if defect == "checksum":
        receipt["status"] = "tampered"
    elif defect == "subject":
        receipt["subject"] = "0005.HK"
    elif defect == "cutoff":
        receipt["as_of"] = NOW + timedelta(seconds=1)
    elif defect == "version":
        receipt["model_version"] = "unknown"
    elif defect == "authority":
        receipt["financial_scoring_authorized"] = True
    elif defect == "unbound":
        receipt["source_bound"] = False
    elif defect == "failed":
        receipt["status"] = "rejected_or_ambiguous"
    elif defect == "future":
        receipt["captures"][0]["available_at"] = NOW + timedelta(microseconds=1)
    elif defect == "tie":
        receipt["captures"].append({"evidence_id": "tie", "available_at": NOW})
    elif defect == "trust":
        receipt["trust_ceiling"] = "VERIFIED"
    else:
        receipt["availability_precision"] = "exact"
    if defect != "checksum":
        _seal(receipt)
    result = _review(inputs)
    assert result["status"] == "INPUT_REJECTED" and result["pairs"] == []


def test_row_availability_and_recording_time_cannot_exceed_selected_capture():
    for side in (0, 1):
        inputs = _receipts()
        if side == 0:
            inputs[0]["observations"][0]["available_at"] = NOW + timedelta(microseconds=1)
        else:
            inputs[1]["recorded_at"] = NOW + timedelta(microseconds=1)
        _seal(inputs[side])
        assert _review(inputs)["status"] == "INPUT_REJECTED"


@pytest.mark.parametrize("values", [[], ["x"], ["x=roe"], [" x=annualNetIncome"],
    ["x=annualNetIncome"] * 2, ["x=annualNetIncome"] * 65])
def test_candidates_are_bounded_exact_and_explicit(values):
    with pytest.raises(ValueError):
        parse_native_pairs(values)
