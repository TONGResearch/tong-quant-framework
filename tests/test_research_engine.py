import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import permutations
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.data.market_value_inputs import (
    MarketValueInputSnapshot,
    MarketValueInspection,
    market_value_record_hash,
)
from tong_quant.data.native_financial_inputs import read_native_financial_research_input
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.eastmoney_market_values import (
    DATASET as MARKET_VALUE_DATASET,
)
from tong_quant.data.providers.eastmoney_market_values import (
    EastmoneyMarketValueAdapter,
    QuoteHttpCapture,
)
from tong_quant.data.reviewed_document_inputs import read_reviewed_document_research_input
from tong_quant.data.sec_period_inputs import SECPeriodSelection, read_sec_period_research_input
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    EvidenceQuality,
    InvestmentAssessmentStatus,
    Market,
    Regime,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
    ScoreType,
    SignalAction,
)
from tong_quant.domain.models import Bar, FundamentalFact, Instrument
from tong_quant.market_regime.models import MarketRegime, RegimeContribution
from tong_quant.research.bar_inputs import checked_daily_bars, research_daily_bars
from tong_quant.research.base import evidence_driven_assessment, evidence_score
from tong_quant.research.conditions import ResearchConditionPolicy, research_condition_features
from tong_quant.research.confidence import combine_confidence
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.financial.comparisons import (
    FinancialComparisonStatus,
    financial_comparisons,
)
from tong_quant.research.financial.market_value import MarketValueMatchingPolicy
from tong_quant.research.financial.trailing import TrailingEditionReview, trailing_input_hash
from tong_quant.research.industry import IndustryResearchModule
from tong_quant.research.investment import InvestmentAssessmentBuilder
from tong_quant.research.models import (
    ResearchContext,
    ResearchEvidence,
    ResearchRequest,
    ThesisInvalidationCondition,
)
from tong_quant.research.pattern import PATTERN_FIELDS, PatternResearchModule
from tong_quant.research.policy import PolicyResearchModule
from tong_quant.research.reporting import DefaultResearchReportBuilder
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.trend import TrendResearchModule
from tong_quant.research.value import ValueResearchModule
from tong_quant.screening.models import (
    CompositeScore,
    HardScreenResult,
    OpportunityCandidate,
    ResearchQueueEntry,
    ScoreComponent,
)
from tong_quant.version import FINANCIAL_RESEARCH_VERSION, RESEARCH_CONFIDENCE_VERSION


def test_research_request_requires_counter_thesis_and_invalidation() -> None:
    context = _context(evidence=_evidence(ResearchModuleName.POLICY, "fiscal_policy"))
    with pytest.raises(ValueError, match="thesis and counter thesis"):
        ResearchRequest(
            context=context,
            modules=(ResearchModuleName.POLICY,),
            thesis="Demand may improve",
            counter_thesis="",
            invalidation_conditions=(_invalidation(),),
        )
    with pytest.raises(ValueError, match="invalidation"):
        ResearchRequest(
            context=context,
            modules=(ResearchModuleName.POLICY,),
            thesis="Demand may improve",
            counter_thesis="Policy support may be ineffective",
            invalidation_conditions=(),
        )


def test_configured_manual_diagnostics_cannot_be_silently_ignored_without_receipt():
    with pytest.raises(ValueError, match="reviewed receipt"):
        module = FinancialResearchModule(manual_income_change_pairs=("current=prior",))
        module.evaluate(_context(), {})


@pytest.mark.parametrize("defect", ["symbol", "market", "future_cutoff", "equity", "parallel"])
def test_native_financial_context_cannot_cross_identity_or_authority_boundaries(tmp_path, defect):
    context = _context(market=Market.US)
    store = SQLiteStore(tmp_path / "native.sqlite3")
    store.initialize()
    inputs = read_native_financial_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "TEST", Market.US, as_of=context.as_of, sector_profile="nonfinancial")
    context = replace(context, native_financial_inputs=inputs)
    instrument = context.queue_entry.candidate.instrument
    if defect == "future_cutoff":
        changes = {"as_of": context.as_of + timedelta(seconds=1)}
    elif defect == "parallel":
        changes = {"financial_inputs": _financial_snapshot(_financial_fact(), context.as_of)}
    else:
        instrument = replace(instrument, **{
            "symbol": {"symbol": "AAPL"}, "market": {"market": Market.HONG_KONG},
            "equity": {"asset_type": AssetType.ETF}}[defect])
        changes = {"queue_entry": replace(context.queue_entry,
            candidate=replace(context.queue_entry.candidate, instrument=instrument))}
    with pytest.raises(ValueError):
        replace(context, **changes)


def test_native_receipt_revalidated_before_research_writes_or_direct_evaluation(tmp_path):
    context = _context(market=Market.US)
    store = SQLiteStore(tmp_path / "native.sqlite3")
    store.initialize()
    inputs = read_native_financial_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "TEST", Market.US, as_of=context.as_of, sector_profile="nonfinancial")
    context = replace(context, native_financial_inputs=inputs)
    request = _request(context, modules=(ResearchModuleName.FINANCIAL,))
    object.__setattr__(inputs, "receipt_json", inputs.receipt_json.replace('"LOW"', '"VERIFIED"'))
    repository = Mock()
    with pytest.raises(ValueError):
        ResearchEngine(modules=(FinancialResearchModule(),), repository=repository).run(request)
    repository.start_run.assert_not_called()
    with pytest.raises(ValueError):
        FinancialResearchModule().evaluate(context, {})


