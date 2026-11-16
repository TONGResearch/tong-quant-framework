"""Single transcription evidence cannot silently become accounting/PIT authority."""

import json
import subprocess
import sys
import tomllib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.global_document_review_inputs import (
    ingest_global_document_review,
    prepare_global_document_review,
    read_global_document_review_inputs,
)
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import global_document_reviews as reviews
from tong_quant.data.providers import global_documents as source
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.reviewed_document_inputs import (
    ReviewedDocumentResearchInput,
    read_reviewed_document_research_input,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.financial.document_bank import (
    BankDocumentInputPlan,
    BankDocumentRequirement,
    bank_document_input_coverage,
    parse_bank_document_plan,
)
from tong_quant.research.financial.native_pairs import (
    parse_income_changes,
    parse_income_sums,
    review_income_changes,
    review_income_sums,
)

NOW = datetime(2026, 10, 28, tzinfo=UTC)
REVIEWED, RECORDED = NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)
URL = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf"


def _row(**changes):
    values = {"row_key": "native_amount", "native_label": "Synthetic source label",
        "statement": "income", "reporting_scope": "group", "period_start": date(2025, 1, 1),
        "period_end": date(2025, 12, 31), "column_kind": "current", "column_label": "Group 2025",
        "currency": "CNY", "source_unit": "million", "source_unit_label": "RMB million",
        "source_value": Decimal("123.45"), "value_status": "transcribed",
        "raw_cell_text": "123.45", "pdf_page": 130, "printed_page": "129",
        "restatement_label": "unknown"}
    return reviews.GlobalMonetaryRow(**{**values, **changes})


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "review.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    _capture_source(store, artifacts)
    return store, artifacts


def _capture_source(store, artifacts, at=NOW, error="", period_end="2025-12-31"):
    request = ProviderDatasetRequest(source.DATASET, Market.HONG_KONG, "0700.HK", at,
        {"document_url": URL, "landing_url": URL, "issuer_label": "Synthetic",
         "period_end": period_end, "document_kind": "annual_report"})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        source.GlobalDocumentAdapter(Market.HONG_KONG, clock=lambda: at,
            download=lambda _: source.DocumentCapture(
                None if error else b"%PDF-1.7\nSynthetic", error)),
        request)


def _review(foundation, rows=None, **changes):
    receipt = read_global_document_inputs(*foundation, Market.HONG_KONG, "0700.HK", URL, as_of=NOW)
    return reviews.GlobalDocumentReview(**{"market": Market.HONG_KONG, "subject": "0700.HK",
        "document_url": URL, "source_evidence_id": receipt["selected_evidence_id"],
        "source_envelope_sha256": receipt["captures"][0]["raw_data_hash"],
        "source_document_sha256": receipt["document_sha256"], "source_available_at": NOW,
        "reviewed_at": REVIEWED, "reviewer": "Synthetic single reviewer",
        "report_period_end": date(2025, 12, 31), "rows": rows or (_row(),), **changes})


def _read(foundation, at=RECORDED):
    return read_global_document_review_inputs(*foundation, Market.HONG_KONG, "0700.HK", URL,
                                              as_of=at)


def _arithmetic_receipt(foundation, *, component_changes=None):
    rows = (_row(row_key="result", native_label="Synthetic total", source_value=Decimal("10")),
        _row(row_key="income", native_label="Synthetic income", source_value=Decimal("30")),
        _row(**{"row_key": "expense", "native_label": "Synthetic expense",
                "source_value": Decimal("-20"), **(component_changes or {})}))
    ingest_global_document_review(*foundation, _review(foundation, rows), clock=lambda: RECORDED)
    return _read(foundation)


def _arithmetic(receipt, identities=("result=income+expense",), as_of=RECORDED):
    return review_income_sums(receipt, identities=identities, subject="0700.HK",
                              market=Market.HONG_KONG, as_of=as_of)


