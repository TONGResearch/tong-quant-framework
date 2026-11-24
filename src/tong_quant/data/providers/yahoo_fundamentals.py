"""Native annual observations, deliberately outside canonical FundamentalFact semantics."""

import json
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

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
from tong_quant.data.providers.yahoo_identity import TIMEZONES, validate_yahoo_equity_subject
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION

PROVIDER = "yahoo_finance"
DATASET = "global_native_fundamental_snapshot"
MAX_BYTES = 1024 * 1024
NATIVE_METRICS = (
    "annualTotalRevenue", "annualNetIncome", "annualOperatingCashFlow", "annualTotalAssets",
    "annualTotalLiabilitiesNetMinorityInterest", "annualStockholdersEquity", "annualTotalDebt",
)
LIMITATIONS = (
    "Decoded unofficial Yahoo snapshot; no independent issuer or accounting verification",
    "Availability is retrieval time; publication dates and issuer revisions are unknown",
    "asOfDate is a provider-labelled period end, never publication or historical availability",
    "Native names/currency/raw amounts are not admitted canonical financial definitions",
    "Bank, securities, insurance and nonfinancial scoring policies remain unadmitted",
    "No FX, PE/PB, ROE/ROIC, historical replay, InvestmentScore or trading authorization",
)


def validate_fundamental_request(request: ProviderDatasetRequest) -> None:
    request.__post_init__()
    validate_yahoo_equity_subject(request.market, request.subject)
    if request.dataset != DATASET or set(request.parameters) != {"start_date", "end_date"}:
        raise ValueError("native fundamental snapshot requires explicit start and end dates")
    start = date.fromisoformat(request.parameters["start_date"])
    end = date.fromisoformat(request.parameters["end_date"])
    if start > end or (end - start).days > 15000:
        raise ValueError("native fundamental date range is reversed or exceeds bound")


@dataclass(frozen=True, slots=True)
class YahooFundamentalCapture:
    payload: dict[str, Any] | None
    error_code: str = ""

    def __post_init__(self) -> None:
        if self.payload is not None and not isinstance(self.payload, dict):
            raise ValueError("native fundamental payload must be an object")
        if (self.payload is None) != bool(self.error_code) or self.error_code not in {
            "", "http_401", "http_403", "http_404", "http_429", "http_error",
            "network_unavailable", "invalid_decoded_response",
        }:
            raise ValueError("invalid native fundamental capture state")
        reject_sensitive_structure(self.payload, path="native_fundamental_capture")
        if len(json.dumps(self.payload, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode()) > MAX_BYTES:
            raise ValueError("native fundamental capture exceeds byte bound")


def fundamental_url(request: ProviderDatasetRequest) -> str:
    validate_fundamental_request(request)
    start = date.fromisoformat(request.parameters["start_date"])
    end = date.fromisoformat(request.parameters["end_date"])
    return ("https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
        + quote(request.subject, safe="") + "?" + urlencode({"symbol": request.subject,
            "type": ",".join(NATIVE_METRICS),
            "period1": int(datetime.combine(start, time.min, tzinfo=UTC).timestamp()),
            "period2": int(datetime.combine(end, time.min, tzinfo=UTC).timestamp()) + 86400}))


def download_fundamentals(request: ProviderDatasetRequest) -> YahooFundamentalCapture:
    url = fundamental_url(request)
    error_code = "network_unavailable"
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers={"User-Agent": "TongQuant/0.8 research-data"}),
                         timeout=8, context=ssl.create_default_context(
                             cafile=certifi.where())) as response:  # noqa: S310
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return YahooFundamentalCapture(None, "invalid_decoded_response")
            return YahooFundamentalCapture(json.loads(raw.decode("utf-8")))
        except HTTPError as error:
            error_code = (f"http_{error.code}" if error.code in {401, 403, 404, 429}
                          else "http_error")
            if error.code < 500 and error.code != 429:
                break
        except (TimeoutError, URLError, OSError):
            error_code = "network_unavailable"
        except (UnicodeDecodeError, ValueError):
            return YahooFundamentalCapture(None, "invalid_decoded_response")
        if attempt == 0:
            sleep(1)
    return YahooFundamentalCapture(None, error_code)


def _native_row(metric: str, index: int, row: object, captured: datetime,
                request: ProviderDatasetRequest) -> dict[str, Any]:
    output: dict[str, Any] = {"native_metric": metric, "row_index": index,
        "period_end": None, "period_start": None, "period_type": None, "currency": None,
        "value": None, "published_at": None, "issuer_revision": None,
        "available_at": captured.astimezone(UTC).isoformat(), "status": "INVALID_NATIVE_ROW",
        "unit": "provider_reported_raw", "accounting_scope": "UNVERIFIED"}
    try:
        if not isinstance(row, dict):
            raise ValueError("not an object")
        period = date.fromisoformat(row["asOfDate"])
        output["period_end"] = period.isoformat()
        if (period > captured.astimezone(UTC).date()
                or not date.fromisoformat(request.parameters["start_date"]) <= period <= (
                    date.fromisoformat(request.parameters["end_date"]))):
            output["status"] = "FUTURE_OR_OUT_OF_RANGE_PERIOD"
            return output
        if row.get("periodType") != "12M":
            output["status"] = "UNSUPPORTED_PERIOD_TYPE"
            return output
        output["period_type"] = "12M"
        currency = row.get("currencyCode")
        if not isinstance(currency, str) or re.fullmatch(r"[A-Z]{3}", currency) is None:
            output["status"] = "INVALID_CURRENCY"
            return output
        output["currency"] = currency
        native = row["reportedValue"]["raw"]
        if type(native) not in (float, int):
            raise ValueError("native value is not numeric")
        value = Decimal(str(native))
        if not value.is_finite() or abs(value) > Decimal("1e24"):
            raise ValueError("invalid native numeric value")
        output.update(value=str(value), status="OBSERVED_UNQUALIFIED")
    except (ValueError, KeyError, TypeError, ArithmeticError):
        pass
    return output


