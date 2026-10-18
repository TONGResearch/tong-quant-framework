"""Pinned, reviewed notice assertions, not an inferred full exchange calendar."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

import requests

from tong_quant.data.calendar_evidence import (
    SSECalendarNoticeProfile as SSECalendarNoticeProfile,
)
from tong_quant.data.calendar_evidence import require_notice_url as require_notice_url
from tong_quant.data.providers.contracts import (
    SSE_CALENDAR_DATASET,
    SSE_CALENDAR_PROVIDER,
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
from tong_quant.domain.models import require_timezone
from tong_quant.version import SSE_CALENDAR_NOTICE_VERSION

MAX_NOTICE_BYTES = 2 * 1024 * 1024


def fetch_notice(url: str) -> bytes:
    require_notice_url(url)
    with requests.get(url, stream=True, allow_redirects=False, timeout=(5, 20)) as response:
        if response.status_code != 200:
            raise ValueError("calendar notice fetch failed or redirected")
        content = bytearray()
        for chunk in response.iter_content(65536):
            content.extend(chunk)
            if len(content) > MAX_NOTICE_BYTES:
                raise ValueError("calendar notice exceeds capture size limit")
        return bytes(content)



_LIMITATIONS = (
    EvidenceLimitation(
        "sse_calendar_partial_notice",
        "Explicit notice dates only; unlisted dates, later emergency closures "
        "and settlement are unknown",
        DataTrustLevel.MEDIUM,
    ),
    EvidenceLimitation(
        "sse_calendar_retrieval_visibility",
        "Publication date has no authenticated clock time; visibility starts at capture, "
        "not publication",
        DataTrustLevel.MEDIUM,
    ),
    EvidenceLimitation(
        "sse_calendar_no_trust_promotion",
        "Pinned source assertions remain MEDIUM trust; "
        "they do not certify a complete trading calendar",
        DataTrustLevel.MEDIUM,
    ),
)


@dataclass(slots=True)
class SSECalendarNoticeAdapter:
    profile: SSECalendarNoticeProfile
    fetch_bytes: Callable[[str], bytes] = fetch_notice
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    provider_id: str = SSE_CALENDAR_PROVIDER

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                self.provider_id,
                SSE_CALENDAR_DATASET,
                (Market.CHINA_A,),
                ProviderCapabilityStatus.DEGRADED,
                DataTrustLevel.MEDIUM,
                AvailabilityPrecision.RETRIEVAL_TIME,
                False,
                (),
                _LIMITATIONS,
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if (request.dataset, request.market, request.subject) != (
            SSE_CALENDAR_DATASET,
            Market.CHINA_A,
            "SSE",
        ) or request.parameters:
            raise ValueError("calendar notice supports only explicit SSE China A evidence")
        started_at = self.clock()
        self._require_current_review(started_at)
        content = self.fetch_bytes(self.profile.source_url)
        if not content or len(content) > MAX_NOTICE_BYTES:
            raise ValueError("calendar notice is empty or oversized")
        if sha256(content).hexdigest() != self.profile.content_sha256:
            raise ValueError("calendar notice changed; source review is required")
        retrieved_at = self.clock()
        self._require_current_review(retrieved_at)
        if retrieved_at < started_at:
            raise ValueError("calendar capture clock moved backwards")
        artifact = ProviderArtifact(
            artifact_id=provider_artifact_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject="SSE",
                source_identity=self.profile.source_url,
                source_reference=self.profile.source_url,
                content_hash=self.profile.content_sha256,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject="SSE",
            source_identity=self.profile.source_url,
            source_reference=self.profile.source_url,
            # Conservative bound; the source's actual publication clock is unknown.
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            content_hash=self.profile.content_sha256,
            media_type="text/html",
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.MEDIUM,
            content=content,
        )
        records: list[ProviderEvidenceRecord] = []
        for day, is_open in self.profile.sessions:
            payload: dict[str, object] = {
                "exchange": "SSE",
                "trade_date": day.isoformat(),
                "is_open": is_open,
                "assertion_kind": "explicit_notice_date",
                "source_publication_date": self.profile.source_publication_date.isoformat(),
                "profile_sha256": self.profile.profile_sha256,
                "profile_version": SSE_CALENDAR_NOTICE_VERSION,
                "reviewed_at": self.profile.reviewed_at.isoformat(),
                "review_expires_at": self.profile.review_expires_at.isoformat(),
                "artifact_id": artifact.artifact_id,
            }
            records.append(
                ProviderEvidenceRecord(
                    evidence_id=provider_evidence_id(
                        provider=self.provider_id,
                        dataset=request.dataset,
                        market=request.market,
                        subject="SSE",
                        available_at=retrieved_at,
                        source_reference=self.profile.source_url,
                        payload=payload,
                    ),
                    provider=self.provider_id,
                    dataset=request.dataset,
                    market=request.market,
                    subject="SSE",
                    available_at=retrieved_at,
                    retrieved_at=retrieved_at,
                    source_reference=self.profile.source_url,
                    payload=payload,
                    raw_data_hash=self.profile.content_sha256,
                    availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                    trust_level=DataTrustLevel.MEDIUM,
                    limitations=tuple(item.description for item in _LIMITATIONS),
                    observed_at=retrieved_at,
                )
            )
        observation = ProviderArtifactObservation(
            observation_id=provider_artifact_observation_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject="SSE",
                source_identity=self.profile.source_url,
                source_reference=self.profile.source_url,
                published_at=retrieved_at,
                retrieved_at=retrieved_at,
                status=ProviderArtifactStatus.CAPTURED,
                artifact_id=artifact.artifact_id,
                error_code="",
                related_source_identities=(),
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject="SSE",
            source_identity=self.profile.source_url,
            source_reference=self.profile.source_url,
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            status=ProviderArtifactStatus.CAPTURED,
            artifact_id=artifact.artifact_id,
            error_code="",
        )
        return ProviderEvidenceBatch(
            self.provider_id,
            request.dataset,
            request.market,
            retrieved_at,
            self.profile.source_url,
            {"subject": "SSE", "profile_sha256": self.profile.profile_sha256},
            self.profile.content_sha256,
            len(records),
            tuple(records),
            _LIMITATIONS,
            (artifact,),
            (observation,),
        )

    def _require_current_review(self, at: datetime) -> None:
        require_timezone(at, "calendar capture time")
        if not self.profile.reviewed_at <= at < self.profile.review_expires_at:
            raise ValueError("calendar notice review is not current")
