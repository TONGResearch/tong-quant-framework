import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.global_document_review_inputs import ingest_global_document_review
from tong_quant.data.global_ratio_review_inputs import ingest_global_ratio_review
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.market_value_reader import MarketValueInputReader
from tong_quant.data.native_financial_inputs import read_native_financial_research_input
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.eastmoney_market_values import (
    DATASET as MARKET_VALUE_DATASET,
)
from tong_quant.data.providers.eastmoney_market_values import (
    EastmoneyMarketValueAdapter,
    QuoteHttpCapture,
)
from tong_quant.data.providers.global_document_reviews import (
    GlobalDocumentReview,
    GlobalMonetaryRow,
)
from tong_quant.data.providers.global_documents import (
    DATASET as DOCUMENT_DATASET,
)
from tong_quant.data.providers.global_documents import DocumentCapture, GlobalDocumentAdapter
from tong_quant.data.providers.global_ratio_reviews import GlobalRatioReview, GlobalRatioRow
from tong_quant.data.providers.sec_body import SECBodyAdapter, SECBodyCapture
from tong_quant.data.providers.sec_submissions import SECSubmissionsAdapter, SECSubmissionsCapture
from tong_quant.data.providers.yahoo_fundamentals import (
    DATASET as NATIVE_DATASET,
)
from tong_quant.data.providers.yahoo_fundamentals import (
    NATIVE_METRICS,
    YahooFundamentalCapture,
    YahooFundamentalSnapshotAdapter,
)
from tong_quant.data.reviewed_document_inputs import read_reviewed_document_research_input
from tong_quant.data.reviewed_ratio_inputs import read_reviewed_ratio_research_input
from tong_quant.data.sec_body_inputs import build_sec_body_request
from tong_quant.data.sec_period_inputs import SECPeriodSelection, read_sec_period_research_input
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    EvidenceQuality,
    InvestmentAssessmentStatus,
    Market,
    ResearchModuleName,
    ResearchRunStatus,
    ScoreType,
)
from tong_quant.domain.models import Bar, FundamentalFact, Instrument
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.financial.document_bank import (
    BankDocumentInputPlan,
    BankDocumentRequirement,
)
from tong_quant.research.financial.market_value import MarketValueMatchingPolicy
from tong_quant.research.financial.nonfinancial_inputs import NonfinancialInputPolicy
from tong_quant.research.financial.ratio_arithmetic import ManualRatioIdentity, RatioArithmeticPlan
from tong_quant.research.investment import InvestmentAssessmentBuilder
from tong_quant.research.models import (
    ResearchContext,
    ResearchEvidence,
    ResearchRequest,
    ThesisInvalidationCondition,
)
from tong_quant.research.policy import PolicyResearchModule
from tong_quant.research.reporting import DefaultResearchReportBuilder
from tong_quant.research.repository import SQLiteResearchRepository
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.thesis_bindings import (
    ThesisConditionBinding,
    ThesisEvidenceReference,
    ThesisMetricBinding,
    ThesisPeriod,
    ThesisReportBindingPlan,
    thesis_report_binding_features,
)
from tong_quant.screening.models import (
    CompositeScore,
    HardScreenResult,
    OpportunityCandidate,
    ResearchQueueEntry,
    ScoreComponent,
    screening_instrument_id,
)
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository
from tong_quant.version import (
    FINANCIAL_RESEARCH_VERSION,
    RESEARCH_CONFIDENCE_VERSION,
    RESEARCH_REPORT_VERSION,
    RESEARCH_THESIS_REPORT_VERSION,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("legacy", [False, True])
def test_research_fold_availability_and_confidence_version_survive_storage(tmp_path, legacy):
    # Synthetic policy evidence exercises persistence, never source or investment admission.
    first = datetime(2026, 11, 1, 1, 45, tzinfo=ZoneInfo("America/New_York"), fold=0)
    second = first.replace(minute=15, fold=1)
    cutoff = second.replace(minute=30)
    store = SQLiteStore(tmp_path / "confidence-fold.sqlite3")
    store.initialize()
    instrument = Instrument("TEST", Market.US, "Synthetic", currency="USD",
                            available_at=first - timedelta(days=1), source="synthetic")
    entry = _queue_entry(instrument, cutoff)
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(instrument=instrument,
        discovery_source=entry.candidate.discovery_source, discovered_at=cutoff,
        admitted_at=cutoff, priority_score=entry.priority_score, urgency_score=entry.urgency_score,
        confidence_score=entry.confidence_score, research_score=entry.research_score.score,
        status=entry.status, thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic")
    evidence = tuple(replace(_policy_evidence(name, first),
        observed_at=first - timedelta(days=1), available_at=second if index % 2 else first)
        for index, name in enumerate(("regulatory_environment", "industrial_policy",
                                     "fiscal_policy", "monetary_policy", "geopolitical_factors")))
    context = ResearchContext(queue_id, entry, cutoff, (), {}, evidence)
    request = ResearchRequest(context, (ResearchModuleName.POLICY,),
        "Synthetic hypothesis", "Evidence may be misleading",
        (ThesisInvalidationCondition("fixture", "Synthetic changes", "fixture", "<", 0,
                                     "next observation", "Synthetic only"),))
    run = ResearchEngine(modules=(PolicyResearchModule(),)).run(request)
    if legacy:
        old_method = "weighted_geometric_with_weakest_link_cap"
        assessment = replace(run.report.assessments[0], confidence=replace(
            run.report.assessments[0].confidence, method=old_method))
        report = replace(run.report, assessments=(assessment,),
            confidence=replace(run.report.confidence, method=old_method),
            policy_assessment=replace(run.report.policy_assessment, assessment=assessment))
        run = replace(run, report=report)
    repository = SQLiteResearchRepository(store)
    run = replace(run, run_id=repository.start_run(request))
    repository.save_run(run)
    restored = SQLiteHistoricalReplayRepository(store).research_report(instrument, cutoff)
    assert restored is not None
    assessment = restored.assessments[0]
    assert assessment.available_at.astimezone(UTC) == second.astimezone(UTC)
    assert assessment.evaluated_at.astimezone(UTC) == cutoff.astimezone(UTC)
    assert assessment.confidence.point_in_time_integrity == 100
    assert restored.confidence == run.report.confidence
    assert assessment.confidence == run.report.assessments[0].confidence
    assert (RESEARCH_CONFIDENCE_VERSION in restored.confidence.method) is not legacy
    before = store.path.read_bytes()
    repeated = SQLiteHistoricalReplayRepository(store).research_report(instrument, cutoff)
    assert repeated == restored and store.path.read_bytes() == before
    assert store.table_count("fundamental_facts") == 0


@pytest.fixture(params=[Market.HONG_KONG, Market.MALAYSIA])
def multi_ratio_context(tmp_path, request):
    market = request.param
    symbol = "1155.KL" if market is Market.MALAYSIA else "0700.HK"
    captured = datetime(2026, 10, 31, tzinfo=UTC)
    as_of = captured + timedelta(seconds=3)
    store = SQLiteStore(tmp_path / "multi-ratios.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    urls = tuple((
        "https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/"
        f"synthetic-{index}.pdf" if market is Market.MALAYSIA else
        "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/"
        f"202604090123{index}.pdf") for index in range(4))
    parameters = tuple({"document_url": url, "landing_url": (
        "https://www.maybank.com/en/investor-relations/financial-overview/annual-reports.page"
        if market is Market.MALAYSIA else url), "issuer_label": "Synthetic only",
        "period_end": "2025-12-31", "document_kind": "annual_report"} for url in urls)
    for index in range(2):
        ProviderNeutralIngestionService(store, artifact_store=artifacts,
            clock=lambda: captured).ingest(GlobalDocumentAdapter(market,
                download=lambda _: DocumentCapture(b"%PDF-1.7\nSynthetic"), clock=lambda: captured),
                ProviderDatasetRequest(DOCUMENT_DATASET, market, symbol, captured,
                                       parameters[index]))
        source = read_global_document_inputs(store, artifacts, market, symbol, urls[index],
                                             as_of=captured)
        row = GlobalRatioRow("native_ratio", "Synthetic original ratio", "group",
            "unknown" if index else "instant", None, date(2025, 12, 31), "current", "Group 2025",
            "percent", "%", Decimal("138.2" if index else "106.7"), "transcribed",
            "138.2" if index else "106.7", 1, "1", "unknown",
            "Rolling average not admitted" if index else "unknown", "unknown", "unknown")
        rows = (row, replace(row, row_key="liquidity_only", native_label="Other original ratio",
            source_value=Decimal("116.6"), raw_cell_text="116.6")) if index else (row,)
        review = GlobalRatioReview(market, symbol, urls[index], source["selected_evidence_id"],
            source["captures"][0]["raw_data_hash"], source["document_sha256"], captured,
            captured + timedelta(seconds=1), "Synthetic reviewer", date(2025, 12, 31), rows)
        ingest_global_ratio_review(store, artifacts, review,
                                   clock=lambda: captured + timedelta(seconds=2))
    instrument = Instrument(symbol, market, "Synthetic only", available_at=captured)
    entry = _queue_entry(instrument, as_of)
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic")
    with store.read_snapshot():
        inputs = tuple(read_reviewed_ratio_research_input(store, artifacts, symbol, market, url,
            as_of=as_of, sector_profile="bank") for url in urls[:3])
    bars = tuple(Bar(instrument, captured - timedelta(days=100 - i),
        captured - timedelta(days=100 - i), Decimal(10 + i), Decimal(12 + i),
        Decimal(9 + i), Decimal(11 + i), Decimal(10000)) for i in range(100))
    older = FundamentalFact(instrument, "synthetic_old_fact", date(2025, 12, 31),
        captured, captured, Decimal(1), "Synthetic only")
    context = ResearchContext(queue_id, entry, as_of, bars, {"synthetic_old_fact": (older,)}, (),
        reviewed_ratio_inputs=inputs[0], supplemental_ratio_inputs=inputs[1:])
    return store, artifacts, context, parameters


def _multi_ratio_request(context):
    return ResearchRequest(context, (ResearchModuleName.FINANCIAL, ResearchModuleName.TECHNICAL),
        "Synthetic contract test, not admitted research", "Sources may be insufficient",
        (ThesisInvalidationCondition("fixture", "Inputs change", "ratio", "<", 0,
                                     "next observation", "Synthetic only"),))


def test_multiple_original_ratio_documents_survive_official_report_without_merging(
    multi_ratio_context,
):
    store, _, context, _ = multi_ratio_context
    financial_module = FinancialResearchModule(
        manual_ratio_row_keys=("native_ratio", "liquidity_only"))
    assessment = financial_module.evaluate(context, {})
    reversed_context = replace(context,
        supplemental_ratio_inputs=tuple(reversed(context.supplemental_ratio_inputs)))
    assert financial_module.evaluate(reversed_context, {}) == assessment
    assert assessment.available_at == context.as_of
    assert assessment.model_version == FINANCIAL_RESEARCH_VERSION
    assert assessment.score is None and assessment.confidence.confidence == 0
    features = assessment.features
    receipts = json.loads(features["supplemental_ratio_receipts_json"])
    assert receipts == sorted((item.document() for item in context.supplemental_ratio_inputs),
                              key=lambda item: item["document_url"])
    assert features["supplemental_ratio_document_count"] == 2
    assert features["supplemental_ratio_sector_policy"] == "NOT_ADMITTED"
    assert not features["supplemental_ratio_aggregation_authorized"]
    assert not features["supplemental_ratio_scoring_authorized"]
    freshness = json.loads(features["reviewed_source_freshness_json"])
    assert len(freshness) == 3
    assert [item["status"] for item in freshness] == ["UNASSESSED", "UNASSESSED", "BLOCKED_INPUT"]
    assert all(not item["latest_issuer_filing_verified"] for item in freshness)
    assert freshness[0]["source_capture_age_seconds"] == 3
    assert freshness[0]["review_recording_age_seconds"] == 1
    assert receipts[0]["observations"][0]["unqualified_reported_percent"] == "138.2"
    assert receipts[0]["observations"][0]["period_basis"] == "unknown"
    assert receipts[1]["status"] == "missing" and not receipts[1]["observations"]
    primary = json.loads(features["reviewed_ratio_receipt_json"])
    assert primary["observations"][0]["unqualified_reported_percent"] == "106.7"
    questions = json.loads(features["reviewed_ratio_questions_json"])["questions"]
    assert [item["status"] for item in questions] == [
        "DEFINITION_REVIEW_REQUIRED", "MISSING_REVIEWED_ROW"]
    no_supplements = replace(context, supplemental_ratio_inputs=())
    assert not any(key.startswith("supplemental_ratio_") for key in
                   financial_module.evaluate(no_supplements, {}).features)
    run = ResearchEngine(modules=(financial_module, TechnicalResearchModule()),
        repository=SQLiteResearchRepository(store)).run(_multi_ratio_request(context))
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    assert next(item for item in run.report.assessments if item.module is
                ResearchModuleName.TECHNICAL).features["macd_dif"] is not None
    restored = SQLiteHistoricalReplayRepository(store).research_report(
        context.queue_entry.candidate.instrument, context.as_of)
    assert restored is not None and restored.assessments == run.report.assessments
    assert InvestmentAssessmentBuilder().build(restored,
        assessed_at=context.as_of).investment_score is None
    assert store.table_count("fundamental_facts") == 0


@pytest.mark.parametrize("defect", ["list", "none", "string", "wrong_type", "too_many",
    "duplicate", "primary_duplicate", "no_primary", "sector", "cutoff", "symbol", "market"])
def test_supplemental_ratio_context_rejects_ambiguous_or_mismatched_inputs(
    multi_ratio_context, defect,
):
    store, artifacts, context, parameters = multi_ratio_context
    supplements = context.supplemental_ratio_inputs
    changes = {}
    if defect == "list":
        changes["supplemental_ratio_inputs"] = list(supplements)
    elif defect == "none":
        changes["supplemental_ratio_inputs"] = None
    elif defect == "string":
        changes["supplemental_ratio_inputs"] = "not a tuple"
    elif defect == "wrong_type":
        changes["supplemental_ratio_inputs"] = (object(),)
    elif defect == "too_many":
        changes["supplemental_ratio_inputs"] = supplements * 2
    elif defect == "duplicate":
        changes["supplemental_ratio_inputs"] = (supplements[0], supplements[0])
    elif defect == "primary_duplicate":
        changes["supplemental_ratio_inputs"] = (context.reviewed_ratio_inputs,)
    elif defect == "no_primary":
        changes["reviewed_ratio_inputs"] = None
    elif defect == "sector":
        changes["supplemental_ratio_inputs"] = (
            replace(supplements[0], sector_profile="insurance"),)
    else:
        instrument = context.queue_entry.candidate.instrument
        other_market = Market.HONG_KONG if instrument.market is Market.MALAYSIA else Market.MALAYSIA
        market = other_market if defect == "market" else instrument.market
        symbol = ("0005.HK" if market is Market.HONG_KONG else "1023.KL") if defect in {
            "symbol", "market"} else instrument.symbol
        url = parameters[1]["document_url"] if defect != "market" else (
            "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901240.pdf"
            if market is Market.HONG_KONG else
            "https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/test.pdf")
        mismatched = read_reviewed_ratio_research_input(store, artifacts, symbol, market, url,
            as_of=context.as_of + timedelta(seconds=1) if defect == "cutoff" else context.as_of,
            sector_profile="bank")
        changes["supplemental_ratio_inputs"] = (mismatched,)
    before = store.table_count("research_runs")
    with pytest.raises(ValueError):
        replace(context, **changes)
    assert store.table_count("research_runs") == before


@pytest.mark.parametrize("defect", ["receipt", "sector", "container"])
def test_supplemental_revalidation_precedes_research_run_writes(multi_ratio_context, defect):
    store, _, context, _ = multi_ratio_context
    if defect == "receipt":
        item = context.supplemental_ratio_inputs[0]
        object.__setattr__(item, "receipt_json", item.receipt_json + " ")
    elif defect == "sector":
        object.__setattr__(context.supplemental_ratio_inputs[0], "sector_profile", "insurance")
    else:
        object.__setattr__(context, "supplemental_ratio_inputs",
                           [context.supplemental_ratio_inputs[0]])
    with pytest.raises(ValueError):
        FinancialResearchModule().evaluate(context, {})
    with pytest.raises(ValueError):
        ResearchEngine(modules=(FinancialResearchModule(), TechnicalResearchModule()),
            repository=SQLiteResearchRepository(store)).run(_multi_ratio_request(context))
    assert store.table_count("research_runs") == 0


@pytest.mark.parametrize("failed_document", [0, 1])
def test_latest_failure_keeps_other_document_visible_without_fallback(
    multi_ratio_context, failed_document,
):
    store, artifacts, context, parameters = multi_ratio_context
    instrument = context.queue_entry.candidate.instrument
    at = context.as_of + timedelta(seconds=1)
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        GlobalDocumentAdapter(instrument.market, clock=lambda: at,
            download=lambda _: DocumentCapture(None, "http_403")),
        ProviderDatasetRequest(DOCUMENT_DATASET, instrument.market, instrument.symbol, at,
                               parameters[failed_document]))
    with store.read_snapshot():
        inputs = tuple(read_reviewed_ratio_research_input(store, artifacts, instrument.symbol,
            instrument.market, values["document_url"], as_of=at, sector_profile="bank")
            for values in parameters)
    current = replace(context, as_of=at, reviewed_ratio_inputs=inputs[0],
                      supplemental_ratio_inputs=inputs[1:])
    assessment = FinancialResearchModule(manual_ratio_row_keys=("native_ratio",)).evaluate(
        current, {})
    assert not inputs[failed_document].document()["source_bound"]
    assert inputs[1 - failed_document].document()["source_bound"]
    assert assessment.features["supplemental_ratio_document_count"] == 3  # Maximum accepted bound.
    assert assessment.available_at == at and assessment.score is None
    questions = json.loads(assessment.features["reviewed_ratio_questions_json"])["questions"]
    assert questions[0]["status"] == (
        "BLOCKED_INPUT" if failed_document == 0 else "DEFINITION_REVIEW_REQUIRED")
    receipts = json.loads(assessment.features["supplemental_ratio_receipts_json"])
    assert receipts[0] == inputs[1].document()
    if failed_document == 1:
        assert not receipts[0]["observations"]


