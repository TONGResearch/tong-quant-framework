import json
import runpy
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from tong_quant.data.models import IngestionResult

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
