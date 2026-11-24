"""Unqualified same-filing inventory; no accounting or financial change calculator."""

import json
import runpy
import sqlite3
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.application import sec_window_inventory as inventory
from tong_quant.application.sec_window_inventory import SECWindowPair, read_sec_window_inventory
from tong_quant.data import sec_body_inputs
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sec_submissions as sec
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.sec_period_inputs import SECPeriodSelection
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.version import (
    SEC_SOURCE_CAPTURE_IDENTITY_VERSION,
    SEC_SOURCE_CHECK_GAP_VERSION,
    SEC_SOURCE_RECORD_PROJECTION_VERSION,
    SEC_WINDOW_INVENTORY_VERSION,
)

NS = "http://fasb.org/us-gaap/2025"
LEFT = SECPeriodSelection("Revenues", date(2023, 7, 1), date(2024, 6, 30))
RIGHT = SECPeriodSelection("Revenues", date(2024, 7, 1), date(2025, 6, 30))
PAIR = SECWindowPair(LEFT, RIGHT, NS)


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_sec_body.py")))


@pytest.fixture
def foundation(tmp_path):
    return _helpers()["foundation"].__wrapped__(tmp_path)


def _content(*, extra="", prior_namespace=NS):
    helper = _helpers()
    prior = f'''<xbrli:context id="prior"><xbrli:entity><xbrli:identifier
        scheme="http://www.sec.gov/CIK">{helper['CIK']}</xbrli:identifier></xbrli:entity>
        <xbrli:period><xbrli:startDate>2023-07-01</xbrli:startDate>
        <xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>
        <ix:nonFraction xmlns:prior="{prior_namespace}" name="prior:Revenues"
        contextRef="prior" unitRef="u" decimals="-6" scale="6">100</ix:nonFraction>'''
    return helper["_xml"](extra=prior + extra)


def _capture(foundation, content=None, **kwargs):
    return _helpers()["_capture"](foundation, content or _content(), **kwargs)


def _read(foundation, *, pairs=(PAIR,), at=None, age=3600):
    helper = _helpers()
    return read_sec_window_inventory(SQLiteStore(foundation[0].path, read_only=True),
        foundation[1], helper["CIK"], helper["ACCESSION"], symbol="MSFT",
        as_of=at or helper["NOW"] + timedelta(seconds=2), pairs=pairs,
        maximum_capture_age_seconds=age)


def _footprint(foundation):
    paths = [foundation[0].path, *foundation[1].root.rglob("*.bin")]
    wal = foundation[0].path.with_name(foundation[0].path.name + "-wal")
    return {**{path: sha256(path.read_bytes()).hexdigest() for path in paths},
            wal: sha256(wal.read_bytes() if wal.exists() else b"").hexdigest()}


def _unadmitted(result):
    assert result["economic_comparison_status"] == "NOT_ADMITTED"
    assert result["fundamental_assessment"] == result["source_record_changes"] == "NOT_ASSESSED"
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    for name in ("source_qualified", "pit_qualified", "issuer_to_instrument_verified",
                 "accounting_definitions_admitted", "financial_scoring_authorized",
                 "investment_scoring_authorized", "validation_authorized",
                 "historical_replay_eligible",
                 "holding_management_authorized", "execution_authorized", "research_report_created",
                 "freshness_policy_independently_reviewed"):
        assert result[name] is False
    for pair in result["pairs"]:
        assert pair["economic_comparison_status"] == "NOT_ADMITTED"
        for side in (pair["left"], pair["right"]):
            assert all("value" not in row for row in side["occurrence_references"])


def test_original_factory_binding_is_deterministic_compact_and_never_financial_admission(
    foundation,
):
    _capture(foundation)
    pins = _footprint(foundation)
    result = _read(foundation)
    assert result == _read(foundation)
    assert result["model_version"] == SEC_WINDOW_INVENTORY_VERSION
    assert result["capture_age_seconds"] == 1 and result["capture_freshness"] == "WITHIN_LIMIT"
    assert result["pairs"][0]["raw_context_status"] == "OBSERVED_UNQUALIFIED"
    for side, context, start in (("left", "prior", "2023-07-01"), ("right", "c", "2024-07-01")):
        frame = result["pairs"][0][side]
        assert frame["matching_occurrence_count"] == 1
        assert frame["occurrence_references"][0]["context_ref"] == context
        assert frame["occurrence_references"][0]["period_start"] == start
    helper = _helpers()
    original = helper["read_sec_period_research_input"](
        SQLiteStore(foundation[0].path, read_only=True), foundation[1],
        helper["CIK"], helper["ACCESSION"], symbol="MSFT",
        as_of=helper["NOW"] + timedelta(seconds=2),
        selections=(LEFT, RIGHT), sector_profile="unknown")
    assert result["source_period_input_hash"] == original.document()["input_hash"]
    assert result["source_research_binding_hash"] == original.binding_hash
    assert len(financial_input_json(result).encode()) < 12_000
    body = {key: value for key, value in result.items() if key != "inventory_hash"}
    assert result["inventory_hash"] == sha256(financial_input_json(body).encode()).hexdigest()
    assert pins == _footprint(foundation)
    _unadmitted(result)
    for table in ("fundamental_facts", "research_reports", "signals"):
        assert foundation[0].table_count(table) == 0


def test_pair_order_is_canonical_and_same_window_is_not_new_evidence(foundation):
    _capture(foundation)
    reverse = SECWindowPair(RIGHT, LEFT, NS)
    assert _read(foundation, pairs=(PAIR, reverse)) == _read(foundation, pairs=(reverse, PAIR))
    result = _read(foundation, pairs=(SECWindowPair(RIGHT, RIGHT, NS),))
    assert result["source_occurrence_count"] == 2  # Tag inventory, not just the selected window.
    assert result["pairs"][0]["left"]["occurrence_references"] == (
        result["pairs"][0]["right"]["occurrence_references"])
    _unadmitted(result)


@pytest.mark.parametrize("kind", ("wrong_namespace", "mixed_namespace", "conflict", "unresolved",
                                  "wrong_unit", "missing_window", "future_window", "mixed_basis"))