@pytest.mark.parametrize("defect", ["symbol", "market", "cutoff", "equity", "parallel", "sector"])
def test_sec_period_context_rejects_identity_time_and_parallel_input_mismatch(tmp_path, defect):
    context = _context(market=Market.US)
    store = SQLiteStore(tmp_path / "sec-context.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    inputs = read_sec_period_research_input(store, artifacts, "0000789019",
        "0001193125-25-123456", symbol="TEST", as_of=context.as_of,
        selections=(SECPeriodSelection("NetIncomeLoss", date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile="nonfinancial")
    context = replace(context, sec_period_inputs=inputs)
    if defect == "cutoff":
        changes = {"as_of": context.as_of + timedelta(microseconds=1)}
    elif defect == "parallel":
        changes = {"financial_inputs": FinancialInputSnapshot(
            "TEST", Market.US, context.as_of, ("revenue",), "nonfinancial", "group", ())}
    elif defect == "sector":
        changes = {"native_financial_inputs": read_native_financial_research_input(
            store, artifacts, "TEST", Market.US, as_of=context.as_of, sector_profile="bank")}
    else:
        instrument = replace(context.queue_entry.candidate.instrument, **{
            "symbol": {"symbol": "OTHER"}, "market": {"market": Market.HONG_KONG},
            "equity": {"asset_type": AssetType.ETF}}[defect])
        changes = {"queue_entry": replace(context.queue_entry,
            candidate=replace(context.queue_entry.candidate, instrument=instrument))}
    with pytest.raises(ValueError):
        replace(context, **changes)


def test_sec_period_receipt_is_revalidated_before_any_research_write(tmp_path):
    context = _context(market=Market.US)
    store = SQLiteStore(tmp_path / "sec-context.sqlite3")
    store.initialize()
    inputs = read_sec_period_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "0000789019", "0001193125-25-123456", symbol="TEST", as_of=context.as_of,
        selections=(SECPeriodSelection("NetIncomeLoss", date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile="nonfinancial")
    context = replace(context, sec_period_inputs=inputs)
    request = _request(context, modules=(ResearchModuleName.FINANCIAL,))
    object.__setattr__(inputs, "receipt_json", inputs.receipt_json.replace('"LOW"', '"VERIFIED"'))
    repository = Mock()
    with pytest.raises(ValueError):
        ResearchEngine(modules=(FinancialResearchModule(),), repository=repository).run(request)
    repository.start_run.assert_not_called()
    with pytest.raises(ValueError):
        FinancialResearchModule().evaluate(context, {})


def test_sec_period_failure_receipt_availability_is_not_backdated_to_old_facts(tmp_path):
    context = _context(market=Market.US)
    store = SQLiteStore(tmp_path / "sec-cutoff.sqlite3")
    store.initialize()
    bound = read_sec_period_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "0000789019", "0001193125-25-123456", symbol="TEST", as_of=context.as_of,
        selections=(SECPeriodSelection("NetIncomeLoss", date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile="nonfinancial")
    old = context.as_of - timedelta(days=1)
    fact = FundamentalFact(context.queue_entry.candidate.instrument,
        "synthetic", date(2024, 12, 31), old, old, Decimal(1), "Synthetic only")
    context = replace(context, fundamentals={"synthetic": (fact,)})
    assert FinancialResearchModule().evaluate(context, {}).available_at == old
    current = replace(context, sec_period_inputs=bound)
    assert FinancialResearchModule().evaluate(current, {}).available_at == context.as_of


def test_sec_period_context_rejects_same_wall_clock_but_different_dst_fold(tmp_path):
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    second = first.replace(fold=1)
    context = _context(as_of=first, market=Market.US)
    store = SQLiteStore(tmp_path / "sec-fold.sqlite3")
    store.initialize()
    bound = read_sec_period_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "0000789019", "0001193125-25-123456", symbol="TEST", as_of=first,
        selections=(SECPeriodSelection("NetIncomeLoss", date(2024, 7, 1), date(2025, 6, 30)),),
        sector_profile="nonfinancial")
    context = replace(context, sec_period_inputs=bound)
    with pytest.raises(ValueError, match="context mismatch"):
        replace(context, as_of=second)


@pytest.mark.parametrize("defect", ["symbol", "market", "cutoff", "equity", "canonical", "sector"])
def test_reviewed_document_context_rejects_identity_and_parallel_policy_mismatch(tmp_path, defect):
    context = _context(market=Market.HONG_KONG)
    instrument = replace(context.queue_entry.candidate.instrument, symbol="0700.HK")
    context = replace(context, queue_entry=replace(context.queue_entry,
        candidate=replace(context.queue_entry.candidate, instrument=instrument)))
    store = SQLiteStore(tmp_path / "manual.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    url = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf"
    inputs = read_reviewed_document_research_input(store, artifacts, "0700.HK", Market.HONG_KONG,
        url, as_of=context.as_of, sector_profile="bank")
    context = replace(context, reviewed_document_inputs=inputs)
    if defect == "cutoff":
        changes = {"as_of": context.as_of + timedelta(microseconds=1)}
    elif defect == "canonical":
        changes = {"financial_inputs": _financial_snapshot(_financial_fact(), context.as_of)}
    elif defect == "sector":
        changes = {"native_financial_inputs": read_native_financial_research_input(
            store, artifacts, "0700.HK", Market.HONG_KONG,
            as_of=context.as_of, sector_profile="nonfinancial")}
    else:
        instrument = replace(instrument, **{
            "symbol": {"symbol": "0005.HK"}, "market": {"market": Market.MALAYSIA},
            "equity": {"asset_type": AssetType.ETF}}[defect])
        changes = {"queue_entry": replace(context.queue_entry,
            candidate=replace(context.queue_entry.candidate, instrument=instrument))}
    with pytest.raises(ValueError):
        replace(context, **changes)


def test_reviewed_document_input_is_revalidated_before_run_writes(tmp_path):
    context = _context(market=Market.HONG_KONG)
    instrument = replace(context.queue_entry.candidate.instrument, symbol="0700.HK")
    context = replace(context, queue_entry=replace(context.queue_entry,
        candidate=replace(context.queue_entry.candidate, instrument=instrument)))
    store = SQLiteStore(tmp_path / "manual.sqlite3")
    store.initialize()
    bound = read_reviewed_document_research_input(store, FileSystemArtifactStore(tmp_path / "raw"),
        "0700.HK", Market.HONG_KONG,
        "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf",
        as_of=context.as_of, sector_profile="bank")
    context = replace(context, reviewed_document_inputs=bound)
    request = _request(context, modules=(ResearchModuleName.FINANCIAL,))
    object.__setattr__(bound, "receipt_json", bound.receipt_json.replace('"LOW"', '"HIGH"'))
    repository = Mock()
    with pytest.raises(ValueError):
        ResearchEngine(modules=(FinancialResearchModule(),), repository=repository).run(request)
    repository.start_run.assert_not_called()
    with pytest.raises(ValueError):
        FinancialResearchModule().evaluate(context, {})


def test_context_rejects_future_evidence() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    future = ResearchEvidence(
        evidence_id="future",
        module=ResearchModuleName.POLICY,
        name="fiscal_policy",
        value=70,
        observed_at=as_of,
        available_at=as_of + timedelta(days=1),
        source="test",
        quality=EvidenceQuality.PRIMARY,
    )
    with pytest.raises(ValueError, match="future data"):
        _context(as_of=as_of, evidence=(future,))


def test_confidence_is_not_a_simple_average_and_caps_weak_links() -> None:
    confidence = combine_confidence(
        evidence_quality=100,
        data_completeness=100,
        module_agreement=100,
        point_in_time_integrity=20,
    )

    assert confidence.confidence <= 30
    assert confidence.confidence != 80
    assert confidence.method == (
        f"weighted_geometric_with_weakest_link_cap:{RESEARCH_CONFIDENCE_VERSION}")


@pytest.mark.parametrize("reverse", [False, True])
def test_evidence_driven_assessment_keeps_actual_latest_fold_availability(reverse):
    first = datetime(2026, 11, 1, 1, 45, tzinfo=ZoneInfo("America/New_York"), fold=0)
    second = first.replace(minute=15, fold=1)
    cutoff = second.replace(minute=30)
    inputs = tuple(ResearchEvidence(name, ResearchModuleName.POLICY, name, 70,
        first - timedelta(days=1), timestamp, "synthetic", EvidenceQuality.PRIMARY)
        for name, timestamp in (("first", first), ("second", second)))
    if reverse:
        inputs = tuple(reversed(inputs))
    result = evidence_driven_assessment(module=ResearchModuleName.POLICY,
        context=_context(as_of=cutoff, evidence=inputs),
        required_names=frozenset({"first", "second"}), model_version="synthetic")
    assert result.available_at.astimezone(UTC) == second.astimezone(UTC)
    assert result.confidence.point_in_time_integrity == 100
    assert result.confidence.method.endswith(RESEARCH_CONFIDENCE_VERSION)


def test_policy_assessment_contains_all_policy_dimensions() -> None:
    context = _context(evidence=_all_policy_evidence())
    output = PolicyResearchModule().evaluate(context, {})

    assert output.assessment.module is ResearchModuleName.POLICY
    assert output.regulatory_environment == "regulatory_environment summary"
    assert output.geopolitical_factors == "geopolitical_factors summary"
    assert output.assessment.confidence.data_completeness == 100


@pytest.mark.parametrize("module,fields", [
    (ResearchModuleName.POLICY, ("fiscal_policy", "monetary_policy")),
    (ResearchModuleName.INDUSTRY, ("industry_trend", "industry_heat")),
    (ResearchModuleName.VALUE, ("survival", "valuation")),
])
@pytest.mark.parametrize("defect", ["unknown_only", "missing", "duplicate", "boolean", "text"])
def test_declared_research_score_inputs_fail_closed(module, fields, defect):
    evidence = _evidence_set(module, fields)
    if defect == "unknown_only":
        evidence = _evidence(module, "unrelated_numeric_annotation", score=99)
    elif defect == "missing":
        evidence = evidence[:1]
    elif defect == "duplicate":
        evidence = (*evidence, replace(evidence[0], evidence_id="duplicate", value=100))
    elif defect in {"boolean", "text"}:
        evidence = (replace(evidence[0], value=True if defect == "boolean" else "99"),
                    *evidence[1:])
    result = evidence_driven_assessment(
        module=module, context=_context(evidence=evidence), required_names=frozenset(fields),
        model_version="synthetic", dependencies={},
    )
    assert result.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert result.score is None and result.confidence.confidence == 0
    assert result.evidence == evidence
    assert result.evidence_ids == tuple(item.evidence_id for item in evidence)


def test_unknown_annotations_cannot_raise_declared_score_or_confidence():
    module = ResearchModuleName.INDUSTRY
    fields = ("industry_trend", "industry_heat")
    declared = tuple(replace(item, quality=EvidenceQuality.ESTIMATED)
                     for item in _evidence_set(module, fields, score=30))
    unknown = _evidence(module, "unrelated_numeric_annotation", score=100)
    before = evidence_driven_assessment(
        module=module, context=_context(evidence=declared), required_names=frozenset(fields),
        model_version="synthetic",
    )
    after = evidence_driven_assessment(
        module=module, context=_context(evidence=(*declared, *unknown)),
        required_names=frozenset(fields), model_version="synthetic",
    )
    assert before.score == after.score == 30
    assert before.confidence == after.confidence
    assert after.evidence == (*declared, *unknown)
    assert after.features["ignored_evidence_names"] == "unrelated_numeric_annotation"


def test_boolean_is_not_a_numeric_research_score():
    item = replace(_evidence(ResearchModuleName.VALUE, "survival")[0], value=True)
    assert evidence_score(item) is None


def test_empty_declared_rubric_cannot_score_unrelated_evidence():
    result = evidence_driven_assessment(
        module=ResearchModuleName.INDUSTRY,
        context=_context(evidence=_evidence(ResearchModuleName.INDUSTRY, "unrelated", score=99)),
        required_names=frozenset(), model_version="synthetic",
    )
    assert result.score is None and result.conclusion is ResearchConclusion.INSUFFICIENT_DATA


def test_shared_scoring_entry_revalidates_mutated_future_context():
    module = ResearchModuleName.VALUE
    context = _context(evidence=_evidence(module, "survival"))
    object.__setattr__(context, "evidence", tuple(replace(
        item, observed_at=context.as_of + timedelta(days=1),
        available_at=context.as_of + timedelta(days=1)) for item in context.evidence))
    with pytest.raises(ValueError, match="future data"):
        evidence_driven_assessment(
            module=module, context=context, required_names=frozenset({"survival"}),
            model_version="synthetic")


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_declared_invalid_numeric_scores_are_rejected(value):
    module = ResearchModuleName.INDUSTRY
    evidence = (replace(_evidence(module, "industry_trend")[0], value=value),)
    with pytest.raises(ValueError, match="score out of range"):
        evidence_driven_assessment(
            module=module, context=_context(evidence=evidence),
            required_names=frozenset({"industry_trend"}), model_version="test")


def test_value_research_runs_policy_financial_and_industry_dependencies() -> None:
    evidence = (
        *_all_policy_evidence(),
        *_evidence_set(
            ResearchModuleName.FINANCIAL,
            ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        ),
        *_evidence_set(
            ResearchModuleName.INDUSTRY,
            ("industry_trend", "industry_heat", "industry_cycle", "relative_strength"),
        ),
        *_evidence_set(
            ResearchModuleName.VALUE,
            ("survival", "cycle", "valuation", "growth"),
        ),
    )
    context = _context(evidence=evidence)
    request = _request(context, modules=(ResearchModuleName.VALUE,))
    engine = ResearchEngine(
        modules=(
            PolicyResearchModule(),
            FinancialResearchModule(),
            IndustryResearchModule(),
            ValueResearchModule(),
        )
    )

    run = engine.run(request)

    assert [item.module for item in run.report.assessments] == [
        ResearchModuleName.FINANCIAL,
        ResearchModuleName.POLICY,
        ResearchModuleName.INDUSTRY,
        ResearchModuleName.VALUE,
    ]
    assert run.report.thesis == request.thesis
    assert run.report.counter_thesis == request.counter_thesis
    assert run.report.invalidation_conditions == request.invalidation_conditions
    assert run.signal.action is SignalAction.RESEARCH
    assert run.signal.features["informational_only"] is True
    assert not hasattr(run, "order")


@pytest.mark.parametrize("market", list(Market))
def test_shared_technical_calculations_preserve_four_market_scope(market: Market) -> None:
    module = TechnicalResearchModule()
    baseline = module.evaluate(_context(bars=_bars(260)), {})
    result = module.evaluate(_context(market=market, bars=_bars(260, market=market)), {})

    # Synthetic observations check calculation reuse, not exchange or source approval.
    for name in (
        "macd_dif", "macd_dea", "macd_histogram", "macd_cross",
        "kdj_k", "kdj_d", "kdj_j", "kdj_cross", "technical_atr",
        "triple_average_events", "granville_events", "granville_available",
        "trend_structure_family", "momentum_family", "technical_confluence",
        "setup_state", "structural_invalidation_reference", "dynamic_invalidation_reference",
        "short_moving_average", "long_moving_average", "position_52_week",
    ):
        assert result.features[name] == baseline.features[name]
    assert result.features["macd_dif"] is not None
    assert result.features["kdj_k"] is not None
    assert result.features["granville_available"] is True
    assert result.features["technical_research_only"] is True
    assert result.features["technical_scoring_admitted"] is False
    assert result.features["size_style_status"] == "INSUFFICIENT_DATA"
    assert result.features["seven_plus_one_status"] == "DEFERRED_BY_OWNER"
    if market is not Market.CHINA_A:
        assert result.features["technical_input_hash"] != baseline.features["technical_input_hash"]
    assert not hasattr(result, "order")


@pytest.mark.parametrize("market", list(Market))
@pytest.mark.parametrize("failed", [None, "breakout", "volume", "sentiment", "heat"])
def test_four_market_turtle_requires_every_confirmation(
    market: Market, failed: str | None,
) -> None:
    bars = _bars(40, market=market)
    current = replace(bars[-1], open=Decimal(14), close=Decimal(15), high=Decimal(16),
                      low=Decimal(13), volume=Decimal(4000))
    if failed == "breakout":
        current = replace(current, close=bars[-2].high, open=Decimal(10), low=Decimal(9))
    if failed == "volume":
        current = replace(current, volume=Decimal(1))
    evidence = _evidence_set(
        ResearchModuleName.TREND,
        ("market_sentiment_confirmation", "industry_heat_confirmation"), score=80,
    )
    if failed == "sentiment":
        evidence = (replace(evidence[0], value=0), evidence[1])
    if failed == "heat":
        evidence = (evidence[0], replace(evidence[1], value=0))
    context = _context(market=market, bars=(*bars[:-1], current), evidence=evidence)
    result = TrendResearchModule().evaluate(context, {})

    assert result.features["trend_setup_valid"] is (failed is None)
    assert result.features["framework_only"] is True
    assert "atr_stop_reference" in result.features
    assert "pyramid_scenario_levels" in result.features
    if failed is None:
        assert result.score == 80
    else:
        assert result.conclusion is ResearchConclusion.CAUTION
        assert result.score is None
    assert not hasattr(result, "action")
    assert not hasattr(result, "order")


@pytest.mark.parametrize("market", list(Market))
def test_four_market_pattern_applicability_does_not_export_a_share_rules(market: Market) -> None:
    context = _context(market=market, bars=_bars(40, market=market))
    result = PatternResearchModule().evaluate(context, {})

    expected = (ResearchConclusion.INSUFFICIENT_DATA if market is Market.CHINA_A
                else ResearchConclusion.NOT_APPLICABLE)
    assert result.conclusion is expected
    assert result.score is None


def test_technical_and_trend_research_produce_analysis_not_trade_decisions() -> None:
    context = _context(
        bars=_bars(260),
        evidence=_evidence_set(
            ResearchModuleName.TREND,
            ("market_sentiment_confirmation", "industry_heat_confirmation"),
            score=80,
        ),
    )
    technical = TechnicalResearchModule().evaluate(context, {})
    trend = TrendResearchModule().evaluate(
        context,
        {
            ResearchModuleName.POLICY: _supportive_assessment(
                ResearchModuleName.POLICY, context
            ),
            ResearchModuleName.INDUSTRY: _supportive_assessment(
                ResearchModuleName.INDUSTRY, context
            ),
            ResearchModuleName.TECHNICAL: technical,
        },
    )

    assert technical.score is not None
    assert technical.features["position_52_week"] is not None
    assert trend.features["framework_only"] is True
    assert "atr_stop_reference" in trend.features
    assert "pyramid_scenario_levels" in trend.features
    assert not hasattr(trend, "action")
    assert not hasattr(trend, "order")


def test_pattern_research_is_china_specific_and_requires_intraday_evidence() -> None:
    module = PatternResearchModule()
    us_context = _context(
        market=Market.US,
        bars=_bars(30, market=Market.US),
        evidence=(),
    )
    china_context = _context(bars=_bars(30), evidence=())

    not_applicable = module.evaluate(us_context, {})
    insufficient = module.evaluate(china_context, {})

    assert not_applicable.conclusion is ResearchConclusion.NOT_APPLICABLE
    assert insufficient.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert insufficient.score is None


@pytest.mark.parametrize("external", [True, "99", None])
def test_trend_confirmation_requires_numeric_external_evidence(external):
    evidence = _evidence_set(ResearchModuleName.TREND,
                             ("market_sentiment_confirmation", "industry_heat_confirmation"),
                             score=100)
    evidence = (replace(evidence[0], value=external), evidence[1])
    result = TrendResearchModule().evaluate(_context(bars=_bars(40), evidence=evidence), {})
    assert result.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert result.score is None


@pytest.mark.parametrize("failed", ["breakout", "volume", "sentiment", "heat"])
def test_four_confirmations_cannot_compensate_for_each_other(failed):
    bars = _bars(40)
    current = replace(bars[-1], open=Decimal(14), close=Decimal(15), high=Decimal(16),
                      low=Decimal(13), volume=Decimal(4000))
    if failed == "breakout":
        current = replace(current, close=bars[-2].high, open=Decimal(10), low=Decimal(9))
    if failed == "volume":
        current = replace(current, volume=Decimal(1))
    evidence = _evidence_set(ResearchModuleName.TREND,
                             ("market_sentiment_confirmation", "industry_heat_confirmation"),
                             score=100)
    if failed == "sentiment":
        evidence = (replace(evidence[0], value=0), evidence[1])
    if failed == "heat":
        evidence = (evidence[0], replace(evidence[1], value=0))
    context = _context(bars=(*bars[:-1], current), evidence=evidence)
    result = TrendResearchModule().evaluate(context, {})
    assert result.features["trend_setup_valid"] is False
    assert result.conclusion is ResearchConclusion.CAUTION and result.score is None


def test_all_four_trend_confirmations_and_zero_volume_warmup():
    bars = _bars(40)
    current = replace(bars[-1], open=Decimal(14), close=Decimal(15), high=Decimal(16),
                      low=Decimal(13), volume=Decimal(4000))
    evidence = _evidence_set(ResearchModuleName.TREND,
                             ("market_sentiment_confirmation", "industry_heat_confirmation"),
                             score=80)
    result = TrendResearchModule().evaluate(_context(bars=(*bars[:-1], current),
                                                     evidence=evidence), {})
    assert result.features["trend_setup_valid"] is True
    assert result.score == 80
    no_prior_volume = tuple(replace(bar, volume=Decimal(0)) for bar in bars[:-1])
    result = TrendResearchModule().evaluate(_context(bars=(*no_prior_volume, current),
                                                     evidence=evidence), {})
    assert result.conclusion is ResearchConclusion.INSUFFICIENT_DATA


@pytest.mark.parametrize("case,digest", [
    ("all_four", "60b13e1c44a98ecbfa4f25413a8ae6f585690651620b221790857566e4c8a218"),
    ("no_breakout", "9ae03ff260657b054ff62180320f335cdc7bb3b27f45ff63825ea0e60071d4a1"),
    ("zero_volume", "9a6ad45ada2bfb5d9ae8f27da33f20bb91b8354623112009da42a29ccd50ef8b"),
])
def test_trend_price_extraction_preserves_existing_full_assessment_hash(case, digest):
    from dataclasses import asdict
    from hashlib import sha256

    from tong_quant.data.financial_inputs import financial_input_json

    bars = _bars(40)
    current = replace(bars[-1], open=Decimal(14), close=Decimal(15), high=Decimal(16),
                      low=Decimal(13), volume=Decimal(4000))
    evidence = _evidence_set(ResearchModuleName.TREND,
        ("market_sentiment_confirmation", "industry_heat_confirmation"), score=80)
    series = bars if case == "no_breakout" else (
        *tuple(replace(bar, volume=Decimal(0)) if case == "zero_volume" else bar
               for bar in bars[:-1]), current)
    module = TrendResearchModule()
    result = module.evaluate(_context(bars=series, evidence=evidence), {})
    assert sha256(financial_input_json(asdict(result)).encode()).hexdigest() == digest
    partial = module.evaluate(_context(bars=series), {})
    assert partial.conclusion is ResearchConclusion.INSUFFICIENT_DATA and partial.score is None


def test_technical_module_exposes_shorter_indicators_without_faking_long_warmup():
    result = TechnicalResearchModule().evaluate(_context(bars=_bars(50)), {})
    assert result.score is None and result.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert result.features["macd_dif"] is not None
    assert result.features["kdj_k"] is not None
    assert result.features["granville_available"] is False
    assert result.features["technical_scoring_admitted"] is False


@pytest.mark.parametrize("rising_count", [None, True, "3500", -1, 3000, 3001])
def test_pattern_breadth_rule_requires_actual_count_strictly_above_3000(rising_count):
    evidence = _evidence_set(ResearchModuleName.PATTERN,
                             tuple(sorted(PATTERN_FIELDS - {"high_volume_long_upper_shadow"})),
                             score=90)
    evidence = tuple(replace(item, metadata={"rising_stocks": rising_count})
                     if item.name == "rising_stocks_environment" else item for item in evidence)
    result = PatternResearchModule().evaluate(_context(bars=_bars(40), evidence=evidence), {})
    if type(rising_count) is not int or rising_count < 0:
        assert result.conclusion is ResearchConclusion.INSUFFICIENT_DATA
        assert result.score is None
    elif rising_count == 3000:
        assert result.conclusion is ResearchConclusion.CAUTION and result.score is None
        assert result.features["rising_stocks_environment_satisfied"] is False
    else:
        assert result.features["rising_stocks_environment_satisfied"] is True


def _condition_fixture():
    # Pure specification fixtures, never real financial/source authorization.
    context = _context(bars=_bars(260))
    request = replace(_request(context, modules=(ResearchModuleName.TECHNICAL,)),
                      condition_style="long_term_confirmation")
    financial = _supportive_assessment(ResearchModuleName.FINANCIAL, context)
    financial = replace(financial, features={"financial_scoring_authorized": True})
    value = _supportive_assessment(ResearchModuleName.VALUE, context)
    technical = TechnicalResearchModule().evaluate(context, {})
    technical = replace(technical, features={**technical.features,
                                            "trend_structure_family": "BULLISH",
                                            "momentum_family": "BULLISH"})
    return request, (financial, value, technical)


def test_complete_candidate_conditions_require_validation_not_execution():
    request, assessments = _condition_fixture()
    result = research_condition_features(request, assessments)
    document = json.loads(result["condition_review_json"])
    assert result["condition_review_state"] == "VALIDATION_REQUIRED"
    assert document["validation_status"] == "NOT_EVALUATED"
    assert document["execution_authorized"] is False
    assert document["thesis_invalidation_evaluation"] == "NOT_EVALUATED"
    report = DefaultResearchReportBuilder().build(request, assessments, None)
    assert report.model_version == "research-report-v0.5.4-utc-period-date"


@pytest.mark.parametrize("defect", ["absent", "unscored", "legacy", "disabled"])
def test_missing_or_unqualified_financial_research_cannot_be_replaced_by_technicals(defect):
    request, assessments = _condition_fixture()
    financial, value, technical = assessments
    if defect == "absent":
        assessments = (value, technical)
    else:
        financial = replace(financial, **({"score": None} if defect == "unscored" else {
            "features": {} if defect == "legacy" else {"financial_scoring_authorized": False}}))
        assessments = (financial, value, technical)
    result = research_condition_features(request, assessments)
    assert result["condition_review_state"] == "DATA_BLOCKED"


@pytest.mark.parametrize("family", ["trend_structure_family", "momentum_family"])
def test_conflict_means_wait_for_candidate_confirmation_not_reject_or_sell(family):
    request, (financial, value, technical) = _condition_fixture()
    technical = replace(technical, features={**technical.features, family: "CONFLICTED"})
    result = research_condition_features(request, (financial, value, technical))
    assert result["condition_review_state"] == "WAIT_CONFIRMATION"
    assert result["condition_review_execution_authorized"] is False


def test_candidate_confidence_threshold_is_an_explicit_policy():
    request, assessments = _condition_fixture()
    policy = ResearchConditionPolicy(minimum_research_confidence=100)
    financial = assessments[0]
    financial = replace(financial, confidence=replace(financial.confidence, confidence=90))
    result = research_condition_features(request, (financial, *assessments[1:]), policy=policy)
    assert result["condition_review_state"] == "WAIT_CONFIRMATION"


@pytest.mark.parametrize("name", ["breakout_confirmation", "volume_confirmation",
                                  "market_sentiment_confirmation", "industry_heat_confirmation"])
def test_candidate_turtle_requires_every_confirmation(name):
    request, (financial, value, technical) = _condition_fixture()
    request = replace(request, condition_style="improved_turtle")
    trend = replace(technical, module=ResearchModuleName.TREND, features={
        "breakout_confirmation_confirmed": True, "volume_confirmation_confirmed": True,
        "market_sentiment_confirmation_confirmed": True,
        "industry_heat_confirmation_confirmed": True, "strict_donchian_breakout": True,
    })
    result = research_condition_features(request, (financial, value, trend))
    assert result["condition_review_state"] == "VALIDATION_REQUIRED"
    trend = replace(trend, features={**trend.features, f"{name}_confirmed": False})
    result = research_condition_features(request, (financial, value, trend))
    assert result["condition_review_state"] == "WAIT_CONFIRMATION"


def test_turtle_keeps_contrary_financial_context_without_requiring_long_term_value():
    request, (financial, _, technical) = _condition_fixture()
    request = replace(request, condition_style="improved_turtle")
    financial = replace(financial, conclusion=ResearchConclusion.CAUTION, score=40)
    trend = replace(technical, module=ResearchModuleName.TREND, features={
        "breakout_confirmation_confirmed": True, "volume_confirmation_confirmed": True,
        "market_sentiment_confirmation_confirmed": True,
        "industry_heat_confirmation_confirmed": True, "strict_donchian_breakout": True,
    })
    result = research_condition_features(request, (financial, trend))
    assert result["condition_review_state"] == "VALIDATION_REQUIRED"
    assert result["condition_review_execution_authorized"] is False


@pytest.mark.parametrize("confidence", [True, -1, 101, float("nan")])
def test_invalid_condition_confidence_policy_is_rejected(confidence):
    with pytest.raises(ValueError):
        ResearchConditionPolicy(confidence)


def test_actual_hard_failure_cannot_be_offset_in_condition_report():
    request, assessments = _condition_fixture()
    entry = request.context.queue_entry
    # Simulate mutation after queue admission: a recheck must not publish a completed report.
    object.__setattr__(entry, "hard_screen_results", (replace(entry.hard_screen_results[0],
                                                            passed=False),))
    report = DefaultResearchReportBuilder().build(request, assessments, None)
    assert report.status is ResearchRunStatus.INCOMPLETE
    assert report.assessments[0].features["condition_review_state"] == "SCREEN_REJECTED"


def test_condition_identity_binds_policy_assessments_thesis_and_ignores_tuple_order():
    request, assessments = _condition_fixture()
    initial = research_condition_features(request, assessments)
    assert initial == research_condition_features(request, tuple(reversed(assessments)))
    assert initial["condition_review_hash"] != research_condition_features(
        replace(request, counter_thesis="Different bear case"), assessments
    )["condition_review_hash"]
    assert initial["condition_review_hash"] != research_condition_features(
        request, assessments, policy=ResearchConditionPolicy(61))["condition_review_hash"]


def test_condition_future_child_evidence_and_duplicate_modules_are_rejected():
    request, assessments = _condition_fixture()
    future = replace(assessments[0].evidence[0],
                     observed_at=request.context.as_of + timedelta(days=1),
                     available_at=request.context.as_of + timedelta(days=1))
    with pytest.raises(ValueError, match="future child"):
        research_condition_features(request, (replace(assessments[0], evidence=(future,)),
                                              *assessments[1:]))
    with pytest.raises(ValueError, match="duplicate"):
        research_condition_features(request, (*assessments, assessments[0]))


@pytest.mark.parametrize("style", ["long_term_confirmation", "improved_turtle"])
@pytest.mark.parametrize("module_index", [0, 1, 2])
@pytest.mark.parametrize("age", [timedelta(seconds=1), timedelta(days=1)])
def test_condition_review_cannot_mix_previous_evaluation_with_current_decision(
    style, module_index, age,
):
    request, assessments = _condition_fixture()
    request = replace(request, condition_style=style)
    if style == "improved_turtle":
        trend = replace(assessments[2], module=ResearchModuleName.TREND, features={
            "breakout_confirmation_confirmed": True, "volume_confirmation_confirmed": True,
            "market_sentiment_confirmation_confirmed": True,
            "industry_heat_confirmation_confirmed": True, "strict_donchian_breakout": True,
        })
        assessments = (*assessments[:2], trend)
    assert research_condition_features(request, assessments)["condition_review_state"] == (
        "VALIDATION_REQUIRED")
    cached = list(assessments)
    previous = request.context.as_of - age
    cached[module_index] = replace(cached[module_index], evaluated_at=previous,
                                   available_at=previous)
    with pytest.raises(ValueError, match="share the request decision cutoff"):
        research_condition_features(request, tuple(cached))


@pytest.mark.parametrize("module_index", [0, 1, 2])
def test_condition_review_rejects_future_module_evaluation(module_index):
    request, assessments = _condition_fixture()
    future = request.context.as_of + timedelta(seconds=1)
    changed = list(assessments)
    changed[module_index] = replace(changed[module_index], evaluated_at=future, available_at=future)
    with pytest.raises(ValueError, match="future assessments"):
        research_condition_features(request, tuple(changed))


@pytest.mark.parametrize("offset", [8, -5])
def test_condition_review_allows_equivalent_instants_without_changing_identity(offset):
    from datetime import timezone

    request, assessments = _condition_fixture()
    original = research_condition_features(request, assessments)
    equivalent = tuple(replace(item, evaluated_at=item.evaluated_at.astimezone(
        timezone(timedelta(hours=offset)))) for item in assessments)
    assert research_condition_features(request, equivalent) == original
    assert original["condition_review_version"] == "research-candidate-conditions-v2-cutoff-bound"


def test_condition_review_cannot_reuse_cached_assessments_at_a_later_request_cutoff():
    request, assessments = _condition_fixture()
    later = replace(request, context=replace(request.context,
                                             as_of=request.context.as_of + timedelta(hours=1)))
    with pytest.raises(ValueError, match="share the request decision cutoff"):
        research_condition_features(later, assessments)


@pytest.mark.parametrize("field", ["evaluated_at", "available_at", "child_evidence"])
def test_condition_review_rejects_future_dst_fold_even_when_wall_clock_looks_equal(field):
    from zoneinfo import ZoneInfo

    request, assessments = _condition_fixture()
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    later = cutoff.replace(fold=1)
    assert cutoff == later and cutoff.astimezone(UTC) < later.astimezone(UTC)
    request = replace(request, context=replace(request.context, as_of=cutoff))
    current = tuple(replace(item, evaluated_at=cutoff) for item in assessments)
    with pytest.raises(ValueError, match="future"):
        if field == "child_evidence":
            child = replace(current[0].evidence[0], observed_at=later, available_at=later)
            changed = replace(current[0], evidence=(child,))
        else:
            changed = replace(current[0], **{field: later})
        research_condition_features(request, (changed, *current[1:]))


def test_condition_review_rejects_older_dst_fold_as_a_different_evaluation_cutoff():
    from zoneinfo import ZoneInfo

    request, assessments = _condition_fixture()
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1)
    request = replace(request, context=replace(request.context, as_of=cutoff))
    current = tuple(replace(item, evaluated_at=cutoff) for item in assessments)
    previous = replace(current[0], evaluated_at=cutoff.replace(fold=0))
    with pytest.raises(ValueError, match="share the request decision cutoff"):
        research_condition_features(request, (previous, *current[1:]))


@pytest.mark.parametrize("age", [timedelta(days=1), -timedelta(seconds=1)])
def test_condition_free_reports_cannot_bypass_assessment_cutoff_binding(age):
    request, assessments = _condition_fixture()
    request = replace(request, condition_style=None)
    timestamp = request.context.as_of - age
    cached = replace(assessments[0], evaluated_at=timestamp, available_at=timestamp)
    with pytest.raises(ValueError, match="decision cutoff|future assessments"):
        DefaultResearchReportBuilder().build(request, (cached, *assessments[1:]), None)


def test_condition_free_report_rechecks_separately_supplied_policy_assessment():
    request, assessments = _condition_fixture()
    request = replace(request, condition_style=None)
    from tong_quant.research.models import PolicyAssessment

    policy = _supportive_assessment(ResearchModuleName.POLICY, request.context)
    previous = request.context.as_of - timedelta(days=1)
    policy = replace(policy, evaluated_at=previous, available_at=previous)
    wrapper = PolicyAssessment(policy, "fixture", "fixture", "fixture", "fixture", "fixture")
    with pytest.raises(ValueError, match="decision cutoff"):
        DefaultResearchReportBuilder().build(request, assessments, wrapper)


def test_bearish_setup_reference_is_never_presented_as_long_position_stop():
    request, (financial, value, technical) = _condition_fixture()
    technical = replace(technical, features={**technical.features, "setup_direction": "bearish",
                                            "setup_state": "CONFIRMED",
                                            "dynamic_invalidation_reference": 99.0})
    result = research_condition_features(request, (financial, value, technical))
    assert json.loads(result["condition_review_json"])["long_invalidation_reference"] is None
    assert result["long_candidate_invalidation_observed"] is False


def test_report_builder_explicit_opt_in_keeps_real_financial_gap_visible():
    context = _context(bars=_bars(260))
    request = replace(_request(context, modules=(ResearchModuleName.TECHNICAL,
                                                ResearchModuleName.FINANCIAL)),
                      condition_style="long_term_confirmation")
    run = ResearchEngine(
        modules=(TechnicalResearchModule(), FinancialResearchModule()),
    ).run(request)
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    assert run.report.assessments[0].features["condition_review_state"] == "DATA_BLOCKED"
    assert run.signal.action is SignalAction.RESEARCH
    assert InvestmentAssessmentBuilder().build(
        run.report, assessed_at=context.as_of).investment_score is None
    raw = TechnicalResearchModule().evaluate(context, {})
    old_request = replace(request, condition_style=None)
    old = DefaultResearchReportBuilder().build(old_request, (raw,), None)
    assert "condition_review_state" not in old.assessments[0].features


def test_report_condition_annotations_cannot_be_recursively_reused_as_module_results():
    request, assessments = _condition_fixture()
    report = DefaultResearchReportBuilder().build(request, assessments, None)
    with pytest.raises(ValueError, match="raw module"):
        research_condition_features(request, report.assessments)


def test_financial_research_exposes_visible_restatement_history() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = _instrument(Market.CHINA_A)
    facts = (
        FundamentalFact(
            instrument=instrument,
            metric="revenue",
            period_end=date(2025, 12, 31),
            published_at=as_of - timedelta(days=2),
            available_at=as_of - timedelta(days=2),
            value=Decimal("100"),
            source="test",
        ),
        FundamentalFact(
            instrument=instrument,
            metric="revenue",
            period_end=date(2025, 12, 31),
            published_at=as_of - timedelta(days=1),
            available_at=as_of - timedelta(days=1),
            value=Decimal("90"),
            revision=1,
            source="test",
        ),
    )
    context = _context(
        as_of=as_of,
        evidence=_evidence_set(
            ResearchModuleName.FINANCIAL,
            ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        ),
        fundamentals={"revenue": facts},
    )

    assessment = FinancialResearchModule().evaluate(context, {})

    assert assessment.features["restatement_detected"] is True
    assert "revenue" in str(assessment.features["restated_metrics"])


def _financial_fact() -> FundamentalFact:
    return FundamentalFact(
        instrument=_instrument(Market.CHINA_A), metric="revenue",
        period_end=date(2025, 9, 30),
        published_at=datetime(2025, 10, 20, tzinfo=UTC),
        available_at=datetime(2025, 10, 21, tzinfo=UTC),
        value=Decimal("100"), source="fixture", currency="CNY",
    )


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_financial_latest_value_uses_period_and_visible_version_not_input_order(
    order: tuple[int, ...],
) -> None:
    first = _financial_fact()
    facts = (
        first,
        replace(first, revision=1, value=Decimal("90"),
                available_at=first.available_at + timedelta(days=1)),
        replace(first, period_end=date(2025, 6, 30), value=Decimal("999"),
                available_at=first.available_at + timedelta(days=10)),
    )
    context = _context(fundamentals={"revenue": tuple(facts[index] for index in order)})
    assessment = FinancialResearchModule().evaluate(context, {})
    assert assessment.features["latest_revenue"] == "90"
    assert assessment.features["latest_revenue_period_end"] == "2025-09-30"
    assert assessment.features["latest_revenue_unit"] == "absolute"
    assert assessment.features["latest_revenue_currency"] == "CNY"
    assert assessment.features["latest_revenue_trust_level"] == "unknown"
    assert assessment.features["latest_revenue_availability_precision"] == "unknown"
    assert assessment.score is None  # Diagnostic values are not research scores.


@pytest.mark.parametrize("kind", ["symbol", "market", "asset_type"])
def test_research_context_rejects_mixed_instrument_bars_and_facts(kind: str) -> None:
    fact = _financial_fact()
    fields = {
        "symbol": {"symbol": "600001"},
        "market": {"market": Market.US},
        "asset_type": {"asset_type": AssetType.INDEX},
    }[kind]
    wrong_instrument = replace(fact.instrument, **fields)
    with pytest.raises(ValueError, match="fundamental instrument mismatch"):
        _context(fundamentals={"revenue": (replace(fact, instrument=wrong_instrument),)})
    with pytest.raises(ValueError, match="bar instrument mismatch"):
        _context(bars=(replace(_bars(1)[0], instrument=wrong_instrument),))


def test_research_context_rejects_a_metric_dictionary_alias() -> None:
    with pytest.raises(ValueError, match="fundamental metric mismatch"):
        _context(fundamentals={"profit": (_financial_fact(),)})


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_research_context_rejects_nonfinite_fundamental_values(value: str) -> None:
    with pytest.raises(ValueError, match="fundamental value must be finite"):
        _context(fundamentals={"revenue": (replace(_financial_fact(), value=Decimal(value)),)})


def test_research_context_rejects_a_future_report_period_even_with_old_availability() -> None:
    with pytest.raises(ValueError, match="future data"):
        _context(fundamentals={
            "revenue": (replace(_financial_fact(), period_end=date(2026, 3, 31)),),
        })


@pytest.mark.parametrize("zone", ["UTC", "Asia/Kuala_Lumpur", "America/New_York"])
@pytest.mark.parametrize("future_period", [False, True])
def test_fundamental_period_visibility_uses_one_utc_date_for_equivalent_instants(
    zone, future_period
):
    instant = datetime(2026, 9, 30, 23, 30, tzinfo=UTC)
    cutoff = instant.astimezone(ZoneInfo(zone))
    fact = replace(_financial_fact(), period_end=date(2026, 10, 1) if future_period
                   else date(2026, 9, 30))
    if future_period:
        with pytest.raises(ValueError, match="future data"):
            _context(as_of=cutoff, fundamentals={"revenue": (fact,)})
    else:
        context = _context(as_of=cutoff, fundamentals={"revenue": (fact,)})
        assert context.as_of is cutoff
        assert context.fundamentals["revenue"][0] is fact


def test_research_context_rejects_future_bar_time_with_backdated_availability() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    future = as_of + timedelta(days=1)
    with pytest.raises(ValueError, match="observation timestamp"):
        replace(_bars(1)[0], timestamp=future, available_at=as_of)
    bar = replace(_bars(1)[0], timestamp=future, available_at=future)
    with pytest.raises(ValueError, match="future data"):
        _context(as_of=as_of, bars=(bar,))


@pytest.mark.parametrize("kind", [
    "bar_observed", "bar_available", "candidate_metadata", "bar_metadata", "fact_metadata",
    "evidence_available", "evidence_observed", "fact_available", "fact_published",
    "queue_admitted", "candidate_available", "candidate_discovered", "queue_score",
    "screen_available", "screen_evaluated",
])
def test_research_context_rejects_future_dst_fold_inputs(kind):
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    future = cutoff.replace(fold=1)
    context = _context(as_of=cutoff, market=Market.US)
    instrument = context.queue_entry.candidate.instrument
    bar = Bar(instrument, cutoff, cutoff, Decimal(10), Decimal(11), Decimal(9),
              Decimal(10), Decimal(100), source="synthetic")
    fact = FundamentalFact(instrument, "revenue", date(2026, 9, 30), cutoff, cutoff,
                           Decimal(100), "synthetic")
    evidence = _evidence(ResearchModuleName.FINANCIAL, "fixture", as_of=cutoff)[0]
    if kind.startswith("bar_") and kind != "bar_metadata":
        field = "timestamp" if kind == "bar_observed" else "available_at"
        # Mutate this fixture to exercise revalidation of an existing context.
        object.__setattr__(bar, field, future)
        object.__setattr__(context, "bars", (bar,))
    elif kind.endswith("metadata"):
        later_instrument = replace(instrument, available_at=future)
        if kind == "candidate_metadata":
            object.__setattr__(context, "queue_entry", replace(context.queue_entry,
                candidate=replace(context.queue_entry.candidate, instrument=later_instrument)))
        elif kind == "bar_metadata":
            object.__setattr__(context, "bars", (replace(bar, instrument=later_instrument),))
        else:
            context.fundamentals["revenue"] = (replace(fact, instrument=later_instrument),)
    elif kind.startswith("evidence_"):
        field = "observed_at" if kind.endswith("observed") else "available_at"
        object.__setattr__(evidence, field, future)
        object.__setattr__(context, "evidence", (evidence,))
    elif kind.startswith("fact_"):
        field = "published_at" if kind.endswith("published") else "available_at"
        object.__setattr__(fact, field, future)
        context.fundamentals["revenue"] = (fact,)
    else:
        entry = context.queue_entry
        if kind == "queue_admitted":
            object.__setattr__(entry, "admitted_at", future)
        elif kind.startswith("candidate_"):
            field = "discovered_at" if kind.endswith("discovered") else "available_at"
            object.__setattr__(entry.candidate, field, future)
        elif kind == "queue_score":
            object.__setattr__(entry.research_score, "calculated_at", future)
        else:
            field = "evaluated_at" if kind.endswith("evaluated") else "available_at"
            object.__setattr__(entry.hard_screen_results[0], field, future)
    repository = Mock()
    request = _request(context, modules=(ResearchModuleName.FINANCIAL,))
    with pytest.raises(ValueError, match="future"):
        ResearchEngine(modules=(FinancialResearchModule(),), repository=repository).run(request)
    repository.start_run.assert_not_called()
    repository.save_run.assert_not_called()


@pytest.mark.parametrize("field", ["timestamp", "available_at", "instrument"])
def test_daily_selector_rejects_future_dst_fold_without_a_context(field):
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    future = cutoff.replace(fold=1)
    instrument = Instrument("TEST", Market.US, "Synthetic DST fixture", available_at=cutoff)
    timestamp = future if field == "timestamp" else cutoff - timedelta(days=1)
    bar = Bar(instrument, timestamp, future if field != "instrument" else cutoff,
              Decimal(10), Decimal(11), Decimal(9), Decimal(10), Decimal(100),
              source="synthetic")
    if field == "instrument":
        bar = replace(bar, instrument=replace(instrument, available_at=future))
    with pytest.raises(ValueError, match="future"):
        checked_daily_bars((bar,), as_of=cutoff)


def test_daily_revision_order_uses_utc_instants_not_repeated_wall_clock():
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)
    second = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    cutoff = datetime(2026, 11, 1, 2, 0, tzinfo=zone)
    instrument = Instrument("TEST", Market.US, "Synthetic revision fixture")
    bar = Bar(instrument, first - timedelta(days=1), first, Decimal(10), Decimal(11),
              Decimal(9), Decimal(10), Decimal(100), source="synthetic")
    revised = replace(bar, available_at=second, close=Decimal("10.5"))
    for supplied in ((bar, revised), (revised, bar)):
        assert checked_daily_bars(supplied, as_of=cutoff)[0].close == Decimal("10.5")
        suspended = replace(revised, is_suspended=True)
        assert checked_daily_bars((bar, suspended), as_of=cutoff) == ()


def test_daily_repeated_fold_versions_do_not_collide_or_hide_intraday_inputs():
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    cutoff = datetime(2026, 11, 1, 2, 0, tzinfo=zone)
    instrument = Instrument("TEST", Market.US, "Synthetic fold fixture")
    bar = Bar(instrument, first - timedelta(days=1), first, Decimal(10), Decimal(11),
              Decimal(9), Decimal(10), Decimal(100), source="synthetic")
    revised = replace(bar, available_at=second, close=Decimal("10.5"))
    assert checked_daily_bars((bar, revised), as_of=cutoff)[0].close == Decimal("10.5")
    intraday = (replace(bar, timestamp=first), replace(revised, timestamp=second))
    with pytest.raises(ValueError, match="multiple timestamps"):
        checked_daily_bars(intraday, as_of=cutoff)


def test_financial_latest_revision_uses_utc_order_and_preserves_diagnostic_only_state():
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)
    second = datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1)
    cutoff = datetime(2026, 11, 1, 2, 0, tzinfo=zone)
    context = _context(as_of=cutoff, market=Market.US)
    instrument = context.queue_entry.candidate.instrument
    fact = FundamentalFact(instrument, "revenue", date(2026, 9, 30),
                           first - timedelta(days=1), first,
                           Decimal(100), "synthetic")
    revised = replace(fact, available_at=second, value=Decimal(90))
    for facts in ((fact, revised), (revised, fact)):
        assessment = FinancialResearchModule().evaluate(
            replace(context, fundamentals={"revenue": facts}), {})
        assert assessment.features["latest_revenue"] == "90"
        assert assessment.available_at.astimezone(UTC) == second.astimezone(UTC)
        assert assessment.score is None and assessment.confidence.confidence == 0


