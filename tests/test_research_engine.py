from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import permutations
from unittest.mock import Mock

import pytest

from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    EvidenceQuality,
    Market,
    ResearchConclusion,
    ResearchModuleName,
    ScoreType,
    SignalAction,
)
from tong_quant.domain.models import Bar, FundamentalFact, Instrument
from tong_quant.research.bar_inputs import research_daily_bars
from tong_quant.research.confidence import combine_confidence
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.industry import IndustryResearchModule
from tong_quant.research.models import (
    ResearchContext,
    ResearchEvidence,
    ResearchRequest,
    ThesisInvalidationCondition,
)
from tong_quant.research.pattern import PATTERN_FIELDS, PatternResearchModule
from tong_quant.research.policy import PolicyResearchModule
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
    assert confidence.method == "weighted_geometric_with_weakest_link_cap"


def test_policy_assessment_contains_all_policy_dimensions() -> None:
    context = _context(evidence=_all_policy_evidence())
    output = PolicyResearchModule().evaluate(context, {})

    assert output.assessment.module is ResearchModuleName.POLICY
    assert output.regulatory_environment == "regulatory_environment summary"
    assert output.geopolitical_factors == "geopolitical_factors summary"
    assert output.assessment.confidence.data_completeness == 100


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


def test_research_context_rejects_future_bar_time_with_backdated_availability() -> None:
    as_of = datetime(2026, 1, 2, tzinfo=UTC)
    future = as_of + timedelta(days=1)
    with pytest.raises(ValueError, match="observation timestamp"):
        replace(_bars(1)[0], timestamp=future, available_at=as_of)
    bar = replace(_bars(1)[0], timestamp=future, available_at=future)
    with pytest.raises(ValueError, match="future data"):
        _context(as_of=as_of, bars=(bar,))


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


def test_technical_warmup_includes_every_configured_window() -> None:
    module = TechnicalResearchModule(short_ma_period=300)
    assessment = module.evaluate(_context(bars=_bars(260)), {})
    assert assessment.conclusion is ResearchConclusion.INSUFFICIENT_DATA


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
