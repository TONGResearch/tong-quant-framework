"""Original ratios stay visible without becoming monetary facts or trading authority."""

import json
import sqlite3
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
from tong_quant.data.global_document_review_inputs import read_global_document_review_inputs
from tong_quant.data.global_ratio_review_inputs import (
    ingest_global_ratio_review,
    prepare_global_ratio_review,
    read_global_ratio_review_inputs,
)
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import global_documents as source
from tong_quant.data.providers import global_ratio_reviews as ratios
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.data.reviewed_ratio_inputs import (
    ReviewedRatioResearchInput,
    read_reviewed_ratio_research_input,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.financial.ratio_questions import review_ratio_questions

NOW = datetime(2026, 10, 29, tzinfo=UTC)
REVIEWED, RECORDED = NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)
URL = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf"


def _row(**changes):
    return ratios.GlobalRatioRow(**{"row_key": "ratio", "native_label": "Synthetic ratio (%)",
        "reporting_scope": "group", "period_basis": "instant", "period_start": None,
        "period_end": date(2025, 12, 31), "column_kind": "current", "column_label": "Group 2025",
        "source_unit": "percent", "source_unit_label": "%", "source_value": Decimal("106.7"),
        "value_status": "transcribed", "raw_cell_text": "106.7", "pdf_page": 5,
        "printed_page": "3", "restatement_label": "not_marked", "definition_note": "unknown",
        "denominator_note": "unknown", "regulatory_scope_note": "unknown", **changes})


def _capture_source(store, artifacts, *, at=NOW, error="", url=URL):
    request = ProviderDatasetRequest(source.DATASET, Market.HONG_KONG, "0700.HK", at,
        {"document_url": url, "landing_url": url, "issuer_label": "Synthetic",
         "period_end": "2025-12-31", "document_kind": "annual_report"})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        source.GlobalDocumentAdapter(Market.HONG_KONG, clock=lambda: at,
            download=lambda _: source.DocumentCapture(
                None if error else b"%PDF-1.7\nSynthetic", error)), request)


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "ratios.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    _capture_source(store, artifacts)
    return store, artifacts


def _review(foundation, rows=None, **changes):
    receipt = read_global_document_inputs(*foundation, Market.HONG_KONG, "0700.HK", URL, as_of=NOW)
    return ratios.GlobalRatioReview(**{"market": Market.HONG_KONG, "subject": "0700.HK",
        "document_url": URL, "source_evidence_id": receipt["selected_evidence_id"],
        "source_envelope_sha256": receipt["captures"][0]["raw_data_hash"],
        "source_document_sha256": receipt["document_sha256"], "source_available_at": NOW,
        "reviewed_at": REVIEWED, "reviewer": "Synthetic single reviewer",
        "report_period_end": date(2025, 12, 31), "rows": rows or (_row(),), **changes})


def _read(foundation, at=RECORDED):
    return read_global_ratio_review_inputs(*foundation, Market.HONG_KONG, "0700.HK", URL,
                                           as_of=at)


