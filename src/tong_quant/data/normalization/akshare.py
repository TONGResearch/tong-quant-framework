import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.data.models import (
    DailyBarRequest,
    FundamentalPublicationEvent,
    RawDataset,
    SecurityLifecycleEvent,
)
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    CorporateActionType,
    DataTrustLevel,
    LifecycleEventType,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import (
    Bar,
    CorporateAction,
    FundamentalFact,
    Instrument,
    InstrumentStatus,
    TradingSession,
    UniverseMembership,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")
MARKET_CLOSE = time(hour=15)


def normalize_daily_bars(
    dataset: RawDataset,
    request: DailyBarRequest,
    instrument: Instrument,
) -> list[Bar]:
    bars: list[Bar] = []
    for row in dataset.frame.to_dict(orient="records"):
        trade_date = _to_date(row["日期"])
        timestamp = datetime.combine(trade_date, MARKET_CLOSE, tzinfo=SHANGHAI)
        available_at = timestamp + timedelta(minutes=1)
        if available_at > dataset.retrieved_at.astimezone(SHANGHAI):
            continue
        bars.append(
            Bar(
                instrument=instrument,
                timestamp=timestamp,
                available_at=available_at,
                open=_decimal(row["开盘"]),
                high=_decimal(row["最高"]),
                low=_decimal(row["最低"]),
                close=_decimal(row["收盘"]),
                volume=_decimal(row["成交量"]),
                turnover=_optional_decimal(row.get("成交额")),
                adjustment=request.adjustment,
                source=dataset.source,
                ingested_at=dataset.retrieved_at,
            )
        )
    return bars


def normalize_trading_calendar(dataset: RawDataset) -> list[TradingSession]:
    sessions = []
    for raw_date in dataset.frame["trade_date"].tolist():
        trade_date = _to_date(raw_date)
        known_at = datetime.combine(trade_date, time.min, tzinfo=SHANGHAI)
        sessions.append(
            TradingSession(
                market=Market.CHINA_A,
                trade_date=trade_date,
                is_open=True,
                available_at=known_at,
                source=dataset.source,
            )
        )
    return sessions


def normalize_company_info(dataset: RawDataset, symbol: str) -> Instrument:
    values = {
        str(row["item"]): row["value"]
        for row in dataset.frame.to_dict(orient="records")
        if pd.notna(row["item"])
    }
    listing_date = _optional_date(values.get("上市时间"))
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=str(values.get("股票简称") or symbol),
        asset_type=AssetType.EQUITY,
        currency="CNY",
        lot_size=100,
        exchange=infer_exchange(symbol),
        industry=_optional_text(values.get("行业")),
        listing_date=listing_date,
        available_at=dataset.retrieved_at,
        source=dataset.source,
    )


def normalize_universe(dataset: RawDataset) -> list[Instrument]:
    instruments = []
    for row in dataset.frame.to_dict(orient="records"):
        symbol = str(row["代码"]).split(".")[0].zfill(6)
        instruments.append(
            Instrument(
                symbol=symbol,
                market=Market.CHINA_A,
                name=str(row["名称"]),
                asset_type=AssetType.EQUITY,
                currency="CNY",
                lot_size=100,
                exchange=infer_exchange(symbol),
                available_at=dataset.retrieved_at,
                source=dataset.source,
            )
        )
    return instruments


