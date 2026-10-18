"""Synthetic bytes exercise evidence contracts; never provider-readiness evidence."""

import json
import runpy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import sse_calendar
from tong_quant.data.providers.contracts import (
    SSE_CALENDAR_DATASET,
    SSE_CALENDAR_PROVIDER,
    ProviderDatasetRequest,
)
from tong_quant.data.providers.sse_calendar import (
    SSECalendarNoticeAdapter,
    SSECalendarNoticeProfile,
    fetch_notice,
    require_notice_url,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import TradingSession
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config/markets/sse-calendar-notice-2026-09.toml"
NOW = datetime(2026, 10, 16, 5, tzinfo=UTC)
CONTENT = b"Synthetic reviewed notice bytes; not an exchange capture"
REQUEST = ProviderDatasetRequest(SSE_CALENDAR_DATASET, Market.CHINA_A, "SSE", NOW)


@pytest.fixture
def profile(tmp_path: Path) -> SSECalendarNoticeProfile:
    original = SSECalendarNoticeProfile.load(PROFILE_PATH)
    fixture_path = tmp_path / "profile.toml"
    fixture_path.write_text(
        PROFILE_PATH.read_text().replace(original.content_sha256, sha256(CONTENT).hexdigest())
    )
    return SSECalendarNoticeProfile.load(fixture_path)


def adapter(profile: SSECalendarNoticeProfile) -> SSECalendarNoticeAdapter:
    return SSECalendarNoticeAdapter(profile, fetch_bytes=lambda _: CONTENT, clock=lambda: NOW)


def service(tmp_path: Path) -> ProviderNeutralIngestionService:
    store = SQLiteStore(tmp_path / "notice.sqlite3")
    store.initialize()
    return ProviderNeutralIngestionService(
        store,
        clock=lambda: NOW,
        artifact_store=FileSystemArtifactStore(tmp_path / "artifacts"),
    )


def test_notice_contains_only_explicit_dates_and_never_backdates_availability(
    profile: SSECalendarNoticeProfile,
) -> None:
    batch = adapter(profile).fetch(REQUEST)
    dates = {row.payload["trade_date"]: row.payload["is_open"] for row in batch.records}
    assert len(dates) == 14
    assert sum(value is False for value in dates.values()) == 12
    assert dates["2026-10-10"] is False
    assert dates["2026-10-08"] is True
    assert "2026-10-11" not in dates
    assert "2026-10-09" not in dates  # Reopening is one explicit date, not an open-ended interval.
    assert all(row.available_at == NOW and row.published_at is None for row in batch.records)
    assert all(row.trust_level is DataTrustLevel.MEDIUM for row in batch.records)
    assert all(
        row.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME for row in batch.records
    )
    assert batch.artifacts[0].content == CONTENT
    assert batch.artifacts[0].published_at == NOW  # Conservative bound, not publication midnight.
    assert batch.artifact_observations[0].artifact_id == batch.artifacts[0].artifact_id


def test_neutral_ingestion_persists_raw_artifact_and_typed_pit_evidence_idempotently(
    tmp_path: Path,
    profile: SSECalendarNoticeProfile,
) -> None:
    ingestion = service(tmp_path)
    data = MarketDataService(ingestion.store)
    kwargs = dict(
        provider=SSE_CALENDAR_PROVIDER,
        dataset=SSE_CALENDAR_DATASET,
        market=Market.CHINA_A,
        subject="SSE",
    )
    first = ingestion.ingest(adapter(profile), REQUEST)
    second = ingestion.ingest(adapter(profile), REQUEST)
    assert (first.accepted, second.accepted) == (14, 14)
    assert ingestion.store.table_count("provider_evidence_records") == 14
    assert ingestion.store.table_count("provider_artifacts") == 1
    assert ingestion.store.table_count("provider_artifact_observations") == 1
    assert ingestion.store.table_count("trading_calendar") == 0
    assert data.provider_evidence(**kwargs, as_of=NOW - timedelta(microseconds=1)) == ()
    rows = data.provider_evidence(**kwargs, as_of=NOW)
    assert len(rows) == 14 and rows[0].raw_data_hash == sha256(CONTENT).hexdigest()
    history = ingestion.store.provider_artifact_history(
        provider=SSE_CALENDAR_PROVIDER, dataset=SSE_CALENDAR_DATASET, subject="SSE"
    )
    assert (tmp_path / "artifacts" / history[0]["storage_key"]).read_bytes() == CONTENT
    assert "complete trading calendar" in rows[0].limitations[-1]


def test_future_capture_is_rejected_before_artifact_or_audit_writes(
    tmp_path: Path,
    profile: SSECalendarNoticeProfile,
) -> None:
    ingestion = service(tmp_path)
    with pytest.raises(ValueError, match="future event data"):
        ingestion.ingest(adapter(profile), replace(REQUEST, as_of=NOW - timedelta(seconds=1)))
    assert ingestion.store.table_count("ingestion_batches") == 0
    assert ingestion.store.table_count("provider_evidence_records") == 0
    assert not (tmp_path / "artifacts").exists()


def test_changed_source_bytes_are_not_silently_reparsed(profile: SSECalendarNoticeProfile) -> None:
    changed = SSECalendarNoticeAdapter(profile, fetch_bytes=lambda _: b"changed", clock=lambda: NOW)
    with pytest.raises(ValueError, match="changed; source review"):
        changed.fetch(REQUEST)


@pytest.mark.parametrize("when", (NOW - timedelta(days=1), NOW + timedelta(days=31)))
def test_not_yet_reviewed_or_expired_profile_is_rejected_before_network(
    profile: SSECalendarNoticeProfile,
    when: datetime,
) -> None:
    def unexpected_fetch(url: str) -> bytes:
        raise AssertionError("must not fetch outside review window")

    with pytest.raises(ValueError, match="review is not current"):
        SSECalendarNoticeAdapter(profile, unexpected_fetch, lambda: when).fetch(REQUEST)


@pytest.mark.parametrize(
    "changes",
    (
        {"subject": "SZSE"},
        {"market": Market.US},
        {"parameters": {"infer_weekends": "true"}},
    ),
)
def test_request_cannot_broaden_exchange_scope(
    profile: SSECalendarNoticeProfile,
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="explicit SSE"):
        adapter(profile).fetch(replace(REQUEST, **changes))


@pytest.mark.parametrize(
    "url",
    (
        "http://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml",
        "https://www.sse.com.cn.evil.test/disclosure/announcement/general/c/c_20260915_10832273.shtml",
        "https://user:pass@www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml",
        "https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml?token=x",
        "https://www.sse.com.cn/disclosure/announcement/general/c/c_%2e%2e%2f.shtml",
    ),
)
def test_notice_transport_rejects_unapproved_urls(url: str) -> None:
    with pytest.raises(ValueError, match="official SSE notice URL"):
        require_notice_url(url)


@pytest.mark.parametrize(
    "old,new",
    (
        ("open_dates = [2026-09-28, 2026-10-08]", "open_dates = [2026-10-01]"),
        ("[2026-10-01, 2026-10-07]", "[2026-10-07, 2026-10-01]"),
        ("year = 2026", "year = 2027"),
    ),
)
def test_conflicting_or_invalid_reviewed_assertions_are_rejected(
    tmp_path: Path,
    old: str,
    new: str,
) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(PROFILE_PATH.read_text().replace(old, new))
    with pytest.raises(ValueError):
        SSECalendarNoticeProfile.load(path)


def test_runtime_inventory_retains_official_notice_without_overriding_calendar(
    tmp_path: Path,
    profile: SSECalendarNoticeProfile,
) -> None:
    ingestion = service(tmp_path)
    ingestion.ingest(adapter(profile), REQUEST)
    ingestion.store.upsert_trading_sessions(
        (TradingSession(Market.CHINA_A, date(2026, 10, 8), False, NOW, "conflicting_fixture"),)
    )
    reader = SSERuntimeInputReader(MarketDataService(ingestion.store))
    query = MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 10, 16), NOW)
    snapshot = reader.read("600000", query, calendar_start=date(2026, 10, 1))
    assert len(snapshot.calendar_notices) == 9
    assert snapshot.sessions[0].is_open is False
    assert date(2026, 10, 11) in snapshot.missing_calendar_dates
    assert {
        "calendar_notice_conflict",
        "calendar_notice_not_authoritative",
        "calendar_provenance_unavailable",
        "calendar_incomplete",
    } <= {item.code for item in snapshot.gaps}
    assert (
        snapshot.input_hash
        == reader.read("600000", query, calendar_start=date(2026, 10, 1)).input_hash
    )


