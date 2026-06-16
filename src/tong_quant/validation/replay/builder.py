from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal

from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.domain.enums import DataTrustLevel, ResearchRunStatus, ThesisOutcomeStatus
from tong_quant.domain.models import Instrument
from tong_quant.research.models import ResearchReport
from tong_quant.validation.models import OutcomeDefinition, ValidationOutcome, ValidationSample
from tong_quant.validation.replay.confidence import (
    ReplayConfidenceEvaluator,
    ReplayConfidenceInput,
)
from tong_quant.validation.replay.hashing import stable_hash
from tong_quant.validation.replay.integrity import validate_replay_sample
from tong_quant.validation.replay.models import (
    HistoricalReplayResult,
    ReplayManifest,
    ReplayQuery,
    ReplayValidationSample,
)
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository


@dataclass(slots=True)
class HistoricalReplayBuilder:
    repository: SQLiteHistoricalReplayRepository
    confidence_evaluator: ReplayConfidenceEvaluator = ReplayConfidenceEvaluator()
    persist: bool = True

    def build(
        self,
        query: ReplayQuery,
        *,
        generated_at: datetime | None = None,
    ) -> HistoricalReplayResult:
        generated = generated_at or datetime.now(UTC)
        query_hash = stable_hash(query)
        provider_limitations = tuple(
            self.repository.provider_limitations(query.provider_limitation_datasets)
        )
        readiness = self.repository.readiness_assessments(query.required_inputs)
        instruments = self._subjects(query)
        samples = tuple(
            sample
            for instrument in instruments
            for sample in self._samples_for_instrument(
                query,
                query_hash=query_hash,
                instrument=instrument,
                provider_limitations=provider_limitations,
                readiness=readiness,
            )
            if query.include_incomplete_samples or sample.validation_sample is not None
        )
        trust_summary = _merge_trust_summaries(sample.data_trust_summary for sample in samples)
        missing_warnings = tuple(
            sorted(
                {
                    flag
                    for sample in samples
                    for flag in sample.missing_data_flags
                }
            )
        )
        manifest_confidence = self.confidence_evaluator.evaluate(
            ReplayConfidenceInput(
                trust_levels=_trust_levels_from_summary(trust_summary),
                readiness_assessments=readiness,
                missing_data_count=sum(len(sample.missing_data_flags) for sample in samples),
                expected_input_count=max(1, len(samples) * len(query.required_inputs)),
                provider_limitations=provider_limitations,
            )
        )
        manifest = ReplayManifest(
            manifest_id=f"manifest-{query_hash[:24]}",
            query_hash=query_hash,
            input_hashes={sample.sample_id: sample.replay_hash for sample in samples},
            dataset_versions={
                "schema": self.repository.store.schema_version(),
                **{item.dataset: item.model_version for item in readiness},
            },
            schema_version=self.repository.store.schema_version(),
            framework_version=query.framework_version,
            configuration_hash=query.configuration_hash,
            git_commit=query.git_commit,
            data_trust_summary=trust_summary,
            provider_limitations=tuple(_limitation_code(item) for item in provider_limitations),
            missing_data_warnings=missing_warnings,
            replay_confidence=manifest_confidence,
            generated_at=generated,
        )
        result = HistoricalReplayResult(query=query, manifest=manifest, samples=samples)
        if self.persist:
            self.repository.save_result(result)
        return result

    def _subjects(self, query: ReplayQuery) -> tuple[Instrument, ...]:
        if query.subject_type == "universe":
            return tuple(
                self.repository.subjects(query.market, query.universe, query.decision_as_of)
            )
        instruments = [
            instrument
            for symbol in query.symbols
            if (
                instrument := self.repository.instrument(
                    symbol,
                    query.market,
                    as_of=query.decision_as_of,
                )
            )
            is not None
        ]
        return tuple(instruments)

    def _samples_for_instrument(
        self,
        query: ReplayQuery,
        *,
        query_hash: str,
        instrument: Instrument,
        provider_limitations: tuple[ProviderLimitation, ...],
        readiness: tuple[PITReadinessAssessment, ...],
    ) -> tuple[ReplayValidationSample, ...]:
        decision_context = self._decision_context(query, instrument)
        report = self.repository.research_report(instrument, query.decision_as_of)
        samples = tuple(
            self._sample_for_definition(
                query,
                query_hash=query_hash,
                instrument=instrument,
                decision_context=decision_context,
                report=report,
                definition=definition,
                provider_limitations=provider_limitations,
                readiness=readiness,
            )
            for definition in query.outcome_definitions
        )
        for sample in samples:
            validate_replay_sample(sample)
        return samples

    def _decision_context(
        self,
        query: ReplayQuery,
        instrument: Instrument,
    ) -> dict[str, object]:
        status = self.repository.instrument_status(
            instrument,
            on_date=query.decision_as_of.date(),
            as_of=query.decision_as_of,
        )
        fundamental_rows = self.repository.fundamental_rows(instrument, query.decision_as_of)
        screening_rows = self.repository.screening_rows(instrument, query.decision_as_of)
        return {
            "instrument_id": _instrument_key(instrument),
            "status": None if status is None else status.status.value,
            "status_trust_level": None if status is None else status.trust_level.value,
            "status_tradable": None if status is None else status.is_tradable,
            "fundamental_count": len(fundamental_rows),
            "fundamental_trust_levels": tuple(row["trust_level"] for row in fundamental_rows),
            "screening_dimensions": tuple(row["dimension"] for row in screening_rows),
            "screening_count": len(screening_rows),
        }

    def _sample_for_definition(
        self,
        query: ReplayQuery,
        *,
        query_hash: str,
        instrument: Instrument,
        decision_context: dict[str, object],
        report: ResearchReport | None,
        definition: OutcomeDefinition,
        provider_limitations: tuple[ProviderLimitation, ...],
        readiness: tuple[PITReadinessAssessment, ...],
    ) -> ReplayValidationSample:
        outcome, outcome_context = self._outcome(query, instrument, definition)
        missing_flags = _missing_flags(query, decision_context, report, outcome.value)
        trust_summary = _trust_summary(decision_context)
        replay_confidence = self.confidence_evaluator.evaluate(
            ReplayConfidenceInput(
                trust_levels=_trust_levels_from_summary(trust_summary),
                readiness_assessments=readiness,
                missing_data_count=len(missing_flags),
                expected_input_count=len(query.required_inputs),
                provider_limitations=provider_limitations,
            )
        )
        sample_hash_payload = {
            "query_hash": query_hash,
            "instrument": _instrument_key(instrument),
            "definition": asdict(definition),
            "decision_context": decision_context,
            "outcome_context": outcome_context,
            "report_id": None if report is None else report.report_id,
            "missing_flags": missing_flags,
            "replay_confidence": asdict(replay_confidence),
        }
        replay_hash = stable_hash(sample_hash_payload)
        sample_id = f"replay-{replay_hash[:24]}"
        validation_sample = None
        if report is not None and outcome.value is not None:
            validation_sample = ValidationSample(
                sample_id=sample_id,
                instrument=instrument,
                research_report=report,
                decision_at=query.decision_as_of,
                research_expected_success=_expected_success(report),
                outcome=outcome,
                factor_scores=_factor_scores(report, decision_context),
                market_regime=(
                    None if report.market_regime is None else report.market_regime.state
                ),
            )
        return ReplayValidationSample(
            sample_id=sample_id,
            instrument=instrument,
            decision_as_of=query.decision_as_of,
            outcome_as_of=query.outcome_as_of,
            decision_context=decision_context,
            outcome_context=outcome_context,
            evidence_references=() if report is None else _evidence_references(report),
            missing_data_flags=missing_flags,
            replay_hash=replay_hash,
            replay_confidence=replay_confidence,
            validation_sample=validation_sample,
            provider_limitations=tuple(_limitation_code(item) for item in provider_limitations),
            data_trust_summary=trust_summary,
        )

    def _outcome(
        self,
        query: ReplayQuery,
        instrument: Instrument,
        definition: OutcomeDefinition,
    ) -> tuple[ValidationOutcome, dict[str, object]]:
        bars = self.repository.daily_bars(
            instrument,
            start=query.decision_as_of.date(),
            end=query.outcome_as_of.date(),
            as_of=query.outcome_as_of,
        )
        decision_bar = bars[0] if bars else None
        outcome_bar = bars[-1] if bars else None
        value = None
        benchmark_value = None
        succeeded = None
        if (
            definition.target_metric == "close_return_pct"
            and decision_bar is not None
            and outcome_bar is not None
            and decision_bar.close != 0
        ):
            value = float((outcome_bar.close / decision_bar.close - Decimal("1")) * 100)
            succeeded = _compare(value, definition.success_operator, definition.success_threshold)
        outcome = ValidationOutcome(
            outcome_id=f"{definition.outcome_id}:{_instrument_key(instrument)}",
            definition_id=definition.outcome_id,
            subject_id=_instrument_key(instrument),
            observed_at=query.outcome_as_of,
            available_at=(
                query.outcome_as_of
                if outcome_bar is None
                else max(outcome_bar.available_at, query.outcome_as_of)
            ),
            value=value,
            benchmark_value=benchmark_value,
            succeeded=succeeded,
            thesis_status=(
                ThesisOutcomeStatus.NOT_OBSERVABLE
                if value is None
                else (
                    ThesisOutcomeStatus.SUPPORTED
                    if succeeded
                    else ThesisOutcomeStatus.INVALIDATED
                )
            ),
            invalidation_triggered=None if value is None else not bool(succeeded),
            metadata={"target_metric": definition.target_metric},
        )
        context = {
            "bar_count": len(bars),
            "target_metric": definition.target_metric,
            "value": value,
            "outcome_available_at": outcome.available_at.isoformat(),
        }
        return outcome, context


