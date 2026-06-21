import re
from collections.abc import Mapping
from datetime import date
from typing import Any, cast

import pandas as pd

from tong_quant.data.calibration.models import (
    CalibrationDataset,
    CalibrationQuery,
    CalibrationRecord,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.providers.akshare import AkShareAdapter


class AkShareCalibrationAdapter:
    source_id = "akshare"
    index_symbols = {
        CalibrationDataset.CSI300_MEMBERSHIP: "000300",
        CalibrationDataset.CSI500_MEMBERSHIP: "000905",
        CalibrationDataset.CSI1000_MEMBERSHIP: "000852",
    }

    def __init__(self, adapter: AkShareAdapter) -> None:
        self._adapter = adapter

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
            CalibrationDataset.CORPORATE_ACTIONS: self._corporate_actions,
            CalibrationDataset.UNIVERSE_COVERAGE: self._universe_coverage,
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
        del query
        frame = self._adapter.shenzhen_name_changes().dataset.frame
        records = []
        for row in _rows(frame):
            symbol = _symbol(row, "证券代码", "股票代码", "代码")
            effective_date = _date_text(row.get("变更日期"))
            new_name = _text(
                row.get("变更后简称")
                or row.get("变更后证券简称")
                or row.get("变更后名称")
            )
            if not symbol or not effective_date or not _is_st_name(new_name):
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{effective_date}",
                    fields={
                        "is_st": True,
                        "effective_date": effective_date,
                        "effective_to": None,
                        "name": new_name,
                        "ann_date": None,
                    },
                )
            )
        return tuple(records), (
            "AKShare dated ST name-change evidence currently covers Shenzhen only",
        )

    def _suspension_status(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        trade_date = _required(query, "trade_date")
        frame = self._adapter.suspension_events(trade_date).dataset.frame
        records = []
        for row in _rows(frame):
            symbol = _symbol(row, "代码", "股票代码", "证券代码")
            start_date = _date_text(row.get("停牌时间"))
            if symbol and start_date:
                records.append(
                    CalibrationRecord(
                        key=f"{symbol}:{start_date}:suspension_started",
                        fields={
                            "event_type": "suspension_started",
                            "effective_date": start_date,
                            "timing": "",
                        },
                    )
                )
            resume_date = _date_text(
                row.get("停牌截止时间") or row.get("预计复牌时间")
            )
            if symbol and resume_date:
                records.append(
                    CalibrationRecord(
                        key=f"{symbol}:{resume_date}:trading_resumed",
                        fields={
                            "event_type": "trading_resumed",
                            "effective_date": resume_date,
                            "timing": "",
                        },
                    )
                )
        return tuple(records), (
            "AKShare suspension history is queried by date and retained at retrieval time",
        )

    def _delisting_records(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        del query
        records = []
        for exchange in ("sh", "sz"):
            frame = self._adapter.delisted_stocks(exchange).dataset.frame
            for row in _rows(frame):
                symbol = _symbol(row, "代码", "股票代码", "证券代码")
                delist_date = _date_text(
                    row.get("终止上市日期")
                    or row.get("退市日期")
                    or row.get("摘牌日期")
                )
                if not symbol or not delist_date:
                    continue
                records.append(
                    CalibrationRecord(
                        key=f"{symbol}:{delist_date}",
                        fields={
                            "delist_date": delist_date,
                            "name": _text(
                                row.get("证券简称")
                                or row.get("股票简称")
                                or row.get("名称")
                            ),
                            "exchange": exchange.upper(),
                        },
                    )
                )
        return _deduplicate(records), (
            "AKShare delisting records do not prove complete warning-period coverage",
        )

    def _financial_publication_dates(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        period_end = _required(query, "period_end")
        frame = self._adapter.fundamental_publication_schedule(period_end).dataset.frame
        records = []
        for row in _rows(frame):
            symbol = _symbol(row, "股票代码", "证券代码", "代码")
            actual_date = _date_text(row.get("实际披露时间"))
            if not symbol or not actual_date:
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{period_end}",
                    fields={
                        "actual_date": actual_date,
                        "ann_date": None,
                        "modify_date": None,
                    },
                )
            )
        return tuple(records), (
            "AKShare actual disclosure schedule is date-only",
        )

    def _fundamental_revisions(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        symbol = _required(query, "symbol")
        frame = self._adapter.fundamental_disclosures(
            symbol,
            start_date=_required(query, "start_date"),
            end_date=_required(query, "end_date"),
        ).dataset.frame
        grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
        for row in _rows(frame):
            row_symbol = _symbol(row, "代码", "股票代码", "证券代码") or symbol
            period_end = _period_end_from_title(_text(row.get("公告标题")))
            if period_end:
                grouped.setdefault((row_symbol, period_end), []).append(row)
        records = []
        for (row_symbol, period_end), rows in sorted(grouped.items()):
            ordered = sorted(rows, key=lambda row: _text(row.get("公告时间")))
            for revision, revision_row in enumerate(ordered):
                records.append(
                    CalibrationRecord(
                        key=f"{row_symbol}:{period_end}:{revision}",
                        fields={
                            "published_at": _date_text(revision_row.get("公告时间")),
                            "report_type": _report_type(period_end),
                            "update_flag": "1" if revision == len(ordered) - 1 else "0",
                            "total_revenue": None,
                            "revenue": None,
                        },
                    )
                )
        return tuple(records), (
            "AKShare CNInfo announcements identify revisions but not prior numeric values",
        )

    def _index_membership(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        frame = self._adapter.index_membership(
            self.index_symbols[query.dataset]
        ).dataset.frame
        records = []
        for row in _rows(frame):
            symbol = _symbol(row, "成分券代码", "证券代码", "股票代码", "代码")
            if not symbol:
                continue
            records.append(
                CalibrationRecord(
                    key=symbol,
                    fields={
                        "member": True,
                        "effective_date": _date_text(
                            row.get("日期") or row.get("生效日期")
                        ),
                        "weight": _number(row.get("权重")),
                    },
                )
            )
        return _deduplicate(records), (
            "AKShare CSI constituents are current snapshots, not historical ledgers",
        )

    def _corporate_actions(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        symbol = _required(query, "symbol")
        frame = self._adapter.corporate_actions(symbol).dataset.frame
        records = []
        for row in _rows(frame):
            effective_date = _date_text(
                row.get("除权除息日") or row.get("股权登记日")
            )
            if not effective_date:
                continue
            records.append(
                CalibrationRecord(
                    key=f"{symbol}:{effective_date}",
                    fields={
                        "effective_date": effective_date,
                        "cash_dividend": _number(
                            row.get("现金分红") or row.get("派息")
                        ),
                        "stock_dividend": _number(
                            row.get("送转股份") or row.get("送转比例")
                        ),
                        "ann_date": _date_text(
                            row.get("公告日期") or row.get("实施公告日")
                        ),
                    },
                )
            )
        return _deduplicate(records), (
            "AKShare corporate-action announcement timing remains provider-limited",
        )

    def _universe_coverage(
        self, query: CalibrationQuery
    ) -> tuple[tuple[CalibrationRecord, ...], tuple[str, ...]]:
        del query
        frame = self._adapter.a_share_universe().dataset.frame
        records = []
        for row in _rows(frame):
            symbol = _symbol(row, "代码", "股票代码", "证券代码")
            if symbol:
                records.append(
                    CalibrationRecord(key=symbol, fields={"listed": True})
                )
        return _deduplicate(records), (
            "AKShare A-share universe is a retrieval-time listing snapshot",
        )


def _required(query: CalibrationQuery, key: str) -> str:
    value = query.parameters.get(key)
    if not value:
        raise ValueError(f"{query.dataset.value} requires parameter {key}")
    return value


def _symbol(row: Mapping[str, object], *columns: str) -> str:
    for column in columns:
        value = _text(row.get(column))
        if value:
            return value.split(".", maxsplit=1)[0].zfill(6)
    return ""


def _text(value: object) -> str:
    if value is None or bool(pd.isna(cast(Any, value))):
        return ""
    return str(value).strip()


def _date_text(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    parsed = pd.Timestamp(text)
    return parsed.strftime("%Y%m%d") if not pd.isna(parsed) else ""


def _number(value: object) -> float | None:
    if value is None or bool(pd.isna(cast(Any, value))):
        return None
    return float(cast(Any, value))


def _is_st_name(name: str) -> bool:
    return name.upper().replace(" ", "").lstrip("*").startswith(("ST", "SST"))


def _period_end_from_title(title: str) -> str:
    year_match = re.search(r"(20\d{2})年", title)
    if year_match is None:
        return ""
    year = int(year_match.group(1))
    if re.search(r"第一季度|一季度", title):
        period = date(year, 3, 31)
    elif re.search(r"半年度|半年报|中期报告", title):
        period = date(year, 6, 30)
    elif re.search(r"第三季度|三季度", title):
        period = date(year, 9, 30)
    elif re.search(r"年度报告|年报", title):
        period = date(year, 12, 31)
    else:
        return ""
    return period.strftime("%Y%m%d")


def _report_type(period_end: str) -> str:
    return {
        "0331": "first_quarter",
        "0630": "half_year",
        "0930": "third_quarter",
        "1231": "annual",
    }.get(period_end[-4:], "periodic_report")


def _deduplicate(records: list[CalibrationRecord]) -> tuple[CalibrationRecord, ...]:
    return tuple({record.key: record for record in records}.values())


def _rows(frame: pd.DataFrame) -> tuple[dict[str, object], ...]:
    return tuple(
        {str(key): value for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    )


__all__ = ["AkShareCalibrationAdapter"]
