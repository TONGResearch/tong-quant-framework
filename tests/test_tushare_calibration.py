from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.core.exceptions import ConfigurationError
from tong_quant.data.calibration import (
    CalibrationDataset,
    CalibrationQuery,
    CalibrationRecord,
    ProviderCalibrationCoordinator,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.calibration import AkShareCalibrationAdapter
from tong_quant.data.providers.tushare import TushareCalibrationAdapter
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import DataTrustLevel

NOW = datetime(2026, 1, 5, tzinfo=UTC)


class FakeTushareClient:
    def namechange(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "name": ["*ST平安"],
                "start_date": ["20240102"],
                "end_date": ["20240202"],
                "ann_date": ["20240101"],
                "change_reason": ["ST"],
            }
        )

    def suspend_d(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240103"],
                "suspend_timing": [None],
                "suspend_type": ["S"],
            }
        )

    def stock_basic(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["600001.SH"],
                "symbol": ["600001"],
                "name": ["退市测试"],
                "exchange": ["SSE"],
                "list_status": ["D"],
                "list_date": ["19990101"],
                "delist_date": ["20240104"],
            }
        )

    def disclosure_date(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH"],
                "ann_date": ["20240101"],
                "end_date": ["20231231"],
                "pre_date": ["20240103"],
                "actual_date": ["20240103"],
                "modify_date": [None],
            }
        )

    def income(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH", "600000.SH"],
                "ann_date": ["20240103", "20240104"],
                "f_ann_date": ["20240103", "20240104"],
                "end_date": ["20231231", "20231231"],
                "report_type": ["1", "1"],
                "update_flag": ["0", "1"],
                "total_revenue": [100.0, 101.0],
                "revenue": [90.0, 91.0],
            }
        )

    def index_weight(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "index_code": ["000300.SH"],
                "con_code": ["600000.SH"],
                "trade_date": ["20240105"],
                "weight": [1.2],
            }
        )

    def dividend(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH"],
                "end_date": ["20231231"],
                "ann_date": ["20240401"],
                "div_proc": ["实施"],
                "stk_div": [0.0],
                "cash_div_tax": [0.3],
                "record_date": ["20240601"],
                "ex_date": ["20240602"],
                "imp_ann_date": ["20240520"],
            }
        )


class FakeAkSharePublicationClient:
    def stock_yysj_em(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return pd.DataFrame(
            {
                "股票代码": ["600000"],
                "股票简称": ["浦发银行"],
                "实际披露时间": ["2024-01-03"],
            }
        )


class StaticSource:
    def __init__(self, source_id: str, is_st: bool) -> None:
        self.source_id = source_id
        self._is_st = is_st

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=(
                CalibrationRecord(
                    "000001:20240102",
                    {"is_st": self._is_st, "effective_date": "20240102"},
                ),
            ),
        )


def test_tushare_requires_environment_token_for_live_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="TUSHARE_TOKEN"):
        TushareCalibrationAdapter()


@pytest.mark.parametrize(
    ("dataset", "parameters"),
    [
        (CalibrationDataset.SECURITY_LIFECYCLE, {"trade_date": "20240103"}),
        (CalibrationDataset.ST_STATUS, {}),
        (CalibrationDataset.SUSPENSION_STATUS, {"trade_date": "20240103"}),
        (CalibrationDataset.DELISTING_RECORDS, {}),
        (
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
            {"period_end": "20231231"},
        ),
        (
            CalibrationDataset.FUNDAMENTAL_REVISIONS,
            {"symbol": "600000", "start_date": "20240101", "end_date": "20240131"},
        ),
        (CalibrationDataset.CORPORATE_ACTIONS, {"symbol": "600000"}),
        (CalibrationDataset.UNIVERSE_COVERAGE, {}),
        (CalibrationDataset.CSI300_MEMBERSHIP, {"trade_date": "20240105"}),
        (CalibrationDataset.CSI500_MEMBERSHIP, {"trade_date": "20240105"}),
        (CalibrationDataset.CSI1000_MEMBERSHIP, {"trade_date": "20240105"}),
    ],
)
def test_tushare_supports_every_phase_two_dataset(
    dataset: CalibrationDataset,
    parameters: dict[str, str],
) -> None:
    adapter = TushareCalibrationAdapter(client=FakeTushareClient())

    snapshot = adapter.calibration_snapshot(
        CalibrationQuery(dataset=dataset, as_of=NOW, parameters=parameters)
    )

    assert snapshot.provider == "tushare"
    assert snapshot.dataset == dataset.value
    assert snapshot.records
    assert snapshot.limitations


