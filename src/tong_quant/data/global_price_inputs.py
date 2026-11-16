"""Reconstruct retained global snapshots for exploratory, noncanonical calculations."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import (
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
)
from tong_quant.data.providers.yahoo_snapshot import (
    DATASET,
    LIMITATIONS,
    MAX_BYTES,
    PROVIDER,
    TIMEZONES,
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
    snapshot_prices,
)
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, require_timezone
from tong_quant.version import GLOBAL_PRICE_SNAPSHOT_VERSION


@dataclass(frozen=True, slots=True)
class GlobalPriceInputs:
    subject: str
    market: Market
    as_of: datetime
    status: str
    bars: tuple[Bar, ...]
    observations: tuple[dict[str, object], ...]
    selected_evidence_id: str | None
    freshness: str
    observation_age_seconds: float | None
    maximum_age_seconds: int | None

    def document(self) -> dict[str, object]:
        output: dict[str, object] = {
            "subject": self.subject, "market": self.market.value, "as_of": self.as_of,
            "status": self.status, "observed_bar_count": len(self.bars),
            "bars_content_hash": sha256(financial_input_json(
                [asdict(bar) for bar in self.bars]).encode()).hexdigest(),
            "selected_evidence_id": self.selected_evidence_id,
            "observations": self.observations,
            "first_observed_at": self.bars[0].timestamp if self.bars else None,
            "last_observed_at": self.bars[-1].timestamp if self.bars else None,
            "observation_age_seconds": self.observation_age_seconds,
            "maximum_age_seconds": self.maximum_age_seconds, "freshness": self.freshness,
            "price_basis": "PROVIDER_NATIVE_UNVERIFIED", "trust_ceiling": "LOW",
            "availability_precision": "retrieval_time", "limitations": LIMITATIONS,
            "financial_assessed": False, "research_report_created": False,
            "investment_scoring_authorized": False, "historical_replay_eligible": False,
            "validation_authorized": False, "execution_authorized": False,
            "model_version": GLOBAL_PRICE_SNAPSHOT_VERSION,
        }
        return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}


def _reconstruct(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                 record: ProviderEvidenceRecord, as_of: datetime) -> tuple[Bar, ...]:
    def rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
        if envelope["model_version"] != GLOBAL_PRICE_SNAPSHOT_VERSION:
            raise ValueError("unsupported snapshot normalization version")
        captured = datetime.fromisoformat(envelope["retrieved_at"])
        request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                         captured, envelope["parameters"])
        capture = YahooSnapshotCapture(envelope["decoded_payload"], envelope["error_code"])
        return YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: captured).fetch(
            request)

    envelope = verify_retained_snapshot(store, artifacts, record, as_of=as_of,
        max_bytes=MAX_BYTES + 4096, rebuild=rebuild)
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    capture = YahooSnapshotCapture(envelope["decoded_payload"], envelope["error_code"])
    return snapshot_prices(capture, request, captured)[1]


def read_global_price_inputs(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                            subject: str, market: Market, *, as_of: datetime,
                            maximum_age_seconds: int | None = None) -> GlobalPriceInputs:
    require_timezone(as_of, "global snapshot read cutoff")
    if market not in TIMEZONES or not subject.strip():
        raise ValueError("global snapshot reader requires an overseas market and subject")
    if maximum_age_seconds is not None and (
        type(maximum_age_seconds) is not int or maximum_age_seconds <= 0
    ):
        raise ValueError("global snapshot age limit must be a positive integer")
    bars: tuple[Bar, ...] = ()
    status, selected, freshness, age = "missing", None, "UNASSESSED", None
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(
            provider=PROVIDER, dataset=DATASET, market=market, subject=subject, as_of=as_of)
        ordered = sorted(records, key=lambda item: (item.available_at.astimezone(UTC),
                                                    item.evidence_id))
        observations = tuple({"evidence_id": item.evidence_id, "raw_data_hash": item.raw_data_hash,
                              "available_at": item.available_at,
                              "status": item.payload.get("status", "invalid_response"),
                              "trust_level": item.trust_level.value}
                             for item in ordered)
        if ordered:
            latest_time = ordered[-1].available_at.astimezone(UTC)
            latest = tuple(item for item in ordered
                           if item.available_at.astimezone(UTC) == latest_time)
            status = "rejected_or_ambiguous"
            if len(latest) == 1:
                record = latest[0]
                selected = record.evidence_id
                try:
                    bars = _reconstruct(store, artifacts, record, as_of)
                    status = str(record.payload["status"])
                    if bars:
                        age = (as_of.astimezone(UTC) - bars[-1].timestamp.astimezone(UTC)
                               ).total_seconds()
                        if maximum_age_seconds is not None:
                            freshness = "STALE" if age > maximum_age_seconds else "WITHIN_LIMIT"
                            if freshness == "STALE":
                                status, bars = "stale_observation", ()
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    bars = ()
    return GlobalPriceInputs(subject, market, as_of, status, bars, observations, selected,
                             freshness, age, maximum_age_seconds)
