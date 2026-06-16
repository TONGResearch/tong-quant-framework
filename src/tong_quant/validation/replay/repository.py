import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.data.storage.sqlite import SQLiteStore, instrument_id
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    EvidenceQuality,
    Market,
    Regime,
    ResearchConclusion,
    ResearchModuleName,
    ResearchRunStatus,
)
from tong_quant.domain.models import Bar, Instrument, InstrumentStatus
from tong_quant.market_regime.models import MarketRegime, RegimeContribution
from tong_quant.research.models import (
    ConfidenceBreakdown,
    PolicyAssessment,
    ResearchAssessment,
    ResearchEvidence,
    ResearchReport,
    ResearchValue,
    ThesisInvalidationCondition,
)
from tong_quant.validation.replay.hashing import stable_json
from tong_quant.validation.replay.models import (
    HistoricalReplayResult,
)


@dataclass(slots=True)
class SQLiteHistoricalReplayRepository:
    store: SQLiteStore

    def instrument(
        self,
        symbol: str,
        market: Market,
        *,
        as_of: datetime,
    ) -> Instrument | None:
        return self.store.get_instrument(symbol, market, AssetType.EQUITY, as_of=as_of)

    def subjects(
        self,
        query_market: Market,
        universe: str | None,
        as_of: datetime,
    ) -> list[Instrument]:
        if universe is None:
            return []
        return self.store.universe_as_of(
            universe,
            query_market,
            on_date=as_of.date(),
            as_of=as_of,
            tradable_only=False,
        )

    def instrument_status(
        self,
        instrument: Instrument,
        *,
        on_date: date,
        as_of: datetime,
    ) -> InstrumentStatus | None:
        return self.store.instrument_status(
            instrument.symbol,
            instrument.market,
            instrument.asset_type,
            on_date=on_date,
            as_of=as_of,
        )

    def daily_bars(
        self,
        instrument: Instrument,
        *,
        start: date,
        end: date,
        as_of: datetime,
    ) -> list[Bar]:
        return self.store.daily_bars(
            instrument.symbol,
            instrument.market,
            instrument.asset_type,
            start,
            end,
            as_of=as_of,
            adjustment=Adjustment.NONE,
        )

    def provider_limitations(
        self,
        datasets: tuple[str, ...],
    ) -> list[ProviderLimitation]:
        return self.store.provider_limitations(datasets)

    def readiness_assessments(
        self,
        datasets: tuple[str, ...],
    ) -> tuple[PITReadinessAssessment, ...]:
        assessments = [
            assessment
            for dataset in datasets
            if (assessment := self.store.latest_pit_readiness(dataset)) is not None
        ]
        return tuple(assessments)

    def fundamental_rows(self, instrument: Instrument, as_of: datetime) -> list[sqlite3.Row]:
        return self.store.fundamental_facts_for_replay(instrument, as_of=as_of)

    def screening_rows(self, instrument: Instrument, as_of: datetime) -> list[sqlite3.Row]:
        return self.store.screening_results_for_replay(instrument, as_of=as_of)

    def research_report(self, instrument: Instrument, as_of: datetime) -> ResearchReport | None:
        row = self.store.latest_research_report_for_replay(instrument, as_of=as_of)
        if row is None:
            return None
        evidence_rows = self.store.research_evidence_for_run(row["run_id"])
        evidence = {
            _row_text(item, "evidence_id"): _evidence_from_row(item)
            for item in evidence_rows
        }
        assessments = tuple(
            _assessment_from_row(item, evidence)
            for item in self.store.research_assessments_for_report(row["report_id"])
        )
        policy_assessment = _policy_assessment(row["policy_assessment_json"])
        return ResearchReport(
            report_id=row["report_id"],
            queue_id=row["queue_id"],
            instrument_id=row["instrument_id"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            available_at=datetime.fromisoformat(row["available_at"]),
            status=ResearchRunStatus(row["status"]),
            thesis=row["thesis"],
            counter_thesis=row["counter_thesis"],
            invalidation_conditions=tuple(
                ThesisInvalidationCondition(**item)
                for item in json.loads(row["invalidation_conditions_json"])
            ),
            assessments=assessments,
            policy_assessment=policy_assessment,
            confidence=_confidence_from_record(json.loads(row["confidence_json"])),
            key_findings=tuple(json.loads(row["key_findings_json"])),
            key_risks=tuple(json.loads(row["key_risks_json"])),
            unresolved_questions=tuple(json.loads(row["unresolved_questions_json"])),
            market_regime=_market_regime(row["market_regime_json"]),
            model_version=row["model_version"],
        )

    def save_result(self, result: HistoricalReplayResult) -> None:
        manifest = result.manifest
        self.store.save_historical_replay_manifest(
            manifest_id=manifest.manifest_id,
            query_hash=manifest.query_hash,
            input_hashes=manifest.input_hashes,
            dataset_versions=manifest.dataset_versions,
            schema_version=manifest.schema_version,
            framework_version=manifest.framework_version,
            configuration_hash=manifest.configuration_hash,
            git_commit=manifest.git_commit,
            data_trust_summary=manifest.data_trust_summary,
            provider_limitations=manifest.provider_limitations,
            missing_data_warnings=manifest.missing_data_warnings,
            replay_confidence=cast(dict[str, object], stable_json(manifest.replay_confidence)),
            generated_at=manifest.generated_at,
            model_version=manifest.model_version,
        )
        for sample in result.samples:
            validation_json = (
                None
                if sample.validation_sample is None
                else cast(dict[str, object], stable_json(sample.validation_sample))
            )
            self.store.save_historical_replay_sample(
                sample_id=sample.sample_id,
                manifest_id=manifest.manifest_id,
                instrument_id_value=instrument_id(sample.instrument),
                decision_as_of=sample.decision_as_of,
                outcome_as_of=sample.outcome_as_of,
                replay_hash=sample.replay_hash,
                replay_confidence=cast(dict[str, object], stable_json(sample.replay_confidence)),
                decision_context=sample.decision_context,
                outcome_context=sample.outcome_context,
                evidence_references=sample.evidence_references,
                missing_data_flags=sample.missing_data_flags,
                provider_limitations=sample.provider_limitations,
                data_trust_summary=sample.data_trust_summary,
                validation_sample=validation_json,
                is_complete=sample.is_complete,
                model_version=manifest.model_version,
            )


def _evidence_from_row(row: sqlite3.Row) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=row["evidence_id"],
        module=ResearchModuleName(row["module"]),
        name=row["name"],
        value=_research_value(json.loads(row["value_json"])),
        observed_at=datetime.fromisoformat(row["observed_at"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        source=row["source"],
        quality=EvidenceQuality(row["quality"]),
        source_reference=row["source_reference"],
        calculation_version=row["calculation_version"],
        input_hash=row["input_hash"],
        metadata=_research_value_dict(json.loads(row["metadata_json"])),
    )


def _assessment_from_row(
    row: sqlite3.Row,
    evidence: dict[str, ResearchEvidence],
) -> ResearchAssessment:
    evidence_ids = tuple(json.loads(row["evidence_ids_json"]))
    return ResearchAssessment(
        module=ResearchModuleName(row["module"]),
        conclusion=ResearchConclusion(row["conclusion"]),
        score=row["score"],
        confidence=_confidence_from_record(json.loads(row["confidence_json"])),
        evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
        available_at=datetime.fromisoformat(row["available_at"]),
        findings=tuple(json.loads(row["findings_json"])),
        risks=tuple(json.loads(row["risks_json"])),
        limitations=tuple(json.loads(row["limitations_json"])),
        evidence_ids=evidence_ids,
        model_version=row["model_version"],
        features=_research_value_dict(json.loads(row["features_json"])),
        evidence=tuple(evidence[item] for item in evidence_ids if item in evidence),
    )


def _policy_assessment(payload: str | None) -> PolicyAssessment | None:
    if payload is None:
        return None
    record = json.loads(payload)
    if not isinstance(record, dict) or "assessment" not in record:
        return None
    assessment_record = cast(dict[str, object], record["assessment"])
    assessment = ResearchAssessment(
        module=ResearchModuleName(str(assessment_record["module"])),
        conclusion=ResearchConclusion(str(assessment_record["conclusion"])),
        score=cast(float | None, assessment_record["score"]),
        confidence=_confidence_from_record(assessment_record["confidence"]),
        evaluated_at=datetime.fromisoformat(str(assessment_record["evaluated_at"])),
        available_at=datetime.fromisoformat(str(assessment_record["available_at"])),
        findings=tuple(cast(list[str], assessment_record["findings"])),
        risks=tuple(cast(list[str], assessment_record["risks"])),
        limitations=tuple(cast(list[str], assessment_record["limitations"])),
        evidence_ids=tuple(cast(list[str], assessment_record["evidence_ids"])),
        model_version=str(assessment_record["model_version"]),
        features=_research_value_dict(cast(dict[str, object], assessment_record["features"])),
    )
    return PolicyAssessment(
        assessment=assessment,
        regulatory_environment=str(record["regulatory_environment"]),
        industrial_policy=str(record["industrial_policy"]),
        fiscal_policy=str(record["fiscal_policy"]),
        monetary_policy=str(record["monetary_policy"]),
        geopolitical_factors=str(record["geopolitical_factors"]),
    )


def _market_regime(payload: str | None) -> MarketRegime | None:
    if payload is None:
        return None
    record = json.loads(payload)
    return MarketRegime(
        market=Market(record["market"]),
        state=Regime(record["state"]),
        confidence=int(record["confidence"]),
        reasons=tuple(record["reasons"]),
        as_of=datetime.fromisoformat(record["as_of"]),
        score=float(record["score"]),
        contributions=tuple(
            RegimeContribution(
                metric=item["metric"],
                value=float(item["value"]),
                weight=float(item["weight"]),
                contribution=float(item["contribution"]),
                reason=item["reason"],
            )
            for item in record["contributions"]
        ),
        model_version=record["model_version"],
        subject=record["subject"],
        metadata=record.get("metadata", {}),
    )


def _confidence_from_record(value: object) -> ConfidenceBreakdown:
    record = cast(dict[str, object], value)
    return ConfidenceBreakdown(
        evidence_quality=_required_float(record["evidence_quality"]),
        data_completeness=_required_float(record["data_completeness"]),
        module_agreement=_required_float(record["module_agreement"]),
        point_in_time_integrity=_required_float(record["point_in_time_integrity"]),
        confidence=_required_float(record["confidence"]),
        method=str(record.get("method", "replay-reconstructed")),
    )


def _required_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    raise TypeError(f"expected numeric value, got {type(value).__name__}")


def _research_value(value: object) -> ResearchValue:
    if isinstance(value, int | float | str | bool) or value is None:
        return value
    if isinstance(value, Decimal):
        return value
    raise TypeError(f"unsupported research value: {type(value).__name__}")


def _research_value_dict(value: object) -> dict[str, ResearchValue]:
    if not isinstance(value, dict):
        raise TypeError("expected research value dictionary")
    return {str(key): _research_value(item) for key, item in value.items()}


def _row_text(row: sqlite3.Row, key: str) -> str:
    return str(row[key])


__all__ = ["SQLiteHistoricalReplayRepository"]
