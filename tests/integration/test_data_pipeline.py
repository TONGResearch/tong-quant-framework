from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType, Market


class FakeAkShareClient:
    def __init__(self) -> None:
        self.daily_calls = 0
        self.index_calls = 0

    def stock_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.daily_calls += 1
        return _daily_frame(include_symbol=True)

    def index_zh_a_hist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        self.index_calls += 1
        return _daily_frame(include_symbol=False)

    def tool_trade_date_hist_sina(self) -> pd.DataFrame:
        return pd.DataFrame({"trade_date": [date(2024, 1, 2), date(2024, 1, 3)]})

    def stock_individual_info_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "item": ["股票代码", "股票简称", "行业", "上市时间"],
                "value": ["600000", "浦发银行", "银行", 19991110],
            }
        )

    def stock_zh_a_spot_em(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "代码": ["600000", "000001"],
                "名称": ["浦发银行", "平安银行"],
            }
        )

    def stock_financial_benefit_new_ths(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "report_date": ["2023-12-31", "2023-12-31"],
                "metric_name": ["revenue", "profit"],
                "value": [100, 20],
            }
        )

    def stock_financial_debt_new_ths(self, **kwargs: object) -> pd.DataFrame:
        return self.stock_financial_benefit_new_ths(**kwargs)

    def stock_financial_cash_new_ths(self, **kwargs: object) -> pd.DataFrame:
        return self.stock_financial_benefit_new_ths(**kwargs)

    def stock_zh_a_st_em(self) -> pd.DataFrame:
        return pd.DataFrame({"代码": ["600000"], "名称": ["*ST 测试"]})

    def stock_zh_a_stop_em(self) -> pd.DataFrame:
        raise AssertionError("Delisted-market quotes must never be used as suspension evidence")

    def stock_info_sh_delist(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "代码": ["600001"],
                "证券简称": ["退市测试"],
                "终止上市日期": ["2024-01-04"],
            }
        )

    def stock_info_sz_delist(self, **kwargs: object) -> pd.DataFrame:
        return self.stock_info_sh_delist(**kwargs)

    def index_stock_cons_csindex(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "日期": ["2024-01-04", "2024-01-04"],
                "成分券代码": ["600000", "000001"],
                "成分券名称": ["浦发银行", "平安银行"],
            }
        )

    def stock_fhps_detail_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "除权除息日": ["2024-01-04"],
                "方案进度": ["实施分配"],
                "现金分红-现金分红比例": [0.5],
                "现金分红-现金分红比例描述": ["10派0.50元(含税)"],
                "送转股份-送转总比例": [0.0],
            }
        )

    def stock_tfp_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["平安银行"],
                "停牌时间": ["2024-01-02"],
                "停牌截止时间": ["2024-01-03"],
                "停牌期限": ["1 day"],
                "停牌原因": ["test event"],
            }
        )

    def stock_info_sz_change_name(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "证券代码": ["000001", "000001"],
                "变更日期": ["2022-01-02", "2023-01-02"],
                "变更前简称": ["平安银行", "*ST平安"],
                "变更后简称": ["*ST平安", "平安银行"],
            }
        )

    def stock_yysj_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "股票代码": ["600000"],
                "股票简称": ["浦发银行"],
                "实际披露时间": ["2024-01-03"],
            }
        )

    def stock_zh_a_disclosure_report_cninfo(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "代码": ["600000", "600000"],
                "简称": ["浦发银行", "浦发银行"],
                "公告标题": ["2023年年度报告", "2023年年度报告（修订版）"],
                "公告时间": ["2024-01-03 18:00:00", "2024-01-04 18:00:00"],
                "公告链接": ["https://example.invalid/1", "https://example.invalid/2"],
            }
        )


