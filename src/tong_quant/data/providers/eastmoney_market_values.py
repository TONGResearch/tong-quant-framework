"""Bounded public quote-body capture, retaining failures instead of inventing market values."""

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from urllib.parse import urlencode

import requests

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
from tong_quant.version import MARKET_VALUE_CAPTURE_VERSION

PROVIDER = "eastmoney_direct"
DATASET = "equity_market_value_snapshot"
MAX_BYTES = 65536
FIELDS = "f57,f58,f43,f59,f84,f85,f86,f116,f117"
LIMITATIONS = (
    EvidenceLimitation("market_value_unreviewed_native_units",
                      "Native field mappings follow AKShare's Eastmoney implementation; "
                      "CNY/share units, share-class scope and quote clock need independent review",
                      DataTrustLevel.LOW),
    EvidenceLimitation("market_value_current_snapshot_only",
                      "Current snapshot only; no historical shares, market values or PIT coverage",
                      DataTrustLevel.LOW),
    EvidenceLimitation("market_value_not_independent_of_akshare_eastmoney",
                      "Direct Eastmoney and AKShare Eastmoney share an upstream; agreement is not "
                      "independent provider calibration, valuation or scoring approval",
                      DataTrustLevel.LOW),
)


def quote_url(symbol: str) -> str:
    if (len(symbol) != 6 or not symbol.isascii() or not symbol.isdigit()
            or not symbol.startswith(("000", "001", "002", "003", "300", "301", "600",
                                      "601", "603", "605", "688", "689"))):
        raise ValueError("quote capture supports explicit SZSE/SSE equity code scopes only")
    return "https://push2.eastmoney.com/api/qt/stock/get?" + urlencode({
        "secid": f"{1 if symbol.startswith('6') else 0}.{symbol}",
        "fltt": "2", "invt": "2", "fields": FIELDS,
    })


@dataclass(frozen=True, slots=True)
class QuoteHttpCapture:
    status_code: int | None
    body: bytes
    error_code: str = ""

    def __post_init__(self) -> None:
        if (type(self.body) is not bytes or len(self.body) > MAX_BYTES
                or (self.status_code is not None and (
                    type(self.status_code) is not int or not 100 <= self.status_code <= 599))
                or self.error_code not in {"", "Timeout", "ConnectionError", "RequestException",
                                           "ResponseTooLarge"}
                or (self.status_code is None and not self.error_code)):
            raise ValueError("invalid bounded quote HTTP capture")
        reject_sensitive_structure(self.body.decode("utf-8", errors="replace"), path="quote_body")
        try:
            decoded = json.loads(self.body)
        except (ValueError, UnicodeError, RecursionError):
            decoded = None
        if isinstance(decoded, (dict, list)):
            reject_sensitive_structure(decoded, path="quote_body_json")


def download_quote(symbol: str) -> QuoteHttpCapture:
    url = quote_url(symbol)
    try:
        with requests.get(url, timeout=(3, 8), allow_redirects=False, stream=True) as response:
            content = bytearray()
            for chunk in response.iter_content(8192):
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    return QuoteHttpCapture(response.status_code, b"", "ResponseTooLarge")
            return QuoteHttpCapture(response.status_code, bytes(content))
    except requests.Timeout:
        return QuoteHttpCapture(None, b"", "Timeout")
    except requests.ConnectionError:
        return QuoteHttpCapture(None, b"", "ConnectionError")
    except requests.RequestException:
        return QuoteHttpCapture(None, b"", "RequestException")


