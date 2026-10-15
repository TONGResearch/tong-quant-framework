from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from tong_quant.data.models import DailyBarRequest, FundamentalPublicationEvent, RawDataset
from tong_quant.data.normalization.akshare import (
    build_bar_instrument,
    first_bar_available_at,
    normalize_daily_bars,
    normalize_financial_statement,
    normalize_trading_calendar,
)
from tong_quant.domain.enums import AssetType, AvailabilityPrecision, DataTrustLevel

RETRIEVED = datetime(2026, 10, 16, 3, tzinfo=UTC)


def raw(frame: pd.DataFrame) -> RawDataset:
    return RawDataset("synthetic", frame, RETRIEVED, "synthetic fixture", {})


def test_old_bar_and_instrument_are_not_backdated_to_close() -> None:
    dataset = raw(
        pd.DataFrame(
            {
                "日期": [date(2024, 1, 2)],
                "开盘": [10],
                "最高": [11],
                "最低": [9],
                "收盘": [10],
                "成交量": [100],
            }
        )
    )
    instrument = build_bar_instrument("600000", AssetType.EQUITY, first_bar_available_at(dataset))
    bar = normalize_daily_bars(
        dataset, DailyBarRequest("600000", "20240102", "20240102"), instrument
    )[0]
    assert bar.timestamp.date() == date(2024, 1, 2)
    assert bar.available_at == bar.ingested_at == instrument.available_at == RETRIEVED


@pytest.mark.parametrize("minutes", [0, -1])
def test_same_day_bar_before_conservative_close_filter_is_not_ingested(minutes: int) -> None:
    dataset = raw(
        pd.DataFrame(
            {
                "日期": [date(2026, 10, 16)],
                "开盘": [10],
                "最高": [11],
                "最低": [9],
                "收盘": [10],
                "成交量": [100],
            }
        )
    )
    dataset = replace(
        dataset, retrieved_at=datetime(2026, 10, 16, 7, tzinfo=UTC) + timedelta(minutes=minutes)
    )
    instrument = build_bar_instrument("600000", AssetType.EQUITY, dataset.retrieved_at)
    assert (
        normalize_daily_bars(dataset, DailyBarRequest("600000", "20261016", "20261016"), instrument)
        == []
    )


def test_calendar_preserves_only_returned_dates_from_retrieval_time() -> None:
    sessions = normalize_trading_calendar(
        raw(pd.DataFrame({"trade_date": [date(2024, 1, 2), date(2024, 1, 4)]}))
    )
    assert [session.trade_date for session in sessions] == [date(2024, 1, 2), date(2024, 1, 4)]
    assert all(session.is_open and session.available_at == RETRIEVED for session in sessions)


def test_disclosure_date_cannot_backdate_or_promote_a_current_numeric_fact() -> None:
    instrument = build_bar_instrument("600000", AssetType.EQUITY, RETRIEVED)
    publication = FundamentalPublicationEvent(
        instrument=instrument,
        period_end=date(2023, 12, 31),
        report_type="annual",
        published_at=datetime(2024, 4, 1, tzinfo=UTC),
        available_at=datetime(2024, 4, 1, tzinfo=UTC),
        title="Synthetic report",
        revision=1,
        source="fixture",
        source_reference="https://example.invalid/report",
        raw_data_hash="a" * 64,
        availability_precision=AvailabilityPrecision.EXACT,
        trust_level=DataTrustLevel.HIGH,
    )
    dataset = raw(
        pd.DataFrame({"report_date": ["2023-12-31"], "metric_name": ["revenue"], "value": [123]})
    )
    facts = normalize_financial_statement(
        dataset, instrument, batch_id="fixture", publication_events=(publication,)
    )
    assert facts[0].value == Decimal("123")
    assert facts[0].published_at == publication.published_at
    assert facts[0].available_at == RETRIEVED
    assert facts[0].availability_precision is AvailabilityPrecision.RETRIEVAL_TIME
    assert facts[0].trust_level is DataTrustLevel.LOW
    future = replace(
        publication,
        available_at=RETRIEVED + timedelta(days=1),
        published_at=RETRIEVED + timedelta(days=1),
    )
    future_facts = normalize_financial_statement(
        dataset, instrument, batch_id="fixture", publication_events=(future,)
    )
    assert future_facts[0].published_at == RETRIEVED
    assert future_facts[0].revision == 0
