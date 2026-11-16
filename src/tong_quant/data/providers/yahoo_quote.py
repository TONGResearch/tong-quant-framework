"""Current China-A price observations from decoded Yahoo charts, never market values."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from urllib.parse import urlencode

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
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import YAHOO_CHINA_QUOTE_VERSION

PROVIDER = "yahoo_finance"
DATASET = "china_equity_quote_observation"
MAX_BYTES = 256 * 1024
LIMITATIONS = (
    EvidenceLimitation("unofficial_price_only",
        "Unofficial current price only; no share counts, market values or valuation authority",
        DataTrustLevel.LOW),
    EvidenceLimitation("decoded_not_wire_capture",
        "Retained SDK-decoded JSON, not original HTTP bytes; native precision is unqualified",
        DataTrustLevel.LOW),
    EvidenceLimitation("quote_clock_and_identity_unqualified",
        "Provider-claimed identity, currency and quote clock need independent review; "
        "a regular-market snapshot is not a verified daily close, listing or session record",
        DataTrustLevel.LOW),
    EvidenceLimitation("current_retrieval_only",
        "Retrieval-time availability only; no historical availability, revisions or calibration",
        DataTrustLevel.LOW),
)


def yahoo_equity_symbol(symbol: str) -> str:
    if len(symbol) != 6 or not symbol.isascii() or not symbol.isdigit():
        raise ValueError("explicit six-digit China-A equity code required")
    if symbol.startswith(("000", "001", "002", "003", "300", "301")):
        return f"{symbol}.SZ"
    if symbol.startswith(("600", "601", "603", "605", "688", "689")):
        return f"{symbol}.SS"
    raise ValueError("Yahoo quote routing does not admit BSE, funds or other instruments")


def query_url(symbol: str, query_date: date) -> str:
    ticker = yahoo_equity_symbol(symbol)
    start = datetime.combine(query_date - timedelta(days=7), time.min, UTC)
    end = datetime.combine(query_date + timedelta(days=1), time.min, UTC)
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?" + urlencode({
        "period1": str(int(start.timestamp())), "period2": str(int(end.timestamp())),
        "interval": "1d", "events": "div,splits,capitalGains", "includeAdjustedClose": "false",
    })


@dataclass(frozen=True, slots=True)
class YahooQuoteCapture:
    query_date: date
    payload: dict[str, object] | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if (type(self.query_date) is not date or self.error_code not in (
            "", "provider_unavailable", "invalid_decoded_response")
                or (self.payload is None) != bool(self.error_code)
                or (self.payload is not None and type(self.payload) is not dict)):
            raise ValueError("invalid decoded Yahoo quote capture")
        reject_sensitive_structure(self.payload, path="yahoo_quote")
        encoded = json.dumps(self.payload, sort_keys=True, allow_nan=False)
        if len(encoded.encode()) > MAX_BYTES:
            raise ValueError("decoded Yahoo quote capture exceeds size bound")


def download_quote(symbol: str) -> YahooQuoteCapture:
    ticker = yahoo_equity_symbol(symbol)
    query_date = datetime.now(UTC).date()
    try:
        payload = YahooChartHttpClient(timeout_seconds=6, max_attempts=1).chart(
            ticker, start_date=(query_date - timedelta(days=7)).isoformat(),
            end_date=query_date.isoformat())
        return YahooQuoteCapture(query_date, payload)
    except DataProviderUnavailableError:
        return YahooQuoteCapture(query_date, None, "provider_unavailable")
    except (ValueError, UnicodeError):
        return YahooQuoteCapture(query_date, None, "invalid_decoded_response")


def normalize_quote(
    capture: YahooQuoteCapture, symbol: str, retrieved: datetime,
) -> dict[str, object]:
    capture.__post_init__()
    require_timezone(retrieved, "quote retrieval")
    ticker = yahoo_equity_symbol(symbol)
    output: dict[str, object] = {
        "symbol": symbol, "provider_symbol": ticker, "status": "unavailable",
        "price": None, "claimed_quote_at": None, "currency": None,
        "price_kind": "regular_market_snapshot_not_verified_daily_close",
        "total_shares": None, "float_shares": None, "total_market_value": None,
        "float_market_value": None, "valuation_authorized": False,
        "investment_scoring_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "model_version": YAHOO_CHINA_QUOTE_VERSION,
        "reasons": [capture.error_code] if capture.error_code else [],
    }
    if capture.payload is None:
        return output
    try:
        chart = capture.payload.get("chart")
        if not isinstance(chart, dict) or chart.get("error") is not None:
            raise ValueError("chart_status")
        results = chart.get("result")
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise ValueError("chart_result")
        meta = results[0].get("meta")
        exchange = "SHZ" if ticker.endswith(".SZ") else "SHH"
        if not isinstance(meta, dict) or (
            meta.get("symbol"), meta.get("currency"), meta.get("exchangeName"),
            meta.get("instrumentType"), meta.get("exchangeTimezoneName"),
        ) != (ticker, "CNY", exchange, "EQUITY", "Asia/Shanghai"):
            raise ValueError("quote_identity_or_scope")
        price, stamp = meta.get("regularMarketPrice"), meta.get("regularMarketTime")
        if type(price) not in (int, float, str) or type(stamp) is not int:
            raise ValueError("quote_value_or_clock")
        value = Decimal(str(price))
        if (not value.is_finite() or value <= 0 or len(value.as_tuple().digits) > 30
                or abs(int(value.as_tuple().exponent)) > 12 or not 0 < stamp < 253402300800):
            raise ValueError("quote_value_or_clock")
        claimed = datetime.fromtimestamp(stamp, UTC)
        if claimed > retrieved.astimezone(UTC):
            raise ValueError("future_quote_claim")
        output.update(status="price_only_unqualified", price=str(value), currency="CNY",
            claimed_quote_at=claimed.isoformat(), reasons=[
                "Price-only decoded observation; shares and market value unavailable",
                "Identity, currency, quote clock and session freshness are unqualified",
            ])
    except (ValueError, InvalidOperation, OverflowError):
        output.update(status="invalid_response", reasons=["quote_identity_value_or_clock_rejected"])
    return output


class YahooChinaQuoteEvidenceAdapter:
    provider_id = PROVIDER

    def __init__(self, *, download: Callable[[str], YahooQuoteCapture] = download_quote,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.download, self.clock = download, clock

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, (Market.CHINA_A,),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, (), LIMITATIONS,
            YAHOO_CHINA_QUOTE_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.market is not Market.CHINA_A or request.dataset != DATASET or request.parameters:
            raise ValueError("unsupported Yahoo China equity quote request")
        yahoo_equity_symbol(request.subject)
        capture = self.download(request.subject)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "quote capture")
        if (captured.astimezone(UTC) < request.as_of.astimezone(UTC)
                or capture.query_date > captured.astimezone(UTC).date()):
            raise ValueError("quote capture precedes request or query date")
        url = query_url(request.subject, capture.query_date)
        envelope = {"symbol": request.subject, "query_date": capture.query_date.isoformat(),
            "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload,
            "error_code": capture.error_code, "model_version": YAHOO_CHINA_QUOTE_VERSION}
        content = json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()
        digest = sha256(content).hexdigest()
        identity = f"{request.subject}:decoded-yahoo-current-price"
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=identity,
            source_reference=url, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market,
            request.subject, identity, url, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            YAHOO_CHINA_QUOTE_VERSION)
        payload = {**normalize_quote(capture, request.subject, captured),
                   "artifact_id": artifact_id}
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=url, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, url, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW,
            tuple(item.description for item in LIMITATIONS))
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, url,
            {"subject": request.subject, "query_date": capture.query_date.isoformat(),
             "normalization_version": YAHOO_CHINA_QUOTE_VERSION}, digest, 1, (record,),
            LIMITATIONS, (artifact,))
