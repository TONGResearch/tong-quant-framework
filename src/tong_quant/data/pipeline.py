from datetime import UTC, datetime
from uuid import uuid4

from tong_quant.data.models import (
    DailyBarRequest,
    DataAvailabilityWarning,
    IngestionBatch,
    IngestionResult,
    ProviderLimitation,
    ProviderResponse,
    RawDatasetFingerprint,
)
from tong_quant.data.normalization import (
    build_bar_instrument,
    first_bar_available_at,
    normalize_company_info,
    normalize_corporate_actions,
    normalize_current_status_snapshot,
    normalize_daily_bars,
    normalize_delisted_statuses,
    normalize_delisting_lifecycle,
    normalize_financial_statement,
    normalize_fundamental_disclosures,
    normalize_index_membership,
    normalize_market_universe_snapshot,
    normalize_publication_schedule,
    normalize_st_name_change_lifecycle,
    normalize_suspension_lifecycle,
    normalize_trading_calendar,
    normalize_universe,
)
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.quality import DataQualityError, validate_bars, validate_raw_dataset
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    DataTrustLevel,
    IngestionBatchStatus,
    Market,
    SecurityStatus,
)


class DataIngestionPipeline:
    def __init__(
        self,
        provider: AkShareAdapter,
        store: SQLiteStore,
        *,
        strict_point_in_time: bool = True,
    ) -> None:
        self._provider = provider
        self._store = store
        self._strict_point_in_time = strict_point_in_time

    def initialize(self) -> None:
        self._store.initialize()
        self._document_provider_limitations()

    def ingest_daily_bars(self, request: DailyBarRequest) -> IngestionResult:
        if (
            self._strict_point_in_time
            and request.adjustment is not Adjustment.NONE
        ):
            raise ValueError(
                "strict point-in-time mode rejects provider-adjusted bars; "
                "ingest unadjusted prices until dated corporate-action factors exist"
            )
        response = self._provider.daily_bars(request)
        raw_report = validate_raw_dataset(response.dataset)
        if not raw_report.is_valid:
            raise DataQualityError(raw_report)

        instrument = build_bar_instrument(
            request.symbol,
            request.asset_type,
            first_bar_available_at(response.dataset),
        )
        bars = normalize_daily_bars(response.dataset, request, instrument)
        normalized_report = validate_bars(bars)
        if not normalized_report.is_valid:
            raise DataQualityError(normalized_report)

        self._store.upsert_instruments([instrument])
        accepted = self._store.upsert_daily_bars(bars)
        batch_id, warnings = self._record_dataset_audit(response, accepted)
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=batch_id,
            warnings=warnings,
        )

    def ingest_trading_calendar(self) -> IngestionResult:
        response = self._provider.trading_calendar()
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        sessions = normalize_trading_calendar(response.dataset)
        accepted = self._store.upsert_trading_sessions(sessions)
        batch_id, warnings = self._record_dataset_audit(response, accepted)
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=batch_id,
            warnings=warnings,
        )

    def ingest_company_info(self, symbol: str) -> IngestionResult:
        response = self._provider.company_info(symbol)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instrument = normalize_company_info(response.dataset, symbol)
        accepted = self._store.upsert_instruments([instrument])
        batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            warning_code="current_snapshot_only",
            warning_message=(
                "Company information is a retrieval-time snapshot, not "
                "historical fundamentals"
            ),
            trust_level=DataTrustLevel.LOW,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=0,
            cached=response.cache_hit,
            batch_id=batch_id,
            warnings=warnings,
        )

    def ingest_a_share_universe(self) -> IngestionResult:
        response = self._provider.a_share_universe()
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instruments = normalize_universe(response.dataset)
        batch_id = str(uuid4())
        accepted = self._store.upsert_instruments(instruments)
        memberships = normalize_market_universe_snapshot(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_universe_memberships(memberships)
        batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="current_universe_snapshot",
            warning_message=(
                "A-share universe is a retrieval-time snapshot unless "
                "historical membership is ingested"
            ),
            trust_level=DataTrustLevel.LOW,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=batch_id,
            warnings=warnings,
        )

    def ingest_financial_statement(self, symbol: str, statement: str) -> IngestionResult:
        response = self._provider.financial_statement(symbol, statement)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instrument = self._store.get_instrument(
            symbol,
            market=Market.CHINA_A,
            asset_type=AssetType.EQUITY,
            as_of=response.dataset.retrieved_at,
        )
        if instrument is None:
            instrument = build_bar_instrument(
                symbol,
                asset_type=AssetType.EQUITY,
                available_at=response.dataset.retrieved_at,
            )
            self._store.upsert_instruments([instrument])
        batch_id = str(uuid4())
        facts = normalize_financial_statement(
            response.dataset,
            instrument,
            batch_id=batch_id,
            publication_events=self._store.fundamental_publication_events(
                symbol,
                Market.CHINA_A,
                AssetType.EQUITY,
                as_of=response.dataset.retrieved_at,
            ),
        )
        accepted = self._store.upsert_fundamental_facts(facts)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="publication_time_unavailable",
            warning_message=(
                "AKShare financial statement payload does not provide reliable "
                "issuer publication timestamps; records are retrieval-time safe"
            ),
            trust_level=DataTrustLevel.LOW,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_special_treatment_status(self) -> IngestionResult:
        return self._ingest_status_snapshot(
            self._provider.st_stocks(),
            status=SecurityStatus.SPECIAL_TREATMENT,
            is_tradable=True,
            warning_code="st_snapshot_only",
            warning_message=(
                "ST data is a retrieval-time snapshot without full historical "
                "status intervals"
            ),
        )

    def ingest_suspended_status(self) -> IngestionResult:
        return self._ingest_status_snapshot(
            self._provider.suspended_stocks(),
            status=SecurityStatus.SUSPENDED,
            is_tradable=False,
            warning_code="suspension_snapshot_only",
            warning_message="Suspension data may lack complete historical effective intervals",
        )

    def ingest_delisted_statuses(self, exchange: str) -> IngestionResult:
        response = self._provider.delisted_stocks(exchange)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        statuses = normalize_delisted_statuses(response.dataset, batch_id=batch_id)
        lifecycle_events = normalize_delisting_lifecycle(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([status.instrument for status in statuses])
        accepted = self._store.upsert_instrument_statuses(statuses)
        self._store.upsert_security_lifecycle_events(lifecycle_events)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="delisting_history_partial",
            warning_message=(
                "Delisting data may not include the full warning or "
                "delisting-risk period"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_suspension_lifecycle(self, on_date: str) -> IngestionResult:
        response = self._provider.suspension_events(on_date)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        events = normalize_suspension_lifecycle(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([event.instrument for event in events])
        accepted = self._store.upsert_security_lifecycle_events(events)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="suspension_event_retrieval_time",
            warning_message=(
                "Suspension effective dates are retained, but historical "
                "availability is known only from retrieval time"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=max(len(response.dataset.frame) - accepted, 0),
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_shenzhen_st_history(self) -> IngestionResult:
        response = self._provider.shenzhen_name_changes()
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        events = normalize_st_name_change_lifecycle(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([event.instrument for event in events])
        accepted = self._store.upsert_security_lifecycle_events(events)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="st_history_shenzhen_only",
            warning_message=(
                "Dated ST name-change evidence currently covers Shenzhen only; "
                "Shanghai and Beijing history remain incomplete"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=max(len(response.dataset.frame) - accepted, 0),
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_fundamental_publication_schedule(
        self,
        period_end: str,
    ) -> IngestionResult:
        response = self._provider.fundamental_publication_schedule(period_end)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        events = normalize_publication_schedule(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([event.instrument for event in events])
        accepted = self._store.upsert_fundamental_publication_events(events)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="publication_date_only",
            warning_message=(
                "Actual disclosure dates are date-only and become usable at end of day"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=max(len(response.dataset.frame) - accepted, 0),
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_fundamental_disclosures(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category: str = "",
    ) -> IngestionResult:
        response = self._provider.fundamental_disclosures(
            symbol,
            start_date=start_date,
            end_date=end_date,
            category=category,
        )
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        events = normalize_fundamental_disclosures(
            response.dataset,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([event.instrument for event in events])
        accepted = self._store.upsert_fundamental_publication_events(events)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="publication_title_parsing",
            warning_message=(
                "Report period and revision order are parsed from announcement titles; "
                "unrecognized titles remain excluded with source evidence retained raw"
            ),
            trust_level=DataTrustLevel.HIGH,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=max(len(response.dataset.frame) - accepted, 0),
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_index_membership(self, index_symbol: str) -> IngestionResult:
        response = self._provider.index_membership(index_symbol)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        memberships = normalize_index_membership(
            response.dataset,
            universe=f"index:{index_symbol}",
            batch_id=batch_id,
        )
        self._store.upsert_instruments([membership.instrument for membership in memberships])
        accepted = self._store.upsert_universe_memberships(memberships)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="membership_availability_retrieval_time",
            warning_message=(
                "Index membership availability is treated as retrieval time "
                "unless source publication is known"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def ingest_corporate_actions(self, symbol: str) -> IngestionResult:
        response = self._provider.corporate_actions(symbol)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instrument = build_bar_instrument(
            symbol,
            asset_type=AssetType.EQUITY,
            available_at=response.dataset.retrieved_at,
        )
        self._store.upsert_instruments([instrument])
        batch_id = str(uuid4())
        actions = normalize_corporate_actions(
            response.dataset,
            instrument,
            batch_id=batch_id,
        )
        accepted = self._store.upsert_corporate_actions(actions)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code="corporate_action_not_adjustment_ready",
            warning_message=(
                "Corporate actions are stored for audit, but strict PIT adjusted "
                "price reconstruction remains disabled until factors are complete"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def _ingest_status_snapshot(
        self,
        response: ProviderResponse,
        *,
        status: SecurityStatus,
        is_tradable: bool,
        warning_code: str,
        warning_message: str,
    ) -> IngestionResult:
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        batch_id = str(uuid4())
        statuses = normalize_current_status_snapshot(
            response.dataset,
            status=status,
            is_tradable=is_tradable,
            batch_id=batch_id,
        )
        self._store.upsert_instruments([item.instrument for item in statuses])
        accepted = self._store.upsert_instrument_statuses(statuses)
        recorded_batch_id, warnings = self._record_dataset_audit(
            response,
            accepted,
            batch_id=batch_id,
            warning_code=warning_code,
            warning_message=warning_message,
            trust_level=DataTrustLevel.LOW,
        )
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
            batch_id=recorded_batch_id,
            warnings=warnings,
        )

    def _record_dataset_audit(
        self,
        response: ProviderResponse,
        accepted: int,
        *,
        batch_id: str | None = None,
        warning_code: str = "",
        warning_message: str = "",
        trust_level: DataTrustLevel = DataTrustLevel.HIGH,
    ) -> tuple[str, tuple[str, ...]]:
        dataset = response.dataset
        recorded_batch_id = batch_id or str(uuid4())
        completed_at = datetime.now(UTC)
        raw_hash = dataset.content_hash()
        self._store.save_raw_dataset_fingerprint(
            RawDatasetFingerprint(
                dataset=dataset.dataset,
                provider=self._provider.source_id,
                raw_data_hash=raw_hash,
                retrieved_at=dataset.retrieved_at,
                parameters=dataset.parameters,
                row_count=len(dataset.frame),
                source=dataset.source,
            )
        )
        self._store.save_ingestion_batch(
            IngestionBatch(
                batch_id=recorded_batch_id,
                provider=self._provider.source_id,
                dataset=dataset.dataset,
                started_at=dataset.retrieved_at,
                completed_at=completed_at,
                status=IngestionBatchStatus.COMPLETED,
                parameters=dataset.parameters,
                raw_response_hash=raw_hash,
            )
        )
        warnings: tuple[str, ...] = ()
        if warning_code and warning_message:
            warning = DataAvailabilityWarning(
                batch_id=recorded_batch_id,
                dataset=dataset.dataset,
                warning_code=warning_code,
                message=warning_message,
                trust_level=trust_level,
                created_at=completed_at,
            )
            self._store.save_data_availability_warning(warning)
            warnings = (warning_message,)
        if accepted == 0:
            message = "Provider payload produced no accepted normalized records"
            self._store.save_data_availability_warning(
                DataAvailabilityWarning(
                    batch_id=recorded_batch_id,
                    dataset=dataset.dataset,
                    warning_code="no_accepted_records",
                    message=message,
                    trust_level=DataTrustLevel.UNKNOWN,
                    created_at=completed_at,
                )
            )
            warnings = (*warnings, message)
        return recorded_batch_id, warnings

    def _document_provider_limitations(self) -> None:
        documented_at = datetime.now(UTC)
        limitations = (
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="fundamental_facts",
                limitation_code="publication_time_not_guaranteed",
                description=(
                    "AKShare financial statement endpoints may not provide reliable "
                    "issuer publication timestamps; conservative ingestion uses retrieval time"
                ),
                trust_level=DataTrustLevel.LOW,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="security_lifecycle_events",
                limitation_code="st_history_exchange_gap",
                description=(
                    "Dated ST name changes are currently available for Shenzhen; "
                    "Shanghai and Beijing timelines require a secondary source"
                ),
                trust_level=DataTrustLevel.LOW,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="security_lifecycle_events",
                limitation_code="relisting_history_unavailable",
                description=(
                    "AKShare does not provide a verified complete A-share relisting history"
                ),
                trust_level=DataTrustLevel.UNKNOWN,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="universe_memberships",
                limitation_code="csi_membership_latest_snapshot",
                description=(
                    "CSI300, CSI500, and CSI1000 constituent endpoints provide current "
                    "snapshots, not complete historical entries and exits"
                ),
                trust_level=DataTrustLevel.LOW,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="fundamental_publications",
                limitation_code="schedule_date_only",
                description=(
                    "Actual disclosure schedules provide dates; intraday availability "
                    "requires CNInfo announcement evidence"
                ),
                trust_level=DataTrustLevel.MEDIUM,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="instrument_status_history",
                limitation_code="historical_intervals_partial",
                description=(
                    "ST, suspension, and delisting endpoints may provide snapshots or "
                    "partial histories instead of complete status intervals"
                ),
                trust_level=DataTrustLevel.LOW,
                documented_at=documented_at,
            ),
            ProviderLimitation(
                provider=self._provider.source_id,
                dataset="corporate_actions",
                limitation_code="adjustment_factor_not_ready",
                description=(
                    "Corporate-action records do not by themselves enable strict "
                    "point-in-time adjusted-price reconstruction"
                ),
                trust_level=DataTrustLevel.MEDIUM,
                documented_at=documented_at,
            ),
        )
        for limitation in limitations:
            self._store.save_provider_limitation(limitation)