def _missing_flags(
    query: ReplayQuery,
    decision_context: dict[str, object],
    report: ResearchReport | None,
    outcome_value: float | None,
) -> tuple[str, ...]:
    flags: list[str] = []
    required = set(query.required_inputs)
    if "instrument_status" in required and decision_context["status"] is None:
        flags.append("instrument_status_missing")
    if "fundamentals" in required and decision_context["fundamental_count"] == 0:
        flags.append("fundamentals_missing")
    if "screening_results" in required and decision_context["screening_count"] == 0:
        flags.append("screening_results_missing")
    if "research_report" in required and report is None:
        flags.append("research_report_missing")
    if "market_regime" in required and (report is None or report.market_regime is None):
        flags.append("market_regime_missing")
    if "outcome" in required and outcome_value is None:
        flags.append("outcome_missing")
    status = decision_context["status"]
    if status in {"special_treatment", "suspended", "delisted", "delisting"}:
        flags.append(f"security_status_preserved:{status}")
    return tuple(flags)


def _trust_summary(decision_context: dict[str, object]) -> dict[str, int]:
    summary = {level.value: 0 for level in DataTrustLevel}
    status_level = decision_context["status_trust_level"]
    if isinstance(status_level, str):
        summary[status_level] += 1
    fundamental_levels = decision_context["fundamental_trust_levels"]
    if isinstance(fundamental_levels, tuple):
        for level in fundamental_levels:
            if isinstance(level, str):
                summary[level] += 1
    return {key: value for key, value in summary.items() if value}


