from datetime import UTC, datetime

import pandas as pd

from tong_quant.data.models import RawDataset
from tong_quant.data.quality import validate_raw_dataset


def test_raw_validation_rejects_missing_columns() -> None:
    dataset = RawDataset(
        dataset="a_share_daily",
        frame=pd.DataFrame({"日期": ["2024-01-02"]}),
        retrieved_at=datetime(2024, 1, 3, tzinfo=UTC),
        source="test",
        parameters={},
    )

    report = validate_raw_dataset(dataset)

    assert report.is_valid is False
    assert report.issues[0].code == "missing_columns"


def test_raw_validation_rejects_inconsistent_ohlc() -> None:
    dataset = RawDataset(
        dataset="index_daily",
        frame=pd.DataFrame(
            {
                "日期": ["2024-01-02"],
                "开盘": [10],
                "收盘": [11],
                "最高": [10.5],
                "最低": [9],
                "成交量": [100],
                "成交额": [1000],
            }
        ),
        retrieved_at=datetime(2024, 1, 3, tzinfo=UTC),
        source="test",
        parameters={},
    )

    report = validate_raw_dataset(dataset)

    assert report.is_valid is False
    assert any(issue.code == "inconsistent_ohlc" for issue in report.issues)


def test_optional_turnover_is_unknown_not_fabricated_and_invalid_values_still_fail() -> None:
    from dataclasses import replace

    dataset = RawDataset(
        dataset="index_daily",
        frame=pd.DataFrame(
            {
                "日期": ["2024-01-02"],
                "开盘": [10],
                "收盘": [11],
                "最高": [12],
                "最低": [9],
                "成交量": [100],
                "成交额": [None],
            }
        ),
        retrieved_at=datetime(2024, 1, 3, tzinfo=UTC),
        source="fixture",
        parameters={},
    )
    report = validate_raw_dataset(dataset)
    assert report.is_valid
    assert any(issue.code == "turnover_unavailable" for issue in report.issues)
    invalid = dataset.frame.copy()
    invalid["成交额"] = "not a number"
    assert not validate_raw_dataset(replace(dataset, frame=invalid)).is_valid
    invalid["成交额"] = -1
    assert not validate_raw_dataset(replace(dataset, frame=invalid)).is_valid
    invalid["成交额"] = float("inf")
    assert not validate_raw_dataset(replace(dataset, frame=invalid)).is_valid
