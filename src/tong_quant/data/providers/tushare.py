import os
from collections.abc import Callable
from datetime import UTC, datetime
from time import sleep
from typing import Any, Protocol, cast

import pandas as pd
import tushare as ts

from tong_quant.core.exceptions import ConfigurationError, DataProviderError
from tong_quant.data.calibration.models import (
    CalibrationDataset,
    CalibrationQuery,
    CalibrationRecord,
    ProviderCalibrationSnapshot,
)


class TushareClient(Protocol):
    def namechange(self, **kwargs: Any) -> pd.DataFrame: ...

    def suspend_d(self, **kwargs: Any) -> pd.DataFrame: ...

    def stock_basic(self, **kwargs: Any) -> pd.DataFrame: ...

    def disclosure_date(self, **kwargs: Any) -> pd.DataFrame: ...

    def income(self, **kwargs: Any) -> pd.DataFrame: ...

    def index_weight(self, **kwargs: Any) -> pd.DataFrame: ...


class TushareCalibrationAdapter:
    source_id = "tushare"
    index_codes = {
        CalibrationDataset.CSI300_MEMBERSHIP: "000300.SH",
        CalibrationDataset.CSI500_MEMBERSHIP: "000905.SH",
        CalibrationDataset.CSI1000_MEMBERSHIP: "000852.SH",
    }

    def __init__(
        self,
        *,
        client: TushareClient | None = None,
        clock: Callable[[], datetime] | None = None,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if client is None:
            token = os.getenv("TUSHARE_TOKEN")
            if not token:
                raise ConfigurationError(
                    "TUSHARE_TOKEN environment variable is required for live Tushare access"
                )
            client = ts.pro_api(token)
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._sleeper = sleeper

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        handlers = {
            CalibrationDataset.SECURITY_LIFECYCLE: self._security_lifecycle,
            CalibrationDataset.ST_STATUS: self._st_status,
            CalibrationDataset.SUSPENSION_STATUS: self._suspension_status,
            CalibrationDataset.DELISTING_RECORDS: self._delisting_records,
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES: (
                self._financial_publication_dates
            ),
            CalibrationDataset.FUNDAMENTAL_REVISIONS: self._fundamental_revisions,
            CalibrationDataset.CSI300_MEMBERSHIP: self._index_membership,
            CalibrationDataset.CSI500_MEMBERSHIP: self._index_membership,
            CalibrationDataset.CSI1000_MEMBERSHIP: self._index_membership,
        }
        records, limitations = handlers[query.dataset](query)
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=records,
            limitations=limitations,
        )

    def _security_lifecycle(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        st_records, st_limitations = self._st_status(query)
        suspension_records, suspension_limitations = self._suspension_status(query)
        delisting_records, delisting_limitations = self._delisting_records(query)
        return (
            (*st_records, *suspension_records, *delisting_records),
            (*st_limitations, *suspension_limitations, *delisting_limitations),
        )

    def _st_status(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        frame = self._call(
            "namechange",
            lambda: self._client.namechange(
                **_compact(
                    ts_code=query.parameters.get("ts_code"),
                    start_date=query.parameters.get("start_date"),
                    end_date=query.parameters.get("end_date"),
                    fields=(
                        "ts_code,name,start_date,end_date,ann_date,change_reason"
                    ),
                )
            ),
        )
        records = []
        for row in _rows(frame):
            name = _text(row.get("name"))
            if not _is_st_name(name):
                continue
            symbol = _symbol(row.get("ts_code"))
            effective_date = _date_text(row.get("start_date"))
            if not symbol or not effective_date:
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{effective_date}",
                    fields={
                        "is_st": True,
                        "effective_date": effective_date,
                        "effective_to": _date_text(row.get("end_date")),
                        "name": name,
                        "ann_date": _date_text(row.get("ann_date")),
                    },
                )
            )
        return tuple(records), (
            "Tushare namechange is historical name evidence, not an exchange status ledger",
        )

    def _suspension_status(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        frame = self._call(
            "suspend_d",
            lambda: self._client.suspend_d(
                **_compact(
                    ts_code=query.parameters.get("ts_code"),
                    trade_date=query.parameters.get("trade_date"),
                    start_date=query.parameters.get("start_date"),
                    end_date=query.parameters.get("end_date"),
                    fields="ts_code,trade_date,suspend_timing,suspend_type",
                )
            ),
        )
        records = []
        for row in _rows(frame):
            symbol = _symbol(row.get("ts_code"))
            effective_date = _date_text(row.get("trade_date"))
            suspend_type = _text(row.get("suspend_type")).upper()
            if not symbol or not effective_date or suspend_type not in {"S", "R"}:
                continue
            event_type = (
                "suspension_started" if suspend_type == "S" else "trading_resumed"
            )
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{effective_date}:{event_type}",
                    fields={
                        "event_type": event_type,
                        "effective_date": effective_date,
                        "timing": _text(row.get("suspend_timing")),
                    },
                )
            )
        return tuple(records), (
            "suspend_d availability depends on account permissions and provider coverage",
        )

    def _delisting_records(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        frame = self._call(
            "stock_basic",
            lambda: self._client.stock_basic(
                list_status="D",
                fields=(
                    "ts_code,symbol,name,exchange,list_status,list_date,delist_date"
                ),
            ),
        )
        records = []
        for row in _rows(frame):
            symbol = _symbol(row.get("ts_code") or row.get("symbol"))
            delist_date = _date_text(row.get("delist_date"))
            if not symbol or not delist_date:
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{delist_date}",
                    fields={
                        "delist_date": delist_date,
                        "name": _text(row.get("name")),
                        "exchange": _text(row.get("exchange")),
                    },
                )
            )
        return tuple(records), (
            "stock_basic delisting dates do not reconstruct warning-period announcements",
        )

    def _financial_publication_dates(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        period_end = _required(query, "period_end")
        frame = self._call(
            "disclosure_date",
            lambda: self._client.disclosure_date(
                **_compact(
                    ts_code=query.parameters.get("ts_code"),
                    end_date=period_end,
                    fields=(
                        "ts_code,ann_date,end_date,pre_date,actual_date,modify_date"
                    ),
                )
            ),
        )
        records = []
        for row in _rows(frame):
            symbol = _symbol(row.get("ts_code"))
            report_period = _date_text(row.get("end_date"))
            actual_date = _date_text(row.get("actual_date"))
            if not symbol or not report_period or not actual_date:
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{report_period}",
                    fields={
                        "actual_date": actual_date,
                        "ann_date": _date_text(row.get("ann_date")),
                        "modify_date": _date_text(row.get("modify_date")),
                    },
                )
            )
        return tuple(records), (
            "disclosure_date is date-only and requires at least the provider permission tier",
        )

    def _fundamental_revisions(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        ts_code = query.parameters.get("ts_code")
        if not ts_code:
            symbol = _required(query, "symbol")
            ts_code = _ts_code(symbol)
        frame = self._call(
            "income",
            lambda: self._client.income(
                **_compact(
                    ts_code=ts_code,
                    start_date=query.parameters.get("start_date"),
                    end_date=query.parameters.get("end_date"),
                    period=query.parameters.get("period_end"),
                    fields=(
                        "ts_code,ann_date,f_ann_date,end_date,report_type,"
                        "update_flag,total_revenue,revenue"
                    ),
                )
            ),
        )
        return _revision_records(frame), (
            "income revisions require sufficient Tushare points and may not expose "
            "every raw filing",
        )

    def _index_membership(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        index_code = self.index_codes[query.dataset]
        frame = self._call(
            "index_weight",
            lambda: self._client.index_weight(
                **_compact(
                    index_code=index_code,
                    trade_date=query.parameters.get("trade_date"),
                    start_date=query.parameters.get("start_date"),
                    end_date=query.parameters.get("end_date"),
                )
            ),
        )
        records = []
        for row in _rows(frame):
            symbol = _symbol(row.get("con_code"))
            if not symbol:
                continue
            records.append(
                CalibrationRecord(
                    key=symbol,
                    fields={
                        "member": True,
                        "effective_date": _date_text(row.get("trade_date")),
                        "weight": _number(row.get("weight")),
                    },
                )
            )
        return tuple(_deduplicate(records)), (
            "index_weight is monthly and requires sufficient Tushare points",
        )

    def _call(self, dataset: str, fetch: Callable[[], pd.DataFrame]) -> pd.DataFrame:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return fetch().copy()
            except Exception as error:
                last_error = error
                if attempt < self._max_attempts:
                    self._sleeper(self._retry_delay_seconds * attempt)
        raise DataProviderError(
            f"Tushare dataset {dataset} failed after {self._max_attempts} attempts"
        ) from last_error


def _revision_records(frame: pd.DataFrame) -> tuple[CalibrationRecord, ...]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in _rows(frame):
        symbol = _symbol(row.get("ts_code"))
        period_end = _date_text(row.get("end_date"))
        if symbol and period_end:
            grouped.setdefault((symbol, period_end), []).append(row)
    records: list[CalibrationRecord] = []
    for (symbol, period_end), rows in sorted(grouped.items()):
        ordered = sorted(
            rows,
            key=lambda row: (
                _date_text(row.get("f_ann_date") or row.get("ann_date")),
                _text(row.get("report_type")),
                _text(row.get("update_flag")),
            ),
        )
        for revision, revision_row in enumerate(ordered):
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{period_end}:{revision}",
                    fields={
                        "published_at": _date_text(
                            revision_row.get("f_ann_date")
                            or revision_row.get("ann_date")
                        ),
                        "report_type": _text(revision_row.get("report_type")),
                        "update_flag": _text(revision_row.get("update_flag")),
                        "total_revenue": _number(revision_row.get("total_revenue")),
                        "revenue": _number(revision_row.get("revenue")),
                    },
                )
            )
    return tuple(records)


