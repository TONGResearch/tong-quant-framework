"""Source-bound record hashes, never original-XML or financial qualification."""

import json
import runpy
import subprocess
from dataclasses import replace
from datetime import date, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.application import sec_window_inventory as inventory
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.version import SEC_SOURCE_RECORD_PROJECTION_VERSION


@lru_cache
def _windows():
    return runpy.run_path(str(Path(__file__).with_name("test_sec_window_inventory.py")))


@pytest.fixture
def foundation(tmp_path):
    return _windows()["foundation"].__wrapped__(tmp_path)


def _read(foundation, **kwargs):
    return _windows()["_changes"](foundation, with_identity=True, with_gaps=True,
                                  with_records=True, **kwargs)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _expected(bound):
    parsed, representation, counts = [], [], []
    for check in bound.document()["checks"]:
        selection = {key: check[key] for key in ("native_tag", "period_start", "period_end")}
        rows = check["matching_occurrences"]
        material = [{key: row.get(key) for key in ("tag", "taxonomy", "namespace", "entity_cik",
            "period_start", "period_end", "unit", "value", "status", "reason")} for row in rows]
        parsed.append({"selection": selection, "occurrences": sorted(material, key=_canonical)})
        representation.append({"selection": selection,
                               "occurrences": sorted(rows, key=_canonical)})
        counts.append({"selection": selection, "matching_occurrence_count": len(rows)})
    return {"parsed_subset_records": sorted(parsed, key=_canonical),
        "parser_occurrence_representation": sorted(representation, key=_canonical),
        "selection_counts": sorted(counts, key=_canonical)}


def _assert_axis(axis, before, after, status):
    assert axis == {"status": status, "interpretation_status": "SAME_VERSIONS",
        "previous_material_hash": sha256(_canonical(before).encode()).hexdigest(),
        "current_material_hash": sha256(_canonical(after).encode()).hexdigest()}


def _assert_no_values(value):
    if isinstance(value, dict):
        assert not {"value", "raw_text", "native_attributes", "occurrences"}.intersection(value)
        for child in value.values():
            _assert_no_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_no_values(child)


