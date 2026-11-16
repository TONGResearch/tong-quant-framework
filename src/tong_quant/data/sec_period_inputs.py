"""Exact SEC context selections, not annualization, accounting aliases or financial scores."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.sec_body import DATASET, body_subject, validate_request
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.sec_body_inputs import read_sec_body_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    SEC_INLINE_REVIEW_VERSION,
    SEC_PERIOD_INPUT_VERSION,
    SEC_PERIOD_RESEARCH_INPUT_VERSION,
)

_SECTORS = frozenset({"nonfinancial", "bank", "securities", "insurance", "unknown"})


@dataclass(frozen=True, slots=True)
class SECPeriodSelection:
    native_tag: str
    period_start: date | None
    period_end: date

    def __post_init__(self) -> None:
        if (not isinstance(self.native_tag, str) or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.-]{0,127}", self.native_tag, flags=re.ASCII) is None
                or type(self.period_end) is not date
                or self.period_start is not None and (type(self.period_start) is not date
                    or self.period_start > self.period_end)):
            raise ValueError("SEC period selection requires a native tag and exact ordered dates")


def _ordered(selections: tuple[SECPeriodSelection, ...]) -> tuple[SECPeriodSelection, ...]:
    if (type(selections) is not tuple or not 1 <= len(selections) <= 16
            or any(type(item) is not SECPeriodSelection for item in selections)):
        raise ValueError("SEC period review requires one to sixteen immutable selections")
    for item in selections:
        item.__post_init__()
    if len(set(selections)) != len(selections):
        raise ValueError("duplicate SEC period selections are not supported")
    return tuple(sorted(selections, key=lambda item: (
        item.native_tag, item.period_start.isoformat() if item.period_start else "",
        item.period_end.isoformat())))


def parse_sec_period_selections(values: list[str]) -> tuple[SECPeriodSelection, ...]:
    """Accept TAG=START/END or TAG=@END; no guessed fiscal windows or whitespace repair."""
    if type(values) is not list or not 1 <= len(values) <= 16:
        raise ValueError("SEC period review requires one to sixteen explicit selections")
    results = []
    for value in values:
        if not isinstance(value, str) or len(value) > 160:
            raise ValueError("invalid SEC period selection")
        match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.-]{0,127})=(?:([0-9]{4}-[0-9]{2}-[0-9]{2})/|@)"
            r"([0-9]{4}-[0-9]{2}-[0-9]{2})", value, flags=re.ASCII)
        if match is None:
            raise ValueError("SEC period requires TAG=START/END or TAG=@END")
        results.append(SECPeriodSelection(match[1], date.fromisoformat(match[2]) if match[2]
                                          else None, date.fromisoformat(match[3])))
    return _ordered(tuple(results))


def _check(selection: SECPeriodSelection, facts: list[dict[str, Any]],
           source_available: bool, cutoff: datetime, filing_end: date | None) -> dict[str, Any]:
    start = selection.period_start.isoformat() if selection.period_start else None
    end = selection.period_end.isoformat()
    tagged = [fact for fact in facts if fact["tag"] == selection.native_tag]
    matching = [fact for fact in tagged
                if (fact["period_start"], fact["period_end"]) == (start, end)]
    unresolved = [fact["element_index"] for fact in tagged
                  if fact["status"] != "OBSERVED_UNQUALIFIED"
                  and (fact["period_end"] is None or "entity_cik" not in fact)]
    status, agreement = "SOURCE_UNAVAILABLE", None
    if selection.period_end > cutoff.astimezone(UTC).date():
        status = "FUTURE_TARGET"
    elif filing_end is not None and selection.period_end > filing_end:
        status = "AFTER_FILING_REPORT_END"
    elif source_available:
        if not matching:
            status = "MISSING_EXACT_PERIOD"
        elif any(fact["status"] != "OBSERVED_UNQUALIFIED" for fact in matching):
            status = "UNSUPPORTED_MATCHING_OCCURRENCE"
        else:
            agreement = len({Decimal(fact["value"]) for fact in matching}) == 1
            status = "OBSERVED_SUBSET_UNQUALIFIED" if agreement else "NUMERIC_CONFLICT"
    return {
        **asdict(selection), "period_basis": "instant" if start is None else "duration",
        "duration_calendar_days": ((selection.period_end - selection.period_start).days + 1
                                   if selection.period_start is not None else None),
        "status": status, "numeric_agreement_within_subset": agreement,
        "matching_occurrences": matching, "unresolved_tag_occurrence_indices": unresolved,
        "unresolved_tag_contexts_present": bool(unresolved),
        "annual_or_quarter_classification": "NOT_ADMITTED",
        "statement_and_consolidation_scope": "NOT_QUALIFIED",
        "amount_aggregation_authorized": False,
    }


def read_sec_period_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                           cik: str, accession: str, *, as_of: datetime,
                           selections: tuple[SECPeriodSelection, ...],
                           sector_profile: str) -> dict[str, Any]:
    """Read exact supported contexts; even consistent source observations remain unadmitted."""
    require_timezone(as_of, "SEC period input cutoff")
    ordered = _ordered(selections)
    if sector_profile not in _SECTORS:
        raise ValueError("SEC period review requires an explicit supported sector context")
    tags = tuple(sorted({item.native_tag for item in ordered}))
    with store.read_snapshot():
        source = read_sec_body_inputs(store, artifacts, cik, accession, as_of=as_of, tags=tags)
        body = source["body_review"]
        available = (source["source_bound"] is True
                     and source["status"] == "captured_body_unqualified"
                     and isinstance(body, dict) and body["status"] == "SUBSET_REVIEW_UNQUALIFIED")
        facts = body["facts"] if available else []
        filing_end = (date.fromisoformat(source["parent_binding"]["report_date"])
                      if available else None)
        checks = [_check(item, facts, available, as_of, filing_end) for item in ordered]
    document: dict[str, Any] = {
        "model_version": SEC_PERIOD_INPUT_VERSION, "subject": source["subject"],
        "as_of": as_of.astimezone(UTC), "requested_sector_profile": sector_profile,
        "sector_classification_verified": False, "sector_policy_status": "NOT_ADMITTED",
        "source_status": source["status"], "source_bound": source["source_bound"],
        "source_input_hash": source["input_hash"],
        "source_evidence_id": source.get("selected_evidence_id"),
        "source_body_sha256": source.get("body_sha256"),
        "source_parent_binding": source.get("parent_binding"),
        "source_captures": source["captures"],
        "source_review_version": source["review_version"], "checks": checks,
        "selected_fact_occurrence_count": len(facts),
        "unsupported_fact_occurrence_count": sum(
            fact["status"] != "OBSERVED_UNQUALIFIED" for fact in facts),
        "status": "SOURCE_SUBSET_REVIEW" if available else "SOURCE_UNAVAILABLE",
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "issuer_to_instrument_verified": False,
        "accounting_definitions_admitted": False, "financial_scoring_authorized": False,
        "investment_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False,
        "research_report_created": False,
        "limitations": (
            "Exact native periods and inclusive calendar-day counts are not fiscal approval",
            "No FY/12M/filing-form shortcut, annualization, TTM, FX or accounting alias",
            "Supported repeated occurrences are not summed, averaged or independent evidence",
            "Unresolved/dimensional/excluded contexts stay visible; this subset is incomplete",
            "Missing requested contexts are not issuer-wide nondisclosure or zero amounts",
            "Sector labels do not apply generic company health rules to banks or insurers",
            "Retrieval-time comparative values are not original historical vintages",
            "No research completion, financial score, validation or trading authority",
        ),
    }
    reject_sensitive_structure(document)
    return {**document, "input_hash": sha256(financial_input_json(document).encode()).hexdigest()}


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("SEC research receipt requires explicit timestamps")
    result = datetime.fromisoformat(value)
    require_timezone(result, "SEC research input timestamp")
    return result.astimezone(UTC)


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True, slots=True)
class SECPeriodResearchInput:
    """Copied diagnostic receipt with caller-selected equity binding, never authentication."""

    receipt_json: str
    symbol: str
    sector_profile: str
    model_version: str = SEC_PERIOD_RESEARCH_INPUT_VERSION

    def __post_init__(self) -> None:
        self.validate_context()

    def document(self) -> dict[str, Any]:
        if not isinstance(self.receipt_json, str) or len(self.receipt_json.encode()) > 2_097_152:
            raise ValueError("SEC research receipt outside supported bounds")
        result = json.loads(self.receipt_json)
        if not isinstance(result, dict):
            raise ValueError("SEC research receipt must be an object")
        return result

    @property
    def as_of(self) -> datetime:
        return _instant(self.document().get("as_of"))

    @property
    def binding_hash(self) -> str:
        return sha256(financial_input_json({
            "version": self.model_version, "requested_symbol": self.symbol,
            "requested_sector": self.sector_profile, "receipt": self.document(),
        }).encode()).hexdigest()

    def validate_context(self, *, symbol: str | None = None, market: Market | None = None,
                         as_of: datetime | None = None) -> None:
        try:
            self._validate_context(symbol=symbol, market=market, as_of=as_of)
        except (KeyError, TypeError, AttributeError, ArithmeticError):
            raise ValueError("malformed SEC research receipt") from None

    def _validate_context(self, *, symbol: str | None, market: Market | None,
                          as_of: datetime | None) -> None:
        document = self.document()
        reject_sensitive_structure(document, path="sec_period_research_input")
        validate_yahoo_equity_subject(Market.US, self.symbol)
        content = {key: value for key, value in document.items() if key != "input_hash"}
        if (self.model_version != SEC_PERIOD_RESEARCH_INPUT_VERSION
                or self.sector_profile not in _SECTORS
                or document.get("requested_sector_profile") != self.sector_profile
                or self.receipt_json != financial_input_json(document)
                or document.get("model_version") != SEC_PERIOD_INPUT_VERSION
                or document.get("source_review_version") != SEC_INLINE_REVIEW_VERSION
                or sha256(financial_input_json(content).encode()).hexdigest()
                != document.get("input_hash")
                or document.get("trust_ceiling") != "LOW"
                or document.get("availability_precision") != "retrieval_time"
                or document.get("freshness") != "UNASSESSED"
                or document.get("sector_policy_status") != "NOT_ADMITTED"
                or any(document.get(name) is not False for name in (
                    "sector_classification_verified", "issuer_to_instrument_verified",
                    "accounting_definitions_admitted", "financial_scoring_authorized",
                    "investment_scoring_authorized", "historical_replay_eligible",
                    "validation_authorized", "execution_authorized", "research_report_created"))):
            raise ValueError("SEC research receipt integrity or authority mismatch")
        cutoff = self.as_of
        if as_of is not None:
            require_timezone(as_of, "SEC research context cutoff")
        if ((symbol is not None and symbol != self.symbol)
                or (market is not None and market is not Market.US)
                or (as_of is not None and as_of.astimezone(UTC) != cutoff)):
            raise ValueError("SEC research context mismatch")
        parts = str(document.get("subject", "")).split(":")
        if len(parts) != 2 or body_subject(*parts) != document["subject"]:
            raise ValueError("SEC research requires exact CIK/accession scope")
        captures = document.get("source_captures")
        if (not _hash(document.get("source_input_hash"))
                or type(document.get("source_bound")) is not bool
                or not isinstance(captures, list) or len(captures) > 10000
                or any(not isinstance(row, dict) or _instant(row.get("available_at")) > cutoff
                       or not _hash(row.get("evidence_id")) or not _hash(row.get("raw_data_hash"))
                       for row in captures)):
            raise ValueError("SEC research source visibility or identity mismatch")
        ready = document.get("status") == "SOURCE_SUBSET_REVIEW"
        if document.get("status") not in {"SOURCE_SUBSET_REVIEW", "SOURCE_UNAVAILABLE"}:
            raise ValueError("unsupported SEC research receipt state")
        if ready and (document["source_bound"] is not True
                      or document.get("source_status") != "captured_body_unqualified"
                      or not _hash(document.get("source_body_sha256"))):
            raise ValueError("SEC period review requires a captured unqualified body")
        if document["source_bound"]:
            if not captures:
                raise ValueError("SEC source-bound receipt requires a capture")
            latest = max(_instant(row["available_at"]) for row in captures)
            selected = [row for row in captures if _instant(row["available_at"]) == latest]
            if (len(selected) != 1
                    or selected[0]["evidence_id"] != document.get("source_evidence_id")):
                raise ValueError("SEC research selected source mismatch")
            params = document.get("source_parent_binding")
            if not isinstance(params, dict):
                raise ValueError("SEC research requires a pinned parent")
            validate_request(ProviderDatasetRequest(DATASET, Market.US, document["subject"],
                                                    latest, params))
        else:
            params = None
        filing_end = date.fromisoformat(params["report_date"]) if ready and params else None
        checks = document.get("checks")
        total, unsupported = (document.get("selected_fact_occurrence_count"),
                              document.get("unsupported_fact_occurrence_count"))
        if (not isinstance(checks, list) or not 1 <= len(checks) <= 16
                or type(total) is not int or not 0 <= total <= 10000
                or type(unsupported) is not int or not 0 <= unsupported <= total
                or not ready and total != 0):
            raise ValueError("SEC research checks or occurrence counts outside supported bounds")
        selections = []
        for check in checks:
            selection = SECPeriodSelection(check["native_tag"],
                date.fromisoformat(check["period_start"]) if check["period_start"] is not None
                else None, date.fromisoformat(check["period_end"]))
            selections.append(selection)
            rows = check["matching_occurrences"]
            unresolved = check["unresolved_tag_occurrence_indices"]
            if (not isinstance(rows, list) or len(rows) > total
                    or not isinstance(unresolved, list) or len(unresolved) > unsupported
                    or any(type(index) is not int or not 0 <= index < 250000
                           for index in unresolved)
                    or len(set(unresolved)) != len(unresolved)
                    or check["unresolved_tag_contexts_present"] is not bool(unresolved)
                    or not ready and (rows or unresolved)):
                raise ValueError("SEC research occurrence inventory mismatch")
            indices = []
            for row in rows:
                self._validate_row(row, selection, parts[0], cutoff)
                indices.append(row["element_index"])
            if len(set(indices)) != len(indices):
                raise ValueError("SEC research occurrence indices must remain unique")
            expected = _check(selection, rows, ready, cutoff, filing_end)
            excluded = {"unresolved_tag_occurrence_indices", "unresolved_tag_contexts_present"}
            if financial_input_json({key: value for key, value in check.items()
                                     if key not in excluded}) != financial_input_json({
                    key: value for key, value in expected.items() if key not in excluded}):
                raise ValueError("SEC research period result contradicts its observations")
        if tuple(selections) != _ordered(tuple(selections)):
            raise ValueError("SEC research selections must have canonical order")

    @staticmethod
    def _validate_row(row: dict[str, Any], selection: SECPeriodSelection,
                      cik: str, cutoff: datetime) -> None:
        if (type(row.get("element_index")) is not int or not 0 <= row["element_index"] < 250000
                or row.get("tag") != selection.native_tag
                or row.get("period_start") != (
                    selection.period_start.isoformat() if selection.period_start else None)
                or row.get("period_end") != selection.period_end.isoformat()
                or row.get("status") not in {"OBSERVED_UNQUALIFIED", "UNSUPPORTED_FACT"}):
            raise ValueError("SEC research occurrence scope mismatch")
        if row["status"] == "UNSUPPORTED_FACT":
            if row.get("value") is not None:
                raise ValueError("Unsupported SEC occurrence cannot carry a usable amount")
            return
        value = row.get("value")
        if (not isinstance(value, str) or re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value) is None
                or len(value) > 128 or row.get("unit") != "USD"
                or row.get("taxonomy") != "us-gaap" or row.get("entity_cik") != cik
                or re.fullmatch(r"https?://fasb.org/us-gaap/[0-9]{4}",
                                str(row.get("namespace"))) is None
                or selection.period_end > cutoff.date()):
            raise ValueError("SEC research occurrence value/unit/visibility mismatch")
        amount = Decimal(value)
        exponent = amount.as_tuple().exponent
        if (not amount.is_finite() or abs(amount) > Decimal("1e24")
                or not isinstance(exponent, int) or exponent < -36):
            raise ValueError("SEC research amount outside supported bounds")


def read_sec_period_research_input(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    cik: str, accession: str, *, symbol: str, as_of: datetime,
    selections: tuple[SECPeriodSelection, ...], sector_profile: str,
) -> SECPeriodResearchInput:
    """Retained source checks precede the copied, explicitly unverified equity context."""
    validate_yahoo_equity_subject(Market.US, symbol)
    receipt = read_sec_period_inputs(store, artifacts, cik, accession, as_of=as_of,
                                    selections=selections, sector_profile=sector_profile)
    return SECPeriodResearchInput(financial_input_json(receipt), symbol, sector_profile)
