"""Synthetic calendar assertions verify contracts, not actual exchange operations."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.application.sse_calendar_plan import SSECalendarPlanBuilder
from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calendar_evidence import SSECalendarNoticeProfile
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import SSE_CALENDAR_DATASET, ProviderDatasetRequest
from tong_quant.data.providers.sse_calendar import SSECalendarNoticeAdapter
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import DataTrustLevel, Market
from tong_quant.domain.models import TradingSession
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import (
    SSE_PILOT_SCOPE,
    SSE_PROFILE_VERSION,
    ReviewedRuleDocument,
    SSEReferenceBundle,
)

ROOT = Path(__file__).resolve().parents[1]
YEAR_PROFILE = ROOT / "config/markets/sse-calendar-notice-2026-year.toml"
NOW = datetime(2026, 10, 16, 6, tzinfo=UTC)
CONTENT = b"Synthetic annual holiday fixture; not real exchange evidence"
START, END = date(2026, 10, 1), date(2026, 10, 16)


@pytest.fixture
def foundation(tmp_path: Path):
    source = SSECalendarNoticeProfile.load(YEAR_PROFILE)
    path = tmp_path / "year.toml"
    path.write_text(
        YEAR_PROFILE.read_text().replace(source.content_sha256, sha256(CONTENT).hexdigest())
    )
    profile = SSECalendarNoticeProfile.load(path)
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    store = SQLiteStore(tmp_path / "calendar.sqlite3")
    store.initialize()
    ProviderNeutralIngestionService(store, clock=lambda: NOW, artifact_store=artifacts).ingest(
        SSECalendarNoticeAdapter(profile, fetch_bytes=lambda _: CONTENT, clock=lambda: NOW),
        ProviderDatasetRequest(SSE_CALENDAR_DATASET, Market.CHINA_A, "SSE", NOW),
    )
    notices = MarketDataService(store).provider_evidence(
        provider="sse_calendar_notice",
        dataset=SSE_CALENDAR_DATASET,
        market=Market.CHINA_A,
        subject="SSE",
        as_of=NOW,
    )
    references = SSEReferenceBundle(
        SSE_PROFILE_VERSION,
        date(2026, 7, 6),
        NOW - timedelta(days=1),
        NOW + timedelta(days=20),
        tuple(
            ReviewedRuleDocument(role, f"https://www.sse.com.cn/lawandrules/test/{role}", "a" * 64)
            for role in ("rules", "deferred", "odd_lots")
        ),
        "b" * 64,
        DataTrustLevel.HIGH,
    )
    return SSECalendarPlanBuilder(references, profile, artifacts), notices, store


def build(builder, notices, **kwargs):
    return builder.build(notices, start=START, end=END, as_of=NOW, **kwargs)


def test_ordinary_schedule_covers_dates_without_claiming_actual_open_or_settlement(
    foundation,
) -> None:
    builder, notices, store = foundation
    assert len(notices) == 46
    plan = build(builder, notices)
    assert len(plan.days) == 16 and plan.missing_dates == ()
    by_date = {day.trade_date: day for day in plan.days}
    assert by_date[date(2026, 10, 11)].is_open is False
    assert by_date[date(2026, 10, 11)].basis == "reviewed_weekly_rule"
    assert by_date[date(2026, 10, 8)].is_open is True
    assert by_date[date(2026, 10, 8)].basis == "explicit_annual_notice"
    assert sum(day.is_open is True for day in plan.days) == 7
    assert plan.trust_level is DataTrustLevel.MEDIUM
    assert plan.available_at == NOW
    assert "exceptional_closure_coverage_unverified" in plan.warnings
    assert "settlement_and_security_status_not_inferred" in plan.warnings
    assert store.table_count("trading_calendar") == 0
    assert plan.plan_hash == build(builder, tuple(reversed(notices))).plan_hash


def test_missing_any_annual_claim_prevents_favorable_inference_even_outside_query_window(
    foundation,
) -> None:
    builder, notices, _ = foundation
    assert notices[0].payload["trade_date"] not in {day.isoformat() for day in (START, END)}
    plan = build(builder, notices[1:])
    assert len(plan.missing_dates) == 16
    assert "annual_notice_evidence_incomplete" in plan.warnings
    assert plan.trust_level is DataTrustLevel.UNKNOWN


@pytest.mark.parametrize(
    "field", ("artifact_id", "raw_hash", "trust", "boolean", "scope", "exchange")
)
def test_invalid_or_weak_evidence_cannot_create_planned_sessions(foundation, field: str) -> None:
    builder, notices, _ = foundation
    record = notices[0]
    if field == "artifact_id":
        record = replace(record, payload={**record.payload, "artifact_id": "f" * 64})
    elif field == "raw_hash":
        record = replace(record, raw_data_hash="f" * 64)
    elif field == "trust":
        record = replace(record, trust_level=DataTrustLevel.LOW)
    elif field == "boolean":
        record = replace(record, payload={**record.payload, "is_open": "false"})
    elif field == "exchange":
        record = replace(record, payload={**record.payload, "exchange": "SZSE"})
    else:
        record = replace(record, subject="SZSE")
    plan = build(builder, (record, *notices[1:]))
    assert len(plan.missing_dates) == 16
    assert "annual_notice_evidence_invalid" in plan.warnings


def test_future_notice_and_future_review_are_rejected(foundation) -> None:
    builder, notices, _ = foundation
    future = replace(
        notices[0], available_at=NOW + timedelta(seconds=1), retrieved_at=NOW + timedelta(seconds=1)
    )
    with pytest.raises(ValueError, match="future notice"):
        build(builder, (future, *notices[1:]))
    with pytest.raises(ValueError, match="sources are not visible"):
        build(
            replace(
                builder,
                references=replace(builder.references, available_at=NOW + timedelta(seconds=1)),
            ),
            notices,
        )


def test_review_expiry_is_unknown_not_a_current_calendar(foundation) -> None:
    builder, notices, _ = foundation
    expired = replace(builder.references, review_expires_at=NOW - timedelta(seconds=1))
    plan = build(replace(builder, references=expired), notices)
    assert len(plan.missing_dates) == 16
    assert "calendar_source_review_expired" in plan.warnings


def test_unreviewed_rule_period_is_not_backfilled_from_current_rules(foundation) -> None:
    builder, notices, _ = foundation
    plan = builder.build(notices, start=date(2026, 7, 5), end=date(2026, 7, 7), as_of=NOW)
    assert plan.missing_dates == (date(2026, 7, 5),)
    assert plan.days[0].basis == "outside_reviewed_rule_period"
    beyond = builder.build(notices, start=date(2026, 12, 31), end=date(2027, 1, 1), as_of=NOW)
    assert beyond.missing_dates == (date(2027, 1, 1),)


@pytest.mark.parametrize("tamper", (True, False))
def test_missing_or_tampered_raw_notice_cannot_build_a_complete_plan(
    foundation, tamper: bool
) -> None:
    builder, notices, _ = foundation
    path = next(builder.artifacts.root.rglob("*.bin"))
    if tamper:
        path.write_bytes(b"changed")
    else:
        path.unlink()
    plan = build(builder, notices)
    assert len(plan.missing_dates) == 16
    assert "annual_notice_artifact_unverified" in plan.warnings


def test_later_conflict_is_preserved_and_does_not_select_the_more_favorable_notice(
    foundation,
) -> None:
    builder, notices, _ = foundation
    conflict = replace(
        notices[0],
        evidence_id="c" * 64,
        available_at=NOW + timedelta(minutes=1),
        retrieved_at=NOW + timedelta(minutes=1),
        payload={"trade_date": "2026-10-09", "exchange": "SSE", "is_open": False},
    )
    plan = builder.build(
        (*notices, conflict), start=START, end=END, as_of=NOW + timedelta(minutes=2)
    )
    assert plan.missing_dates == (date(2026, 10, 9),)
    assert conflict in plan.notice_evidence
    assert plan.available_at == conflict.available_at
    assert "calendar_notice_conflict" in plan.warnings


def test_runtime_keeps_raw_and_planned_calendars_separate_in_one_snapshot(foundation) -> None:
    builder, _, store = foundation
    store.upsert_trading_sessions(
        (TradingSession(Market.CHINA_A, date(2026, 10, 11), True, NOW, "conflicting fixture"),)
    )
    snapshot = SSERuntimeInputReader(MarketDataService(store), calendar_builder=builder).read(
        "600000",
        MarketRuleQuery(SSE_PILOT_SCOPE, END, NOW),
        calendar_start=START,
    )
    assert snapshot.calendar_plan.missing_dates == ()
    assert snapshot.to_record()["calendar_plan_hash"] == snapshot.calendar_plan.plan_hash
    assert snapshot.to_record()["calendar_plan_missing_dates"] == ()
    assert snapshot.sessions[0].is_open is True
    assert len(snapshot.missing_calendar_dates) == 15
    assert {
        "calendar_plan_raw_conflict",
        "calendar_plan_not_authoritative",
        "calendar_incomplete",
    } <= {gap.code for gap in snapshot.gaps}
    assert store.table_count("trading_calendar") == 1


def test_partial_notice_is_not_an_annual_calendar(foundation) -> None:
    builder, notices, _ = foundation
    with pytest.raises(ValueError, match="annual holiday"):
        build(
            replace(
                builder, annual_notice=replace(builder.annual_notice, notice_scope="partial_notice")
            ),
            notices,
        )


def test_artifact_reader_bounds_content_and_rejects_symlink_escape(tmp_path: Path) -> None:
    content = b"synthetic"
    digest = sha256(content).hexdigest()
    root = tmp_path / "store"
    path = root / "sha256" / digest[:2] / f"{digest}.bin"
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    store = FileSystemArtifactStore(root)
    assert store.read_content(digest, "text/html", max_bytes=20) == content
    with pytest.raises(ValueError, match="size or content-hash"):
        store.read_content(digest, "text/html", max_bytes=1)
    with pytest.raises(ValueError, match="SHA-256"):
        store.read_content("../escape", "text/html", max_bytes=20)
    path.unlink()
    external = tmp_path / "outside"
    external.write_bytes(content)
    path.symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        store.read_content(digest, "text/html", max_bytes=20)
