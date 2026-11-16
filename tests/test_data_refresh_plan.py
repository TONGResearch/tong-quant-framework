import json
import runpy
import socket
import sqlite3
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.providers import yahoo_fundamentals, yahoo_snapshot
from tong_quant.data.refresh_plan import (
    MAX_CONFIG_BYTES,
    MAX_SCOPES,
    RefreshScope,
    RefreshWatchlist,
    akshare_daily_refresh_request,
    build_refresh_plan,
    parse_refresh_watchlist,
)
from tong_quant.domain.enums import Adjustment, AssetType, Market

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "config/refresh/example-watchlist.toml"
SCRIPT = ROOT / "scripts/plan_data_refresh.py"
CUTOFF = datetime(2026, 11, 3, 5, tzinfo=UTC)
COMMIT = "1" * 40


def plan(watchlist: RefreshWatchlist | None = None, **kwargs: object) -> dict[str, object]:
    return build_refresh_plan(watchlist or parse_refresh_watchlist(SAMPLE.read_text()),
                              **{"planned_as_of": CUTOFF, "git_commit": COMMIT,
                                 "git_dirty": True, **kwargs})


def test_four_market_scopes_remain_visible_without_provider_or_readiness_approval() -> None:
    result = plan()
    entries = result["entries"]
    assert len(entries) == 5
    assert {entry["scope"]["market"] for entry in entries} == set(Market)
    china = next(entry for entry in entries if entry["scope"]["market"] == Market.CHINA_A)
    assert china["request_contract_status"] == "REQUEST_SCOPE_VALIDATED"
    assert china["request_contract"] == "DailyBarRequest"
    assert china["request_parameters"]["adjustment"] == Adjustment.NONE
    assert china["request_parameters"]["start_date"] == "20260101"
    assert china["reason_code"] == "static_legacy_contract_only"
    assert sum(entry["request_contract_status"] == "REQUEST_SCOPE_VALIDATED"
               for entry in entries) == 5
    for entry in entries:
        assert entry["provider_permission"] == "NOT_TESTED"
        assert entry["data_availability"] == entry["data_trust_level"] == "UNKNOWN"
        assert entry["calendar_status"] == entry["availability_precision"] == "UNKNOWN"
        assert not entry["closed_bar_qualified"]
    assert not any(result[key] for key in (
        "collection_authorized", "schedule_enabled", "research_refresh_authorized"))


