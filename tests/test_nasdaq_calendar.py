"""Synthetic transport/source receipts must never become an admitted US trading calendar."""

import json
import runpy
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.nasdaq_calendar_inputs import read_nasdaq_calendar_inputs
from tong_quant.data.providers import nasdaq_calendar as source
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

AT = datetime(2026, 11, 7, tzinfo=UTC)
BODY = b"""<html><h1>U.S. Equity and Options Markets Holiday Schedule 2026</h1>
<table><tr><th>2026</th><th>Holiday</th><th>Status</th></tr>
<tr><td>January 2, 2026</td><td>Synthetic closure</td><td>Closed</td></tr>
<tr><td>November 27, 2026</td><td>Early Close* - synthetic</td><td>1:00 p.m.</td></tr>
</table></html>"""


def _request(at=AT, year=2026):
    return ProviderDatasetRequest(source.DATASET, Market.US, source.calendar_subject(year), at,
                                  {"year": str(year)})


def _capture(body=BODY, error=""):
    return source.NasdaqCalendarCapture(body, error)


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "calendar.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "raw")


def _ingest(foundation, capture=None, *, at=AT, year=2026, completed=None):
    store, artifacts = foundation
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: completed or at).ingest(source.NasdaqCalendarAdapter(
            download=lambda _: capture or _capture(), clock=lambda: at), _request(at, year))


def _read(foundation, at=AT, year=2026, **kwargs):
    return read_nasdaq_calendar_inputs(*foundation, year, as_of=at, **kwargs)


