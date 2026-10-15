import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.config.settings import load_settings
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    InvestmentAssessmentStatus,
    Market,
    PortfolioAssetCategory,
    PortfolioProposalStatus,
    ResearchRunStatus,
    ValidationStatus,
)
from tong_quant.domain.models import Instrument
from tong_quant.portfolio import (
    PortfolioCandidate,
    PortfolioConstructionConfig,
    PortfolioEvidenceGate,
    PortfolioEvidencePolicy,
    PortfolioProposalEngine,
    PositionProposal,
    SQLitePortfolioRepository,
)
from tong_quant.version import PORTFOLIO_MODEL_VERSION, RISK_MODEL_VERSION


def test_portfolio_proposal_consumes_investment_score_candidates_only() -> None:
    candidate = _candidate("600000", "score-1", 88, 82)

    proposal = PortfolioProposalEngine(
        PortfolioConstructionConfig(maximum_single_position_weight=0.20)
    ).build((candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC))

    assert proposal.status in {
        PortfolioProposalStatus.PROPOSED,
        PortfolioProposalStatus.CONDITIONAL,
        PortfolioProposalStatus.REJECTED,
    }
    assert proposal.status is not PortfolioProposalStatus.PROPOSED
    assert proposal.metadata["artifact_type"] == "research_artifact"
    assert "Research artifact only" in proposal.limitations
    assert proposal.cash_weight >= 0.05
    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.risk_budget.total_risk_budget == 0.12
    assert len(proposal.risk_assessment.scenario_results) == 4
    assert not hasattr(proposal, "order")


def test_candidate_without_investment_score_is_rejected() -> None:
    with pytest.raises(ValueError, match="InvestmentScore"):
        PortfolioCandidate(
            instrument=_instrument("600000"),
            research_report_id="research-1",
            investment_assessment_id="assessment-1",
            investment_score_id="",
            validation_report_id="validation-1",
            score=80,
            confidence=80,
            assessment_status=InvestmentAssessmentStatus.COMPLETED,
            validation_status=ValidationStatus.RELIABLE,
            validation_generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            validation_configuration_hash="a" * 64,
            validation_model_version="validation-test-v1",
            expected_role="value",
            sector="Banks",
            country="China",
            theme="Value",
            volatility=0.2,
            liquidity_score=80,
            average_correlation=0.3,
            max_drawdown=0.2,
            reasons=("scored",),
        )


def test_candidate_requires_typed_validation_status() -> None:
    with pytest.raises(ValueError, match="validation status must be typed"):
        replace(
            _candidate("600000", "score-1", 88, 82),
            validation_status="reliable",  # type: ignore[arg-type]
        )


