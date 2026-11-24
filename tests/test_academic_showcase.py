"""Synthetic presentation checks; screenshots use separately retained real observations."""

import json
import runpy
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from tong_quant.application import academic_showcase as showcase
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters, sma

AT = datetime(2026, 11, 15, 9, tzinfo=UTC)


def _source():
    instrument = Instrument("TEST", Market.US, "Synthetic academic fixture",
                            currency="USD", exchange="SYN")
    rows = []
    for index in range(400):
        close = Decimal(100) + Decimal(index) / 10
        rows.append(Bar(instrument, AT - timedelta(days=400 - index), AT,
            close - Decimal("0.2"), close + 1, close - 1, close,
            Decimal(1000 + index), source="synthetic-academic-fixture"))
    return GlobalPriceInputs("TEST", Market.US, AT, "observed_unqualified", tuple(rows),
        ({"evidence_id": "synthetic-selected", "raw_data_hash": "a" * 64,
          "available_at": AT.isoformat(), "status": "ok", "trust_level": "LOW"},),
        "synthetic-selected", "WITHIN_LIMIT", 86400, 604800)


def _context():
    return {"git_commit": "b" * 40, "working_tree_dirty": True,
            "governance_consistent": True, "governance_total": 1, "governance_passed": 1,
            "controls": [{"name": "execution_mode", "passed": True}],
            "pit_readiness": "unsuitable", "production_readiness": "not_ready",
            "test_record": None}


def test_snapshot_is_repeatable_and_reuses_full_original_binding_and_formulas():
    source = _source()
    result = showcase.build_academic_snapshot(source)
    assert result == showcase.build_academic_snapshot(source)
    expected = technical_diagnostics(source.bars, TechnicalParameters(), as_of=AT)
    assert result["diagnostics"] == expected
    assert result["displayed_row_count"] == len(source.bars)
    assert result["frames"]["daily"]["averages"][0]["values"] == sma(
        [float(bar.close) for bar in source.bars], 5)
    assert result["frames"]["daily"]["macd"]["dif"] == expected["macd_dif"]
    assert result["frames"]["yearly"]["macd"] is None
    assert result["frames"]["yearly"]["macd_required_periods"] == 35
    for key in ("source_qualified", "pit_qualified", "validation_authorized",
                "holding_management_authorized", "execution_authorized",
                "investment_scoring_authorized", "research_report_created"):
        assert result[key] is False
    body = {k: v for k, v in result.items() if k != "snapshot_hash"}
    assert sha256(financial_input_json(body).encode()).hexdigest() == result["snapshot_hash"]


def test_duplicate_versions_do_not_inflate_chart_or_indicator_warmup():
    source = _source()
    duplicated = replace(source, bars=(*source.bars, source.bars[-1]))
    result = showcase.build_academic_snapshot(duplicated)
    assert result["supplied_row_count"] == 401 and result["displayed_row_count"] == 400
    assert result["frames"]["daily"]["available_periods"] == 400
    assert result["diagnostics"] == technical_diagnostics(
        duplicated.bars, TechnicalParameters(), as_of=AT)


@pytest.mark.parametrize("kind", ("stale", "rejected", "missing", "suspended"))
def test_blocked_or_latest_suspended_inputs_never_restore_an_old_chart(kind):
    source = _source()
    if kind == "stale":
        source = replace(source, freshness="STALE")
    elif kind == "rejected":
        source = replace(source, status="rejected_or_ambiguous")
    elif kind == "missing":
        source = replace(source, bars=(), observations=(), selected_evidence_id=None,
                         status="missing", freshness="UNASSESSED")
    else:
        source = replace(source, bars=(*source.bars[:-1],
                                      replace(source.bars[-1], is_suspended=True)))
    result = showcase.build_academic_snapshot(source)
    assert result["display_status"] == "BLOCKED_OR_UNAVAILABLE"
    for frame in result["frames"].values():
        assert frame["bars"] == [] and frame["macd"] is None and frame["kdj"] is None
    assert result["execution_authorized"] is False


