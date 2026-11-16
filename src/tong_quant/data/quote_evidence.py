"""Read-only reconstruction of retained price observations, not valuation inputs."""

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from hashlib import sha256

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceRecord
from tong_quant.data.providers.yahoo_quote import (
    DATASET,
    MAX_BYTES,
    PROVIDER,
    YahooChinaQuoteEvidenceAdapter,
    YahooQuoteCapture,
    yahoo_equity_symbol,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import YAHOO_CHINA_QUOTE_VERSION


def _verify(store: SQLiteStore, artifacts: FileSystemArtifactStore,
            record: ProviderEvidenceRecord, as_of: datetime) -> None:
    if max(record.available_at.astimezone(UTC), record.retrieved_at.astimezone(UTC)) > (
        as_of.astimezone(UTC)
    ):
        raise ValueError("future quote record")
    content = artifacts.read_content(record.raw_data_hash, "application/json",
                                     max_bytes=MAX_BYTES + 4096)
    envelope = json.loads(content)
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    capture = YahooQuoteCapture(date.fromisoformat(envelope["query_date"]),
                                envelope["decoded_payload"], envelope["error_code"])
    adapter = YahooChinaQuoteEvidenceAdapter(download=lambda _: capture, clock=lambda: captured)
    batch = adapter.fetch(ProviderDatasetRequest(DATASET, Market.CHINA_A, record.subject, captured))
    artifact = batch.artifacts[0]
    if batch.records != (record,) or artifact.content != content:
        raise ValueError("quote capture reconstruction mismatch")
    saved_artifact = store.provider_artifact(artifact.artifact_id)
    if (saved_artifact is None or saved_artifact["storage_key"] != (
        f"sha256/{record.raw_data_hash[:2]}/{record.raw_data_hash}.bin")
            or saved_artifact["byte_size"] != len(content)):
        raise ValueError("quote artifact registry mismatch")
    for key, value in asdict(artifact).items():
        if key not in {"content", "published_at", "retrieved_at"} and saved_artifact[key] != value:
            raise ValueError("quote artifact metadata mismatch")
    for key in ("published_at", "first_retrieved_at"):
        if datetime.fromisoformat(saved_artifact[key]).astimezone(UTC) != captured.astimezone(UTC):
            raise ValueError("quote artifact chronology mismatch")
    row = next((row for row in store.provider_evidence_as_of(
        provider=PROVIDER, dataset=DATASET, market=Market.CHINA_A, subject=record.subject,
        as_of=as_of) if row["evidence_id"] == record.evidence_id), None)
    if row is None:
        raise ValueError("quote evidence ownership missing")
    for batch_id in {row["batch_id"], saved_artifact["first_batch_id"]}:
        saved = store.ingestion_batch(batch_id)
        if (saved is None or saved["provider"] != PROVIDER or saved["dataset"] != DATASET
                or saved["status"] != "completed" or saved["completed_at"] is None
                or saved["raw_response_hash"] != record.raw_data_hash
                or json.loads(saved["parameters_json"]) != batch.parameters
                or datetime.fromisoformat(saved["started_at"]).astimezone(UTC) != (
                    captured.astimezone(UTC))
                or not captured.astimezone(UTC) <= datetime.fromisoformat(
                    saved["completed_at"]).astimezone(UTC) <= as_of.astimezone(UTC)):
            raise ValueError("quote ingestion batch chronology or ownership rejected")


def inspect_yahoo_quote(store: SQLiteStore, artifacts: FileSystemArtifactStore,
                        symbol: str, *, as_of: datetime) -> dict[str, object]:
    require_timezone(as_of, "quote inspection cutoff")
    yahoo_equity_symbol(symbol)
    entries: list[dict[str, object]] = []
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(
            provider=PROVIDER, dataset=DATASET, market=Market.CHINA_A, subject=symbol, as_of=as_of)
        for record in sorted(records, key=lambda item: (
            item.available_at.astimezone(UTC), item.evidence_id)):
            try:
                _verify(store, artifacts, record, as_of)
                bound = True
            except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                bound = False
            entries.append({"evidence_id": record.evidence_id, "available_at": record.available_at,
                "raw_data_hash": record.raw_data_hash, "source_bound": bound,
                "trust_level": record.trust_level.value,
                "availability_precision": record.availability_precision.value,
                "payload": record.payload, "limitations": record.limitations})
    output: dict[str, object] = {
        "symbol": symbol, "market": Market.CHINA_A.value, "as_of": as_of,
        "provider": PROVIDER, "dataset": DATASET, "inspections": entries,
        "status": "missing", "price": None, "claimed_quote_at": None,
        "freshness": "UNASSESSED", "source_bound": False, "market_value_available": False,
        "valuation_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "model_version": YAHOO_CHINA_QUOTE_VERSION,
    }
    if records:
        latest_time = max(record.available_at.astimezone(UTC) for record in records)
        ordered = sorted(records, key=lambda item: (item.available_at.astimezone(UTC),
                                                    item.evidence_id))
        latest = [(record, entry) for record, entry in zip(ordered, entries, strict=True)
                  if record.available_at.astimezone(UTC) == latest_time]
        if len(latest) != 1 or not latest[0][1]["source_bound"]:
            output["status"] = "rejected_or_ambiguous"
        else:
            record = latest[0][0]
            payload = record.payload
            output.update(status=payload["status"], price=payload["price"],
                claimed_quote_at=payload["claimed_quote_at"], source_bound=True,
                evidence_id=record.evidence_id)
    return {**output, "inspection_hash": sha256(financial_input_json(output).encode()).hexdigest()}