@pytest.mark.parametrize("module_class", [TechnicalResearchModule, TrendResearchModule,
                                          PatternResearchModule])
def test_direct_research_modules_reject_future_dst_fold_inputs(module_class):
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    context = _context(as_of=cutoff)
    bar = Bar(context.queue_entry.candidate.instrument, cutoff, cutoff,
              Decimal(10), Decimal(11), Decimal(9), Decimal(10), Decimal(100), source="synthetic")
    object.__setattr__(bar, "available_at", cutoff.replace(fold=1))
    object.__setattr__(context, "bars", (bar,))
    with pytest.raises(ValueError, match="future"):
        module_class().evaluate(context, {})


@pytest.mark.parametrize("reversed_chronology", [False, True])
def test_research_evidence_chronology_compares_actual_fold_instants(reversed_chronology):
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    observed, available = first, first.replace(fold=1)
    evidence = _evidence(ResearchModuleName.FINANCIAL, "fixture", as_of=first)[0]
    if reversed_chronology:
        with pytest.raises(ValueError, match="precede observed"):
            replace(evidence, observed_at=available, available_at=observed)
    else:
        accepted = replace(evidence, observed_at=observed, available_at=available)
        assert accepted.available_at.fold == 1


def test_visible_folded_fundamental_versions_do_not_alias_each_other():
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    second = first.replace(fold=1)
    context = _context(as_of=second, market=Market.US)
    instrument = context.queue_entry.candidate.instrument
    fact = FundamentalFact(instrument, "revenue", date(2026, 9, 30),
                           first - timedelta(days=1), first, Decimal(100), "synthetic")
    revised = replace(fact, available_at=second, value=Decimal(90))
    visible = replace(context, fundamentals={"revenue": (fact, revised)})
    assert FinancialResearchModule().evaluate(visible, {}).features["latest_revenue"] == "90"
    conflicting = replace(revised, available_at=second.astimezone(UTC), value=Decimal(80))
    with pytest.raises(ValueError, match="conflicting fundamental versions"):
        replace(context, fundamentals={"revenue": (revised, conflicting)})


