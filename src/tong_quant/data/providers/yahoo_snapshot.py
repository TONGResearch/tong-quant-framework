"""Retain global equity price snapshots without qualifying prices for research."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from urllib.parse import quote
from zoneinfo import ZoneInfo

from tong_quant.core.exceptions import DataProviderUnavailableError
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
from tong_quant.data.providers.yahoo import YahooChartHttpClient
from tong_quant.data.providers.yahoo_identity import TIMEZONES as TIMEZONES
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel
from tong_quant.domain.models import Bar, Instrument, require_timezone
from tong_quant.version import GLOBAL_PRICE_SNAPSHOT_VERSION

PROVIDER = "yahoo_finance"
DATASET = "global_equity_price_snapshot"
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 10000
LIMITATIONS = (
    "Decoded Yahoo response, not original HTTP bytes or independently verified truth",
    "LOW/retrieval-time evidence; historical publication and continuity are unverified",
    "Provider-native OHLC may contain adjustments; includeAdjustedClose=false is not proof",
    "No verified calendar, completion, lifecycle, sector, fundamental or strategy qualification",
    "No historical replay, InvestmentScore, validation or trading authorization",
)


def validate_snapshot_request(request: ProviderDatasetRequest) -> None:
    request.__post_init__()
    if request.dataset != DATASET:
        raise ValueError("unsupported global equity snapshot identity")
    validate_yahoo_equity_subject(request.market, request.subject)
    params = request.parameters
    if set(params) != {"start_date", "end_date", "currency", "exchange", "timezone"}:
        raise ValueError("snapshot requires explicit dates, currency, exchange and timezone")
    if (not re.fullmatch(r"[A-Z]{3}", params["currency"], flags=re.ASCII)
            or not re.fullmatch(r"[A-Z0-9]{2,12}", params["exchange"], flags=re.ASCII)
            or params["timezone"] != TIMEZONES[request.market]):
        raise ValueError("unsupported snapshot currency, exchange or market timezone")
    start, end = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
    if start > end or (end - start).days > 15000:
        raise ValueError("snapshot date range is reversed or exceeds bound")


@dataclass(frozen=True, slots=True)
class YahooSnapshotCapture:
    payload: dict[str, object] | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if self.payload is not None and not isinstance(self.payload, dict):
            raise ValueError("decoded snapshot payload must be an object")
        if (self.payload is None) != bool(self.error_code):
            raise ValueError("capture must have either decoded payload or a failure code")
        if self.error_code not in {"", "provider_unavailable", "invalid_decoded_response"}:
            raise ValueError("unsupported capture failure code")
        reject_sensitive_structure(self.payload, path="global_price_capture")
        content = json.dumps(self.payload, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()
        if len(content) > MAX_BYTES:
            raise ValueError("global price capture exceeds byte bound")


def download_snapshot(request: ProviderDatasetRequest) -> YahooSnapshotCapture:
    validate_snapshot_request(request)
    try:
        payload = YahooChartHttpClient(timeout_seconds=8, max_attempts=2).chart(
            request.subject, start_date=request.parameters["start_date"],
            end_date=request.parameters["end_date"])
    except DataProviderUnavailableError:
        return YahooSnapshotCapture(None, "provider_unavailable")
    except ValueError:
        return YahooSnapshotCapture(None, "invalid_decoded_response")
    return YahooSnapshotCapture(payload)


def snapshot_prices(capture: YahooSnapshotCapture, request: ProviderDatasetRequest,
                    captured: datetime) -> tuple[str, tuple[Bar, ...]]:
    """Only a complete, consistent delivered series reaches exploratory calculations."""
    validate_snapshot_request(request)
    capture.__post_init__()
    require_timezone(captured, "global snapshot capture")
    if capture.payload is None:
        return capture.error_code, ()
    try:
        chart = capture.payload["chart"]
        if not isinstance(chart, dict) or chart.get("error") is not None:
            raise ValueError("chart error")
        results = chart["result"]
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise ValueError("ambiguous chart result")
        result = results[0]
        meta = result["meta"]
        if not isinstance(meta, dict):
            raise ValueError("missing metadata")
        params = request.parameters
        for field, expected in (("symbol", request.subject), ("currency", params["currency"]),
                                ("exchangeName", params["exchange"]),
                                ("exchangeTimezoneName", params["timezone"]),
                                ("instrumentType", "EQUITY"), ("dataGranularity", "1d")):
            if meta.get(field) != expected:
                raise ValueError("native identity, units or granularity mismatch")
        timestamps = result["timestamp"]
        indicators = result["indicators"]
        if (not isinstance(timestamps, list) or len(timestamps) > MAX_ROWS
                or not isinstance(indicators, dict)):
            raise ValueError("unsupported observation series")
        quotes = indicators["quote"]
        if not isinstance(quotes, list) or len(quotes) != 1 or not isinstance(quotes[0], dict):
            raise ValueError("ambiguous quote arrays")
        rows = quotes[0]
        fields = ("open", "high", "low", "close", "volume")
        if any(not isinstance(rows.get(name), list) or len(rows[name]) != len(timestamps)
               for name in fields):
            raise ValueError("unaligned OHLCV arrays")
        instrument = Instrument(request.subject, request.market, request.subject,
            currency=params["currency"], exchange=params["exchange"],
            available_at=captured, source=PROVIDER)
        bars: list[Bar] = []
        seen_dates: set[date] = set()
        zone = ZoneInfo(params["timezone"])
        for index, stamp in enumerate(timestamps):
            if type(stamp) is not int or not 0 < stamp < 253402300800:
                raise ValueError("invalid observation clock")
            observed = datetime.fromtimestamp(stamp, UTC)
            session_date = observed.astimezone(zone).date()
            if (observed > captured.astimezone(UTC) or session_date in seen_dates
                    or (bars and observed <= bars[-1].timestamp)
                    or not date.fromisoformat(params["start_date"]) <= session_date <= (
                        date.fromisoformat(params["end_date"]))):
                raise ValueError("future, duplicate, reversed or out-of-range observation")
            seen_dates.add(session_date)
            values = []
            for name in fields:
                native = rows[name][index]
                if type(native) not in (float, int):
                    raise ValueError("missing or nonnumeric OHLCV")
                value = Decimal(str(native))
                if not value.is_finite() or abs(value) > Decimal("1e18"):
                    raise ValueError("nonfinite or excessive OHLCV")
                values.append(value)
            opening, high, low, close, volume = values
            if min(opening, high, low, close) <= 0 or volume != volume.to_integral_value():
                raise ValueError("nonpositive price or fractional volume")
            # NONE means no Tong transformation, not proof of unadjusted source history.
            bars.append(Bar(instrument, observed, captured, opening, high, low, close, volume,
                            source=f"{PROVIDER}:{DATASET}:native_unverified"))
        if not bars:
            return "no_observations", ()
        if bars[-1].timestamp.astimezone(zone).date() == captured.astimezone(zone).date():
            return "current_session_completion_unverified", ()
        return "observed_unqualified", tuple(bars)
    except (ValueError, KeyError, TypeError, ArithmeticError, OverflowError):
        return "invalid_response", ()


@dataclass(slots=True)
class YahooGlobalSnapshotAdapter:
    download: Callable[[ProviderDatasetRequest], YahooSnapshotCapture] = download_snapshot
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, tuple(TIMEZONES),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False,
            ("start_date", "end_date", "currency", "exchange", "timezone"),
            tuple(EvidenceLimitation(f"global_snapshot_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), GLOBAL_PRICE_SNAPSHOT_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        validate_snapshot_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "global snapshot capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("global snapshot capture clock must use UTC")
        content = json.dumps({"model_version": GLOBAL_PRICE_SNAPSHOT_VERSION,
            "market": request.market.value, "subject": request.subject,
            "parameters": request.parameters, "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload, "error_code": capture.error_code},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest = sha256(content).hexdigest()
        reference = f"https://finance.yahoo.com/quote/{quote(request.subject, safe='')}/history"
        identity = f"{request.subject}:{GLOBAL_PRICE_SNAPSHOT_VERSION}"
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=identity,
            source_reference=reference, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            identity, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            GLOBAL_PRICE_SNAPSHOT_VERSION)
        status, bars = snapshot_prices(capture, request, captured)
        payload: dict[str, object] = {"status": status, "observed_bar_count": len(bars),
            "artifact_id": artifact_id, "price_basis": "PROVIDER_NATIVE_UNVERIFIED",
            "model_version": GLOBAL_PRICE_SNAPSHOT_VERSION}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, **request.parameters,
             "normalization_version": GLOBAL_PRICE_SNAPSHOT_VERSION}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
