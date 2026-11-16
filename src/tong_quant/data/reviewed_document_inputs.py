"""Immutable overseas manual-review receipt for existing unscored Financial research."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_review_inputs import read_global_document_review_inputs
from tong_quant.data.providers.global_document_reviews import parse_global_document_review
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_DOCUMENT_REVIEW_VERSION

_SECTORS = frozenset({"nonfinancial", "bank", "securities", "insurance", "unknown"})
_DENIED = ("financial_scoring_authorized", "investment_scoring_authorized",
    "historical_replay_eligible", "validation_authorized", "execution_authorized",
    "canonical_population_authorized", "accounting_definition_qualified",
    "source_location_verified", "independent_review", "issuer_to_instrument_verified")


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("reviewed-document input requires explicit timestamps")
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, "reviewed-document timestamp")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ReviewedDocumentResearchInput:
    """A retained-reader receipt, not canonical facts, source authentication or policy approval."""

    receipt_json: str
    sector_profile: str

    def __post_init__(self) -> None:
        self.validate_context()

    def document(self) -> dict[str, Any]:
        if not isinstance(self.receipt_json, str) or len(self.receipt_json.encode()) > 2_097_152:
            raise ValueError("reviewed-document receipt outside supported bounds")
        document = json.loads(self.receipt_json)
        if not isinstance(document, dict):
            raise ValueError("reviewed-document receipt must be an object")
        return document

    @property
    def as_of(self) -> datetime:
        return _utc(self.document().get("as_of"))

    def validate_context(self, *, symbol: str | None = None, market: Market | None = None,
                         as_of: datetime | None = None) -> None:
        document = self.document()
        reject_sensitive_structure(document, path="reviewed_document_research_input")
        body = {key: value for key, value in document.items() if key != "input_hash"}
        if (self.sector_profile not in _SECTORS
                or self.receipt_json != financial_input_json(document)
                or document.get("model_version") != GLOBAL_DOCUMENT_REVIEW_VERSION
                or sha256(financial_input_json(body).encode()).hexdigest()
                != document.get("input_hash")
                or document.get("trust_ceiling") != "LOW"
                or document.get("availability_precision") != "retrieval_time"
                or any(document.get(name) is not False for name in _DENIED)):
            raise ValueError("reviewed-document integrity or authority mismatch")
        receipt_market = Market(document["market"])
        validate_yahoo_equity_subject(receipt_market, document["subject"])
        validate_document_url(receipt_market, document["document_url"])
        cutoff = self.as_of
        if as_of is not None:
            require_timezone(as_of, "reviewed-document research cutoff")
        if ((symbol is not None and document["subject"] != symbol)
                or (market is not None and receipt_market is not market)
                or (as_of is not None and cutoff != as_of.astimezone(UTC))):
            raise ValueError("reviewed-document research context mismatch")
        captures, observations = document.get("captures"), document.get("observations")
        if (not isinstance(captures, list) or len(captures) > 10000
                or not isinstance(observations, list) or len(observations) > 64
                or any(not isinstance(row, dict) or _utc(row.get("available_at")) > cutoff
                       for row in captures)):
            raise ValueError("reviewed-document rows or visibility mismatch")
        status = document.get("status")
        if status in {"missing", "rejected_or_ambiguous"}:
            if (document.get("source_bound") is not False or observations
                    or status == "missing" and captures):
                raise ValueError("unusable reviewed-document input contains usable observations")
            return
        if (status != "MANUAL_TRANSCRIPTION_UNQUALIFIED"
                or document.get("source_bound") is not True or not captures):
            raise ValueError("unsupported reviewed-document input state")
        latest = max(_utc(row["available_at"]) for row in captures)
        selected = [row for row in captures if _utc(row["available_at"]) == latest]
        if (len(selected) != 1 or selected[0]["evidence_id"] != document.get("selected_evidence_id")
                or _utc(document.get("recorded_at")) != latest):
            raise ValueError("reviewed-document selected capture mismatch")
        raw = document["review"]
        metadata = {key: value for key, value in raw.items() if key != "rows"}
        review = parse_global_document_review({"review": metadata, "rows": raw["rows"]})
        if (review.subject != document["subject"] or review.market is not receipt_market
                or review.document_url != document["document_url"]
                or review.reviewed_at.astimezone(UTC) > latest
                or observations != [row.observation() for row in review.rows]):
            raise ValueError("reviewed-document annotations or observations mismatch")


def read_reviewed_document_research_input(store: SQLiteStore, artifacts: FileSystemArtifactStore,
    subject: str, market: Market, document_url: str, *, as_of: datetime, sector_profile: str,
) -> ReviewedDocumentResearchInput:
    """Current source/artifact/batch checks remain with the exact retained reader."""
    receipt = read_global_document_review_inputs(store, artifacts, market, subject,
                                               document_url, as_of=as_of)
    return ReviewedDocumentResearchInput(financial_input_json(receipt), sector_profile)