def normalize_financial_statement(
    dataset: RawDataset,
    instrument: Instrument,
    *,
    batch_id: str,
    publication_events: Sequence[FundamentalPublicationEvent] = (),
) -> list[FundamentalFact]:
    facts: list[FundamentalFact] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        metric = _optional_text(row.get("metric_name") or row.get("指标名称"))
        if metric is None:
            continue
        value = _optional_decimal(row.get("value") or row.get("金额"))
        if value is None:
            continue
        period_end = _optional_date(
            row.get("report_date")
            or row.get("报告期")
            or row.get("报告日期")
            or row.get("date")
        )
        if period_end is None:
            continue
        publication = _latest_publication(publication_events, period_end)
        facts.append(
            FundamentalFact(
                instrument=instrument,
                metric=metric,
                period_end=period_end,
                published_at=(
                    dataset.retrieved_at
                    if publication is None
                    else publication.published_at
                ),
                available_at=(
                    dataset.retrieved_at
                    if publication is None
                    else publication.available_at
                ),
                value=value,
                currency="CNY",
                revision=0 if publication is None else publication.revision,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=(
                    AvailabilityPrecision.RETRIEVAL_TIME
                    if publication is None
                    else publication.availability_precision
                ),
                trust_level=(
                    DataTrustLevel.LOW
                    if publication is None
                    else DataTrustLevel.MEDIUM
                ),
            )
        )
    return facts


def normalize_current_status_snapshot(
    dataset: RawDataset,
    *,
    status: SecurityStatus,
    is_tradable: bool,
    batch_id: str,
) -> list[InstrumentStatus]:
    statuses: list[InstrumentStatus] = []
    raw_hash = dataset.content_hash()
    effective_from = dataset.retrieved_at.astimezone(SHANGHAI).date()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        if symbol is None:
            continue
        statuses.append(
            InstrumentStatus(
                instrument=Instrument(
                    symbol=symbol,
                    market=Market.CHINA_A,
                    name=str(row.get("名称") or row.get("股票简称") or symbol),
                    asset_type=AssetType.EQUITY,
                    currency="CNY",
                    lot_size=100,
                    exchange=infer_exchange(symbol),
                    available_at=dataset.retrieved_at,
                    source=dataset.source,
                ),
                effective_from=effective_from,
                status=status,
                is_tradable=is_tradable,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.LOW,
            )
        )
    return statuses


