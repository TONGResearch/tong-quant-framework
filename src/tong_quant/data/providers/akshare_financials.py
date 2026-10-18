"""Retain native statement observations; do not guess accounting units or revisions."""

import json
from dataclasses import dataclass
from hashlib import sha256

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.models import RawDataset, dataframe_snapshot_bytes
from tong_quant.data.providers.contracts import (
    FINANCIAL_SNAPSHOT_DATASET,
    EvidenceLimitation,
    ProviderArtifact,
    ProviderArtifactObservation,
    ProviderArtifactStatus,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_artifact_id,
    provider_artifact_observation_id,
    provider_evidence_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.version import AKSHARE_FINANCIAL_SNAPSHOT_VERSION

_LIMITATIONS = (
    EvidenceLimitation(
        "financial_native_semantics_unreviewed",
        "Native statement fields, currency, accounting units and canonical metric mapping "
        "are unreviewed; this capture does not populate FundamentalFact or research scores",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "financial_retrieval_time_only",
        "Report period is observation metadata, not publication availability; current "
        "numeric revisions cannot be backdated to historical disclosure dates",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "financial_transformed_frame",
        "Artifact preserves the delivered AKShare frame, not upstream wire bytes or "
        "independently verified issuer filings; full historical continuity is unknown",
        DataTrustLevel.LOW,
    ),
)


@dataclass(frozen=True, slots=True)
class AkShareFinancialSnapshotAdapter:
    dataset: RawDataset
    provider_id: str = "akshare"

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                self.provider_id,
                FINANCIAL_SNAPSHOT_DATASET,
                (Market.CHINA_A,),
                ProviderCapabilityStatus.DEGRADED,
                DataTrustLevel.LOW,
                AvailabilityPrecision.RETRIEVAL_TIME,
                False,
                ("statement",),
                _LIMITATIONS,
                model_version=AKSHARE_FINANCIAL_SNAPSHOT_VERSION,
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        dataset = self.dataset
        statement = request.parameters.get("statement")
        if (
            statement not in {"income", "balance", "cash_flow"}
            or request.dataset != FINANCIAL_SNAPSHOT_DATASET
            or request.market is not Market.CHINA_A
            or len(request.subject) != 6
            or not request.subject.isascii()
            or not request.subject.isdigit()
            or dataset.dataset != "fundamental_facts"
            or dataset.source != f"akshare:financial:{statement}"
            or dataset.parameters != {"symbol": request.subject, "statement": statement}
            or not {"report_date", "metric_name", "value"} <= set(dataset.frame.columns)
        ):
            raise ValueError("financial snapshot does not match the supported native query")
        frame = dataset.raw_frame_json or dataset.frame.to_json(
            orient="table", date_format="iso", force_ascii=True
        )
        decoded = json.loads(frame)
        reject_sensitive_structure(decoded, path="financial_snapshot.frame")
        reject_sensitive_structure(dataset.parameters, path="financial_snapshot.parameters")
        content = dataframe_snapshot_bytes(frame, dataset.parameters)
        digest = sha256(content).hexdigest()
        if (
            not dataset.raw_data_hash
            or digest != dataset.content_hash()
            or len(content) > 16 * 1024 * 1024
        ):
            raise ValueError("financial snapshot fingerprint or size check failed")
        captured_rows = [
            {str(column): row[str(column)] for column in dataset.frame.columns}
            for row in decoded["data"]
        ]
        delivered_rows = json.loads(
            dataset.frame.to_json(orient="records", date_format="iso", force_ascii=True)
        )
        if json.dumps(captured_rows, sort_keys=True) != json.dumps(delivered_rows, sort_keys=True):
            raise ValueError("financial artifact cannot reproduce the delivered native rows")
        identity = f"{dataset.source}:{request.subject}:{statement}"
        artifact_id = provider_artifact_id(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            source_identity=identity,
            source_reference=dataset.source,
            content_hash=digest,
        )
        artifact = ProviderArtifact(
            artifact_id=artifact_id,
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            source_identity=identity,
            source_reference=dataset.source,
            published_at=dataset.retrieved_at,
            retrieved_at=dataset.retrieved_at,
            content_hash=digest,
            media_type="application/json",
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.LOW,
            content=content,
        )
        records = []
        for row_number, row in enumerate(decoded["data"]):
            payload = {
                "statement": statement,
                "row_number": row_number,
                "native_row": row,
                "artifact_id": artifact_id,
                "canonical_metric": None,
                "accounting_unit": None,
                "normalization_status": "unreviewed_native_observation",
                "model_version": AKSHARE_FINANCIAL_SNAPSHOT_VERSION,
            }
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject=request.subject,
                        available_at=dataset.retrieved_at,
                        source_reference=dataset.source,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject=request.subject,
                    available_at=dataset.retrieved_at,
                    retrieved_at=dataset.retrieved_at,
                    source_reference=dataset.source,
                    payload=payload,
                    raw_data_hash=digest,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.LOW,
                    limitations=tuple(item.description for item in _LIMITATIONS),
                )
            )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=dataset.retrieved_at,
            source=dataset.source,
            parameters={
                **dataset.parameters,
                "normalization_version": AKSHARE_FINANCIAL_SNAPSHOT_VERSION,
            },
            raw_data_hash=digest,
            raw_record_count=len(dataset.frame),
            records=tuple(records),
            artifacts=(artifact,),
            artifact_observations=(
                ProviderArtifactObservation(
                    observation_id=provider_artifact_observation_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject=request.subject,
                        source_identity=identity,
                        source_reference=dataset.source,
                        published_at=dataset.retrieved_at,
                        artifact_id=artifact_id,
                        retrieved_at=dataset.retrieved_at,
                        status=ProviderArtifactStatus.CAPTURED,
                        error_code="",
                        related_source_identities=(),
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject=request.subject,
                    source_identity=identity,
                    artifact_id=artifact_id,
                    published_at=dataset.retrieved_at,
                    retrieved_at=dataset.retrieved_at,
                    source_reference=dataset.source,
                    status=ProviderArtifactStatus.CAPTURED,
                    error_code="",
                ),
            ),
            limitations=_LIMITATIONS,
        )
