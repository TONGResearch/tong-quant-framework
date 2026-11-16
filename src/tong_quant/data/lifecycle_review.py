"""Review record usability without deleting evidence or clearing a security to trade."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256

from tong_quant.data.models import SecurityLifecycleEvent
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, LifecycleEventType
from tong_quant.domain.models import InstrumentStatus, require_timezone
from tong_quant.version import AKSHARE_SUSPENSION_VERSION, LIFECYCLE_REVIEW_VERSION


class LifecycleRecordDisposition(StrEnum):
    REVIEWABLE = "reviewable"
    OBSERVATION_ONLY = "observation_only"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class LifecycleRecordReview:
    record_hash: str
    as_of: datetime
    disposition: LifecycleRecordDisposition
    reasons: tuple[str, ...]
    model_version: str = LIFECYCLE_REVIEW_VERSION


def review_lifecycle_record(
    record: SecurityLifecycleEvent | InstrumentStatus,
    *,
    as_of: datetime,
    effective_on_or_before: date,
) -> LifecycleRecordReview:
    """REVIEWABLE is structural eligibility for review, not source/coverage approval."""
    require_timezone(as_of, "lifecycle review as_of")
    cutoff = as_of.astimezone(UTC)
    errors: list[str] = []
    warnings: list[str] = []
    if record.available_at.astimezone(UTC) > cutoff:
        errors.append("future_availability")
    if (record.instrument.available_at is not None
            and record.instrument.available_at.astimezone(UTC) > cutoff):
        errors.append("future_instrument_snapshot")
    effective_date = (
        record.effective_date
        if isinstance(record, SecurityLifecycleEvent)
        else record.effective_from
    )
    if effective_date > effective_on_or_before:
        errors.append("future_effective_date")
    if not record.source.strip():
        errors.append("source_missing")
    if len(record.raw_data_hash) != 64 or any(
        char not in "0123456789abcdef" for char in record.raw_data_hash
    ):
        errors.append("raw_hash_invalid")
    if isinstance(record, InstrumentStatus):
        if record.provider_dataset == "instrument_status_suspended" or (
            "stock_zh_a_stop_em" in record.source
        ):
            errors.append("legacy_delisted_quote_status")
        if record.effective_to is not None and record.effective_to < effective_on_or_before:
            errors.append("status_interval_ended")
    elif (
        record.provider_dataset == "security_lifecycle_suspension"
        or record.source.startswith("akshare:stock_tfp_em")
        or (record.source == "akshare" and record.event_type is LifecycleEventType.TRADING_RESUMED)
    ):
        if record.event_type is LifecycleEventType.TRADING_RESUMED:
            errors.append("unconfirmed_akshare_resumption")
        if record.details.get("normalization_version") != AKSHARE_SUSPENSION_VERSION:
            errors.append("legacy_suspension_normalization")
        warnings.append("partial_suspension_observation")
    if record.trust_level in {DataTrustLevel.UNKNOWN, DataTrustLevel.LOW}:
        warnings.append("trust_insufficient_for_historical_clearance")
    if record.availability_precision in {
        AvailabilityPrecision.UNKNOWN,
        AvailabilityPrecision.ESTIMATED,
    }:
        warnings.append("availability_precision_unverified")
    if record.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME:
        warnings.append("retrieval_time_not_original_publication")
    disposition = (
        LifecycleRecordDisposition.QUARANTINED
        if errors
        else LifecycleRecordDisposition.OBSERVATION_ONLY
        if warnings
        else LifecycleRecordDisposition.REVIEWABLE
    )
    content = json.dumps(asdict(record), default=str, sort_keys=True, separators=(",", ":"))
    return LifecycleRecordReview(
        sha256(content.encode("utf-8")).hexdigest(),
        as_of,
        disposition,
        tuple(sorted(set((*errors, *warnings)))),
    )