@pytest.mark.parametrize("market,symbol,profile", [
    (Market.HONG_KONG, "0700.HK", "nonfinancial"),
    (Market.MALAYSIA, "1155.KL", "bank"),
])
@pytest.mark.parametrize("state", ["observed", "missing", "failed", "tampered"])
def test_manual_primary_receipt_persists_with_technical_research_but_no_investment_score(
    tmp_path, market, symbol, profile, state,
):
    # Synthetic screening/source fixtures test contracts, not real admission or returns.
    captured = datetime(2026, 10, 28, tzinfo=UTC)
    as_of = captured + timedelta(seconds=3)
    store = SQLiteStore(tmp_path / "manual-research.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    malaysia = market is Market.MALAYSIA
    url = ("https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/"
           "maybank-ar2025-financial-statements.pdf") if malaysia else (
        "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf")
    parameters = {"document_url": url, "landing_url": (
        "https://www.maybank.com/en/investor-relations/financial-overview/annual-reports.page"
        if malaysia else url), "issuer_label": "Synthetic only", "period_end": "2025-12-31",
        "document_kind": "annual_report"}
    if state != "missing":
        ProviderNeutralIngestionService(store, artifact_store=artifacts,
            clock=lambda: captured).ingest(GlobalDocumentAdapter(market,
                download=lambda _: DocumentCapture(b"%PDF-1.7\nSynthetic"), clock=lambda: captured),
                ProviderDatasetRequest(DOCUMENT_DATASET, market, symbol, captured, parameters))
        source = read_global_document_inputs(store, artifacts, market, symbol, url, as_of=captured)
        row = GlobalMonetaryRow("native_income", "Synthetic native income", "income", "group",
            date(2025, 1, 1), date(2025, 12, 31), "current", "Group 2025",
            "MYR" if malaysia else "CNY", "thousand", "Synthetic thousand", Decimal(10),
            "transcribed", "10", 1, "1", "unknown")
        review = GlobalDocumentReview(market, symbol, url, source["selected_evidence_id"],
            source["captures"][0]["raw_data_hash"], source["document_sha256"], captured,
            captured + timedelta(seconds=1), "Synthetic reviewer", date(2025, 12, 31),
            (row, replace(row, row_key="prior_income", source_value=Decimal(8),
                period_start=date(2024, 1, 1), period_end=date(2024, 12, 31),
                column_kind="comparative", column_label="Group 2024"),
             replace(row, row_key="ratio_numerator", native_label="Synthetic numerator",
                 statement="balance", period_start=None, source_value=Decimal(1067)),
             replace(row, row_key="ratio_denominator", native_label="Synthetic denominator",
                 statement="balance", period_start=None, source_value=Decimal(1000))))
        ingest_global_document_review(store, artifacts, review,
                                       clock=lambda: captured + timedelta(seconds=2))
        ratio_row = GlobalRatioRow("native_ratio", "Synthetic reported ratio", "group", "instant",
            None, date(2025, 12, 31), "current", "Group 2025", "percent", "%", Decimal("106.7"),
            "transcribed", "106.7", 1, "1", "unknown", "unknown", "unknown", "unknown")
        ratio_review = GlobalRatioReview(market, symbol, url, source["selected_evidence_id"],
            source["captures"][0]["raw_data_hash"], source["document_sha256"], captured,
            captured + timedelta(seconds=1), "Synthetic ratio reviewer", date(2025, 12, 31),
            (ratio_row,))
        ingest_global_ratio_review(store, artifacts, ratio_review,
                                   clock=lambda: captured + timedelta(seconds=2))
        if state == "failed":
            ProviderNeutralIngestionService(store, artifact_store=artifacts,
                clock=lambda: as_of).ingest(GlobalDocumentAdapter(market,
                    download=lambda _: DocumentCapture(None, "http_403"), clock=lambda: as_of),
                    ProviderDatasetRequest(DOCUMENT_DATASET, market, symbol, as_of, parameters))
        if state == "tampered":
            for path in artifacts.root.rglob("*"):
                if path.is_file():
                    path.write_bytes(b"{}")
    bound = read_reviewed_document_research_input(store, artifacts, symbol, market, url,
                                                 as_of=as_of, sector_profile=profile)
    native = read_native_financial_research_input(store, artifacts, symbol, market,
                                                 as_of=as_of, sector_profile=profile)
    ratios = read_reviewed_ratio_research_input(store, artifacts, symbol, market, url,
                                               as_of=as_of, sector_profile=profile)
    instrument = Instrument(symbol, market, "Synthetic", available_at=captured,
                            currency="MYR" if malaysia else "HKD")
    entry = _queue_entry(instrument, as_of)
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic")
    bars = tuple(Bar(instrument, captured - timedelta(days=100 - i),
        captured - timedelta(days=100 - i), Decimal(10 + i), Decimal(12 + i),
        Decimal(9 + i), Decimal(11 + i), Decimal(10000))
        for i in range(100))
    context = ResearchContext(queue_id, entry, as_of, bars, {}, (),
        native_financial_inputs=native, reviewed_document_inputs=bound,
        reviewed_ratio_inputs=ratios)
    with pytest.raises(ValueError, match="sector contexts disagree"):
        replace(context, reviewed_ratio_inputs=replace(ratios, sector_profile="insurance"))
    with pytest.raises(ValueError, match="reviewed ratio receipt"):
        FinancialResearchModule(manual_ratio_row_keys=("native_ratio",)).evaluate(
            replace(context, reviewed_ratio_inputs=None), {})
    request = ResearchRequest(context, (ResearchModuleName.FINANCIAL, ResearchModuleName.TECHNICAL),
        "Synthetic thesis", "Synthetic counter thesis", (ThesisInvalidationCondition(
            "fixture", "Fixture invalidation", "native_income", "<", 0, "annual", "Synthetic"),))
    ratio_only = replace(context, native_financial_inputs=None, reviewed_document_inputs=None)
    with pytest.raises(ValueError, match="context mismatch"):
        replace(ratio_only, as_of=as_of + timedelta(microseconds=1))
    fund = replace(instrument, asset_type=AssetType.ETF)
    with pytest.raises(ValueError, match="requires equity"):
        replace(ratio_only, bars=(), queue_entry=_queue_entry(fund, as_of))
    original_json = ratios.receipt_json
    changed = ratios.document()
    changed["denominator_verified"] = True
    object.__setattr__(ratios, "receipt_json", json.dumps(changed))
    with pytest.raises(ValueError):
        FinancialResearchModule().evaluate(context, {})
    with pytest.raises(ValueError):
        ResearchEngine(modules=(FinancialResearchModule(), TechnicalResearchModule()),
            repository=SQLiteResearchRepository(store)).run(request)
    assert store.table_count("research_runs") == 0
    object.__setattr__(ratios, "receipt_json", original_json)
    older = FundamentalFact(instrument, "synthetic_old_fact", date(2025, 12, 31),
        captured, captured, Decimal(1), "Synthetic old context, not provider data")
    for field, receipt in (("native_financial_inputs", native), ("reviewed_document_inputs", bound),
                           ("reviewed_ratio_inputs", ratios)):
        slots = {"native_financial_inputs": None, "reviewed_document_inputs": None,
                 "reviewed_ratio_inputs": None, field: receipt}
        old_context = replace(context, fundamentals={"synthetic_old_fact": (older,)}, **slots)
        assert FinancialResearchModule().evaluate(old_context, {}).available_at == as_of
    plan = None
    if malaysia:
        receipt = bound.document()
        annotation = {"native_label": "Synthetic native income", "statement": "income",
            "reporting_scope": "group", "period_start": "2025-01-01", "period_end": "2025-12-31",
            "column_kind": "current", "column_label": "Group 2025", "currency": "MYR",
            "source_unit": "thousand", "source_unit_label": "Synthetic thousand", "pdf_page": "1",
            "printed_page": "1", "restatement_label": "unknown"}
        plan = BankDocumentInputPlan("synthetic", market, symbol, url,
            receipt.get("selected_evidence_id", "f" * 64),
            receipt["captures"][-1]["raw_data_hash"] if receipt["captures"] else "f" * 64,
            receipt.get("review", {}).get("source_document_sha256", "f" * 64), as_of,
            (BankDocumentRequirement("income", "cycle", "monetary", "Synthetic", "native_income",
                                     tuple(sorted(annotation.items()))),
             BankDocumentRequirement("capital", "survival", "ratio_contract_required", "Ratio")))
    monetary_receipt, ratio_receipt = bound.document(), ratios.document()
    arithmetic_plan = RatioArithmeticPlan(
        monetary_receipt.get("selected_evidence_id", "f" * 64),
        (monetary_receipt["captures"][-1]["raw_data_hash"]
         if monetary_receipt["captures"] else "f" * 64),
        ratio_receipt.get("selected_evidence_id", "f" * 64),
        ratio_receipt["captures"][-1]["raw_data_hash"] if ratio_receipt["captures"] else "f" * 64,
        monetary_receipt.get("review", {}).get("source_document_sha256", "f" * 64), as_of,
        (ManualRatioIdentity("native_ratio", "ratio_numerator", "ratio_denominator", 1,
            "half_even", "Synthetic exact equation for report-storage testing only"),))
    for absent in ("reviewed_document_inputs", "reviewed_ratio_inputs"):
        with pytest.raises(ValueError, match="both monetary and ratio receipts"):
            FinancialResearchModule(ratio_arithmetic_plan=arithmetic_plan).evaluate(
                replace(context, **{absent: None}), {})
    run = ResearchEngine(modules=(FinancialResearchModule(bank_document_input_plan=plan,
                                     manual_income_change_pairs=("native_income=prior_income",),
                                     manual_ratio_row_keys=("native_ratio", "unreviewed_lcr"),
                                     ratio_arithmetic_plan=arithmetic_plan),
                                 TechnicalResearchModule()),
                         repository=SQLiteResearchRepository(store)).run(request)
    financial = next(item for item in run.report.assessments
                     if item.module is ResearchModuleName.FINANCIAL)
    technical = next(item for item in run.report.assessments
                     if item.module is ResearchModuleName.TECHNICAL)
    assert technical.features["macd_dif"] is not None
    assert financial.model_version == FINANCIAL_RESEARCH_VERSION
    assert financial.score is None and financial.confidence.confidence == 0
    assert financial.features["reviewed_document_sector_policy"] == "NOT_ADMITTED"
    assert financial.features["native_financial_source_status"] == "missing"
    assert json.loads(financial.features["reviewed_ratio_receipt_json"]) == ratios.document()
    assert financial.features["reviewed_ratio_sector_policy"] == "NOT_ADMITTED"
    assert not financial.features["reviewed_ratio_scoring_authorized"]
    questions = json.loads(financial.features["reviewed_ratio_questions_json"])
    assert questions["questions"][0]["status"] == (
        "DEFINITION_REVIEW_REQUIRED" if state == "observed" else "BLOCKED_INPUT")
    assert questions["questions"][1]["status"] == (
        "MISSING_REVIEWED_ROW" if state == "observed" else "BLOCKED_INPUT")
    arithmetic = json.loads(financial.features["ratio_arithmetic_json"])
    assert arithmetic["checks"][0]["status"] == (
        "ARITHMETIC_AGREES_AS_TRANSCRIBED" if state == "observed" else "BLOCKED_INPUT")
    assert arithmetic["checks"][0]["rounded_percent"] == ("106.7" if state == "observed" else None)
    assert not arithmetic["formula_mapping_verified"]
    assert not arithmetic["issuer_rounding_verified"]
    assert not arithmetic["financial_scoring_authorized"]
    if malaysia:
        coverage = json.loads(financial.features["bank_document_input_json"])
        assert coverage["plan_status"] == "DRAFT_NOT_ADMITTED"
        assert coverage["financial_scoring_authorized"] is False
        assert coverage["status"] == ("INPUT_COVERAGE_ONLY" if state == "observed"
                                      else "SOURCE_INPUT_UNUSABLE")
    receipt = json.loads(financial.features["reviewed_document_receipt_json"])
    assert receipt == bound.document()
    assert receipt["source_bound"] is (state == "observed")
    assert len(receipt["observations"]) == (4 if state == "observed" else 0)
    changes = json.loads(financial.features["manual_income_changes_json"])
    assert changes["comparisons"][0]["change_percent"] == ("25.0000" if state == "observed"
                                                           else None)
    assert not changes["historical_replay_eligible"]
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=as_of)
    assert investment.investment_score is None
    restored = SQLiteHistoricalReplayRepository(store).research_report(instrument, as_of)
    assert restored is not None and restored.assessments == run.report.assessments
    assert InvestmentAssessmentBuilder().build(restored, assessed_at=as_of).investment_score is None
    assert store.table_count("fundamental_facts") == 0