@pytest.fixture
def data_foundation(
    tmp_path: Path,
) -> tuple[
    FakeAkShareClient,
    DataIngestionPipeline,
    MarketDataService,
    SQLiteStore,
]:
    client = FakeAkShareClient()
    retrieved_at = datetime(2024, 1, 5, 8, tzinfo=UTC)
    cache = DataFrameCache(
        tmp_path / "cache",
        timedelta(days=1),
        clock=lambda: retrieved_at,
    )
    adapter = AkShareAdapter(
        client=client,
        cache=cache,
        clock=lambda: retrieved_at,
    )
    store = SQLiteStore(tmp_path / "tong_quant.sqlite3")
    pipeline = DataIngestionPipeline(adapter, store)
    pipeline.initialize()
    return client, pipeline, MarketDataService(store), store


@pytest.mark.integration
def test_daily_pipeline_caches_normalizes_and_enforces_point_in_time(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    client, pipeline, service, store = data_foundation
    request = DailyBarRequest("600000", "20240102", "20240103")

    first = pipeline.ingest_daily_bars(request)
    second = pipeline.ingest_daily_bars(request)

    assert first.accepted == 2
    assert first.cached is False
    assert second.cached is True
    assert client.daily_calls == 1
    assert store.table_count("daily_bars") == 2

    before_second_bar = datetime(2024, 1, 3, 7, 0, tzinfo=UTC)
    visible = service.daily_bars(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        date(2024, 1, 2),
        date(2024, 1, 3),
        as_of=before_second_bar,
    )
    assert visible == []

    after_second_bar = datetime(2024, 1, 3, 7, 2, tzinfo=UTC)
    visible = service.daily_bars(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        date(2024, 1, 2),
        date(2024, 1, 3),
        as_of=after_second_bar,
    )
    assert visible == []
    retrieved_at = datetime(2024, 1, 5, 8, tzinfo=UTC)
    visible = service.daily_bars(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        date(2024, 1, 2),
        date(2024, 1, 3),
        as_of=retrieved_at,
    )
    assert [bar.timestamp.date() for bar in visible] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
    ]
    assert all(bar.available_at == retrieved_at for bar in visible)
    assert "retrieval time" in " ".join(first.warnings)


