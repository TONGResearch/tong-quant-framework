"""Reconstruct the ordinary SSE schedule; exceptional closure coverage stays unknown."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calendar_evidence import SSECalendarNoticeProfile
from tong_quant.data.providers.contracts import (
    SSE_CALENDAR_DATASET,
    SSE_CALENDAR_PROVIDER,
    ProviderEvidenceRecord,
    provider_artifact_id,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.markets.sse_references import SSEReferenceBundle, evidence_hash
from tong_quant.version import SSE_CALENDAR_PLAN_VERSION


@dataclass(frozen=True, slots=True)
class SSEPlannedCalendarDay:
    trade_date: date
    is_open: bool | None
    basis: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SSECalendarPlan:
    start: date
    end: date
    as_of: datetime
    days: tuple[SSEPlannedCalendarDay, ...]
    notice_evidence: tuple[ProviderEvidenceRecord, ...]
    reference_hash: str
    notice_profile_hash: str
    available_at: datetime | None
    warnings: tuple[str, ...]
    exchange: str = "SSE"
    trust_level: DataTrustLevel = DataTrustLevel.MEDIUM
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.RETRIEVAL_TIME
    model_version: str = SSE_CALENDAR_PLAN_VERSION

    @property
    def missing_dates(self) -> tuple[date, ...]:
        return tuple(day.trade_date for day in self.days if day.is_open is None)

    @property
    def plan_hash(self) -> str:
        return evidence_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class SSECalendarPlanBuilder:
    references: SSEReferenceBundle
    annual_notice: SSECalendarNoticeProfile
    artifacts: FileSystemArtifactStore

    def build(
        self,
        notices: tuple[ProviderEvidenceRecord, ...],
        *,
        start: date,
        end: date,
        as_of: datetime,
    ) -> SSECalendarPlan:
        require_timezone(as_of, "calendar plan as_of")
        if not 0 <= (end - start).days < 366:
            raise ValueError("calendar plan requires an ordered window of at most 366 days")
        profile, rules = self.annual_notice, self.references
        if profile.notice_scope != "annual_holidays" or profile.calendar_year != 2026:
            raise ValueError("calendar plan requires reviewed 2026 annual holiday claims")
        if profile.reviewed_at > as_of or rules.available_at > as_of:
            raise ValueError("calendar plan sources are not visible at the requested time")
        if any(record.available_at > as_of for record in notices):
            raise ValueError("calendar plan rejects future notice evidence")
        warnings = [
            "ordinary_schedule_only",
            "exceptional_closure_coverage_unverified",
            "settlement_and_security_status_not_inferred",
        ]
        usable = True
        if as_of >= min(profile.review_expires_at, rules.review_expires_at):
            warnings.append("calendar_source_review_expired")
            usable = False
        selected = tuple(
            sorted(
                (
                    record
                    for record in notices
                    if record.payload.get("profile_sha256") == profile.profile_sha256
                ),
                key=lambda item: item.evidence_id,
            )
        )
        expected = dict(profile.sessions)
        observed: set[date] = set()
        artifact_id = provider_artifact_id(
            provider=SSE_CALENDAR_PROVIDER,
            dataset=SSE_CALENDAR_DATASET,
            market=Market.CHINA_A,
            subject="SSE",
            source_identity=profile.source_url,
            source_reference=profile.source_url,
            content_hash=profile.content_sha256,
        )
        for record in selected:
            payload = record.payload
            try:
                day = date.fromisoformat(str(payload.get("trade_date", "")))
                if (
                    (record.provider, record.dataset, record.market, record.subject)
                    != (SSE_CALENDAR_PROVIDER, SSE_CALENDAR_DATASET, Market.CHINA_A, "SSE")
                    or record.source_reference != profile.source_url
                    or record.raw_data_hash != profile.content_sha256
                    or record.available_at != record.retrieved_at
                    or record.available_at < profile.reviewed_at
                    or record.trust_level
                    not in {DataTrustLevel.MEDIUM, DataTrustLevel.HIGH, DataTrustLevel.VERIFIED}
                    or record.availability_precision is not AvailabilityPrecision.RETRIEVAL_TIME
                    or payload.get("artifact_id") != artifact_id
                    or payload.get("exchange") != "SSE"
                    or type(payload.get("is_open")) is not bool
                    or day not in expected
                    or payload["is_open"] != expected[day]
                ):
                    raise ValueError("invalid annual evidence")
                observed.add(day)
            except ValueError:
                usable = False
                warnings.append("annual_notice_evidence_invalid")
        if observed != set(expected):
            usable = False
            warnings.append("annual_notice_evidence_incomplete")
        try:
            self.artifacts.read_content(
                profile.content_sha256, "text/html", max_bytes=2 * 1024 * 1024
            )
        except (OSError, ValueError):
            usable = False
            warnings.append("annual_notice_artifact_unverified")
        available_at = max((record.available_at for record in selected), default=None)
        if available_at is not None:
            available_at = max(
                available_at,
                profile.reviewed_at,
                rules.available_at,
                *(record.available_at for record in notices),
            )
        days: list[SSEPlannedCalendarDay] = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            is_open: bool | None = None
            basis = "source_evidence_unavailable"
            ids = tuple(
                record.evidence_id
                for record in selected
                if record.payload.get("trade_date") == day.isoformat()
            )
            if usable and day.year == profile.calendar_year and day >= rules.effective_from:
                is_open = expected.get(day, day.weekday() < 5)
                basis = "explicit_annual_notice" if day in expected else "reviewed_weekly_rule"
                for record in notices:
                    if record.payload.get("trade_date") == day.isoformat() and (
                        record.payload.get("exchange") != "SSE"
                        or type(record.payload.get("is_open")) is not bool
                        or record.payload["is_open"] != is_open
                    ):
                        is_open = None
                        basis = "notice_conflict"
                        warnings.append("calendar_notice_conflict")
                        break
            elif day.year != profile.calendar_year or day < rules.effective_from:
                basis = "outside_reviewed_rule_period"
            days.append(SSEPlannedCalendarDay(day, is_open, basis, ids))
        return SSECalendarPlan(
            start,
            end,
            as_of,
            tuple(days),
            tuple(sorted(notices, key=lambda item: item.evidence_id)),
            rules.reference_hash,
            profile.profile_sha256,
            available_at,
            tuple(sorted(set(warnings))),
            trust_level=DataTrustLevel.MEDIUM if usable else DataTrustLevel.UNKNOWN,
        )
