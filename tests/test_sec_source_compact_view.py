"""Compact source diagnostics keep full recomputation and explicit unqualified scope."""

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
from tong_quant.version import SEC_SOURCE_COMPACT_VIEW_VERSION


@lru_cache
def _windows():
    return runpy.run_path(str(Path(__file__).with_name("test_sec_window_inventory.py")))


@pytest.fixture
def foundation(tmp_path):
    return _windows()["foundation"].__wrapped__(tmp_path)


def _options(mode):
    return {"with_identity": mode >= 2, "with_gaps": mode >= 3, "with_records": mode >= 4}


def _assert_bound_view(full, view):
    assert view["model_version"] == SEC_SOURCE_COMPACT_VIEW_VERSION
    assert view["output_scope"] == "COMPACT_SOURCE_OBSERVATION_VIEW"
    assert view["source_observation_model_version"] == full["model_version"]
    assert view["source_observation_hash"] == full["observation_hash"]
    assert not {"observation_hash", "previous_inventory", "current_inventory"}.intersection(view)
    for key, value in full.items():
        if key not in {"model_version", "observation_hash", "previous_inventory",
                       "current_inventory", "limitations"}:
            assert view[key] == value
    assert view["limitations"][:-1] == full["limitations"]
    assert view["limitations"][-1] == (
        "compact_view_omits_detail_and_is_not_a_new_source_or_research_report")
    skipped = {"occurrence_references", "unresolved_tag_occurrence_indices"}
    assert set(view["omitted_occurrence_fields"]) == skipped
    omitted = set()
    for name in ("previous", "current"):
        original, summary = full[f"{name}_inventory"], view[f"{name}_source_summary"]
        assert summary["full_inventory_hash"] == original["inventory_hash"]
        assert summary["inventory_model_version"] == original["model_version"]
        for key, value in summary.items():
            if key not in {"full_inventory_hash", "inventory_model_version", "pairs"}:
                assert value == original[key]
        included = set(summary) - {"full_inventory_hash", "inventory_model_version", "pairs"}
        omitted.update(set(original) - included - {"inventory_hash", "model_version", "pairs"})
        assert len(summary["pairs"]) == len(original["pairs"])
        for prior, current in zip(original["pairs"], summary["pairs"], strict=True):
            for key, value in prior.items():
                if key not in {"left", "right"}:
                    assert current[key] == value
            for side in ("left", "right"):
                assert not skipped.intersection(current[side])
                for key, value in prior[side].items():
                    if key not in skipped:
                        assert current[side][key] == value
                indices = prior[side]["unresolved_tag_occurrence_indices"]
                assert current[side]["unresolved_tag_occurrence_count"] == (
                    len(indices) if indices is not None else None)
    assert view["omitted_inventory_fields"] == sorted(omitted)
    content = {key: value for key, value in view.items() if key != "summary_hash"}
    assert view["summary_hash"] == sha256(financial_input_json(content).encode()).hexdigest()
    assert view["summary_hash"] != view["source_observation_hash"]
    _windows()["_reference_only"](full)


@pytest.mark.parametrize("mode", (1, 2, 3, 4))
@pytest.mark.parametrize("kind", (
    "same", "missing", "failed", "stale", "namespace", "unresolved", "first", "many", "empty",
))
def test_compact_modes_preserve_diagnostics_and_bound_full_identity(foundation, mode, kind):
    window, helper = _windows(), _windows()["_helpers"]()
    options = _options(mode)
    content = window["_content"]()
    if kind == "namespace":
        content = window["_content"](prior_namespace="http://fasb.org/us-gaap/2026")
    elif kind in {"unresolved", "many"}:
        context = "missing" if kind == "unresolved" else "c"
        extra = f'''<ix:nonFraction name="us-gaap:Revenues" contextRef="{context}"
            unitRef="u" decimals="-6" scale="6">120</ix:nonFraction>'''
        content = window["_content"](extra=extra * (80 if kind == "many" else 1))
    if kind not in {"missing", "first"}:
        window["_capture"](foundation, content)
    if kind in {"failed", "first"}:
        window["_capture"](foundation, at=helper["NOW"] + timedelta(seconds=3),
                           error="http_403" if kind == "failed" else "")
    if kind == "stale":
        boundary = helper["NOW"] + timedelta(seconds=3601)
        options.update(previous=boundary, current=boundary + timedelta(microseconds=1))
    if kind == "empty":
        left = replace(window["LEFT"], period_start=date(2020, 7, 1), period_end=date(2021, 6, 30))
        right = replace(window["RIGHT"], period_start=date(2021, 7, 1),
                        period_end=date(2022, 6, 30))
        options["pairs"] = (inventory.SECWindowPair(left, right, window["NS"]),)
    pins = window["_footprint"](foundation)
    full = window["_changes"](foundation, **options)
    before = financial_input_json(full)
    view = window["_changes"](foundation, compact=True, **options)
    assert view == window["_changes"](foundation, compact=True, **options)
    _assert_bound_view(full, view)
    assert financial_input_json(full) == before
    assert len(financial_input_json(view).encode()) < len(before.encode())
    current = view["current_source_summary"]
    if kind in {"missing", "failed"}:
        assert current["source_occurrence_count"] is None
        assert current["source_occurrence_inventory_evaluated"] is False
        assert current["pairs"][0]["left"]["unresolved_tag_occurrence_count"] is None
    if kind == "empty":
        assert current["source_occurrence_count"] == 2
        assert current["pairs"][0]["left"]["matching_occurrence_count"] == 0
        assert current["pairs"][0]["raw_context_status"] == "BLOCKED"
    if kind in {"namespace", "unresolved"}:
        assert current["pairs"][0]["blocking_reasons"]
    assert pins == window["_footprint"](foundation)


