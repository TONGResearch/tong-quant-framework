import json
import runpy
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from tong_quant.data.models import IngestionResult
from tong_quant.data.providers.akshare import (
    AkShareDailyBarsUnavailableError,
    DailyEndpointFailure,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ingest_data.py"


def test_ingestion_cli_bounds_uncooperative_worker_and_reports_only_safe_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--timeout-seconds", "1", "calendar"])

    def timeout(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--worker" in command
        assert kwargs["timeout"] == 1
        assert kwargs["capture_output"] is True
        raise subprocess.TimeoutExpired(command, 1, output="untrusted provider output")

    monkeypatch.setattr(subprocess, "run", timeout)
    assert namespace["main"]() == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "failed",
        "error_type": "ProviderTimeout",
    }


@pytest.mark.parametrize("stdout,code", [("not JSON", 1), ('{"status":"completed"}', 1)])
def test_invalid_worker_output_cannot_be_reported_successful(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stdout: str, code: int
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "calendar"])
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], code, stdout, "not rendered"),
    )
    assert namespace["main"]() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


@pytest.mark.parametrize("timeout", ["0", "nan", "inf", "301"])
def test_invalid_cli_timeout_rejected_before_database_creation(
    tmp_path: Path, timeout: str
) -> None:
    database = tmp_path / "must-not-exist.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database",
            str(database),
            "--timeout-seconds",
            timeout,
            "calendar",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert not database.exists()


def test_empty_normalization_stays_partial_not_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "corporate-actions", "600000"])
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [],
            2,
            '{"status":"partial","accepted":0,"received":26}',
            "",
        ),
    )
    assert namespace["main"]() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "partial"


def test_partially_accepted_payload_is_not_a_completed_cli_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    namespace = runpy.run_path(str(SCRIPT))

    class FakePipeline:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def initialize(self) -> None:
            pass

        def ingest_corporate_actions(self, symbol: str) -> IngestionResult:
            return IngestionResult("corporate_actions", 2, 1, 1, False)

    monkeypatch.setitem(namespace["run_worker"].__globals__, "DataIngestionPipeline", FakePipeline)
    args = Namespace(
        refresh=False,
        database=tmp_path / "unused.sqlite3",
        command="corporate-actions",
        symbol="600000",
    )
    assert namespace["run_worker"](args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "partial"


def test_financial_capture_never_claims_canonical_data_completion(monkeypatch, capsys, tmp_path):
    namespace = runpy.run_path(str(SCRIPT))

    class FakePipeline:
        def __init__(self, *args, **kwargs):
            pass

        def initialize(self):
            pass

        def capture_financial_statement(self, symbol, statement):
            assert (symbol, statement) == ("600000", "income")
            return IngestionResult("financial_statement_snapshot", 5, 5, 0, True)

    monkeypatch.setitem(namespace["run_worker"].__globals__, "DataIngestionPipeline", FakePipeline)
    args = Namespace(
        refresh=False,
        database=tmp_path / "unused.sqlite3",
        command="financial-snapshot",
        symbol="600000",
        statement="income",
    )
    assert namespace["run_worker"](args) == 2
    record = json.loads(capsys.readouterr().out)
    assert record["accepted"] == 5 and record["status"] == "partial"


def test_daily_worker_and_parent_preserve_safe_endpoint_failure(monkeypatch, capsys):
    namespace = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--worker", "daily-bars", "920982",
                                     "20240101", "20261019"])
    error = AkShareDailyBarsUnavailableError((
        DailyEndpointFailure("stock_zh_a_hist", "failed", "network_or_upstream",
                             "ConnectionError", attempts=3),
        DailyEndpointFailure("stock_zh_a_hist_tx", "failed", "provider_or_contract",
                             "KeyError", "day", limitation="bse_daily_payload_unavailable"),
    ))

    def failed_worker(args):
        raise error

    monkeypatch.setitem(namespace["main"].__globals__, "run_worker", failed_worker)
    assert namespace["main"]() == 2
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == error.diagnostic_record()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "daily-bars", "920982", "20240101", "20261019"])
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess([], 2, stdout, "private provider response"))
    assert namespace["main"]() == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out) == error.diagnostic_record()
    assert "private" not in captured.out + captured.err


def test_sina_worker_admits_capture_at_retrieval_and_never_creates_canonical_bars(
    tmp_path, monkeypatch, capsys,
):
    from tong_quant.data.providers.sina_prices import SinaBsePriceObservationAdapter
    from tong_quant.data.storage import SQLiteStore

    namespace = runpy.run_path(str(SCRIPT))
    source = SinaBsePriceObservationAdapter(
        download=lambda _: b"synthetic raw wire",
        decode=lambda *args: [{"date": "2026-01-02", "open": 10, "high": 11,
                               "low": 9, "close": 10, "volume": 100, "amount": 1000}],
    )
    monkeypatch.setitem(namespace["run_worker"].__globals__, "SinaBsePriceObservationAdapter",
                        lambda: source)
    path = tmp_path / "sina.sqlite3"
    args = Namespace(command="sina-bse-snapshot", symbol="920982", start_date="20260101",
                     end_date="20260102", database=path)
    assert namespace["run_worker"](args) == 2
    document = json.loads(capsys.readouterr().out)
    assert document["accepted"] == 1 and not document["canonical_bar_authorized"]
    assert SQLiteStore(path).table_count("daily_bars") == 0