def test_actual_cutoff_and_daily_identity_are_independent_of_timezone_spelling():
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1)
    context = _context(as_of=cutoff, market=Market.US)
    instrument = context.queue_entry.candidate.instrument
    bar = Bar(instrument, cutoff - timedelta(days=1), cutoff, Decimal(10), Decimal(11),
              Decimal(9), Decimal(10), Decimal(100), source="synthetic")
    equivalent = replace(bar, timestamp=bar.timestamp.astimezone(UTC),
                         available_at=bar.available_at.astimezone(UTC))
    for as_of in (cutoff, cutoff.astimezone(UTC), cutoff.astimezone(ZoneInfo("Asia/Shanghai"))):
        assert len(research_daily_bars(replace(context, as_of=as_of, bars=(bar, equivalent)))) == 1


@pytest.mark.parametrize("future", [False, True])
def test_research_regime_cutoff_uses_actual_fold_instant(future):
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    context = _context(as_of=first if future else first.replace(fold=1), market=Market.US)
    regime = MarketRegime(Market.US, Regime.BULL, 50, ("Synthetic fixture",),
                          first.replace(fold=1) if future else first, 0,
                          (RegimeContribution("fixture", 0, 1, 0, "Synthetic"),),
                          "synthetic", "fixture")
    if future:
        with pytest.raises(ValueError, match="future Market Regime"):
            replace(context, market_regime=regime)
    else:
        assert replace(context, market_regime=regime).market_regime is regime