def test_future_originals_are_rejected_even_when_a_source_status_is_blocked():
    source = _source()
    future = replace(source.bars[-1], timestamp=AT + timedelta(seconds=1),
                     available_at=AT + timedelta(seconds=1))
    with pytest.raises(ValueError, match="future"):
        showcase.build_academic_snapshot(replace(source, bars=(*source.bars, future),
                                                 status="rejected_or_ambiguous"))


@pytest.mark.parametrize("kind", ("subject", "market"))
def test_original_bar_identity_must_match_the_case_study(kind):
    source = _source()
    if kind == "subject":
        source = replace(source, subject="OTHER")
    else:
        source = replace(source, subject="1155.KL", market=Market.MALAYSIA,
            bars=tuple(replace(bar, instrument=replace(bar.instrument, symbol="1155.KL"))
                       for bar in source.bars))
    with pytest.raises(ValueError, match="subject or market mismatch"):
        showcase.build_academic_snapshot(source)


def test_render_is_self_contained_repeatable_and_contains_no_account_context():
    snapshot = showcase.build_academic_snapshot(_source())
    html = showcase.render_academic_showcase(snapshot, _context())
    assert html == showcase.render_academic_showcase(snapshot, _context())
    assert "__ACADEMIC_PAYLOAD__" not in html and "__LUCIDE_ICONS__" not in html
    assert '<script src=' not in html and "fetch(" not in html
    assert all(label in html for label in (
        "Research workbench", "Evidence lineage", "Verification &amp; safety",
        "System architecture"))
    assert "account_number" not in html and "reported_average_cost" not in html
    assert "quantity" not in html and "synthetic-academic-fixture" not in html
    assert "unadjusted" not in html and "adjustment basis unverified" in html
    assert "Lucide" in html or '"package": "lucide"' in html


@pytest.mark.parametrize("key", ("execution_authorized", "validation_authorized",
                               "source_qualified", "holding_management_authorized"))
def test_rehashed_authority_flags_cannot_render(key):
    snapshot = showcase.build_academic_snapshot(_source())
    snapshot[key] = True
    body = {k: v for k, v in snapshot.items() if k != "snapshot_hash"}
    snapshot["snapshot_hash"] = sha256(financial_input_json(body).encode()).hexdigest()
    with pytest.raises(ValueError, match="authority"):
        showcase.render_academic_showcase(snapshot, _context())


def test_render_escapes_script_boundaries_and_rejects_inconsistent_governance():
    snapshot = showcase.build_academic_snapshot(_source())
    context = {**_context(), "display_annotation": "</script><script>alert(1)</script>"}
    html = showcase.render_academic_showcase(snapshot, context)
    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script\\u003e" in html
    with pytest.raises(ValueError, match="governance"):
        showcase.render_academic_showcase(snapshot, {**_context(), "governance_consistent": False})
    snapshot["subject"] = "OTHER"
    with pytest.raises(ValueError, match="hash mismatch"):
        showcase.render_academic_showcase(snapshot, _context())


def test_local_junit_counts_are_descriptive_not_strategy_validation(tmp_path):
    path = tmp_path / "test-record.xml"
    path.write_text('<testsuites><testsuite><testcase classname="a" name="one"/>'
        '<testcase classname="a" name="two"/><testcase classname="a" name="three"><skipped/>'
        '</testcase><testcase classname="a" name="four"><failure/></testcase>'
        '</testsuite></testsuites>')
    result = showcase.read_test_record(path)
    assert (result["tests"], result["passed"], result["skipped"], result["failed"]) == (4, 2, 1, 1)
    assert result["basis"] == "LOCAL_JUNIT_RECORD_NOT_INDEPENDENT_STRATEGY_VALIDATION"
    assert result["record_sha256"] == sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("oversized", (False, True))