def _number(value: object) -> str | None:
    if type(value) not in {str, int, Decimal}:
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return str(number) if (number.is_finite() and number >= 0
                          and len(number.as_tuple().digits) <= 30
                          and abs(int(number.as_tuple().exponent)) <= 12) else None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def normalize_quote(
    capture: QuoteHttpCapture, symbol: str, retrieved: datetime,
) -> dict[str, object]:
    capture.__post_init__()
    payload: dict[str, object] = {
        "symbol": symbol, "status": "unavailable", "reasons": [], "claimed_quote_at": None,
        "currency_mapping": "CNY_unreviewed", "share_unit_mapping": "shares_unreviewed",
        "share_class_scope": "unverified", "model_version": MARKET_VALUE_CAPTURE_VERSION,
        "valuation_authorized": False,
    }
    fields = {"price": "f43", "total_shares": "f84", "float_shares": "f85",
              "total_market_value": "f116", "float_market_value": "f117"}
    payload.update(dict.fromkeys(fields))
    reasons = []
    if capture.error_code or capture.status_code != 200:
        payload["reasons"] = [capture.error_code or f"HTTP_{capture.status_code}"]
        return payload
    try:
        decoded = json.loads(capture.body, parse_float=Decimal, object_pairs_hook=_unique_object)
        if (not isinstance(decoded, dict) or type(decoded.get("rc")) is not int
                or decoded["rc"] != 0):
            raise ValueError("provider_status_or_schema")
        data = decoded.get("data")
        if not isinstance(data, dict) or data.get("f57") != symbol:
            raise ValueError("subject_or_schema_mismatch")
        for name, key in fields.items():
            payload[name] = _number(data.get(key))
            if payload[name] is None:
                reasons.append(f"missing_or_invalid_{name}")
        stamp = data.get("f86")
        if type(stamp) is int and 0 < stamp < 253402300800:
            quote_at = datetime.fromtimestamp(stamp, UTC)
            payload["claimed_quote_at"] = quote_at.isoformat()
            if quote_at > retrieved.astimezone(UTC):
                reasons.append("future_claimed_quote_time")
        else:
            reasons.append("missing_or_invalid_quote_time")
        price, shares, total = (payload[key] for key in (
            "price", "total_shares", "total_market_value"))
        if any(value is not None and Decimal(str(value)) <= 0
               for value in (price, shares, total)):
            reasons.append("nonpositive_price_shares_or_total_value")
        for key in ("total_shares", "float_shares"):
            value = payload[key]
            if value is not None and Decimal(str(value)) != Decimal(str(value)).to_integral_value():
                reasons.append("fractional_share_count")
        for small, large in (("float_shares", "total_shares"),
                             ("float_market_value", "total_market_value")):
            if payload[small] is not None and payload[large] is not None and (
                Decimal(str(payload[small])) > Decimal(str(payload[large]))
            ):
                reasons.append(f"{small}_exceeds_total")
        payload["status"] = "incomplete_or_inconsistent" if reasons else "observed_unqualified"
    except (ValueError, UnicodeError, ArithmeticError, RecursionError):
        payload["status"] = "invalid_response"
        reasons.append("provider_json_identity_or_schema_invalid")
    payload["reasons"] = reasons
    return payload


class EastmoneyMarketValueAdapter:
    provider_id = PROVIDER

    def __init__(self, *, download: Callable[[str], QuoteHttpCapture] = download_quote,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.download, self.clock = download, clock

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(
            PROVIDER, DATASET, (Market.CHINA_A,), ProviderCapabilityStatus.DEGRADED,
            DataTrustLevel.LOW, AvailabilityPrecision.RETRIEVAL_TIME, False, (), LIMITATIONS,
            MARKET_VALUE_CAPTURE_VERSION,
        ),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != DATASET or request.market is not Market.CHINA_A or request.parameters:
            raise ValueError("unsupported market-value snapshot request")
        url = quote_url(request.subject)
        capture = self.download(request.subject)
        retrieved = self.clock()
        require_timezone(retrieved, "retrieved_at")
        if retrieved.astimezone(UTC) < request.as_of.astimezone(UTC):
            raise ValueError("capture clock precedes request; do not retimestamp provider data")
        envelope = {"symbol": request.subject,
                    "retrieved_at": retrieved.astimezone(UTC).isoformat(),
                    "status_code": capture.status_code, "error_code": capture.error_code,
                    "body_base64": base64.b64encode(capture.body).decode("ascii"),
                    "model_version": MARKET_VALUE_CAPTURE_VERSION}
        content = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(content).hexdigest()
        identity = f"{request.subject}:current-market-value-capture"
        artifact = ProviderArtifact(
            provider_artifact_id(provider=PROVIDER, dataset=DATASET, market=request.market,
                                 subject=request.subject, source_identity=identity,
                                 source_reference=url, content_hash=digest),
            PROVIDER, DATASET, request.market, request.subject, identity, url, retrieved, retrieved,
            digest, "application/json", AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW,
            content, MARKET_VALUE_CAPTURE_VERSION,
        )
        payload = {**normalize_quote(capture, request.subject, retrieved),
                   "artifact_id": artifact.artifact_id,
                   "response_body_sha256": (sha256(capture.body).hexdigest()
                                            if capture.body else None)}
        record = ProviderEvidenceRecord(
            provider_evidence_id(provider=PROVIDER, dataset=DATASET, market=request.market,
                                 subject=request.subject, available_at=retrieved,
                                 source_reference=url, payload=payload),
            PROVIDER, DATASET, request.market, request.subject, retrieved, retrieved, url,
            payload, digest, AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW,
            tuple(item.description for item in LIMITATIONS),
        )
        return ProviderEvidenceBatch(
            PROVIDER, DATASET, request.market, retrieved, url,
            {"subject": request.subject, "normalization_version": MARKET_VALUE_CAPTURE_VERSION},
            digest, 1, (record,), LIMITATIONS, (artifact,),
        )
