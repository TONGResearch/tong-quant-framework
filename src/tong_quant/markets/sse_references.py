"""Verified document references for a limited SSE research calculation profile."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlsplit

from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.markets.capabilities import (
    MarketRuleCapability,
    MarketRuleEvidence,
    MarketRuleScope,
)

SSE_PROFILE_VERSION = "sse-main-board-2026-v1"
SSE_PILOT_SCOPE = MarketRuleScope(Market.CHINA_A, "SSE", "main", "cash")
SSE_EXCHANGE_IDENTIFIERS = frozenset({"SSE", "XSHG"})


def evidence_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, default=str, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def require_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("evidence requires a lowercase SHA-256 hash")


def require_sse_url(value: str) -> None:
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or url.netloc != "www.sse.com.cn"
        or not url.path.startswith("/lawandrules/")
        or url.query
        or url.fragment
    ):
        raise ValueError("rule references require approved official SSE HTTPS paths")


@dataclass(frozen=True, slots=True)
class ReviewedRuleDocument:
    role: str
    source_url: str
    content_sha256: str

    def __post_init__(self) -> None:
        if self.role not in {"rules", "deferred", "odd_lots"}:
            raise ValueError("unsupported SSE rule-document role")
        require_sse_url(self.source_url)
        require_sha256(self.content_sha256)


@dataclass(frozen=True, slots=True)
class SSEReferenceBundle:
    profile_version: str
    effective_from: date
    available_at: datetime
    review_expires_at: datetime
    documents: tuple[ReviewedRuleDocument, ...]
    capture_hash: str
    trust_level: DataTrustLevel

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")
        require_timezone(self.review_expires_at, "review_expires_at")
        require_sha256(self.capture_hash)
        if self.profile_version != SSE_PROFILE_VERSION or self.effective_from != date(2026, 7, 6):
            raise ValueError("unsupported SSE rule profile or effective date")
        if self.available_at >= self.review_expires_at:
            raise ValueError("SSE references require renewed review")
        if len(self.documents) != 3 or {doc.role for doc in self.documents} != {
            "rules",
            "deferred",
            "odd_lots",
        }:
            raise ValueError(
                "SSE references require rules, deferred provisions, and odd-lot sources"
            )
        if not isinstance(self.trust_level, DataTrustLevel) or self.trust_level not in {
            DataTrustLevel.HIGH,
            DataTrustLevel.VERIFIED,
        }:
            raise ValueError("SSE reference trust requires an explicit source review")

    @property
    def reference_hash(self) -> str:
        return evidence_hash(
            {
                "profile_version": self.profile_version,
                "effective_from": self.effective_from,
                "available_at": self.available_at,
                "review_expires_at": self.review_expires_at,
                "capture_hash": self.capture_hash,
                "trust_level": self.trust_level.value,
                "documents": sorted(
                    ((doc.role, doc.source_url, doc.content_sha256) for doc in self.documents),
                ),
            }
        )

    def evidence(self, *, as_of: datetime) -> tuple[MarketRuleEvidence, ...]:
        require_timezone(as_of, "as_of")
        if not self.available_at <= as_of < self.review_expires_at:
            raise MarketRuleEvidenceUnavailableError(
                "SSE reference capture is future or review expired"
            )
        return tuple(
            MarketRuleEvidence(
                evidence_id=f"{self.profile_version}:{capability.value}",
                scope=SSE_PILOT_SCOPE,
                capability=capability,
                rule_version=self.profile_version,
                effective_from=self.effective_from,
                effective_to=None,
                available_at=self.available_at,
                source_reference=f"reviewed-sse-reference:{self.reference_hash}",
                content_sha256=self.reference_hash,
                trust_level=self.trust_level,
                availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            )
            for capability in (
                MarketRuleCapability.QUANTITY,
                MarketRuleCapability.SETTLEMENT,
                MarketRuleCapability.PRICE_LIMIT,
            )
        )
