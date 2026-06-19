import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import cast

from tong_quant.data.storage.sqlite import SQLiteStore, instrument_id
from tong_quant.domain.enums import (
    PortfolioAssetCategory,
    PortfolioProposalStatus,
    RiskAssessmentStatus,
    StressScenarioType,
)
from tong_quant.portfolio.models import PortfolioProposal, PositionProposal
from tong_quant.risk.models import (
    ExposureBreakdown,
    RiskAssessment,
    RiskBudget,
    StressScenario,
    StressScenarioResult,
)


@dataclass(frozen=True, slots=True)
class PortfolioConstraintRecord:
    constraint_name: str
    constraint_value: float
    breached: bool
    reasons: tuple[str, ...]


@dataclass(slots=True)
class SQLitePortfolioRepository:
    store: SQLiteStore

    def save_proposal(self, proposal: PortfolioProposal) -> None:
        instruments = tuple(
            position.instrument
            for position in proposal.positions
            if position.instrument is not None
        )
        self.store.upsert_instruments(instruments)
        self.store.save_portfolio_proposal(
            proposal_id=proposal.proposal_id,
            as_of=proposal.as_of,
            base_currency=proposal.base_currency,
            status=proposal.status.value,
            cash_weight=proposal.cash_weight,
            target_volatility=proposal.target_volatility,
            expected_portfolio_volatility=proposal.expected_portfolio_volatility,
            expected_max_drawdown=proposal.expected_max_drawdown,
            concentration_summary=proposal.concentration_summary,
            exposure_summary=proposal.exposure_summary,
            correlation_summary=proposal.correlation_summary,
            reasons=proposal.reasons,
            limitations=proposal.limitations,
            metadata=proposal.metadata,
            model_version=proposal.model_version,
        )
        for position in proposal.positions:
            self.store.save_position_proposal(
                proposal_id=proposal.proposal_id,
                instrument_id_value=(
                    None if position.instrument is None else instrument_id(position.instrument)
                ),
                asset_category=position.asset_category.value,
                proposed_weight=position.proposed_weight,
                min_weight=position.min_weight,
                max_weight=position.max_weight,
                confidence=position.confidence,
                liquidity_score=position.liquidity_score,
                volatility_estimate=position.volatility_estimate,
                expected_role=position.expected_role,
                reasons=position.reasons,
                risk_flags=position.risk_flags,
                constraints_applied=position.constraints_applied,
            )
        assessment = proposal.risk_assessment
        if assessment is None:
            return
        self.store.save_risk_assessment(
            assessment_id=assessment.assessment_id,
            proposal_id=assessment.proposal_id,
            assessed_at=assessment.assessed_at,
            status=assessment.status.value,
            score=assessment.score,
            confidence=assessment.confidence,
            risk_budget=asdict(assessment.risk_budget),
            concentration_risk=assessment.concentration_risk,
            correlation_risk=assessment.correlation_risk,
            volatility_risk=assessment.volatility_risk,
            drawdown_risk=assessment.drawdown_risk,
            liquidity_risk=assessment.liquidity_risk,
            scenario_results=[asdict(result) for result in assessment.scenario_results],
            reasons=assessment.reasons,
            required_adjustments=assessment.required_adjustments,
            limitations=assessment.limitations,
            model_version=assessment.model_version,
        )
        for exposure in (
            assessment.sector_exposure,
            assessment.country_exposure,
            assessment.theme_exposure,
        ):
            self.store.save_portfolio_exposure(
                proposal_id=proposal.proposal_id,
                dimension=exposure.dimension,
                exposures=exposure.exposures,
                max_allowed=exposure.max_allowed,
                breached=exposure.breached,
                reasons=exposure.reasons,
            )
        for name, value in asdict(assessment.risk_budget).items():
            self.store.save_portfolio_constraint(
                proposal_id=proposal.proposal_id,
                constraint_name=name,
                constraint_value=float(value),
                breached=name in " ".join(assessment.required_adjustments),
                reasons=assessment.required_adjustments or ("constraint recorded",),
            )

    def get_proposal(self, proposal_id: str) -> PortfolioProposal | None:
        row = self.store.portfolio_proposal_row(proposal_id)
        if row is None:
            return None
        as_of = datetime.fromisoformat(row["as_of"])
        positions = self.get_positions(proposal_id, as_of=as_of)
        risk_assessment = self.get_risk_assessment(proposal_id)
        return PortfolioProposal(
            proposal_id=row["proposal_id"],
            as_of=as_of,
            base_currency=row["base_currency"],
            status=PortfolioProposalStatus(row["status"]),
            positions=positions,
            cash_weight=float(row["cash_weight"]),
            target_volatility=float(row["target_volatility"]),
            expected_portfolio_volatility=float(row["expected_portfolio_volatility"]),
            expected_max_drawdown=float(row["expected_max_drawdown"]),
            concentration_summary={
                str(key): float(value)
                for key, value in json.loads(row["concentration_summary_json"]).items()
            },
            exposure_summary={
                str(dimension): {
                    str(key): float(value) for key, value in values.items()
                }
                for dimension, values in json.loads(row["exposure_summary_json"]).items()
            },
            correlation_summary={
                str(key): float(value)
                for key, value in json.loads(row["correlation_summary_json"]).items()
            },
            risk_assessment=risk_assessment,
            reasons=tuple(json.loads(row["reasons_json"])),
            limitations=tuple(json.loads(row["limitations_json"])),
            model_version=row["model_version"],
            metadata=json.loads(row["metadata_json"]),
        )

    def get_positions(
        self,
        proposal_id: str,
        *,
        as_of: datetime,
    ) -> tuple[PositionProposal, ...]:
        positions: list[PositionProposal] = []
        for row in self.store.position_proposal_rows(proposal_id):
            instrument_id_value = row["instrument_id"]
            instrument = (
                None
                if instrument_id_value is None
                else self.store.get_instrument_by_id(instrument_id_value, as_of=as_of)
            )
            positions.append(
                PositionProposal(
                    instrument=instrument,
                    asset_category=PortfolioAssetCategory(row["asset_category"]),
                    proposed_weight=float(row["proposed_weight"]),
                    min_weight=float(row["min_weight"]),
                    max_weight=float(row["max_weight"]),
                    confidence=float(row["confidence"]),
                    liquidity_score=float(row["liquidity_score"]),
                    volatility_estimate=float(row["volatility_estimate"]),
                    expected_role=row["expected_role"],
                    reasons=tuple(json.loads(row["reasons_json"])),
                    risk_flags=tuple(json.loads(row["risk_flags_json"])),
                    constraints_applied=tuple(json.loads(row["constraints_applied_json"])),
                )
            )
        return tuple(positions)

    def get_risk_assessment(self, proposal_id: str) -> RiskAssessment | None:
        row = self.store.risk_assessment_row(proposal_id)
        if row is None:
            return None
        exposures = {item.dimension: item for item in self.get_exposures(proposal_id)}
        return RiskAssessment(
            assessment_id=row["assessment_id"],
            proposal_id=row["proposal_id"],
            assessed_at=datetime.fromisoformat(row["assessed_at"]),
            status=RiskAssessmentStatus(row["status"]),
            score=float(row["score"]),
            confidence=float(row["confidence"]),
            risk_budget=RiskBudget(**json.loads(row["risk_budget_json"])),
            concentration_risk=float(row["concentration_risk"]),
            sector_exposure=exposures["sector"],
            country_exposure=exposures["country"],
            theme_exposure=exposures["theme"],
            correlation_risk=float(row["correlation_risk"]),
            volatility_risk=float(row["volatility_risk"]),
            drawdown_risk=float(row["drawdown_risk"]),
            liquidity_risk=float(row["liquidity_risk"]),
            scenario_results=tuple(
                _stress_result_from_record(item)
                for item in json.loads(row["scenario_results_json"])
            ),
            reasons=tuple(json.loads(row["reasons_json"])),
            required_adjustments=tuple(json.loads(row["required_adjustments_json"])),
            limitations=tuple(json.loads(row["limitations_json"])),
            model_version=row["model_version"],
        )

    def get_exposures(self, proposal_id: str) -> tuple[ExposureBreakdown, ...]:
        exposures: list[ExposureBreakdown] = []
        for row in self.store.portfolio_exposure_rows(proposal_id):
            exposures.append(
                ExposureBreakdown(
                    dimension=row["dimension"],
                    exposures={
                        str(key): float(value)
                        for key, value in json.loads(row["exposures_json"]).items()
                    },
                    max_allowed=float(row["max_allowed"]),
                    breached=bool(row["breached"]),
                    reasons=tuple(json.loads(row["reasons_json"])),
                )
            )
        return tuple(exposures)

    def get_constraints(self, proposal_id: str) -> tuple[PortfolioConstraintRecord, ...]:
        constraints: list[PortfolioConstraintRecord] = []
        for row in self.store.portfolio_constraint_rows(proposal_id):
            constraints.append(
                PortfolioConstraintRecord(
                    constraint_name=row["constraint_name"],
                    constraint_value=float(row["constraint_value"]),
                    breached=bool(row["breached"]),
                    reasons=tuple(json.loads(row["reasons_json"])),
                )
            )
        return tuple(constraints)


def _stress_result_from_record(record: dict[str, object]) -> StressScenarioResult:
    scenario_record = record["scenario"]
    if not isinstance(scenario_record, dict):
        raise ValueError("stress scenario record is invalid")
    reasons_record = record["reasons"]
    if not isinstance(reasons_record, list):
        raise ValueError("stress scenario reasons are invalid")
    estimated_loss = cast(float | int | str, record["estimated_loss"])
    affected_weight = cast(float | int | str, record["affected_weight"])
    return StressScenarioResult(
        scenario=StressScenario(
            scenario_type=StressScenarioType(str(scenario_record["scenario_type"])),
            name=str(scenario_record["name"]),
            shock=float(cast(float | int | str, scenario_record["shock"])),
            target=(
                None
                if scenario_record.get("target") is None
                else str(scenario_record["target"])
            ),
        ),
        estimated_loss=float(estimated_loss),
        affected_weight=float(affected_weight),
        breached=bool(record["breached"]),
        reasons=tuple(str(item) for item in reasons_record),
    )


__all__ = ["PortfolioConstraintRecord", "SQLitePortfolioRepository"]
