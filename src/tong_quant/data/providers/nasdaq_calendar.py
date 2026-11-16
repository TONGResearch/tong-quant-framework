"""Retain Nasdaq's explicitly listed holiday dates, never infer a full US calendar."""

import base64
import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from html.parser import HTMLParser
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import certifi

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderArtifact,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_evidence_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import NASDAQ_CALENDAR_VERSION

PROVIDER, DATASET = "nasdaq_calendar", "exchange_holiday_snapshot"
SOURCE_URL = "https://www.nasdaqtrader.com/Trader.aspx?id=Calendar"
MAX_BYTES, MAX_ENVELOPE_BYTES = 2 * 1024 * 1024, 3 * 1024 * 1024
LIMITATIONS = (
    "Explicit Nasdaq holiday/early-close declarations only; unlisted dates remain unknown",
    "Exchange scope is Nasdaq equities, not NYSE, options, broker sessions or settlement",
    "Current page retrieval is not historical publication/revision or emergency-event coverage",
    "Official-domain transport and byte hashes do not independently authenticate source truth",
    "LOW/retrieval-time; no calendar completeness, canonical sessions, PIT or strategy admission",
    "No scoring, historical replay, validation or execution authority",
)
_ERRORS = {"", "http_403", "http_404", "http_429", "http_error", "network_unavailable",
           "response_too_large", "empty_response", "invalid_html_payload"}
_MONTHS = {name: index for index, name in enumerate(("January", "February", "March", "April",
    "May", "June", "July", "August", "September", "October", "November", "December"), 1)}


def calendar_subject(year: int) -> str:
    if type(year) is not int or not 2000 <= year <= 2100:
        raise ValueError("Nasdaq calendar requires an explicit year in 2000..2100")
    return f"NASDAQ:{year}"


def validate_request(request: ProviderDatasetRequest) -> int:
    request.__post_init__()
    if (request.dataset != DATASET or request.market is not Market.US
            or set(request.parameters) != {"year"}
            or not isinstance(request.parameters["year"], str)
            or re.fullmatch(r"[0-9]{4}", request.parameters["year"], flags=re.ASCII) is None):
        raise ValueError("unsupported Nasdaq calendar request")
    year = int(request.parameters["year"])
    if request.subject != calendar_subject(year):
        raise ValueError("Nasdaq calendar subject/year mismatch")
    return year


@dataclass(frozen=True, slots=True)
class NasdaqCalendarCapture:
    content: bytes | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if ((self.content is None) != bool(self.error_code) or self.error_code not in _ERRORS
                or self.content is not None and (type(self.content) is not bytes
                    or not 0 < len(self.content) <= MAX_BYTES)):
            raise ValueError("invalid bounded Nasdaq calendar capture")
        if self.content is not None:
            text = self.content.decode("utf-8-sig")
            reject_sensitive_structure(text, path="nasdaq_calendar_body")


@dataclass
class _Table:
    rows: list[list[str]] = field(default_factory=list)
    row: list[str] | None = None
    cell: list[str] | None = None
    invalid: bool = False


class _CalendarHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_Table] = []
        self.tables: list[_Table] = []
        self.headings: list[str] = []
        self.heading: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1":
            self.heading = []
        if tag == "table":
            if self.stack:
                self.stack[-1].invalid = True
            self.stack.append(_Table())
            if len(self.stack) > 32:
                raise ValueError("calendar HTML nesting exceeds bound")
        elif self.stack:
            current = self.stack[-1]
            if tag == "tr":
                current.invalid |= current.row is not None
                current.row = []
            elif tag in {"td", "th"}:
                current.invalid |= current.cell is not None or current.row is None
                current.cell = []
            elif tag in {"script", "style"} and current.cell is not None:
                current.invalid = True

    def handle_data(self, text: str) -> None:
        if self.heading is not None:
            self.heading.append(text)
        if self.stack and self.stack[-1].cell is not None:
            self.stack[-1].cell.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.heading is not None:
            self.headings.append(" ".join("".join(self.heading).split()))
            self.heading = None
        if not self.stack:
            return
        current = self.stack[-1]
        if tag in {"td", "th"} and current.cell is not None:
            if current.row is not None:
                current.row.append(" ".join("".join(current.cell).split()))
            current.cell = None
        elif tag == "tr" and current.row is not None:
            current.invalid |= current.cell is not None
            current.rows.append(current.row)
            current.row = None
        elif tag == "table":
            current.invalid |= current.row is not None or current.cell is not None
            self.tables.append(self.stack.pop())


def _native_date(text: str) -> date:
    match = re.fullmatch(r"([A-Za-z]+) ([0-9]{1,2}), ([0-9]{4})", text, flags=re.ASCII)
    if match is None or match[1] not in _MONTHS:
        raise ValueError("unsupported calendar date")
    return date(int(match[3]), _MONTHS[match[1]], int(match[2]))


