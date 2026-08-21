import json
import ssl
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, tzinfo
from hashlib import sha256
from time import sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import certifi

from tong_quant.core.exceptions import DataProviderUnavailableError
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_evidence_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

YAHOO_DAILY_BARS_DATASET = "global_daily_bars"


class YahooChartClient(Protocol):
    def chart(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]: ...


@dataclass(slots=True)
class YahooChartHttpClient:
    timeout_seconds: float = 15
    max_attempts: int = 3
    sleeper: Callable[[float], None] = sleep

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.max_attempts <= 0:
            raise ValueError("Yahoo HTTP timeout and attempts must be positive")

    def chart(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        parameters = {
            "period1": str(_epoch(start_date)),
            "period2": str(_epoch(end_date, end_of_range=True)),
            "interval": "1d",
            "events": "div,splits,capitalGains",
            "includeAdjustedClose": "false",
        }
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?"
            f"{urlencode(parameters)}"
        )
        request = Request(url, headers={"User-Agent": "TongQuant/0.8 research-data"})
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        last_reason = "transport_unavailable"
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urlopen(  # noqa: S310
                    request,
                    timeout=self.timeout_seconds,
                    context=ssl_context,
                ) as response:
                    raw = response.read()
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Yahoo chart response is not an object")
                return payload
            except HTTPError as error:
                last_reason = f"http_{error.code}"
            except (TimeoutError, URLError, OSError) as error:
                last_reason = type(error).__name__
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Yahoo chart response is not valid JSON") from error
            if attempt < self.max_attempts:
                self.sleeper(float(attempt))
        raise DataProviderUnavailableError("yahoo_finance", last_reason)


@dataclass(slots=True)
class YahooFinanceEvidenceAdapter:
    client: YahooChartClient
    clock: Callable[[], datetime]
    provider_id: str = "yahoo_finance"

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset=YAHOO_DAILY_BARS_DATASET,
                markets=(Market.US, Market.HONG_KONG, Market.MALAYSIA),
                status=ProviderCapabilityStatus.DEGRADED,
                trust_level=DataTrustLevel.LOW,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                historical_continuity=False,
                required_parameters=("start_date", "end_date"),
                limitations=_yahoo_limitations(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != YAHOO_DAILY_BARS_DATASET:
            raise ValueError("Yahoo adapter only supports global daily bar evidence")
        raw_payload = self.client.chart(
            request.subject,
            start_date=request.parameters["start_date"],
            end_date=request.parameters["end_date"],
        )
        retrieved_at = self.clock()
        encoded = json.dumps(
            raw_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        raw_hash = sha256(encoded).hexdigest()
        result = _chart_result(raw_payload)
        timestamps = _timestamps(result)
        quote_rows = _quote_rows(result)
        meta = result.get("meta")
        metadata = meta if isinstance(meta, dict) else {}
        exchange_timezone, timezone_limitation = _exchange_timezone(metadata)
        limitations = list(_yahoo_limitations())
        if timezone_limitation is not None:
            limitations.append(timezone_limitation)
        corporate_actions = _corporate_actions_by_session(
            result,
            exchange_timezone,
        )
        records = []
        for index, timestamp in enumerate(timestamps):
            observed_at = datetime.fromtimestamp(timestamp, tz=UTC)
            if observed_at > request.as_of:
                continue
            session_date = observed_at.astimezone(exchange_timezone).date().isoformat()
            payload = {
                "session_date": session_date,
                "open": _at(quote_rows, "open", index),
                "high": _at(quote_rows, "high", index),
                "low": _at(quote_rows, "low", index),
                "close": _at(quote_rows, "close", index),
                "volume": _at(quote_rows, "volume", index),
                "price_basis": "unadjusted",
                "corporate_actions": list(corporate_actions.get(session_date, ())),
                "currency": metadata.get("currency"),
                "exchange": metadata.get("exchangeName"),
                "timezone": metadata.get("exchangeTimezoneName"),
            }
            source_reference = f"https://finance.yahoo.com/quote/{quote(request.subject)}/history"
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject=request.subject,
                        available_at=retrieved_at,
                        source_reference=source_reference,
                        payload={"timestamp": observed_at.isoformat(), **payload},
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject=request.subject,
                    observed_at=observed_at,
                    available_at=retrieved_at,
                    retrieved_at=retrieved_at,
                    source_reference=source_reference,
                    payload={"timestamp": observed_at.isoformat(), **payload},
                    raw_data_hash=raw_hash,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.LOW,
                    limitations=tuple(
                        limitation.description for limitation in limitations
                    ),
                )
            )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=retrieved_at,
            source="yahoo_finance:chart_v8_unofficial",
            parameters={"subject": request.subject, **request.parameters},
            raw_data_hash=raw_hash,
            raw_record_count=len(timestamps),
            records=tuple(records),
            limitations=tuple(limitations),
        )


