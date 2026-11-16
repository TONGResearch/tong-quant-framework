import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.sina_prices import (
    MAX_BYTES,
    SINA_BSE_DATASET,
    SinaBsePriceObservationAdapter,
    _decode,
)
from tong_quant.data.storage import SQLiteStore
from tong_quant.domain.enums import DataTrustLevel, Market

NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)
WIRE = b'var KLC_K2_bj920982="AAAA"; /* retained provider comment */'


def row(date="2026-10-19"):
    return {"date": date, "open": "10.15", "high": "10.30", "low": "10.00",
            "close": "10.20", "volume": "12345", "amount": "125000.50"}


def query():
    return ProviderDatasetRequest(SINA_BSE_DATASET, Market.CHINA_A, "920982", NOW,
                                  {"start_date": "20260101", "end_date": "20261019"})


def adapter(rows=None):
    return SinaBsePriceObservationAdapter(download=lambda _: WIRE,
                                         decode=lambda *args: rows or [row()], clock=lambda: NOW)


def test_native_snapshot_keeps_raw_bytes_limits_trust_and_does_not_write_bars(tmp_path):
    source = adapter([row("2025-12-31"), row("2026-10-16"), row()])
    first = source.fetch(query())
    assert first.raw_record_count == 3 and len(first.records) == 2
    assert first.artifacts[0].content == WIRE
    assert first.raw_data_hash == sha256(WIRE).hexdigest()
    assert all(r.trust_level is DataTrustLevel.LOW and r.available_at == NOW for r in first.records)
    assert all(not r.payload["canonical_bar_authorized"] for r in first.records)
    assert all(not r.payload["forward_filled"] and not r.payload["rounded"] for r in first.records)
    store = SQLiteStore(tmp_path / "sina.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    ingest = ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW)
    one = ingest.ingest(source, query())
    two = ingest.ingest(source, query())
    assert one.accepted == two.accepted == 2
    assert store.table_count("provider_evidence_records") == 2
    assert store.table_count("provider_artifacts") == 1
    assert store.table_count("daily_bars") == 0
    assert artifacts.read_content(first.raw_data_hash, "application/javascript",
                                  max_bytes=MAX_BYTES) == WIRE


@pytest.mark.parametrize("defect", [
    "wrong_symbol", "wrong_market", "extra_parameter", "adjusted", "reversed",
    "future", "short_date", "oversize", "duplicate_date", "intraday", "boolean",
    "missing_close", "nan", "negative_volume", "bad_ohlc", "invalid_date",
])
def test_observation_rejects_ambiguous_or_invalid_data_without_repair(defect):
    request, rows = query(), [row()]
    source = adapter(rows)
    if defect == "wrong_symbol":
        request = replace(request, subject="600000")
    elif defect == "wrong_market":
        request = replace(request, market=Market.US)
    elif defect in {"extra_parameter", "adjusted"}:
        request = replace(request, parameters={**request.parameters, "adjust": "qfq"})
    elif defect in {"reversed", "future", "short_date"}:
        parameters = dict(request.parameters)
        parameters["end_date" if defect == "future" else "start_date"] = {
            "reversed": "20261020", "future": "20261021", "short_date": "2026011",
        }[defect]
        request = replace(request, parameters=parameters)
    elif defect == "oversize":
        source.download = lambda _: b"x" * (MAX_BYTES + 1)
    elif defect == "duplicate_date":
        rows.append(copy.deepcopy(rows[0]))
    else:
        key, value = {"intraday": ("date", "2026-10-19T10:00:00Z"),
                      "boolean": ("volume", True), "missing_close": ("close", None),
                      "nan": ("open", "NaN"), "negative_volume": ("volume", "-1"),
                      "bad_ohlc": ("high", "10.01"),
                      "invalid_date": ("date", "not-a-date")}[defect]
        rows[0][key] = value
    with pytest.raises(ValueError):
        source.fetch(request)


@pytest.mark.parametrize("wire", [
    b'var KLC_K2_bj832982="AAAA";', b'var KLC_K2_bj920982=alert(1);',
    b'var KLC_K2_bj920982="AAAA"; alert(1);',
])
def test_untrusted_javascript_and_wrong_source_identity_are_never_evaluated(wire, monkeypatch):
    monkeypatch.setattr("tong_quant.data.providers.sina_prices.py_mini_racer.MiniRacer",
                        lambda: pytest.fail("must not evaluate malformed provider content"))
    with pytest.raises(ValueError, match="identity/schema"):
        _decode(wire, "920982")


def test_decoder_uses_fixed_sdk_code_not_provider_javascript(monkeypatch):
    class Runtime:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def eval(self, code, **kwargs):
            assert code != WIRE.decode() and "function" in code
            assert kwargs["timeout"] == 2000

        def call(self, name, encoded, **kwargs):
            assert name == "d" and encoded == "AAAA"
            assert kwargs["max_memory"] == 64 * 1024 * 1024
            return [row()]

    monkeypatch.setattr("tong_quant.data.providers.sina_prices.py_mini_racer.MiniRacer", Runtime)
    assert _decode(WIRE, "920982") == [row()]


def test_retrieval_time_cannot_be_backdated_to_request_cutoff(tmp_path):
    source = adapter()
    source.clock = lambda: NOW + timedelta(seconds=1)
    assert source.fetch(query()).records[0].available_at == NOW + timedelta(seconds=1)
    store = SQLiteStore(tmp_path / "time.sqlite3")
    store.initialize()
    with pytest.raises(ValueError, match="future"):
        ProviderNeutralIngestionService(store).ingest(source, query())