def test_daily_availability_cannot_precede_actual_fold_observation():
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    bar = Bar(Instrument("TEST", Market.US, "Synthetic chronology fixture"),
              first.replace(fold=1), first, Decimal(10), Decimal(11), Decimal(9),
              Decimal(10), Decimal(100), source="synthetic")
    with pytest.raises(ValueError, match="precede observation"):
        checked_daily_bars((bar,), as_of=first.replace(hour=2))


@pytest.mark.parametrize("field", ["value", "unit", "source"])
def test_research_context_rejects_ambiguous_same_version_facts(field: str) -> None:
    fact = _financial_fact()
    changes = {"value": Decimal("101"), "unit": "millions", "source": "other"}
    with pytest.raises(ValueError, match="conflicting fundamental versions"):
        _context(fundamentals={"revenue": (fact, replace(fact, **{field: changes[field]}))})


def test_research_context_allows_semantically_identical_repeat_observations() -> None:
    fact = _financial_fact()
    context = _context(fundamentals={
        "revenue": (fact, replace(fact, batch_id="another-batch", value=Decimal("100.00"))),
    })
    assert FinancialResearchModule().evaluate(context, {}).features["latest_revenue"] == "100.00"


def test_semantically_identical_repeats_have_order_independent_diagnostics() -> None:
    fact = _financial_fact()
    repeat = replace(fact, batch_id="repeat", value=Decimal("100.00"))
    left = FinancialResearchModule().evaluate(
        _context(fundamentals={"revenue": (fact, repeat)}), {},
    )
    right = FinancialResearchModule().evaluate(
        _context(fundamentals={"revenue": (repeat, fact)}), {},
    )
    assert left == right


def test_financial_assessment_availability_includes_all_used_facts() -> None:
    fact = _financial_fact()
    evidence = _evidence(
        ResearchModuleName.FINANCIAL, "revenue", as_of=fact.available_at - timedelta(days=1),
    )
    assessment = FinancialResearchModule().evaluate(_context(
        evidence=evidence, fundamentals={"revenue": (fact,)},
    ), {})
    assert assessment.available_at == fact.available_at


@pytest.mark.parametrize("location", ["candidate", "bar", "fundamental"])
def test_research_context_rejects_future_instrument_metadata(location: str) -> None:
    context = _context()
    future_instrument = replace(
        _financial_fact().instrument, available_at=context.as_of + timedelta(days=1),
    )
    changes = {
        "candidate": {"queue_entry": replace(context.queue_entry, candidate=replace(
            context.queue_entry.candidate, instrument=future_instrument,
        ))},
        "bar": {"bars": (replace(_bars(1)[0], instrument=future_instrument),)},
        "fundamental": {"fundamentals": {"revenue": (
            replace(_financial_fact(), instrument=future_instrument),
        )}},
    }[location]
    with pytest.raises(ValueError, match="future instrument metadata"):
        replace(context, **changes)