def test_test_record_bounds_the_read_itself_before_parsing(tmp_path, monkeypatch, oversized):
    content = (b"x" * 3_000_000 if oversized else
               b'<testsuite><testcase name="one"/></testsuite>')
    requests = []

    class BoundedReader(BytesIO):
        def read(self, size=-1):
            requests.append(size)
            assert size == 2_000_001
            return super().read(size)

    path = tmp_path / "local.xml"

    def open_record(target, mode):
        assert target == path and mode == "rb"
        return BoundedReader(content)

    monkeypatch.setattr(Path, "open", open_record)
    if oversized:
        with pytest.raises(ValueError, match="unsupported test record"):
            showcase.read_test_record(path)
    else:
        assert showcase.read_test_record(path)["record_sha256"] == sha256(content).hexdigest()
    assert requests == [2_000_001]


@pytest.mark.parametrize("content", (b"broken", b"<testsuites/>", b"<unknown/>",
    b"<!DOCTYPE x><testsuite/>", b"<!ENTITY x 'no'><testsuite/>",
    b'<testsuite><testcase name="one"/><testcase name="one"/></testsuite>',
    b'<testsuite><testcase name="one"><skipped/><failure/></testcase></testsuite>'))
def test_unsupported_or_ambiguous_test_records_fail_closed(tmp_path, content):
    path = tmp_path / "invalid.xml"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        showcase.read_test_record(path)


