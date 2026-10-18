import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    EvidenceQuality,
    Market,
    ResearchModuleName,
    ScoreType,
)
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.engine import ResearchEngine
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.models import (
    ResearchContext,
    ResearchEvidence,
    ResearchRequest,
    ThesisInvalidationCondition,
)
from tong_quant.research.policy import PolicyResearchModule
from tong_quant.research.repository import SQLiteResearchRepository
from tong_quant.screening.models import (
    CompositeScore,
    HardScreenResult,
    OpportunityCandidate,
    ResearchQueueEntry,
    ScoreComponent,
)
from tong_quant.version import FINANCIAL_RESEARCH_VERSION

pytestmark = pytest.mark.integration


def test_research_queue_to_report_persistence(tmp_path: Path) -> None:
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

    with pytest.raises(ValueError, match="already claimed"):
        engine.run(request)


def test_financial_input_integrity_through_database_and_report_persistence(tmp_path: Path) -> None:
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

    run = engine.run(request)
    rows = store.research_assessments_for_report(run.report.report_id)
    assert len(rows) == 1
    assert rows[0]["model_version"] == FINANCIAL_RESEARCH_VERSION
    assert rows[0]["score"] is None
    assert json.loads(rows[0]["features_json"])["latest_revenue"] == "90"
    assert run.report.status.value == "incomplete"
    assert store.table_count("fundamental_facts") == 2


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