def test_canonical_scope_order_and_equivalent_utc_instants_are_deterministic() -> None:
    watchlist = parse_refresh_watchlist(SAMPLE.read_text())
    result = plan(watchlist)
    reordered = replace(watchlist, scopes=tuple(reversed(watchlist.scopes)))
    assert result == plan(reordered, planned_as_of=CUTOFF.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur")))
    payload = {key: value for key, value in result.items() if key != "plan_hash"}
    assert result["plan_hash"] == sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize("change", ["cutoff", "git", "dirty", "version", "window"])
def test_material_context_changes_change_plan_hash(change: str) -> None:
    watchlist = parse_refresh_watchlist(SAMPLE.read_text())
    kwargs = {}
    if change == "cutoff":
        kwargs["planned_as_of"] = CUTOFF.replace(hour=6)
    elif change == "git":
        kwargs["git_commit"] = "2" * 40
    elif change == "dirty":
        kwargs["git_dirty"] = False
    elif change == "version":
        watchlist = replace(watchlist, version="changed-v2")
    else:
        watchlist = replace(watchlist, scopes=(
            replace(watchlist.scopes[0], start_date="2026-01-02"), *watchlist.scopes[1:]))
    assert plan(watchlist, **kwargs)["plan_hash"] != plan()["plan_hash"]


def test_dst_fold_is_an_actual_instant_not_a_wall_clock_hash() -> None:
    watchlist = parse_refresh_watchlist(SAMPLE.read_text())
    watchlist = replace(watchlist, scopes=tuple(
        replace(scope, end_date="2026-10-30") for scope in watchlist.scopes))
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    assert plan(watchlist, planned_as_of=first)["plan_hash"] != plan(
        watchlist, planned_as_of=first.replace(fold=1))["plan_hash"]


@pytest.mark.parametrize("replacement", [
    ('version = "four-market-example-v1"', 'version = true'),
    ('version = "four-market-example-v1"', 'version = "x"\ntoken = "private-fixture"'),
    ('subject = "MSFT"', 'subject = "secret=private-fixture"'),
    ('subject = "MSFT"', 'subject = 123'),
    ('subject = "MSFT"', 'subject = "0700.HK"'),
    ('subject = "MSFT"', 'subject = "https://example.invalid"'),
    ('market = "us"', 'market = "other"'),
    ('timezone = "America/New_York"', 'timezone = "UTC"'),
    ('start_date = "2026-01-01"', 'start_date = "20260101"'),
    ('start_date = "2026-01-01"', 'start_date = "2026-13-01"'),
    ('start_date = "2026-01-01"', 'start_date = "1900-01-01"'),
    ('start_date = "2026-01-01"', 'start_date = "2027-01-01"'),
    ('currency = "USD"', 'currency = "usd"'),
])
def test_invalid_config_or_supported_request_is_rejected(replacement: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        plan(parse_refresh_watchlist(SAMPLE.read_text().replace(*replacement)))


@pytest.mark.parametrize("key", ["token", "api_key", "secret", "password", "webhook_url"])
def test_sensitive_fields_reject_before_rendering(key: str) -> None:
    with pytest.raises(ValueError):
        parse_refresh_watchlist(SAMPLE.read_text() + f'\n{key} = "private-fixture"\n')


def test_bounds_duplicates_and_unknown_fields_reject() -> None:
    sample = parse_refresh_watchlist(SAMPLE.read_text())
    for scopes in ((), sample.scopes * MAX_SCOPES, (sample.scopes[0], sample.scopes[0]),
                   (sample.scopes[0], replace(sample.scopes[0], end_date="2026-10-01"))):
        with pytest.raises(ValueError):
            RefreshWatchlist("v1", scopes)
    with pytest.raises(ValueError):
        parse_refresh_watchlist("#" * (MAX_CONFIG_BYTES + 1))
    with pytest.raises(ValueError):
        parse_refresh_watchlist(SAMPLE.read_text().replace(
            'provider = "akshare"', 'unexpected = "field"'))


@pytest.mark.parametrize("kwargs", [
    {"git_dirty": 1}, {"git_commit": "unknown"}, {"planned_as_of": CUTOFF.replace(tzinfo=None)},
    {"planned_as_of": CUTOFF.replace(day=1)},
])
def test_unknown_provenance_or_future_windows_fail_closed(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        plan(**kwargs)


def test_market_local_date_not_utc_date_and_current_day_is_not_closed() -> None:
    scope = RefreshScope("yahoo_finance", "global_equity_price_snapshot", Market.US,
        "MSFT", "USD", "NMS", "America/New_York", "2026-11-02", "2026-11-02")
    watchlist = RefreshWatchlist("v1", (scope,))
    with pytest.raises(ValueError):
        plan(watchlist, planned_as_of=datetime(2026, 11, 2, 1, tzinfo=UTC))
    result = plan(watchlist, planned_as_of=datetime(2026, 11, 2, 19, tzinfo=UTC))
    assert result["entries"][0]["closed_bar_qualified"] is False


def test_unknown_provider_or_dataset_is_retained_not_replaced() -> None:
    sample = parse_refresh_watchlist(SAMPLE.read_text())
    for change in ({"provider": "unknown_provider"}, {"dataset": "new_dataset"}):
        watchlist = replace(sample, scopes=(replace(sample.scopes[1], **change),))
        entry = plan(watchlist)["entries"][0]
        assert entry["request_contract_status"] == "UNSUPPORTED"
        assert entry["scope"] == {**asdict(sample.scopes[1]), **change}


@pytest.mark.parametrize("market", [Market.US, Market.HONG_KONG, Market.MALAYSIA])
def test_native_annual_requests_share_existing_three_market_validator(market: Market) -> None:
    sample = parse_refresh_watchlist(SAMPLE.read_text())
    scope = next(scope for scope in sample.scopes if scope.market == market)
    entry = plan(RefreshWatchlist("native-v1", (replace(
        scope, dataset="global_native_fundamental_snapshot"),)))["entries"][0]
    assert entry["request_contract_status"] == "REQUEST_SCOPE_VALIDATED"
    assert set(entry["request_parameters"]) == {"start_date", "end_date"}
    assert entry["provider_permission"] == "NOT_TESTED"


def test_no_network_database_provider_fetch_or_subprocess_in_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("offline planner crossed an I/O boundary")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(yahoo_snapshot, "download_snapshot", forbidden)
    monkeypatch.setattr(yahoo_fundamentals, "download_fundamentals", forbidden)
    assert plan()["plan_hash"]


@pytest.mark.parametrize("symbol,exchange", [
    ("000063", "SZSE"), ("002624", "SZSE"), ("301001", "SZSE"),
    ("600109", "SSE"), ("688363", "SSE"), ("920982", "BSE"),
    ("430047", "BSE"), ("830001", "BSE"),
])
def test_akshare_request_conversion_is_explicit_unadjusted_equity_only(
    symbol: str, exchange: str,
) -> None:
    scope = replace(parse_refresh_watchlist(SAMPLE.read_text()).scopes[0],
                    subject=symbol, exchange=exchange)
    request = akshare_daily_refresh_request(scope)
    assert request.symbol == symbol
    assert request.market is Market.CHINA_A and request.asset_type is AssetType.EQUITY
    assert request.adjustment is Adjustment.NONE
    assert (request.start_date, request.end_date) == ("20260101", "20261102")
    entry = plan(RefreshWatchlist("a-v1", (scope,)))["entries"][0]
    assert set(entry["provider_contract_versions"]) == {"fetch", "routing", "normalization"}
    assert "endpoint" not in entry["request_parameters"]
    assert entry["provider_permission"] == "NOT_TESTED"
    assert not entry["closed_bar_qualified"]


@pytest.mark.parametrize("change", [
    {"currency": "USD"}, {"exchange": "SSE"}, {"provider": "other"},
    {"dataset": "index_daily"}, {"subject": "900901"}, {"subject": "510300"},
    {"subject": "00700"}, {"subject": "600109.SS"},
])
def test_legacy_request_factory_rejects_incompatible_scopes(change: dict[str, str]) -> None:
    scope = replace(parse_refresh_watchlist(SAMPLE.read_text()).scopes[0], **change)
    with pytest.raises(ValueError):
        akshare_daily_refresh_request(scope)


@pytest.mark.parametrize("symbol", ["900901", "510300", "700000", "00700", "600109.SS"])
def test_unrecognized_akshare_scope_is_retained_without_implied_equity_coverage(
    symbol: str,
) -> None:
    scope = replace(parse_refresh_watchlist(SAMPLE.read_text()).scopes[0], subject=symbol)
    entry = plan(RefreshWatchlist("unrecognized-v1", (scope,)))["entries"][0]
    assert entry["scope"]["subject"] == symbol
    assert entry["request_contract_status"] == "UNSUPPORTED"
    assert entry["reason_code"] == "akshare_equity_route_unrecognized"
    assert entry["request_parameters"] is None
    assert entry["request_contract"] is None


@pytest.mark.parametrize("dataset", ["index_daily", "financial_statement_snapshot"])
def test_unimplemented_akshare_datasets_remain_visible(dataset: str) -> None:
    scope = replace(parse_refresh_watchlist(SAMPLE.read_text()).scopes[0], dataset=dataset)
    entry = plan(RefreshWatchlist("unsupported-v1", (scope,)))["entries"][0]
    assert entry["scope"]["dataset"] == dataset
    assert entry["request_contract_status"] == "UNSUPPORTED"
    assert entry["request_parameters"] is None


def test_cli_reads_only_explicit_file_and_git_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path,
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    config = tmp_path / "watchlist.toml"
    config.write_text(SAMPLE.read_text())
    before = config.read_bytes()
    calls = []

    def git(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(command)
        assert kwargs["timeout"] == 5 and kwargs["check"]
        if command == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, COMMIT + "\n")
        assert command == ["git", "--no-optional-locks", "status", "--porcelain",
                           "--untracked-files=all"]
        return subprocess.CompletedProcess(command, 0, b" M existing.py\n")

    monkeypatch.setattr(subprocess, "run", git)
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network attempted"))
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: pytest.fail("database attempted"))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--watchlist", str(config),
                                     "--as-of", CUTOFF.isoformat()])
    namespace["main"]()
    assert json.loads(capsys.readouterr().out) == plan()
    assert len(calls) == 2 and config.read_bytes() == before
    assert list(tmp_path.iterdir()) == [config]


