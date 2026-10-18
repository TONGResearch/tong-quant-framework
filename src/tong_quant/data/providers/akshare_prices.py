"""Adapt a captured AKShare frame into auditable, unadjusted daily-bar evidence."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

import pandas as pd

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.models import DailyBarRequest, RawDataset, dataframe_snapshot_bytes
from tong_quant.data.normalization import normalize_daily_bars
from tong_quant.data.price_evidence import daily_bar_content, daily_bar_content_hash
from tong_quant.data.providers.contracts import (
    AKSHARE_PRICE_PROVIDER,
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
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    Market,
)
from tong_quant.domain.models import Bar

MAX_PRICE_SNAPSHOT_BYTES = 16 * 1024 * 1024
_SOURCES = {"akshare:stock_zh_a_hist", "akshare:stock_zh_a_hist_tx", "akshare:index_zh_a_hist"}
_LIMITATIONS = (
    EvidenceLimitation(
        "retrieval_time_price_snapshot",
        "Historical price values are visible only from retrieval time; "
        "original publication and correction history are unverified",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "akshare_transformed_frame",
        "Artifact is the delivered AKShare DataFrame plus query parameters, "
        "not upstream HTTP wire bytes or official exchange verification",
        DataTrustLevel.LOW,
    ),
    EvidenceLimitation(
        "price_activity_units_unverified",
        "Missing turnover remains unknown; provider-native volume units "
        "and historical unit consistency are not independently verified",
        DataTrustLevel.LOW,
    ),
)


@dataclass(frozen=True, slots=True)
class AkShareDailyBarEvidenceAdapter:
    dataset: RawDataset
    query: DailyBarRequest
    bars: tuple[Bar, ...]
    provider_id: str = AKSHARE_PRICE_PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                self.provider_id,
                self.dataset.dataset,
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
        dataset, query = self.dataset, self.query
        expected_dataset = "index_daily" if query.asset_type is AssetType.INDEX else "a_share_daily"
        if (
            query.market is not Market.CHINA_A
            or query.asset_type not in {AssetType.EQUITY, AssetType.INDEX}
            or query.adjustment is not Adjustment.NONE
            or dataset.dataset != expected_dataset
            or (request.dataset, request.market, request.subject)
            != (dataset.dataset, query.market, query.symbol)
            or request.parameters
            or dataset.source not in _SOURCES
            or len(query.symbol) != 6
            or not query.symbol.isascii()
            or not query.symbol.isdigit()
        ):
            raise ValueError("price evidence requires a matching unadjusted China A/index capture")
        if any(
            len(value) != 8 or not value.isascii() or not value.isdigit()
            for value in (query.start_date, query.end_date)
        ):
            raise ValueError("price evidence requires explicit YYYYMMDD query dates")
        start = datetime.strptime(query.start_date, "%Y%m%d").date()
        end = datetime.strptime(query.end_date, "%Y%m%d").date()
        if start > end:
            raise ValueError("price evidence query dates are reversed")
        expected_parameters = {
            "symbol": query.symbol,
            "start_date": query.start_date,
            "end_date": query.end_date,
            "asset_type": query.asset_type.value,
            "adjustment": Adjustment.NONE.value,
        }
        if any(dataset.parameters.get(key) != value for key, value in expected_parameters.items()):
            raise ValueError("captured price parameters do not match the unadjusted query")
        if query.asset_type is AssetType.EQUITY and any(
            str(value).zfill(6) != query.symbol for value in dataset.frame["股票代码"]
        ):
            raise ValueError("captured security identifiers do not match the query")
        for bar in self.bars:
            if (
                (bar.instrument.symbol, bar.instrument.market, bar.instrument.asset_type)
                != (query.symbol, query.market, query.asset_type)
                or bar.available_at != dataset.retrieved_at
                or bar.source != dataset.source
                or bar.adjustment is not Adjustment.NONE
                or not start <= bar.timestamp.date() <= end
            ):
                raise ValueError("canonical price row does not match its captured query")
        # Reproduce the exact RawDataset fingerprint, including its frame serialization.
        frame = dataset.raw_frame_json or dataset.frame.to_json(
            orient="table", date_format="iso", force_ascii=True
        )
        reject_sensitive_structure(json.loads(frame), path="price_snapshot.frame")
        reject_sensitive_structure(dataset.parameters, path="price_snapshot.parameters")
        content = dataframe_snapshot_bytes(frame, dataset.parameters)
        digest = sha256(content).hexdigest()
        if (
            not dataset.raw_data_hash
            or len(content) > MAX_PRICE_SNAPSHOT_BYTES
            or digest != dataset.content_hash()
        ):
            raise ValueError("price snapshot size or raw fingerprint integrity check failed")
        if self.bars:
            decoded = json.loads(frame, parse_float=Decimal)
            reconstructed = normalize_daily_bars(
                RawDataset(
                    dataset.dataset,
                    pd.DataFrame(decoded["data"], dtype=object),
                    dataset.retrieved_at,
                    dataset.source,
                    dataset.parameters,
                ),
                query,
                self.bars[0].instrument,
            )
            if [daily_bar_content(bar) for bar in reconstructed] != [
                daily_bar_content(bar) for bar in self.bars
            ]:
                raise ValueError("archived price snapshot cannot reproduce the canonical bars")
        identity = f"{dataset.source}:{query.asset_type.value}:{query.symbol}"
        artifact = ProviderArtifact(
            artifact_id=provider_artifact_id(
                provider=self.provider_id,
                dataset=dataset.dataset,
                market=query.market,
                subject=query.symbol,
                source_identity=identity,
                source_reference=dataset.source,
                content_hash=digest,
            ),
            provider=self.provider_id,
            dataset=dataset.dataset,
            market=query.market,
            subject=query.symbol,
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
        for bar in self.bars:
            payload: dict[str, object] = {
                "bar": daily_bar_content(bar),
                "bar_hash": daily_bar_content_hash(bar),
                "artifact_id": artifact.artifact_id,
            }
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=dataset.dataset,
                        market=query.market,
                        subject=query.symbol,
                        available_at=bar.available_at,
                        source_reference=dataset.source,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=dataset.dataset,
                    market=query.market,
                    subject=query.symbol,
                    available_at=bar.available_at,
                    retrieved_at=dataset.retrieved_at,
                    source_reference=dataset.source,
                    payload=payload,
                    raw_data_hash=digest,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.LOW,
                    limitations=tuple(item.description for item in _LIMITATIONS),
                    observed_at=bar.timestamp,
                )
            )
        observation = ProviderArtifactObservation(
            observation_id=provider_artifact_observation_id(
                provider=self.provider_id,
                dataset=dataset.dataset,
                market=query.market,
                subject=query.symbol,
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
            market=query.market,
            subject=query.symbol,
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
            query.market,
            dataset.retrieved_at,
            dataset.source,
            dataset.parameters,
            digest,
            len(dataset.frame),
            tuple(records),
            _LIMITATIONS,
            (artifact,),
            (observation,),
        )
