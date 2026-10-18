"""Archive partial suspension evidence, never infer current tradability or resumption."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.models import RawDataset, dataframe_snapshot_bytes
from tong_quant.data.normalization import normalize_suspension_lifecycle
from tong_quant.data.providers.contracts import (
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
from tong_quant.version import AKSHARE_SUSPENSION_VERSION

SUSPENSION_DATASET = "security_lifecycle_suspension"
_LIMITATIONS = (
    EvidenceLimitation(
        "partial_suspension_observation",
        "Date-filtered provider observations are not a complete current status or history; "
        "absence never proves normal listing, no ST, no suspension or no delisting",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "resumption_unconfirmed",
        "Reported end and expected resumption dates are metadata, not confirmed resumption",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "suspension_retrieval_snapshot",
        "Delivered AKShare frame is not upstream wire or issuer confirmation; "
        "historical publication/revisions are unknown and availability starts at retrieval",
        DataTrustLevel.LOW,
    ),
)


@dataclass(frozen=True, slots=True)
class AkShareSuspensionEvidenceAdapter:
    dataset: RawDataset
    provider_id: str = "akshare"

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                self.provider_id,
                SUSPENSION_DATASET,
                (Market.CHINA_A,),
                ProviderCapabilityStatus.DEGRADED,
                DataTrustLevel.LOW,
                AvailabilityPrecision.RETRIEVAL_TIME,
                False,
                (),
                _LIMITATIONS,
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        dataset = self.dataset
        query_date = str(dataset.parameters.get("date", ""))
        if len(query_date) != 8 or not query_date.isascii() or not query_date.isdigit():
            raise ValueError("suspension evidence requires an explicit YYYYMMDD date")
        if (
            datetime.strptime(query_date, "%Y%m%d").date()
            > dataset.retrieved_at.astimezone(ZoneInfo("Asia/Shanghai")).date()
        ):
            raise ValueError("suspension query is beyond capture date")
        if (
            dataset.dataset != SUSPENSION_DATASET
            or dataset.source != "akshare:stock_tfp_em"
            or dataset.parameters.get("normalization_version") != AKSHARE_SUSPENSION_VERSION
            or (request.dataset, request.market, request.subject)
            != (SUSPENSION_DATASET, Market.CHINA_A, f"ALL:{query_date}")
            or request.parameters
        ):
            raise ValueError("suspension evidence requires a matching versioned dated capture")
        frame = dataset.raw_frame_json or dataset.frame.to_json(
            orient="table", date_format="iso", force_ascii=True
        )
        decoded = json.loads(frame)
        reject_sensitive_structure(decoded, path="suspension_snapshot.frame")
        reject_sensitive_structure(dataset.parameters, path="suspension_snapshot.parameters")
        content = dataframe_snapshot_bytes(frame, dataset.parameters)
        digest = sha256(content).hexdigest()
        if (
            len(content) > 16 * 1024 * 1024
            or not dataset.raw_data_hash
            or digest != dataset.content_hash()
        ):
            raise ValueError("suspension snapshot fingerprint or size is invalid")
        events = normalize_suspension_lifecycle(dataset, batch_id="")
        reconstructed = normalize_suspension_lifecycle(
            RawDataset(
                dataset.dataset,
                pd.DataFrame(decoded["data"]),
                dataset.retrieved_at,
                dataset.source,
                dataset.parameters,
                raw_data_hash=digest,
            ),
            batch_id="",
        )
        if events != reconstructed:
            raise ValueError("archived suspension snapshot cannot reproduce normalized events")
        identity = f"{dataset.source}:{query_date}"
        artifact = ProviderArtifact(
            artifact_id=provider_artifact_id(
                provider=self.provider_id,
                dataset=dataset.dataset,
                market=Market.CHINA_A,
                subject=request.subject,
                source_identity=identity,
                source_reference=dataset.source,
                content_hash=digest,
            ),
            provider=self.provider_id,
            dataset=dataset.dataset,
            market=Market.CHINA_A,
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
        seen: set[tuple[str, str]] = set()
        for event in events:
            key = (event.instrument.symbol, event.effective_date.isoformat())
            if key in seen:
                raise ValueError("duplicate suspension keys require source review")
            seen.add(key)
            payload: dict[str, object] = {
                "symbol": event.instrument.symbol,
                "effective_date": event.effective_date.isoformat(),
                "event_type": event.event_type.value,
                "details": event.details,
                "artifact_id": artifact.artifact_id,
                "query_date": query_date,
                "status_confirmation": "unverified",
            }
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=dataset.dataset,
                        market=Market.CHINA_A,
                        subject=event.instrument.symbol,
                        available_at=dataset.retrieved_at,
                        source_reference=dataset.source,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=dataset.dataset,
                    market=Market.CHINA_A,
                    subject=event.instrument.symbol,
                    available_at=dataset.retrieved_at,
                    retrieved_at=dataset.retrieved_at,
                    source_reference=dataset.source,
                    payload=payload,
                    raw_data_hash=digest,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.LOW,
                    limitations=tuple(item.description for item in _LIMITATIONS),
                    observed_at=dataset.retrieved_at,
                )
            )
        limitations: tuple[EvidenceLimitation, ...] = _LIMITATIONS
        if len(events) != len(dataset.frame):
            limitations = (
                *limitations,
                EvidenceLimitation(
                    "suspension_rows_rejected",
                    "Malformed identifiers, invalid dates or future starts were not normalized; "
                    "all source rows remain in the captured frame",
                    DataTrustLevel.LOW,
                ),
            )
        observation = ProviderArtifactObservation(
            observation_id=provider_artifact_observation_id(
                provider=self.provider_id,
                dataset=dataset.dataset,
                market=Market.CHINA_A,
                subject=request.subject,
                source_identity=identity,
                source_reference=dataset.source,
                published_at=dataset.retrieved_at,
                retrieved_at=dataset.retrieved_at,
                status=ProviderArtifactStatus.CAPTURED,
                artifact_id=artifact.artifact_id,
                error_code="",
                related_source_identities=(),
            ),
            provider=self.provider_id,
            dataset=dataset.dataset,
            market=Market.CHINA_A,
            subject=request.subject,
            source_identity=identity,
            source_reference=dataset.source,
            published_at=dataset.retrieved_at,
            retrieved_at=dataset.retrieved_at,
            status=ProviderArtifactStatus.CAPTURED,
            artifact_id=artifact.artifact_id,
            error_code="",
        )
        return ProviderEvidenceBatch(
            self.provider_id,
            dataset.dataset,
            Market.CHINA_A,
            dataset.retrieved_at,
            dataset.source,
            dataset.parameters,
            digest,
            len(dataset.frame),
            tuple(records),
            limitations,
            (artifact,),
            (observation,),
        )