def _income_pair_input(foundation, changes=None, *, fiscal=False):
    end = date(2025, 6, 30) if fiscal else date(2025, 12, 31)
    start = date(2024, 7, 1) if fiscal else date(2025, 1, 1)
    current = _row(row_key="current", source_value=Decimal("110"),
                   period_start=start, period_end=end)
    prior = replace(current, **{"row_key": "prior", "source_value": Decimal("100"),
        "period_start": date(start.year - 1, start.month, start.day),
        "period_end": date(end.year - 1, end.month, end.day),
        "column_kind": "comparative", "column_label": "Group prior column", **(changes or {})})
    review = _review(foundation, rows=(current, prior), report_period_end=end)
    ingest_global_document_review(*foundation, review, clock=lambda: RECORDED)
    return read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                                  as_of=RECORDED, sector_profile="bank")


def test_same_filing_income_change_is_descriptive_not_original_history(foundation):
    inputs = _income_pair_input(foundation)
    result = review_income_changes(inputs, pairs=("current=prior",))
    assert result == review_income_changes(inputs, pairs=("current=prior",))
    comparison = result["comparisons"][0]
    assert comparison["status"] == "DESCRIPTIVE_UNQUALIFIED"
    assert comparison["amount_change_source_units"] == "10"
    assert comparison["change_percent"] == "10.0000"
    assert comparison["source_unit"] == "million"
    assert all(result[key] is False for key in ("accounting_comparability_verified",
        "original_historical_vintages_verified", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized"))
    digest = result.pop("review_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()
    assert review_income_changes(inputs, pairs=("prior=current",))["comparisons"][0][
        "status"] == "COLUMN_KIND_MISMATCH"


@pytest.mark.parametrize("value", [Decimal(0), Decimal(-100)])
def test_income_changes_withhold_percent_for_nonpositive_prior(foundation, value):
    inputs = _income_pair_input(foundation, {"source_value": value})
    comparison = review_income_changes(inputs, pairs=("current=prior",))["comparisons"][0]
    assert comparison["status"] == "NONPOSITIVE_BASE"
    assert comparison["change_percent"] is None
    assert Decimal(comparison["amount_change_source_units"]) == Decimal(110) - value


@pytest.mark.parametrize("changes,status", [
    ({"reporting_scope": "bank"}, "CONTEXT_MISMATCH"),
    ({"currency": "USD"}, "CONTEXT_MISMATCH"),
    ({"source_unit": "thousand"}, "CONTEXT_MISMATCH"),
    ({"native_label": "Total rather than attributable profit"}, "CONTEXT_MISMATCH"),
    ({"restatement_label": "marked_restated"}, "CONTEXT_MISMATCH"),
    ({"statement": "cash_flow"}, "CONTEXT_MISMATCH"),
    ({"period_start": date(2024, 4, 1)}, "UNSUPPORTED_ANNUAL_WINDOWS"),
    ({"period_end": date(2024, 9, 30)}, "UNSUPPORTED_ANNUAL_WINDOWS"),
    ({"source_value": None, "value_status": "conflicting"}, "UNRESOLVED_VALUE"),
])
def test_income_change_rejects_incompatible_semantics_without_favorable_fallback(
    foundation, changes, status,
):
    inputs = _income_pair_input(foundation, changes)
    comparison = review_income_changes(inputs, pairs=("current=prior",))["comparisons"][0]
    assert comparison["status"] == status
    assert comparison["amount_change_source_units"] is None and comparison["change_percent"] is None


def test_income_changes_preserve_missing_and_latest_source_failure(foundation):
    inputs = _income_pair_input(foundation)
    assert review_income_changes(inputs, pairs=("current=absent",))["comparisons"][0][
        "status"] == "MISSING_ROW"
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403")
    failed = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                                   as_of=later, sector_profile="bank")
    result = review_income_changes(failed, pairs=("current=prior",))
    assert result["status"] == "SOURCE_INPUT_UNUSABLE"
    assert result["comparisons"][0]["change_percent"] is None


def test_income_changes_support_explicit_noncalendar_annual_windows(tmp_path):
    store = SQLiteStore(tmp_path / "fiscal.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    _capture_source(store, artifacts, period_end="2025-06-30")
    inputs = _income_pair_input((store, artifacts), fiscal=True)
    assert review_income_changes(inputs, pairs=("current=prior",))["comparisons"][0][
        "status"] == "DESCRIPTIVE_UNQUALIFIED"


@pytest.mark.parametrize("values", [[], ["a"], ["a=a"], ["a=b", "a=c"], ["a=b"] * 17,
    [" a=b"], ["a=b=c"]])
def test_income_changes_require_bounded_explicit_pairs(values):
    with pytest.raises(ValueError):
        parse_income_changes(values)


def _bank_plan(receipt):
    row = receipt["observations"][2]
    fields = ("native_label", "statement", "reporting_scope", "period_start", "period_end",
        "column_kind", "column_label", "currency", "source_unit", "source_unit_label",
        "pdf_page", "printed_page", "restatement_label")
    requirement = BankDocumentRequirement("source_expense", "cycle", "monetary", "Synthetic only",
        row["row_key"], tuple(sorted((name, str(row[name])) for name in fields)))
    requirements = (requirement,
        replace(requirement, requirement_id="missing_amount", dimension="growth", row_key="absent"),
        BankDocumentRequirement("capital", "survival", "ratio_contract_required", "Ratio"),
        BankDocumentRequirement("dated_price", "valuation", "external_evidence_required", "Dated"),
    )
    return BankDocumentInputPlan("synthetic", Market.HONG_KONG, "0700.HK", URL,
        receipt["selected_evidence_id"], receipt["captures"][-1]["raw_data_hash"],
        receipt["review"]["source_document_sha256"], RECORDED, requirements)


def test_bank_document_coverage_preserves_observed_missing_and_unsupported_contracts(foundation):
    receipt = _arithmetic_receipt(foundation)
    bound = ReviewedDocumentResearchInput(financial_input_json(receipt), "bank")
    plan = _bank_plan(receipt)
    before = foundation[0].path.read_bytes()
    result = bank_document_input_coverage(bound, plan)
    assert result == bank_document_input_coverage(bound, plan)
    assert result["status"] == "INPUT_COVERAGE_ONLY"
    assert [row["status"] for row in result["checks"]] == ["MATCHED_UNQUALIFIED_ANNOTATIONS",
        "MISSING_REVIEWED_ROW", "RATIO_CONTRACT_REQUIRED", "EXTERNAL_EVIDENCE_REQUIRED"]
    assert result["checks"][0]["observation"]["source_value"] == "-20"
    assert result["checks"][1]["missing_row_key"] == "absent"
    assert all(result[name] is False for name in ("financial_scoring_authorized",
        "investment_scoring_authorized", "validation_authorized", "historical_replay_eligible",
        "execution_authorized", "issuer_and_sector_verified"))
    assert result["trust_ceiling"] == "LOW" and result["freshness"] == "UNASSESSED"
    digest = result.pop("assessment_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("field", ["native_label", "reporting_scope", "currency", "source_unit",
    "source_unit_label", "period_start", "period_end", "column_kind", "column_label",
    "pdf_page", "printed_page", "restatement_label", "statement"])
def test_bank_document_exact_annotation_mismatch_withholds_match(foundation, field):
    receipt = _arithmetic_receipt(foundation)
    bound = ReviewedDocumentResearchInput(financial_input_json(receipt), "bank")
    plan = _bank_plan(receipt)
    expected = dict(plan.requirements[0].expected)
    expected[field] = "Different annotation"
    changed = replace(plan.requirements[0], expected=tuple(sorted(expected.items())))
    plan = replace(plan, requirements=(changed,))
    result = bank_document_input_coverage(bound, plan)
    assert result["checks"][0]["status"] == "ANNOTATION_MISMATCH"
    assert result["checks"][0]["mismatched_fields"] == [field]


@pytest.mark.parametrize("field", ["review_evidence_id", "review_envelope_sha256",
                                  "source_document_sha256"])
def test_bank_plan_never_rebinds_different_source_or_manual_edition(foundation, field):
    receipt = _arithmetic_receipt(foundation)
    bound = ReviewedDocumentResearchInput(financial_input_json(receipt), "bank")
    plan = replace(_bank_plan(receipt), **{field: "f" * 64})
    result = bank_document_input_coverage(bound, plan)
    assert result["status"] == "SOURCE_PLAN_BINDING_MISMATCH"
    assert all(row["status"] == "BLOCKED_INPUT" and row["observation"] is None
               for row in result["checks"])


@pytest.mark.parametrize("time", [NOW, RECORDED + timedelta(microseconds=1)])
def test_bank_plan_cannot_precede_pinned_evidence_or_follow_cutoff(foundation, time):
    receipt = _arithmetic_receipt(foundation)
    plan = replace(_bank_plan(receipt), available_at=time)
    with pytest.raises(ValueError):
        bank_document_input_coverage(
            ReviewedDocumentResearchInput(financial_input_json(receipt), "bank"), plan)


def test_bank_plan_is_draft_versioned_and_equivalent_utc_instants_hash_equally(foundation):
    plan = _bank_plan(_arithmetic_receipt(foundation))
    equivalent = replace(plan, available_at=RECORDED.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert plan.plan_hash == equivalent.plan_hash
    assert plan.plan_hash != replace(plan, plan_id="new-draft").plan_hash
    document = plan.document()
    metadata = {key: value for key, value in document.items()
                if key not in {"requirements", "model_version", "status"}}
    metadata["available_at"] = RECORDED.isoformat()
    raw = {"plan": metadata, "requirements": document["requirements"]}
    assert parse_bank_document_plan(raw) == plan
    raw["requirements"][0]["weight"] = 1
    with pytest.raises(ValueError):
        parse_bank_document_plan(raw)


def test_bank_plan_cannot_add_amount_expectations_or_fill_unresolved_values(foundation):
    receipt = _arithmetic_receipt(foundation, component_changes={
        "source_value": None, "value_status": "conflicting"})
    plan = _bank_plan(receipt)
    with pytest.raises(ValueError):
        replace(plan.requirements[0], expected=(*plan.requirements[0].expected,
                                               ("source_value", "999")))
    bound = ReviewedDocumentResearchInput(financial_input_json(receipt), "bank")
    result = bank_document_input_coverage(bound, plan)
    assert result["checks"][0]["status"] == "UNRESOLVED_VALUE"
    assert result["checks"][0]["observation"]["unqualified_scaled_amount"] is None


def test_bank_plan_rejects_other_sector_and_preserves_latest_parent_failure(foundation):
    receipt = _arithmetic_receipt(foundation)
    plan = _bank_plan(receipt)
    other = ReviewedDocumentResearchInput(financial_input_json(receipt), "nonfinancial")
    assert bank_document_input_coverage(other, plan)["status"] == "PLAN_CONTEXT_MISMATCH"
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403")
    failed = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                                  as_of=later, sector_profile="bank")
    result = bank_document_input_coverage(failed, plan)
    assert result["status"] == "SOURCE_INPUT_UNUSABLE"
    assert all(row["status"] == "BLOCKED_INPUT" for row in result["checks"])


def test_new_manual_edition_preserves_old_cutoff_and_requires_new_plan_pins(foundation):
    old = _arithmetic_receipt(foundation)
    plan = _bank_plan(old)
    raw = old["review"]
    metadata = {key: value for key, value in raw.items() if key != "rows"}
    review = reviews.parse_global_document_review({"review": metadata, "rows": raw["rows"]})
    prior = replace(review.rows[0], row_key="prior", period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31), column_kind="comparative", column_label="Prior column")
    later = RECORDED + timedelta(seconds=2)
    ingest_global_document_review(*foundation, replace(review, reviewed_at=later,
        rows=(*review.rows, prior)), clock=lambda: later)
    assert _read(foundation, RECORDED) == old
    bound = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                                  as_of=later, sector_profile="bank")
    assert bank_document_input_coverage(bound, plan)["status"] == "SOURCE_PLAN_BINDING_MISMATCH"
    receipt = bound.document()
    new_plan = replace(plan, review_evidence_id=receipt["selected_evidence_id"],
        review_envelope_sha256=receipt["captures"][-1]["raw_data_hash"], available_at=later)
    assert bank_document_input_coverage(bound, new_plan)["status"] == "INPUT_COVERAGE_ONLY"
    assert new_plan.plan_hash != plan.plan_hash


