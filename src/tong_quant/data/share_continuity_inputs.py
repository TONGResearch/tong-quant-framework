"""Visible disclosure inventory for share-count review, never proof of no changes."""

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import CNINFO_DISCLOSURES_DATASET, provider_evidence_id
from tong_quant.data.service import MarketDataService
from tong_quant.data.share_action_reviews import (
    ShareActionDocumentReview,
    inspect_share_action_review,
)
from tong_quant.data.share_capital_inputs import ShareCapitalReview, inspect_share_capital_review
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import SHARE_CONTINUITY_REVIEW_VERSION

_TITLE_GROUPS = {
    "repurchase": ("回购", "repurchase", "buyback"),
    "cancellation": ("注销", "cancellation"),
    "issuance_conversion": ("增发", "配股", "转股", "可转", "issuance", "conversion"),
    "bonus_split_distribution": ("转增", "送股", "分红", "权益分派", "split", "dividend"),
    "employee_or_restricted_plan": ("员工持股", "限制性股票", "解除限售", "employee", "restricted"),
    "share_capital": ("股本", "股份变动", "share capital"),
    "governance_or_periodic_report": (
        "董事会", "股东大会", "年度报告", "季度报告", "board", "report"),
}


def inspect_share_continuity(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, review: ShareCapitalReview, *,
    through: date, as_of: datetime,
    document_reviews: tuple[ShareActionDocumentReview, ...] = (),
) -> dict[str, object]:
    review.__post_init__()
    require_timezone(as_of, "share continuity cutoff")
    cutoff = as_of.astimezone(UTC)
    if (type(through) is not date or through < review.period_end
            or through > cutoff.astimezone(ZoneInfo("Asia/Shanghai")).date()):
        raise ValueError("share continuity requires a visible date not before the base period")
    entries: list[dict[str, object]] = []
    identifiers: set[str] = set()
    triaged: set[str] = set()
    reviewed_identifiers: set[str] = set()
    matched_review_hashes: set[str] = set()
    if (type(document_reviews) is not tuple or len(document_reviews) > 128
            or any(not isinstance(item, ShareActionDocumentReview)
                   or item.subject != review.subject for item in document_reviews)
            or len({item.filing_artifact_id for item in document_reviews})
            != len(document_reviews)):
        raise ValueError("share continuity requires unique same-subject document reviews")
    with store.read_snapshot():
        base = inspect_share_capital_review(store, artifacts, review, as_of=cutoff)
        inspections = sorted((inspect_share_action_review(store, artifacts, item, as_of=cutoff)
                              for item in document_reviews), key=lambda item: item["review_hash"])
        rows = {row["evidence_id"]: row for row in store.provider_evidence_as_of(
            provider="cninfo_direct", dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A, subject=review.subject, as_of=cutoff)}
        records = MarketDataService(store).provider_evidence(
            provider="cninfo_direct", dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A, subject=review.subject, as_of=cutoff)
        for record in sorted(records, key=lambda item: (
            item.retrieved_at.astimezone(UTC), item.evidence_id)):
            # Source-claimed publication visibility alone must not reveal a later capture.
            if any(value is not None and value.astimezone(UTC) > cutoff for value in (
                record.available_at, record.retrieved_at, record.published_at, record.observed_at)):
                continue
            published = record.published_at
            if published is not None and not review.period_end < (
                published.astimezone(ZoneInfo("Asia/Shanghai")).date()) <= through:
                continue
            saved = rows[record.evidence_id]
            batch = store.ingestion_batch(saved["batch_id"])
            batch_receipt = dict(batch) if batch is not None else None
            if batch is not None and batch["completed_at"] is not None:
                completed = datetime.fromisoformat(batch["completed_at"])
                require_timezone(completed, "disclosure batch completion")
                if completed.astimezone(UTC) > cutoff:
                    continue
            reasons = []
            expected_id = provider_evidence_id(
                provider=record.provider, dataset=record.dataset, market=record.market,
                subject=record.subject, available_at=record.available_at,
                source_reference=record.source_reference, payload=record.payload)
            title = record.payload.get("title")
            identifier = record.payload.get("announcement_id")
            if (expected_id != record.evidence_id or record.payload.get("symbol") != review.subject
                    or not isinstance(title, str) or not title.strip()
                    or not isinstance(identifier, str) or not identifier.strip()
                    or published is None):
                reasons.append("Disclosure identity/publication/title contract rejected")
            if batch is None:
                reasons.append("Disclosure ingestion batch missing")
            else:
                parameters = json.loads(batch["parameters_json"])
                started = datetime.fromisoformat(batch["started_at"])
                require_timezone(started, "disclosure batch start")
                if (batch["provider"] != record.provider or batch["dataset"] != record.dataset
                        or batch["status"] != "completed" or batch["completed_at"] is None
                        or batch["raw_response_hash"] != record.raw_data_hash
                        or not isinstance(parameters, dict)
                        or parameters.get("subject") != review.subject
                        or started.astimezone(UTC) != record.retrieved_at.astimezone(UTC)
                        or (batch["completed_at"] is not None and
                            datetime.fromisoformat(batch["completed_at"]).astimezone(UTC)
                            < record.retrieved_at.astimezone(UTC))):
                    reasons.append("Disclosure batch ownership/hash/chronology rejected")
            tags = tuple(name for name, keywords in _TITLE_GROUPS.items()
                         if not reasons and isinstance(title, str)
                         and any(word in title.casefold() for word in keywords))
            if not reasons and isinstance(identifier, str):
                identifiers.add(identifier)
                if tags:
                    triaged.add(identifier)
            entry: dict[str, object] = {
                "record": asdict(record), "batch_receipt": batch_receipt,
                "record_hash": sha256(financial_input_json(asdict(record)).encode()).hexdigest(),
                "binding_status": "REJECTED" if reasons else "METADATA_BATCH_BOUND",
                "binding_reasons": reasons,
                "title_review_tags": tags,
                "document_review_state": "NOT_REVIEWED",
                "effective_share_change": "NOT_ESTABLISHED",
            }
            matching = [item for item in inspections if not reasons and published is not None
                        and item["announcement_id"] == identifier
                        and item["filing_sha256"] == record.payload.get("artifact_content_hash")
                        and record.payload.get("artifact_status") == "captured"
                        and item["source_reference"] == record.payload.get("artifact_url")
                        and item["source_claimed_published_at"] == published.astimezone(UTC)]
            if matching:
                if len(matching) != 1:
                    raise ValueError("ambiguous document review binding")
                annotation = matching[0]
                entry["document_review_state"] = annotation["status"]
                entry["document_review_inspection_hash"] = annotation["inspection_hash"]
                matched_review_hashes.add(annotation["review_hash"])
                reviewed_identifiers.add(str(identifier))
            reject_sensitive_structure(entry, path="share_continuity_entry")
            entries.append(entry)
    output = {
        "subject": review.subject, "market": Market.CHINA_A.value, "as_of": cutoff,
        "base_period_end": review.period_end, "through": through,
        "share_review_inspection_hash": base["inspection_hash"],
        "model_version": SHARE_CONTINUITY_REVIEW_VERSION,
        "status": "PARTIAL_INVENTORY" if entries else "NO_VISIBLE_DISCLOSURE_EVIDENCE",
        "observed_metadata_versions": len(entries), "unique_bound_announcements": len(identifiers),
        "title_triaged_announcements": len(triaged), "document_review_items": entries,
        "manually_reviewed_announcements": len(reviewed_identifiers),
        "document_review_inspections": inspections,
        "action_interval_observations": [
            {"document_inspection_hash": item["inspection_hash"],
             "reference": observation["reference"],
             "effective_date": observation["effective_date"],
             "relation_to_base_interval": (
                 "UNKNOWN_DATE" if observation["effective_date"] is None else
                 "AT_OR_BEFORE_BASE" if observation["effective_date"] <= review.period_end else
                 "WITHIN_INTERVAL" if observation["effective_date"] <= through else
                 "AFTER_THROUGH"),
             "issuer_share_delta": None}
            for item in inspections for observation in item["observations"]],
        "unmatched_document_review_hashes": tuple(
            item["review_hash"] for item in inspections
            if item["review_hash"] not in matched_review_hashes),
        "effective_action_timeline": "NOT_ESTABLISHED",
        "historical_coverage": "NOT_VERIFIED", "current_shares": None, "market_value": None,
        "current_share_count_status": "UNQUALIFIED_CONTINUITY",
        "valuation_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "readiness_promoted": False,
        "limitations": (
            "Publication-window inventory only, not an effective-date corporate-action ledger.",
            "Titles prioritize document review, not implemented actions or share deltas.",
            "Unmatched titles and empty queries do not prove no changes.",
            "Prior announcements with later effective dates, missing pages, corrections, source "
            "availability, share-class semantics and complete coverage require separate review.",
            "Changed captures are versions, not independent actions or provider agreement.",
            "Batch/record consistency does not verify original query bytes, PDF contents or truth.",
            "Only explicitly supplied, visible, exact-PDF-bound annotations mark a document as "
            "manually reviewed, not independently verified or an implemented issuer change.",
            "Metadata-only or changed-PDF versions never inherit an annotation by title/id alone.",
            "No share carry-forward, price multiplication, valuation or decision authority.",
        ),
    }
    return {**output, "inspection_hash": sha256(financial_input_json(output).encode()).hexdigest()}