@pytest.mark.parametrize("market,symbol,currency,profile", [
    (Market.US, "MSFT", "USD", "nonfinancial"),
    (Market.HONG_KONG, "0700.HK", "CNY", "securities"),
    (Market.MALAYSIA, "1155.KL", "MYR", "bank"),
    (Market.US, "TEST", "USD", "insurance"),
])
@pytest.mark.parametrize("capture_state", ["observed", "missing", "failed", "tampered"])
def test_native_financials_survive_report_storage_without_score_or_replay_authority(
    tmp_path, market, symbol, currency, profile, capture_state,
):
    # Synthetic admitted queue for contract testing, never a real candidate or source claim.
    as_of = datetime(2026, 10, 27, tzinfo=UTC)
    store = SQLiteStore(tmp_path / "native-research.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    if capture_state != "missing":
        payload = {"timeseries": {"error": None, "result": [
            {"meta": {"symbol": [symbol], "type": [metric]},
             metric: [{"asOfDate": f"{year}-06-30", "periodType": "12M",
                       "currencyCode": currency, "reportedValue": {"raw": value}}
                      for year, value in ((2024, 100), (2025, 120))]}
            for metric in NATIVE_METRICS]}}
        capture = (YahooFundamentalCapture(payload) if capture_state != "failed"
                   else YahooFundamentalCapture(None, "http_403"))
        request = ProviderDatasetRequest(NATIVE_DATASET, market, symbol, as_of,
            {"start_date": "2020-01-01", "end_date": "2026-10-26"})
        service = ProviderNeutralIngestionService(
            store, artifact_store=artifacts, clock=lambda: as_of)
        service.ingest(YahooFundamentalSnapshotAdapter(
            download=lambda _: capture, clock=lambda: as_of), request)
        if capture_state == "tampered":
            next(path for path in artifacts.root.rglob("*") if path.is_file()).write_bytes(b"{}")
    inputs = read_native_financial_research_input(store, artifacts, symbol, market,
                                                 as_of=as_of, sector_profile=profile)
    instrument = Instrument(symbol, market, "Synthetic fixture", available_at=as_of)
    entry = _queue_entry(instrument, as_of)
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic-fixture")
    context = ResearchContext(queue_id, entry, as_of, (), {}, (), native_financial_inputs=inputs)
    request = ResearchRequest(context=context, modules=(ResearchModuleName.FINANCIAL,),
        thesis="Synthetic research fixture", counter_thesis="Missing evidence may refute it",
        invalidation_conditions=(ThesisInvalidationCondition(
            condition_id="fixture", description="Fixture invalidation", metric="revenue",
            operator="<", threshold=0, observation_window="annual", rationale="Fixture only"),))
    run = ResearchEngine(modules=(FinancialResearchModule(),),
                         repository=SQLiteResearchRepository(store)).run(request)
    assessment = run.report.assessments[0]
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=as_of)
    assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert investment.investment_score is None
    features = assessment.features
    assert features["financial_scoring_authorized"] is False
    assert features["native_financial_sector_policy"] == "NOT_ADMITTED"
    assert json.loads(features["native_financial_receipt_json"]) == inputs.document()
    review = json.loads(features["native_financial_review_json"])
    assert review["requested_sector_profile"] == profile
    assert review["historical_replay_eligible"] is False
    if capture_state == "observed":
        assert review["comparisons"][0]["native_change_percent"] == "20.0000"
    else:
        assert all(row["current_value"] is None and row["native_change_percent"] is None
                   for row in review["comparisons"])
        assert features["native_financial_source_status"] != "observed_unqualified"
    restored = SQLiteHistoricalReplayRepository(store).research_report(instrument, as_of)
    assert restored is not None
    assert restored.assessments[0].features == features
    assert restored.status is ResearchRunStatus.INCOMPLETE
    assert InvestmentAssessmentBuilder().build(restored, assessed_at=as_of).investment_score is None
    assert store.table_count("fundamental_facts") == 0