@pytest.mark.parametrize("kind,parsed_status,representation_status", (
    ("same", "OBSERVED_SAME", "OBSERVED_SAME"),
    ("recapture", "OBSERVED_SAME", "OBSERVED_SAME"),
    ("value", "OBSERVED_DIFFERENT", "OBSERVED_DIFFERENT"),
    ("location", "OBSERVED_SAME", "OBSERVED_DIFFERENT"),
    ("markup", "OBSERVED_SAME", "OBSERVED_SAME"),
    ("character_reference", "OBSERVED_SAME", "OBSERVED_SAME"),
    ("context", "OBSERVED_SAME", "OBSERVED_DIFFERENT"),
    ("prefix", "OBSERVED_SAME", "OBSERVED_DIFFERENT"),
    ("decimal", "OBSERVED_DIFFERENT", "OBSERVED_DIFFERENT"),
    ("duplicate", "OBSERVED_DIFFERENT", "OBSERVED_DIFFERENT"),
    ("order", "OBSERVED_SAME", "OBSERVED_DIFFERENT"),
    ("unsupported_preview", "OBSERVED_SAME", "OBSERVED_SAME"),
    ("whitespace_value", "OBSERVED_DIFFERENT", "OBSERVED_DIFFERENT"),
    ("unsupported_reason", "OBSERVED_DIFFERENT", "OBSERVED_DIFFERENT"),
))
def test_original_factory_record_hashes_preserve_scope_and_multiplicity(
    foundation, kind, parsed_status, representation_status,
):
    window, helper = _windows(), _windows()["_helpers"]()
    first = window["_content"]()
    if kind == "markup":
        first = first.replace(b">120<", b"><span>120</span><")
    elif kind == "decimal":
        first = first.replace(b">120<", b">120.0<")
    elif kind == "unsupported_preview":
        first = first.replace(b">120<", b">" + b"1" * 512 + b"2<")
    elif kind == "whitespace_value":
        first = first.replace(b">120<", b">" + b" " * 512 + b"120<")
    elif kind == "unsupported_reason":
        first = first.replace(b'scale="6"', b'scale="6" format="ixt:num-dot-decimal"', 1)
    extra = '''<ix:nonFraction name="us-gaap:Revenues" contextRef="c" unitRef="u"
        decimals="-6" scale="6">120</ix:nonFraction>'''
    if kind == "order":
        first = window["_content"](extra=extra + extra.replace(">120<", ">121<"))
    second = first
    if kind in {"value", "whitespace_value"}:
        second = first.replace(b"120<", b"121<")
    elif kind == "location":
        second = first.replace(b"<head/>", b"<head><meta/></head>")
    elif kind == "markup":
        second = first.replace(b"<span>120</span>", b"<b>120</b>")
    elif kind == "character_reference":
        second = first.replace(b">120<", b">12&#48;<")
    elif kind == "context":
        second = first.replace(b'id="c"', b'id="renamed"').replace(
            b'contextRef="c"', b'contextRef="renamed"')
    elif kind == "prefix":
        second = first.replace(b"xmlns:us-gaap=", b"xmlns:g=").replace(
            b'name="us-gaap:Revenues"', b'name="g:Revenues"')
    elif kind == "decimal":
        second = first.replace(b">120.0<", b">120.00<")
    elif kind == "duplicate":
        second = window["_content"](extra=extra)
    elif kind == "order":
        second = window["_content"](extra=extra + extra).replace(b">120<", b">121<", 1)
    elif kind == "unsupported_preview":
        second = first.replace(b"1" * 512 + b"2<", b"1" * 512 + b"3<")
    elif kind == "unsupported_reason":
        second = first.replace(b'ixt:num-dot-decimal', b'ixt:unknown-transform')
    if kind not in {"same", "recapture"}:
        assert first != second
    window["_capture"](foundation, first)
    if kind != "same":
        window["_capture"](foundation, second, at=helper["NOW"] + timedelta(seconds=3))
    pins = window["_footprint"](foundation)
    result = _read(foundation)
    assert result == _read(foundation)
    assert result["model_version"] == SEC_SOURCE_RECORD_PROJECTION_VERSION
    expected = {}
    for name, seconds in (("previous", 2), ("current", 4)):
        bound = inventory.read_sec_period_research_input(
            SQLiteStore(foundation[0].path, read_only=True), foundation[1],
            helper["CIK"], helper["ACCESSION"], symbol="MSFT",
            as_of=helper["NOW"] + timedelta(seconds=seconds),
            selections=(window["LEFT"], window["RIGHT"]), sector_profile="unknown")
        expected[name] = _expected(bound)
        assert result["record_projection_counts"][name] == expected[name]["selection_counts"]
        counts = expected[name]["selection_counts"]
        assert sum(row["matching_occurrence_count"] for row in counts) == (
            4 if kind == "order" else 3 if kind == "duplicate" and name == "current" else 2)
    for name, status in (("parsed_subset_records", parsed_status),
                          ("parser_occurrence_representation", representation_status)):
        _assert_axis(result["source_reference_observations"][name],
                     expected["previous"][name], expected["current"][name], status)
    if kind in {"markup", "character_reference", "unsupported_preview"}:
        assert result["source_reference_observations"]["body_bytes"][
            "status"] == "OBSERVED_DIFFERENT"
    if kind == "decimal":
        values = [row["value"] for side in expected["current"]["parsed_subset_records"]
                  for row in side["occurrences"]]
        assert "120000000.00" in values
    if kind == "unsupported_preview":
        rows = [row for side in expected["current"]["parsed_subset_records"]
                for row in side["occurrences"] if row["status"] == "UNSUPPORTED_FACT"]
        assert len(rows) == 1 and rows[0]["value"] is None
        assert rows[0]["reason"] == "numeric text exceeds bounds"
    _assert_no_values(result)
    window["_reference_only"](result)
    assert pins == window["_footprint"](foundation)


