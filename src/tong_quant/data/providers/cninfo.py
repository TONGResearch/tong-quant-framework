from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.data.models import ProviderResponse
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

CNINFO_DISCLOSURES_DATASET = "china_disclosures"
SHANGHAI = ZoneInfo("Asia/Shanghai")


class CnInfoTransport(Protocol):
    def fundamental_disclosures(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category: str = "",
    ) -> ProviderResponse: ...


@dataclass(slots=True)
class CnInfoEvidenceAdapter:
    transport: CnInfoTransport
    provider_id: str = "cninfo_via_akshare"

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset=CNINFO_DISCLOSURES_DATASET,
                markets=(Market.CHINA_A,),
                status=ProviderCapabilityStatus.DEGRADED,
                trust_level=DataTrustLevel.MEDIUM,
                availability_precision=AvailabilityPrecision.EXACT,
                historical_continuity=False,
                required_parameters=("start_date", "end_date"),
                limitations=_base_limitations(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != CNINFO_DISCLOSURES_DATASET:
            raise ValueError("CNInfo adapter only supports China disclosure evidence")
        if request.market != Market.CHINA_A:
            raise ValueError("CNInfo disclosure evidence is China A specific")
        response = self.transport.fundamental_disclosures(
            request.subject,
            start_date=_compact_date(request.parameters["start_date"]),
            end_date=_compact_date(request.parameters["end_date"]),
            category=request.parameters.get("category", ""),
        )
        dataset = response.dataset
        raw_hash = dataset.content_hash()
        limitations = list(_base_limitations())
        records: list[ProviderEvidenceRecord] = []
        missing_timestamp = 0
        future_timestamp = 0
        for row in dataset.frame.to_dict(orient="records"):
            published_at = _published_at(row.get("公告时间"))
            if published_at is None:
                missing_timestamp += 1
                continue
            if published_at > dataset.retrieved_at:
                future_timestamp += 1
                continue
            subject = _text(row.get("代码")) or request.subject
            title = _text(row.get("公告标题"))
            source_reference = _text(row.get("公告链接"))
            announcement_id = _announcement_id(source_reference)
            payload: dict[str, object] = {
                "symbol": subject,
                "name": _text(row.get("简称")),
                "title": title,
                "announcement_id": announcement_id,
                "announcement_time": published_at.isoformat(),
                "category": request.parameters.get("category", ""),
            }
            record_limitations = tuple(item.description for item in _base_limitations())
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject=subject,
                        available_at=published_at,
                        source_reference=source_reference,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject=subject,
                    observed_at=published_at,
                    published_at=published_at,
                    available_at=published_at,
                    retrieved_at=dataset.retrieved_at,
                    source_reference=source_reference,
                    payload=payload,
                    raw_data_hash=raw_hash,
                    availability_precision=AvailabilityPrecision.EXACT,
                    trust_level=DataTrustLevel.MEDIUM,
                    limitations=record_limitations,
                )
            )
        if missing_timestamp:
            limitations.append(
                EvidenceLimitation(
                    code="cninfo_missing_announcement_timestamp",
                    description=(
                        f"{missing_timestamp} CNInfo rows lacked a usable announcement timestamp"
                    ),
                    trust_level=DataTrustLevel.LOW,
                )
            )
        if future_timestamp:
            limitations.append(
                EvidenceLimitation(
                    code="cninfo_future_timestamp_rejected",
                    description=(
                        f"{future_timestamp} CNInfo rows were rejected because their "
                        "announcement timestamp followed retrieval"
                    ),
                    trust_level=DataTrustLevel.UNKNOWN,
                )
            )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=dataset.retrieved_at,
            source=dataset.source,
            parameters={
                "subject": request.subject,
                **request.parameters,
            },
            raw_data_hash=raw_hash,
            raw_record_count=len(dataset.frame),
            records=tuple(records),
            limitations=tuple(limitations),
        )


def _base_limitations() -> tuple[EvidenceLimitation, ...]:
    return (
        EvidenceLimitation(
            code="cninfo_akshare_transport",
            description=(
                "CNInfo evidence is transported through AKShare; direct-source parity "
                "has not been independently verified"
            ),
            trust_level=DataTrustLevel.MEDIUM,
        ),
        EvidenceLimitation(
            code="cninfo_historical_continuity_unverified",
            description="CNInfo historical disclosure continuity has not been proven",
            trust_level=DataTrustLevel.MEDIUM,
        ),
    )


def _published_at(value: Any) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(SHANGHAI)
    else:
        timestamp = timestamp.tz_convert(SHANGHAI)
    return timestamp.to_pydatetime()


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _announcement_id(source_reference: str) -> str:
    if not source_reference:
        return ""
    values = parse_qs(urlparse(source_reference).query).get("announcementId", ())
    return values[0].strip() if values else ""


def _compact_date(value: str) -> str:
    normalized = value.strip()
    if len(normalized) == 8 and normalized.isdigit():
        date.fromisoformat(
            f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
        )
        return normalized
    return date.fromisoformat(normalized).strftime("%Y%m%d")


__all__ = ["CNINFO_DISCLOSURES_DATASET", "CnInfoEvidenceAdapter", "CnInfoTransport"]