@pytest.mark.parametrize("bad", ["secret", "oversize", "symlink", "missing", "git_error"])
def test_cli_rejects_safely_without_traceback_or_config_echo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, bad: str,
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    config = tmp_path / "watchlist.toml"
    if bad == "secret":
        config.write_text('token = "private-fixture"')
    elif bad == "oversize":
        config.write_text("#" * (MAX_CONFIG_BYTES + 1))
    elif bad == "symlink":
        config.symlink_to(SAMPLE)
    elif bad == "git_error":
        config.write_text(SAMPLE.read_text())

    def fail(*args: object, **kwargs: object) -> None:
        if bad != "git_error":
            pytest.fail("Git called before input validation")
        raise subprocess.TimeoutExpired("git", 5, stderr="private-fixture")

    monkeypatch.setattr(subprocess, "run", fail)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--watchlist", str(config),
                                     "--as-of", CUTOFF.isoformat()])
    with pytest.raises(SystemExit) as error:
        namespace["main"]()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "no data collected" in output.err
    assert "private-fixture" not in output.err and "Traceback" not in output.err


@pytest.mark.parametrize("flag", ["--execute", "--capture", "--token"])
def test_cli_has_no_collection_or_credential_arguments(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], flag: str,
) -> None:
    namespace = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--watchlist", str(SAMPLE),
        "--as-of", CUTOFF.isoformat(), flag, "private-fixture"])
    with pytest.raises(SystemExit) as error:
        namespace["main"]()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "private-fixture" not in output.err