@pytest.mark.parametrize("flag", (None, 0, 1, "true", (), object()))
def test_record_option_is_exact_bool_before_source_reads(foundation, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid record option must not enter source readers")

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", forbidden)
    with pytest.raises(ValueError, match="exact boolean"):
        _windows()["_changes"](foundation, with_identity=True, with_gaps=True, with_records=flag)


def test_record_option_requires_gap_context_before_source_reads(foundation, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("record option dependency must reject before source reads")

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", forbidden)
    with pytest.raises(ValueError, match="require check-gap"):
        _windows()["_changes"](foundation, with_identity=True, with_records=True)


def test_repeated_window_references_do_not_duplicate_original_selection_records(foundation):
    window = _windows()
    window["_capture"](foundation)
    reverse = inventory.SECWindowPair(window["RIGHT"], window["LEFT"], window["NS"])
    single = _read(foundation)
    repeated = _read(foundation, pairs=(window["PAIR"], reverse))
    assert repeated == _read(foundation, pairs=(reverse, window["PAIR"]))
    assert len(repeated["previous_inventory"]["pairs"]) == 2
    for name in ("previous", "current"):
        assert len(repeated["record_projection_counts"][name]) == 2
        assert repeated["record_projection_counts"][name] == (
            single["record_projection_counts"][name])
    for name in ("parsed_subset_records", "parser_occurrence_representation"):
        assert repeated["source_reference_observations"][name] == (
            single["source_reference_observations"][name])
    window["_reference_only"](repeated)


def test_observed_empty_exact_windows_are_not_unavailable_source_material(foundation):
    window = _windows()
    window["_capture"](foundation)
    left = replace(window["LEFT"], period_start=date(2020, 7, 1), period_end=date(2021, 6, 30))
    right = replace(window["RIGHT"], period_start=date(2021, 7, 1), period_end=date(2022, 6, 30))
    result = _read(foundation, pairs=(inventory.SECWindowPair(left, right, window["NS"]),))
    for name in ("previous", "current"):
        frame = result[f"{name}_inventory"]
        assert frame["source_occurrence_inventory_evaluated"] is True
        assert frame["source_occurrence_count"] == 2
        assert frame["pairs"][0]["raw_context_status"] == "BLOCKED"
        for side in ("left", "right"):
            assert frame["pairs"][0][side]["check_status"] == "MISSING_EXACT_PERIOD"
        counts = result["record_projection_counts"][name]
        assert len(counts) == 2 and all(row["matching_occurrence_count"] == 0 for row in counts)
    for name in ("parsed_subset_records", "parser_occurrence_representation"):
        axis = result["source_reference_observations"][name]
        assert axis["status"] == "OBSERVED_SAME"
        assert axis["previous_material_hash"] == axis["current_material_hash"] is not None
    _assert_no_values(result)
    window["_reference_only"](result)


@pytest.mark.parametrize("defect", (
    "binding_hash", "period_hash", "subject", "model_version", "review_version",
    "capture_hash", "bound_absent", "bound_other_cutoff",
))
def test_record_projection_rejects_cross_bound_internal_material(foundation, monkeypatch, defect):
    window, helper = _windows(), _windows()["_helpers"]()
    window["_capture"](foundation)
    reader = inventory._read_sec_window_inventory

    def mismatched(*args, **kwargs):
        frame, capture, bound = reader(*args, **kwargs)
        if kwargs["as_of"] == helper["NOW"] + timedelta(seconds=4):
            keys = {"binding_hash": "source_research_binding_hash",
                "period_hash": "source_period_input_hash", "subject": "subject",
                "model_version": "source_model_version", "review_version": "source_review_version"}
            if defect in keys:
                frame = {**frame, keys[defect]: "synthetic-mismatch"}
            elif defect == "capture_hash":
                capture = {**capture, "raw_data_hash": "a" * 64}
            elif defect == "bound_absent":
                bound = None
            else:
                earlier = helper["NOW"] + timedelta(seconds=2)
                bound = reader(*args, **{**kwargs, "as_of": earlier})[2]
        return frame, capture, bound

    monkeypatch.setattr(inventory, "_read_sec_window_inventory", mismatched)
    with pytest.raises(ValueError):
        _read(foundation)


@pytest.mark.parametrize("gap,identity,previous", (
    (False, True, True), (True, False, True), (True, True, False),
))
def test_record_cli_dependencies_do_not_create_storage(tmp_path, gap, identity, previous):
    window, helper = _windows(), _windows()["_helpers"]()
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    args = [*window["_cli"](database, raw), "--with-record-projections"]
    if gap:
        args.append("--with-check-gap-state")
    if identity:
        args.append("--with-selected-capture-identity")
    if previous:
        args += ["--previous-as-of", helper["NOW"].isoformat()]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only SEC window inputs could not be verified.\n"
    assert not database.exists() and not raw.exists()


def test_record_cli_matches_api_and_does_not_publish_values(foundation):
    window, helper = _windows(), _windows()["_helpers"]()
    window["_capture"](foundation)
    args = [*window["_cli"](foundation[0].path, foundation[1].root), "--with-record-projections",
        "--with-check-gap-state", "--with-selected-capture-identity", "--previous-as-of",
        helper["NOW"].isoformat()]
    first, second = (subprocess.run(args, capture_output=True, text=True) for _ in range(2))
    assert first.returncode == second.returncode == 2 and not first.stderr + second.stderr
    assert first.stdout == second.stdout
    expected = _read(foundation, previous=helper["NOW"],
                     current=helper["NOW"] + timedelta(seconds=2))
    assert json.loads(first.stdout) == json.loads(financial_input_json(expected))
    _assert_no_values(json.loads(first.stdout))
    window["_reference_only"](expected)