def _merge_trust_summaries(
    summaries: Iterable[dict[str, int]],
) -> dict[str, int]:
    merged = {level.value: 0 for level in DataTrustLevel}
    for summary in summaries:
        for key, value in summary.items():
            merged[str(key)] += int(value)
    return {key: value for key, value in merged.items() if value}


def _trust_levels_from_summary(summary: dict[str, int]) -> tuple[DataTrustLevel, ...]:
    levels: list[DataTrustLevel] = []
    for key, count in summary.items():
        levels.extend(DataTrustLevel(key) for _ in range(count))
    return tuple(levels)


def _expected_success(report: ResearchReport) -> bool:
    return report.status is ResearchRunStatus.COMPLETED and report.confidence.confidence >= 50


def _factor_scores(
    report: ResearchReport,
    decision_context: dict[str, object],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for assessment in report.assessments:
        if assessment.score is not None:
            scores[assessment.module.value] = assessment.score
    screening_count = decision_context.get("screening_count")
    if isinstance(screening_count, int | float):
        scores["screening_coverage"] = min(100.0, float(screening_count) * 10)
    return scores


def _evidence_references(report: ResearchReport) -> tuple[str, ...]:
    return tuple(
        evidence_id
        for assessment in report.assessments
        for evidence_id in assessment.evidence_ids
    )


def _instrument_key(instrument: Instrument) -> str:
    return f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"


def _limitation_code(limitation: ProviderLimitation) -> str:
    return f"{limitation.provider}:{limitation.dataset}:{limitation.limitation_code}"


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    if operator == "!=":
        return value != threshold
    raise ValueError(f"unsupported outcome operator: {operator}")


__all__ = ["HistoricalReplayBuilder"]