@pytest.mark.parametrize("profile", ["nonfinancial", "bank", "securities", "insurance", "unknown"])
@pytest.mark.parametrize("state", ["observed", "missing", "failed", "tampered", "conflict"])
def test_sec_periods_persist_in_official_report_with_technical_research_but_no_score(
    tmp_path, profile, state,
):
    # Synthetic queue, issuer and prices test contracts, never real screening or source approval.
    captured = datetime(2026, 10, 27, tzinfo=UTC)
    as_of = captured + timedelta(seconds=2)
    store = SQLiteStore(tmp_path / "sec-research.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    cik, accession = "0000789019", "0001193125-25-123456"
    if state != "missing":
        payload = {"cik": 789019, "filings": {"files": [], "recent": {
            "accessionNumber": [accession], "filingDate": ["2025-07-30"],
            "acceptanceDateTime": ["2025-07-30T20:05:12Z"], "reportDate": ["2025-06-30"],
            "form": ["10-K"], "primaryDocument": ["annual.htm"]}}}
        service = ProviderNeutralIngestionService(store, artifact_store=artifacts,
                                                 clock=lambda: captured)
        service.ingest(SECSubmissionsAdapter(download=lambda _: SECSubmissionsCapture(payload),
            clock=lambda: captured), ProviderDatasetRequest(
                "sec_issuer_filings_snapshot", Market.US, cik, captured))
        extra = ('''<ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="c" unitRef="u"
            decimals="0">121</ix:nonFraction>''' if state == "conflict" else "")
        content = f'''<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
          xmlns:xbrli="http://www.xbrl.org/2003/instance"
          xmlns:us-gaap="http://fasb.org/us-gaap/2025"
          xmlns:iso="http://www.xbrl.org/2003/iso4217"><body>
          <xbrli:context id="c"><xbrli:entity><xbrli:identifier
          scheme="http://www.sec.gov/CIK">{cik}</xbrli:identifier></xbrli:entity>
          <xbrli:period><xbrli:startDate>2024-07-01</xbrli:startDate>
          <xbrli:endDate>2025-06-30</xbrli:endDate></xbrli:period></xbrli:context>
          <xbrli:unit id="u"><xbrli:measure>iso:USD</xbrli:measure></xbrli:unit>
          <ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="c" unitRef="u"
          decimals="0">120</ix:nonFraction>{extra}</body></html>'''.encode()
        body_at = captured + timedelta(seconds=1)
        capture = SECBodyCapture(None, "http_403") if state == "failed" else SECBodyCapture(content)
        body_request = build_sec_body_request(store, artifacts, cik, accession, as_of=body_at)
        body_service = ProviderNeutralIngestionService(store, artifact_store=artifacts,
                                                       clock=lambda: body_at)
        body_service.ingest(
            SECBodyAdapter(download=lambda _: capture, clock=lambda: body_at), body_request)
        if state == "tampered":
            with store._connect() as connection:
                digest = connection.execute("SELECT raw_data_hash FROM provider_evidence_records "
                    "WHERE dataset='sec_primary_filing_body_snapshot'").fetchone()[0]
            (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"{}")
    inputs = read_sec_period_research_input(store, artifacts, cik, accession, symbol="TEST",
        as_of=as_of, selections=(SECPeriodSelection("NetIncomeLoss", date(2024, 7, 1),
                                                   date(2025, 6, 30)),), sector_profile=profile)
    instrument = Instrument("TEST", Market.US, "Synthetic only", available_at=captured)
    entry = _queue_entry(instrument, as_of)
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic-fixture")
    bars = tuple(Bar(instrument, captured - timedelta(days=100 - index),
        captured - timedelta(days=100 - index), Decimal(10 + index), Decimal(12 + index),
        Decimal(9 + index), Decimal(11 + index), Decimal(10000)) for index in range(100))
    native = read_native_financial_research_input(store, artifacts, "TEST", Market.US,
                                                 as_of=as_of, sector_profile=profile)
    context = ResearchContext(queue_id, entry, as_of, bars, {}, (),
                              native_financial_inputs=native, sec_period_inputs=inputs)
    request = ResearchRequest(context,
        (ResearchModuleName.FINANCIAL, ResearchModuleName.TECHNICAL),
        "Synthetic thesis", "Incomplete source definitions may refute the thesis",
        (ThesisInvalidationCondition("fixture", "Fixture invalidation", "NetIncomeLoss", "<", 0,
                                     "explicit period", "Synthetic only"),))
    result = ResearchEngine(modules=(FinancialResearchModule(), TechnicalResearchModule()),
                            repository=SQLiteResearchRepository(store)).run(request)
    financial = next(item for item in result.report.assessments
                     if item.module is ResearchModuleName.FINANCIAL)
    assert financial.available_at == as_of and financial.score is None
    assert financial.confidence.confidence == 0
    assert financial.model_version == FINANCIAL_RESEARCH_VERSION
    assert financial.features["sec_period_binding_hash"] == inputs.binding_hash
    assert json.loads(financial.features["sec_period_receipt_json"]) == inputs.document()
    assert financial.features["sec_period_requested_symbol"] == "TEST"
    assert financial.features["sec_period_requested_sector"] == profile
    assert financial.features["sec_period_sector_policy"] == "NOT_ADMITTED"
    assert financial.features["sec_period_issuer_to_instrument_verified"] is False
    assert financial.features["sec_period_scoring_authorized"] is False
    assert financial.features["native_financial_source_status"] == "missing"
    check = inputs.document()["checks"][0]
    if state == "observed":
        assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    elif state == "conflict":
        assert check["status"] == "NUMERIC_CONFLICT"
    else:
        assert check["status"] == "SOURCE_UNAVAILABLE"
    assert result.report.status is ResearchRunStatus.INCOMPLETE
    restored = SQLiteHistoricalReplayRepository(store).research_report(instrument, as_of)
    assert restored is not None
    assert restored.assessments == result.report.assessments
    assessment = InvestmentAssessmentBuilder().build(restored, assessed_at=as_of)
    assert assessment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert assessment.investment_score is None
    assert store.table_count("fundamental_facts") == 0


def test_nonfinancial_input_checklist_persists_without_admitting_scoring_or_conditions(tmp_path):
    as_of = datetime(2026, 10, 27, tzinfo=UTC)
    instrument = Instrument("002624", Market.CHINA_A, "Synthetic nonfinancial fixture",
                            available_at=as_of, source="synthetic")
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "nonfinancial-inputs.sqlite3")
    store.initialize()
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic")
    fact = FundamentalFact(instrument, "revenue", date(2026, 6, 30), as_of, as_of,
        Decimal(100), "Synthetic only", period_start=date(2026, 1, 1),
        unit="absolute", currency="CNY")
    inspection = FinancialFactInspection(
        fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic structural receipt only",),
        reporting_scope="group", sector_profile="nonfinancial", evidence_id="a" * 64,
        review_artifact_id="b" * 64, filing_artifact_id="c" * 64, filing_sha256="d" * 64,
        source_pages=(1,), source_unit="CNY", source_column="group_current_period",
        audit_status="unaudited", statement="income", filing_period_end=fact.period_end)
    snapshot = FinancialInputSnapshot(instrument.symbol, instrument.market, as_of, ("revenue",),
                                      "nonfinancial", "group", (inspection,))
    request = ResearchRequest(
        context=ResearchContext(queue_id, entry, as_of, (), {"revenue": (fact,)}, (),
                                financial_inputs=snapshot),
        modules=(ResearchModuleName.FINANCIAL, ResearchModuleName.TECHNICAL),
        condition_style="long_term_confirmation", thesis="Synthetic research hypothesis",
        counter_thesis="Missing inputs and source qualification can invalidate it",
        invalidation_conditions=(ThesisInvalidationCondition(
            "fixture", "Revenue changes", "revenue", "<", 0, "annual", "Synthetic only"),))
    run = ResearchEngine(modules=(
        FinancialResearchModule(nonfinancial_input_policy=NonfinancialInputPolicy(90)),
        TechnicalResearchModule()), repository=SQLiteResearchRepository(store)).run(request)
    rows = store.research_assessments_for_report(run.report.report_id)
    financial = next(row for row in rows if row["module"] == "financial")
    features = json.loads(financial["features_json"])
    checklist = json.loads(features["nonfinancial_input_assessment_json"])
    row = next(item for item in checklist["checks"] if item["metric"] == "revenue")
    assert row["status"] == "observed_unqualified" and row["freshness"] == "stale"
    assert checklist["assessment_hash"] == features["nonfinancial_input_assessment_hash"]
    assert checklist["input_hash"] == snapshot.input_hash
    assert not features["financial_scoring_authorized"] and financial["score"] is None
    assert run.report.status.value == "incomplete"
    assert features["condition_review_state"] == "DATA_BLOCKED"
    assessment = InvestmentAssessmentBuilder().build(
        run.report, assessed_at=run.report.available_at)
    assert assessment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert assessment.investment_score is None