def test_raw_alignment_blockers_cannot_be_overridden_by_same_values(foundation, kind):
    extra = ""
    pairs = (PAIR,)
    if kind == "wrong_namespace":
        pairs = (replace(PAIR, expected_namespace="http://fasb.org/us-gaap/2026"),)
    elif kind in {"mixed_namespace", "conflict"}:
        namespace = "http://fasb.org/us-gaap/2026" if kind == "mixed_namespace" else NS
        extra = f'''<ix:nonFraction xmlns:alt="{namespace}" name="alt:Revenues"
            contextRef="c" unitRef="u" decimals="-6" scale="6">{
                '120' if kind == 'mixed_namespace' else '121'}</ix:nonFraction>'''
    elif kind == "unresolved":
        extra = _helpers()["_xml"]().decode().split('<xbrli:context id="c">')[1].split(
            '</xbrli:context>')[0]
        extra = ('<xbrli:context id="dim">' + extra.replace('</xbrli:entity>',
            '<xbrli:segment/></xbrli:entity>') + '</xbrli:context>'
            '<ix:nonFraction name="us-gaap:Revenues" contextRef="dim" unitRef="u" '
            'decimals="-6" scale="6">120</ix:nonFraction>')
    elif kind == "wrong_unit":
        _capture(foundation, _content().replace(b'iso:USD', b'iso:EUR'))
    elif kind in {"missing_window", "future_window"}:
        year = 2022 if kind == "missing_window" else 2027
        pairs = (replace(PAIR, left=SECPeriodSelection("Revenues", date(year, 7, 1),
                                                       date(year + 1, 6, 30))),)
    else:
        context = f'''<xbrli:context id="instant"><xbrli:entity><xbrli:identifier
            scheme="http://www.sec.gov/CIK">{_helpers()['CIK']}</xbrli:identifier></xbrli:entity>
            <xbrli:period><xbrli:instant>2025-06-30</xbrli:instant></xbrli:period></xbrli:context>
            <ix:nonFraction name="us-gaap:Revenues" contextRef="instant" unitRef="u"
            decimals="-6" scale="6">120</ix:nonFraction>'''
        extra = context
        pairs = (SECWindowPair(SECPeriodSelection("Revenues", None, date(2025, 6, 30)), RIGHT, NS),)
    if kind != "wrong_unit":
        _capture(foundation, _content(extra=extra))
    result = _read(foundation, pairs=pairs)
    assert result["pairs"][0]["raw_context_status"] == "BLOCKED"
    assert result["pairs"][0]["blocking_reasons"]
    _unadmitted(result)


@pytest.mark.parametrize("kind", ("missing", "failed", "ambiguous", "tampered", "future_complete"))
def test_source_failures_leave_inventory_unassessed_without_good_fallback(foundation, kind):
    helper = _helpers()
    if kind != "missing":
        _capture(foundation)
    if kind == "failed":
        _capture(foundation, error="http_403", at=helper["NOW"] + timedelta(seconds=2))
    elif kind == "ambiguous":
        _capture(foundation, _content().replace(b">120<", b">121<"))
    elif kind == "future_complete":
        _capture(foundation, at=helper["NOW"] + timedelta(seconds=2),
                 completed=helper["NOW"] + timedelta(seconds=3))
    elif kind == "tampered":
        for path in foundation[1].root.rglob("*.bin"):
            if b'body_base64' in path.read_bytes():
                path.write_bytes(b"synthetic corruption")
    pins = _footprint(foundation)
    result = _read(foundation)
    assert not result["source_occurrence_inventory_evaluated"]
    assert result["source_occurrence_count"] is None
    assert result["unsupported_source_occurrence_count"] is None
    assert all(pair["raw_context_status"] == "BLOCKED" for pair in result["pairs"])
    assert result["pairs"][0]["left"]["matching_occurrence_count"] is None
    assert pins == _footprint(foundation)
    _unadmitted(result)


@pytest.mark.parametrize("microseconds,expected", ((0, "WITHIN_LIMIT"), (1, "STALE")))
def test_capture_age_boundary_does_not_round_up_freshness(foundation, microseconds, expected):
    helper = _helpers()
    _capture(foundation)
    result = _read(foundation, at=helper["NOW"] + timedelta(
        seconds=3601, microseconds=microseconds))
    assert result["capture_freshness"] == expected
    assert (result["pairs"][0]["raw_context_status"] == "BLOCKED") is bool(microseconds)
    _unadmitted(result)


