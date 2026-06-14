from tong_quant.data.models import DailyBarRequest, IngestionResult
from tong_quant.data.normalization import (
    build_bar_instrument,
    first_bar_available_at,
    normalize_company_info,
    normalize_daily_bars,
    normalize_trading_calendar,
    normalize_universe,
)
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.quality import DataQualityError, validate_bars, validate_raw_dataset
from tong_quant.data.storage.sqlite import SQLiteStore


class DataIngestionPipeline:
    def __init__(self, provider: AkShareAdapter, store: SQLiteStore) -> None:
        self._provider = provider
        self._store = store

    def initialize(self) -> None:
        self._store.initialize()

    def ingest_daily_bars(self, request: DailyBarRequest) -> IngestionResult:
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
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
        )

    def ingest_trading_calendar(self) -> IngestionResult:
        response = self._provider.trading_calendar()
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        sessions = normalize_trading_calendar(response.dataset)
        accepted = self._store.upsert_trading_sessions(sessions)
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
        )

    def ingest_company_info(self, symbol: str) -> IngestionResult:
        response = self._provider.company_info(symbol)
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instrument = normalize_company_info(response.dataset, symbol)
        accepted = self._store.upsert_instruments([instrument])
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=0,
            cached=response.cache_hit,
        )

    def ingest_a_share_universe(self) -> IngestionResult:
        response = self._provider.a_share_universe()
        report = validate_raw_dataset(response.dataset)
        if not report.is_valid:
            raise DataQualityError(report)
        instruments = normalize_universe(response.dataset)
        accepted = self._store.upsert_instruments(instruments)
        return IngestionResult(
            dataset=response.dataset.dataset,
            received=len(response.dataset.frame),
            accepted=accepted,
            rejected=len(response.dataset.frame) - accepted,
            cached=response.cache_hit,
        )
