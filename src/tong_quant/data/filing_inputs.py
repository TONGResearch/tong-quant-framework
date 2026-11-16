"""Read-side reconstruction of reviewed filing facts; never admits scored evidence."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.filing_facts import prepare_filing_extraction
from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.data.providers.contracts import ProviderArtifact
from tong_quant.data.providers.reviewed_filings import (
    REVIEWED_FILING_DATASET,
    parse_filing_review,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import FundamentalFact
from tong_quant.version import (
    REVIEWED_BANK_RATIOS_VERSION,
    REVIEWED_COMPARATIVE_FACTS_VERSION,
    REVIEWED_FILING_FACTS_VERSION,
    REVIEWED_MONETARY_FACTS_VERSION,
    REVIEWED_NONFINANCIAL_CASH_BALANCE_VERSION,
    REVIEWED_NONFINANCIAL_PARENT_EQUITY_VERSION,
    REVIEWED_NONFINANCIAL_RATIOS_VERSION,
)


def _completed_batch(store: SQLiteStore, batch_id: str, *, dataset: str,
                     as_of: datetime, raw_hash: str | None = None,
                     started_at: datetime | None = None,
                     parameters: dict[str, str] | None = None) -> None:
    row = store.ingestion_batch(batch_id)
    if (
        row is None or row["provider"] != "cninfo_direct" or row["dataset"] != dataset
        or row["status"] != "completed" or row["completed_at"] is None
        or datetime.fromisoformat(row["started_at"]) > as_of
        or datetime.fromisoformat(row["completed_at"]) > as_of
        or datetime.fromisoformat(row["completed_at"]) < datetime.fromisoformat(row["started_at"])
        or (raw_hash is not None and row["raw_response_hash"] != raw_hash)
        or (started_at is not None and datetime.fromisoformat(row["started_at"]) != started_at)
        or (parameters is not None and json.loads(row["parameters_json"]) != parameters)
    ):
        raise ValueError("financial source batch incomplete, future or mismatched")


def _registered_artifact(store: SQLiteStore, artifact: ProviderArtifact, *, batch_id: str) -> None:
    stored = store.provider_artifact(artifact.artifact_id)
    suffix = ".pdf" if artifact.media_type == "application/pdf" else ".bin"
    if (stored is None or stored["first_batch_id"] != batch_id
            or stored["byte_size"] != len(artifact.content)
            or stored["storage_key"] != (
                f"sha256/{artifact.content_hash[:2]}/{artifact.content_hash}{suffix}")):
        raise ValueError("financial artifact ownership, size or key mismatch")
    for key, expected in asdict(artifact).items():
        if key in {"content", "published_at", "retrieved_at"}:
            continue
        if stored[key] != expected:
            raise ValueError("financial artifact metadata mismatch")
    if (datetime.fromisoformat(stored["published_at"]) != artifact.published_at
            or datetime.fromisoformat(stored["first_retrieved_at"]) != artifact.retrieved_at):
        raise ValueError("financial artifact capture mismatch")


@dataclass(frozen=True, slots=True)
class ReviewedFinancialInputReader:
    store: SQLiteStore
    artifacts: FileSystemArtifactStore

    def read(self, symbol: str, market: Market, metrics: tuple[str, ...], *, as_of: datetime,
             sector_profile: str, reporting_scope: str = "group") -> FinancialInputSnapshot:
        # Validate query semantics before database access, including an empty result.
        query = FinancialInputSnapshot(
            symbol, market, as_of, tuple(sorted(metrics)), sector_profile, reporting_scope, (),
        )
        service = MarketDataService(self.store)
        entries = []
        with service.read_snapshot():
            for metric in query.requested_metrics:
                for fact in service.fundamental_facts(
                    symbol, market, AssetType.EQUITY, metric, as_of=as_of,
                ):
                    if fact.provider_dataset != REVIEWED_FILING_DATASET:
                        entries.append(FinancialFactInspection(
                            fact, FinancialBindingStatus.UNSUPPORTED,
                            ("No source verifier exists for this financial dataset",),
                        ))
                        continue
                    try:
                        entries.append(self._inspect(fact, as_of=as_of,
                                                     sector_profile=sector_profile))
                    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
                        entries.append(FinancialFactInspection(
                            fact, FinancialBindingStatus.REJECTED,
                            ("Source, review, fact, batch or requested sector failed binding",),
                        ))
        return FinancialInputSnapshot(
            symbol, market, as_of, query.requested_metrics, sector_profile, reporting_scope,
            tuple(entries),
        )

    def _inspect(self, fact: FundamentalFact, *, as_of: datetime,
                 sector_profile: str) -> FinancialFactInspection:
        content = self.artifacts.read_content(
            fact.raw_data_hash, "application/json", max_bytes=64 * 1024,
        )
        packet = json.loads(content)
        reject_sensitive_structure(packet, path="financial_source_packet")
        if packet["model_version"] not in {
            REVIEWED_FILING_FACTS_VERSION, REVIEWED_COMPARATIVE_FACTS_VERSION,
            REVIEWED_BANK_RATIOS_VERSION,
            REVIEWED_MONETARY_FACTS_VERSION,
            REVIEWED_NONFINANCIAL_RATIOS_VERSION,
            REVIEWED_NONFINANCIAL_CASH_BALANCE_VERSION,
            REVIEWED_NONFINANCIAL_PARENT_EQUITY_VERSION,
        }:
            raise ValueError("unsupported financial review packet version")
        review_values = dict(packet["review"])
        rows = review_values.pop("rows")
        review = parse_filing_review({"review": review_values, "rows": rows})
        if review.model_version != packet["model_version"]:
            raise ValueError("financial review version differs from packet declaration")
        if review.sector_profile != sector_profile:
            raise ValueError("financial research sector differs from reviewed source scope")
        prepared = prepare_filing_extraction(self.store, self.artifacts, review, as_of=as_of)
        expected_facts = prepared.facts(fact.batch_id)
        if fact not in expected_facts or prepared.batch.raw_data_hash != fact.raw_data_hash:
            raise ValueError("stored financial value cannot be reproduced from its review packet")
        _completed_batch(self.store, fact.batch_id, dataset=REVIEWED_FILING_DATASET,
                         as_of=as_of, raw_hash=fact.raw_data_hash,
                         started_at=prepared.batch.retrieved_at,
                         parameters=prepared.batch.parameters)
        artifact = prepared.batch.artifacts[0]
        _registered_artifact(self.store, artifact, batch_id=fact.batch_id)
        actual = self.store.provider_evidence(
            provider="cninfo_direct", dataset=REVIEWED_FILING_DATASET,
            market=fact.instrument.market, subject=fact.instrument.symbol, as_of=as_of,
        )
        expected = next(record for record in prepared.batch.records
                        if record.payload["metric"] == fact.metric)
        matches = [record for record in actual if record.evidence_id == expected.evidence_id]
        if len(matches) != 1 or financial_input_json(asdict(matches[0])) != (
            financial_input_json(asdict(expected))
        ):
            raise ValueError("financial evidence content differs from reconstructed input")
        metadata = self.store.provider_evidence_as_of(
            provider="cninfo_direct", dataset=REVIEWED_FILING_DATASET,
            market=fact.instrument.market, subject=fact.instrument.symbol, as_of=as_of,
        )
        if not any(row["evidence_id"] == expected.evidence_id
                   and row["batch_id"] == fact.batch_id for row in metadata):
            raise ValueError("financial evidence batch ownership mismatch")
        source = prepared.adapter.source
        captures = [row for row in self.store.provider_artifact_history(
            provider="cninfo_direct", dataset=source.dataset, subject=source.subject,
        ) if row["artifact_id"] == source.artifact_id and row["status"] == "captured"
            and datetime.fromisoformat(row["retrieved_at"]) == source.retrieved_at]
        if not captures:
            raise ValueError("financial source capture observation missing")
        _registered_artifact(self.store, source, batch_id=captures[0]["batch_id"])
        _completed_batch(self.store, captures[0]["batch_id"], dataset=source.dataset, as_of=as_of)
        reviewed_row = next(row for row in review.rows if row.metric == fact.metric)
        return FinancialFactInspection(
            fact, FinancialBindingStatus.SOURCE_BOUND,
            tuple(item.description for item in prepared.batch.limitations),
            reporting_scope=review.reporting_scope, sector_profile=review.sector_profile,
            evidence_id=expected.evidence_id, review_artifact_id=artifact.artifact_id,
            filing_artifact_id=source.artifact_id, filing_sha256=source.content_hash,
            source_pages=reviewed_row.source_pages, source_unit=review.source_unit,
            source_column=review.source_column, audit_status=review.audit_status,
            statement=reviewed_row.statement,
            filing_period_end=review.filing_period_end or review.period_end,
            comparability=review.comparability,
            issuer_revision_status=review.issuer_revision_status,
            measurement_basis=review.measurement_basis,
        )