@pytest.mark.parametrize("flag", (None, 0, 1, "true", (), object()))
def test_compact_option_requires_exact_bool_before_source_reads(foundation, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid compact flag must not enter source factories")

    monkeypatch.setattr(inventory, "read_sec_period_research_input", forbidden)
    with pytest.raises(ValueError, match="exact boolean"):
        _windows()["_changes"](foundation, compact=flag)


def test_compact_recomputes_original_sources_not_a_cached_or_caller_receipt(
    foundation, monkeypatch,
):
    window = _windows()
    window["_capture"](foundation)
    original = inventory.read_sec_period_research_input
    calls = []

    def checked(store, *args, **kwargs):
        assert store.read_only and store.has_active_connection
        calls.append(kwargs["as_of"])
        return original(store, *args, **kwargs)

    monkeypatch.setattr(inventory, "read_sec_period_research_input", checked)
    first = window["_changes"](foundation, compact=True, **_options(4))
    assert len(calls) == 2 and calls[0] < calls[1]
    first["execution_authorized"] = True
    altered = {key: value for key, value in first.items() if key != "summary_hash"}
    assert sha256(financial_input_json(altered).encode()).hexdigest() != first["summary_hash"]
    second = window["_changes"](foundation, compact=True, **_options(4))
    assert len(calls) == 4 and second["execution_authorized"] is False
    assert first["source_observation_hash"] == second["source_observation_hash"]

    def rejected(*args, **kwargs):
        raise ValueError("synthetic source cannot be reconstructed")

    monkeypatch.setattr(inventory, "read_sec_period_research_input", rejected)
    with pytest.raises(ValueError):
        window["_changes"](foundation, compact=True, **_options(4))


def test_compact_snapshot_keeps_interleaved_latest_failure_outside_current_read(
    foundation, monkeypatch,
):
    window, helper = _windows(), _windows()["_helpers"]()
    window["_capture"](foundation)
    original = inventory.read_sec_period_research_input
    calls = 0

    def interleaved(store, *args, **kwargs):
        nonlocal calls
        result = original(store, *args, **kwargs)
        calls += 1
        if calls == 1:
            window["_capture"](foundation, error="http_403",
                               at=helper["NOW"] + timedelta(seconds=3))
        return result

    with monkeypatch.context() as patch:
        patch.setattr(inventory, "read_sec_period_research_input", interleaved)
        view = window["_changes"](foundation, compact=True, **_options(4))
    assert calls == 2 and view["current_source_summary"]["source_bound"] is True
    assert view["source_reference_observations"]["parsed_subset_records"][
        "status"] == "OBSERVED_SAME"
    later = window["_changes"](foundation, compact=True, **_options(4))
    # A retained failure can be hash-bound while its data remain unusable.
    assert later["current_source_summary"]["source_bound"] is True
    assert later["current_source_summary"]["source_occurrence_inventory_evaluated"] is False
    assert later["current_source_summary"]["source_occurrence_count"] is None
    assert later["source_reference_observations"]["parsed_subset_records"][
        "status"] == "NOT_EVALUATED"


def test_compact_cli_requires_two_cutoffs_before_storage(tmp_path):
    database, raw = tmp_path / "absent.sqlite3", tmp_path / "absent-raw"
    result = subprocess.run([*_windows()["_cli"](database, raw), "--compact"],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == "Read-only SEC window inputs could not be verified.\n"
    assert not database.exists() and not raw.exists()


@pytest.mark.parametrize("mode", (1, 2, 3, 4))
def test_compact_cli_matches_original_factory_api(foundation, mode):
    window, helper = _windows(), _windows()["_helpers"]()
    window["_capture"](foundation)
    args = [*window["_cli"](foundation[0].path, foundation[1].root), "--compact",
        "--previous-as-of", helper["NOW"].isoformat()]
    if mode >= 2:
        args.append("--with-selected-capture-identity")
    if mode >= 3:
        args.append("--with-check-gap-state")
    if mode >= 4:
        args.append("--with-record-projections")
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stderr
    expected = window["_changes"](foundation, compact=True, previous=helper["NOW"],
        current=helper["NOW"] + timedelta(seconds=2), **_options(mode))
    assert json.loads(result.stdout) == json.loads(financial_input_json(expected))