@pytest.mark.parametrize("kind", ["bar_available", "fact_available", "evidence", "queue",
                                   "financial_snapshot_cutoff"])
def test_future_fold_or_snapshot_cutoff_rejected_before_starting_persisted_research(tmp_path, kind):
    as_of = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    later = as_of.replace(fold=1)
    instrument = Instrument("TEST", Market.US, "Synthetic DST fixture",
                            available_at=as_of - timedelta(days=1), source="synthetic")
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "utc-research.sqlite3")
    store.initialize()
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic",
    )
    context = ResearchContext(queue_id, entry, as_of, (), {}, ())
    if kind == "bar_available":
        bar = Bar(instrument, as_of - timedelta(days=1), later,
                  Decimal(10), Decimal(11), Decimal(9), Decimal(10), Decimal(100),
                  source="synthetic")
        object.__setattr__(context, "bars", (bar,))
    elif kind == "fact_available":
        context.fundamentals["revenue"] = (FundamentalFact(
            instrument, "revenue", date(2026, 9, 30), as_of - timedelta(days=1), later,
            Decimal(100), "synthetic"),)
    elif kind == "evidence":
        object.__setattr__(context, "evidence", (ResearchEvidence(
            "synthetic-fold", ResearchModuleName.FINANCIAL, "fixture", 99, as_of, later,
            "synthetic", EvidenceQuality.PRIMARY),))
    elif kind == "financial_snapshot_cutoff":
        fact = FundamentalFact(instrument, "revenue", date(2026, 9, 30),
            as_of - timedelta(days=1), as_of, Decimal(100), "synthetic")
        snapshot = FinancialInputSnapshot(instrument.symbol, instrument.market, later,
            ("revenue",), "unknown", "group", (FinancialFactInspection(
                fact, FinancialBindingStatus.UNSUPPORTED, ("Synthetic unverified source",)),))
        context.fundamentals["revenue"] = (fact,)
        object.__setattr__(context, "financial_inputs", snapshot)
    else:
        object.__setattr__(entry.research_score, "calculated_at", later)
    request = ResearchRequest(
        context=context, modules=(ResearchModuleName.FINANCIAL,),
        thesis="Synthetic DST hypothesis", counter_thesis="Future evidence must be excluded",
        invalidation_conditions=(ThesisInvalidationCondition(
            "fixture", "Visible inputs change", "fixture", "<", 0, "next input", "test"),),
    )
    engine = ResearchEngine(modules=(FinancialResearchModule(),),
                            repository=SQLiteResearchRepository(store))
    with pytest.raises(ValueError, match="future|snapshot does not match"):
        engine.run(request)
    for table in ("research_runs", "research_reports", "research_assessments",
                  "research_evidence", "signals"):
        assert store.table_count(table) == 0
    assert len(store.research_queue(status=entry.status)) == 1