def native_fundamentals(capture: YahooFundamentalCapture, request: ProviderDatasetRequest,
                        captured: datetime) -> dict[str, Any]:
    validate_fundamental_request(request)
    capture.__post_init__()
    require_timezone(captured, "native fundamental capture")
    output: dict[str, Any] = {"status": capture.error_code or "invalid_response",
        "requested_native_metrics": NATIVE_METRICS, "observations": [], "latest": {},
        "usable_native_metric_count": 0,
        "missing_metrics": list(NATIVE_METRICS), "reporting_currencies": [],
        "accounting_definitions_admitted": False, "publication_dates_available": False,
        "revision_history_available": False, "financial_scoring_authorized": False}
    if capture.payload is None:
        return output
    try:
        body = capture.payload["timeseries"]
        if not isinstance(body, dict) or body.get("error") is not None:
            raise ValueError("native response error")
        results = body["result"]
        if not isinstance(results, list) or len(results) > len(NATIVE_METRICS):
            raise ValueError("invalid native metric groups")
        groups = {}
        for group in results:
            meta = group["meta"]
            kinds = meta["type"]
            if (meta["symbol"] != [request.subject] or not isinstance(kinds, list)
                    or len(kinds) != 1 or kinds[0] not in NATIVE_METRICS or kinds[0] in groups):
                raise ValueError("wrong or duplicate native identity")
            metric = kinds[0]
            rows = group.get(metric, [])
            if not isinstance(rows, list) or len(rows) > 64:
                raise ValueError("invalid native observation list")
            groups[metric] = [_native_row(metric, index, row, captured, request)
                              for index, row in enumerate(rows)]
        observations = [row for metric in NATIVE_METRICS for row in groups.get(metric, [])]
        latest = {}
        for metric in NATIVE_METRICS:
            rows = groups.get(metric, [])
            if not rows:
                latest[metric] = {"status": "MISSING", "value": None}
            elif any(row["period_end"] is None for row in rows):
                latest[metric] = {"status": "AMBIGUOUS_PERIOD", "value": None}
            else:
                newest = max(row["period_end"] for row in rows)
                selected = [row for row in rows if row["period_end"] == newest]
                latest[metric] = selected[0] if len(selected) == 1 else {
                    "status": "AMBIGUOUS_PERIOD", "period_end": newest, "value": None}
        missing = [metric for metric in NATIVE_METRICS if not groups.get(metric)]
        complete = all(row["status"] == "OBSERVED_UNQUALIFIED" for row in latest.values())
        usable = sum(row["status"] == "OBSERVED_UNQUALIFIED" for row in latest.values())
        output.update(status="observed_unqualified" if complete else (
            "partial_unqualified" if usable else (
                "insufficient_native_data" if observations else "no_observations")),
            observations=observations, latest=latest, missing_metrics=missing,
            usable_native_metric_count=usable,
            reporting_currencies=sorted({row["currency"] for row in observations
                                         if row["currency"] is not None}))
    except (ValueError, KeyError, TypeError, ArithmeticError):
        pass
    return output


@dataclass(slots=True)
class YahooFundamentalSnapshotAdapter:
    download: Callable[[ProviderDatasetRequest], YahooFundamentalCapture] = download_fundamentals
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(PROVIDER, DATASET, tuple(TIMEZONES),
            ProviderCapabilityStatus.DEGRADED, DataTrustLevel.LOW,
            AvailabilityPrecision.RETRIEVAL_TIME, False, ("start_date", "end_date"),
            tuple(EvidenceLimitation(f"native_financial_{index}", text, DataTrustLevel.LOW)
                  for index, text in enumerate(LIMITATIONS)), GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        validate_fundamental_request(request)
        capture = self.download(request)
        capture.__post_init__()
        captured = self.clock()
        require_timezone(captured, "native fundamental capture")
        if captured.utcoffset() != timedelta(0):
            raise ValueError("native fundamental capture clock must use UTC")
        content = json.dumps({"model_version": GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION,
            "market": request.market.value, "subject": request.subject,
            "parameters": request.parameters, "retrieved_at": captured.astimezone(UTC).isoformat(),
            "decoded_payload": capture.payload, "error_code": capture.error_code},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest = sha256(content).hexdigest()
        reference = fundamental_url(request)
        identity = f"{request.subject}:{GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION}"
        artifact_id = provider_artifact_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, source_identity=identity,
            source_reference=reference, content_hash=digest)
        artifact = ProviderArtifact(artifact_id, PROVIDER, DATASET, request.market, request.subject,
            identity, reference, captured, captured, digest, "application/json",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION)
        normalized = native_fundamentals(capture, request, captured)
        # Keep persisted payload types identical to their JSON read-side reconstruction.
        payload = json.loads(json.dumps({**normalized, "artifact_id": artifact_id}, sort_keys=True))
        record = ProviderEvidenceRecord(provider_evidence_id(provider=PROVIDER, dataset=DATASET,
            market=request.market, subject=request.subject, available_at=captured,
            source_reference=reference, payload=payload), PROVIDER, DATASET, request.market,
            request.subject, captured, captured, reference, payload, digest,
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, LIMITATIONS)
        return ProviderEvidenceBatch(PROVIDER, DATASET, request.market, captured, reference,
            {"subject": request.subject, **request.parameters,
             "normalization_version": GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION}, digest, 1, (record,),
            self.capabilities()[0].limitations, (artifact,))