def test_offsets_and_dst_use_actual_capture_age(foundation):
    helper = _helpers()
    _capture(foundation)
    cutoff = helper["NOW"] + timedelta(seconds=2)
    assert _read(foundation) == _read(foundation, at=cutoff.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur")))
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    _capture(foundation, at=first.astimezone(UTC))
    assert _read(foundation, at=second)["capture_age_seconds"] == 3600


@pytest.mark.parametrize("age", (None, True, False, 0, -1, 1.5))
def test_invalid_capture_limit_rejects_before_source_access(foundation, age, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid input must not read source")
    monkeypatch.setattr(inventory, "read_sec_period_research_input", forbidden)
    with pytest.raises(ValueError, match="positive integer"):
        _read(foundation, age=age)


@pytest.mark.parametrize("pairs", ((), [], (PAIR, PAIR), (PAIR,) * 9, (True,)))
def test_invalid_pair_collections_reject_before_source_access(foundation, pairs):
    with pytest.raises(ValueError):
        _read(foundation, pairs=pairs)


@pytest.mark.parametrize("namespace", (None, "", "https://example.com/us-gaap/2025", NS + "#other"))
def test_namespace_is_explicit_bounded_and_never_downloaded(namespace):
    with pytest.raises(ValueError):
        SECWindowPair(LEFT, RIGHT, namespace)


def test_pair_rejects_cross_tag_and_untyped_periods():
    with pytest.raises(ValueError):
        SECWindowPair(LEFT, replace(RIGHT, native_tag="NetIncomeLoss"), NS)
    with pytest.raises(ValueError):
        SECWindowPair(True, RIGHT, NS)


def test_eight_pairs_keep_sixteen_explicit_selections_without_fallback(foundation):
    _capture(foundation)
    pairs = tuple(SECWindowPair(
        SECPeriodSelection("Revenues", date(2000 + i * 2, 7, 1), date(2001 + i * 2, 6, 30)),
        SECPeriodSelection("Revenues", date(2001 + i * 2, 7, 1), date(2002 + i * 2, 6, 30)), NS)
        for i in range(8))
    result = _read(foundation, pairs=pairs)
    assert len(result["pairs"]) == 8
    assert all(pair["raw_context_status"] == "BLOCKED" for pair in result["pairs"])
    _unadmitted(result)


@pytest.mark.parametrize("defect", ("symbol", "cutoff", "filing", "selections"))
def test_factory_receipt_cannot_be_rebound_to_another_requested_context(
    foundation, monkeypatch, defect,
):
    _capture(foundation)
    original = inventory.read_sec_period_research_input

    def altered(store, artifacts, cik, accession, **kwargs):
        if defect == "symbol":
            kwargs["symbol"] = "AAPL"
        elif defect == "cutoff":
            kwargs["as_of"] += timedelta(seconds=1)
        elif defect == "filing":
            cik = "0000789020"
        else:
            kwargs["selections"] = (replace(LEFT, native_tag="Assets"),)
        return original(store, artifacts, cik, accession, **kwargs)

    monkeypatch.setattr(inventory, "read_sec_period_research_input", altered)
    with pytest.raises(ValueError, match="mismatch"):
        _read(foundation)


def test_writable_store_and_naive_cutoff_cannot_enter_reader(foundation):
    helper = _helpers()
    with pytest.raises(ValueError, match="read-only"):
        read_sec_window_inventory(*foundation, helper["CIK"], helper["ACCESSION"], symbol="MSFT",
            as_of=helper["NOW"], pairs=(PAIR,), maximum_capture_age_seconds=3600)
    with pytest.raises(ValueError, match="timezone"):
        _read(foundation, at=helper["NOW"].replace(tzinfo=None))


def test_one_factory_read_uses_active_snapshot_and_retains_old_view(foundation, monkeypatch):
    _capture(foundation)
    original = inventory.read_sec_period_research_input
    calls = []

    def interleaved(store, *args, **kwargs):
        assert store.read_only and store.has_active_connection
        bound = original(store, *args, **kwargs)
        calls.append(1)
        _capture(foundation, error="http_403", at=_helpers()["NOW"] + timedelta(seconds=2))
        return bound

    with monkeypatch.context() as patch:
        patch.setattr(inventory, "read_sec_period_research_input", interleaved)
        result = _read(foundation)
    assert calls == [1] and result["pairs"][0]["raw_context_status"] == "OBSERVED_UNQUALIFIED"
    assert _read(foundation)["pairs"][0]["raw_context_status"] == "BLOCKED"


def test_existing_nonempty_committed_wal_remains_exact(foundation):
    with sqlite3.connect(foundation[0].path) as keeper:
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        _capture(foundation)
        assert foundation[0].path.with_name(foundation[0].path.name + "-wal").stat().st_size > 32
        pins = _footprint(foundation)
        _read(foundation)
        assert pins == _footprint(foundation)


def test_wrong_artifact_root_does_not_search_correct_store_or_fall_back(foundation, tmp_path):
    _capture(foundation)
    pins = _footprint(foundation)
    result = _read((foundation[0], FileSystemArtifactStore(tmp_path / "wrong-root")))
    assert result["source_occurrence_inventory_evaluated"] is False
    assert result["source_occurrence_count"] is None
    assert result["pairs"][0]["raw_context_status"] == "BLOCKED"
    assert _read(foundation)["pairs"][0]["raw_context_status"] == "OBSERVED_UNQUALIFIED"
    assert pins == _footprint(foundation)
    assert not (tmp_path / "wrong-root").exists()
    _unadmitted(result)


def test_body_and_parent_reads_share_old_view_during_independent_parent_update(
    foundation, monkeypatch,
):
    helper = _helpers()
    _capture(foundation)
    original = sec_body_inputs.read_sec_filing_inputs
    calls = []

    def interleaved(store, artifacts, cik, **kwargs):
        assert store.read_only and store.has_active_connection
        calls.append(1)
        catalog = helper["_catalog"]()
        catalog["filings"]["recent"]["primaryDocument"] = ["changed.htm"]
        at = helper["NOW"] + timedelta(seconds=2)
        helper["ProviderNeutralIngestionService"](foundation[0], artifact_store=foundation[1],
            clock=lambda: at).ingest(helper["sec"].SECSubmissionsAdapter(
                download=lambda _: helper["sec"].SECSubmissionsCapture(catalog), clock=lambda: at),
                helper["ProviderDatasetRequest"](
                    helper["sec"].DATASET, helper["Market"].US, cik, at))
        return original(store, artifacts, cik, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(sec_body_inputs, "read_sec_filing_inputs", interleaved)
        result = _read(foundation)
    assert calls == [1]
    assert result["pairs"][0]["raw_context_status"] == "OBSERVED_UNQUALIFIED"
    assert result["source_parent_binding"]["primary_document"] == "annual.htm"
    later = _read(foundation)
    assert later["source_occurrence_count"] is None
    assert later["pairs"][0]["raw_context_status"] == "BLOCKED"
    _unadmitted(later)


def _cli(database, raw):
    return [sys.executable, "scripts/inspect_sec_windows.py", "--database", str(database),
        "--artifact-root", str(raw), "--cik", _helpers()["CIK"],
        "--accession", _helpers()["ACCESSION"],
        "--symbol", "MSFT", "--as-of", (_helpers()["NOW"] + timedelta(seconds=2)).isoformat(),
        "--left", "Revenues=2023-07-01/2024-06-30", "--right", "Revenues=2024-07-01/2025-06-30",
        "--namespace", NS, "--max-capture-age-seconds", "3600"]


def test_cli_repeats_offline_without_scoring_or_capture(foundation):
    _capture(foundation)
    pins = _footprint(foundation)
    args = _cli(foundation[0].path, foundation[1].root)
    first = subprocess.run(args, capture_output=True, text=True)
    second = subprocess.run(args, capture_output=True, text=True)
    assert first.returncode == second.returncode == 2 and not first.stderr + second.stderr
    assert first.stdout == second.stdout
    _unadmitted(json.loads(first.stdout))
    assert pins == _footprint(foundation)


@pytest.mark.parametrize("extra", (("--capture",), ("--max-capture-age-seconds", "0"),
    ("--namespace", "synthetic-private-probe"), ("--as-of", "2026-10-27T10:00:02"),
    ("--left", "NetIncomeLoss=2023-07-01/2024-06-30")))
def test_cli_invalid_options_are_sanitized_without_creating_database(tmp_path, extra):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    result = subprocess.run([*_cli(database, raw), *extra], capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert "synthetic-private-probe" not in result.stderr and "Traceback" not in result.stderr
    assert not database.exists() and not raw.exists()


@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                   "9999-12-31T23:59:59-01:00"))
def test_cli_utc_overflow_is_sanitized_before_database_access(tmp_path, cutoff):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    result = subprocess.run([*_cli(database, raw), "--as-of", cutoff],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only SEC window inputs could not be verified.\n"
    assert not database.exists() and not raw.exists()


@pytest.mark.parametrize("cutoff", ("0001-01-01T00:00:00+01:00",
                                   "9999-12-31T23:59:59-01:00"))
def test_api_utc_overflow_rejects_before_factory_read(foundation, monkeypatch, cutoff):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid UTC cutoff must not enter the source factory")
    monkeypatch.setattr(inventory, "read_sec_period_research_input", forbidden)
    pins = _footprint(foundation)
    with pytest.raises(ValueError, match="outside UTC bounds"):
        _read(foundation, at=datetime.fromisoformat(cutoff))
    assert pins == _footprint(foundation)


def _changes(
    foundation, *, previous=None, current=None, age=3600, pairs=(PAIR,), with_identity=False,
    with_gaps=False,
    with_records=False,
    compact=False,
):
    helper = _helpers()
    return inventory.read_sec_source_reference_changes(
        SQLiteStore(foundation[0].path, read_only=True), foundation[1],
        helper["CIK"], helper["ACCESSION"], symbol="MSFT",
        previous_as_of=previous if previous is not None else helper["NOW"] + timedelta(seconds=2),
        as_of=current if current is not None else helper["NOW"] + timedelta(seconds=4),
        pairs=pairs, maximum_capture_age_seconds=age, with_selected_capture_identity=with_identity,
        with_check_gap_state=with_gaps, with_record_projections=with_records, compact=compact)


def _reference_only(result):
    assert result["mode"] == "SOURCE_REFERENCE_OBSERVATION"
    assert result["fundamental_assessment"] == "NOT_ASSESSED"
    assert result["economic_comparison_status"] == "NOT_ADMITTED"
    assert result["source_record_changes"] == "PARTIAL_REFERENCE_OBSERVATION_ONLY"
    if result["model_version"] == SEC_SOURCE_RECORD_PROJECTION_VERSION:
        assert result["unimplemented_comparison_axes"] == ["full_lexical_representation"]
        assert result["representation_scope"] == "PARSER_OCCURRENCE_PROJECTION_ONLY"
        assert result["full_source_change_mode_implemented"] is False
    else:
        assert "parsed_subset_records" in result["unimplemented_comparison_axes"]
    for name in ("source_qualified", "pit_qualified", "issuer_to_instrument_verified",
                 "accounting_definitions_admitted", "financial_scoring_authorized",
                 "investment_scoring_authorized", "validation_authorized",
                 "historical_replay_eligible", "holding_management_authorized",
                 "execution_authorized", "research_report_created",
                 "freshness_policy_independently_reviewed"):
        assert result[name] is False
    _unadmitted(result["previous_inventory"])
    _unadmitted(result["current_inventory"])


def _assert_reference_material(axis, previous, current, status):
    def digest(value):
        if value is None:
            return None
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    assert axis == {"status": status,
        "previous_material_hash": digest(previous), "current_material_hash": digest(current)}


@pytest.mark.parametrize("previous,current,status", (
    (None, None, "NOT_EVALUATED"),
    (None, {"a": "synthetic"}, "NOT_EVALUATED"),
    ({"a": "synthetic"}, None, "NOT_EVALUATED"),
    ({"a": "synthetic", "b": [1, 2]}, {"b": [1, 2], "a": "synthetic"}, "OBSERVED_SAME"),
    ({"a": [1, 2]}, {"a": [2, 1]}, "OBSERVED_DIFFERENT"),
    ("synthetic", "synthetic", "OBSERVED_SAME"),
    ("synthetic", "changed", "OBSERVED_DIFFERENT"),
))
def test_reference_axis_canonical_material_hashes(previous, current, status):
    _assert_reference_material(inventory._reference_axis(previous, current),
                               previous, current, status)


@pytest.mark.parametrize("kind", (
    "unchanged", "body_recapture", "body_change", "parent_recapture",
    "primary_document", "form", "filed", "report_date", "parent_without_body",
    "missing", "failed", "stale",
))
@pytest.mark.parametrize("with_identity,with_gaps,with_records", (
    (False, False, False), (True, False, False), (True, True, False), (True, True, True),
))
def test_original_source_parent_and_all_axis_material_hashes(
    foundation, kind, with_identity, with_gaps, with_records,
):
    helper = _helpers()
    parent_fields = {"primary_document": ("primaryDocument", "revised.htm"),
        "form": ("form", "10-Q"), "filed": ("filingDate", "2025-07-31"),
        "report_date": ("reportDate", "2025-03-31")}
    if kind != "missing":
        _capture(foundation)
    if kind in {"parent_recapture", "parent_without_body", *parent_fields}:
        catalog = helper["_catalog"]()
        if kind in parent_fields:
            field, value = parent_fields[kind]
            catalog["filings"]["recent"][field] = [value]
        at = helper["NOW"] + timedelta(seconds=3)
        ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
            clock=lambda: at).ingest(sec.SECSubmissionsAdapter(
                download=lambda _: sec.SECSubmissionsCapture(catalog), clock=lambda: at),
                ProviderDatasetRequest(sec.DATASET, Market.US, helper["CIK"], at))
        if kind != "parent_without_body":
            _capture(foundation, at=at)
    elif kind in {"body_recapture", "body_change", "failed"}:
        content = _content().replace(b">120<", b">121<") if kind == "body_change" else _content()
        _capture(foundation, content, at=helper["NOW"] + timedelta(seconds=3),
                 error="http_403" if kind == "failed" else "")
    pins = _footprint(foundation)
    if kind == "stale":
        boundary = helper["NOW"] + timedelta(seconds=3601)
        result = _changes(foundation, previous=boundary,
                          current=boundary + timedelta(microseconds=1),
                          with_identity=with_identity, with_gaps=with_gaps,
                          with_records=with_records)
    else:
        result = _changes(foundation, with_identity=with_identity,
                          with_gaps=with_gaps, with_records=with_records)
    previous, current = result["previous_inventory"], result["current_inventory"]
    axes = result["source_reference_observations"]
    unavailable = kind in {"missing", "failed", "stale", "parent_without_body"}
    before_available = kind != "missing"
    expected_parent = "NOT_EVALUATED" if unavailable else (
        "OBSERVED_DIFFERENT" if kind in {"parent_recapture", *parent_fields} else "OBSERVED_SAME")
    _assert_reference_material(axes["parent_binding"],
        previous["source_parent_binding"] if before_available else None,
        current["source_parent_binding"] if not unavailable else None, expected_parent)
    _assert_reference_material(axes["selected_capture_reference"],
        [previous["source_selected_evidence_id"], previous["capture_available_at"]]
        if before_available else None,
        [current["source_selected_evidence_id"], current["capture_available_at"]]
        if not unavailable else None,
        "NOT_EVALUATED" if unavailable else
        "OBSERVED_SAME" if kind == "unchanged" else "OBSERVED_DIFFERENT")
    _assert_reference_material(axes["body_bytes"],
        previous["source_body_sha256"] if before_available else None,
        current["source_body_sha256"] if not unavailable else None,
        "NOT_EVALUATED" if unavailable else
        "OBSERVED_DIFFERENT" if kind == "body_change" else "OBSERVED_SAME")
    _assert_reference_material(axes["period_receipt_identity"],
        previous["source_period_input_hash"], current["source_period_input_hash"],
        "OBSERVED_DIFFERENT")
    if kind in parent_fields:
        assert previous["source_parent_binding"][kind] != current["source_parent_binding"][kind]
        assert current["source_parent_binding"][kind] == parent_fields[kind][1]
    if kind == "parent_recapture":
        old_parent, new_parent = previous["source_parent_binding"], current["source_parent_binding"]
        for field in parent_fields:
            assert old_parent[field] == new_parent[field]
        for field in ("parent_evidence_id", "parent_raw_data_hash", "parent_available_at"):
            assert old_parent[field] != new_parent[field]
    if kind == "parent_without_body":
        assert current["source_bound"] is False
        assert current["source_occurrence_inventory_evaluated"] is False
    if with_identity:
        identities = result["selected_capture_identity_material"]
        assert (identities["previous"] is not None) is before_available
        assert (identities["current"] is not None) is not unavailable
        _assert_reference_material(axes["selected_capture_identity"], identities["previous"],
            identities["current"], "NOT_EVALUATED" if unavailable else
            "OBSERVED_SAME" if kind == "unchanged" else "OBSERVED_DIFFERENT")
    if with_gaps:
        gaps = result["check_gap_state_material"]
        assert (gaps["previous"] is not None) is before_available
        assert (gaps["current"] is not None) is not unavailable
        assert axes["check_gap_state"]["status"] == (
            "NOT_EVALUATED" if unavailable else
            "OBSERVED_DIFFERENT" if kind == "report_date" else "OBSERVED_SAME")
        if kind == "report_date":
            assert gaps["current"]["pairs"][0]["right"]["check_status"] == (
                "AFTER_FILING_REPORT_END")
            assert gaps["current"]["pairs"][0]["blocking_reasons"] == [
                "right:period_check:AFTER_FILING_REPORT_END"]
    assert pins == _footprint(foundation)
    _reference_only(result)


@pytest.mark.parametrize("with_gaps,with_records", ((False, False), (True, False), (True, True)))
def test_first_body_between_cutoffs_keeps_current_material_hashes(
    foundation, with_gaps, with_records,
):
    _capture(foundation, at=_helpers()["NOW"] + timedelta(seconds=3))
    pins = _footprint(foundation)
    result = _changes(foundation, with_identity=with_gaps,
                      with_gaps=with_gaps, with_records=with_records)
    previous, current = result["previous_inventory"], result["current_inventory"]
    assert previous["source_bound"] is False
    assert previous["source_occurrence_inventory_evaluated"] is False
    assert current["source_bound"] is True
    assert current["source_occurrence_inventory_evaluated"] is True
    assert current["capture_freshness"] == "WITHIN_LIMIT"
    materials = {"parent_binding": current["source_parent_binding"],
        "selected_capture_reference": [current["source_selected_evidence_id"],
                                       current["capture_available_at"]],
        "body_bytes": current["source_body_sha256"]}
    for name, value in materials.items():
        assert value is not None
        _assert_reference_material(result["source_reference_observations"][name],
                                   None, value, "NOT_EVALUATED")
    _assert_reference_material(result["source_reference_observations"]["period_receipt_identity"],
        previous["source_period_input_hash"], current["source_period_input_hash"],
        "OBSERVED_DIFFERENT")
    if with_gaps:
        gaps = result["check_gap_state_material"]
        assert gaps["previous"] is None
        assert gaps["current"]["source_occurrence_count"] == 2
        assert gaps["current"]["unsupported_source_occurrence_count"] == 0
        axis = dict(result["source_reference_observations"]["check_gap_state"])
        assert axis.pop("interpretation_status") == "NOT_EVALUATED"
        _assert_reference_material(axis, None, gaps["current"], "NOT_EVALUATED")
    if with_records:
        assert result["record_projection_counts"]["previous"] is None
        assert len(result["record_projection_counts"]["current"]) == 2
        for name in ("parsed_subset_records", "parser_occurrence_representation"):
            axis = result["source_reference_observations"][name]
            assert axis["status"] == axis["interpretation_status"] == "NOT_EVALUATED"
            assert axis["previous_material_hash"] is None
            assert axis["current_material_hash"] is not None
    assert pins == _footprint(foundation)
    _reference_only(result)


def test_cutoff_only_source_reference_observation_is_not_body_change(foundation):
    _capture(foundation)
    pins = _footprint(foundation)
    result = _changes(foundation)
    assert result == _changes(foundation)
    axes = result["source_reference_observations"]
    assert axes["period_receipt_identity"]["status"] == "OBSERVED_DIFFERENT"
    assert axes["selected_capture_reference"]["status"] == "OBSERVED_SAME"
    assert axes["body_bytes"]["status"] == "OBSERVED_SAME"
    body = {key: value for key, value in result.items() if key != "observation_hash"}
    assert result["observation_hash"] == sha256(financial_input_json(body).encode()).hexdigest()
    assert pins == _footprint(foundation)
    _reference_only(result)


@pytest.mark.parametrize("kind", ("recapture", "value", "whitespace"))
def test_recapture_body_change_and_representation_are_not_economic_comparison(foundation, kind):
    _capture(foundation)
    content = _content()
    if kind == "value":
        content = content.replace(b">120<", b">121<")
    elif kind == "whitespace":
        content = content.replace(b"</html>", b"\n</html>")
    _capture(foundation, content, at=_helpers()["NOW"] + timedelta(seconds=3))
    result = _changes(foundation)
    axes = result["source_reference_observations"]
    assert axes["selected_capture_reference"]["status"] == "OBSERVED_DIFFERENT"
    assert axes["body_bytes"]["status"] == (
        "OBSERVED_SAME" if kind == "recapture" else "OBSERVED_DIFFERENT")
    assert "representation_location" in result["unimplemented_comparison_axes"]
    _reference_only(result)


@pytest.mark.parametrize("kind", (
    "missing", "failed", "tampered", "ambiguous", "future_complete", "wrong_root",
))
@pytest.mark.parametrize("with_identity,with_gaps,with_records", (
    (False, False, False), (True, False, False), (True, True, False), (True, True, True),
))
def test_unusable_sources_never_compare_as_unchanged(
    foundation, tmp_path, kind, with_identity, with_gaps, with_records,
):
    helper = _helpers()
    chosen = foundation
    if kind != "missing":
        _capture(foundation)
    if kind == "failed":
        _capture(foundation, error="http_403", at=helper["NOW"] + timedelta(seconds=3))
    elif kind == "tampered":
        for path in foundation[1].root.rglob("*.bin"):
            if b"body_base64" in path.read_bytes():
                path.write_bytes(b"synthetic corruption")
    elif kind == "ambiguous":
        _capture(foundation, _content().replace(b">120<", b">121<"))
    elif kind == "future_complete":
        _capture(foundation, at=helper["NOW"] + timedelta(seconds=3),
                 completed=helper["NOW"] + timedelta(seconds=5))
    elif kind == "wrong_root":
        chosen = (foundation[0], FileSystemArtifactStore(tmp_path / "wrong-root"))
    pins = _footprint(foundation)
    result = _changes(chosen, with_identity=with_identity,
                      with_gaps=with_gaps, with_records=with_records)
    for name in ("body_bytes", "parent_binding", "selected_capture_reference"):
        assert result["source_reference_observations"][name]["status"] == "NOT_EVALUATED"
    assert not result["current_inventory"]["source_occurrence_inventory_evaluated"]
    assert result["current_inventory"]["source_occurrence_count"] is None
    if kind in {"failed", "future_complete"}:
        assert result["previous_inventory"]["source_occurrence_inventory_evaluated"]
    if with_identity:
        assert result["selected_capture_identity_material"]["current"] is None
        assert result["source_reference_observations"]["selected_capture_identity"][
            "status"] == "NOT_EVALUATED"
    if with_gaps:
        assert result["check_gap_state_material"]["current"] is None
        assert result["source_reference_observations"]["check_gap_state"][
            "status"] == "NOT_EVALUATED"
    if with_records:
        assert result["record_projection_counts"]["current"] is None
        for name in ("parsed_subset_records", "parser_occurrence_representation"):
            assert result["source_reference_observations"][name]["status"] == "NOT_EVALUATED"
    assert pins == _footprint(foundation)
    _reference_only(result)


def test_source_capture_becoming_stale_is_not_unchanged_content_approval(foundation):
    _capture(foundation)
    boundary = _helpers()["NOW"] + timedelta(seconds=3601)
    result = _changes(foundation, previous=boundary,
                      current=boundary + timedelta(microseconds=1))
    assert result["previous_inventory"]["capture_freshness"] == "WITHIN_LIMIT"
    assert result["current_inventory"]["capture_freshness"] == "STALE"
    assert result["source_reference_observations"]["body_bytes"]["status"] == "NOT_EVALUATED"
    _reference_only(result)


def test_source_byte_agreement_does_not_override_window_context_blockers(foundation):
    _capture(foundation)
    result = _changes(foundation, pairs=(replace(PAIR,
        expected_namespace="http://fasb.org/us-gaap/2026"),))
    assert result["source_reference_observations"]["body_bytes"]["status"] == "OBSERVED_SAME"
    assert result["current_inventory"]["pairs"][0]["raw_context_status"] == "BLOCKED"
    _reference_only(result)


@pytest.mark.parametrize("previous,current", (
    (None, _helpers()["NOW"]), (_helpers()["NOW"], None),
    (_helpers()["NOW"].replace(tzinfo=None), _helpers()["NOW"]),
    (_helpers()["NOW"], _helpers()["NOW"].replace(tzinfo=None)),
    (_helpers()["NOW"], _helpers()["NOW"]),
    (_helpers()["NOW"] + timedelta(seconds=1), _helpers()["NOW"]),
    (datetime.fromisoformat("0001-01-01T00:00:00+01:00"), _helpers()["NOW"]),
    (_helpers()["NOW"], datetime.fromisoformat("9999-12-31T23:59:59-01:00")),
))
def test_reference_cutoffs_reject_before_inventory_calls(
    foundation, monkeypatch, previous, current,
):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid cutoffs must not enter an inventory reader")
    monkeypatch.setattr(inventory, "read_sec_window_inventory", forbidden)
    with pytest.raises(ValueError):
        inventory.read_sec_source_reference_changes(
            SQLiteStore(foundation[0].path, read_only=True), foundation[1],
            _helpers()["CIK"], _helpers()["ACCESSION"], symbol="MSFT",
            previous_as_of=previous, as_of=current, pairs=(PAIR,), maximum_capture_age_seconds=3600)


def test_reference_cutoffs_compare_actual_utc_and_preserve_offset_equivalence(foundation):
    _capture(foundation)
    first, last = (_helpers()["NOW"] + timedelta(seconds=n) for n in (2, 4))
    assert _changes(foundation) == _changes(foundation,
        previous=first.astimezone(ZoneInfo("Asia/Kuala_Lumpur")),
        current=last.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    last = first.replace(fold=1)
    _capture(foundation, at=first.astimezone(UTC))
    result = _changes(foundation, previous=first + timedelta(seconds=1), current=last)
    assert result["source_reference_observations"]["body_bytes"]["status"] == "OBSERVED_SAME"


def test_source_reference_observation_rejects_writable_store(foundation):
    helper = _helpers()
    with pytest.raises(ValueError, match="read-only"):
        inventory.read_sec_source_reference_changes(*foundation,
            helper["CIK"], helper["ACCESSION"], symbol="MSFT", previous_as_of=helper["NOW"],
            as_of=helper["NOW"] + timedelta(seconds=1), pairs=(PAIR,),
            maximum_capture_age_seconds=3600)


@pytest.mark.parametrize("with_identity,with_gaps,with_records", (
    (False, False, False), (True, False, False), (True, True, False), (True, True, True),
))
def test_both_reference_cutoffs_share_one_snapshot_during_writer_update(
    foundation, monkeypatch, with_identity, with_gaps, with_records,
):
    _capture(foundation)
    original = inventory.read_sec_period_research_input
    calls = []

    def interleaved(store, *args, **kwargs):
        assert store.read_only and store.has_active_connection
        bound = original(store, *args, **kwargs)
        calls.append(kwargs["as_of"])
        if len(calls) == 1:
            _capture(foundation, error="http_403", at=_helpers()["NOW"] + timedelta(seconds=3))
        return bound

    with monkeypatch.context() as patch:
        patch.setattr(inventory, "read_sec_period_research_input", interleaved)
        result = _changes(foundation, with_identity=with_identity,
                          with_gaps=with_gaps, with_records=with_records)
    assert len(calls) == 2 and calls[0] < calls[1]
    assert result["source_reference_observations"]["body_bytes"]["status"] == "OBSERVED_SAME"
    if with_identity:
        assert result["source_reference_observations"]["selected_capture_identity"][
            "status"] == "OBSERVED_SAME"
    if with_gaps:
        assert result["source_reference_observations"]["check_gap_state"][
            "status"] == "OBSERVED_SAME"
    if with_records:
        for name in ("parsed_subset_records", "parser_occurrence_representation"):
            assert result["source_reference_observations"][name]["status"] == "OBSERVED_SAME"
    assert _changes(foundation)["source_reference_observations"]["body_bytes"][
        "status"] == "NOT_EVALUATED"


def test_source_reference_cli_is_opt_in_deterministic_and_preserves_default_bytes(foundation):
    _capture(foundation)
    args = _cli(foundation[0].path, foundation[1].root)
    default = subprocess.run(args, capture_output=True, text=True)
    assert default.stdout == financial_input_json(_read(foundation)) + "\n"
    args += ["--previous-as-of", (_helpers()["NOW"] + timedelta(seconds=1)).isoformat()]
    pins = _footprint(foundation)
    first, second = (subprocess.run(args, capture_output=True, text=True) for _ in range(2))
    assert first.returncode == second.returncode == 2 and not first.stderr + second.stderr
    assert first.stdout == second.stdout
    _reference_only(json.loads(first.stdout))
    assert pins == _footprint(foundation)


@pytest.mark.parametrize("previous", (
    "synthetic-private-probe", _helpers()["NOW"].replace(tzinfo=None).isoformat(),
    (_helpers()["NOW"] + timedelta(seconds=2)).isoformat(),
    (_helpers()["NOW"] + timedelta(seconds=3)).isoformat(),
    "0001-01-01T00:00:00+01:00",
))
def test_reference_cli_errors_are_sanitized_and_do_not_create_storage(tmp_path, previous):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    result = subprocess.run([*_cli(database, raw), "--previous-as-of", previous],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert "synthetic-private-probe" not in result.stderr and "Traceback" not in result.stderr
    assert not database.exists() and not raw.exists()


@pytest.mark.parametrize("kind", (
    "same", "recapture", "body_change", "missing", "first", "failed", "stale",
))
def test_opt_in_complete_capture_identity_binds_original_factory(foundation, kind):
    helper = _helpers()
    if kind not in {"missing", "first"}:
        _capture(foundation)
    if kind in {"recapture", "body_change", "first", "failed"}:
        content = _content().replace(b">120<", b">121<") if kind == "body_change" else _content()
        _capture(foundation, content, at=helper["NOW"] + timedelta(seconds=3),
                 error="http_403" if kind == "failed" else "")
    previous, current = (helper["NOW"] + timedelta(seconds=n) for n in (2, 4))
    if kind == "stale":
        previous = helper["NOW"] + timedelta(seconds=3601)
        current = previous + timedelta(microseconds=1)
    pins = _footprint(foundation)
    result = _changes(foundation, previous=previous, current=current, with_identity=True)
    assert result == _changes(foundation, previous=previous, current=current, with_identity=True)
    assert result["model_version"] == SEC_SOURCE_CAPTURE_IDENTITY_VERSION
    assert "full_selected_capture_including_raw_data_hash" not in result[
        "unimplemented_comparison_axes"]
    expected = {}
    for name, at, usable in (("previous", previous, kind not in {"missing", "first"}),
                             ("current", current, kind not in {"missing", "failed", "stale"})):
        original = inventory.read_sec_period_research_input(
            SQLiteStore(foundation[0].path, read_only=True), foundation[1],
            helper["CIK"], helper["ACCESSION"], symbol="MSFT", as_of=at,
            selections=(LEFT, RIGHT), sector_profile="unknown").document()
        capture = next((row for row in original["source_captures"]
                        if row["evidence_id"] == original["source_evidence_id"]), None)
        if usable:
            assert capture is not None
            expected[name] = {key: capture[key]
                             for key in ("evidence_id", "available_at", "raw_data_hash")}
            assert capture["raw_data_hash"] != original["source_body_sha256"]
            assert capture["raw_data_hash"] != original["source_parent_binding"][
                "parent_raw_data_hash"]
        else:
            expected[name] = None
    assert result["selected_capture_identity_material"] == expected
    status = "NOT_EVALUATED" if kind in {"missing", "first", "failed", "stale"} else (
        "OBSERVED_SAME" if kind == "same" else "OBSERVED_DIFFERENT")
    _assert_reference_material(result["source_reference_observations"]["selected_capture_identity"],
                               expected["previous"], expected["current"], status)
    legacy = _changes(foundation, previous=previous, current=current)
    assert "selected_capture_identity_material" not in legacy
    assert "selected_capture_identity" not in legacy["source_reference_observations"]
    assert legacy["previous_inventory"] == result["previous_inventory"]
    assert legacy["current_inventory"] == result["current_inventory"]
    for name, axis in legacy["source_reference_observations"].items():
        assert result["source_reference_observations"][name] == axis
    assert pins == _footprint(foundation)
    _reference_only(result)


@pytest.mark.parametrize("defect", (
    "absent", "missing_hash", "empty_hash", "uppercase_hash", "numeric_hash",
    "wrong_id", "wrong_time",
))
@pytest.mark.parametrize("with_gaps,with_records", ((False, False), (True, False), (True, True)))
def test_capture_identity_does_not_fill_missing_or_mismatched_material(
    foundation, monkeypatch, defect, with_gaps, with_records,
):
    _capture(foundation)
    reader = inventory._read_sec_window_inventory

    def incomplete(*args, **kwargs):
        frame, capture, bound = reader(*args, **kwargs)
        assert capture is not None
        if kwargs["as_of"] == _helpers()["NOW"] + timedelta(seconds=4):
            capture = dict(capture)
            if defect == "absent":
                capture = None
            elif defect == "missing_hash":
                del capture["raw_data_hash"]
            elif defect == "empty_hash":
                capture["raw_data_hash"] = ""
            elif defect == "uppercase_hash":
                capture["raw_data_hash"] = "A" * 64
            elif defect == "numeric_hash":
                capture["raw_data_hash"] = 1
            elif defect == "wrong_id":
                capture["evidence_id"] = "a" * 64
            else:
                capture["available_at"] = _helpers()["NOW"].isoformat()
        return frame, capture, bound

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", incomplete)
    result = _changes(foundation, with_identity=True,
                      with_gaps=with_gaps, with_records=with_records)
    material = result["selected_capture_identity_material"]
    assert material["previous"] is not None and material["current"] is None
    _assert_reference_material(result["source_reference_observations"]["selected_capture_identity"],
                               material["previous"], None, "NOT_EVALUATED")
    assert result["source_reference_observations"]["body_bytes"]["status"] == "OBSERVED_SAME"
    if with_gaps:
        assert result["check_gap_state_material"]["current"] is None
        assert result["source_reference_observations"]["check_gap_state"][
            "status"] == "NOT_EVALUATED"
    if with_records:
        assert result["record_projection_counts"]["current"] is None
        for name in ("parsed_subset_records", "parser_occurrence_representation"):
            assert result["source_reference_observations"][name]["status"] == "NOT_EVALUATED"
    _reference_only(result)


@pytest.mark.parametrize("flag", (None, 0, 1, "true", (), object()))
def test_capture_identity_flag_is_exact_boolean_before_reader(foundation, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid option must not enter any source reader")

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", forbidden)
    monkeypatch.setattr(inventory, "read_sec_window_inventory", forbidden)
    pins = _footprint(foundation)
    with pytest.raises(ValueError, match="exact boolean"):
        _changes(foundation, with_identity=flag)
    assert pins == _footprint(foundation)


def test_capture_identity_hash_only_projection_fault_is_not_lost(foundation, monkeypatch):
    _capture(foundation)
    reader = inventory._read_sec_window_inventory
    alternative = sha256(b"synthetic projection-only envelope").hexdigest()

    def changed_projection(*args, **kwargs):
        frame, capture, bound = reader(*args, **kwargs)
        assert capture is not None
        if kwargs["as_of"] == _helpers()["NOW"] + timedelta(seconds=4):
            assert capture["raw_data_hash"] != alternative
            capture = {**capture, "raw_data_hash": alternative}
        return frame, capture, bound

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", changed_projection)
    result = _changes(foundation, with_identity=True)
    identities = result["selected_capture_identity_material"]
    assert identities["current"]["raw_data_hash"] == alternative
    for key in ("evidence_id", "available_at"):
        assert identities["previous"][key] == identities["current"][key]
    _assert_reference_material(result["source_reference_observations"]["selected_capture_identity"],
                               identities["previous"], identities["current"], "OBSERVED_DIFFERENT")
    for name in ("selected_capture_reference", "parent_binding", "body_bytes"):
        assert result["source_reference_observations"][name]["status"] == "OBSERVED_SAME"
    _reference_only(result)


def test_capture_identity_cli_requires_previous_cutoff_without_creating_storage(tmp_path):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    result = subprocess.run([*_cli(database, raw), "--with-selected-capture-identity"],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only SEC window inputs could not be verified.\n"
    assert not database.exists() and not raw.exists()


def test_capture_identity_cli_is_explicit_and_matches_api(foundation):
    _capture(foundation)
    pins = _footprint(foundation)
    args = [*_cli(foundation[0].path, foundation[1].root), "--previous-as-of",
            (_helpers()["NOW"] + timedelta(seconds=1)).isoformat()]
    legacy = subprocess.run(args, capture_output=True, text=True)
    first, second = (subprocess.run([*args, "--with-selected-capture-identity"],
        capture_output=True, text=True) for _ in range(2))
    assert first.returncode == second.returncode == legacy.returncode == 2
    assert not first.stderr + second.stderr + legacy.stderr
    assert first.stdout == second.stdout == financial_input_json(_changes(foundation,
        previous=_helpers()["NOW"] + timedelta(seconds=1),
        current=_helpers()["NOW"] + timedelta(seconds=2), with_identity=True)) + "\n"
    assert json.loads(legacy.stdout)["model_version"] != SEC_SOURCE_CAPTURE_IDENTITY_VERSION
    assert pins == _footprint(foundation)
    _reference_only(json.loads(first.stdout))


@pytest.mark.parametrize("kind", (
    "same", "recapture", "value", "location", "namespace", "unresolved", "duplicate", "conflict",
))
def test_check_gap_projection_separates_states_from_content_and_locations(foundation, kind):
    _capture(foundation)
    content = _content()
    if kind == "value":
        content = content.replace(b">120<", b">121<")
    elif kind == "location":
        content = content.replace(b"<head/>", b"<head><meta/></head>")
    elif kind == "namespace":
        content = _content(prior_namespace="http://fasb.org/us-gaap/2026")
    elif kind in {"unresolved", "duplicate", "conflict"}:
        context = "missing" if kind == "unresolved" else "c"
        amount = "121" if kind == "conflict" else "120"
        content = _content(extra=f'''<ix:nonFraction name="us-gaap:Revenues"
            contextRef="{context}" unitRef="u" scale="6" decimals="-6">{amount}</ix:nonFraction>''')
    if kind != "same":
        _capture(foundation, content, at=_helpers()["NOW"] + timedelta(seconds=3))
    pins = _footprint(foundation)
    result = _changes(foundation, with_identity=True, with_gaps=True)
    assert result == _changes(foundation, with_identity=True, with_gaps=True)
    assert result["model_version"] == SEC_SOURCE_CHECK_GAP_VERSION
    assert result["unimplemented_comparison_axes"] == ["parsed_subset_records",
                                                       "representation_location"]
    gaps = result["check_gap_state_material"]
    axis = dict(result["source_reference_observations"]["check_gap_state"])
    assert axis.pop("interpretation_status") == "SAME_VERSIONS"
    status = ("OBSERVED_DIFFERENT"
              if kind in {"namespace", "unresolved", "duplicate", "conflict"}
              else "OBSERVED_SAME")
    _assert_reference_material(axis, gaps["previous"], gaps["current"], status)
    assert gaps["previous"]["source_occurrence_count"] == 2
    assert gaps["previous"]["unsupported_source_occurrence_count"] == 0
    assert gaps["current"]["source_occurrence_count"] == (
        3 if kind in {"unresolved", "duplicate", "conflict"} else 2)
    assert gaps["current"]["unsupported_source_occurrence_count"] == (
        1 if kind == "unresolved" else 0)
    current_pair = gaps["current"]["pairs"][0]
    for side in ("left", "right"):
        assert current_pair[side]["matching_occurrence_count"] == (
            2 if side == "right" and kind in {"duplicate", "conflict"} else 1)
        assert current_pair[side]["unresolved_tag_occurrence_count"] == (
            1 if kind == "unresolved" else 0)
    if kind == "conflict":
        assert current_pair["right"]["check_status"] == "NUMERIC_CONFLICT"
        assert current_pair["right"]["numeric_agreement_within_supported_subset"] is False
        assert current_pair["blocking_reasons"] == ["right:period_check:NUMERIC_CONFLICT"]
    for name in ("previous", "current"):
        frame = result[f"{name}_inventory"]
        projection = gaps[name]
        assert set(projection) == {"source_model_version", "source_review_version",
            "source_occurrence_count", "unsupported_source_occurrence_count", "pairs"}
        assert projection["source_occurrence_count"] == frame["source_occurrence_count"]
        for observed, original in zip(projection["pairs"], frame["pairs"], strict=True):
            assert set(observed) == {"expected_namespace", "left", "right",
                                     "raw_context_status", "blocking_reasons"}
            assert observed["blocking_reasons"] == original["blocking_reasons"]
            for side in ("left", "right"):
                assert observed[side]["selection"] == original[side]["selection"]
                assert observed[side]["unresolved_tag_occurrence_count"] == len(
                    original[side]["unresolved_tag_occurrence_indices"])
                assert set(observed[side]) == {"selection", "check_status",
                    "requested_period_basis", "requested_duration_calendar_days",
                    "matching_occurrence_count", "numeric_agreement_within_supported_subset",
                    "unresolved_tag_contexts_present", "unresolved_tag_occurrence_count"}
    if kind == "location":
        assert result["previous_inventory"]["pairs"][0]["left"]["occurrence_references"] != (
            result["current_inventory"]["pairs"][0]["left"]["occurrence_references"])
    if kind in {"value", "location"}:
        assert result["source_reference_observations"]["body_bytes"][
            "status"] == "OBSERVED_DIFFERENT"
    if kind == "namespace":
        assert gaps["current"]["pairs"][0]["raw_context_status"] == "BLOCKED"
    assert pins == _footprint(foundation)
    _reference_only(result)


@pytest.mark.parametrize("field", ("source_model_version", "source_review_version"))
def test_check_gap_interpretation_version_fault_keeps_material_unassessed(
    foundation, monkeypatch, field,
):
    _capture(foundation)
    reader = inventory._read_sec_window_inventory

    def changed(*args, **kwargs):
        frame, capture, bound = reader(*args, **kwargs)
        if kwargs["as_of"] == _helpers()["NOW"] + timedelta(seconds=4):
            frame = {**frame, field: "synthetic-unsupported-version"}
        return frame, capture, bound

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", changed)
    result = _changes(foundation, with_identity=True, with_gaps=True)
    gaps = result["check_gap_state_material"]
    axis = dict(result["source_reference_observations"]["check_gap_state"])
    assert axis.pop("interpretation_status") == "VERSION_CHANGED"
    assert gaps["previous"] is not None and gaps["current"] is not None
    _assert_reference_material(axis, gaps["previous"], gaps["current"], "NOT_EVALUATED")
    _reference_only(result)


@pytest.mark.parametrize("flag", (None, 0, 1, "true", (), object()))
def test_check_gap_option_is_exact_bool_before_read(foundation, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid gap option must not enter source readers")

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", forbidden)
    with pytest.raises(ValueError, match="exact boolean"):
        _changes(foundation, with_identity=True, with_gaps=flag)


def test_check_gap_requires_complete_identity_before_read(foundation, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("missing identity opt-in must not enter source readers")

    monkeypatch.setattr(inventory, "read_sec_window_inventory", forbidden)
    monkeypatch.setattr(inventory, "_read_sec_window_inventory", forbidden)
    with pytest.raises(ValueError, match="requires complete"):
        _changes(foundation, with_gaps=True)


def test_check_gap_pair_order_is_canonical_and_old_v2_unchanged(foundation):
    _capture(foundation)
    reverse = SECWindowPair(RIGHT, LEFT, NS)
    result = _changes(foundation, pairs=(PAIR, reverse), with_identity=True, with_gaps=True)
    assert result == _changes(foundation, pairs=(reverse, PAIR), with_identity=True, with_gaps=True)
    prior = _changes(foundation, pairs=(PAIR, reverse), with_identity=True)
    assert prior["model_version"] == SEC_SOURCE_CAPTURE_IDENTITY_VERSION
    assert "check_gap_state_material" not in prior
    for name, axis in prior["source_reference_observations"].items():
        assert result["source_reference_observations"][name] == axis
    assert result["previous_inventory"] == prior["previous_inventory"]
    assert result["current_inventory"] == prior["current_inventory"]


@pytest.mark.parametrize("identity,previous", ((False, True), (True, False)))
def test_check_gap_cli_dependencies_fail_before_storage(tmp_path, identity, previous):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    args = [*_cli(database, raw), "--with-check-gap-state"]
    if identity:
        args += ["--with-selected-capture-identity"]
    if previous:
        args += ["--previous-as-of", _helpers()["NOW"].isoformat()]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only SEC window inputs could not be verified.\n"
    assert not database.exists() and not raw.exists()


def test_check_gap_cli_matches_api_and_stays_unqualified(foundation):
    _capture(foundation)
    args = [*_cli(foundation[0].path, foundation[1].root), "--with-check-gap-state",
        "--with-selected-capture-identity", "--previous-as-of", _helpers()["NOW"].isoformat()]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    assert result.stdout == financial_input_json(_changes(foundation,
        previous=_helpers()["NOW"], current=_helpers()["NOW"] + timedelta(seconds=2),
        with_identity=True, with_gaps=True)) + "\n"
    _reference_only(json.loads(result.stdout))
