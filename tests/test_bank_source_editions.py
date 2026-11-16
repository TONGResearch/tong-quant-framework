"""Source editions preserve provenance, original scope and unqualified research boundaries."""

import json
import tomllib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.config.settings import FinancialResearchSettings, load_settings
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.global_document_review_inputs import ingest_global_document_review
from tong_quant.data.global_ratio_review_inputs import ingest_global_ratio_review
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.global_document_reviews import parse_global_document_review
from tong_quant.data.providers.global_documents import (
    DATASET,
    DocumentCapture,
    GlobalDocumentAdapter,
)
from tong_quant.data.providers.global_ratio_reviews import (
    AUTHORITY_FLAGS,
    parse_global_ratio_review,
)
from tong_quant.data.reviewed_document_inputs import read_reviewed_document_research_input
from tong_quant.data.reviewed_ratio_inputs import (
    ReviewedRatioResearchInput,
    read_reviewed_ratio_research_input,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.config import research_engine_from_settings
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.financial.document_bank import (
    bank_document_input_coverage,
    parse_bank_document_plan,
)
from tong_quant.research.financial.document_freshness import (
    DocumentFreshnessPolicy,
    review_document_freshness,
)
from tong_quant.research.financial.ratio_arithmetic import (
    ManualRatioIdentity,
    RatioArithmeticPlan,
    parse_ratio_arithmetic_plan,
    review_ratio_arithmetic,
)
from tong_quant.research.financial.ratio_questions import review_ratio_questions

ROOT = Path("config/global-document-reviews")
NOW = datetime(2026, 10, 30, tzinfo=UTC)
OLD = NOW + timedelta(seconds=2)
NEW = NOW + timedelta(seconds=3)


def _money(name):
    return parse_global_document_review(tomllib.loads((ROOT / name).read_text()))


def _ratio(name):
    return parse_global_ratio_review(tomllib.loads((ROOT / name).read_text()))


def test_capital_equity_edition_preserves_all_previous_income_rows():
    old = _money("maybank-2025-income-comparatives.toml")
    new = _money("maybank-2025-capital-equity.toml")
    assert len(old.rows) == 22 and len(new.rows) == 31
    assert new.rows[:22] == old.rows
    assert new.reviewed_at >= old.reviewed_at
    assert new.source_document_sha256 == old.source_document_sha256
    assert new.source_evidence_id == old.source_evidence_id
    assert all(row.statement == "balance" and row.period_start is None for row in new.rows[22:])
    assert all(row.currency == "MYR" and row.source_unit == "thousand" for row in new.rows[22:])
    assert all(row.observation()["canonical_metric"] is None for row in new.rows)


@pytest.mark.parametrize("key,value,page", [
    ("group_parent_equity_2025", "93444627", 30),
    ("group_parent_equity_2024_comparative", "93970628", 30),
    ("group_non_controlling_interests_2025", "3397216", 30),
    ("group_non_controlling_interests_2024_comparative", "3236509", 30),
    ("group_cet1_capital_note59_2025", "69954382", 243),
    ("group_total_capital_note59_2025", "87042398", 243),
    ("group_total_rwa_note59_2025", "436091630", 244),
    ("group_net_impaired_loans_note12_2025", "5081470", 86),
    ("group_net_loans_note12_2025", "644366273", 86),
])
def test_source_plan_retains_exact_original_amount_unit_and_page(key, value, page):
    row = next(row for row in _money("maybank-2025-capital-equity.toml").rows if row.row_key == key)
    assert row.source_value == Decimal(value) and row.pdf_page == page
    assert row.printed_page == str(page - 2)
    assert row.column_kind == ("comparative" if "2024" in key else "current")
    assert row.period_end.year == (2024 if "2024" in key else 2025)


def test_definition_edition_preserves_summary_notes_and_does_not_alias_net_to_gross():
    old = _ratio("maybank-2025-ratios.toml")
    new = _ratio("maybank-2025-ratio-definitions.toml")
    assert len(old.rows) == 5 and len(new.rows) == 6
    assert new.rows[2:5] == old.rows[2:5]
    assert [row.source_value for row in new.rows[:2]] == [row.source_value for row in old.rows[:2]]
    assert all(row.pdf_page == 243 and row.printed_page == "241" for row in new.rows[:2])
    assert all("excluding" in row.regulatory_scope_note for row in new.rows[:2])
    assert all("no independently admitted" in row.denominator_note for row in new.rows[:2])
    net = new.rows[-1]
    assert net.native_label == "Ratio of net impaired loans" and net.pdf_page == 86
    assert net.source_value == Decimal("0.79") and "not gross NPL" in net.definition_note
    assert "Investment Accounts" in net.denominator_note
    assert net.observation()["denominator_verified"] is False
    assert net.observation()["regulatory_scope_verified"] is False
    assert not any("liquidity" in row.row_key for row in new.rows)


@pytest.fixture
def editions(tmp_path):
    # Synthetic source identity and clocks; these tests do not corroborate the real PDF.
    store = SQLiteStore(tmp_path / "editions.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    old_money = _money("maybank-2025-income-comparatives.toml")
    url = old_money.document_url
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        GlobalDocumentAdapter(Market.MALAYSIA, clock=lambda: NOW,
            download=lambda _: DocumentCapture(b"%PDF-1.7\nSynthetic edition contract")),
        ProviderDatasetRequest(DATASET, Market.MALAYSIA, "1155.KL", NOW,
            {"document_url": url, "landing_url": "https://www.maybank.com/en/investor-relations/"
                "financial-overview/annual-reports.page", "issuer_label": "Synthetic only",
             "period_end": "2025-12-31", "document_kind": "annual_report"}))
    source = read_global_document_inputs(store, artifacts, Market.MALAYSIA, "1155.KL", url,
                                         as_of=NOW)
    pins = {"source_evidence_id": source["selected_evidence_id"],
        "source_envelope_sha256": source["captures"][0]["raw_data_hash"],
        "source_document_sha256": source["document_sha256"], "source_available_at": NOW,
        "reviewed_at": NOW + timedelta(seconds=1), "reviewer": "Synthetic edition reviewer"}
    ingest_global_document_review(store, artifacts, replace(old_money, **pins), clock=lambda: OLD)
    ingest_global_ratio_review(store, artifacts,
        replace(_ratio("maybank-2025-ratios.toml"), **pins), clock=lambda: OLD)
    return store, artifacts, pins, url


def _freshness_input(editions, kind, at=OLD):
    store, artifacts, _, url = editions
    reader = (read_reviewed_ratio_research_input if kind == "ratio"
              else read_reviewed_document_research_input)
    return reader(store, artifacts, "1155.KL", Market.MALAYSIA, url,
                  as_of=at, sector_profile="bank")


@pytest.mark.parametrize("kind", ["money", "ratio"])
@pytest.mark.parametrize("limits,expected", [
    ((0, 0), "UNASSESSED"), ((1000, 2), "WITHIN_CONFIGURED_LIMITS"),
    ((1000, 1), "STALE"), ((1, 100), "STALE"), ((1000, 0), "UNASSESSED"),
])
def test_document_freshness_separates_source_review_period_and_diagnostic_limits(
    editions, kind, limits, expected,
):
    inputs = _freshness_input(editions, kind)
    before = editions[0].path.read_bytes()
    result = review_document_freshness(inputs, DocumentFreshnessPolicy(*limits))
    assert result["status"] == expected
    assert result["source_capture_age_seconds"] == 2
    assert result["review_recording_age_seconds"] == 0
    assert result["annotated_report_age_days"] == (OLD.date() - datetime(2025, 12, 31).date()).days
    assert all(result[key] is False for key in ("published_at_known",
        "latest_issuer_filing_verified", "source_qualified", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized"))
    digest = result.pop("assessment_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()
    assert editions[0].path.read_bytes() == before


@pytest.mark.parametrize("kind", ["money", "ratio"])
def test_new_manual_review_cannot_refresh_old_source_or_old_reporting_period(editions, kind):
    store, artifacts, pins, _ = editions
    at = NOW + timedelta(days=3)
    if kind == "ratio":
        review = _ratio("maybank-2025-ratios.toml")
        ingest = ingest_global_ratio_review
    else:
        review = _money("maybank-2025-income-comparatives.toml")
        ingest = ingest_global_document_review
    ingest(store, artifacts, replace(review, **{**pins, "reviewed_at": at}), clock=lambda: at)
    result = review_document_freshness(_freshness_input(editions, kind, at),
                                     DocumentFreshnessPolicy(1000, 86400))
    assert result["status"] == "STALE" and result["source_freshness"] == "STALE"
    assert result["review_recording_age_seconds"] == 0
    assert result["source_capture_age_seconds"] == 3 * 86400
    assert result["annotated_report_period_end"] == datetime(2025, 12, 31).date()


@pytest.mark.parametrize("kind", ["money", "ratio"])
@pytest.mark.parametrize("defect", ["missing", "failed", "tampered"])
def test_unusable_documents_keep_unknown_ages_and_cannot_fall_back(editions, kind, defect):
    store, artifacts, _, url = editions
    at = NEW
    if defect == "missing":
        at = NOW
    elif defect == "failed":
        ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
            GlobalDocumentAdapter(Market.MALAYSIA, clock=lambda: at,
                download=lambda _: DocumentCapture(None, "http_403")),
            ProviderDatasetRequest(DATASET, Market.MALAYSIA, "1155.KL", at,
                {"document_url": url, "landing_url": "https://www.maybank.com/en/investor-relations/"
                    "financial-overview/annual-reports.page", "issuer_label": "Synthetic only",
                 "period_end": "2025-12-31", "document_kind": "annual_report"}))
    else:
        for path in artifacts.root.rglob("*.bin"):
            path.write_bytes(b"{}")
    result = review_document_freshness(_freshness_input(editions, kind, at),
                                     DocumentFreshnessPolicy(1000, 86400))
    assert result["status"] == "BLOCKED_INPUT"
    assert all(result[name] is None for name in ("annotated_report_age_days",
        "source_capture_age_seconds", "review_recording_age_seconds"))
    assert result["source_freshness"] == result["report_freshness"] == "UNASSESSED"


@pytest.mark.parametrize("kind", ["money", "ratio"])
def test_document_freshness_uses_market_date_and_actual_utc_instants(editions, kind):
    at = NOW + timedelta(hours=20)
    first = _freshness_input(editions, kind, at)
    other = _freshness_input(editions, kind, at.astimezone(ZoneInfo("America/New_York")))
    result = review_document_freshness(first, DocumentFreshnessPolicy())
    assert result == review_document_freshness(other, DocumentFreshnessPolicy())
    assert result["decision_date"] == (NOW + timedelta(days=1)).date()
    assert result["annotated_report_age_days"] == (
        at.astimezone(ZoneInfo("Asia/Kuala_Lumpur")).date() - datetime(2025, 12, 31).date()).days
    assert result["source_capture_age_seconds"] == 20 * 3600


@pytest.mark.parametrize("field", ["maximum_report_age_days", "maximum_source_age_seconds"])
@pytest.mark.parametrize("value", [-1, True, 1.5, "100", None])
def test_document_freshness_settings_and_policy_reject_invalid_age_values(field, value):
    with pytest.raises(ValueError):
        DocumentFreshnessPolicy(**{field: value})
    with pytest.raises(ValueError):
        FinancialResearchSettings(**{field: value})


def test_document_freshness_configuration_reaches_financial_engine():
    settings = load_settings(Path("config/default.toml"))
    configured = replace(settings.research, financial=FinancialResearchSettings(1000, 86400))
    module = next(item for item in research_engine_from_settings(configured).modules
                  if isinstance(item, FinancialResearchModule))
    assert module.document_freshness_policy == DocumentFreshnessPolicy(1000, 86400)
    assert settings.research.financial.maximum_source_age_seconds == 0
    with pytest.raises(ValueError):
        DocumentFreshnessPolicy(model_version="unapproved")


@pytest.mark.parametrize("timezone", [UTC, ZoneInfo("Asia/Kuala_Lumpur")])
def test_edition_recording_preserves_old_receipts_and_blocks_stale_plan(editions, timezone):
    store, artifacts, pins, url = editions

    def money(at):
        return read_reviewed_document_research_input(store, artifacts, "1155.KL", Market.MALAYSIA,
            url, as_of=at.astimezone(timezone), sector_profile="bank")

    def ratio(at):
        return read_reviewed_ratio_research_input(store, artifacts, "1155.KL", Market.MALAYSIA,
            url, as_of=at.astimezone(timezone), sector_profile="bank")

    old_money, old_ratio = money(OLD), ratio(OLD)
    plan = parse_bank_document_plan(tomllib.loads(Path(
        "config/bank-document-input-plans/maybank-2025-comparatives.toml").read_text()))
    receipt = old_money.document()
    plan = replace(plan, source_document_sha256=pins["source_document_sha256"],
        review_evidence_id=receipt["selected_evidence_id"],
        review_envelope_sha256=receipt["captures"][-1]["raw_data_hash"], available_at=OLD)
    assert bank_document_input_coverage(old_money, plan)["status"] == "INPUT_COVERAGE_ONLY"
    ingest_global_document_review(store, artifacts,
        replace(_money("maybank-2025-capital-equity.toml"), **pins), clock=lambda: NEW)
    ingest_global_ratio_review(store, artifacts,
        replace(_ratio("maybank-2025-ratio-definitions.toml"), **pins), clock=lambda: NEW)
    assert money(OLD) == old_money and ratio(OLD) == old_ratio
    assert len(money(OLD).document()["observations"]) == 22
    assert len(ratio(OLD).document()["observations"]) == 5
    assert len(money(NEW).document()["observations"]) == 31
    new_ratio = ratio(NEW)
    assert len(new_ratio.document()["observations"]) == 6
    assert all(new_ratio.document()[name] is False for name in AUTHORITY_FLAGS)
    assert bank_document_input_coverage(money(NEW), plan)["status"] == (
        "SOURCE_PLAN_BINDING_MISMATCH")
    current_receipt = money(NEW).document()
    expanded = parse_bank_document_plan(tomllib.loads(Path(
        "config/bank-document-input-plans/maybank-2025-capital-equity.toml").read_text()))
    expanded = replace(expanded, source_document_sha256=pins["source_document_sha256"],
        review_evidence_id=current_receipt["selected_evidence_id"],
        review_envelope_sha256=current_receipt["captures"][-1]["raw_data_hash"], available_at=NEW)
    coverage = bank_document_input_coverage(money(NEW), expanded)
    assert coverage["status"] == "INPUT_COVERAGE_ONLY"
    statuses = [check["status"] for check in coverage["checks"]]
    assert statuses.count("MATCHED_UNQUALIFIED_ANNOTATIONS") == 11
    assert statuses.count("RATIO_CONTRACT_REQUIRED") == 5
    assert statuses.count("EXTERNAL_EVIDENCE_REQUIRED") == 3
    assert coverage["plan_status"] == "DRAFT_NOT_ADMITTED"
    assert coverage["financial_scoring_authorized"] is False
    assert coverage["historical_replay_eligible"] is False
    questions = review_ratio_questions(new_ratio,
        row_keys=("cet1_group_2025", "net_impaired_loans_note12_group_2025", "unreviewed_lcr"))
    assert [row["status"] for row in questions["questions"]] == [
        "DEFINITION_REVIEW_REQUIRED", "DEFINITION_REVIEW_REQUIRED", "MISSING_REVIEWED_ROW"]
    assert not questions["financial_scoring_authorized"]
    assert store.table_count("fundamental_facts") == 0
    assert store.table_count("research_reports") == 0


def test_expanded_plan_keeps_attribution_and_regulatory_questions_separate():
    plan = parse_bank_document_plan(tomllib.loads(Path(
        "config/bank-document-input-plans/maybank-2025-capital-equity.toml").read_text()))
    assert len(plan.requirements) == 19
    money = _money("maybank-2025-capital-equity.toml")
    selected = {row.row_key: row for row in money.rows}
    for item in plan.requirements:
        if item.kind == "monetary":
            row = selected[item.row_key].observation()
            assert all(str(row[name] if row[name] is not None else "") == value
                       for name, value in item.expected)
    requirements = {item.requirement_id: item for item in plan.requirements}
    assert requirements["parent_equity"].row_key == "group_parent_equity_2025"
    assert requirements["prior_parent_equity"].row_key == "group_parent_equity_2024_comparative"
    assert requirements["non_controlling_interests"].row_key == (
        "group_non_controlling_interests_2025")
    assert requirements["capital_cet1"].kind == "ratio_contract_required"
    assert requirements["liquidity_coverage"].kind == "ratio_contract_required"
    assert requirements["dated_valuation_inputs"].kind == "external_evidence_required"


def _arithmetic_inputs(editions, *, money_changes=None, ratio_changes=None):
    store, artifacts, pins, url = editions
    money = _money("maybank-2025-capital-equity.toml")
    ratios = _ratio("maybank-2025-ratio-definitions.toml")
    money = replace(money, rows=tuple(replace(row, **(money_changes or {}).get(row.row_key, {}))
                                      for row in money.rows), **pins)
    ratios = replace(ratios, rows=tuple(replace(row, **(ratio_changes or {}).get(row.row_key, {}))
                                       for row in ratios.rows), **pins)
    ingest_global_document_review(store, artifacts, money, clock=lambda: NEW)
    ingest_global_ratio_review(store, artifacts, ratios, clock=lambda: NEW)
    cutoff = NEW + timedelta(seconds=1)
    return (read_reviewed_document_research_input(store, artifacts, "1155.KL", Market.MALAYSIA,
                url, as_of=cutoff, sector_profile="bank"),
            read_reviewed_ratio_research_input(store, artifacts, "1155.KL", Market.MALAYSIA,
                url, as_of=cutoff, sector_profile="bank"))


def _arithmetic_plan(money, ratios, *, identities=None):
    m, r = money.document(), ratios.document()
    return RatioArithmeticPlan(m["selected_evidence_id"], m["captures"][-1]["raw_data_hash"],
        r["selected_evidence_id"], r["captures"][-1]["raw_data_hash"],
        m["review"]["source_document_sha256"], NEW,
        identities or (ManualRatioIdentity("cet1_group_2025", "group_cet1_capital_note59_2025",
            "group_total_rwa_note59_2025", 3, "half_even", "Synthetic explicit candidate only"),))


def test_explicit_ratio_arithmetic_is_deterministic_not_source_or_formula_admission(editions):
    money, ratios = _arithmetic_inputs(editions)
    plan = _arithmetic_plan(money, ratios, identities=(
        ManualRatioIdentity("cet1_group_2025", "group_cet1_capital_note59_2025",
            "group_total_rwa_note59_2025", 3, "half_even", "Synthetic explicit capital candidate"),
        ManualRatioIdentity("total_capital_group_2025", "group_total_capital_note59_2025",
            "group_total_rwa_note59_2025", 3, "half_even", "Synthetic explicit capital candidate"),
        ManualRatioIdentity("net_impaired_loans_note12_group_2025",
            "group_net_impaired_loans_note12_2025", "group_net_loans_note12_2025",
            2, "half_even", "Synthetic explicit net-loan candidate")))
    first = review_ratio_arithmetic(money, ratios, plan)
    with localcontext() as context:
        context.prec = 2
        assert first == review_ratio_arithmetic(money, ratios, plan)
    assert first["status"] == "TRANSCRIPTION_ARITHMETIC_ONLY"
    assert [row["rounded_percent"] for row in first["checks"]] == ["16.041", "19.960", "0.79"]
    assert all(row["status"] == "ARITHMETIC_AGREES_AS_TRANSCRIBED" for row in first["checks"])
    assert all(first[key] is False for key in (
        "formula_mapping_verified", "issuer_rounding_verified",
        "regulatory_scope_verified", "canonical_population_authorized", "independent_review",
        "financial_scoring_authorized", "investment_scoring_authorized", "validation_authorized",
        "historical_replay_eligible", "execution_authorized"))
    digest = first.pop("review_hash")
    assert digest == sha256(financial_input_json(first).encode()).hexdigest()
    assert first["checks"][0]["ratio_observation"]["regulatory_scope_verified"] is False
    offset = ratios.document()
    offset["review"]["source_available_at"] = NOW.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur")).isoformat()
    offset.pop("input_hash")
    offset["input_hash"] = sha256(financial_input_json(offset).encode()).hexdigest()
    assert review_ratio_arithmetic(money,
        ReviewedRatioResearchInput(financial_input_json(offset), "bank"), plan)["status"] == (
        "TRANSCRIPTION_ARITHMETIC_ONLY")


@pytest.mark.parametrize("changes,status", [
    ({"reporting_scope": "bank"}, "ROW_CONTEXT_MISMATCH"),
    ({"currency": "USD"}, "ROW_CONTEXT_MISMATCH"),
    ({"source_unit": "million"}, "ROW_CONTEXT_MISMATCH"),
    ({"source_unit_label": "Different unit label"}, "ROW_CONTEXT_MISMATCH"),
    ({"restatement_label": "unknown"}, "ROW_CONTEXT_MISMATCH"),
    ({"period_end": datetime(2024, 12, 31).date(), "column_kind": "comparative"},
     "ROW_CONTEXT_MISMATCH"),
    ({"statement": "income", "period_start": datetime(2025, 1, 1).date()},
     "UNSUPPORTED_PERIOD_BASIS"),
    ({"source_value": None, "value_status": "conflicting"}, "UNRESOLVED_VALUE"),
    ({"source_value": Decimal(0)}, "NONPOSITIVE_DENOMINATOR"),
    ({"source_value": Decimal(-1)}, "NONPOSITIVE_DENOMINATOR"),
])
def test_ratio_arithmetic_rejects_mixed_context_and_unusable_denominators(
    editions, changes, status,
):
    money, ratios = _arithmetic_inputs(editions,
        money_changes={"group_total_rwa_note59_2025": changes})
    result = review_ratio_arithmetic(money, ratios, _arithmetic_plan(money, ratios))
    assert result["checks"][0]["status"] == status
    assert result["checks"][0]["rounded_percent"] is None


@pytest.mark.parametrize("numerator,displayed", [(10, "2"), (14, "4"), (-10, "-2")])
def test_exact_fraction_rounding_handles_positive_and_negative_half_even_ties(
    editions, numerator, displayed,
):
    money, ratios = _arithmetic_inputs(editions, money_changes={
        "group_cet1_capital_note59_2025": {"source_value": Decimal(numerator)},
        "group_total_rwa_note59_2025": {"source_value": Decimal(400)}},
        ratio_changes={"cet1_group_2025": {"source_value": Decimal(displayed)}})
    plan = _arithmetic_plan(money, ratios, identities=(ManualRatioIdentity("cet1_group_2025",
        "group_cet1_capital_note59_2025", "group_total_rwa_note59_2025", 0, "half_even",
        "Synthetic explicit rounding test; not an issuer convention"),))
    check = review_ratio_arithmetic(money, ratios, plan)["checks"][0]
    assert check["rounded_percent"] == displayed
    assert check["status"] == "ARITHMETIC_AGREES_AS_TRANSCRIBED"
    assert check["exact_residual_percent_fraction"]["numerator"] != "0"


@pytest.mark.parametrize("defect,status", [("precision", "DISPLAY_PRECISION_MISMATCH"),
    ("missing", "MISSING_REVIEWED_ROW"), ("annual", "UNSUPPORTED_PERIOD_BASIS"),
    ("unresolved", "UNRESOLVED_VALUE"), ("residual", "ARITHMETIC_RESIDUAL_AS_TRANSCRIBED")])
def test_ratio_arithmetic_preserves_bad_display_missing_annual_and_conflicting_cases(
    editions, defect, status,
):
    changes = {"period_basis": "reported_annual", "period_start": datetime(2025, 1, 1).date()}
    if defect == "unresolved":
        changes = {"source_value": None, "value_status": "unreadable"}
    elif defect == "residual":
        changes = {"source_value": Decimal("1.000")}
    elif defect != "annual":
        changes = {}
    money, ratios = _arithmetic_inputs(editions, ratio_changes={"cet1_group_2025": changes})
    plan = _arithmetic_plan(money, ratios)
    identity = plan.identities[0]
    if defect == "precision":
        identity = replace(identity, decimal_places=2)
    elif defect == "missing":
        identity = replace(identity, ratio_row_key="not_transcribed")
    result = review_ratio_arithmetic(money, ratios, replace(plan, identities=(identity,)))
    assert result["checks"][0]["status"] == status
    assert not result["financial_scoring_authorized"]


@pytest.mark.parametrize("field", [
    "money_evidence_id", "ratio_evidence_id", "money_envelope_sha256",
                                 "ratio_envelope_sha256", "source_document_sha256"])
def test_arithmetic_plan_does_not_rebind_stale_receipt_pins(editions, field):
    money, ratios = _arithmetic_inputs(editions)
    plan = replace(_arithmetic_plan(money, ratios), **{field: "f" * 64})
    result = review_ratio_arithmetic(money, ratios, plan)
    assert result["status"] == "SOURCE_PLAN_BINDING_MISMATCH"
    assert result["checks"][0]["status"] == "BLOCKED_INPUT"


@pytest.mark.parametrize("when", [NOW, NEW + timedelta(seconds=2)])
def test_arithmetic_plan_availability_cannot_predate_evidence_or_follow_cutoff(editions, when):
    money, ratios = _arithmetic_inputs(editions)
    with pytest.raises(ValueError):
        review_ratio_arithmetic(money, ratios, replace(_arithmetic_plan(money, ratios),
                                                       available_at=when))


@pytest.mark.parametrize("defect", ["sector", "cutoff", "parent", "tamper", "source_failure"])
def test_arithmetic_cannot_mix_context_sources_or_revive_bad_current_input(editions, defect):
    money, ratios = _arithmetic_inputs(editions)
    plan = _arithmetic_plan(money, ratios)
    if defect == "sector":
        with pytest.raises(ValueError):
            review_ratio_arithmetic(money, replace(ratios, sector_profile="insurance"), plan)
        return
    document = ratios.document()
    if defect == "cutoff":
        document["as_of"] = NEW + timedelta(seconds=2)
    elif defect == "parent":
        document["review"]["source_document_sha256"] = "f" * 64
    elif defect == "source_failure":
        document.update(status="rejected_or_ambiguous", source_bound=False, observations=[])
    else:
        document["financial_scoring_authorized"] = True
    document.pop("input_hash")
    document["input_hash"] = sha256(financial_input_json(document).encode()).hexdigest()
    if defect in {"cutoff", "tamper"}:
        with pytest.raises(ValueError):
            review_ratio_arithmetic(money,
                ReviewedRatioResearchInput(financial_input_json(document), "bank"), plan)
    else:
        result = review_ratio_arithmetic(money,
            ReviewedRatioResearchInput(financial_input_json(document), "bank"), plan)
        assert result["status"] == ("SOURCE_PARENT_MISMATCH" if defect == "parent"
                                    else "SOURCE_INPUT_UNUSABLE")
        assert result["checks"][0]["rounded_percent"] is None


@pytest.mark.parametrize("changes", [{"decimal_places": True}, {"decimal_places": -1},
    {"decimal_places": 13}, {"rounding": "unknown"}, {"rationale": ""},
    {"rationale": "password=synthetic-not-real"}, {"ratio_row_key": "a b"},
    {"denominator_row_key": "n"}])
def test_arithmetic_identities_reject_ambiguous_precision_rounding_keys_and_secrets(changes):
    with pytest.raises(ValueError):
        ManualRatioIdentity(**{"ratio_row_key": "r", "numerator_row_key": "n",
            "denominator_row_key": "d", "decimal_places": 2, "rounding": "half_even",
            "rationale": "Synthetic", **changes})


def test_arithmetic_plan_parser_roundtrip_and_strict_field_ownership(editions):
    money, ratios = _arithmetic_inputs(editions)
    plan = _arithmetic_plan(money, ratios)
    doc = json.loads(financial_input_json(plan.document()))
    raw = {"plan": {key: value for key, value in doc.items()
                    if key not in {"identities", "model_version", "status"}},
           "identities": doc["identities"]}
    assert parse_ratio_arithmetic_plan(raw) == plan
    raw["identities"][0]["expected_percent"] = "16.041"
    with pytest.raises(ValueError):
        parse_ratio_arithmetic_plan(raw)
    with pytest.raises(ValueError):
        replace(plan, identities=plan.identities * 2)