@pytest.mark.parametrize("condition_style", [None, "long_term_confirmation", "improved_turtle"])
def test_cached_module_cutoff_failure_retains_run_without_publishing_report_or_signal(
    tmp_path, monkeypatch, condition_style,
):
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = Instrument("000063", Market.CHINA_A, "Synthetic clock fixture",
                            available_at=as_of, source="synthetic")
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "cutoff.sqlite3")
    store.initialize()
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic",
    )
    request = ResearchRequest(
        context=ResearchContext(queue_id, entry, as_of, (), {}, ()),
        modules=(ResearchModuleName.TECHNICAL,), condition_style=condition_style,
        thesis="Synthetic temporal hypothesis", counter_thesis="Cached assessment is obsolete",
        invalidation_conditions=(ThesisInvalidationCondition(
            "clock", "Input period changes", "fixture", "<", 0, "next observation", "test"),),
    )
    original = TechnicalResearchModule.evaluate

    def cached(self, context, dependencies):
        assessment = original(self, context, dependencies)
        previous = context.as_of - timedelta(days=1)
        return replace(assessment, evaluated_at=previous, available_at=previous)

    monkeypatch.setattr(TechnicalResearchModule, "evaluate", cached)
    engine = ResearchEngine(modules=(TechnicalResearchModule(),),
                            repository=SQLiteResearchRepository(store))
    with pytest.raises(ValueError, match="share the request decision cutoff"):
        engine.run(request)
    assert store.table_count("research_runs") == 1
    assert store.table_count("research_reports") == store.table_count("research_assessments") == 0
    assert store.table_count("research_evidence") == store.table_count("signals") == 0
    with store._connect() as connection:
        row = connection.execute("SELECT status, failure_reason FROM research_runs").fetchone()
    assert row["status"] == "failed" and "decision cutoff" in row["failure_reason"]
    assert len(store.research_queue(status=entry.status)) == 1


@pytest.mark.parametrize("condition_style", [None, "long_term_confirmation"])
@pytest.mark.parametrize("latest_suspended", [False, True])
def test_technical_diagnostics_survive_official_report_persistence(
    tmp_path: Path, condition_style: str | None, latest_suspended: bool,
) -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = Instrument("000063", Market.CHINA_A, "Synthetic fixture",
                            available_at=as_of, source="synthetic")
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "technical.sqlite3")
    store.initialize()
    store.upsert_instruments([instrument])
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="fixture",
    )
    bars = tuple(Bar(
        instrument=instrument, timestamp=as_of - timedelta(days=260 - index),
        available_at=as_of - timedelta(days=260 - index),
        open=Decimal(10) + Decimal(index) / 10,
        close=Decimal(10) + Decimal(index) / 10,
        high=Decimal("10.1") + Decimal(index) / 10,
        low=Decimal("9.9") + Decimal(index) / 10,
        volume=Decimal(1000), source="synthetic",
    ) for index in range(260))
    if latest_suspended:
        bars = (*bars, replace(bars[-1], is_suspended=True,
                                available_at=bars[-1].available_at + timedelta(hours=1)))
    request = ResearchRequest(
        context=ResearchContext(queue_id, entry, as_of, bars, {}, ()),
        modules=(ResearchModuleName.TECHNICAL,),
        thesis="Synthetic technical relationship, not an issuer recommendation",
        counter_thesis="Price transformations can fail",
        condition_style=condition_style,
        invalidation_conditions=(ThesisInvalidationCondition(
            "fixture", "Relationship fails", "close", "<", 1, "next observation", "test"),),
    )
    run = ResearchEngine(modules=(TechnicalResearchModule(),),
                         repository=SQLiteResearchRepository(store)).run(request)
    stored = store.research_assessments_for_report(run.report.report_id)
    features = json.loads(stored[0]["features_json"])
    assert features == run.report.assessments[0].features
    if latest_suspended:
        assert features["technical_input_status"] == "SUSPENDED_LATEST"
        assert features["technical_confluence"] == "INSUFFICIENT_DATA"
        assert features["macd_dif"] is features["kdj_k"] is None
        assert run.report.assessments[0].score is None
        assert run.report.status is ResearchRunStatus.INCOMPLETE
        investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=as_of)
        assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
        assert investment.investment_score is None
    else:
        assert features["macd_dif"] is not None and features["kdj_k"] is not None
    assert len(features["technical_input_hash"]) == 64
    assert features["technical_scoring_admitted"] is False
    if condition_style is not None:
        assert features["condition_review_state"] == "DATA_BLOCKED"
        assert run.report.status is ResearchRunStatus.INCOMPLETE
        document = json.loads(features["condition_review_json"])
        assert document["execution_authorized"] is False
        assert document["symbol"] == "000063"
        assert document["thesis"] == request.thesis
    assert store.table_count("research_reports") == 1


@pytest.mark.parametrize("partial", [False, True])
def test_research_queue_to_report_persistence(tmp_path: Path, partial: bool) -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = Instrument(
        "600000",
        Market.CHINA_A,
        "Example",
        available_at=as_of,
        source="test",
    )
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "research.sqlite3")
    store.initialize()
    store.upsert_instruments([instrument])
    queue_id = store.save_research_queue_entry(
        instrument=instrument,
        discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of,
        admitted_at=as_of,
        priority_score=entry.priority_score,
        urgency_score=entry.urgency_score,
        confidence_score=entry.confidence_score,
        research_score=entry.research_score.score,
        status=entry.status,
        thesis=entry.candidate.thesis,
        evidence=entry.candidate.evidence,
        assigned_to=None,
        model_version="v0.4",
    )
    evidence = tuple(
        _policy_evidence(name, as_of)
        for name in (
            "regulatory_environment",
            "industrial_policy",
            "fiscal_policy",
            "monetary_policy",
            "geopolitical_factors",
        )
    )
    if partial:
        evidence = (*evidence[:-1], _policy_evidence("unrelated_numeric_annotation", as_of))
    request = ResearchRequest(
        context=ResearchContext(
            queue_id=queue_id,
            queue_entry=entry,
            as_of=as_of,
            bars=(),
            fundamentals={},
            evidence=evidence,
        ),
        modules=(ResearchModuleName.POLICY,),
        thesis="Policy support may improve demand",
        counter_thesis="Policy transmission may be weak",
        invalidation_conditions=(
            ThesisInvalidationCondition(
                condition_id="industry-growth",
                description="Industry growth falls below zero",
                metric="industry_growth",
                operator="<",
                threshold=0,
                observation_window="two quarters",
                rationale="The thesis depends on industry expansion",
            ),
        ),
        researcher="integration-test",
    )
    engine = ResearchEngine(
        modules=(PolicyResearchModule(),),
        repository=SQLiteResearchRepository(store),
    )

    run = engine.run(request)

    assert store.table_count("research_runs") == 1
    assert store.table_count("research_evidence") == 5
    assert store.table_count("research_assessments") == 1
    assert store.table_count("research_reports") == 1
    assert store.table_count("signals") == 1
    assert len(store.research_queue(status=entry.status)) == 0
    assert run.report.policy_assessment is not None
    expected_status = ResearchRunStatus.INCOMPLETE if partial else ResearchRunStatus.COMPLETED
    assert run.report.status is expected_status
    if partial:
        assessment = run.report.policy_assessment.assessment
        assert assessment.score is None and assessment.confidence.confidence == 0
        assert assessment.evidence_ids == tuple(item.evidence_id for item in evidence)
        stored = store.research_assessments_for_report(run.report.report_id)
        assert stored[0]["score"] is None
        assert json.loads(stored[0]["features_json"])["ignored_evidence_names"] == (
            "unrelated_numeric_annotation")
        investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=as_of)
        assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
        assert investment.investment_score is None

    with pytest.raises(ValueError, match="already claimed"):
        engine.run(request)


@pytest.mark.parametrize("evidence_only", [False, True])
def test_financial_input_integrity_through_database_and_report_persistence(
    tmp_path: Path, evidence_only: bool,
) -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = Instrument("600000", Market.CHINA_A, "fixture", available_at=as_of)
    entry = _queue_entry(instrument, as_of)
    store = SQLiteStore(tmp_path / "financial-research.sqlite3")
    store.initialize()
    store.upsert_instruments([instrument])
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="fixture",
    )
    fact = FundamentalFact(
        instrument=instrument, metric="revenue", period_end=date(2025, 9, 30),
        published_at=as_of - timedelta(days=10),
        available_at=as_of - timedelta(days=9), value=Decimal("100"), source="fixture",
    )
    restated = replace(
        fact, revision=1, value=Decimal("90"), available_at=as_of - timedelta(days=8),
    )
    store.upsert_fundamental_facts([fact, restated])
    history = store.fundamental_revision_history(
        "600000", Market.CHINA_A, AssetType.EQUITY, "revenue", as_of=as_of,
    )
    context = ResearchContext(
        queue_id=queue_id, queue_entry=entry, as_of=as_of,
        bars=(), fundamentals={"revenue": tuple(reversed(history))}, evidence=(),
    )
    request = ResearchRequest(
        context=context, modules=(ResearchModuleName.FINANCIAL,),
        thesis="Research fixture", counter_thesis="The evidence may be insufficient",
        invalidation_conditions=(ThesisInvalidationCondition(
            condition_id="fixture", description="Fixture invalidation", metric="revenue",
            operator="<", threshold=0, observation_window="annual", rationale="Fixture only",
        ),),
    )
    engine = ResearchEngine(
        modules=(FinancialResearchModule(),), repository=SQLiteResearchRepository(store),
    )
    context.fundamentals["profit"] = (fact,)
    with pytest.raises(ValueError, match="fundamental metric mismatch"):
        engine.run(request)
    assert store.table_count("research_runs") == 0
    assert store.table_count("research_reports") == 0
    assert store.table_count("signals") == 0
    del context.fundamentals["profit"]
    if evidence_only:
        context = replace(context, fundamentals={}, evidence=(ResearchEvidence(
            evidence_id="unqualified-financial-score", module=ResearchModuleName.FINANCIAL,
            name="unrelated_numeric_annotation", value=99, observed_at=as_of,
            available_at=as_of, source="synthetic annotation", quality=EvidenceQuality.PRIMARY,
        ),))
        request = replace(request, context=context)

    run = engine.run(request)
    rows = store.research_assessments_for_report(run.report.report_id)
    assert len(rows) == 1
    assert rows[0]["model_version"] == FINANCIAL_RESEARCH_VERSION
    assert rows[0]["score"] is None
    features = json.loads(rows[0]["features_json"])
    assert features["financial_scoring_authorized"] is False
    assert features["financial_input_binding_present"] is False
    if evidence_only:
        assert "latest_revenue" not in features
        assert json.loads(rows[0]["evidence_ids_json"]) == ["unqualified-financial-score"]
    else:
        assert features["latest_revenue"] == "90"
    assert run.report.status.value == "incomplete"
    assert store.table_count("fundamental_facts") == 2


