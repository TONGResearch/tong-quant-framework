"""Exact economic-row identity; a hash match is not a provider trust upgrade."""

import json
from datetime import UTC
from hashlib import sha256

from tong_quant.data.providers.contracts import ProviderEvidenceRecord, provider_artifact_id
from tong_quant.domain.models import Bar
from tong_quant.version import DAILY_BAR_EVIDENCE_VERSION


def daily_bar_content(bar: Bar) -> dict[str, object]:
    values = (bar.open, bar.high, bar.low, bar.close, bar.volume, bar.turnover)
    if any(value is not None and not value.is_finite() for value in values):
        raise ValueError("price evidence requires finite economic values")
    return {
        "version": DAILY_BAR_EVIDENCE_VERSION,
        "symbol": bar.instrument.symbol,
        "market": bar.instrument.market.value,
        "asset_type": bar.instrument.asset_type.value,
        "currency": bar.instrument.currency,
        "timestamp": bar.timestamp.astimezone(UTC).isoformat(),
        "available_at": bar.available_at.astimezone(UTC).isoformat(),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
        "turnover": None if bar.turnover is None else str(bar.turnover),
        "adjustment": bar.adjustment.value,
        "is_suspended": bar.is_suspended,
        "source": bar.source,
    }


def daily_bar_content_hash(bar: Bar) -> str:
    return sha256(
        json.dumps(
            daily_bar_content(bar), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def matches_daily_bar(record: ProviderEvidenceRecord, bar: Bar) -> bool:
    artifact_id = record.payload.get("artifact_id")
    if not isinstance(artifact_id, str) or any(
        len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
        for value in (artifact_id, record.raw_data_hash)
    ):
        return False
    return (
        record.market is bar.instrument.market
        and record.subject == bar.instrument.symbol
        and record.available_at == bar.available_at
        and record.retrieved_at == bar.available_at
        and record.observed_at == bar.timestamp
        and record.source_reference == bar.source
        and artifact_id
        == provider_artifact_id(
            provider=record.provider,
            dataset=record.dataset,
            market=record.market,
            subject=record.subject,
            source_identity=f"{bar.source}:{bar.instrument.asset_type.value}:{bar.instrument.symbol}",
            source_reference=bar.source,
            content_hash=record.raw_data_hash,
        )
        and record.payload.get("bar") == daily_bar_content(bar)
        and record.payload.get("bar_hash") == daily_bar_content_hash(bar)
    )
