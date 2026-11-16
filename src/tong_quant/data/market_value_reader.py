"""Reproduce market-value observations from exact retained capture bytes at one cutoff."""

import base64
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.market_value_inputs import (
    MarketValueInputSnapshot,
    MarketValueInspection,
    market_value_record_hash,
)
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceRecord
from tong_quant.data.providers.eastmoney_market_values import (
    DATASET,
    PROVIDER,
    EastmoneyMarketValueAdapter,
    QuoteHttpCapture,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


@dataclass(frozen=True, slots=True)
class MarketValueInputReader:
    store: SQLiteStore
    artifacts: FileSystemArtifactStore

    def read(self, symbol: str, market: Market, *, as_of: datetime) -> MarketValueInputSnapshot:
        MarketValueInputSnapshot(symbol, market, as_of, ())
        service = MarketDataService(self.store)
        entries = []
        with service.read_snapshot():
            for record in service.provider_evidence(provider=PROVIDER, dataset=DATASET,
                                                     market=market, subject=symbol, as_of=as_of):
                try:
                    self._verify(record, as_of)
                    entries.append(MarketValueInspection(
                        record, True, ("Exact capture/evidence/artifact/completed-batch binding",),
                        market_value_record_hash(record)))
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    entries.append(MarketValueInspection(
                        record, False, ("Market-value source, bytes, evidence or batch rejected",),
                        market_value_record_hash(record)))
        return MarketValueInputSnapshot(symbol, market, as_of, tuple(entries))

    def _verify(self, record: ProviderEvidenceRecord, as_of: datetime) -> None:
        content = self.artifacts.read_content(record.raw_data_hash, "application/json",
                                              max_bytes=128 * 1024)
        envelope = json.loads(content)
        captured = datetime.fromisoformat(envelope["retrieved_at"])
        adapter = EastmoneyMarketValueAdapter(
            download=lambda _: QuoteHttpCapture(
                envelope["status_code"], base64.b64decode(envelope["body_base64"], validate=True),
                envelope["error_code"]), clock=lambda: captured,
        )
        batch = adapter.fetch(ProviderDatasetRequest(
            DATASET, record.market, record.subject, captured))
        if len(batch.records) != 1 or batch.records[0] != record or batch.raw_data_hash != (
            record.raw_data_hash):
            raise ValueError("market-value source reconstruction mismatch")
        artifact = batch.artifacts[0]
        stored = self.store.provider_artifact(artifact.artifact_id)
        if stored is None or stored["storage_key"] != (
            f"sha256/{record.raw_data_hash[:2]}/{record.raw_data_hash}.bin"
        ) or stored["byte_size"] != len(content):
            raise ValueError("market-value artifact missing or mismatched")
        for key, value in asdict(artifact).items():
            if key not in {"content", "published_at", "retrieved_at"} and stored[key] != value:
                raise ValueError("market-value artifact metadata mismatch")
        if any(datetime.fromisoformat(stored[key]).astimezone(UTC) != captured.astimezone(UTC)
               for key in ("published_at", "first_retrieved_at")):
            raise ValueError("market-value artifact capture time mismatch")
        # Evidence ownership is separate from artifact ownership on repeated captures.
        row = next((r for r in self.store.provider_evidence_as_of(
            provider=PROVIDER, dataset=DATASET, market=record.market,
            subject=record.subject, as_of=as_of,
        ) if r["evidence_id"] == record.evidence_id), None)
        if row is None:
            raise ValueError("market-value evidence batch missing")
        for batch_id in {row["batch_id"], stored["first_batch_id"]}:
            saved = self.store.ingestion_batch(batch_id)
            if (saved is None or saved["provider"] != PROVIDER or saved["dataset"] != DATASET
                    or saved["status"] != "completed" or saved["completed_at"] is None
                    or saved["raw_response_hash"] != record.raw_data_hash
                    or json.loads(saved["parameters_json"]) != batch.parameters
                    or datetime.fromisoformat(saved["started_at"]).astimezone(UTC) != (
                        captured.astimezone(UTC))
                    or not captured.astimezone(UTC) <= datetime.fromisoformat(
                        saved["completed_at"]).astimezone(UTC) <= as_of.astimezone(UTC)):
                raise ValueError("market-value batch incomplete, future or mismatched")