def test_market_value_evidence_reaches_persisted_report_without_admitting_scoring(tmp_path):
    as_of = datetime(2026, 10, 23, 8, tzinfo=UTC)
    quote_at = as_of - timedelta(hours=1)
    instrument = Instrument("000063", Market.CHINA_A, "Synthetic receipt fixture",
                            available_at=quote_at, source="synthetic")
    store = SQLiteStore(tmp_path / "market-value-research.sqlite3")
    store.initialize()
    store.upsert_instruments((instrument,))
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    body = json.dumps({"rc": 0, "data": {
        "f57": instrument.symbol, "f43": 20, "f84": 20000, "f85": 10000,
        "f116": 400000, "f117": 200000, "f86": int(quote_at.timestamp()),
    }}).encode()
    adapter = EastmoneyMarketValueAdapter(
        download=lambda _: QuoteHttpCapture(200, body), clock=lambda: as_of)
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: as_of).ingest(
        adapter, ProviderDatasetRequest(
            MARKET_VALUE_DATASET, Market.CHINA_A, instrument.symbol, as_of))
    receipt = MarketValueInputReader(store, artifacts).read(
        instrument.symbol, instrument.market, as_of=as_of)
    (inspection,) = receipt.inspections
    assert inspection.source_bound
    entry = _queue_entry(instrument, as_of)
    queue_id = store.save_research_queue_entry(
        instrument=instrument, discovery_source=entry.candidate.discovery_source,
        discovered_at=as_of, admitted_at=as_of, priority_score=entry.priority_score,
        urgency_score=entry.urgency_score, confidence_score=entry.confidence_score,
        research_score=entry.research_score.score, status=entry.status,
        thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic",
    )
    bar = Bar(instrument, quote_at, quote_at, Decimal("20"), Decimal("21"),
              Decimal("19"), Decimal("20"), Decimal("100"), source="synthetic")
    context = ResearchContext(queue_id, entry, as_of, (bar,), {}, (),
                              market_value_inputs=receipt)
    request = ResearchRequest(
        context=context, modules=(ResearchModuleName.FINANCIAL,),
        thesis="Synthetic source binding, not issuer research",
        counter_thesis="Matching quotes do not qualify source truth",
        invalidation_conditions=(ThesisInvalidationCondition(
            "fixture", "Source input changes", "fixture", "<", 0, "next input", "test"),),
    )
    policy = MarketValueMatchingPolicy(3600, 60, 3600)
    engine = ResearchEngine(modules=(FinancialResearchModule(market_value_policy=policy),),
                            repository=SQLiteResearchRepository(store))
    inspection.record.payload["price"] = "999"
    with pytest.raises(ValueError, match="receipt mismatch"):
        engine.run(request)
    assert store.table_count("research_runs") == store.table_count("research_reports") == 0
    assert store.table_count("signals") == 0
    assert len(store.research_queue(status=entry.status)) == 1
    inspection.record.payload["price"] = "20"

    run = engine.run(request)
    (row,) = store.research_assessments_for_report(run.report.report_id)
    features = json.loads(row["features_json"])
    assert features == run.report.assessments[0].features
    assert features["market_value_input_hash"] == receipt.input_hash
    assert features["market_value_policy_hash"] == policy.policy_hash
    assert features["market_value_evidence_id"] == inspection.record.evidence_id
    diagnostic = json.loads(features["market_value_matching_json"])
    assert diagnostic["diagnostic_hash"] == features["market_value_diagnostic_hash"]
    assert diagnostic["bar_input_hash"] == features["market_value_bar_input_hash"]
    assert diagnostic["matching_policy"]["max_quote_age_seconds"] == 3600
    assert diagnostic["quote_age_microseconds"] == 3600000000
    assert diagnostic["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert diagnostic["reasons"] and diagnostic["trust_level"] == "low"
    assert diagnostic["valuation_multiple"] is None
    assert not diagnostic["valuation_authorized"] and not diagnostic["validation_authorized"]
    assert row["score"] is None and run.report.assessments[0].confidence.confidence == 0
    assert not features["financial_scoring_authorized"]
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=as_of)
    assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert investment.investment_score is None


def _queue_entry(instrument: Instrument, as_of: datetime) -> ResearchQueueEntry:
    candidate = OpportunityCandidate(
        instrument=instrument,
        discovery_source="discovery.policy",
        discovered_at=as_of,
        available_at=as_of,
        thesis="Policy opportunity",
        evidence=("Policy publication",),
        urgency_score=70,
        confidence_score=75,
    )
    component = ScoreComponent(
        name="policy",
        score=70,
        confidence=80,
        weight=1,
        contribution=70,
        reasons=("Policy evidence",),
    )
    score = CompositeScore(
        score_type=ScoreType.RESEARCH,
        score=70,
        confidence=80,
        calculated_at=as_of,
        components=(component,),
        reasons=("Research priority",),
        model_version="v0.4",
    )
    hard_screen = HardScreenResult(
        rule_id="data_quality",
        passed=True,
        evaluated_at=as_of,
        available_at=as_of,
        reasons=("Data passed",),
    )
    return ResearchQueueEntry(
        candidate=candidate,
        admitted_at=as_of,
        priority_score=72,
        urgency_score=70,
        confidence_score=75,
        research_score=score,
        hard_screen_results=(hard_screen,),
    )


def _policy_evidence(name: str, as_of: datetime) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=f"policy:{name}",
        module=ResearchModuleName.POLICY,
        name=name,
        value=70,
        observed_at=as_of,
        available_at=as_of,
        source="test",
        quality=EvidenceQuality.PRIMARY,
        metadata={"summary": f"{name} summary"},
    )


@pytest.fixture
def thesis_report_case(tmp_path):
    from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel

    cutoff = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    instrument = Instrument("TEST", Market.US, "Synthetic", currency="USD",
                            available_at=cutoff, source="synthetic")
    entry = _queue_entry(instrument, cutoff)
    store = SQLiteStore(tmp_path / "thesis-binding.sqlite3")
    store.initialize()
    store.upsert_instruments((instrument,))
    queue_id = store.save_research_queue_entry(instrument=instrument,
        discovery_source=entry.candidate.discovery_source, discovered_at=cutoff,
        admitted_at=cutoff, priority_score=entry.priority_score, urgency_score=entry.urgency_score,
        confidence_score=entry.confidence_score, research_score=entry.research_score.score,
        status=entry.status, thesis=entry.candidate.thesis, evidence=entry.candidate.evidence,
        assigned_to=None, model_version="synthetic")
    evidence = tuple(_policy_evidence(name, cutoff) for name in (
        "regulatory_environment", "industrial_policy", "fiscal_policy",
        "monetary_policy", "geopolitical_factors"))
    condition = ThesisInvalidationCondition("H1", "Synthetic condition", "fixture", "<", 0,
                                           "legacy text", "Synthetic, not an approved rule")
    request = ResearchRequest(ResearchContext(queue_id, entry, cutoff, (), {}, evidence),
        (ResearchModuleName.POLICY,), "Synthetic thesis", "Synthetic counter thesis", (condition,))
    metric = ThesisMetricBinding(screening_instrument_id(instrument), "fixture", "SyntheticTag",
        "synthetic-gaap", "synthetic-v1", "group", "nonfinancial", "ratio", "dimensionless")
    period = ThesisPeriod(date(2026, 7, 1), date(2026, 9, 30))
    reference = ThesisEvidenceReference(metric, period, "synthetic-reference", "synthetic-batch",
        "synthetic", "synthetic-document", "a" * 64, "b" * 64, "original",
        cutoff - timedelta(days=1), cutoff, DataTrustLevel.HIGH,
        AvailabilityPrecision.RETRIEVAL_TIME)
    plan = ThesisReportBindingPlan(queue_id, metric.instrument_id, cutoff,
        (ThesisConditionBinding(condition, metric, (period,), (reference,)),))
    return store, request, plan


def _thesis_policy_output(request):
    return PolicyResearchModule().evaluate(request.context, {})