def _compact(**values: str | None) -> dict[str, str]:
    return {
        key: value
        for key, value in values.items()
        if value is not None and value != ""
    }


def _required(query: CalibrationQuery, key: str) -> str:
    value = query.parameters.get(key)
    if not value:
        raise ValueError(f"{query.dataset.value} requires parameter {key}")
    return value


def _symbol(value: object) -> str:
    return _text(value).split(".", maxsplit=1)[0].zfill(6)


def _ts_code(symbol: str) -> str:
    if symbol.startswith(("6", "9")):
        suffix = "SH"
    elif symbol.startswith(("4", "8")):
        suffix = "BJ"
    else:
        suffix = "SZ"
    return f"{symbol}.{suffix}"


def _text(value: object) -> str:
    if value is None or bool(pd.isna(cast(Any, value))):
        return ""
    return str(value).strip()


def _date_text(value: object) -> str:
    text = _text(value).replace("-", "")
    return text if len(text) == 8 and text.isdigit() else ""


def _number(value: object) -> float | None:
    if value is None or bool(pd.isna(cast(Any, value))):
        return None
    return float(cast(Any, value))


def _is_st_name(name: str) -> bool:
    return name.upper().replace(" ", "").lstrip("*").startswith(("ST", "SST"))


def _deduplicate(records: list[CalibrationRecord]) -> tuple[CalibrationRecord, ...]:
    return tuple({record.key: record for record in records}.values())


def _rows(frame: pd.DataFrame) -> tuple[dict[str, object], ...]:
    return tuple(
        {str(key): value for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    )


__all__ = ["TushareCalibrationAdapter", "TushareClient"]
