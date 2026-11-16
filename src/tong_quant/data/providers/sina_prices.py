"""Retain Sina BSE raw prices without the SDK's share-count merge or forward fill."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

import pandas as pd
import py_mini_racer
import requests
from akshare.stock.cons import hk_js_decode

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
from tong_quant.version import SINA_PRICE_OBSERVATION_VERSION

SINA_BSE_DATASET = "bse_daily_price_observations"
MAX_BYTES = 2 * 1024 * 1024
LIMITATIONS = (
    EvidenceLimitation("unverified_sina_price_observation",
                      "Public Sina source, not exchange or independently calibrated prices",
                      DataTrustLevel.LOW),
    EvidenceLimitation("sina_retrieval_time_only",
                      "Current history snapshot; original revisions and publication unknown",
                      DataTrustLevel.LOW),
    EvidenceLimitation("sina_price_basis_and_units_unverified",
                      "Native prices decoded without adjustment, fill, rounding or deduplication; "
                      "basis, volume units, code history and session completeness need review",
                      DataTrustLevel.LOW),
)


def _download(symbol: str) -> bytes:
    url = f"https://finance.sina.com.cn/realstock/company/bj{symbol}/hisdata_klc2/klc_kl.js"
    with requests.get(url, timeout=5, allow_redirects=False, stream=True) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Sina response must not redirect")
        content = bytearray()
        for chunk in response.iter_content(65536):
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise ValueError("Sina payload exceeds size bound")
        return bytes(content)


def _decode(content: bytes, symbol: str) -> list[dict[str, object]]:
    # Parse the assignment as data; only the installed, fixed SDK decoder is evaluated.
    match = re.fullmatch(
        rf'\s*var\s+KLC_(?:K2|KL)_bj{symbol}\s*=\s*("[A-Za-z0-9+/=]+")'
        r'\s*;?\s*(?:/\*[\s\S]*?\*/\s*)?',
        content.decode("ascii"),
    )
    if match is None:
        raise ValueError("Sina price assignment identity/schema mismatch")
    with py_mini_racer.MiniRacer() as runtime:
        runtime.eval(hk_js_decode, timeout=2000)
        result = runtime.call("d", json.loads(match[1]), timeout=2000,
                              max_memory=64 * 1024 * 1024)
    if not isinstance(result, list) or not all(isinstance(row, dict) for row in result):
        raise ValueError("Sina decoder did not return price rows")
    return result


class SinaBsePriceObservationAdapter:
    provider_id = "sina_via_akshare_decoder"

    def __init__(self, *, download: Callable[[str], bytes] = _download,
                 decode: Callable[[bytes, str], list[dict[str, object]]] = _decode,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.download, self.decode, self.clock = download, decode, clock

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (ProviderDatasetCapability(
            self.provider_id, SINA_BSE_DATASET, (Market.CHINA_A,),
            ProviderCapabilityStatus.DEGRADED,
            DataTrustLevel.LOW, AvailabilityPrecision.RETRIEVAL_TIME, False,
            ("start_date", "end_date"), LIMITATIONS, SINA_PRICE_OBSERVATION_VERSION,
        ),)

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        symbol = request.subject
        if (request.dataset != SINA_BSE_DATASET or request.market is not Market.CHINA_A
                or len(symbol) != 6 or not symbol.isascii() or not symbol.isdigit()
                or not symbol.startswith(("920", "4", "8"))
                or set(request.parameters) != {"start_date", "end_date"}):
            raise ValueError("explicit BSE symbol and date range required")
        if any(len(value) != 8 or not value.isascii() or not value.isdigit()
               for value in request.parameters.values()):
            raise ValueError("Sina query dates require YYYYMMDD")
        start, end = (datetime.strptime(request.parameters[key], "%Y%m%d").date()
                      for key in ("start_date", "end_date"))
        if start > end or end > request.as_of.astimezone(UTC).date():
            raise ValueError("Sina date range reversed or future")
        content = self.download(symbol)
        if not content or len(content) > MAX_BYTES:
            raise ValueError("Sina payload empty or exceeds size bound")
        decoded = self.decode(content, symbol)
        available = max(self.clock(), request.as_of)
        digest = sha256(content).hexdigest()
        url = f"https://finance.sina.com.cn/realstock/company/bj{symbol}/hisdata_klc2/klc_kl.js"
        identity = f"bj{symbol}:unadjusted-native-price-series"
        artifact = ProviderArtifact(
            provider_artifact_id(provider=self.provider_id, dataset=SINA_BSE_DATASET,
                                 market=request.market, subject=symbol, source_identity=identity,
                                 source_reference=url, content_hash=digest),
            self.provider_id, SINA_BSE_DATASET, request.market, symbol, identity, url,
            available, available, digest, "application/javascript",
            AvailabilityPrecision.RETRIEVAL_TIME, DataTrustLevel.LOW, content,
            SINA_PRICE_OBSERVATION_VERSION,
        )
        records = []
        dates = set()
        for row in decoded:
            if "date" not in row:
                raise ValueError("Sina row missing date")
            if not isinstance(row["date"], (str, datetime)):
                raise ValueError("Sina date must be an explicit timestamp")
            timestamp = pd.Timestamp(row["date"])
            if pd.isna(timestamp):
                raise ValueError("Sina date invalid")
            if timestamp != timestamp.normalize():
                raise ValueError("Sina daily timestamp must be midnight")
            observed_date = timestamp.date()
            if observed_date in dates:
                raise ValueError("Sina duplicate date must not be silently removed")
            dates.add(observed_date)
            if not start <= observed_date <= end:
                continue
            numbers = {}
            for name in ("open", "high", "low", "close", "volume", "amount"):
                value = row.get(name)
                if value is None or isinstance(value, bool):
                    raise ValueError("Sina numeric value missing or invalid")
                number = Decimal(str(value))
                if not number.is_finite() or number < 0 or (
                    name in {"open", "high", "low", "close"} and number == 0
                ):
                    raise ValueError("Sina numeric value invalid")
                numbers[name] = number
            if (numbers["low"] > min(numbers["open"], numbers["close"])
                    or numbers["high"] < max(numbers["open"], numbers["close"])
                    or numbers["low"] > numbers["high"]):
                raise ValueError("Sina OHLC inconsistent")
            payload = {"symbol": symbol, "date": observed_date.isoformat(),
                       **{name: str(value) for name, value in numbers.items()},
                       "artifact_id": artifact.artifact_id,
                       "decoder_sha256": sha256(hk_js_decode.encode()).hexdigest(),
                       "forward_filled": False, "rounded": False, "deduplicated": False,
                       "canonical_bar_authorized": False,
                       "model_version": SINA_PRICE_OBSERVATION_VERSION}
            records.append(ProviderEvidenceRecord(
                provider_evidence_id(provider=self.provider_id, dataset=SINA_BSE_DATASET,
                                     market=request.market, subject=symbol, available_at=available,
                                     source_reference=url, payload=payload),
                self.provider_id, SINA_BSE_DATASET, request.market, symbol,
                available, available, url, payload, digest, AvailabilityPrecision.RETRIEVAL_TIME,
                DataTrustLevel.LOW, tuple(item.description for item in LIMITATIONS),
            ))
        return ProviderEvidenceBatch(
            self.provider_id, SINA_BSE_DATASET, request.market, available, url,
            {**request.parameters, "subject": symbol,
             "normalization_version": SINA_PRICE_OBSERVATION_VERSION},
            digest, len(decoded), tuple(records), LIMITATIONS, (artifact,),
        )