@pytest.mark.integration
def test_strict_pipeline_rejects_provider_adjusted_history(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    _, pipeline, _, store = data_foundation

    with pytest.raises(ValueError, match="rejects provider-adjusted bars"):
        pipeline.ingest_daily_bars(
            DailyBarRequest(
                "600000",
                "20240102",
                "20240103",
                adjustment=Adjustment.FORWARD,
            )
        )
    assert store.table_count("daily_bars") == 0


@pytest.mark.integration
def test_ingestion_rolls_back_domain_and_audit_writes_together(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, pipeline, _, store = data_foundation

    def fail_batch_write(batch: object) -> str:
        del batch
        raise RuntimeError("synthetic ingestion audit failure")

    monkeypatch.setattr(store, "save_ingestion_batch", fail_batch_write)

    with pytest.raises(RuntimeError, match="synthetic ingestion audit failure"):
        pipeline.ingest_daily_bars(DailyBarRequest("600000", "20240102", "20240103"))

    assert store.table_count("instruments") == 0
    assert store.table_count("daily_bars") == 0
    assert store.table_count("raw_dataset_fingerprints") == 0
    assert store.table_count("ingestion_batches") == 0


@pytest.mark.integration
def test_index_calendar_company_and_universe_ingestion(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    client, pipeline, service, store = data_foundation

    pipeline.ingest_daily_bars(
        DailyBarRequest(
            "000001",
            "20240102",
            "20240103",
            asset_type=AssetType.INDEX,
        )
    )
    pipeline.ingest_trading_calendar()
    pipeline.ingest_company_info("600000")
    pipeline.ingest_a_share_universe()

    assert (
        service.trading_days(
            Market.CHINA_A,
            date(2024, 1, 1),
            date(2024, 1, 4),
            as_of=datetime(2024, 1, 4, tzinfo=UTC),
        )
        == []
    )

    assert client.index_calls == 1
    assert store.table_count("daily_bars") == 2
    assert store.table_count("trading_calendar") == 2
    assert store.table_count("instruments") == 3

    as_of = datetime(2024, 1, 6, tzinfo=UTC)
    company = service.instrument(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        as_of=as_of,
    )
    assert company is not None
    assert company.name == "浦发银行"
    assert company.industry == "银行"
    assert company.listing_date == date(1999, 11, 10)
    assert service.trading_days(
        Market.CHINA_A,
        date(2024, 1, 1),
        date(2024, 1, 4),
        as_of=as_of,
    ) == [date(2024, 1, 2), date(2024, 1, 3)]


@pytest.mark.integration
def test_pit_population_records_batches_hashes_warnings_and_domain_tables(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    _, pipeline, service, store = data_foundation

    financial = pipeline.ingest_financial_statement("600000", "income")
    st_status = pipeline.ingest_special_treatment_status()
    suspended = pipeline.ingest_suspension_lifecycle("20240102")
    delisted = pipeline.ingest_delisted_statuses("sh")
    membership = pipeline.ingest_index_membership("000300")
    actions = pipeline.ingest_corporate_actions("600000")

    assert financial.accepted == 2
    assert financial.batch_id
    assert "publication timestamps" in " ".join(financial.warnings)
    assert "semantics remain unreviewed" in " ".join(financial.warnings)
    assert st_status.accepted == 1
    assert suspended.accepted == 1
    assert delisted.accepted == 1
    assert membership.accepted == 2
    assert actions.accepted >= 1
    assert store.table_count("fundamental_facts") == 2
    assert store.table_count("instrument_status_history") == 2
    assert store.table_count("universe_memberships") == 2
    assert store.table_count("corporate_actions") >= 1
    assert store.table_count("ingestion_batches") == 6
    assert store.table_count("raw_dataset_fingerprints") == 6
    assert store.table_count("data_availability_warnings") >= 6
    assert store.table_count("provider_limitations") == 10

    visible = service.fundamental_facts(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=datetime(2024, 1, 6, tzinfo=UTC),
    )
    assert visible
    assert visible[0].raw_data_hash


@pytest.mark.integration
def test_financial_numeric_conflict_rolls_back_all_domain_and_audit_writes(
    data_foundation: tuple[
        FakeAkShareClient, DataIngestionPipeline, MarketDataService, SQLiteStore,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, pipeline, _, store = data_foundation
    tables = (
        "instruments", "fundamental_facts", "ingestion_batches",
        "raw_dataset_fingerprints", "data_availability_warnings", "provider_limitations",
    )
    before = {table: store.table_count(table) for table in tables}

    def conflicting_frame(**kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame({
            "report_date": ["2023-12-31", "2023-12-31"],
            "metric_name": ["revenue", "profit"],
            "value": [100, 0],
            "金额": [100, 20],
        })

    monkeypatch.setattr(client, "stock_financial_benefit_new_ths", conflicting_frame)
    with pytest.raises(ValueError, match="financial value aliases disagree"):
        pipeline.ingest_financial_statement("600000", "income")
    assert {table: store.table_count(table) for table in tables} == before


@pytest.mark.integration
def test_pit_remediation_ingests_lifecycle_and_publication_evidence(
    data_foundation: tuple[
        FakeAkShareClient,
        DataIngestionPipeline,
        MarketDataService,
        SQLiteStore,
    ],
) -> None:
    _, pipeline, service, store = data_foundation

    suspension = pipeline.ingest_suspension_lifecycle("20240102")
    st_history = pipeline.ingest_shenzhen_st_history()
    schedule = pipeline.ingest_fundamental_publication_schedule("20231231")
    disclosures = pipeline.ingest_fundamental_disclosures(
        "600000",
        start_date="20240101",
        end_date="20240105",
    )
    financial = pipeline.ingest_financial_statement("600000", "income")

    assert suspension.accepted == 1
    assert st_history.accepted == 2
    assert schedule.accepted == 1
    assert disclosures.accepted == 2
    assert store.table_count("security_lifecycle_events") == 3
    assert store.table_count("fundamental_publication_events") == 3

    as_of = datetime(2024, 1, 6, tzinfo=UTC)
    lifecycle = store.security_lifecycle_events(
        "000001",
        Market.CHINA_A,
        AssetType.EQUITY,
        as_of=as_of,
    )
    assert {event.event_type.value for event in lifecycle} == {
        "st_enter",
        "st_exit",
        "suspension_started",
    }
    publications = store.fundamental_publication_events(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        as_of=as_of,
    )
    assert [event.revision for event in publications] == [0, 0, 1]
    facts = service.fundamental_facts(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        "revenue",
        as_of=as_of,
    )
    assert financial.accepted == 2
    assert facts[0].revision == 1
    assert facts[0].published_at == datetime(2024, 1, 4, 10, tzinfo=UTC)
    assert facts[0].available_at == datetime(2024, 1, 5, 8, tzinfo=UTC)
    assert facts[0].trust_level.value == "low"


def test_price_and_action_ingestion_do_not_replace_company_metadata_with_placeholders(
    data_foundation: tuple[
        FakeAkShareClient, DataIngestionPipeline, MarketDataService, SQLiteStore
    ],
) -> None:
    client, pipeline, service, store = data_foundation
    pipeline.ingest_company_info("600000")
    before = service.instrument(
        "600000",
        Market.CHINA_A,
        AssetType.EQUITY,
        as_of=datetime(2024, 1, 6, tzinfo=UTC),
    )
    assert before is not None and before.industry == "银行"
    later = DataIngestionPipeline(
        AkShareAdapter(client=client, clock=lambda: datetime(2024, 1, 6, tzinfo=UTC)),
        store,
    )
    later.ingest_daily_bars(DailyBarRequest("600000", "20240102", "20240103"))
    later.ingest_corporate_actions("600000")
    assert (
        service.instrument(
            "600000",
            Market.CHINA_A,
            AssetType.EQUITY,
            as_of=datetime(2024, 1, 7, tzinfo=UTC),
        )
        == before
    )
    assert store.table_count("instruments") == 1


def test_corporate_action_row_warning_failure_rolls_back_entire_batch(
    data_foundation: tuple[
        FakeAkShareClient, DataIngestionPipeline, MarketDataService, SQLiteStore
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, pipeline, _, store = data_foundation
    frame = client.stock_fhps_detail_em()
    frame = pd.concat([frame, frame.assign(方案进度="董事会决议通过")], ignore_index=True)
    monkeypatch.setattr(client, "stock_fhps_detail_em", lambda **kwargs: frame)
    original = store.save_data_availability_warning

    def fail_row_warning(warning: object) -> str:
        from tong_quant.data.models import DataAvailabilityWarning

        assert isinstance(warning, DataAvailabilityWarning)
        if warning.warning_code == "corporate_action_row_rejected":
            raise RuntimeError("synthetic row-warning failure")
        return original(warning)

    monkeypatch.setattr(store, "save_data_availability_warning", fail_row_warning)
    with pytest.raises(RuntimeError, match="row-warning"):
        pipeline.ingest_corporate_actions("600000")
    for table in (
        "instruments",
        "corporate_actions",
        "ingestion_batches",
        "raw_dataset_fingerprints",
        "data_availability_warnings",
    ):
        assert store.table_count(table) == 0


def _daily_frame(*, include_symbol: bool) -> pd.DataFrame:
    data: dict[str, object] = {
        "日期": [date(2024, 1, 2), date(2024, 1, 3)],
        "开盘": [10.0, 10.5],
        "收盘": [10.5, 10.8],
        "最高": [10.8, 11.0],
        "最低": [9.9, 10.3],
        "成交量": [1000, 1200],
        "成交额": [10000, 12500],
    }
    if include_symbol:
        data["股票代码"] = ["600000", "600000"]
    return pd.DataFrame(data)
