"""A scoped read-only input inventory, never a readiness promotion or strategy run."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import cast

from tong_quant.application.sse_calendar_plan import SSECalendarPlanBuilder
from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.config.settings import Settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.price_evidence import matches_daily_bar
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    FINANCIAL_SNAPSHOT_DATASET,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market, ResearchModuleName
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_main_board import SHANGHAI
from tong_quant.markets.sse_references import require_sha256
from tong_quant.research.financial import FINANCIAL_FIELDS
from tong_quant.validation.replay.hashing import stable_hash, stable_json
from tong_quant.validation.replay.repository import SQLiteHistoricalReplayRepository
from tong_quant.validation.replay.research_binding import research_snapshot
from tong_quant.version import FRAMEWORK_VERSION, SSE_PILOT_COVERAGE_VERSION


class SSEPilotCoverageReader:
    def __init__(
        self,
        store: SQLiteStore,
        settings: Settings,
        *,
        calendar_builder: SSECalendarPlanBuilder | None = None,
    ) -> None:
        self._store = store
        self._data = MarketDataService(store)
        self._runtime = SSERuntimeInputReader(self._data, calendar_builder=calendar_builder)
        self._replay = SQLiteHistoricalReplayRepository(store)
        self._settings = settings

    def read(
        self, symbol: str, query: MarketRuleQuery, *, calendar_start: date, universe: str
    ) -> dict[str, object]:
        if not universe.strip():
            raise ValueError("coverage requires an explicit universe name")
        with self._data.read_snapshot():
            snapshot = self._runtime.read(symbol, query, calendar_start=calendar_start)
            bars = self._data.daily_bars(
                symbol,
                Market.CHINA_A,
                AssetType.EQUITY,
                calendar_start,
                query.trade_date - timedelta(days=1),
                as_of=query.as_of,
            )
            instrument = snapshot.instrument
            facts = (
                []
                if instrument is None
                else [dict(row) for row in self._replay.fundamental_rows(instrument, query.as_of)]
            )
            screening = (
                []
                if instrument is None
                else [dict(row) for row in self._replay.screening_rows(instrument, query.as_of)]
            )
            publications = self._data.fundamental_publications(
                symbol, Market.CHINA_A, AssetType.EQUITY, as_of=query.as_of
            )
            native_financials = self._data.provider_evidence(
                provider="akshare",
                dataset=FINANCIAL_SNAPSHOT_DATASET,
                market=Market.CHINA_A,
                subject=symbol,
                as_of=query.as_of,
            )
            disclosures = self._data.provider_evidence(
                provider="cninfo_direct",
                dataset=CNINFO_DISCLOSURES_DATASET,
                market=Market.CHINA_A,
                subject=symbol,
                as_of=query.as_of,
            )
            members = self._data.universe(
                universe,
                Market.CHINA_A,
                on_date=query.trade_date,
                as_of=query.as_of,
                tradable_only=False,
            )
            report = (
                None
                if instrument is None
                else self._replay.research_report(instrument, query.as_of)
            )
            research = research_snapshot(
                report, decision_at=query.as_of, instrument_id=f"china_a:equity:{symbol}"
            )
            schema_version = self._store.schema_version()
            fingerprint = self._store.physical_schema_fingerprint()
        eligible_bars = [bar for bar in bars if not bar.is_suspended]
        bound = [
            record
            for record in snapshot.price_evidence
            if any(matches_daily_bar(record, bar) for bar in bars)
        ]
        bound_dates = {
            bar.timestamp.astimezone(SHANGHAI).date()
            for bar in bars
            if any(matches_daily_bar(record, bar) for record in bound)
        }
        trend = self._settings.research.trend
        required_bars = max(trend.breakout_period, trend.volume_period, trend.atr_period) + 1
        if min(trend.breakout_period, trend.volume_period, trend.atr_period) <= 0:
            raise ValueError("trend input periods must be positive")
        evidence = (
            ()
            if report is None or research["blocking_reasons"]
            else tuple(item for assessment in report.assessments for item in assessment.evidence)
        )
        confirmations = {
            name: _summary(
                [
                    item
                    for item in evidence
                    if item.module is ResearchModuleName.TREND and item.name == name
                ]
            )
            for name in ("market_sentiment_confirmation", "industry_heat_confirmation")
        }
        gaps = {gap.code for gap in snapshot.gaps}
        if len(eligible_bars) < required_bars:
            gaps.add("trend_daily_history_insufficient")
        missing_facts = sorted(FINANCIAL_FIELDS - {str(row["metric"]) for row in facts})
        if missing_facts:
            gaps.add("fundamental_metrics_missing")
        if not publications:
            gaps.add("fundamental_publications_missing")
        if not members:
            gaps.add("historical_universe_missing")
        elif not any(item.symbol == symbol for item in members):
            gaps.add("subject_not_in_declared_universe")
        if not screening:
            gaps.add("screening_results_missing")
        if report is None:
            gaps.add("research_report_missing")
        if research["blocking_reasons"]:
            gaps.add("research_content_review_failed")
        for name, summary in confirmations.items():
            if summary["observations"] == 0:
                gaps.add(f"{name}_missing")
        if report is None or report.market_regime is None:
            gaps.add("market_regime_report_missing")
        try:
            require_sha256(self._settings.portfolio_evidence.validation_configuration_hash)
        except ValueError:
            gaps.add("validation_configuration_not_pinned")
        datasets = {
            "daily_bars": {
                **_summary(bars),
                "distinct_dates": len({bar.timestamp.date() for bar in bars}),
                "non_suspended_observations": len(eligible_bars),
                "configured_trend_minimum": required_bars,
                "minimum_count_deficit": max(0, required_bars - len(eligible_bars)),
                "exact_bound_dates": len(bound_dates),
                "authoritative_session_coverage_pct": None,
                "limitations": [
                    "unadjusted_price_only",
                    "session_continuity_not_proved",
                    "minimum_count_is_not_strategy_validation",
                ],
            },
            "price_evidence": _summary(bound),
            "calendar": {
                **_summary(snapshot.sessions),
                "missing_calendar_dates": [
                    day.isoformat() for day in snapshot.missing_calendar_dates
                ],
                "planned_calendar_hash": None
                if snapshot.calendar_plan is None
                else snapshot.calendar_plan.plan_hash,
                "limitations": [
                    "missing_dates_unknown_not_closed",
                    "ordinary_plan_not_actual_session_history",
                ],
            },
            "status": _summary([] if snapshot.status is None else [snapshot.status]),
            "lifecycle_events": _summary(snapshot.lifecycle_events),
            "corporate_actions": {
                **_summary(snapshot.corporate_actions),
                "limitations": [
                    "positive_events_not_complete_coverage",
                    "empty_query_not_action_free_proof",
                ],
            },
            "fundamentals": {**_summary(facts), "missing_metrics": missing_facts},
            "native_financial_snapshots": {
                **_summary(native_financials),
                "statements": sorted(
                    {str(row.payload.get("statement")) for row in native_financials}
                ),
                "limitations": [
                    "native_rows_not_canonical_facts",
                    "units_mapping_and_revisions_unreviewed",
                ],
            },
            "direct_disclosure_metadata": {
                **_summary(disclosures),
                "limitations": [
                    "metadata_not_verified_filing_bytes",
                    "timestamps_not_numeric_revision_proof",
                    "provider_pagination_and_precision_require_separate_review",
                ],
            },
            "publication_events": {
                **_summary(publications),
                "limitations": ["publication_dates_do_not_authenticate_numeric_revisions"],
            },
            "universe": {
                **_summary(members),
                "name": universe,
                "subject_present": any(item.symbol == symbol for item in members),
                "limitations": [
                    "single_snapshot_not_historical_continuity",
                    "adverse_status_members_preserved",
                ],
            },
            "screening": _summary(screening),
            "research": research,
            "trend_confirmations": confirmations,
            "market_regime": {
                "raw_input_coverage": "not_inspected",
                "report_state": (
                    None
                    if report is None
                    or research["blocking_reasons"]
                    or report.market_regime is None
                    else report.market_regime.state.value
                ),
                "required_input_names": sorted(self._settings.market_regime.china.weights),
                "limitations": [
                    "state_label_not_raw_metric_coverage",
                    "regime_is_not_a_trading_switch",
                ],
            },
        }
        record: dict[str, object] = {
            "model_version": SSE_PILOT_COVERAGE_VERSION,
            "framework_version": FRAMEWORK_VERSION,
            "schema_version": schema_version,
            "schema_fingerprint": fingerprint,
            "scope": stable_json(query.scope),
            "symbol": symbol,
            "as_of": query.as_of.isoformat(),
            "history_start": calendar_start.isoformat(),
            "history_end": (query.trade_date - timedelta(days=1)).isoformat(),
            "runtime_input_hash": snapshot.input_hash,
            "research_configuration_hash": stable_hash(self._settings.research),
            "datasets": datasets,
            "blocking_requirements": sorted(gaps),
            "readiness_decision": "not_assessed_no_promotion",
            "strict_validation_authorized": False,
            "boundary": "Descriptive inventory only; no validation, simulation or trading approval",
            "limitations": [
                "explicit_symbol_pilot_not_market_wide_selection",
                "screening_rows_do_not_prove_discovery_or_hard_screen_approval",
                "availability_is_not_historical_observation_date",
                "raw_artifact_bytes_and_source_truth_not_authenticated_by_this_inventory",
                "visible_inputs_do_not_prove_original_research_consumption",
            ],
        }
        reject_sensitive_structure(record, path="sse_pilot_coverage")
        return {**record, "manifest_hash": stable_hash(record)}


def _summary(records: Sequence[object]) -> dict[str, object]:
    values = cast(list[dict[str, object]], stable_json(list(records)))
    available = [
        datetime.fromisoformat(str(row["available_at"])).astimezone(UTC).isoformat()
        for row in values
        if row.get("available_at") is not None
    ]
    observed = [
        str(
            next(
                (
                    row[key]
                    for key in (
                        "timestamp",
                        "observed_at",
                        "effective_date",
                        "trade_date",
                        "period_end",
                    )
                    if row.get(key) is not None
                ),
                "",
            )
        )[:10]
        for row in values
    ]
    return {
        "observations": len(values),
        "content_hash": stable_hash(values),
        "first_observation_date": min(filter(None, observed), default=None),
        "last_observation_date": max(filter(None, observed), default=None),
        "first_available_at": min(available, default=None),
        "last_available_at": max(available, default=None),
        "sources": sorted(
            {
                str(row.get("source") or row.get("source_reference"))
                for row in values
                if row.get("source") or row.get("source_reference")
            }
        ),
        "trust_levels": sorted({str(row.get("trust_level", "unknown")) for row in values}),
        "availability_precision": sorted(
            {str(row.get("availability_precision", "unknown")) for row in values}
        ),
    }
