"""Offline academic presentation of existing observations, never a research decision."""

import subprocess
import tomllib
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from tong_quant.application.technical_binding import build_technical_binding
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs, read_global_price_inputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.governance import audit_project_governance
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters, sma
from tong_quant.research.technical.long_horizon import long_horizon_diagnostics
from tong_quant.version import ACADEMIC_SHOWCASE_VERSION, DATABASE_SCHEMA_VERSION, FRAMEWORK_VERSION


class _NoDTDTreeBuilder(ElementTree.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("unsupported test record DTD")


_AUTHORITY = ("source_qualified", "pit_qualified", "validation_authorized",
              "holding_management_authorized", "execution_authorized",
              "investment_scoring_authorized", "research_report_created")
_CHECKS = ("execution_mode", "allow_live_orders", "notification_mode", "framework_version",
           "database_schema_version", "migration_head", "ci_governance_check")


def read_test_record(path: Path) -> dict[str, Any]:
    """Summarize a local pytest JUnit record; never admit it as strategy evidence."""
    with path.open("rb") as handle:
        content = handle.read(2_000_001)
    if len(content) > 2_000_000 or any(x in content.upper() for x in (b"<!DOCTYPE", b"<!ENTITY")):
        raise ValueError("unsupported test record")
    try:
        root = ElementTree.fromstring(content,
            parser=ElementTree.XMLParser(target=_NoDTDTreeBuilder()))
    except ElementTree.ParseError:
        raise ValueError("invalid test record") from None
    if root.tag not in {"testsuites", "testsuite"}:
        raise ValueError("unsupported test record root")
    allowed = {
        "testsuites": {"testsuite"},
        "testsuite": {"testsuite", "testcase", "properties", "system-out", "system-err"},
        "testcase": {"skipped", "failure", "error", "properties", "system-out", "system-err"},
        "properties": {"property"},
    }
    for node in root.iter():
        if any(child.tag not in allowed.get(node.tag, set()) for child in node):
            raise ValueError("unsupported test record structure")
    cases = list(root.iter("testcase"))
    if not cases or len(cases) > 20_000:
        raise ValueError("test record requires bounded cases")
    identifiers = [(x.get("classname"), x.get("name")) for x in cases]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("test record contains duplicate cases")
    if any(sum(len(x.findall(tag)) for tag in ("skipped", "failure", "error")) > 1
           for x in cases):
        raise ValueError("test record contains conflicting outcomes")
    for suite in root.iter():
        if suite.tag not in {"testsuites", "testsuite"}:
            continue
        children = list(suite.iter("testcase"))
        outcomes = (("failures", "failure"), ("errors", "error"), ("skipped", "skipped"))
        counts = {"tests": len(children), **{
            field: sum(case.find(tag) is not None for case in children)
            for field, tag in outcomes}}
        for field, expected in counts.items():
            supplied = suite.get(field)
            if supplied is not None and (not supplied.isascii() or not supplied.isdigit()
                                         or int(supplied) != expected):
                raise ValueError("test record counters contradict cases")
    skipped = sum(x.find("skipped") is not None for x in cases)
    failed = sum(x.find("failure") is not None or x.find("error") is not None for x in cases)
    return {"status": "RECORDED_FAILURES" if failed else "RECORDED_NO_FAILURES",
            "tests": len(cases), "passed": len(cases) - skipped - failed,
            "skipped": skipped, "failed": failed, "record_sha256": sha256(content).hexdigest(),
            "basis": "LOCAL_JUNIT_RECORD_NOT_INDEPENDENT_STRATEGY_VALIDATION"}


def _averages(closes: list[float], periods: tuple[int, ...]) -> list[dict[str, Any]]:
    return [{"period": period, "values": sma(closes, period)} for period in periods]


def _period_view(source: dict[str, Any], periods: tuple[int, ...]) -> dict[str, Any]:
    usable = source["status"] == "OBSERVED_UNQUALIFIED"
    ended = [p for p in source["periods"] if p["calendar_period_ended"]] if usable else []
    rows = [{"date": p["period_start_date"], **p["ohlcv"]} for p in ended]
    closes = [float(p["close"]) for p in rows]
    return {"status": source["status"], "bars": rows,
            "averages": _averages(closes, periods),
            "macd": source["macd"]["values"], "kdj": source["kdj"]["values"],
            "macd_status": source["macd"]["status"], "kdj_status": source["kdj"]["status"],
            "available_periods": source["calculation_period_count"],
            "macd_required_periods": source["macd"]["required_periods"],
            "open_periods": source["open_period_starts"],
            "last_source_observed_at": (ended[-1]["last_observed_at"] if ended else None),
            "session_coverage": "UNVERIFIED"}


def build_academic_snapshot(snapshot: GlobalPriceInputs) -> dict[str, Any]:
    """Build display-only content from the existing checked reader and formulas."""
    if type(snapshot) is not GlobalPriceInputs:
        raise ValueError("academic snapshot requires typed source inputs")
    require_timezone(snapshot.as_of, "academic snapshot cutoff")
    validate_yahoo_equity_subject(snapshot.market, snapshot.subject)
    try:
        cutoff = snapshot.as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("academic cutoff outside UTC bounds") from None
    parameters = TechnicalParameters()
    eligible = snapshot.status == "observed_unqualified" and snapshot.freshness == "WITHIN_LIMIT"
    original = snapshot.bars
    if any(bar.instrument.symbol != snapshot.subject or bar.instrument.market is not snapshot.market
           for bar in original):
        raise ValueError("academic source subject or market mismatch")
    # Validate originals even when the snapshot is blocked; never restore an older good series.
    selected = checked_daily_bars(original, as_of=cutoff, require_latest_active=True)
    bars = selected if eligible else ()
    diagnostics = technical_diagnostics(original if eligible else (), parameters, as_of=cutoff)
    inputs = snapshot.document()
    binding = (build_technical_binding(snapshot, parameters,
               {"research_only": True, "research_report_created": False,
                "readiness_promoted": False, "inputs": inputs, "diagnostics": diagnostics})
               if eligible else None)
    periods = long_horizon_diagnostics(original if eligible else (),
                                      market=snapshot.market, as_of=cutoff,
                                      weekly_sma_periods=(13, 26, 52))
    daily = [{"date": bar.timestamp.astimezone(UTC).date().isoformat(),
              "open": str(bar.open), "high": str(bar.high), "low": str(bar.low),
              "close": str(bar.close), "volume": str(bar.volume)} for bar in bars]
    p = parameters
    daily_frame = {"status": diagnostics["technical_input_status"], "bars": daily,
        "averages": _averages([float(bar.close) for bar in bars], p.triple_periods),
        "macd": ({"dif": diagnostics["macd_dif"], "dea": diagnostics["macd_dea"],
                  "histogram": diagnostics["macd_histogram"]}
                 if diagnostics["macd_dif"] is not None else None),
        "kdj": ({"k": diagnostics["kdj_k"], "d": diagnostics["kdj_d"],
                 "j": diagnostics["kdj_j"]} if diagnostics["kdj_k"] is not None else None),
        "macd_status": ("OBSERVED_UNQUALIFIED" if diagnostics["macd_dif"] is not None
                        else "INSUFFICIENT_HISTORY"),
        "kdj_status": ("OBSERVED_UNQUALIFIED" if diagnostics["kdj_k"] is not None
                       else "INSUFFICIENT_HISTORY"),
        "available_periods": len(bars), "macd_required_periods": p.macd_slow + p.macd_signal,
        "open_periods": [], "session_coverage": "UNVERIFIED",
        "last_source_observed_at": bars[-1].timestamp if bars else None}
    evidence = [{key: row.get(key) for key in (
        "evidence_id", "raw_data_hash", "available_at", "status", "trust_level")}
        for row in snapshot.observations]
    result = {"model_version": ACADEMIC_SHOWCASE_VERSION, "subject": snapshot.subject,
        "market": snapshot.market.value, "as_of": cutoff,
        "currency": original[-1].instrument.currency if original else None,
        "exchange": original[-1].instrument.exchange if original else None,
        "source_status": snapshot.status, "freshness": snapshot.freshness,
        "observation_age_seconds": snapshot.observation_age_seconds,
        "maximum_age_seconds": snapshot.maximum_age_seconds,
        "supplied_row_count": len(original), "displayed_row_count": len(bars),
        "display_status": "OBSERVED_UNQUALIFIED" if bars else "BLOCKED_OR_UNAVAILABLE",
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "price_basis": "PROVIDER_NATIVE_UNVERIFIED", "parameters": asdict(parameters),
        "diagnostics": diagnostics, "technical_binding": binding,
        "price_input_hash": inputs["input_hash"], "bars_content_hash": inputs["bars_content_hash"],
        "period_input_hash": periods["input_hash"],
        "selected_evidence_id": snapshot.selected_evidence_id, "evidence": evidence,
        "timeframe_alignment": periods["timeframe_alignment"],
        "frames": {"daily": daily_frame, "weekly": _period_view(periods["weekly"], (13, 26, 52)),
                   "monthly": _period_view(periods["monthly"], (6, 12, 24)),
                   "yearly": _period_view(periods["yearly"], (3, 5, 10))},
        "framework_version": FRAMEWORK_VERSION, "database_schema_version": DATABASE_SCHEMA_VERSION,
        "research_only": True, "fundamental_assessment": "NOT_ASSESSED",
        "cross_timeframe_decision": "NOT_EVALUATED", "holding_horizon": "NOT_ESTIMATED",
        **{name: False for name in _AUTHORITY}}
    reject_sensitive_structure(result)
    return {**result, "snapshot_hash": sha256(financial_input_json(result).encode()).hexdigest()}


def read_academic_snapshot(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                           subject: str, market: Market, *, as_of: datetime,
                           maximum_age_seconds: int) -> dict[str, Any]:
    if not store.read_only:
        raise ValueError("academic export requires an existing read-only store")
    if type(maximum_age_seconds) is not int or maximum_age_seconds <= 0:
        raise ValueError("academic export requires an explicit positive age limit")
    require_timezone(as_of, "academic read cutoff")
    try:
        cutoff = as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("academic cutoff outside UTC bounds") from None
    return build_academic_snapshot(read_global_price_inputs(
        store, artifacts, subject, market, as_of=cutoff, maximum_age_seconds=maximum_age_seconds))


def academic_project_context(root: Path, test_record: Path | None = None) -> dict[str, Any]:
    audit = audit_project_governance(root)
    checks = {row.name: row for row in audit.checks}
    if not audit.is_consistent or any(
        name not in checks or not checks[name].passed
        for name in ("execution_mode", "allow_live_orders", "notification_mode")
    ):
        raise ValueError("academic project controls require consistent disabled defaults")
    governance = tomllib.loads((root / "config/project-governance.toml").read_text())
    try:
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"],
                                            text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    result = {"git_commit": head, "working_tree_dirty": dirty,
        "pit_readiness": governance["readiness"]["pit"],
        "production_readiness": governance["readiness"]["production"],
        "governance_consistent": audit.is_consistent,
        "governance_total": len(audit.checks),
        "governance_passed": sum(row.passed for row in audit.checks),
        "controls": [{"name": name, "passed": checks[name].passed if name in checks else None}
                     for name in _CHECKS],
        "test_record": read_test_record(test_record) if test_record else None}
    reject_sensitive_structure(result)
    return result


def render_academic_showcase(snapshot: dict[str, Any], context: dict[str, Any]) -> str:
    if (snapshot.get("model_version") != ACADEMIC_SHOWCASE_VERSION
            or any(snapshot.get(name) is not False for name in _AUTHORITY)):
        raise ValueError("academic presentation cannot admit research or trading authority")
    if context.get("governance_consistent") is not True:
        raise ValueError("academic project governance is not verified")
    body = {key: value for key, value in snapshot.items() if key != "snapshot_hash"}
    if sha256(financial_input_json(body).encode()).hexdigest() != snapshot.get("snapshot_hash"):
        raise ValueError("academic snapshot hash mismatch")
    payload = {"snapshot": snapshot, "project": context}
    reject_sensitive_structure(payload)
    encoded = financial_input_json(payload)
    for old, new in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                     ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        encoded = encoded.replace(old, new)
    resources = files("tong_quant.application")
    template = resources.joinpath("academic_showcase.html").read_text(encoding="utf-8")
    icons = resources.joinpath("academic_showcase_icons.json").read_text(encoding="utf-8")
    return template.replace("__ACADEMIC_PAYLOAD__", encoded).replace("__LUCIDE_ICONS__", icons)