def test_preview_recording_and_deterministic_utc_reads(foundation):
    review = _review(foundation)
    before = foundation[0].path.read_bytes()
    batch = prepare_global_ratio_review(*foundation, review, as_of=REVIEWED)
    assert batch.records[0].payload["observations"][0]["unqualified_reported_percent"] == "106.7"
    assert before == foundation[0].path.read_bytes()
    ingest_global_ratio_review(*foundation, review, clock=lambda: RECORDED)
    assert _read(foundation, REVIEWED)["status"] == "missing"
    result = _read(foundation)
    assert result["source_bound"] and result["status"] == "MANUAL_RATIO_TRANSCRIPTION_UNQUALIFIED"
    assert result["recorded_at"] == RECORDED.isoformat()
    assert all(result[key] is False for key in ratios.AUTHORITY_FLAGS)
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    assert result["freshness"] == "UNASSESSED"
    after = foundation[0].path.read_bytes()
    assert result == _read(foundation, RECORDED.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    digest = result.pop("input_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()
    assert after == foundation[0].path.read_bytes()


@pytest.mark.parametrize("value", ["-1.23", "0", "1.23", "106.7", "999.999", "-1000"])
def test_original_percent_is_never_scaled_capped_or_treated_as_money(value):
    row = _row(source_value=Decimal(value))
    doc = row.observation()
    assert doc["source_value"] == value and doc["unqualified_reported_percent"] == value
    assert "currency" not in doc and "unqualified_scaled_amount" not in doc
    assert doc["canonical_metric"] is None


@pytest.mark.parametrize("changes", [
    {"source_unit": "fraction"}, {"source_unit": "million"}, {"source_value": 1.23},
    {"source_value": Decimal("NaN")}, {"source_value": Decimal("Infinity")},
    {"source_value": Decimal("1e13")}, {"source_value": Decimal("1e-13")},
    {"source_value": Decimal("1000000000000.000000000001")},
    {"source_value": Decimal("1." + "1" * 33)}, {"source_value": None},
    {"value_status": "missing"}, {"pdf_page": True}, {"pdf_page": 0}, {"pdf_page": 1001},
    {"reporting_scope": "regulatory_group_guess"}, {"period_basis": "ytd"},
    {"period_start": date(2025, 1, 1)}, {"period_basis": "reported_annual"},
    {"period_basis": "unknown", "period_start": date(2025, 1, 1)},
    {"definition_note": ""}, {"denominator_note": ""}, {"regulatory_scope_note": ""},
    {"native_label": "password=synthetic-not-real"}, {"source_unit_label": ""},
])
def test_invalid_ratio_contract_or_sensitive_annotations_reject(changes):
    with pytest.raises(ValueError):
        _row(**changes)


@pytest.mark.parametrize("status", ["missing", "unreadable", "conflicting"])
def test_unresolved_percentage_is_visible_not_zero(foundation, status):
    review = _review(foundation, (_row(value_status=status, source_value=None,
                                       raw_cell_text="Not resolved"),))
    ingest_global_ratio_review(*foundation, review, clock=lambda: RECORDED)
    row = _read(foundation)["observations"][0]
    assert row["value_status"] == status and row["unqualified_reported_percent"] is None


def test_scope_basis_and_comparative_rows_preserve_distinct_annotations(foundation):
    current = _row()
    annual = replace(current, row_key="annual", period_basis="reported_annual",
        period_start=date(2025, 1, 1))
    bank = replace(current, row_key="bank", reporting_scope="bank")
    prior = replace(current, row_key="prior", column_kind="comparative",
        column_label="Group 2024", period_end=date(2024, 12, 31))
    review = _review(foundation, (current, annual, bank, prior))
    assert len(prepare_global_ratio_review(*foundation, review, as_of=RECORDED).records[0].payload[
        "observations"]) == 4
    with pytest.raises(ValueError):
        _review(foundation, (current, replace(current, row_key="duplicate")))
    with pytest.raises(ValueError):
        _review(foundation, (replace(current, column_kind="comparative"),))
    with pytest.raises(ValueError):
        replace(annual, period_start=date(2026, 1, 1))


@pytest.mark.parametrize("changes", [
    {"source_evidence_id": "0" * 64}, {"source_envelope_sha256": "1" * 64},
    {"source_document_sha256": "2" * 64}, {"source_available_at": NOW - timedelta(seconds=1)},
    {"report_period_end": date(2024, 12, 31), "rows": (_row(
        period_end=date(2024, 12, 31)),)},
])
def test_wrong_source_pins_reject(foundation, changes):
    with pytest.raises(ValueError):
        prepare_global_ratio_review(*foundation, _review(foundation, **changes), as_of=RECORDED)


@pytest.mark.parametrize("changes", [
    {"source_available_at": RECORDED}, {"reviewed_at": NOW.replace(tzinfo=None)},
    {"reviewer": ""}, {"source_document_sha256": "bad"},
])
def test_invalid_review_metadata_rejects(foundation, changes):
    with pytest.raises(ValueError):
        _review(foundation, **changes)


def test_no_cross_dataset_or_research_wrapper_promotion(foundation):
    ingest_global_ratio_review(*foundation, _review(foundation), clock=lambda: RECORDED)
    money = read_global_document_review_inputs(*foundation, Market.HONG_KONG, "0700.HK", URL,
                                               as_of=RECORDED)
    assert money["status"] == "missing" and not money["observations"]
    with pytest.raises(ValueError):
        ReviewedDocumentResearchInput(financial_input_json(_read(foundation)), "bank")
    review = _review(foundation)
    with pytest.raises(ValueError):
        ratios.GlobalRatioReviewAdapter(review, RECORDED).fetch(ProviderDatasetRequest(
            "global_document_monetary_review", review.market, review.subject, RECORDED))
    with pytest.raises(ValueError):
        prepare_global_ratio_review(*foundation, review, as_of=NOW)


@pytest.mark.parametrize("failure", [False, True])
def test_new_parent_capture_or_failure_invalidates_ratios_without_fallback(foundation, failure):
    ingest_global_ratio_review(*foundation, _review(foundation), clock=lambda: RECORDED)
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403" if failure else "")
    assert _read(foundation)["source_bound"]
    assert not _read(foundation, later)["source_bound"]
    assert _read(foundation, later)["observations"] == []


@pytest.mark.parametrize("defect", ["tamper", "tie", "future_completion", "forged_source",
                                   "batch_owner", "artifact_owner"])
def test_latest_invalid_ratio_cannot_fall_back(foundation, defect):
    store, artifacts = foundation
    review = _review(foundation)
    ingest_global_ratio_review(*foundation, review, clock=lambda: RECORDED)
    later = RECORDED + timedelta(seconds=1)
    if defect == "tie":
        ingest_global_ratio_review(*foundation, review, clock=lambda: later)
    changed = replace(review, reviewer="Synthetic second annotation")
    if defect == "forged_source":
        changed = replace(changed, source_document_sha256="f" * 64)
    batch = ratios.GlobalRatioReviewAdapter(changed, later).fetch(ProviderDatasetRequest(
        ratios.DATASET, changed.market, changed.subject, later))
    result = ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: later + timedelta(seconds=1) if defect == "future_completion" else later
    ).ingest(ratios.GlobalRatioReviewAdapter(changed, later), ProviderDatasetRequest(
        ratios.DATASET, changed.market, changed.subject, later))
    if defect == "tamper":
        digest = batch.raw_data_hash
        (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    elif defect == "batch_owner":
        with sqlite3.connect(store.path) as connection:
            connection.execute("UPDATE ingestion_batches SET status = 'failed' WHERE batch_id = ?",
                               (result.batch_id,))
    elif defect == "artifact_owner":
        with sqlite3.connect(store.path) as connection:
            connection.execute("UPDATE provider_artifacts SET byte_size = 1 WHERE artifact_id = ?",
                               (batch.artifacts[0].artifact_id,))
    receipt = _read(foundation, later)
    assert receipt["status"] == "rejected_or_ambiguous"
    assert not receipt["source_bound"] and not receipt["observations"]
    assert len(receipt["captures"]) >= 2


def test_parser_does_not_guess_units_nulls_or_extra_authority_fields(foundation):
    doc = _review(foundation).document()
    plan = {"review": {key: value for key, value in doc.items() if key != "rows"},
            "rows": doc["rows"]}
    assert ratios.parse_global_ratio_review(plan) == _review(foundation)
    plan["rows"][0]["source_value"] = 0.0123
    with pytest.raises(ValueError):
        ratios.parse_global_ratio_review(plan)
    plan["rows"][0].update(source_value="", value_status="missing")
    assert ratios.parse_global_ratio_review(plan).rows[0].source_value is None
    plan["review"]["financial_scoring_authorized"] = True
    with pytest.raises(ValueError):
        ratios.parse_global_ratio_review(plan)


def test_ratio_ingestion_is_idempotent_at_same_recording_instant(foundation):
    first = ingest_global_ratio_review(*foundation, _review(foundation), clock=lambda: RECORDED)
    second = ingest_global_ratio_review(*foundation, _review(foundation), clock=lambda: RECORDED)
    # Attempts have distinct audit IDs; identical evidence must not duplicate or lose ownership.
    assert first.batch_id != second.batch_id
    assert len(_read(foundation)["captures"]) == 1


def test_cli_previews_without_writing_and_forbids_backdating(foundation, tmp_path):
    document = _review(foundation).document()
    lines = ["[review]", *[f"{key} = {json.dumps(value)}" for key, value in document.items()
                           if key != "rows"], "[[rows]]",
             *[f"{key} = {json.dumps(value if value is not None else '')}"
               for key, value in document["rows"][0].items()]]
    plan = tmp_path / "ratio.toml"
    plan.write_text("\n".join(lines))
    args = [sys.executable, "scripts/review_global_document.py", "--kind", "ratio",
        "--database", str(foundation[0].path), "--artifact-root", str(foundation[1].root),
        "--review-plan", str(plan), "--as-of", RECORDED.isoformat()]
    before = foundation[0].path.read_bytes()
    preview = subprocess.run(args, capture_output=True, text=True)
    assert preview.returncode == 2 and not preview.stderr
    assert json.loads(preview.stdout)["persisted"] is False
    rejected = subprocess.run([*args, "--write"], capture_output=True, text=True)
    assert rejected.returncode == 2 and "preview-only" in rejected.stderr
    assert before == foundation[0].path.read_bytes()


def test_real_maybank_ratio_plan_keeps_percent_and_unknown_definitions():
    plan = tomllib.loads(Path(
        "config/global-document-reviews/maybank-2025-ratios.toml").read_text())
    review = ratios.parse_global_ratio_review(plan)
    assert review.market == Market.MALAYSIA and review.subject == "1155.KL"
    assert len(review.rows) == 5
    assert all(row.source_unit == "percent" for row in review.rows)
    assert all(row.denominator_note == "unknown" for row in review.rows)
    assert {row.native_label for row in review.rows} >= {"Net impaired loans (%)",
                                                       "Loan loss coverage (%)"}
    assert next(row for row in review.rows if row.row_key == "loan_loss_coverage_group_2025"
                ).source_value == Decimal("106.7")


def test_integrated_liquidity_plan_keeps_rolling_basis_and_separate_original_source():
    review = ratios.parse_global_ratio_review(tomllib.loads(Path(
        "config/global-document-reviews/maybank-2025-integrated-liquidity.toml").read_text()))
    old = ratios.parse_global_ratio_review(tomllib.loads(Path(
        "config/global-document-reviews/maybank-2025-ratio-definitions.toml").read_text()))
    assert (review.market, review.subject) == (old.market, old.subject)
    assert review.document_url != old.document_url
    assert review.source_document_sha256 != old.source_document_sha256
    assert len(review.rows) == 3 and len(old.rows) == 6
    lcr, nsfr, ldr = review.rows
    assert lcr.source_value == Decimal("138.2")
    assert lcr.period_basis == "unknown" and lcr.period_start is None
    assert lcr.restatement_label == "marked_restated"
    assert "rolling 12-month average" in lcr.definition_note
    assert nsfr.source_value == Decimal("116.6") and ldr.source_value == Decimal("93.8")
    assert nsfr.period_basis == ldr.period_basis == "instant"
    assert all(row.source_unit == "percent" and row.pdf_page == 81 for row in review.rows)
    assert all(row.observation()["canonical_metric"] is None for row in review.rows)


def test_rolling_review_requires_own_document_parent_and_does_not_replace_other_receipt(foundation):
    original = _review(foundation)
    ingest_global_ratio_review(*foundation, original, clock=lambda: RECORDED)
    at = RECORDED + timedelta(seconds=1)
    recorded, failed_at = at + timedelta(seconds=2), at + timedelta(seconds=3)
    baseline = _read(foundation, at=failed_at)
    sibling_url = URL.replace("01231.pdf", "01232.pdf")
    _capture_source(*foundation, at=at, url=sibling_url)
    parent = read_global_document_inputs(*foundation, Market.HONG_KONG, "0700.HK",
                                         sibling_url, as_of=at)
    row = _row(period_basis="unknown", definition_note="Unqualified rolling 12-month average")
    wrong = replace(original, document_url=sibling_url, rows=(row,), reviewed_at=at)
    with pytest.raises(ValueError, match="exact current retained source"):
        prepare_global_ratio_review(*foundation, wrong, as_of=recorded)
    review = replace(wrong, source_evidence_id=parent["selected_evidence_id"],
        source_envelope_sha256=parent["captures"][0]["raw_data_hash"], source_available_at=at)
    # Identical synthetic PDF bytes still cannot substitute for the other document's parent.
    assert review.source_document_sha256 == original.source_document_sha256
    ingest_global_ratio_review(*foundation, review, clock=lambda: recorded)
    result = read_global_ratio_review_inputs(*foundation, Market.HONG_KONG, "0700.HK",
                                             sibling_url, as_of=recorded)
    assert result["source_bound"] and result["observations"][0]["period_basis"] == "unknown"
    bound = read_reviewed_ratio_research_input(*foundation, "0700.HK", Market.HONG_KONG,
        sibling_url, as_of=recorded, sector_profile="bank")
    question = review_ratio_questions(bound, row_keys=("ratio",))
    assert question["questions"][0]["status"] == "DEFINITION_REVIEW_REQUIRED"
    assert all(result[key] is False for key in ratios.AUTHORITY_FLAGS)
    _capture_source(*foundation, at=failed_at, url=sibling_url, error="http_403")
    failed = read_global_ratio_review_inputs(*foundation, Market.HONG_KONG, "0700.HK",
                                             sibling_url, as_of=failed_at)
    assert not failed["source_bound"]
    assert _read(foundation, at=failed_at) == baseline
    assert _read(foundation, at=RECORDED)["source_bound"]


def _research_input(foundation, rows=None):
    ingest_global_ratio_review(*foundation, _review(foundation, rows), clock=lambda: RECORDED)
    return read_reviewed_ratio_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
                                              as_of=RECORDED, sector_profile="bank")


def test_immutable_ratio_input_copies_context_and_explicit_source_questions(foundation):
    bound = _research_input(foundation)
    before = foundation[0].path.read_bytes()
    bound.validate_context(symbol="0700.HK", market=Market.HONG_KONG,
                           as_of=RECORDED.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    modified = bound.document()
    modified["observations"][0]["source_value"] = "0"
    assert bound.document()["observations"][0]["source_value"] == "106.7"
    questions = review_ratio_questions(bound, row_keys=("ratio", "not_transcribed"))
    assert questions == review_ratio_questions(bound, row_keys=("ratio", "not_transcribed"))
    assert [q["status"] for q in questions["questions"]] == [
        "DEFINITION_REVIEW_REQUIRED", "MISSING_REVIEWED_ROW"]
    assert questions["questions"][0]["observation"]["unqualified_reported_percent"] == "106.7"
    assert questions["sector_policy"] == "NOT_ADMITTED"
    assert all(questions[key] is False for key in ("financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "execution_authorized"))
    digest = questions.pop("review_hash")
    assert digest == sha256(financial_input_json(questions).encode()).hexdigest()
    assert foundation[0].path.read_bytes() == before


@pytest.mark.parametrize("context", [
    {"symbol": "0005.HK"}, {"market": Market.MALAYSIA},
    {"as_of": RECORDED + timedelta(microseconds=1)},
    {"as_of": RECORDED.replace(tzinfo=None)},
])
def test_ratio_research_context_mismatch_rejects(foundation, context):
    with pytest.raises(ValueError):
        _research_input(foundation).validate_context(**context)


@pytest.mark.parametrize("defect", ["checksum", "authority", "trust", "precision", "freshness",
    "future", "naive", "recording", "observations", "model", "sector", "tie", "subject",
    "denominator", "scope", "future_review", "money", "missing_with_rows", "source_bound"])
def test_rehashed_ratio_receipts_do_not_upgrade_authority_or_hide_invalid_data(foundation, defect):
    doc = _research_input(foundation).document()
    sector = "bank"
    if defect == "checksum":
        doc["status"] = "tampered"
    elif defect == "authority":
        doc["financial_scoring_authorized"] = True
    elif defect == "trust":
        doc["trust_ceiling"] = "VERIFIED"
    elif defect == "precision":
        doc["availability_precision"] = "exact"
    elif defect == "freshness":
        doc["freshness"] = "VERIFIED"
    elif defect == "future":
        doc["captures"][0]["available_at"] = RECORDED + timedelta(microseconds=1)
    elif defect == "naive":
        doc["as_of"] = RECORDED.replace(tzinfo=None)
    elif defect == "recording":
        doc["recorded_at"] = (RECORDED - timedelta(microseconds=1)).isoformat()
    elif defect == "observations":
        doc["observations"][0]["source_value"] = "0.0123"
    elif defect == "model":
        doc["model_version"] = "global-document-manual-review-v1"
    elif defect == "sector":
        sector = "admitted_bank"
    elif defect == "tie":
        doc["captures"].append({"available_at": RECORDED, "evidence_id": "tied"})
    elif defect == "subject":
        doc["review"]["subject"] = "0005.HK"
    elif defect == "denominator":
        doc["denominator_verified"] = True
    elif defect == "scope":
        doc["regulatory_scope_verified"] = True
    elif defect == "future_review":
        doc["review"]["reviewed_at"] = (RECORDED + timedelta(seconds=1)).isoformat()
    elif defect == "money":
        doc["review"]["rows"][0]["currency"] = "CNY"
    elif defect == "missing_with_rows":
        doc["status"] = "missing"
        doc["source_bound"] = False
    else:
        doc["source_bound"] = False
    if defect != "checksum":
        doc.pop("input_hash")
        doc["input_hash"] = sha256(financial_input_json(doc).encode()).hexdigest()
    with pytest.raises(ValueError):
        ReviewedRatioResearchInput(financial_input_json(doc), sector)


@pytest.mark.parametrize("keys", [(), ("ratio", "ratio"), ("",), (" x",), ("x",) * 33,
                                ([],), (1,), ["ratio"]])
def test_ratio_questions_require_explicit_bounded_unambiguous_keys(foundation, keys):
    with pytest.raises(ValueError):
        review_ratio_questions(_research_input(foundation), row_keys=keys)


def test_failed_ratio_source_is_preserved_and_questions_do_not_fall_back(foundation):
    missing = read_reviewed_ratio_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
        as_of=NOW, sector_profile="bank")
    assert missing.document()["status"] == "missing"
    original = _research_input(foundation)
    later = RECORDED + timedelta(seconds=1)
    _capture_source(*foundation, at=later, error="http_403")
    failed = read_reviewed_ratio_research_input(*foundation, "0700.HK", Market.HONG_KONG, URL,
        as_of=later, sector_profile="bank")
    result = review_ratio_questions(failed, row_keys=("ratio",))
    assert result["status"] == "SOURCE_INPUT_UNUSABLE"
    assert result["questions"][0]["status"] == "BLOCKED_INPUT"
    assert result["questions"][0]["observation"] is None
    assert original.document()["source_bound"]  # Copy preserves its old cutoff, not a live recheck.


def test_unresolved_ratio_questions_do_not_trust_nonempty_definition_notes(foundation):
    bound = _research_input(foundation, (_row(source_value=None, value_status="unreadable",
        definition_note="Caller-supplied description, not verified"),))
    result = review_ratio_questions(bound, row_keys=("ratio",))
    assert result["questions"][0]["status"] == "UNRESOLVED_VALUE"
    assert result["questions"][0]["definition_review_required"] is True