def test_omitted_thesis_plan_preserves_legacy_fields_with_versioned_admission(
    thesis_report_case, monkeypatch
):
    from hashlib import sha256

    from tong_quant.research.repository import _jsonable

    _, request, _ = thesis_report_case
    request = replace(request, context=replace(request.context, queue_id="synthetic-fixed-queue"))
    monkeypatch.setattr("tong_quant.research.reporting.uuid4", lambda: "synthetic-report-id")
    policy = _thesis_policy_output(request)
    default = DefaultResearchReportBuilder().build(request, (policy.assessment,), policy)
    explicit = DefaultResearchReportBuilder(thesis_binding_plan=None).build(
        request, (policy.assessment,), policy)
    from dataclasses import asdict

    assert json.dumps(_jsonable(asdict(default)), sort_keys=True) == json.dumps(
        _jsonable(asdict(explicit)), sort_keys=True)
    # Test-only projection: preserve every old field while recognizing prospective UTC admission.
    legacy_projection = replace(default, model_version="research-report-v0.5.2-utc-inputs")
    body = json.dumps(_jsonable(asdict(legacy_projection)), sort_keys=True, separators=(",", ":"))
    assert sha256(body.encode()).hexdigest() == (
        "eded82f130d832f4ed568550a5b2caf0f2d3dcd0ed61d054d07bc731bdf28112")
    assert default.model_version == RESEARCH_REPORT_VERSION
    assert default.status is ResearchRunStatus.COMPLETED
    assert not any(name.startswith("thesis_binding_") for name in default.assessments[0].features)


@pytest.mark.parametrize("style", [None, "long_term_confirmation", "improved_turtle"])
def test_thesis_declarations_round_trip_in_official_report_but_block_score(
    thesis_report_case, style,
):
    store, request, plan = thesis_report_case
    request = replace(request, condition_style=style)
    before = _thesis_policy_output(request).assessment
    run = ResearchEngine(modules=(PolicyResearchModule(),),
        report_builder=DefaultResearchReportBuilder(thesis_binding_plan=plan),
        repository=SQLiteResearchRepository(store)).run(request)
    assert run.report.model_version == RESEARCH_THESIS_REPORT_VERSION
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    assert run.report.policy_assessment.assessment == run.report.assessments[0]
    assessment = run.report.assessments[0]
    assert assessment.score == before.score and assessment.confidence == before.confidence
    features = assessment.features
    body = json.loads(features["thesis_binding_json"])
    assert body["conditions"][0]["binding_status"] == "DECLARED_ONLY"
    assert body["evaluation"] == "NOT_EVALUATED"
    assert body["source_qualification"] == "NOT_ADMITTED"
    assert body["holding_horizon"] == "NOT_ESTIMATED"
    assert all(value is False for key, value in body.items() if key.endswith("_authorized"))
    from hashlib import sha256

    assert features["thesis_binding_hash"] == sha256(
        features["thesis_binding_json"].encode()).hexdigest()
    restored = SQLiteHistoricalReplayRepository(store).research_report(
        request.context.queue_entry.candidate.instrument, request.context.as_of)
    assert restored == run.report
    original_bytes = store.path.read_bytes()
    assert SQLiteHistoricalReplayRepository(store).research_report(
        request.context.queue_entry.candidate.instrument, request.context.as_of) == restored
    assert store.path.read_bytes() == original_bytes
    investment = InvestmentAssessmentBuilder().build(restored, assessed_at=request.context.as_of)
    assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert investment.investment_score is None
    assert run.signal.action.value == "research" and run.signal.features["informational_only"]
    assert store.table_count("fundamental_facts") == 0


def test_missing_thesis_sources_are_persisted_as_missing_not_success(thesis_report_case):
    store, request, plan = thesis_report_case
    plan = replace(plan, conditions=(replace(plan.conditions[0], evidence=()),))
    report = ResearchEngine(modules=(PolicyResearchModule(),),
        report_builder=DefaultResearchReportBuilder(thesis_binding_plan=plan),
        repository=SQLiteResearchRepository(store)).run(request).report
    body = json.loads(report.assessments[0].features["thesis_binding_json"])
    assert body["conditions"][0]["missing_period_bindings"]
    assert body["conditions"][0]["binding_status"] == "INCOMPLETE_OR_CONFLICTED"
    assert report.status is ResearchRunStatus.INCOMPLETE
    assert SQLiteHistoricalReplayRepository(store).research_report(
        request.context.queue_entry.candidate.instrument, request.context.as_of) == report


@pytest.mark.parametrize("defect", ["queue", "instrument", "cutoff_fold", "condition",
    "unknown_condition", "duplicate_condition", "missing_condition", "metric_instrument",
    "future_available", "future_period"])
def test_invalid_or_future_thesis_plans_publish_no_report_or_signal(thesis_report_case, defect):
    store, request, plan = thesis_report_case
    declaration = plan.conditions[0]
    if defect == "queue":
        plan = replace(plan, queue_id="another-queue")
    elif defect == "instrument":
        plan = replace(plan, instrument_id="us:equity:OTHER")
    elif defect == "cutoff_fold":
        plan = replace(plan, decision_as_of=datetime(2026, 11, 1, 1, 30,
            tzinfo=ZoneInfo("America/New_York"), fold=0))
    elif defect == "condition":
        plan = replace(plan, conditions=(replace(declaration,
            condition=replace(declaration.condition, threshold=1)),))
    elif defect == "unknown_condition":
        plan = replace(plan, conditions=(replace(declaration,
            condition=replace(declaration.condition, condition_id="unknown")),))
    elif defect == "duplicate_condition":
        plan = replace(plan, conditions=(declaration, declaration))
    elif defect == "missing_condition":
        request = replace(request, invalidation_conditions=(declaration.condition,
            replace(declaration.condition, condition_id="H2")))
    elif defect == "metric_instrument":
        plan = replace(plan, conditions=(replace(declaration,
            metric=replace(declaration.metric, instrument_id="us:equity:OTHER")),))
    else:
        reference = declaration.evidence[0]
        reference = replace(reference, **(
            {"available_at": request.context.as_of + timedelta(seconds=1)}
            if defect == "future_available" else {"period": ThesisPeriod(None, date(2027, 1, 1))}))
        plan = replace(plan, conditions=(replace(declaration, evidence=(reference,)),))
    with pytest.raises(ValueError):
        ResearchEngine(modules=(PolicyResearchModule(),),
            report_builder=DefaultResearchReportBuilder(thesis_binding_plan=plan),
            repository=SQLiteResearchRepository(store)).run(request)
    assert store.table_count("research_reports") == store.table_count("signals") == 0


def test_thesis_report_binding_hash_orders_conditions_and_normalizes_utc(thesis_report_case):
    _, request, plan = thesis_report_case
    second = replace(plan.conditions[0], condition=replace(plan.conditions[0].condition,
                                                         condition_id="H2"))
    request = replace(request, invalidation_conditions=(second.condition,
                                                       plan.conditions[0].condition))
    forward = replace(plan, conditions=(*plan.conditions, second))
    reversed_plan = replace(forward, conditions=tuple(reversed(forward.conditions)),
        decision_as_of=plan.decision_as_of.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert thesis_report_binding_features(forward, request) == thesis_report_binding_features(
        reversed_plan, request)


def test_thesis_binding_rejects_preannotated_assessments_and_custom_version(thesis_report_case):
    _, request, plan = thesis_report_case
    policy = _thesis_policy_output(request)
    annotated = replace(policy.assessment, features={**policy.assessment.features,
                                                    "thesis_binding_evaluation": "SUCCESS"})
    with pytest.raises(ValueError, match="unannotated"):
        DefaultResearchReportBuilder(thesis_binding_plan=plan).build(request, (annotated,), None)
    with pytest.raises(ValueError, match="unannotated"):
        DefaultResearchReportBuilder(thesis_binding_plan=plan).build(
            request, (policy.assessment,), replace(policy, assessment=annotated))
    with pytest.raises(ValueError, match="version"):
        DefaultResearchReportBuilder(model_version="legacy", thesis_binding_plan=plan)
    with pytest.raises(ValueError, match="module assessments"):
        DefaultResearchReportBuilder(thesis_binding_plan=plan).build(request, (), None)


def test_thesis_binding_rejects_duplicate_request_conditions(thesis_report_case):
    _, request, plan = thesis_report_case
    request = replace(request, invalidation_conditions=request.invalidation_conditions * 2)
    with pytest.raises(ValueError, match="duplicate request"):
        thesis_report_binding_features(plan, request)


@pytest.mark.parametrize("conditions", [(), [], ("not-a-binding",)])
def test_untyped_or_empty_thesis_report_plans_are_not_opt_out(thesis_report_case, conditions):
    _, _, plan = thesis_report_case
    with pytest.raises(ValueError, match="bounded typed"):
        replace(plan, conditions=conditions)


def test_thesis_report_rejects_reference_overflow_and_malformed_declarations(thesis_report_case):
    _, request, plan = thesis_report_case
    first = plan.conditions[0]
    second = replace(first, condition=replace(first.condition, condition_id="H2"))
    request = replace(request, invalidation_conditions=(first.condition, second.condition))
    refs = tuple(replace(first.evidence[0], evidence_id=f"synthetic-{index}")
                 for index in range(65))
    over = replace(plan, conditions=(replace(first, evidence=refs), replace(second, evidence=refs)))
    with pytest.raises(ValueError, match="reference bound"):
        thesis_report_binding_features(over, request)
    malformed = replace(plan, conditions=(replace(first, metric="not-typed"),))
    with pytest.raises(ValueError, match="typed condition and metric"):
        thesis_report_binding_features(malformed, request)