@pytest.mark.parametrize("encoding", ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"))
@pytest.mark.parametrize("declaration", (
    '<!DOCTYPE testsuite>',
    '<!DOCTYPE testsuite [<!ENTITY label "expanded">]>',
    '<!DOCTYPE testsuite SYSTEM "https://example.invalid/not-fetched">',
))
def test_dtd_is_rejected_at_parser_boundary_in_every_supported_encoding(
        tmp_path, encoding, declaration):
    path = tmp_path / "encoded-dtd.xml"
    content = ('<?xml version="1.0"?>' + declaration +
               '<testsuite><testcase name="one"/></testsuite>').encode(encoding)
    path.write_bytes(content)
    with pytest.raises(ValueError, match="unsupported test record"):
        showcase.read_test_record(path)


@pytest.mark.parametrize("encoding", ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"))
def test_valid_encoded_records_retain_original_byte_identity(tmp_path, encoding):
    path = tmp_path / "encoded-valid.xml"
    content = ('<?xml version="1.0"?><testsuite tests="2" failures="0" errors="0" skipped="1">'
        '<testcase name="one"/><testcase name="two"><skipped/></testcase>'
        '</testsuite>').encode(encoding)
    path.write_bytes(content)
    result = showcase.read_test_record(path)
    assert (result["tests"], result["passed"], result["skipped"], result["failed"]) == (2, 1, 1, 0)
    assert result["record_sha256"] == sha256(content).hexdigest()


@pytest.mark.parametrize("content", (
    '<testsuite tests="2" failures="1"><testcase name="one"/></testsuite>',
    '<testsuites tests="2"><testsuite><testcase name="one"/></testsuite></testsuites>',
    '<testsuite errors="-1"><testcase name="one"/></testsuite>',
    '<testsuite><failure/><testcase name="one"/></testsuite>',
    '<testsuite><testcase name="one"><failure/><failure/></testcase></testsuite>',
))
def test_contradictory_counters_and_outcome_structures_are_rejected(tmp_path, content):
    path = tmp_path / "contradictory.xml"
    path.write_text(content)
    with pytest.raises(ValueError):
        showcase.read_test_record(path)


def test_cli_expands_artifact_home_before_output_protection(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    output = tmp_path / "raw" / "must-not-create.html"
    monkeypatch.setattr(sys, "argv", ["export_academic_showcase.py", "--database",
        str(tmp_path / "source.sqlite3"), "--artifact-root", "~/raw", "--symbol", "MSFT",
        "--market", "us", "--as-of", AT.isoformat(), "--max-observation-age-seconds",
        "604800", "--output", str(output)])

    def forbidden(*args, **kwargs):
        pytest.fail("output protection must run before any retained source read")

    monkeypatch.setattr(showcase, "read_academic_snapshot", forbidden)
    with pytest.raises(SystemExit) as error:
        runpy.run_path("scripts/export_academic_showcase.py", run_name="__main__")
    assert error.value.code == 2 and not output.parent.exists()


@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                  "9999-12-31T23:59:59-01:00"))
def test_academic_read_rejects_utc_overflow_before_source_io(tmp_path, monkeypatch, cutoff):
    def forbidden(*args, **kwargs):
        pytest.fail("overflow must reject before source read")

    monkeypatch.setattr(showcase, "read_global_price_inputs", forbidden)
    with pytest.raises(ValueError, match="outside UTC bounds"):
        showcase.read_academic_snapshot(SQLiteStore(tmp_path / "absent.sqlite3", read_only=True),
            FileSystemArtifactStore(tmp_path / "raw"), "TEST", Market.US,
            as_of=datetime.fromisoformat(cutoff), maximum_age_seconds=604800)
    assert not (tmp_path / "absent.sqlite3").exists()


def test_academic_read_rejects_writable_store(tmp_path):
    with pytest.raises(ValueError, match="read-only"):
        showcase.read_academic_snapshot(SQLiteStore(tmp_path / "absent.sqlite3"),
            FileSystemArtifactStore(tmp_path / "raw"), "TEST", Market.US,
            as_of=AT, maximum_age_seconds=604800)


@pytest.mark.parametrize("extra", (("--capture",), ("--holding-context", "private-probe"),
    ("--as-of", "0001-01-01T00:00:00+01:00"), ("--max-observation-age-seconds", "0")))
def test_cli_never_creates_missing_database_or_echoes_private_arguments(tmp_path, extra):
    database, raw, output = tmp_path / "absent.sqlite3", tmp_path / "raw", tmp_path / "index.html"
    args = [sys.executable, "scripts/export_academic_showcase.py", "--database", str(database),
        "--artifact-root", str(raw), "--symbol", "TEST", "--market", "us",
        "--as-of", AT.isoformat(), "--max-observation-age-seconds", "604800",
        "--output", str(output), *extra]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert "Traceback" not in result.stderr and "private-probe" not in result.stderr
    assert not database.exists() and not raw.exists() and not output.exists()


def test_json_download_payload_contains_only_the_constructed_snapshot_and_context():
    result = showcase.build_academic_snapshot(_source())
    html = showcase.render_academic_showcase(result, _context())
    encoded = html.split('<script id="academicPayload" type="application/json">', 1)[1]
    payload = json.loads(encoded.split("</script>", 1)[0])
    assert payload["snapshot"]["snapshot_hash"] == result["snapshot_hash"]
    assert set(payload) == {"snapshot", "project"}


def test_project_context_rejects_inconsistent_controls_before_presentation(tmp_path, monkeypatch):
    monkeypatch.setattr(showcase, "audit_project_governance",
                        lambda _: SimpleNamespace(is_consistent=False, checks=()))
    with pytest.raises(ValueError, match="consistent disabled defaults"):
        showcase.academic_project_context(tmp_path)


def test_cli_reconstructs_real_reader_contract_and_never_overwrites_an_export(tmp_path):
    helper = runpy.run_path(str(Path(__file__).with_name("test_global_price_inputs.py")))
    store, artifacts = SQLiteStore(tmp_path / "source.sqlite3"), FileSystemArtifactStore(
        tmp_path / "raw")
    store.initialize()
    helper["_ingest"]((store, artifacts), at=AT)
    paths = [store.path, *artifacts.root.rglob("*.bin")]
    pins = {p: sha256(p.read_bytes()).hexdigest() for p in paths}
    output = tmp_path / "showcase.html"
    args = [sys.executable, "scripts/export_academic_showcase.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--symbol", "MSFT", "--market", "us",
        "--as-of", AT.isoformat(), "--max-observation-age-seconds", str(400 * 86400),
        "--output", str(output)]
    first = subprocess.run(args, capture_output=True, text=True)
    assert first.returncode == 0 and not first.stderr
    assert output.is_file() and "MSFT" in output.read_text()
    digest = sha256(output.read_bytes()).hexdigest()
    second = subprocess.run(args, capture_output=True, text=True)
    assert second.returncode == 2 and "Traceback" not in second.stderr
    assert sha256(output.read_bytes()).hexdigest() == digest
    assert pins == {p: sha256(p.read_bytes()).hexdigest() for p in paths}
