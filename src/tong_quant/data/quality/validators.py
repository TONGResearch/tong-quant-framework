from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

import pandas as pd

from tong_quant.data.models import RawDataset
from tong_quant.data.quality.models import QualityIssue, QualityReport, Severity
from tong_quant.domain.models import Bar

RAW_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "a_share_daily": frozenset(
        {"日期", "股票代码", "开盘", "收盘", "最高", "最低", "成交量", "成交额"}
    ),
    "index_daily": frozenset({"日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额"}),
    "trading_calendar": frozenset({"trade_date"}),
    "company_info": frozenset({"item", "value"}),
    "a_share_universe": frozenset({"代码", "名称"}),
    "fundamental_facts": frozenset({"report_date", "metric_name", "value"}),
    "instrument_status_st": frozenset({"代码"}),
    "instrument_status_suspended": frozenset({"代码"}),
    "instrument_status_delisted": frozenset({"代码"}),
    "index_membership": frozenset({"成分券代码"}),
    "corporate_actions": frozenset(),
}


def validate_raw_dataset(dataset: RawDataset) -> QualityReport:
    issues: list[QualityIssue] = []
    required = RAW_REQUIRED_COLUMNS.get(dataset.dataset)
    if required is None:
        issues.append(
            QualityIssue(
                code="unknown_dataset",
                message=f"no validator registered for {dataset.dataset}",
                severity=Severity.ERROR,
            )
        )
    else:
        missing = sorted(required.difference(dataset.frame.columns))
        if missing:
            issues.append(
                QualityIssue(
                    code="missing_columns",
                    message=f"missing required columns: {', '.join(missing)}",
                    severity=Severity.ERROR,
                )
            )
    if dataset.frame.empty:
        issues.append(
            QualityIssue(
                code="empty_dataset",
                message="provider returned no rows",
                severity=Severity.ERROR,
            )
        )
    if not issues and dataset.dataset in {"a_share_daily", "index_daily"}:
        issues.extend(_daily_frame_issues(dataset.frame))
    if not issues and dataset.dataset == "trading_calendar":
        duplicated = dataset.frame["trade_date"].duplicated()
        for row in dataset.frame.index[duplicated]:
            issues.append(
                QualityIssue(
                    code="duplicate_trade_date",
                    message="trading calendar contains a duplicate date",
                    severity=Severity.ERROR,
                    row=int(row),
                )
            )
    return QualityReport(dataset=dataset.dataset, rows=len(dataset.frame), issues=tuple(issues))


def validate_bars(bars: Iterable[Bar], dataset: str = "daily_bars") -> QualityReport:
    materialized = list(bars)
    issues: list[QualityIssue] = []
    seen: set[tuple[str, object, object]] = set()
    for row, bar in enumerate(materialized):
        key = (bar.instrument.symbol, bar.timestamp.date(), bar.adjustment)
        if key in seen:
            issues.append(
                QualityIssue(
                    code="duplicate_bar",
                    message=f"duplicate bar for {bar.instrument.symbol} on {bar.timestamp.date()}",
                    severity=Severity.ERROR,
                    row=row,
                )
            )
        seen.add(key)
        if bar.available_at < bar.timestamp:
            issues.append(
                QualityIssue(
                    code="future_availability",
                    message="bar availability precedes its observation",
                    severity=Severity.ERROR,
                    row=row,
                )
            )
        for field_name in ("open", "high", "low", "close"):
            value = getattr(bar, field_name)
            try:
                if Decimal(value) <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError):
                issues.append(
                    QualityIssue(
                        code="invalid_price",
                        message=f"{field_name} must be positive",
                        severity=Severity.ERROR,
                        row=row,
                    )
                )
    return QualityReport(dataset=dataset, rows=len(materialized), issues=tuple(issues))


def invalid_numeric_rows(frame: pd.DataFrame, columns: tuple[str, ...]) -> set[int]:
    invalid: set[int] = set()
    for column in columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        invalid.update(int(index) for index in frame.index[numeric.isna()])
    return invalid


def _daily_frame_issues(frame: pd.DataFrame) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    numeric_columns = ("开盘", "收盘", "最高", "最低", "成交量", "成交额")
    for row in sorted(invalid_numeric_rows(frame, numeric_columns)):
        issues.append(
            QualityIssue(
                code="invalid_numeric_value",
                message="daily data contains a missing or non-numeric value",
                severity=Severity.ERROR,
                row=row,
            )
        )

    duplicated = frame["日期"].duplicated()
    for row in frame.index[duplicated]:
        issues.append(
            QualityIssue(
                code="duplicate_trade_date",
                message="daily data contains a duplicate trading date",
                severity=Severity.ERROR,
                row=int(row),
            )
        )

    numeric = frame.loc[:, numeric_columns].apply(pd.to_numeric, errors="coerce")
    valid_rows = numeric.dropna().index
    for row in valid_rows:
        open_price = numeric.at[row, "开盘"]
        close_price = numeric.at[row, "收盘"]
        high_price = numeric.at[row, "最高"]
        low_price = numeric.at[row, "最低"]
        volume = numeric.at[row, "成交量"]
        turnover = numeric.at[row, "成交额"]
        if min(open_price, close_price, high_price, low_price) <= 0:
            issues.append(
                QualityIssue(
                    code="non_positive_price",
                    message="daily prices must be positive",
                    severity=Severity.ERROR,
                    row=int(row),
                )
            )
        if low_price > min(open_price, close_price) or high_price < max(
            open_price, close_price
        ):
            issues.append(
                QualityIssue(
                    code="inconsistent_ohlc",
                    message="daily OHLC values are inconsistent",
                    severity=Severity.ERROR,
                    row=int(row),
                )
            )
        if volume < 0 or turnover < 0:
            issues.append(
                QualityIssue(
                    code="negative_activity",
                    message="volume and turnover cannot be negative",
                    severity=Severity.ERROR,
                    row=int(row),
                )
            )
    return issues