def normalize_delisted_statuses(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[InstrumentStatus]:
    statuses: list[InstrumentStatus] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        if symbol is None:
            continue
        effective_from = _optional_date(
            row.get("终止上市日期")
            or row.get("退市日期")
            or row.get("摘牌日期")
            or row.get("delist_date")
        )
        if effective_from is None:
            effective_from = dataset.retrieved_at.astimezone(SHANGHAI).date()
        statuses.append(
            InstrumentStatus(
                instrument=Instrument(
                    symbol=symbol,
                    market=Market.CHINA_A,
                    name=str(row.get("证券简称") or row.get("股票简称") or symbol),
                    asset_type=AssetType.EQUITY,
                    currency="CNY",
                    lot_size=100,
                    exchange=infer_exchange(symbol),
                    delisting_date=effective_from,
                    available_at=dataset.retrieved_at,
                    source=dataset.source,
                ),
                effective_from=effective_from,
                status=SecurityStatus.DELISTED,
                is_tradable=False,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
    return statuses


def normalize_index_membership(
    dataset: RawDataset,
    *,
    universe: str,
    batch_id: str,
) -> list[UniverseMembership]:
    memberships: list[UniverseMembership] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        if symbol is None:
            continue
        effective_from = _optional_date(row.get("日期") or row.get("date"))
        if effective_from is None:
            effective_from = dataset.retrieved_at.astimezone(SHANGHAI).date()
        instrument = Instrument(
            symbol=symbol,
            market=Market.CHINA_A,
            name=str(row.get("成分券名称") or row.get("品种名称") or symbol),
            asset_type=AssetType.EQUITY,
            currency="CNY",
            lot_size=100,
            exchange=infer_exchange(symbol),
            available_at=dataset.retrieved_at,
            source=dataset.source,
        )
        memberships.append(
            UniverseMembership(
                universe=universe,
                instrument=instrument,
                effective_from=effective_from,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
    return memberships


def normalize_corporate_actions(
    dataset: RawDataset,
    instrument: Instrument,
    *,
    batch_id: str,
) -> list[CorporateAction]:
    actions: list[CorporateAction] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        effective_date = _optional_date(
            row.get("除权除息日") or row.get("除息日") or row.get("股权登记日")
        )
        if effective_date is None:
            continue
        cash = _optional_decimal(row.get("现金分红") or row.get("派息"))
        ratio = _optional_decimal(row.get("送转股份") or row.get("转增") or row.get("送股"))
        if cash is not None:
            actions.append(
                CorporateAction(
                    instrument=instrument,
                    action_type=CorporateActionType.DIVIDEND,
                    effective_date=effective_date,
                    available_at=dataset.retrieved_at,
                    cash_amount=cash,
                    currency="CNY",
                    source=dataset.source,
                    raw_data_hash=raw_hash,
                    batch_id=batch_id,
                    provider_dataset=dataset.dataset,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.MEDIUM,
                )
            )
        if ratio is not None:
            actions.append(
                CorporateAction(
                    instrument=instrument,
                    action_type=CorporateActionType.SPLIT,
                    effective_date=effective_date,
                    available_at=dataset.retrieved_at,
                    ratio=ratio,
                    source=dataset.source,
                    raw_data_hash=raw_hash,
                    batch_id=batch_id,
                    provider_dataset=dataset.dataset,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.MEDIUM,
                )
            )
    return actions


def normalize_suspension_lifecycle(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[SecurityLifecycleEvent]:
    events: list[SecurityLifecycleEvent] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        start_date = _optional_date(row.get("停牌时间"))
        if symbol is None or start_date is None:
            continue
        instrument = _snapshot_instrument(dataset, row, symbol)
        details = {
            "reason": str(row.get("停牌原因") or ""),
            "duration": str(row.get("停牌期限") or ""),
        }
        events.append(
            SecurityLifecycleEvent(
                instrument=instrument,
                event_type=LifecycleEventType.SUSPENSION_STARTED,
                effective_date=start_date,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                details=details,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
        resumed_on = _optional_date(
            row.get("停牌截止时间") or row.get("预计复牌时间")
        )
        if resumed_on is not None:
            events.append(
                SecurityLifecycleEvent(
                    instrument=instrument,
                    event_type=LifecycleEventType.TRADING_RESUMED,
                    effective_date=resumed_on,
                    available_at=dataset.retrieved_at,
                    source=dataset.source,
                    details=details,
                    raw_data_hash=raw_hash,
                    batch_id=batch_id,
                    provider_dataset=dataset.dataset,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.MEDIUM,
                )
            )
    return events


def normalize_st_name_change_lifecycle(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[SecurityLifecycleEvent]:
    events: list[SecurityLifecycleEvent] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        changed_on = _optional_date(row.get("变更日期"))
        old_name = _optional_text(
            row.get("变更前简称")
            or row.get("变更前证券简称")
            or row.get("变更前名称")
        )
        new_name = _optional_text(
            row.get("变更后简称")
            or row.get("变更后证券简称")
            or row.get("变更后名称")
        )
        if symbol is None or changed_on is None or old_name is None or new_name is None:
            continue
        was_st = _is_st_name(old_name)
        is_st = _is_st_name(new_name)
        if was_st == is_st:
            continue
        event_type = (
            LifecycleEventType.ST_ENTER if is_st else LifecycleEventType.ST_EXIT
        )
        events.append(
            SecurityLifecycleEvent(
                instrument=_snapshot_instrument(dataset, row, symbol, name=new_name),
                event_type=event_type,
                effective_date=changed_on,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                details={"old_name": old_name, "new_name": new_name},
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
    return events


def normalize_delisting_lifecycle(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[SecurityLifecycleEvent]:
    events: list[SecurityLifecycleEvent] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        delisted_on = _optional_date(
            row.get("终止上市日期")
            or row.get("退市日期")
            or row.get("摘牌日期")
        )
        if symbol is None or delisted_on is None:
            continue
        events.append(
            SecurityLifecycleEvent(
                instrument=_snapshot_instrument(dataset, row, symbol),
                event_type=LifecycleEventType.DELISTED,
                effective_date=delisted_on,
                available_at=dataset.retrieved_at,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
    return events


def normalize_market_universe_snapshot(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[UniverseMembership]:
    effective_from = dataset.retrieved_at.astimezone(SHANGHAI).date()
    raw_hash = dataset.content_hash()
    return [
        UniverseMembership(
            universe="market:china_a",
            instrument=instrument,
            effective_from=effective_from,
            available_at=dataset.retrieved_at,
            source=dataset.source,
            raw_data_hash=raw_hash,
            batch_id=batch_id,
            provider_dataset=dataset.dataset,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.LOW,
        )
        for instrument in normalize_universe(dataset)
    ]


def normalize_publication_schedule(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[FundamentalPublicationEvent]:
    period_end = _optional_date(dataset.parameters.get("period_end"))
    if period_end is None:
        return []
    events: list[FundamentalPublicationEvent] = []
    raw_hash = dataset.content_hash()
    for row in dataset.frame.to_dict(orient="records"):
        symbol = _row_symbol(row)
        disclosed_on = _optional_date(row.get("实际披露时间"))
        if symbol is None or disclosed_on is None:
            continue
        published_at = datetime.combine(disclosed_on, time.max, tzinfo=SHANGHAI)
        events.append(
            FundamentalPublicationEvent(
                instrument=_snapshot_instrument(
                    dataset,
                    row,
                    symbol,
                    available_at=published_at,
                ),
                period_end=period_end,
                report_type=_report_type_for_period(period_end),
                published_at=published_at,
                available_at=published_at,
                title=f"{period_end.isoformat()} actual disclosure date",
                revision=0,
                source=dataset.source,
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.DATE_ONLY,
                trust_level=DataTrustLevel.MEDIUM,
            )
        )
    return events


def normalize_fundamental_disclosures(
    dataset: RawDataset,
    *,
    batch_id: str,
) -> list[FundamentalPublicationEvent]:
    candidates: list[tuple[date, datetime, Mapping[object, Any], str]] = []
    for row in dataset.frame.to_dict(orient="records"):
        title = str(row.get("公告标题") or "").strip()
        period_end = _period_end_from_title(title)
        published_at = _optional_datetime(row.get("公告时间"))
        if period_end is None or published_at is None:
            continue
        candidates.append((period_end, published_at, row, title))
    candidates.sort(key=lambda item: (item[0], item[1], item[3]))
    revisions: dict[date, int] = {}
    events: list[FundamentalPublicationEvent] = []
    raw_hash = dataset.content_hash()
    for period_end, published_at, candidate_row, title in candidates:
        symbol = _row_symbol(candidate_row)
        if symbol is None:
            continue
        revision = revisions.get(period_end, 0)
        revisions[period_end] = revision + 1
        events.append(
            FundamentalPublicationEvent(
                instrument=_snapshot_instrument(
                    dataset,
                    candidate_row,
                    symbol,
                    available_at=published_at,
                ),
                period_end=period_end,
                report_type=_report_type_for_period(period_end),
                published_at=published_at,
                available_at=published_at,
                title=title,
                revision=revision,
                source=dataset.source,
                source_reference=str(candidate_row.get("公告链接") or ""),
                raw_data_hash=raw_hash,
                batch_id=batch_id,
                provider_dataset=dataset.dataset,
                availability_precision=AvailabilityPrecision.EXACT,
                trust_level=DataTrustLevel.HIGH,
            )
        )
    return events


def build_index_instrument(symbol: str, retrieved_at: datetime) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=symbol,
        asset_type=AssetType.INDEX,
        currency="CNY",
        lot_size=1,
        exchange=infer_exchange(symbol),
        available_at=retrieved_at,
        source="akshare",
    )


def build_bar_instrument(
    symbol: str,
    asset_type: AssetType,
    available_at: datetime,
) -> Instrument:
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=symbol,
        asset_type=asset_type,
        currency="CNY",
        lot_size=1 if asset_type is AssetType.INDEX else 100,
        exchange=infer_exchange(symbol),
        available_at=available_at,
        source="akshare",
    )


def first_bar_available_at(dataset: RawDataset) -> datetime:
    first_date = min(_to_date(value) for value in dataset.frame["日期"].tolist())
    return datetime.combine(first_date, MARKET_CLOSE, tzinfo=SHANGHAI) + timedelta(minutes=1)


def infer_exchange(symbol: str) -> str:
    if symbol.startswith(("6", "9")):
        return "XSHG"
    if symbol.startswith(("0", "2", "3")):
        return "XSHE"
    if symbol.startswith(("4", "8")):
        return "XBSE"
    return "UNKNOWN"


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    return date.fromisoformat(text)


def _optional_date(value: Any) -> date | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).replace(".0", "").strip()
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").date()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    return _decimal(value)


def _row_symbol(row: Mapping[object, Any]) -> str | None:
    value = (
        row.get("代码")
        or row.get("股票代码")
        or row.get("证券代码")
        or row.get("成分券代码")
        or row.get("品种代码")
        or row.get("symbol")
    )
    if value is None or pd.isna(value):
        return None
    return str(value).split(".")[0].zfill(6)


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_datetime(value: Any) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(SHANGHAI)
    else:
        timestamp = timestamp.tz_convert(SHANGHAI)
    return timestamp.to_pydatetime()


def _snapshot_instrument(
    dataset: RawDataset,
    row: Mapping[object, Any],
    symbol: str,
    *,
    name: str | None = None,
    available_at: datetime | None = None,
) -> Instrument:
    resolved_name = name or str(
        row.get("名称")
        or row.get("股票简称")
        or row.get("证券简称")
        or row.get("简称")
        or symbol
    )
    return Instrument(
        symbol=symbol,
        market=Market.CHINA_A,
        name=resolved_name,
        asset_type=AssetType.EQUITY,
        currency="CNY",
        lot_size=100,
        exchange=infer_exchange(symbol),
        available_at=available_at or dataset.retrieved_at,
        source=dataset.source,
    )


def _is_st_name(value: str) -> bool:
    normalized = value.upper().replace(" ", "").lstrip("*")
    return normalized.startswith("ST") or normalized.startswith("SST")


def _report_type_for_period(period_end: date) -> str:
    return {
        3: "first_quarter",
        6: "half_year",
        9: "third_quarter",
        12: "annual",
    }.get(period_end.month, "periodic_report")


def _period_end_from_title(title: str) -> date | None:
    year_match = re.search(r"(20\d{2})年", title)
    if year_match is None:
        return None
    year = int(year_match.group(1))
    if re.search(r"第一季度|一季度", title):
        return date(year, 3, 31)
    if re.search(r"半年度|半年报|中期报告", title):
        return date(year, 6, 30)
    if re.search(r"第三季度|三季度", title):
        return date(year, 9, 30)
    if re.search(r"年度报告|年报", title):
        return date(year, 12, 31)
    return None


def _latest_publication(
    events: Sequence[FundamentalPublicationEvent],
    period_end: date,
) -> FundamentalPublicationEvent | None:
    matching = [event for event in events if event.period_end == period_end]
    if not matching:
        return None
    return max(matching, key=lambda event: (event.available_at, event.revision))


def normalize_instruments(datasets: Sequence[RawDataset]) -> list[Instrument]:
    instruments: list[Instrument] = []
    for dataset in datasets:
        if dataset.dataset == "a_share_universe":
            instruments.extend(normalize_universe(dataset))
    return instruments
