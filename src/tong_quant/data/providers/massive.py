import json
import os
import ssl
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
from time import sleep
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from zoneinfo import ZoneInfo

import certifi

from tong_quant.core.exceptions import (
    ConfigurationError,
    DataProviderError,
    DataProviderUnavailableError,
)
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_evidence_id,
)
from tong_quant.data.providers.yahoo import YAHOO_DAILY_BARS_DATASET
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

MASSIVE_PROVIDER_ID = "massive"
MASSIVE_API_ROOT = "https://api.massive.com"
_MASSIVE_HOST = "api.massive.com"
_ALLOWED_PATH_PREFIXES = (
    "/v2/aggs/ticker/",
    "/stocks/v1/dividends",
    "/stocks/v1/splits",
)
_NEW_YORK = ZoneInfo("America/New_York")


class MassiveMarketDataClient(Protocol):
    def aggregates(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]: ...

    def dividends(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]: ...

    def splits(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]: ...


@dataclass(slots=True)
class MassiveHttpClient:
    api_key: str = field(repr=False)
    timeout_seconds: float = 20
    max_attempts: int = 3
    max_pages: int = 5
    sleeper: Callable[[float], None] = sleep

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ConfigurationError("MASSIVE_API_KEY is required for Massive access")
        if self.timeout_seconds <= 0 or self.max_attempts < 1 or self.max_pages < 1:
            raise ValueError("Massive timeout, attempts, and pages must be positive")

    @classmethod
    def from_environment(cls) -> "MassiveHttpClient":
        api_key = os.getenv("MASSIVE_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError("MASSIVE_API_KEY is not configured")
        return cls(api_key=api_key)

    def aggregates(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        return self._get_all(
            f"/v2/aggs/ticker/{quote(symbol, safe='')}/range/1/day/"
            f"{start_date}/{end_date}",
            {"adjusted": "false", "sort": "asc", "limit": "50000"},
        )

    def dividends(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        return self._get_all(
            "/stocks/v1/dividends",
            {
                "ticker": symbol,
                "ex_dividend_date.gte": start_date,
                "ex_dividend_date.lte": end_date,
                "sort": "ex_dividend_date.asc",
                "limit": "5000",
            },
        )

    def splits(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        return self._get_all(
            "/stocks/v1/splits",
            {
                "ticker": symbol,
                "execution_date.gte": start_date,
                "execution_date.lte": end_date,
                "sort": "execution_date.asc",
                "limit": "5000",
            },
        )

    def _get_all(
        self,
        path: str,
        parameters: dict[str, str],
    ) -> dict[str, object]:
        url = f"{MASSIVE_API_ROOT}{path}?{urlencode(parameters)}"
        pages: list[dict[str, object]] = []
        results: list[object] = []
        for _page_number in range(1, self.max_pages + 1):
            payload = self._request_json(url)
            pages.append(payload)
            page_results = payload.get("results", [])
            if not isinstance(page_results, list):
                raise DataProviderError("Massive results payload is malformed")
            results.extend(page_results)
            next_url = payload.get("next_url")
            if not next_url:
                combined = dict(pages[0])
                combined["results"] = results
                combined["tong_quant_page_count"] = len(pages)
                return combined
            url = _safe_next_url(str(next_url))
        raise DataProviderError("Massive pagination exceeded the configured bound")

    def _request_json(self, url: str) -> dict[str, object]:
        _validate_massive_url(url)
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "TongQuant/0.8 research-data",
            },
        )
        context = ssl.create_default_context(cafile=certifi.where())
        opener = build_opener(
            HTTPSHandler(context=context),
            _MassiveRedirectHandler(),
        )
        last_reason = "transport_unavailable"
        for attempt in range(1, self.max_attempts + 1):
            try:
                with opener.open(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    resolved_url = response.geturl()
                    _validate_massive_url(resolved_url)
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise DataProviderError("Massive response is not a JSON object")
                status = str(payload.get("status", "")).upper()
                if status and status not in {"OK", "DELAYED"}:
                    raise DataProviderError("Massive response reports a provider error")
                return payload
            except HTTPError as error:
                if error.code == 401:
                    raise DataProviderUnavailableError(
                        MASSIVE_PROVIDER_ID,
                        "authentication_failed",
                    ) from error
                if error.code == 403:
                    raise DataProviderUnavailableError(
                        MASSIVE_PROVIDER_ID,
                        "permission_restricted",
                    ) from error
                if error.code == 429:
                    last_reason = "rate_limited"
                elif error.code >= 500:
                    last_reason = "provider_server_error"
                else:
                    raise DataProviderError(
                        f"Massive request failed with HTTP {error.code}"
                    ) from error
            except (TimeoutError, URLError, OSError):
                last_reason = "transport_unavailable"
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise DataProviderError("Massive response is not valid JSON") from error
            if attempt < self.max_attempts:
                self.sleeper(float(attempt))
        raise DataProviderUnavailableError(MASSIVE_PROVIDER_ID, last_reason)


@dataclass(slots=True)
class MassiveEvidenceAdapter:
    client: MassiveMarketDataClient
    clock: Callable[[], datetime]
    provider_id: str = field(init=False, default=MASSIVE_PROVIDER_ID)

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset=YAHOO_DAILY_BARS_DATASET,
                markets=(Market.US,),
                status=ProviderCapabilityStatus.DEGRADED,
                trust_level=DataTrustLevel.LOW,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                historical_continuity=False,
                required_parameters=("start_date", "end_date"),
                limitations=_massive_limitations(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != YAHOO_DAILY_BARS_DATASET:
            raise ValueError("Massive adapter only supports global daily bar evidence")
        if request.market is not Market.US:
            raise ValueError("Massive daily bar calibration currently supports US only")
        start_date = request.parameters["start_date"]
        end_date = request.parameters["end_date"]
        if date.fromisoformat(end_date) < date.fromisoformat(start_date):
            raise ValueError("Massive end date cannot precede start date")
        bars = self.client.aggregates(
            request.subject,
            start_date=start_date,
            end_date=end_date,
        )
        if bars.get("adjusted") is not False:
            raise ValueError("Massive aggregate response is not explicitly unadjusted")
        response_symbol = str(bars.get("ticker", "")).strip()
        if response_symbol and response_symbol != request.subject:
            raise DataProviderError("Massive aggregate ticker does not match the request")
        dividends = self.client.dividends(
            request.subject,
            start_date=start_date,
            end_date=end_date,
        )
        splits = self.client.splits(
            request.subject,
            start_date=start_date,
            end_date=end_date,
        )
        retrieved_at = self.clock()
        raw_document = {"aggregates": bars, "dividends": dividends, "splits": splits}
        raw_hash = sha256(
            json.dumps(raw_document, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        actions = _corporate_actions(dividends, splits, request.subject)
        rows = _results(bars, "aggregates")
        records: list[ProviderEvidenceRecord] = []
        aligned_actions: set[str] = set()
        for row in rows:
            timestamp = row.get("t")
            if not isinstance(timestamp, int | float):
                raise DataProviderError("Massive aggregate timestamp is malformed")
            observed_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            if observed_at > request.as_of:
                continue
            session_date = observed_at.astimezone(_NEW_YORK).date().isoformat()
            session_actions = actions.get(session_date, ())
            if session_actions:
                aligned_actions.add(session_date)
            payload: dict[str, object] = {
                "session_date": session_date,
                "open": row.get("o"),
                "high": row.get("h"),
                "low": row.get("l"),
                "close": row.get("c"),
                "volume": row.get("v"),
                "price_basis": "unadjusted",
                "corporate_actions": list(session_actions),
                "currency": "USD",
                "exchange": "US consolidated",
                "timezone": "America/New_York",
            }
            source_reference = (
                f"{MASSIVE_API_ROOT}/v2/aggs/ticker/"
                f"{quote(request.subject, safe='')}/range/1/day/{start_date}/{end_date}"
            )
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject=request.subject,
                        available_at=retrieved_at,
                        source_reference=source_reference,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject=request.subject,
                    observed_at=observed_at,
                    available_at=retrieved_at,
                    retrieved_at=retrieved_at,
                    source_reference=source_reference,
                    payload=payload,
                    raw_data_hash=raw_hash,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.LOW,
                    limitations=tuple(
                        item.description for item in _massive_limitations()
                    ),
                )
            )
        limitations = list(_massive_limitations())
        unaligned = sorted(set(actions) - aligned_actions)
        if unaligned:
            limitations.append(
                EvidenceLimitation(
                    code="massive_unaligned_corporate_actions",
                    description=(
                        f"{len(unaligned)} Massive corporate-action dates did not align "
                        "to a returned aggregate session"
                    ),
                    trust_level=DataTrustLevel.LOW,
                )
            )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=retrieved_at,
            source="massive:aggregates+dividends+splits",
            parameters={"subject": request.subject, **request.parameters},
            raw_data_hash=raw_hash,
            raw_record_count=len(rows),
            records=tuple(records),
            limitations=tuple(limitations),
        )


def _massive_limitations() -> tuple[EvidenceLimitation, ...]:
    return (
        EvidenceLimitation(
            code="massive_optional_calibration_provider",
            description=(
                "Massive is optional calibration evidence and is not trusted by default"
            ),
            trust_level=DataTrustLevel.LOW,
        ),
        EvidenceLimitation(
            code="massive_retrieval_time_only",
            description=(
                "Massive observations are known to Tong Quant only at retrieval time"
            ),
            trust_level=DataTrustLevel.LOW,
        ),
        EvidenceLimitation(
            code="massive_continuity_unverified",
            description=(
                "Massive historical corrections and symbol continuity require a "
                "longitudinal baseline"
            ),
            trust_level=DataTrustLevel.UNKNOWN,
        ),
    )


def _corporate_actions(
    dividends: dict[str, object],
    splits: dict[str, object],
    subject: str,
) -> dict[str, tuple[str, ...]]:
    actions: defaultdict[str, set[str]] = defaultdict(set)
    for row in _results(dividends, "dividends"):
        _validate_action_subject(row, subject)
        action_date = str(row.get("ex_dividend_date", "")).strip()
        if action_date:
            actions[action_date].add("dividend")
    for row in _results(splits, "splits"):
        _validate_action_subject(row, subject)
        action_date = str(row.get("execution_date", "")).strip()
        if action_date:
            actions[action_date].add("split")
    return {key: tuple(sorted(value)) for key, value in actions.items()}


def _results(payload: dict[str, object], dataset: str) -> list[dict[str, object]]:
    rows = payload.get("results", [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise DataProviderError(f"Massive {dataset} results are malformed")
    return rows


def _safe_next_url(url: str) -> str:
    _validate_massive_url(url)
    parsed = urlparse(url)
    safe_query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() != "apikey"
        ]
    )
    return urlunparse(parsed._replace(query=safe_query))


def _validate_massive_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != _MASSIVE_HOST
        or not any(parsed.path.startswith(prefix) for prefix in _ALLOWED_PATH_PREFIXES)
    ):
        raise ValueError("Massive URL is outside the approved official scope")


def _validate_action_subject(row: dict[str, object], subject: str) -> None:
    ticker = str(row.get("ticker", "")).strip()
    if ticker and ticker != subject:
        raise DataProviderError("Massive corporate action ticker does not match request")


class _MassiveRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        _validate_massive_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


__all__ = [
    "MASSIVE_API_ROOT",
    "MASSIVE_PROVIDER_ID",
    "MassiveEvidenceAdapter",
    "MassiveHttpClient",
    "MassiveMarketDataClient",
]