def test_duplicate_instrument_or_score_is_rejected() -> None:
    first = _candidate("600000", "score-1", 88, 82)
    engine = PortfolioProposalEngine()

    with pytest.raises(ValueError, match="unique scores and instruments"):
        engine.build((first, first), as_of=datetime(2026, 1, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="unique scores and instruments"):
        engine.build(
            (first, replace(first, investment_score_id="score-2")),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_low_confidence_high_score_remains_constrained() -> None:
    candidate = _candidate(
        "600000",
        "score-low-confidence",
        98,
        35,
        status=InvestmentAssessmentStatus.LOW_CONFIDENCE,
    )

    proposal = PortfolioProposalEngine().build(
        (candidate,),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )
    equity = [position for position in proposal.positions if position.instrument is not None][0]

    assert "low_confidence_investment_score" in equity.risk_flags
    assert equity.confidence == 35


def test_risk_assessment_flags_concentration_liquidity_and_stress() -> None:
    candidates = (
        _candidate("600000", "score-1", 90, 80, liquidity=40, volatility=0.35),
        _candidate("600001", "score-2", 85, 78, liquidity=45, volatility=0.32),
    )

    proposal = PortfolioProposalEngine(
        PortfolioConstructionConfig(
            maximum_single_position_weight=0.60,
            target_volatility=0.50,
            minimum_cash_weight=0.05,
        )
    ).build(candidates, as_of=datetime(2026, 1, 2, tzinfo=UTC))

    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.liquidity_risk > 0
    assert proposal.risk_assessment.sector_exposure.breached
    assert any(
        result.scenario.name == "single stock -30%"
        for result in proposal.risk_assessment.scenario_results
    )
    assert proposal.risk_assessment.required_adjustments
    assert any(
        "per_sector_risk_budget exceeded" in adjustment
        for adjustment in proposal.risk_assessment.required_adjustments
    )
    assert any(
        "per_theme_risk_budget exceeded" in adjustment
        for adjustment in proposal.risk_assessment.required_adjustments
    )


def test_cash_buffer_does_not_breach_sector_country_or_theme_caps() -> None:
    candidate = replace(
        _candidate("600000", "score-1", 88, 82),
        validation_status=ValidationStatus.RELIABLE,
    )
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )

    assert proposal.cash_weight == 0.9
    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.sector_exposure.exposures["cash"] == 0.9
    assert not proposal.risk_assessment.sector_exposure.breached
    assert not proposal.risk_assessment.country_exposure.breached
    assert not proposal.risk_assessment.theme_exposure.breached
    assert proposal.status is PortfolioProposalStatus.PROPOSED


def test_candidate_exposure_classifications_reach_risk_without_substitution() -> None:
    candidates = tuple(
        replace(
            _candidate(str(600000 + index), f"score-{index}", 80, 80),
            instrument=replace(_instrument(str(600000 + index)), industry=f"old-{index}"),
            sector="Semiconductors", country="China", theme="AI",
            expected_role="long-term core",
        )
        for index in range(2)
    )
    proposal = PortfolioProposalEngine(
        PortfolioConstructionConfig(maximum_single_position_weight=0.60)
    ).build(candidates, as_of=datetime(2026, 1, 2, tzinfo=UTC))

    risk = proposal.risk_assessment
    assert risk is not None
    assert risk.sector_exposure.breached
    for dimension, breakdown, expected in (
        ("sector", risk.sector_exposure, "Semiconductors"),
        ("country", risk.country_exposure, "China"),
        ("theme", risk.theme_exposure, "AI"),
    ):
        assert breakdown.exposures[expected] > 0.6
        assert proposal.exposure_summary[dimension] == breakdown.exposures
        assert set(breakdown.exposures) == {expected, "cash"}


def test_portfolio_factory_applies_effective_risk_configuration() -> None:
    settings = load_settings(Path("config/default.toml"))
    settings = replace(
        settings,
        portfolio=replace(settings.portfolio, minimum_cash_weight=0.25),
        risk=replace(settings.risk, max_portfolio_drawdown=0.08, minimum_liquidity_score=0),
    )

    engine = PortfolioProposalEngine.from_settings(settings)
    proposal = engine.build(
        (_candidate("600000", "score-1", 88, 82, liquidity=0),),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert engine.config.minimum_cash_weight == 0.25
    assert engine.risk_engine.config.maximum_drawdown == 0.08
    assert proposal.risk_assessment is not None
    assert proposal.risk_assessment.liquidity_risk == 0


def test_fund_category_is_reserved_but_not_constructed_by_engine() -> None:
    fund_position = PositionProposal(
        instrument=_instrument("510300"),
        asset_category=PortfolioAssetCategory.FUND,
        proposed_weight=0.10,
        min_weight=0.0,
        max_weight=0.20,
        confidence=60,
        liquidity_score=80,
        volatility_estimate=0.12,
        expected_role="reserved fund exposure",
        reasons=("Fund category is reserved for future architecture",),
    )

    assert fund_position.asset_category is PortfolioAssetCategory.FUND


def test_portfolio_repository_persists_research_artifacts(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(store, "600000", "score-1", 88, 82)
    proposal = PortfolioProposalEngine().build(
        (candidate,),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )

    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)

    assert store.table_count("portfolio_proposals") == 1
    assert store.table_count("portfolio_evidence_references") == 1
    assert store.table_count("position_proposals") == 2
    assert store.table_count("risk_assessments") == 1
    assert store.table_count("portfolio_exposures") == 3
    assert store.table_count("portfolio_constraints") == 4

    loaded = repository.get_proposal(proposal.proposal_id)
    assert loaded is not None
    assert loaded.proposal_id == proposal.proposal_id
    assert loaded.evidence_references == proposal.evidence_references
    assert len(loaded.positions) == 2
    assert loaded.risk_assessment is not None
    assert proposal.risk_assessment is not None
    assert loaded.risk_assessment.assessment_id == proposal.risk_assessment.assessment_id
    assert len(loaded.risk_assessment.scenario_results) == 4
    assert repository.get_exposures(proposal.proposal_id)
    assert len(repository.get_constraints(proposal.proposal_id)) == 4


def test_portfolio_repository_rejects_missing_lineage_atomically(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    proposal = PortfolioProposalEngine().build(
        (_candidate("600000", "score-1", 88, 82),),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="missing or mismatched"):
        SQLitePortfolioRepository(store).save_proposal(proposal)

    assert store.table_count("portfolio_proposals") == 0
    assert store.table_count("portfolio_evidence_references") == 0
    assert store.table_count("position_proposals") == 0


def test_portfolio_repository_rejects_replacing_proposal(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(store, "600000", "score-1", 88, 82)
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)

    with pytest.raises(ValueError, match="identifiers are immutable"):
        repository.save_proposal(proposal)

    assert store.table_count("portfolio_proposals") == 1
    assert store.table_count("portfolio_evidence_references") == 1
    assert store.table_count("position_proposals") == 2


def test_portfolio_evidence_gate_accepts_current_authoritative_research(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(
        store, "600000", "score-1", 88, 82,
        validation_status=ValidationStatus.RELIABLE,
    )
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)

    check = PortfolioEvidenceGate(repository, _evidence_policy()).check(
        proposal.proposal_id,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
    )

    assert check.verified
    assert check.reasons == ()
    assert len(check.policy_hash) == 64
    assert not hasattr(check, "order")


@pytest.mark.parametrize(
    ("policy_change", "decision_at", "reason"),
    (
        ({"maximum_proposal_age": timedelta(minutes=30)},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "proposal_stale"),
        ({"maximum_validation_age": timedelta(minutes=30)},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "validation_stale"),
        ({"maximum_risk_age": timedelta(minutes=30)},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "risk_stale"),
        ({"validation_configuration_hash": "b" * 64},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "validation_config_mismatch"),
        ({"validation_model_version": "other-v1"},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "validation_version_mismatch"),
        ({"portfolio_model_version": "other-v1"},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "portfolio_version_mismatch"),
        ({"risk_model_version": "other-v1"},
         datetime(2026, 1, 2, 1, tzinfo=UTC), "risk_version_mismatch"),
    ),
)
def test_portfolio_evidence_gate_rejects_stale_or_mismatched_artifacts(
    tmp_path: Path,
    policy_change: dict[str, object],
    decision_at: datetime,
    reason: str,
) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(
        store, "600000", "score-1", 88, 82,
        validation_status=ValidationStatus.RELIABLE,
    )
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)
    policy = replace(_evidence_policy(), **policy_change)  # type: ignore[arg-type]

    check = PortfolioEvidenceGate(repository, policy).check(
        proposal.proposal_id, as_of=decision_at
    )

    assert not check.verified
    assert reason in check.reasons


def test_portfolio_evidence_gate_rejects_conditional_and_missing_proposals(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(store, "600000", "score-1", 88, 82)
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)
    gate = PortfolioEvidenceGate(repository, _evidence_policy())
    decision_at = datetime(2026, 1, 2, 1, tzinfo=UTC)

    conditional = gate.check(proposal.proposal_id, as_of=decision_at)
    missing = gate.check("missing", as_of=decision_at)

    assert not conditional.verified
    assert "proposal_not_proposed" in conditional.reasons
    assert "validation_not_reliable" in conditional.reasons
    assert missing.reasons == ("proposal_missing",)


def test_portfolio_evidence_gate_rechecks_database_lineage(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(
        store, "600000", "score-1", 88, 82,
        validation_status=ValidationStatus.RELIABLE,
    )
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE validation_reports SET aggregate_status = ? WHERE report_id = ?",
            (ValidationStatus.UNRELIABLE.value, candidate.validation_report_id),
        )

    check = PortfolioEvidenceGate(repository, _evidence_policy()).check(
        proposal.proposal_id,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
    )

    assert not check.verified
    assert check.reasons == ("lineage_unverified",)


def test_verified_proposal_uses_one_snapshot_during_concurrent_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(
        store, "600000", "score-1", 88, 82, validation_status=ValidationStatus.RELIABLE,
    )
    proposal = PortfolioProposalEngine().build(
        (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )
    repository = SQLitePortfolioRepository(store)
    repository.save_proposal(proposal)
    original = SQLitePortfolioRepository._get_proposal

    def load_and_update(
        repository: SQLitePortfolioRepository, proposal_id: str,
    ) -> object:
        loaded = original(repository, proposal_id)
        with sqlite3.connect(store.path) as connection:
            connection.execute(
                "UPDATE validation_reports SET aggregate_status = ? WHERE report_id = ?",
                (ValidationStatus.UNRELIABLE.value, candidate.validation_report_id),
            )
        return loaded

    monkeypatch.setattr(SQLitePortfolioRepository, "_get_proposal", load_and_update)
    assert repository.get_verified_proposal(proposal.proposal_id) is not None
    monkeypatch.setattr(SQLitePortfolioRepository, "_get_proposal", original)
    with pytest.raises(ValueError, match="validation status does not match"):
        repository.get_verified_proposal(proposal.proposal_id)


def test_read_snapshot_blocks_writes_and_restores_connection_scope(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "readonly.sqlite3")
    store.initialize()
    with store.read_snapshot(), pytest.raises(sqlite3.OperationalError, match="readonly"):
        store.upsert_instruments((_instrument("600000"),))
    assert store.upsert_instruments((_instrument("600000"),)) == 1


def test_portfolio_evidence_policy_requires_explicit_positive_limits() -> None:
    policy = _evidence_policy()
    assert policy.policy_hash == _evidence_policy().policy_hash
    assert policy.policy_hash != replace(
        policy, maximum_proposal_age=timedelta(hours=2)
    ).policy_hash
    with pytest.raises(ValueError, match="maximum_proposal_age"):
        replace(policy, maximum_proposal_age=timedelta(0))
    with pytest.raises(ValueError, match="config hash"):
        replace(policy, validation_configuration_hash="not-a-hash")


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ({"score": 99.0}, "investment score does not match"),
        ({"confidence": 99.0}, "investment score does not match"),
        ({"assessment_status": InvestmentAssessmentStatus.LOW_CONFIDENCE},
         "assessment status does not match"),
        ({"validation_status": ValidationStatus.RELIABLE},
         "validation status does not match"),
        ({"validation_configuration_hash": "b" * 64},
         "configuration hash does not match"),
        ({"validation_model_version": "wrong-version"},
         "validation version does not match"),
    ),
)
def test_portfolio_repository_rejects_conflicting_authoritative_evidence(
    tmp_path: Path,
    change: dict[str, object],
    message: str,
) -> None:
    store = SQLiteStore(tmp_path / "portfolio.sqlite3")
    store.initialize()
    candidate = _persisted_candidate(store, "600000", "score-1", 88, 82)
    proposal = PortfolioProposalEngine().build(
        (replace(candidate, **change),),  # type: ignore[arg-type]
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match=message):
        SQLitePortfolioRepository(store).save_proposal(proposal)

    assert store.table_count("portfolio_proposals") == 0


def test_future_validation_evidence_cannot_enter_portfolio() -> None:
    candidate = replace(
        _candidate("600000", "score-1", 88, 82),
        validation_generated_at=datetime(2026, 1, 2, tzinfo=UTC) + timedelta(days=1),
    )
    with pytest.raises(ValueError, match="newer than the proposal"):
        PortfolioProposalEngine().build(
            (candidate,), as_of=datetime(2026, 1, 2, tzinfo=UTC)
        )


def _candidate(
    symbol: str,
    score_id: str,
    score: float,
    confidence: float,
    *,
    status: InvestmentAssessmentStatus = InvestmentAssessmentStatus.COMPLETED,
    liquidity: float = 85,
    volatility: float = 0.18,
) -> PortfolioCandidate:
    return PortfolioCandidate(
        instrument=_instrument(symbol),
        research_report_id=f"research-{score_id}",
        investment_assessment_id=f"assessment-{score_id}",
        investment_score_id=score_id,
        validation_report_id=f"validation-{score_id}",
        score=score,
        confidence=confidence,
        assessment_status=status,
        validation_status=ValidationStatus.CONDITIONALLY_RELIABLE,
        validation_generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        validation_configuration_hash="a" * 64,
        validation_model_version="validation-test-v1",
        expected_role="Value",
        sector="Banks",
        country="China",
        theme="Value",
        volatility=volatility,
        liquidity_score=liquidity,
        average_correlation=0.35,
        max_drawdown=0.25,
        reasons=("InvestmentScore survived research and validation",),
        limitations=("PortfolioProposal is not an execution instruction",),
    )


def _persisted_candidate(
    store: SQLiteStore,
    symbol: str,
    score_id: str,
    score: float,
    confidence: float,
    *,
    validation_status: ValidationStatus = ValidationStatus.CONDITIONALLY_RELIABLE,
) -> PortfolioCandidate:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    instrument = _instrument(symbol)
    instrument_key = f"china_a:equity:{symbol}"
    research_report_id = f"research-{score_id}"
    validation_report_id = f"validation-{score_id}"
    validation_run_id = f"validation-run-{score_id}"
    store.upsert_instruments((instrument,))
    store.save_research_report(
        run_id=f"research-run-{score_id}",
        report_id=research_report_id,
        queue_id=f"queue-{score_id}",
        instrument_id_value=instrument_key,
        generated_at=now,
        available_at=now,
        status=ResearchRunStatus.COMPLETED,
        thesis="Test thesis",
        counter_thesis="Test counter thesis",
        invalidation_conditions=[{"metric": "test", "operator": "lt", "threshold": 0}],
        confidence={"overall": confidence},
        key_findings=("Research completed",),
        key_risks=("Test risk",),
        unresolved_questions=(),
        policy_assessment=None,
        market_regime=None,
        model_version="research-test-v1",
    )
    assessment_id = store.save_investment_assessment(
        report_id=research_report_id,
        instrument_id_value=instrument_key,
        status=InvestmentAssessmentStatus.COMPLETED,
        assessed_at=now,
        score=score,
        confidence=confidence,
        components=[
            {
                "name": "research",
                "score": score,
                "confidence": confidence,
                "weight": 1,
                "contribution": score,
                "reasons": ["test evidence"],
            }
        ],
        reasons=("Assessment completed",),
        limitations=(),
        market_regime=None,
        model_version="investment-test-v1",
    )
    score_row = store.investment_score_row_for_assessment(assessment_id)
    assert score_row is not None
    persisted_score_id = score_row["score_id"]
    store.save_validation_observation(
        run_id=validation_run_id,
        sample_id=f"sample-{score_id}",
        instrument_id_value=instrument_key,
        research_report_id=research_report_id,
        decision_at=now,
        research_expected_success=True,
        market_regime=None,
        factor_scores={},
        portfolio_position=None,
    )
    configuration_hash = "a" * 64
    store.save_validation_report(
        run_id=validation_run_id,
        report_id=validation_report_id,
        validation_id=f"validation-id-{score_id}",
        generated_at=now,
        status="completed",
        aggregate_status=validation_status.value,
        framework_snapshot={"configuration_hash": configuration_hash},
        known_limitations=("Test validation",),
        reproducibility_manifest={"configuration_hash": configuration_hash},
        decision_summary=None,
        portfolio_risk=None,
        model_version="validation-test-v1",
    )
    return PortfolioCandidate(
        instrument=instrument,
        research_report_id=research_report_id,
        investment_assessment_id=assessment_id,
        investment_score_id=persisted_score_id,
        validation_report_id=validation_report_id,
        score=score,
        confidence=confidence,
        assessment_status=InvestmentAssessmentStatus.COMPLETED,
        validation_status=validation_status,
        validation_generated_at=now,
        validation_configuration_hash=configuration_hash,
        validation_model_version="validation-test-v1",
        expected_role="Value",
        sector="Banks",
        country="China",
        theme="Value",
        volatility=0.18,
        liquidity_score=85,
        average_correlation=0.35,
        max_drawdown=0.25,
        reasons=("Persisted research and validation lineage",),
    )


def _evidence_policy() -> PortfolioEvidencePolicy:
    return PortfolioEvidencePolicy(
        policy_version="portfolio-evidence-test-v1",
        maximum_proposal_age=timedelta(days=1),
        maximum_validation_age=timedelta(days=1),
        maximum_risk_age=timedelta(days=1),
        validation_configuration_hash="a" * 64,
        validation_model_version="validation-test-v1",
        portfolio_model_version=PORTFOLIO_MODEL_VERSION,
        risk_model_version=RISK_MODEL_VERSION,
    )


def _instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=f"Instrument {symbol}",
        industry="Banks",
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="test",
    )