def test_research_engine_rechecks_mutated_context_before_starting_a_run() -> None:
    context = _context()
    request = _request(context, modules=(ResearchModuleName.FINANCIAL,))
    context.fundamentals["wrong-key"] = (_financial_fact(),)
    repository = Mock()
    engine = ResearchEngine(modules=(FinancialResearchModule(),), repository=repository)
    with pytest.raises(ValueError, match="fundamental metric mismatch"):
        engine.run(request)
    repository.start_run.assert_not_called()
    repository.save_run.assert_not_called()
    repository.fail_run.assert_not_called()


def test_financial_module_rechecks_mutation_when_called_directly() -> None:
    context = _context()
    context.fundamentals["wrong-key"] = (_financial_fact(),)
    with pytest.raises(ValueError, match="fundamental metric mismatch"):
        FinancialResearchModule().evaluate(context, {})


def _financial_snapshot(fact: FundamentalFact, as_of: datetime) -> FinancialInputSnapshot:
    return FinancialInputSnapshot(
        fact.instrument.symbol, fact.instrument.market, as_of, (fact.metric,), "bank", "group",
        (FinancialFactInspection(
            fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic structural receipt only",),
            reporting_scope="group", sector_profile="bank", evidence_id="a" * 64,
            review_artifact_id="b" * 64, filing_artifact_id="c" * 64, filing_sha256="d" * 64,
            source_pages=(17,), source_unit="CNY_million", source_column="group_current_period",
            audit_status="unaudited", statement="income",
        ),),
    )


@pytest.mark.parametrize("with_snapshot", [False, True])
def test_unqualified_facts_cannot_be_scored_by_attaching_high_score_evidence(with_snapshot):
    fact = _financial_fact()
    context = _context(fundamentals={"revenue": (fact,)}, evidence=_evidence_set(
        ResearchModuleName.FINANCIAL, ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
    ))
    if with_snapshot:
        context = replace(context, financial_inputs=_financial_snapshot(fact, context.as_of))
    assessment = FinancialResearchModule().evaluate(context, {})
    assert assessment.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.features["financial_scoring_authorized"] is False
    assert assessment.features["financial_input_binding_present"] is with_snapshot
    assert assessment.features["latest_revenue"] == "100"
    if with_snapshot:
        assert assessment.features["financial_input_hash"] == context.financial_inputs.input_hash
        assert assessment.features["latest_revenue_reporting_scope"] == "group"
        assert assessment.features["latest_revenue_audit_status"] == "unaudited"


@pytest.mark.parametrize("value", ["0", "-10.25", "647301141.75"])
def test_nonfinancial_cash_flow_flows_into_official_module_without_financial_scoring(value):
    fact = replace(_financial_fact(), metric="operating_cash_flow", value=Decimal(value),
                   period_start=date(2025, 1, 1))
    revenue_receipt = _financial_snapshot(_financial_fact(), datetime(2026, 1, 2, tzinfo=UTC))
    cash_receipt = replace(revenue_receipt.inspections[0], fact=fact, sector_profile="nonfinancial",
                           statement="cash_flow", source_unit="CNY")
    snapshot = replace(revenue_receipt, sector_profile="nonfinancial",
                       requested_metrics=("operating_cash_flow",), inspections=(cash_receipt,))
    context = replace(_context(fundamentals={"operating_cash_flow": (fact,)}),
                      financial_inputs=snapshot)
    assessment = FinancialResearchModule().evaluate(context, {})
    assert assessment.features["latest_operating_cash_flow"] == value
    assert assessment.features["latest_operating_cash_flow_source_binding"] == (
        FinancialBindingStatus.SOURCE_BOUND.value)
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert not assessment.features["financial_scoring_authorized"]


@pytest.mark.parametrize("industry", ["bank", "nonfinancial", "unknown", None])
@pytest.mark.parametrize("evidence_kind", ["complete", "unrelated", "mixed", "self_authorized"])
def test_evidence_only_financial_inputs_cannot_bypass_scoring_admission(industry, evidence_kind):
    evidence = _evidence_set(
        ResearchModuleName.FINANCIAL, ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        score=99,
    )
    unrelated = _evidence(ResearchModuleName.FINANCIAL, "unrelated_numeric_annotation", score=100)
    if evidence_kind == "unrelated":
        evidence = unrelated
    elif evidence_kind == "mixed":
        evidence = (*evidence, *unrelated)
    elif evidence_kind == "self_authorized":
        evidence = tuple(replace(item, metadata={
            **item.metadata, "financial_scoring_authorized": True,
            "bank_scoring_policy_qualified": True,
        }) for item in evidence)
    context = _context(evidence=evidence)
    entry = context.queue_entry
    context = replace(context, queue_entry=replace(entry, candidate=replace(
        entry.candidate, instrument=replace(entry.candidate.instrument, industry=industry),
    )))
    assessment = FinancialResearchModule().evaluate(context, {})
    assert assessment.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.features["financial_scoring_authorized"] is False
    assert assessment.features["financial_input_binding_present"] is False
    assert assessment.evidence == evidence
    assert assessment.evidence_ids == tuple(item.evidence_id for item in evidence)


def test_empty_financial_context_also_exposes_explicit_denial_and_version():
    assessment = FinancialResearchModule().evaluate(_context(), {})
    assert assessment.features["financial_scoring_authorized"] is False
    assert assessment.features["financial_input_binding_present"] is False
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.model_version == FINANCIAL_RESEARCH_VERSION


def test_evidence_only_financial_report_cannot_create_investment_score():
    context = _context(evidence=_evidence_set(
        ResearchModuleName.FINANCIAL, ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
        score=99,
    ))
    run = ResearchEngine(modules=(FinancialResearchModule(),)).run(
        _request(context, modules=(ResearchModuleName.FINANCIAL,)),
    )
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    result = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert result.status is InvestmentAssessmentStatus.INCOMPLETE
    assert result.investment_score is None


def test_value_dependency_cannot_hide_unqualified_financial_input_at_report_boundary():
    context = _context(evidence=(
        *_all_policy_evidence(),
        *_evidence_set(ResearchModuleName.FINANCIAL,
                       ("revenue", "profit", "cash_flow", "debt", "roe", "roic"), score=99),
        *_evidence_set(ResearchModuleName.INDUSTRY,
                       ("industry_trend", "industry_heat", "industry_cycle", "relative_strength")),
        *_evidence_set(ResearchModuleName.VALUE, ("survival", "cycle", "valuation", "growth")),
    ))
    run = ResearchEngine(modules=(FinancialResearchModule(), PolicyResearchModule(),
                                  IndustryResearchModule(), ValueResearchModule())).run(
        _request(context, modules=(ResearchModuleName.VALUE,)),
    )
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    financial = next(item for item in run.report.assessments
                     if item.module is ResearchModuleName.FINANCIAL)
    assert financial.score is None
    result = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert result.status is InvestmentAssessmentStatus.INCOMPLETE
    assert result.investment_score is None


@pytest.mark.parametrize("field,value", [
    ("value", Decimal("101")), ("unit", "million"), ("currency", "USD"),
    ("raw_data_hash", "f" * 64), ("batch_id", "unrelated"), ("revision", 9),
])
def test_financial_receipt_binds_the_exact_consumed_fact(field, value):
    fact = _financial_fact()
    context = _context(fundamentals={"revenue": (fact,)})
    context = replace(context, financial_inputs=_financial_snapshot(fact, context.as_of))
    context.fundamentals["revenue"] = (replace(fact, **{field: value}),)
    with pytest.raises(ValueError, match="snapshot does not match"):
        FinancialResearchModule().evaluate(context, {})


def test_financial_receipt_cannot_be_reused_at_another_cutoff_or_without_its_facts():
    fact = _financial_fact()
    context = _context(fundamentals={"revenue": (fact,)})
    receipt = _financial_snapshot(fact, context.as_of)
    with pytest.raises(ValueError, match="snapshot does not match"):
        replace(context, financial_inputs=receipt, as_of=context.as_of + timedelta(days=1))
    with pytest.raises(ValueError, match="snapshot does not match"):
        replace(context, financial_inputs=receipt, fundamentals={})
    assert receipt.input_hash == _financial_snapshot(fact, context.as_of).input_hash
    changed = replace(receipt, inspections=(replace(receipt.inspections[0], source_pages=(18,)),))
    assert changed.input_hash != receipt.input_hash


@pytest.mark.parametrize("change", [
    {"requested_metrics": ("revenue", "revenue")}, {"requested_metrics": ()},
    {"requested_metrics": ["revenue"]}, {"inspections": []},
    {"reporting_scope": "company"}, {"sector_profile": "unknown"},
    {"as_of": datetime(2025, 1, 1, tzinfo=UTC)}, {"model_version": "unreviewed"},
])
def test_financial_snapshot_rejects_ambiguous_mutable_future_or_mismatched_contracts(change):
    fact = _financial_fact()
    receipt = _financial_snapshot(fact, _context().as_of)
    with pytest.raises(ValueError):
        replace(receipt, **change)


def test_source_bound_comparative_changes_remain_descriptive_not_financial_scores():
    fact = replace(_financial_fact(), period_start=date(2025, 1, 1))
    prior = replace(fact, period_end=date(2024, 9, 30), period_start=date(2024, 1, 1),
                    value=Decimal("80"))
    context = _context(fundamentals={"revenue": (fact, prior)})
    receipt = _financial_snapshot(fact, context.as_of)
    comparative = replace(
        receipt.inspections[0], fact=prior, evidence_id="e" * 64,
        source_column="group_prior_year_period", filing_period_end=fact.period_end,
        comparability="as_presented_same_filing", issuer_revision_status="unverified",
    )
    receipt = replace(receipt, inspections=(*receipt.inspections, comparative))
    output = FinancialResearchModule().evaluate(replace(context, financial_inputs=receipt), {})
    assert output.features["revenue_descriptive_comparison_status"] == "descriptive_only"
    assert output.features["revenue_descriptive_comparison_percent"] == "25.0000"
    assert output.score is None and output.confidence.confidence == 0
    assert output.features["financial_scoring_authorized"] is False


@pytest.mark.parametrize("value", ["-1.70", "0", "7.22"])
def test_nonfinancial_roe_reaches_research_without_generic_alias_growth_or_score(value):
    original = _financial_fact()
    fact = replace(original, metric="roe_weighted_ytd_unannualized", value=Decimal(value),
                   unit="percent", currency=None, period_start=date(original.period_end.year, 1, 1))
    context = _context(fundamentals={fact.metric: (fact,)}, evidence=_evidence_set(
        ResearchModuleName.FINANCIAL, ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
    ))
    entry = replace(
        _financial_snapshot(original, context.as_of).inspections[0], fact=fact,
        source_unit="percent", statement="nonfinancial_profitability",
        sector_profile="nonfinancial",
        measurement_basis="ytd_unannualized_ratio", filing_period_end=fact.period_end,
    )
    receipt = FinancialInputSnapshot(
        fact.instrument.symbol, fact.instrument.market, context.as_of, (fact.metric,),
        "nonfinancial", "group", (entry,),
    )
    assessment = FinancialResearchModule().evaluate(replace(context, financial_inputs=receipt), {})
    prefix = "latest_roe_weighted_ytd_unannualized"
    assert assessment.features[prefix] == value
    assert assessment.features[f"{prefix}_unit"] == "percent"
    assert assessment.features[f"{prefix}_measurement_basis"] == "ytd_unannualized_ratio"
    comparison_key = "roe_weighted_ytd_unannualized_descriptive_comparison_percent"
    assert assessment.features[comparison_key] is None
    assert "latest_roe" not in assessment.features and "latest_roic" not in assessment.features
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.features["financial_scoring_authorized"] is False


