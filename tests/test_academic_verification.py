"""Public reproduction must be independent, honest and offline."""

import json
import socket
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256

import pytest

from tong_quant.application import academic_showcase as showcase
from tong_quant.application import academic_verification as verification
from tong_quant.application.academic_showcase import build_academic_snapshot
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.domain.enums import Market


def test_public_six_case_protocol_is_repeatable_and_numerically_checked():
    result = verification.verify_academic_reproduction()
    assert result == verification.verify_academic_reproduction()
    assert result["status"] == "CHECKS_PASSED" and len(result["cases"]) == 6
    assert {row["market"] for row in result["cases"]} == {"us", "hong_kong", "malaysia"}
    assert all(all(row["checks"].values()) for row in result["cases"])
    assert not result["real_market_data_used"] and not result["execution_authorized"]
    body = {key: value for key, value in result.items() if key != "report_hash"}
    assert result["report_hash"] == sha256(financial_input_json(body).encode()).hexdigest()


def test_reference_check_fails_when_production_values_drift(monkeypatch):
    original = verification.build_academic_snapshot

    def wrong(source):
        result = original(source)
        if result["frames"]["daily"]["macd"] is not None:
            result["frames"]["daily"]["macd"]["dif"] += 1
        return result

    monkeypatch.setattr(verification, "build_academic_snapshot", wrong)
    result = verification.verify_academic_reproduction()
    assert result["status"] == "CHECKS_FAILED"
    assert all(not row["checks"]["independent_formula_reference"] for row in result["cases"])


def test_reference_is_independent_of_production_indicators(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("reference must not call production computation")

    monkeypatch.setattr(verification, "build_academic_snapshot", forbidden)
    assert verification.reference_values(rising=False) == {
        "sma5": 20, "sma10": 20, "sma20": 20, "dif": 0, "dea": 0, "histogram": 0,
        "k": 50, "d": 50, "j": 50}
    assert verification.reference_values(rising=True)["sma5"] == 113


def test_short_prefixes_detect_lost_kdj_smoothing_despite_converged_endpoint(monkeypatch):
    original = verification.build_academic_snapshot

    def unsmoothed(source):
        result = original(source)
        if result["frames"]["daily"]["kdj"] is not None:
            window = source.bars[-9:]
            low, high = min(bar.low for bar in window), max(bar.high for bar in window)
            rsv = float(100 * (window[-1].close - low) / (high - low))
            result["frames"]["daily"]["kdj"] = {"k": rsv, "d": rsv, "j": rsv}
        return result

    monkeypatch.setattr(verification, "build_academic_snapshot", unsmoothed)
    result = verification.verify_academic_reproduction()
    assert result["status"] == "CHECKS_FAILED"
    assert all(row["checks"]["independent_formula_reference"] for row in result["cases"])
    assert all(not row["checks"]["nonconverged_kdj_references"]
               for row in result["cases"] if row["fixture"] == "rising")


def test_public_protocol_never_reads_retained_sources_or_connects_to_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("public fixtures cannot read retained data or connect to the network")

    monkeypatch.setattr(showcase, "read_global_price_inputs", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert verification.verify_academic_reproduction()["status"] == "CHECKS_PASSED"


@pytest.mark.parametrize("market,symbol,currency", verification.SCOPES)
def test_each_market_export_uses_original_identity_and_rejects_mixed_bars(market, symbol, currency):
    source = verification.academic_fixture(market, rising=True)
    result = build_academic_snapshot(source)
    assert result["subject"] == symbol and result["currency"] == currency
    assert result["market"] == market.value and result["displayed_row_count"] == 96
    with pytest.raises(ValueError, match="subject or market mismatch"):
        build_academic_snapshot(replace(source, subject="OTHER" if market is Market.US
                                        else "9999.HK" if market is Market.HONG_KONG
                                        else "OTHER.KL"))


@pytest.mark.parametrize("value", (None, 1, "true"))
def test_fixture_modes_do_not_coerce_unknown_values(value):
    with pytest.raises(ValueError):
        verification.academic_fixture(Market.US, rising=value)
    with pytest.raises(ValueError):
        verification.reference_values(rising=value)


def test_cli_is_offline_and_does_not_overwrite(tmp_path):
    output = tmp_path / "verification.json"
    command = [sys.executable, "scripts/verify_academic_reproduction.py", "--output", str(output)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0 and not first.stderr
    content = output.read_bytes()
    result = json.loads(content)
    assert result["status"] == "CHECKS_PASSED"
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2 and output.read_bytes() == content
    assert "Traceback" not in second.stderr