def test_expired_notice_is_preserved_with_a_freshness_warning(
    tmp_path: Path,
    profile: SSECalendarNoticeProfile,
) -> None:
    ingestion = service(tmp_path)
    ingestion.ingest(adapter(profile), REQUEST)
    snapshot = SSERuntimeInputReader(MarketDataService(ingestion.store)).read(
        "600000",
        MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 11, 16), datetime(2026, 11, 16, 5, tzinfo=UTC)),
        calendar_start=date(2026, 10, 1),
    )
    assert len(snapshot.calendar_notices) == 9
    assert "calendar_notice_review_expired" in {gap.code for gap in snapshot.gaps}


def test_malformed_notice_remains_visible_and_cannot_clear_a_gap(
    tmp_path: Path,
    profile: SSECalendarNoticeProfile,
) -> None:
    ingestion = service(tmp_path)
    result = ingestion.ingest(adapter(profile), REQUEST)
    record = adapter(profile).fetch(REQUEST).records[0]
    invalid = replace(
        record,
        evidence_id=sha256(b"malformed fixture").hexdigest(),
        payload={**record.payload, "is_open": "false"},
    )
    assert result.batch_id is not None
    ingestion.store.save_provider_evidence_records((invalid,), batch_id=result.batch_id)
    snapshot = SSERuntimeInputReader(MarketDataService(ingestion.store)).read(
        "600000",
        MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 10, 16), NOW),
        calendar_start=date(2026, 10, 1),
    )
    assert invalid in snapshot.calendar_notices
    assert {"calendar_notice_invalid", "calendar_incomplete"} <= {gap.code for gap in snapshot.gaps}


def test_cli_source_failure_does_not_create_database_or_leak_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = runpy.run_path(str(ROOT / "scripts/ingest_data.py"))

    def fail_fetch(*args: object) -> bytes:
        raise ValueError("untrusted upstream response must not be printed")

    monkeypatch.setattr(sse_calendar.SSECalendarNoticeAdapter, "fetch", fail_fetch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest_data.py",
            "--worker",
            "--database",
            str(tmp_path / "absent.sqlite3"),
            "sse-calendar-notice",
        ],
    )
    assert script["main"]() == 2
    assert json.loads(capsys.readouterr().out) == {"status": "failed", "error_type": "ValueError"}
    assert not (tmp_path / "absent.sqlite3").exists()


def test_transport_never_follows_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 302

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def get(url: str, **kwargs: object) -> Response:
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (5, 20)
        return Response()

    monkeypatch.setattr(sse_calendar.requests, "get", get)
    with pytest.raises(ValueError, match="redirected"):
        fetch_notice(SSECalendarNoticeProfile.load(PROFILE_PATH).source_url)