@pytest.mark.parametrize("profile", ["bank", "nonfinancial", "securities", "insurance", "unknown"])
def test_reviewed_research_input_copies_receipt_and_revalidates_exact_context(foundation, profile):
    _arithmetic_receipt(foundation)
    before = foundation[0].path.read_bytes()
    bound = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                                 as_of=RECORDED, sector_profile=profile)
    bound.validate_context(symbol="0700.HK", market=Market.HONG_KONG,
        as_of=RECORDED.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    doc = bound.document()
    assert doc == json.loads(financial_input_json(_read(foundation)))
    doc["observations"][0]["source_value"] = "999"
    assert bound.document() != doc
    with pytest.raises(ValueError):
        bound.validate_context(symbol="0005.HK")
    with pytest.raises(ValueError):
        bound.validate_context(market=Market.MALAYSIA)
    with pytest.raises(ValueError):
        bound.validate_context(as_of=RECORDED + timedelta(microseconds=1))
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("defect", ["checksum", "authority", "trust", "precision", "future",
    "naive", "recording", "observation", "model", "sector", "capture_tie", "source_subject"])
def test_reviewed_research_receipt_rejects_mutation_and_authority(foundation, defect):
    doc = _arithmetic_receipt(foundation)
    profile = "bank"
    if defect == "checksum":
        doc["status"] = "tampered"
    elif defect == "authority":
        doc["financial_scoring_authorized"] = True
    elif defect == "trust":
        doc["trust_ceiling"] = "HIGH"
    elif defect == "precision":
        doc["availability_precision"] = "exact"
    elif defect == "future":
        doc["captures"][0]["available_at"] = RECORDED + timedelta(microseconds=1)
    elif defect == "naive":
        doc["as_of"] = RECORDED.replace(tzinfo=None)
    elif defect == "recording":
        doc["recorded_at"] = (RECORDED - timedelta(microseconds=1)).isoformat()
    elif defect == "observation":
        doc["observations"][0]["source_value"] = "999"
    elif defect == "model":
        doc["model_version"] = "unknown"
    elif defect == "sector":
        profile = "admitted_bank"
    elif defect == "capture_tie":
        doc["captures"].append({"available_at": RECORDED, "evidence_id": "tied"})
    else:
        doc["review"]["subject"] = "0005.HK"
    if defect != "checksum":
        doc.pop("input_hash")
        doc["input_hash"] = sha256(financial_input_json(doc).encode()).hexdigest()
    with pytest.raises(ValueError):
        ReviewedDocumentResearchInput(financial_input_json(doc), profile)


def test_reviewed_research_input_preserves_missing_then_changed_parent_failure(foundation):
    missing = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
        as_of=NOW, sector_profile="bank")
    assert missing.document()["status"] == "missing"
    _arithmetic_receipt(foundation)
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403")
    failed = read_reviewed_document_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
        as_of=later, sector_profile="bank")
    assert failed.document()["status"] == "rejected_or_ambiguous"
    assert failed.document()["observations"] == []
    assert not failed.document()["source_bound"]