def test_nonfinancial_cash_inconsistency_is_retained_in_incomplete_official_report():
    original = _financial_fact()
    template = _financial_snapshot(original, _context().as_of).inspections[0]
    values = {"revenue": "200", "total_assets": "100", "total_liabilities": "50",
              "current_liabilities": "40", "monetary_funds": "20", "operating_cash_flow": "61",
              "operating_cash_inflow": "100", "operating_cash_outflow": "40"}
    entries = []
    for index, (metric, value) in enumerate(sorted(values.items())):
        statement = ("income" if metric == "revenue" else "cash_flow"
                     if metric.startswith("operating_cash_") else "balance")
        fact = replace(original, metric=metric, value=Decimal(value),
                       period_start=(None if statement == "balance"
                                     else date(original.period_end.year, 1, 1)))
        entries.append(replace(
            template, fact=fact, evidence_id=f"{index:064x}", source_unit="CNY",
            sector_profile="nonfinancial", statement=statement, filing_period_end=fact.period_end,
        ))
    context = _context(fundamentals={entry.fact.metric: (entry.fact,) for entry in entries})
    receipt = FinancialInputSnapshot(
        original.instrument.symbol, original.instrument.market, context.as_of,
        tuple(sorted(values)), "nonfinancial", "group", tuple(entries),
    )
    context = replace(context, financial_inputs=receipt)
    run = ResearchEngine(modules=(FinancialResearchModule(),)).run(
        _request(context, modules=(ResearchModuleName.FINANCIAL,)))
    (financial,) = run.report.assessments
    prefix = "nonfinancial_operating_cash_reconciliation_residual"
    assert financial.features[f"{prefix}_status"] == "inconsistent"
    assert financial.features[f"{prefix}_value"] == "-1"
    cash_ratio = "nonfinancial_operating_cash_flow_to_revenue_percent"
    assert financial.features[f"{cash_ratio}_value"] is None
    assert financial.features[f"{cash_ratio}_status"] == "inconsistent"
    assert financial.score is None and financial.confidence.confidence == 0
    assert any("arithmetic inconsistency" in risk for risk in financial.risks)
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    result = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert result.status is InvestmentAssessmentStatus.INCOMPLETE
    assert result.investment_score is None


def test_valuation_denominators_reach_official_report_but_cannot_authorize_a_score():
    original = _financial_fact()
    context = _context()
    template = _financial_snapshot(original, context.as_of).inspections[0]
    entries = []
    values = {"revenue": "200", "profit_attributable_to_parent": "-10",
              "equity_attributable_to_parent": "80"}
    for metric, value in sorted(values.items()):
        balance = metric == "equity_attributable_to_parent"
        fact = replace(original, metric=metric, value=Decimal(value),
                       period_start=None if balance else date(original.period_end.year, 1, 1))
        entries.append(replace(template, fact=fact, sector_profile="nonfinancial",
                               source_unit="CNY", statement="balance" if balance else "income",
                               filing_period_end=fact.period_end))
    receipt = FinancialInputSnapshot(
        original.instrument.symbol, original.instrument.market, context.as_of,
        tuple(sorted(values)), "nonfinancial", "group", tuple(entries),
    )
    context = replace(context, financial_inputs=receipt,
                      fundamentals={entry.fact.metric: (entry.fact,) for entry in entries})
    run = ResearchEngine(modules=(FinancialResearchModule(),)).run(
        _request(context, modules=(ResearchModuleName.FINANCIAL,)))
    (assessment,) = run.report.assessments
    assert assessment.features["valuation_parent_book_basis_status"] == "observed_unqualified"
    assert assessment.features["valuation_annual_earnings_basis_status"] == (
        "partial_year_not_annual_or_ttm")
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    result = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert result.status is InvestmentAssessmentStatus.INCOMPLETE
    assert result.investment_score is None


def test_reviewed_trailing_arithmetic_reaches_report_without_creating_investment_score():
    original = _financial_fact()
    context = _context()
    template = _financial_snapshot(original, context.as_of).inspections[0]
    end = original.period_end
    roles = ((end, "-10", False), (date(end.year - 1, 12, 31), "100", False),
             (date(end.year - 1, end.month, end.day), "30", True))
    entries = []
    for index, (period, value, comparative) in enumerate(roles):
        fact = replace(original, metric="profit_attributable_to_parent", period_end=period,
                       period_start=date(period.year, 1, 1), value=Decimal(value))
        entries.append(replace(
            template, fact=fact, evidence_id=f"{index:064x}", sector_profile="nonfinancial",
            filing_period_end=end if comparative else period,
            source_column="group_prior_year_period" if comparative else "group_current_period",
            comparability="as_presented_same_filing" if comparative else None,
            issuer_revision_status="unverified" if comparative else None,
        ))
    review = TrailingEditionReview(
        "profit_attributable_to_parent", *(trailing_input_hash(e) for e in entries),
        context.as_of, "Synthetic reviewer", ("Not independently qualified",),
    )
    snapshot = FinancialInputSnapshot(
        original.instrument.symbol, original.instrument.market, context.as_of,
        ("profit_attributable_to_parent",), "nonfinancial", "group", tuple(entries),
    )
    context = replace(context, financial_inputs=snapshot,
                      fundamentals={"profit_attributable_to_parent": tuple(
                          e.fact for e in entries)})
    module = FinancialResearchModule(trailing_edition_reviews=(review,))
    run = ResearchEngine(modules=(module,)).run(
        _request(context, modules=(ResearchModuleName.FINANCIAL,)))
    (assessment,) = run.report.assessments
    prefix = "trailing_profit_attributable_to_parent"
    assert assessment.features[f"{prefix}_value"] == "60"
    assert assessment.features[f"{prefix}_status"] == "derived_as_reported_unqualified"
    assert assessment.features[f"{prefix}_review_hash"] == review.review_hash
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    result = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert result.investment_score is None
    assert result.status is InvestmentAssessmentStatus.INCOMPLETE


def _market_value_snapshot(context):
    symbol = context.queue_entry.candidate.instrument.symbol
    body = json.dumps({"rc": 0, "data": {
        "f57": symbol, "f43": 20, "f84": 20000, "f85": 10000,
        "f116": 400000, "f117": 200000,
        "f86": int((context.as_of - timedelta(minutes=1)).timestamp()),
    }}).encode()
    adapter = EastmoneyMarketValueAdapter(
        download=lambda _: QuoteHttpCapture(200, body), clock=lambda: context.as_of)
    record = adapter.fetch(ProviderDatasetRequest(
        MARKET_VALUE_DATASET, Market.CHINA_A, symbol, context.as_of)).records[0]
    return MarketValueInputSnapshot(symbol, Market.CHINA_A, context.as_of, (
        MarketValueInspection(record, True, ("Synthetic structural receipt only",),
                              market_value_record_hash(record)),))


@pytest.mark.parametrize("configured", [False, True])
def test_market_value_diagnostics_reach_official_report_but_cannot_qualify_a_score(configured):
    context = _context()
    at = context.as_of - timedelta(minutes=1)
    bar = Bar(context.queue_entry.candidate.instrument, at, at, Decimal("20"), Decimal("21"),
              Decimal("19"), Decimal("20"), Decimal("100"), source="Synthetic")
    context = replace(context, bars=(bar,), market_value_inputs=_market_value_snapshot(context))
    policy = MarketValueMatchingPolicy(60, 60, 60) if configured else MarketValueMatchingPolicy()
    run = ResearchEngine(modules=(FinancialResearchModule(market_value_policy=policy),)).run(
        _request(context, modules=(ResearchModuleName.FINANCIAL,)))
    (assessment,) = run.report.assessments
    assert assessment.features["market_value_status"] == "observed_unqualified"
    assert assessment.features["market_value_freshness"] == (
        "WITHIN_CONFIGURED_LIMIT" if configured else "UNASSESSED")
    assert assessment.features["market_value_input_hash"] == context.market_value_inputs.input_hash
    assert assessment.features["market_value_policy_hash"] == policy.policy_hash
    assert not assessment.features["market_value_valuation_authorized"]
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.available_at == context.as_of
    assert run.report.status is ResearchRunStatus.INCOMPLETE
    investment = InvestmentAssessmentBuilder().build(run.report, assessed_at=context.as_of)
    assert investment.status is InvestmentAssessmentStatus.INCOMPLETE
    assert investment.investment_score is None


@pytest.mark.parametrize("change", ["cutoff", "symbol", "mutation", "fund"])
def test_official_context_rejects_wrong_market_value_snapshot_before_evaluation(change):
    context = _context()
    snapshot = _market_value_snapshot(context)
    if change == "cutoff":
        snapshot = replace(snapshot, as_of=context.as_of + timedelta(seconds=1))
    elif change == "symbol":
        snapshot = MarketValueInputSnapshot("000063", Market.CHINA_A, context.as_of, ())
    elif change == "fund":
        instrument = replace(context.queue_entry.candidate.instrument, asset_type=AssetType.ETF)
        context = replace(context, queue_entry=replace(context.queue_entry, candidate=replace(
            context.queue_entry.candidate, instrument=instrument)))
    else:
        snapshot.inspections[0].record.payload["price"] = "999"
    with pytest.raises(ValueError):
        replace(context, market_value_inputs=snapshot)


def test_bank_ratio_research_exposes_basis_and_percent_without_scoring_or_growth():
    original = _financial_fact()
    fact = replace(original, metric="provision_coverage_ratio", value=Decimal("204.79"),
                   unit="percent", currency=None, period_start=None)
    context = _context(fundamentals={fact.metric: (fact,)}, evidence=_evidence_set(
        ResearchModuleName.FINANCIAL, ("revenue", "profit", "cash_flow", "debt", "roe", "roic"),
    ))
    entry = replace(
        _financial_snapshot(original, context.as_of).inspections[0], fact=fact,
        source_unit="percent", statement="bank_asset_quality",
        measurement_basis="period_end_ratio", filing_period_end=fact.period_end,
    )
    receipt = FinancialInputSnapshot(
        fact.instrument.symbol, fact.instrument.market, context.as_of, (fact.metric,),
        "bank", "group", (entry,),
    )
    assessment = FinancialResearchModule().evaluate(replace(context, financial_inputs=receipt), {})
    assert assessment.features["latest_provision_coverage_ratio"] == "204.79"
    assert assessment.features["latest_provision_coverage_ratio_unit"] == "percent"
    assert assessment.features["latest_provision_coverage_ratio_measurement_basis"] == (
        "period_end_ratio")
    assert assessment.features["provision_coverage_ratio_descriptive_comparison_percent"] is None
    assert assessment.score is None and assessment.confidence.confidence == 0
    assert assessment.features["financial_scoring_authorized"] is False
    for change in ({"measurement_basis": "annualized"}, {"source_unit": "fraction"},
                   {"filing_period_end": date(2024, 12, 31)}):
        with pytest.raises(ValueError, match="bank ratio"):
            replace(entry, **change)


def test_comparison_rejects_an_unsupported_calendar_without_constructing_year_zero():
    fact = replace(_financial_fact(), period_start=date(1, 1, 1), period_end=date(1, 3, 31))
    receipt = _financial_snapshot(fact, _context().as_of)
    (comparison,) = financial_comparisons(receipt)
    assert comparison.status is FinancialComparisonStatus.INCOMPATIBLE
    assert comparison.change_percent is None


@pytest.mark.parametrize("kind", ["admission", "candidate", "score", "hard_screen"])
def test_research_context_rejects_future_queue_inputs(kind: str) -> None:
    context = _context()
    entry = context.queue_entry
    future = context.as_of + timedelta(days=1)
    changes = {
        "admission": {"admitted_at": future},
        "candidate": {"candidate": replace(entry.candidate, available_at=future)},
        "score": {"research_score": replace(entry.research_score, calculated_at=future)},
        "hard_screen": {"hard_screen_results": (
            replace(entry.hard_screen_results[0], evaluated_at=future, available_at=future),
        )},
    }[kind]
    with pytest.raises(ValueError, match="future queue data"):
        replace(context, queue_entry=replace(entry, **changes))


def _supportive_assessment(
    module: ResearchModuleName,
    context: ResearchContext,
):
    from tong_quant.research.base import evidence_driven_assessment

    return evidence_driven_assessment(
        module=module,
        context=_context(evidence=_evidence(module, "score")),
        required_names=frozenset({"score"}),
        model_version="test",
    )