def test_akshare_and_tushare_publication_dates_share_canonical_contract() -> None:
    query = CalibrationQuery(
        dataset=CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
        as_of=NOW,
        parameters={"period_end": "20231231"},
    )
    akshare = AkShareCalibrationAdapter(
        AkShareAdapter(
            client=FakeAkSharePublicationClient(),  # type: ignore[arg-type]
            clock=lambda: NOW,
        )
    )
    tushare = TushareCalibrationAdapter(client=FakeTushareClient())

    left = akshare.calibration_snapshot(query)
    right = tushare.calibration_snapshot(query)

    assert left.records[0].key == right.records[0].key
    assert left.records[0].fields["actual_date"] == "20240103"
    assert right.records[0].fields["actual_date"] == "20240103"


def test_conflicts_are_detected_scored_and_persisted_as_history(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "provider-calibration.sqlite3")
    store.initialize()
    coordinator = ProviderCalibrationCoordinator(store)
    primary = StaticSource("akshare", True)
    secondary = StaticSource("tushare", False)

    first = coordinator.run(
        primary,
        secondary,
        CalibrationQuery(CalibrationDataset.ST_STATUS, NOW),
    )
    duplicate = coordinator.run(
        primary,
        secondary,
        CalibrationQuery(CalibrationDataset.ST_STATUS, NOW),
    )
    assert duplicate == first
    assert store.table_count("provider_consistency_reports") == 1
    assert store.table_count("provider_conflicts") == 1
    assert store.table_count("dataset_confidence_assessments") == 1

    second = coordinator.run(
        primary,
        secondary,
        CalibrationQuery(CalibrationDataset.ST_STATUS, NOW + timedelta(days=1)),
    )

    assert first.confidence.confidence_score <= 79
    assert first.confidence.trust_level is DataTrustLevel.LOW
    assert first.confidence.critical_conflict_count == 1
    assert store.table_count("provider_consistency_reports") == 2
    assert store.table_count("provider_conflicts") == 2
    assert store.table_count("dataset_confidence_assessments") == 2
    history = store.provider_conflict_history(
        CalibrationDataset.ST_STATUS.value,
        conflict_fingerprint=first.conflicts[0].conflict_fingerprint,
    )
    assert len(history) == 2
    assert history[1].conflict_id == second.conflicts[0].conflict_id
    assert store.latest_dataset_confidence("st_status") == second.confidence


def test_calibration_persistence_rejects_credentials_atomically(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "provider-secrets.sqlite3")
    store.initialize()
    coordinator = ProviderCalibrationCoordinator(store)

    with pytest.raises(ValueError, match="credential-like"):
        coordinator.run(
            StaticSource("akshare", True),
            _SensitiveSource(),
            CalibrationQuery(CalibrationDataset.ST_STATUS, NOW),
        )

    assert store.table_count("provider_consistency_reports") == 0
    assert store.table_count("provider_conflicts") == 0
    assert store.table_count("dataset_confidence_assessments") == 0


class _SensitiveSource:
    source_id = "tushare"

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=(
                CalibrationRecord(
                    "000001:20240102",
                    {"is_st": "token=must-not-persist", "effective_date": "20240102"},
                ),
            ),
        )
