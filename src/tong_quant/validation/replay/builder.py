import json
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta

from tong_quant.data.lifecycle_review import LifecycleRecordDisposition, review_lifecycle_record
from tong_quant.data.models import PITReadinessAssessment, ProviderLimitation
from tong_quant.domain.enums import DataTrustLevel
from tong_quant.domain.models import Instrument, require_timezone
from tong_quant.research.models import ResearchReport
from tong_quant.validation.models import OutcomeDefinition, ValidationOutcome, ValidationSample
from tong_quant.validation.replay.confidence import (
    ReplayConfidenceEvaluator,
    ReplayConfidenceInput,
)
from tong_quant.validation.replay.hashing import stable_hash, stable_json
from tong_quant.validation.replay.integrity import replay_query_hash, validate_replay_sample
from tong_quant.validation.replay.models import (
    OUTCOME_REVIEW_BLOCKED,
    RESEARCH_REVIEW_BLOCKED,
    STATUS_REVIEW_BLOCKED,
    HistoricalReplayResult,
    ReplayManifest,
    ReplayQuery,
    ReplayValidationSample,
)
from tong_quant.validation.replay.outcomes import evaluate_outcome
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository
from tong_quant.validation.replay.research_binding import (
    research_evidence_ids,
    research_expected_success,
    research_factor_scores,
    research_snapshot,
)
from tong_quant.version import (
    HISTORICAL_REPLAY_VERSION,
    LIFECYCLE_REVIEW_VERSION,
    REPLAY_OUTCOME_VERSION,
    REPLAY_RESEARCH_BINDING_VERSION,
)


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
        require_timezone(generated, "replay generated_at")
        if generated < query.outcome_as_of:
            raise ValueError("replay cannot be generated before outcome_as_of")
        with self.repository.store.read_snapshot():
            result = self._reconstruct(query, generated=generated)
        if self.persist:
            self.repository.save_result(result)
        return result

    def _reconstruct(self, query: ReplayQuery, *, generated: datetime) -> HistoricalReplayResult:
        query_hash = replay_query_hash(query)
        provider_limitations = tuple(
            limitation
            for limitation in self.repository.provider_limitations(
                query.provider_limitation_datasets
            )
            if limitation.documented_at <= generated
        )
        readiness = self.repository.readiness_assessments(
            query.readiness_datasets,
            as_of=generated,
        )
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
        )
        trust_summary = _merge_trust_summaries(sample.data_trust_summary for sample in samples)
        missing_warnings = tuple(
            sorted({flag for sample in samples for flag in sample.missing_data_flags})
        )
        manifest_confidence = self.confidence_evaluator.evaluate(
            ReplayConfidenceInput(
                trust_levels=_trust_levels_from_summary(trust_summary),
                readiness_assessments=readiness,
                required_datasets=query.readiness_datasets,
                minimum_trust_level=query.minimum_trust_level,
                missing_data_count=sum(
                    _blocking_missing_data_count(sample.missing_data_flags) for sample in samples
                ),
                expected_input_count=max(1, len(samples) * len(query.required_inputs)),
                provider_limitations=provider_limitations,
                integrity_blockers=tuple(
                    sorted(
                        {
                            flag
                            for sample in samples
                            for flag in sample.missing_data_flags
                            if flag
                            in {
                                STATUS_REVIEW_BLOCKED,
                                OUTCOME_REVIEW_BLOCKED,
                                RESEARCH_REVIEW_BLOCKED,
                            }
                        }
                    )
                ),
            )
        )
        dataset_versions = {
            "schema": self.repository.store.schema_version(),
            "lifecycle_review": LIFECYCLE_REVIEW_VERSION,
            "replay": HISTORICAL_REPLAY_VERSION,
            "outcome_contract": REPLAY_OUTCOME_VERSION,
            "research_binding": REPLAY_RESEARCH_BINDING_VERSION,
            **{item.dataset: item.model_version for item in readiness},
            **{f"readiness_hash:{item.dataset}": stable_hash(item) for item in readiness},
        }
        manifest_hash = stable_hash(
            {
                "query_hash": query_hash,
                "sample_hashes": tuple(sample.replay_hash for sample in samples),
                "dataset_versions": dataset_versions,
                "confidence": manifest_confidence,
                "provider_limitations": provider_limitations,
                "generated_at": generated,
            }
        )
        manifest_id = f"manifest-{manifest_hash}"
        # Samples belong to one manifest, even when their economic content is identical.
        samples = tuple(_bind_sample(sample, manifest_id) for sample in samples)
        manifest = ReplayManifest(
            manifest_id=manifest_id,
            query_hash=query_hash,
            input_hashes={sample.sample_id: sample.replay_hash for sample in samples},
            dataset_versions=dataset_versions,
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
        snapshot = research_snapshot(
            report, decision_at=query.decision_as_of, instrument_id=_instrument_key(instrument)
        )
        decision_context["research_snapshot"] = snapshot
        # Invalid nested evidence remains diagnosable without entering ValidationSample.
        if snapshot["blocking_reasons"]:
            report = None
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
        fundamental_inputs = _input_rows(fundamental_rows)
        screening_inputs = _input_rows(screening_rows)
        status_review = (
            None
            if status is None
            else review_lifecycle_record(
                status,
                as_of=query.decision_as_of,
                effective_on_or_before=query.decision_as_of.date(),
            )
        )
        return {
            "instrument_id": _instrument_key(instrument),
            "status": None if status is None else status.status.value,
            "status_trust_level": None if status is None else status.trust_level.value,
            "status_tradable": None if status is None else status.is_tradable,
            "status_record": (
                None if status is None else json.loads(json.dumps(asdict(status), default=str))
            ),
            "status_review": None if status_review is None else stable_json(status_review),
            "fundamental_count": len(fundamental_rows),
            "fundamental_inputs": fundamental_inputs,
            "fundamental_inputs_hash": stable_hash(fundamental_inputs),
            "fundamental_trust_levels": tuple(row["trust_level"] for row in fundamental_rows),
            "screening_dimensions": tuple(row["dimension"] for row in screening_rows),
            "screening_count": len(screening_rows),
            "screening_inputs": screening_inputs,
            "screening_inputs_hash": stable_hash(screening_inputs),
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
        if outcome_context["blocking_reasons"]:
            missing_flags += (OUTCOME_REVIEW_BLOCKED,)
        snapshot = decision_context["research_snapshot"]
        if isinstance(snapshot, dict) and snapshot["blocking_reasons"]:
            missing_flags += (RESEARCH_REVIEW_BLOCKED,)
        trust_summary = _trust_summary(decision_context)
        replay_confidence = self.confidence_evaluator.evaluate(
            ReplayConfidenceInput(
                trust_levels=_trust_levels_from_summary(trust_summary),
                readiness_assessments=readiness,
                required_datasets=query.readiness_datasets,
                minimum_trust_level=query.minimum_trust_level,
                missing_data_count=_blocking_missing_data_count(missing_flags),
                expected_input_count=len(query.required_inputs),
                provider_limitations=provider_limitations,
                integrity_blockers=tuple(
                    flag
                    for flag in missing_flags
                    if flag
                    in {STATUS_REVIEW_BLOCKED, OUTCOME_REVIEW_BLOCKED, RESEARCH_REVIEW_BLOCKED}
                ),
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
                research_expected_success=research_expected_success(report),
                outcome=outcome,
                factor_scores=research_factor_scores(report, decision_context),
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
            evidence_references=() if report is None else research_evidence_ids(report),
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
        start = query.decision_as_of.astimezone(UTC).date()
        end = start + timedelta(days=definition.observation_horizon_days)
        decision_bars = self.repository.daily_bars(
            instrument,
            start=start,
            end=start,
            as_of=query.decision_as_of,
        )
        outcome_bars = self.repository.daily_bars(
            instrument,
            start=end,
            end=end,
            as_of=query.outcome_as_of,
        )
        return evaluate_outcome(
            query,
            instrument,
            definition,
            decision_bars[0] if len(decision_bars) == 1 else None,
            outcome_bars[0] if len(outcome_bars) == 1 else None,
        )


def _bind_sample(sample: ReplayValidationSample, manifest_id: str) -> ReplayValidationSample:
    sample_id = f"replay-{stable_hash((manifest_id, sample.replay_hash))}"
    return replace(
        sample,
        sample_id=sample_id,
        validation_sample=(
            None
            if sample.validation_sample is None
            else replace(sample.validation_sample, sample_id=sample_id)
        ),
    )


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
    review = decision_context["status_review"]
    if decision_context["status"] is not None and (
        not isinstance(review, dict)
        or review.get("disposition") != LifecycleRecordDisposition.REVIEWABLE.value
    ):
        flags.append(STATUS_REVIEW_BLOCKED)
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


def _blocking_missing_data_count(flags: tuple[str, ...]) -> int:
    return sum(flag.endswith("_missing") for flag in flags)


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


def _input_rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, object]]:
    # Ignore ingestion bookkeeping, but retain all material fields and original JSON.
    return [
        {
            key: value
            for key, value in dict(row).items()
            if key not in {"ingested_at", "version_rank"}
        }
        for row in rows
    ]


def _instrument_key(instrument: Instrument) -> str:
    return f"{instrument.market.value}:{instrument.asset_type.value}:{instrument.symbol}"


def _limitation_code(limitation: ProviderLimitation) -> str:
    return f"{limitation.provider}:{limitation.dataset}:{limitation.limitation_code}"


__all__ = ["HistoricalReplayBuilder"]
