import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("failure", ["timeout", "identity", "invalid_json", "worker_exit"])
def test_bounded_endpoint_workers_fail_closed_without_rendering_stderr(
    monkeypatch, capsys, failure,
):
    path = Path(__file__).resolve().parents[1] / "scripts/diagnose_akshare_daily.py"
    spec = importlib.util.spec_from_file_location("akshare_diagnostics_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def worker(arguments, **kwargs):
        assert kwargs["timeout"] == 1
        assert kwargs["capture_output"] is True
        if failure == "timeout":
            raise subprocess.TimeoutExpired(arguments, 1, stderr="private provider response")
        response = {"endpoint": "other-endpoint", "symbol": "920982",
                    "start_date": "20240101", "end_date": "20261019",
                    "coverage_qualified": False, "status": "available"}
        return SimpleNamespace(
            stdout="not JSON" if failure == "invalid_json" else json.dumps(response),
            stderr="private provider response", returncode=1 if failure == "worker_exit" else 0,
        )

    monkeypatch.setattr(module.subprocess, "run", worker)
    monkeypatch.setattr(module.sys, "argv", [str(path), "920982", "20240101", "20261019",
                                           "--timeout-seconds", "1"])
    assert module.main() == 2
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert len(document["probes"]) == 2
    assert all(item["status"] == ("worker_timeout" if failure == "timeout" else "worker_failed")
               for item in document["probes"])
    assert "private" not in captured.out + captured.err