def _yahoo_limitations() -> tuple[EvidenceLimitation, ...]:
    return (
        EvidenceLimitation(
            code="yahoo_unofficial_interface",
            description="Yahoo Finance chart access is unofficial and may change without notice",
            trust_level=DataTrustLevel.LOW,
        ),
        EvidenceLimitation(
            code="yahoo_retrieval_time_only",
            description=(
                "Historical bars are known to Tong Quant only at retrieval time and are "
                "not authoritative PIT evidence"
            ),
            trust_level=DataTrustLevel.LOW,
        ),
        EvidenceLimitation(
            code="yahoo_continuity_unverified",
            description=(
                "Delistings, symbol changes, revisions, and historical continuity are unverified"
            ),
            trust_level=DataTrustLevel.UNKNOWN,
        ),
    )


def _epoch(value: str, *, end_of_range: bool = False) -> int:
    parsed = date.fromisoformat(value)
    point = datetime.combine(parsed, time.min, tzinfo=UTC)
    if end_of_range:
        return int(point.timestamp()) + 86400
    return int(point.timestamp())


def _chart_result(payload: dict[str, object]) -> dict[str, object]:
    chart = payload.get("chart")
    if not isinstance(chart, dict):
        raise ValueError("Yahoo chart payload is missing chart data")
    error = chart.get("error")
    if error:
        raise DataProviderUnavailableError(
            "yahoo_finance",
            "provider_response_error",
        )
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("Yahoo chart payload has no result")
    return results[0]


def _timestamps(result: dict[str, object]) -> tuple[int, ...]:
    values = result.get("timestamp")
    if not isinstance(values, list):
        return ()
    return tuple(int(value) for value in values if isinstance(value, int | float))


def _quote_rows(result: dict[str, object]) -> dict[str, object]:
    indicators = result.get("indicators")
    if not isinstance(indicators, dict):
        return {}
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or not quotes or not isinstance(quotes[0], dict):
        return {}
    return quotes[0]


def _at(values: dict[str, object], field: str, index: int) -> object:
    series = values.get(field)
    if not isinstance(series, list) or index >= len(series):
        return None
    value = series[index]
    return value if isinstance(value, int | float | str) or value is None else str(value)


def _exchange_timezone(
    metadata: dict[str, object],
) -> tuple[tzinfo, EvidenceLimitation | None]:
    name = str(metadata.get("exchangeTimezoneName", "")).strip()
    try:
        return ZoneInfo(name), None
    except (ZoneInfoNotFoundError, ValueError):
        return UTC, EvidenceLimitation(
            code="yahoo_exchange_timezone_unavailable",
            description=(
                "Yahoo exchange timezone was missing or invalid; UTC session dates "
                "were retained with reduced confidence"
            ),
            trust_level=DataTrustLevel.UNKNOWN,
        )


def _corporate_actions_by_session(
    result: dict[str, object],
    exchange_timezone: tzinfo,
) -> dict[str, tuple[str, ...]]:
    events = result.get("events")
    if not isinstance(events, dict):
        return {}
    normalized_names = {
        "dividends": "dividend",
        "splits": "split",
        "capitalGains": "capital_gain",
    }
    actions: defaultdict[str, set[str]] = defaultdict(set)
    for provider_name, normalized_name in normalized_names.items():
        values = events.get(provider_name)
        if not isinstance(values, dict):
            continue
        for item in values.values():
            if not isinstance(item, dict):
                continue
            timestamp = item.get("date")
            if not isinstance(timestamp, int | float):
                continue
            session = (
                datetime.fromtimestamp(timestamp, tz=UTC)
                .astimezone(exchange_timezone)
                .date()
                .isoformat()
            )
            actions[session].add(normalized_name)
    return {key: tuple(sorted(value)) for key, value in actions.items()}


__all__ = [
    "YAHOO_DAILY_BARS_DATASET",
    "YahooChartClient",
    "YahooChartHttpClient",
    "YahooFinanceEvidenceAdapter",
]