def test_manual_income_signed_arithmetic_does_not_admit_source_or_score(foundation):
    receipt = _arithmetic_receipt(foundation)
    before = foundation[0].path.read_bytes()
    first = _arithmetic(receipt)
    assert first == _arithmetic(receipt, as_of=RECORDED.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert first["status"] == "TRANSCRIPTION_ARITHMETIC_ONLY"
    check = first["checks"][0]
    assert check["status"] == "ARITHMETIC_AGREES_AS_TRANSCRIBED"
    assert check["residual_source_units"] == "0" and check["signed_component_sum"] == "10"
    assert check["source_unit"] == "million" and check["currency"] == "CNY"
    assert all(first[key] is False for key in (
        "accounting_definition_qualified", "source_location_verified", "independent_review",
        "financial_scoring_authorized", "investment_scoring_authorized",
        "historical_replay_eligible", "validation_authorized", "execution_authorized"))
    digest = first.pop("review_hash")
    assert digest == sha256(financial_input_json(first).encode()).hexdigest()
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("changes", [
    {"reporting_scope": "bank"}, {"currency": "USD"}, {"source_unit": "thousand"},
    {"column_label": "A different column"}, {"period_start": date(2025, 2, 1)},
    {"statement": "cash_flow"}, {"restatement_label": "not_marked"},
])
def test_manual_income_sums_reject_scope_currency_units_period_and_column(foundation, changes):
    check = _arithmetic(_arithmetic_receipt(foundation, component_changes=changes))["checks"][0]
    assert check["status"] == "CONTEXT_MISMATCH" and check["residual_source_units"] is None


@pytest.mark.parametrize("value", [Decimal("20"), Decimal("-19.99999999999999999999")])
def test_manual_income_sum_never_infers_expense_sign_or_rounds_residual(foundation, value):
    receipt = _arithmetic_receipt(foundation, component_changes={"source_value": value})
    check = _arithmetic(receipt)["checks"][0]
    assert check["status"] == "ARITHMETIC_RESIDUAL_AS_TRANSCRIBED"
    assert Decimal(check["residual_source_units"]) != 0


def test_manual_income_sum_preserves_missing_and_unresolved_values(foundation):
    receipt = _arithmetic_receipt(foundation, component_changes={
        "source_value": None, "value_status": "conflicting"})
    result = _arithmetic(receipt, identities=("result=income+expense", "absent=income+expense"))
    assert [check["status"] for check in result["checks"]] == ["UNRESOLVED_VALUE", "MISSING_ROW"]
    assert all(check["residual_source_units"] is None for check in result["checks"])


@pytest.mark.parametrize("defect", ["checksum", "observations", "cutoff", "recorded", "latest",
    "authority", "unknown_model"])
def test_manual_income_arithmetic_rejects_bad_receipts(foundation, defect):
    receipt = _arithmetic_receipt(foundation)
    if defect == "checksum":
        receipt["status"] = "changed"
    elif defect == "observations":
        receipt["observations"][0]["source_value"] = "999"
    elif defect == "cutoff":
        receipt["as_of"] = RECORDED + timedelta(microseconds=1)
    elif defect == "recorded":
        receipt["recorded_at"] = RECORDED + timedelta(microseconds=1)
    elif defect == "latest":
        receipt["source_bound"] = False
        receipt["status"] = "rejected_or_ambiguous"
    elif defect == "authority":
        receipt["validation_authorized"] = True
    else:
        receipt["model_version"] = "unknown"
    if defect != "checksum":
        receipt.pop("input_hash")
        receipt["input_hash"] = sha256(financial_input_json(receipt).encode()).hexdigest()
    result = _arithmetic(receipt)
    assert result["status"] == "INPUT_REJECTED" and not result["checks"]


@pytest.mark.parametrize("values", [[], ["x"], ["r=a"], ["r=a+a"], ["r=r+a"],
    ["r=a+b", "r=c+d"], ["r=a+b"] * 17, ["r=a-b"], ["r= a+b"], ["r=a+b=c"]])
def test_manual_income_sums_require_bounded_explicit_nonduplicating_keys(values):
    with pytest.raises(ValueError):
        parse_income_sums(values)


def test_preview_does_not_write_and_actual_recording_cannot_be_backdated(foundation):
    review = _review(foundation)
    before = foundation[0].path.read_bytes()
    batch = prepare_global_document_review(*foundation, review, as_of=REVIEWED)
    observation = batch.records[0].payload["observations"][0]
    assert observation["unqualified_scaled_amount"] == "123450000.00"
    assert before == foundation[0].path.read_bytes()
    ingest_global_document_review(*foundation, review, clock=lambda: RECORDED)
    assert _read(foundation, REVIEWED)["status"] == "missing"
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED"
    assert result["recorded_at"] == RECORDED.isoformat()
    assert all(result[key] is False for key in (
        "financial_scoring_authorized", "independent_review",
        "canonical_population_authorized", "validation_authorized", "historical_replay_eligible",
        "issuer_to_instrument_verified", "execution_authorized", "source_location_verified"))
    assert result["observations"][0]["canonical_metric"] is None
    after = foundation[0].path.read_bytes()
    assert result["input_hash"] == _read(foundation)["input_hash"]
    assert result["input_hash"] == _read(foundation, RECORDED.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur")))["input_hash"]
    assert after == foundation[0].path.read_bytes()


@pytest.mark.parametrize("values", [{"pdf_page": 0}, {"pdf_page": True}, {"pdf_page": 1001},
    {"source_value": Decimal("NaN")}, {"source_value": Decimal("1e25")},
    {"source_value": 123.45}, {"currency": "RMB"}, {"source_unit": "percent"},
    {"source_unit": "unknown"}, {"reporting_scope": "consolidated_guess"},
    {"statement": "ratio"}, {"period_start": None}, {"printed_page": ""},
    {"period_start": date(2026, 1, 1)}, {"source_unit_label": ""},
    {"raw_cell_text": ""}, {"native_label": "password=synthetic-not-real"},
    {"value_status": "missing"}, {"source_value": None}])
def test_bad_semantics_or_secret_content_are_rejected(values):
    with pytest.raises(ValueError):
        _row(**values)


@pytest.mark.parametrize("status", ["missing", "unreadable", "conflicting"])
def test_unusable_cells_remain_visible_without_zero_or_scaled_values(foundation, status):
    row = _row(value_status=status, source_value=None, raw_cell_text="Not resolved")
    review = _review(foundation, rows=(row,))
    ingest_global_document_review(*foundation, review, clock=lambda: RECORDED)
    result = _read(foundation)["observations"][0]
    assert result["source_value"] is None and result["unqualified_scaled_amount"] is None
    assert result["value_status"] == status


def test_group_bank_parent_profit_and_comparative_columns_cannot_collapse(foundation):
    current = _row()
    bank = replace(current, row_key="bank", reporting_scope="bank", source_value=Decimal(100))
    prior = replace(current, row_key="comparative", column_kind="comparative",
        period_start=date(2024, 1, 1), period_end=date(2024, 12, 31))
    review = _review(foundation, rows=(current, bank, prior))
    batch = prepare_global_document_review(*foundation, review, as_of=RECORDED)
    rows = batch.records[0].payload["observations"]
    assert len(rows) == 3
    assert rows[0]["reporting_scope"] != rows[1]["reporting_scope"]
    with pytest.raises(ValueError):
        _review(foundation, rows=(current, replace(current, row_key="duplicate")))
    with pytest.raises(ValueError):
        _review(foundation, rows=(replace(current, column_kind="comparative"),))


def test_balance_period_is_not_flow_and_negative_values_are_not_hard_failures(foundation):
    row = _row(statement="balance", period_start=None, source_value=Decimal("-1"),
               raw_cell_text="(1)")
    review = _review(foundation, rows=(row,))
    assert prepare_global_document_review(*foundation, review, as_of=RECORDED).records
    with pytest.raises(ValueError):
        replace(row, period_start=date(2025, 1, 1))


@pytest.mark.parametrize("values", [{"source_evidence_id": "0" * 64},
    {"source_envelope_sha256": "1" * 64}, {"source_document_sha256": "2" * 64},
    {"source_available_at": NOW - timedelta(seconds=1)}])
def test_wrong_parent_pins_never_become_usable(foundation, values):
    with pytest.raises(ValueError):
        prepare_global_document_review(*foundation, _review(foundation, **values), as_of=RECORDED)


@pytest.mark.parametrize("values", [{"source_available_at": RECORDED},
    {"reviewed_at": NOW.replace(tzinfo=None)}, {"report_period_end": date(2027, 1, 1)},
    {"source_document_sha256": "invalid"}, {"reviewer": ""}])
def test_invalid_or_future_review_metadata_is_rejected(foundation, values):
    with pytest.raises(ValueError):
        _review(foundation, **values)


@pytest.mark.parametrize("failure", [False, True])
def test_new_source_capture_or_failure_requires_explicit_new_review(foundation, failure):
    ingest_global_document_review(*foundation, _review(foundation), clock=lambda: RECORDED)
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403" if failure else "")
    assert not _read(foundation, later)["source_bound"]
    assert _read(foundation)["source_bound"]


@pytest.mark.parametrize("defect", ["tamper", "tie", "future_completion", "forged_source"])
def test_latest_bad_review_does_not_fall_back_to_older(foundation, defect):
    review = _review(foundation)
    ingest_global_document_review(*foundation, review, clock=lambda: RECORDED)
    later = RECORDED + timedelta(seconds=1)
    if defect == "tie":
        ingest_global_document_review(*foundation, review, clock=lambda: later)
    changed = replace(review, reviewer="Synthetic second annotation")
    if defect == "forged_source":
        changed = replace(changed, source_document_sha256="f" * 64)
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: later + timedelta(seconds=1) if defect == "future_completion" else later
    ).ingest(reviews.GlobalDocumentReviewAdapter(changed, later),
             ProviderDatasetRequest(reviews.DATASET, changed.market, changed.subject, later))
    if defect == "tamper":
        digest = _read(foundation, later)["captures"][-1]["raw_data_hash"]
        (foundation[1].root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    result = _read(foundation, later)
    assert not result["source_bound"] and result["observations"] == []
    assert len(result["captures"]) >= 2


def test_plan_schema_decimal_and_null_parsing_are_explicit(foundation):
    review = _review(foundation)
    document = review.document()
    plan = {"review": {k: v for k, v in document.items() if k != "rows"}, "rows": document["rows"]}
    assert reviews.parse_global_document_review(plan) == review
    plan["rows"][0]["source_value"] = 1.23
    with pytest.raises(ValueError):
        reviews.parse_global_document_review(plan)
    plan["rows"][0].update(source_value="", value_status="unreadable")
    assert reviews.parse_global_document_review(plan).rows[0].source_value is None
    plan["review"]["financial_scoring_authorized"] = True
    with pytest.raises(ValueError):
        reviews.parse_global_document_review(plan)


@pytest.mark.parametrize("name", ["tencent-2025-income.toml", "maybank-2025-summary.toml"])
def test_checked_in_plans_are_unqualified_contracts_not_admitted_fixtures(name):
    plan = tomllib.loads((Path("config/global-document-reviews") / name).read_text())
    assert len(reviews.parse_global_document_review(plan).rows) == 4


def test_cli_previews_without_writes_and_rejects_backdated_write(foundation, tmp_path):
    review = _review(foundation)
    plan = tmp_path / "plan.toml"
    doc = review.document()
    metadata = {key: value for key, value in doc.items() if key != "rows"}
    lines = ["[review]", *[f"{key} = {json.dumps(value)}" for key, value in metadata.items()],
             "[[rows]]", *[f"{key} = {json.dumps(value)}" for key, value in doc["rows"][0].items()]]
    plan.write_text("\n".join(lines))
    args = [sys.executable, "scripts/review_global_document.py",
        "--database", str(foundation[0].path),
        "--artifact-root", str(foundation[1].root), "--review-plan", str(plan),
        "--as-of", RECORDED.isoformat()]
    before = foundation[0].path.read_bytes()
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)["persisted"] is False
    result = subprocess.run([*args, "--write"], capture_output=True, text=True)
    assert result.returncode == 2 and "preview-only" in result.stderr
    assert foundation[0].path.read_bytes() == before