def test_retained_original_dates_early_close_and_prospective_schedule_stay_unqualified(foundation):
    _ingest(foundation)
    store, _ = foundation
    before = store.path.read_bytes()
    result = _read(foundation)
    assert result["status"] == "explicit_declarations_unqualified" and result["source_bound"]
    assert result["document_sha256"] == sha256(BODY).hexdigest()
    assert result["document_byte_size"] == len(BODY)
    assert result["exchange"] == "NASDAQ" and result["market_timezone"] == "America/New_York"
    assert result["trust_ceiling"] == "LOW" and result["availability_precision"] == "retrieval_time"
    closed, early = result["declarations"]
    assert closed["trade_date"] == "2026-01-02" and closed["is_open"] is False
    assert early["trade_date"] == "2026-11-27" and early["is_open"] is True
    assert early["core_close_local"] == "13:00:00"
    assert closed["core_close_local"] is None
    assert len(result["declarations"]) == 2  # No implied weekdays or weekends.
    for name in ("published_at_known", "calendar_complete", "actual_session_verified",
        "canonical_calendar_authorized", "scoring_authorized", "historical_replay_eligible",
        "validation_authorized", "execution_authorized"):
        assert result[name] is False
    assert result == _read(foundation, AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur")))
    assert store.path.read_bytes() == before
    for table in ("trading_calendar", "instruments", "daily_bars", "signals", "research_reports"):
        assert store.table_count(table) == 0


def test_capture_does_not_backdate_availability_to_listed_holiday_date(foundation):
    _ingest(foundation)
    assert _read(foundation, AT - timedelta(microseconds=1))["status"] == "missing"
    assert _read(foundation)["captures"][0]["available_at"] == AT


def test_idempotent_ingestion_and_full_hash_are_reproducible(foundation):
    _ingest(foundation)
    first = _read(foundation)
    _ingest(foundation)
    assert first == _read(foundation)
    assert foundation[0].table_count("provider_evidence_records") == 1
    assert foundation[0].table_count("provider_artifacts") == 1
    digest = first.pop("input_hash")
    assert digest == sha256(financial_input_json(first).encode()).hexdigest()


@pytest.mark.parametrize("kind", ["failure", "bad_layout", "tie", "corrupt_bytes",
                                 "not_completed", "tampered_authority"])
def test_latest_bad_capture_never_falls_back_to_an_older_good_calendar(foundation, kind):
    _ingest(foundation)
    at = AT + timedelta(seconds=2)
    capture = (_capture(None, "http_403") if kind == "failure" else
               _capture(b"<html>synthetic unsupported page</html>") if kind == "bad_layout" else
               _capture())
    _ingest(foundation, capture, at=at)
    if kind == "tie":
        _ingest(foundation, _capture(None, "http_429"), at=at)
    elif kind == "corrupt_bytes":
        row = _read(foundation, at)["captures"][-1]
        artifact = foundation[1].root / "sha256" / row["raw_data_hash"][:2] / (
            row["raw_data_hash"] + ".bin")
        artifact.write_bytes(b"synthetic tamper")
    elif kind in {"not_completed", "tampered_authority"}:
        with foundation[0]._connect() as connection:
            if kind == "not_completed":
                connection.execute("UPDATE ingestion_batches SET status = 'failed'")
            else:
                row = connection.execute("SELECT evidence_id, payload_json FROM "
                    "provider_evidence_records ORDER BY available_at DESC LIMIT 1").fetchone()
                payload = json.loads(row["payload_json"])
                payload["scoring_authorized"] = True
                connection.execute("UPDATE provider_evidence_records SET payload_json = ? "
                    "WHERE evidence_id = ?", (json.dumps(payload), row["evidence_id"]))
    result = _read(foundation, at)
    expected = {"failure": "http_403", "bad_layout": "unsupported_calendar_layout"}
    assert result["status"] == expected.get(kind, "rejected_or_ambiguous")
    assert result["declarations"] == [] and result["scoring_authorized"] is False
    guarded = _read(foundation, at, maximum_source_age_seconds=3600)
    assert guarded["freshness"] == "BLOCKED_INPUT"
    assert guarded["source_status"] == result["status"]
    assert guarded["declarations"] == []
    assert guarded["source_capture_at"] == (at if kind == "bad_layout" else None)


@pytest.mark.parametrize("old,new,expected", [
    (b"2026", b"2027", "requested_year_not_present"),
    (b"Closed", b"Unknown system phase", "unsupported_or_conflicting_declarations"),
    (b"January 2, 2026", b"January 40, 2026", "unsupported_or_conflicting_declarations"),
    (b"January 2, 2026", b"January 2, 2025", "unsupported_or_conflicting_declarations"),
    (b"1:00 p.m.", b"13:00", "unsupported_or_conflicting_declarations"),
    (b"<th>Status</th>", b"<th>Something else</th>", "unsupported_calendar_layout"),
    (b"<td>Closed</td>", b"<td>Closed</td><td>Extra</td>", "unsupported_calendar_layout"),
])
def test_schema_drift_and_wrong_year_are_explicit_not_implementation_success(old, new, expected):
    result = source.calendar_declarations(_capture(BODY.replace(old, new)), 2026)
    assert result["status"] == expected


def test_duplicate_table_or_duplicate_dates_cannot_be_silently_selected():
    duplicate = source.calendar_declarations(_capture(BODY + BODY), 2026)
    assert duplicate["status"] == "ambiguous_calendar_tables"
    body = BODY.replace(b"November 27, 2026", b"January 2, 2026")
    assert source.calendar_declarations(_capture(body), 2026)["status"] == (
        "unsupported_or_conflicting_declarations")


@pytest.mark.parametrize("value", [b"12:30 p.m.", b"9:00 a.m."])
def test_early_close_time_is_parsed_from_source_not_hardcoded_to_one_pm(value):
    result = source.calendar_declarations(_capture(BODY.replace(b"1:00 p.m.", value)), 2026)
    assert result["status"] == "explicit_declarations_unqualified"
    assert result["declarations"][1]["core_close_local"] == (
        "12:30:00" if value.startswith(b"12") else "09:00:00")


@pytest.mark.parametrize("year", [True, 1999, 2101, "2026"])
def test_invalid_year_is_rejected(year):
    with pytest.raises(ValueError):
        source.calendar_subject(year)


@pytest.mark.parametrize("defect", ["market", "subject", "dataset", "parameters", "clock"])
def test_adapter_identity_and_actual_utc_capture_are_strict(defect):
    request = _request()
    if defect == "market":
        request = replace(request, market=Market.CHINA_A)
    elif defect == "subject":
        request = replace(request, subject="NYSE:2026")
    elif defect == "dataset":
        request = replace(request, dataset="other")
    elif defect == "parameters":
        request = replace(request, parameters={"year": "2026", "url": "https://example.invalid"})
    clock = AT - timedelta(microseconds=1) if defect == "clock" else AT
    with pytest.raises(ValueError):
        source.NasdaqCalendarAdapter(download=lambda _: _capture(), clock=lambda: clock).fetch(
            request)


@pytest.mark.parametrize("body", [b"", b"x" * (source.MAX_BYTES + 1), b"\xff",
                                 b"token=synthetic-forbidden"])
def test_invalid_or_credential_shaped_body_is_rejected_before_retention(body):
    with pytest.raises(ValueError):
        _capture(body)


@pytest.mark.parametrize("body,error,expected", [(b"", None, "empty_response"),
    (b"x" * (source.MAX_BYTES + 1), None, "response_too_large"),
    (b"\xff", None, "invalid_html_payload"),
    (BODY, 403, "http_403"), (BODY, 429, "http_429"), (BODY, 302, "http_error"),
    (BODY, "network", "network_unavailable"), (BODY, None, "")])
def test_transport_is_fixed_url_bounded_and_reports_sanitized_failure(
    monkeypatch, body, error, expected,
):
    calls = []

    class Reply(BytesIO):
        status = 200

        def geturl(self):
            return source.SOURCE_URL

        def read(self, limit=-1):
            assert limit == source.MAX_BYTES + 1
            return super().read(limit)

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == source.SOURCE_URL and timeout == 15
            assert request.get_header("Accept-encoding") == "identity"
            calls.append(True)
            if error == "network":
                raise URLError("secret=synthetic-must-not-persist")
            if error is not None:
                raise HTTPError(source.SOURCE_URL, error, "synthetic", {}, None)
            return Reply(body)

    monkeypatch.setattr(source, "build_opener", lambda *_: Opener())
    monkeypatch.setattr(source, "sleep", lambda _: None)
    result = source.download_calendar(_request())
    assert result.error_code == expected
    assert len(calls) == (2 if error in {429, "network"} else 1)
    assert result.content == (body if not expected else None)


def test_read_only_cli_is_offline_reproducible_and_preserves_database(
    foundation, monkeypatch, capsys,
):
    _ingest(foundation)
    store, artifacts = foundation
    args = ["scripts/inspect_nasdaq_calendar.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--year", "2026", "--as-of", AT.isoformat()]
    before = store.path.read_bytes()

    def no_network(*args):
        raise AssertionError("read-only calendar attempted network")

    monkeypatch.setattr(source, "download_calendar", no_network)
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(args[0], run_name="__main__")
    assert stopped.value.code == 2
    first = json.loads(capsys.readouterr().out)
    assert first == json.loads(financial_input_json(_read(foundation)))
    assert store.path.read_bytes() == before


def test_cli_capture_refuses_existing_database_before_network(foundation):
    store, artifacts = foundation
    before = store.path.read_bytes()
    result = subprocess.run([sys.executable, "scripts/inspect_nasdaq_calendar.py", "--database",
        str(store.path), "--artifact-root", str(artifacts.root), "--year", "2026", "--capture"],
        capture_output=True, text=True)
    assert result.returncode == 2 and "new diagnostic database" in result.stderr
    assert store.path.read_bytes() == before


def test_cli_capture_retains_raw_body_in_a_new_database_only(tmp_path, monkeypatch, capsys):
    database, artifacts = tmp_path / "new.sqlite3", tmp_path / "raw"
    monkeypatch.setattr(source, "download_calendar", lambda _: _capture())
    args = ["scripts/inspect_nasdaq_calendar.py", "--database", str(database),
        "--artifact-root", str(artifacts), "--year", "2026", "--capture"]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(args[0], run_name="__main__")
    assert stopped.value.code == 2
    result = json.loads(capsys.readouterr().out)
    assert result["document_sha256"] == sha256(BODY).hexdigest()
    assert result["status"] == "explicit_declarations_unqualified"
    assert SQLiteStore(database, read_only=True).table_count("trading_calendar") == 0


def test_competing_database_creation_during_fetch_is_not_overwritten(tmp_path, monkeypatch, capsys):
    database = tmp_path / "new.sqlite3"

    def competing_capture(_):
        database.write_bytes(b"synthetic existing operator file")
        return _capture()

    monkeypatch.setattr(source, "download_calendar", competing_capture)
    monkeypatch.setattr(sys, "argv", ["scripts/inspect_nasdaq_calendar.py", "--database",
        str(database), "--artifact-root", str(tmp_path / "raw"), "--year", "2026", "--capture"])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path("scripts/inspect_nasdaq_calendar.py", run_name="__main__")
    assert stopped.value.code == 2
    assert "could not be reserved" in capsys.readouterr().err
    assert database.read_bytes() == b"synthetic existing operator file"
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("change", ["script", "long_label", "nested_table"])
def test_unsupported_table_markup_or_bounded_cell_cannot_be_admitted(change):
    old = b"Synthetic closure"
    if change == "script":
        new = b"Synthetic closure<script>synthetic</script>"
    elif change == "long_label":
        new = b"x" * 301
    else:
        new = b"Synthetic closure<table><tr><td>nested</td></tr></table>"
    assert source.calendar_declarations(_capture(BODY.replace(old, new)), 2026)["status"] == (
        "unsupported_calendar_layout")


@pytest.mark.parametrize("limit", [True, False, 0, -1, 1.5, "60"])
def test_invalid_source_age_rejected_before_database_access(limit):
    with pytest.raises(ValueError, match="positive integer"):
        read_nasdaq_calendar_inputs(None, None, 2026, as_of=AT,
                                   maximum_source_age_seconds=limit)


@pytest.mark.parametrize("microseconds,expected", [
    (0, "WITHIN_CONFIGURED_LIMIT"), (60_000_000, "WITHIN_CONFIGURED_LIMIT"),
    (60_000_001, "STALE"),
])
def test_source_age_exact_boundary_retains_observations_not_stale_inputs(
    foundation, microseconds, expected,
):
    _ingest(foundation)
    cutoff = AT + timedelta(microseconds=microseconds)
    before = foundation[0].path.read_bytes()
    original = _read(foundation, cutoff)
    result = _read(foundation, cutoff, maximum_source_age_seconds=60)
    assert result["freshness"] == expected
    assert result["source_capture_age_microseconds"] == microseconds
    assert result["source_capture_at"] == AT
    assert result["observed_declarations"] == original["declarations"]
    assert result["declarations"] == ([] if expected == "STALE" else original["declarations"])
    assert result["status"] == ("stale_source_capture" if expected == "STALE" else
                                 "explicit_declarations_unqualified")
    assert result["source_status"] == "explicit_declarations_unqualified"
    assert result["document_sha256"] == original["document_sha256"]
    assert result["captures"] == original["captures"]
    assert result["freshness_model_version"] == "nasdaq-calendar-source-age-v1"
    assert result["trust_ceiling"] == "LOW"
    assert result["availability_precision"] == "retrieval_time"
    for name in ("published_at_known", "calendar_complete", "actual_session_verified",
        "canonical_calendar_authorized", "scoring_authorized", "historical_replay_eligible",
        "validation_authorized", "execution_authorized"):
        assert result[name] is False
    assert original["freshness"] == "UNASSESSED"
    assert "source_capture_age_microseconds" not in original
    assert "observed_declarations" not in original
    assert foundation[0].path.read_bytes() == before


def test_source_age_missing_future_capture_is_blocked_not_zero_age(foundation):
    _ingest(foundation)
    result = _read(foundation, AT - timedelta(microseconds=1), maximum_source_age_seconds=60)
    assert result["status"] == "missing" and result["freshness"] == "BLOCKED_INPUT"
    assert result["source_capture_at"] is None
    assert result["source_capture_age_microseconds"] is None
    assert result["source_capture_age_seconds"] is None
    assert result["observed_declarations"] == result["declarations"] == []


def test_source_age_binds_hash_and_uses_original_capture_not_completion(foundation):
    _ingest(foundation, completed=AT + timedelta(seconds=20))
    cutoff = AT + timedelta(seconds=30)
    result = _read(foundation, cutoff, maximum_source_age_seconds=10)
    assert result["freshness"] == "STALE"
    assert result["source_capture_age_microseconds"] == 30_000_000
    assert result == _read(foundation, cutoff, maximum_source_age_seconds=10)
    other = _read(foundation, cutoff, maximum_source_age_seconds=31)
    assert other["input_hash"] != result["input_hash"]
    assert other["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert other["source_capture_at"] == AT
    huge = _read(foundation, cutoff, maximum_source_age_seconds=1 << 100)
    assert huge["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    digest = result.pop("input_hash")
    assert digest == sha256(financial_input_json(result).encode()).hexdigest()


def test_source_age_compares_actual_utc_across_repeated_dst_hour(foundation):
    ny = ZoneInfo("America/New_York")
    capture = datetime(2026, 11, 1, 1, 30, tzinfo=ny, fold=0)
    cutoff = capture.replace(fold=1)
    _ingest(foundation, at=capture.astimezone(UTC))
    result = _read(foundation, cutoff, maximum_source_age_seconds=3599)
    assert result["freshness"] == "STALE"
    assert result["source_capture_age_microseconds"] == 3600_000_000
    assert result == _read(foundation, cutoff.astimezone(UTC), maximum_source_age_seconds=3599)


def test_non_utc_capture_identity_limitation_cannot_be_mistaken_for_fresh_input(foundation):
    captured = AT.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    batch = source.NasdaqCalendarAdapter(download=lambda _: _capture(), clock=lambda: AT).fetch(
        _request())
    original = batch.records[0]
    record = replace(original, available_at=captured, retrieved_at=captured,
        evidence_id=source.provider_evidence_id(provider=original.provider,
            dataset=original.dataset, market=original.market, subject=original.subject,
            available_at=captured, source_reference=original.source_reference,
            payload=original.payload))
    legacy = replace(batch, retrieved_at=captured, records=(record,), artifacts=(replace(
        batch.artifacts[0], published_at=captured, retrieved_at=captured),))

    # Reproduce a previously persisted v1 record without bypassing the production guard.
    class LegacyFixtureAdapter:
        provider_id = source.PROVIDER

        def capabilities(self):
            return source.NasdaqCalendarAdapter().capabilities()

        def fetch(self, request):
            return legacy

    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[1],
        clock=lambda: AT).ingest(LegacyFixtureAdapter(), _request(captured))
    result = _read(foundation, AT, maximum_source_age_seconds=60)
    assert result["status"] == "rejected_or_ambiguous"
    assert result["freshness"] == "BLOCKED_INPUT"
    assert result["source_capture_at"] is None
    assert result["source_capture_age_microseconds"] is None
    assert result["declarations"] == [] and len(result["captures"]) == 1


@pytest.mark.parametrize("zone,fold", [("Asia/Kuala_Lumpur", 0),
    ("America/New_York", 0), ("America/New_York", 1)])
def test_non_utc_producer_clock_rejected_before_any_retention(foundation, zone, fold):
    captured = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo(zone), fold=fold)
    before = foundation[0].path.read_bytes()
    with pytest.raises(ValueError, match="capture clock must use UTC"):
        _ingest(foundation, at=captured)
    assert foundation[0].path.read_bytes() == before
    assert not foundation[1].root.exists()
    for table in ("ingestion_batches", "provider_artifacts", "provider_evidence_records",
                  "raw_dataset_fingerprints", "provider_limitations"):
        assert foundation[0].table_count(table) == 0


@pytest.mark.parametrize("zone", ["UTC", "Etc/GMT", "Europe/London"])
def test_equivalent_zero_offset_clocks_keep_existing_utc_receipt(foundation, zone):
    canonical = source.NasdaqCalendarAdapter(download=lambda _: _capture(), clock=lambda: AT).fetch(
        _request())
    labelled = AT.astimezone(ZoneInfo(zone))
    actual = source.NasdaqCalendarAdapter(download=lambda _: _capture(),
        clock=lambda: labelled).fetch(_request(labelled))
    assert actual == canonical
    _ingest(foundation, at=labelled)
    result = _read(foundation, maximum_source_age_seconds=60)
    assert result["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert result["source_capture_age_microseconds"] == 0
    assert result["scoring_authorized"] is False and result["execution_authorized"] is False


def test_new_capture_does_not_rejuvenate_historical_read_or_future_event_date(foundation):
    _ingest(foundation)
    _ingest(foundation, at=AT + timedelta(seconds=30))
    old = _read(foundation, AT + timedelta(seconds=29), maximum_source_age_seconds=10)
    current = _read(foundation, AT + timedelta(seconds=31), maximum_source_age_seconds=10)
    assert old["freshness"] == "STALE" and old["source_capture_at"] == AT
    assert current["freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert current["source_capture_at"] == AT + timedelta(seconds=30)
    assert current["source_capture_age_microseconds"] == 1_000_000
    assert current["declarations"][1]["trade_date"] == "2026-11-27"


def test_unsupported_rows_remain_observed_and_blocked_even_when_recent(foundation):
    _ingest(foundation, _capture(BODY.replace(b"Closed", b"Unrecognized status")))
    original = _read(foundation)
    result = _read(foundation, maximum_source_age_seconds=60)
    assert result["source_bound"] and result["source_capture_age_microseconds"] == 0
    assert result["freshness"] == "BLOCKED_INPUT"
    assert result["status"] == "unsupported_or_conflicting_declarations"
    assert result["observed_declarations"] == original["declarations"]
    assert result["declarations"] == []


@pytest.mark.parametrize("limit,mode", [("0", "--as-of"), ("-1", "--as-of"),
                                        ("60", "--capture")])
def test_cli_source_age_invalid_mode_or_limit_before_files_or_network(
    tmp_path, monkeypatch, capsys, limit, mode,
):
    database, artifacts = tmp_path / "absent.sqlite3", tmp_path / "raw"

    def no_network(*args):
        raise AssertionError("invalid source-age arguments attempted a capture")

    monkeypatch.setattr(source, "download_calendar", no_network)
    args = ["scripts/inspect_nasdaq_calendar.py", "--database", str(database),
        "--artifact-root", str(artifacts), "--year", "2026", "--max-source-age-seconds", limit,
        mode]
    if mode == "--as-of":
        args.append(AT.isoformat())
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(args[0], run_name="__main__")
    assert stopped.value.code == 2 and "read-only --as-of" in capsys.readouterr().err
    assert not database.exists() and not artifacts.exists()


def test_cli_source_age_is_offline_deterministic_and_read_only(foundation, monkeypatch, capsys):
    _ingest(foundation)
    store, artifacts = foundation
    before = store.path.read_bytes()
    cutoff = AT + timedelta(seconds=61)
    args = ["scripts/inspect_nasdaq_calendar.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--year", "2026", "--as-of", cutoff.isoformat(),
        "--max-source-age-seconds", "60"]

    def no_network(*args):
        raise AssertionError("read-only source-age check attempted network")

    monkeypatch.setattr(source, "download_calendar", no_network)
    monkeypatch.setattr(sys, "argv", args)
    outputs = []
    for _ in range(2):
        with pytest.raises(SystemExit) as stopped:
            runpy.run_path(args[0], run_name="__main__")
        assert stopped.value.code == 2
        outputs.append(json.loads(capsys.readouterr().out))
    assert outputs[0] == outputs[1] == json.loads(financial_input_json(
        _read(foundation, cutoff, maximum_source_age_seconds=60)))
    assert outputs[0]["freshness"] == "STALE"
    assert store.path.read_bytes() == before