def calendar_declarations(capture: NasdaqCalendarCapture, year: int) -> dict[str, Any]:
    calendar_subject(year)
    capture.__post_init__()
    output: dict[str, Any] = {"status": capture.error_code or "unsupported_calendar_layout",
                              "page_years": [], "declarations": []}
    if capture.content is None:
        return output
    parser = _CalendarHTML()
    try:
        parser.feed(capture.content.decode("utf-8-sig"))
        parser.close()
    except ValueError:
        return output
    matches = [re.fullmatch(r"U\.S\. Equity and Options Markets Holiday Schedule ([0-9]{4})",
                            text, flags=re.ASCII) for text in parser.headings]
    years = [int(match[1]) for match in matches if match is not None]
    output["page_years"] = years
    if year not in years:
        output["status"] = "requested_year_not_present" if years else "unsupported_calendar_layout"
        return output
    tables = [table for table in parser.tables if table.rows
              and table.rows[0] == [str(year), "Holiday", "Status"]]
    if not tables:
        return output
    if len(tables) != 1 or years.count(year) != 1:
        output["status"] = "ambiguous_calendar_tables"
        return output
    table = tables[0]
    if table.invalid or parser.stack or not 1 <= len(table.rows[1:]) <= 500:
        return output
    dates: set[date] = set()
    status = "explicit_declarations_unqualified"
    for cells in table.rows[1:]:
        if len(cells) != 3 or any(not cell or len(cell) > 300 for cell in cells):
            output["status"] = "unsupported_calendar_layout"
            return output
        row: dict[str, Any] = {"native_date": cells[0], "native_label": cells[1],
            "native_status": cells[2], "trade_date": None, "is_open": None,
            "session_kind": "UNSUPPORTED", "core_close_local": None}
        try:
            day = _native_date(cells[0])
            if day.year != year or day in dates:
                raise ValueError("conflicting or wrong-year declaration")
            dates.add(day)
            row["trade_date"] = day.isoformat()
            if cells[2] == "Closed":
                row.update(is_open=False, session_kind="FULL_DAY_CLOSED")
            else:
                early = re.fullmatch(r"(1[0-2]|[1-9]):([0-5][0-9]) ([ap])\.m\.", cells[2])
                if early is None or not cells[1].startswith("Early Close"):
                    raise ValueError("unsupported calendar status")
                hour = int(early[1]) % 12 + (12 if early[3] == "p" else 0)
                row.update(is_open=True, session_kind="EARLY_CORE_CLOSE",
                           core_close_local=f"{hour:02}:{early[2]}:00")
        except ValueError:
            status = "unsupported_or_conflicting_declarations"
        output["declarations"].append(row)
    output["status"] = status
    return output


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        return None


def download_calendar(request: ProviderDatasetRequest) -> NasdaqCalendarCapture:
    validate_request(request)
    opener = build_opener(_NoRedirect(), HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where())))
    error_code = "network_unavailable"
    for attempt in range(2):
        if attempt:
            sleep(2)
        try:
            with opener.open(Request(SOURCE_URL, headers={
                "User-Agent": "TongQuant/0.8 research-calendar", "Accept": "text/html",
                "Accept-Encoding": "identity"}), timeout=15) as response:
                if response.status != 200 or response.geturl() != SOURCE_URL:
                    return NasdaqCalendarCapture(None, "http_error")
                content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                return NasdaqCalendarCapture(None, "response_too_large")
            if not content:
                return NasdaqCalendarCapture(None, "empty_response")
            try:
                return NasdaqCalendarCapture(content)
            except ValueError:
                return NasdaqCalendarCapture(None, "invalid_html_payload")
        except HTTPError as error:
            error_code = f"http_{error.code}" if error.code in {403, 404, 429} else "http_error"
            if error.code < 500 and error.code != 429:
                break
        except (TimeoutError, URLError, OSError):
            error_code = "network_unavailable"
    return NasdaqCalendarCapture(None, error_code)


@dataclass(slots=True)
class NasdaqCalendarAdapter:
    download: Callable[[ProviderDatasetRequest], NasdaqCalendarCapture] = download_calendar
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.US,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, ("year",),
            tuple(EvidenceLimitation(f"nasdaq_calendar_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), NASDAQ_CALENDAR_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        year = validate_request(request)
        if self.provider_id != PROVIDER:
            raise ValueError("Nasdaq calendar provider identity mismatch")
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "Nasdaq calendar capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("Nasdaq calendar capture clock must use UTC")
        if captured.astimezone(UTC) < request.as_of.astimezone(UTC):
            raise ValueError("Nasdaq calendar capture precedes request")
        content = json.dumps({"model_version": NASDAQ_CALENDAR_VERSION,
            "market": Market.US.value, "subject": request.subject,
            "parameters": request.parameters, "retrieved_at": captured.astimezone(UTC).isoformat(),
            "error_code": capture.error_code, "document_base64": (
                base64.b64encode(capture.content).decode() if capture.content else None)},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(content) > MAX_ENVELOPE_BYTES:
            raise ValueError("Nasdaq calendar envelope exceeds bound")
        digest = sha256(content).hexdigest()
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=Market.US, subject=request.subject, source_identity=NASDAQ_CALENDAR_VERSION,
            source_reference=SOURCE_URL, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, Market.US, request.subject,
            NASDAQ_CALENDAR_VERSION, SOURCE_URL, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            NASDAQ_CALENDAR_VERSION)
        payload: dict[str, object] = {**calendar_declarations(capture, year), "year": year,
            "exchange": "NASDAQ", "market_timezone": "America/New_York",
            "artifact_id": artifact_id, "source_url": SOURCE_URL,
            "document_sha256": sha256(capture.content).hexdigest() if capture.content else None,
            "document_byte_size": len(capture.content or b""), "published_at_known": False,
            "calendar_complete": False, "actual_session_verified": False,
            "canonical_calendar_authorized": False, "scoring_authorized": False,
            "historical_replay_eligible": False, "validation_authorized": False,
            "execution_authorized": False}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=Market.US, subject=request.subject, available_at=captured,
            source_reference=SOURCE_URL, payload=payload), PROVIDER, DATASET, Market.US,
            request.subject, captured, captured, SOURCE_URL, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, Market.US, captured, SOURCE_URL,
            {"subject": request.subject, **request.parameters,
             "normalization_version": NASDAQ_CALENDAR_VERSION}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