def _request(
    context: ResearchContext,
    *,
    modules: tuple[ResearchModuleName, ...],
) -> ResearchRequest:
    return ResearchRequest(
        context=context,
        modules=modules,
        thesis="Industry demand and company economics may improve",
        counter_thesis="Policy transmission or company execution may disappoint",
        invalidation_conditions=(_invalidation(),),
        unresolved_questions=("Can margins remain durable?",),
    )


def _invalidation() -> ThesisInvalidationCondition:
    return ThesisInvalidationCondition(
        condition_id="revenue-growth",
        description="Revenue growth falls below 5 percent",
        metric="revenue_growth",
        operator="<",
        threshold=5,
        observation_window="two consecutive quarters",
        rationale="The thesis depends on durable demand growth",
    )


def _context(
    *,
    as_of: datetime | None = None,
    market: Market = Market.CHINA_A,
    bars: tuple[Bar, ...] = (),
    evidence: tuple[ResearchEvidence, ...] = (),
    fundamentals: dict[str, tuple[FundamentalFact, ...]] | None = None,
) -> ResearchContext:
    timestamp = as_of or datetime(2026, 1, 2, tzinfo=UTC)
    return ResearchContext(
        queue_id="queue-1",
        queue_entry=_queue_entry(timestamp, market),
        as_of=timestamp,
        bars=bars,
        fundamentals=fundamentals or {},
        evidence=evidence,
    )


def _queue_entry(as_of: datetime, market: Market) -> ResearchQueueEntry:
    candidate = OpportunityCandidate(
        instrument=_instrument(market),
        discovery_source="discovery.policy",
        discovered_at=as_of,
        available_at=as_of,
        thesis="Potential opportunity",
        evidence=("Published evidence",),
        urgency_score=70,
        confidence_score=75,
    )
    component = ScoreComponent(
        name="industry",
        score=70,
        confidence=80,
        weight=1,
        contribution=70,
        reasons=("Industry evidence",),
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


def _instrument(market: Market) -> Instrument:
    symbol = "600000" if market is Market.CHINA_A else "TEST"
    return Instrument(symbol, market, "Example")


def _evidence(
    module: ResearchModuleName,
    name: str,
    *,
    score: float = 70,
    as_of: datetime | None = None,
) -> tuple[ResearchEvidence, ...]:
    timestamp = as_of or datetime(2026, 1, 2, tzinfo=UTC)
    return (
        ResearchEvidence(
            evidence_id=f"{module.value}:{name}",
            module=module,
            name=name,
            value=score,
            observed_at=timestamp,
            available_at=timestamp,
            source="test",
            quality=EvidenceQuality.PRIMARY,
            metadata={"summary": f"{name} summary", "finding": f"{name} reviewed"},
        ),
    )


def _evidence_set(
    module: ResearchModuleName,
    names: tuple[str, ...],
    *,
    score: float = 70,
) -> tuple[ResearchEvidence, ...]:
    return tuple(item for name in names for item in _evidence(module, name, score=score))


def _all_policy_evidence() -> tuple[ResearchEvidence, ...]:
    return _evidence_set(
        ResearchModuleName.POLICY,
        (
            "regulatory_environment",
            "industrial_policy",
            "fiscal_policy",
            "monetary_policy",
            "geopolitical_factors",
        ),
    )


@pytest.mark.parametrize("module_class", [TechnicalResearchModule, TrendResearchModule,
                                          PatternResearchModule])
def test_duplicate_daily_rows_cannot_fill_warmup(module_class: type) -> None:
    context = _context(
        bars=_bars(1) * 260,
        evidence=_evidence_set(
            ResearchModuleName.TREND,
            ("market_sentiment_confirmation", "industry_heat_confirmation"),
        ) + _evidence_set(
            ResearchModuleName.PATTERN,
            tuple(PATTERN_FIELDS - {"high_volume_long_upper_shadow"}),
        ),
    )
    assessment = module_class().evaluate(context, {})
    assert assessment.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert assessment.score is None


def test_daily_revisions_select_latest_visible_without_mutating_input() -> None:
    bars = _bars(3)
    revised = replace(bars[-1], available_at=bars[-1].available_at + timedelta(days=1),
                      close=bars[-1].close + Decimal("0.01"))
    captured_again = replace(revised, ingested_at=revised.available_at + timedelta(days=1))
    supplied = (revised, bars[1], bars[0], bars[-1], captured_again)
    context = _context(bars=supplied)
    expected = (*bars[:-1], revised)
    assert research_daily_bars(context) == expected
    reordered = research_daily_bars(replace(context, bars=tuple(reversed(supplied))))
    assert reordered[-1].close == revised.close
    assert context.bars == supplied
    earlier = _context(as_of=bars[-1].available_at, bars=bars)
    assert research_daily_bars(earlier)[-1] == bars[-1]


def test_latest_suspension_revision_does_not_resurrect_old_price() -> None:
    bars = _bars(3)
    suspended = replace(bars[-1], available_at=bars[-1].available_at + timedelta(days=1),
                        is_suspended=True)
    assert research_daily_bars(_context(bars=(*bars, suspended))) == bars[:-1]


@pytest.mark.parametrize("module_class", [TechnicalResearchModule, TrendResearchModule,
                                          PatternResearchModule])
@pytest.mark.parametrize("shape", ["revision", "new_observation", "historical", "active_revision"])
def test_current_research_never_scores_pre_suspension_fallback(module_class, shape):
    bars = _bars(260)
    trend = _evidence_set(ResearchModuleName.TREND,
                         ("market_sentiment_confirmation", "industry_heat_confirmation"), score=90)
    patterns = _evidence_set(ResearchModuleName.PATTERN,
                            tuple(PATTERN_FIELDS - {"high_volume_long_upper_shadow"}), score=90)
    patterns = tuple(replace(item, metadata={"rising_stocks": 4000})
                     if item.name == "rising_stocks_environment" else item for item in patterns)
    current = bars[-2] if shape == "historical" else bars[-1]
    suspended = replace(current, is_suspended=True,
                        available_at=current.available_at + timedelta(days=1))
    if shape == "new_observation":
        suspended = replace(suspended, timestamp=suspended.timestamp + timedelta(days=1))
    supplied = (*bars, suspended)
    if shape == "active_revision":
        supplied = (*supplied, replace(suspended, is_suspended=False,
                                       available_at=suspended.available_at + timedelta(days=1)))
    context = _context(bars=supplied, evidence=(*trend, *patterns))
    result = module_class().evaluate(context, {})
    if shape in {"revision", "new_observation"}:
        assert result.score is None and result.conclusion is ResearchConclusion.INSUFFICIENT_DATA
        assert any("no pre-suspension fallback" in item for item in result.limitations)
        assert research_daily_bars(context, require_latest_active=True) == ()
    else:
        assert result.conclusion is not ResearchConclusion.INSUFFICIENT_DATA
        baseline = module_class().evaluate(replace(context, bars=research_daily_bars(context)), {})
        assert (result.score, result.conclusion) == (baseline.score, baseline.conclusion)
        assert research_daily_bars(context, require_latest_active=True)[-1].is_suspended is False
    assert suspended in context.bars


@pytest.mark.parametrize("value", [1, "yes", None])
def test_current_bar_requirement_cannot_be_truthy_or_implicitly_disabled(value):
    with pytest.raises(ValueError, match="must be boolean"):
        research_daily_bars(_context(bars=_bars(3)), require_latest_active=value)


@pytest.mark.parametrize("module_class", [TechnicalResearchModule, TrendResearchModule,
                                          PatternResearchModule])
def test_direct_modules_reject_conflicting_daily_versions(module_class: type) -> None:
    bar = _bars(1)[0]
    changed = replace(bar, close=bar.close + Decimal("0.01"))
    with pytest.raises(ValueError, match="conflicting bar versions"):
        module_class().evaluate(_context(bars=(bar, changed)), {})


@pytest.mark.parametrize("module_class", [TechnicalResearchModule, TrendResearchModule,
                                          PatternResearchModule])
def test_direct_modules_recheck_future_bars(module_class: type) -> None:
    context = _context(bars=_bars(1))
    future = replace(context.bars[0], timestamp=context.as_of + timedelta(days=1),
                     available_at=context.as_of + timedelta(days=1))
    object.__setattr__(context, "bars", (future,))
    with pytest.raises(ValueError, match="future data"):
        module_class().evaluate(context, {})


@pytest.mark.parametrize("kind", ["mixed_source", "intraday", "adjusted", "nonfinite", "zero"])
def test_ambiguous_daily_series_are_rejected(kind: str) -> None:
    bars = _bars(2)
    if kind == "mixed_source":
        supplied = (bars[0], replace(bars[1], source="other"))
    elif kind == "intraday":
        second = replace(bars[0], timestamp=bars[0].timestamp + timedelta(hours=1),
                         available_at=bars[0].available_at + timedelta(hours=1))
        supplied = (bars[0], second)
    elif kind == "adjusted":
        supplied = (replace(bars[0], adjustment=Adjustment.FORWARD),)
    elif kind == "nonfinite":
        supplied = (replace(bars[0], volume=Decimal("Infinity")),)
    else:
        supplied = (replace(bars[0], open=Decimal(0), low=Decimal(0), close=Decimal(0)),)
    with pytest.raises(ValueError):
        research_daily_bars(_context(bars=supplied))


def test_technical_return_uses_five_complete_observation_intervals() -> None:
    bars = _bars(260)
    module = TechnicalResearchModule()
    first = module.evaluate(_context(bars=bars), {})
    shuffled = module.evaluate(_context(bars=tuple(reversed(bars))), {})
    assert first.features == shuffled.features
    assert first.features["weekly_return"] == round(float(bars[-1].close / bars[-6].close - 1), 6)
    assert first.features["monthly_return"] == round(float(bars[-1].close / bars[-22].close - 1), 6)
    expected_long_return = round(float(bars[-1].close / bars[-201].close - 1), 6)
    assert first.features["long_term_return"] == expected_long_return
    assert first.features["weekly_trend_basis"] == "5_OBSERVATIONS_PROXY_NOT_CALENDAR_WEEK"
    assert first.features["monthly_trend_basis"] == "21_OBSERVATIONS_PROXY_NOT_CALENDAR_MONTH"
    assert first.features["position_52_week_basis"] == "252_OBSERVATIONS_PROXY"
    assert first.features["calendar_period_scoring_admitted"] is False
    assert first.model_version == "technical-v0.5.5-explicit-proxy-basis"


def test_technical_warmup_includes_every_configured_window() -> None:
    module = TechnicalResearchModule(short_ma_period=300)
    assessment = module.evaluate(_context(bars=_bars(260)), {})
    assert assessment.conclusion is ResearchConclusion.INSUFFICIENT_DATA
    assert assessment.features["weekly_trend_basis"] == "5_OBSERVATIONS_PROXY_NOT_CALENDAR_WEEK"
    assert assessment.features["calendar_period_scoring_admitted"] is False


@pytest.mark.parametrize("module_class,parameter", [
    (TechnicalResearchModule, "short_ma_period"),
    (TechnicalResearchModule, "long_ma_period"),
    (TechnicalResearchModule, "position_period"),
    (TrendResearchModule, "breakout_period"),
    (TrendResearchModule, "volume_period"),
    (TrendResearchModule, "atr_period"),
    (PatternResearchModule, "volume_period"),
])
@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_research_periods_fail_before_calculation(
    module_class: type, parameter: str, value: object,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        module_class(**{parameter: value})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 101, True])
def test_invalid_trend_thresholds_fail_before_calculation(value: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        TrendResearchModule(confirmation_threshold=value)


def _bars(count: int, *, market: Market = Market.CHINA_A) -> tuple[Bar, ...]:
    instrument = _instrument(market)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    bars = []
    for index in range(count):
        timestamp = start + timedelta(days=index)
        close = Decimal("10") + Decimal(index) / Decimal("100")
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=timestamp,
                open=close - Decimal("0.05"),
                high=close + Decimal("0.10"),
                low=close - Decimal("0.10"),
                close=close,
                volume=Decimal("1000") + index,
                source="test",
            )
        )
    return tuple(bars)
