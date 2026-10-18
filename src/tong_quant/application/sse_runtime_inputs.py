"""Read existing PIT inputs without manufacturing market-rule authority."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from tong_quant.application.sse_calendar_plan import SSECalendarPlan, SSECalendarPlanBuilder
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.lifecycle_review import (
    LifecycleRecordDisposition,
    LifecycleRecordReview,
    review_lifecycle_record,
)
from tong_quant.data.models import SecurityLifecycleEvent
from tong_quant.data.price_evidence import matches_daily_bar
from tong_quant.data.providers.contracts import (
    AKSHARE_PRICE_PROVIDER,
    ASHARE_DAILY_DATASET,
    SSE_CALENDAR_DATASET,
    SSE_CALENDAR_PROVIDER,
    ProviderEvidenceRecord,
)
from tong_quant.data.service import MarketDataService
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    InstrumentCategory,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import (
    Bar,
    CorporateAction,
    Instrument,
    InstrumentStatus,
    TradingSession,
    require_timezone,
)
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_main_board import SHANGHAI
from tong_quant.markets.sse_references import (
    SSE_EXCHANGE_IDENTIFIERS,
    SSE_PILOT_SCOPE,
    evidence_hash,
    require_sha256,
)
from tong_quant.version import SSE_RUNTIME_INPUT_VERSION


@dataclass(frozen=True, slots=True)
class SSERuntimeInputGap:
    code: str
    explanation: str


@dataclass(frozen=True, slots=True)
class SSERuntimeInputSnapshot:
    symbol: str
    query: MarketRuleQuery
    calendar_start: date
    instrument: Instrument | None
    status: InstrumentStatus | None
    sessions: tuple[TradingSession, ...]
    missing_calendar_dates: tuple[date, ...]
    previous_session: date | None
    previous_close: Bar | None
    corporate_actions: tuple[CorporateAction, ...]
    gaps: tuple[SSERuntimeInputGap, ...]
    calendar_notices: tuple[ProviderEvidenceRecord, ...] = ()
    price_evidence: tuple[ProviderEvidenceRecord, ...] = ()
    calendar_plan: SSECalendarPlan | None = None
    lifecycle_events: tuple[SecurityLifecycleEvent, ...] = ()
    lifecycle_evidence: tuple[ProviderEvidenceRecord, ...] = ()
    lifecycle_reviews: tuple[LifecycleRecordReview, ...] = ()
    status_review: LifecycleRecordReview | None = None
    model_version: str = SSE_RUNTIME_INPUT_VERSION

    @property
    def input_hash(self) -> str:
        return evidence_hash(asdict(self))

    @property
    def previous_close_evidence(self) -> tuple[ProviderEvidenceRecord, ...]:
        if self.previous_close is None:
            return ()
        return tuple(
            record
            for record in self.price_evidence
            if matches_daily_bar(record, self.previous_close)
        )

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            **asdict(self),
            "input_hash": self.input_hash,
            "calendar_plan_hash": (
                None if self.calendar_plan is None else self.calendar_plan.plan_hash
            ),
            "calendar_plan_missing_dates": (
                None if self.calendar_plan is None else self.calendar_plan.missing_dates
            ),
            "previous_close_evidence_ids": [
                record.evidence_id for record in self.previous_close_evidence
            ],
            "boundary": "Input inventory only; not PIT readiness or calculation/trading approval",
        }
        reject_sensitive_structure(record, path="sse_runtime_inputs")
        return record


class SSERuntimeInputReader:
    def __init__(
        self, data: MarketDataService, *, calendar_builder: SSECalendarPlanBuilder | None = None
    ) -> None:
        self._data = data
        self._calendar_builder = calendar_builder

    def read(
        self,
        symbol: str,
        query: MarketRuleQuery,
        *,
        calendar_start: date,
    ) -> SSERuntimeInputSnapshot:
        if query.scope != SSE_PILOT_SCOPE:
            raise ValueError("only the SSE main-board cash-account pilot is supported")
        if query.as_of.astimezone(SHANGHAI).date() != query.trade_date:
            raise ValueError("decision time must belong to the requested SSE date")
        if len(symbol) != 6 or not symbol.isascii() or not symbol.isdigit():
            raise ValueError("an explicit six-digit security identifier is required")
        if not 1 <= (query.trade_date - calendar_start).days <= 366:
            raise ValueError("calendar window must start 1 to 366 days before decision date")
        # All component reads share one SQLite snapshot, including nested instrument lookups.
        with self._data.read_snapshot():
            instrument = self._data.instrument(
                symbol,
                Market.CHINA_A,
                AssetType.EQUITY,
                as_of=query.as_of,
            )
            status = self._data.instrument_status(
                symbol,
                Market.CHINA_A,
                AssetType.EQUITY,
                on_date=query.trade_date,
                as_of=query.as_of,
            )
            sessions = tuple(
                self._data.trading_sessions(
                    Market.CHINA_A,
                    calendar_start,
                    query.trade_date,
                    as_of=query.as_of,
                )
            )
            bars = self._data.daily_bars(
                symbol,
                Market.CHINA_A,
                AssetType.EQUITY,
                calendar_start,
                query.trade_date - timedelta(days=1),
                as_of=query.as_of,
            )
            actions = tuple(
                self._data.corporate_actions(
                    symbol,
                    Market.CHINA_A,
                    AssetType.EQUITY,
                    calendar_start,
                    query.trade_date,
                    as_of=query.as_of,
                )
            )
            notices = self._data.provider_evidence(
                provider=SSE_CALENDAR_PROVIDER,
                dataset=SSE_CALENDAR_DATASET,
                market=Market.CHINA_A,
                subject="SSE",
                as_of=query.as_of,
            )
            price_records = self._data.provider_evidence(
                provider=AKSHARE_PRICE_PROVIDER,
                dataset=ASHARE_DAILY_DATASET,
                market=Market.CHINA_A,
                subject=symbol,
                as_of=query.as_of,
            )
            lifecycle_events = tuple(self._data.security_lifecycle(
                symbol, Market.CHINA_A, AssetType.EQUITY, as_of=query.as_of,
                effective_on_or_before=query.trade_date,
            ))
            lifecycle_evidence = self._data.provider_evidence(
                provider="akshare", dataset="security_lifecycle_suspension",
                market=Market.CHINA_A, subject=symbol, as_of=query.as_of,
            )
            calendar_plan = (
                None
                if self._calendar_builder is None
                else self._calendar_builder.build(
                    notices, start=calendar_start, end=query.trade_date, as_of=query.as_of
                )
            )
        dates = {session.trade_date for session in sessions}
        missing_dates = tuple(
            day
            for offset in range((query.trade_date - calendar_start).days + 1)
            if (day := calendar_start + timedelta(days=offset)) not in dates
        )
        previous_session = max(
            (
                item.trade_date
                for item in sessions
                if item.is_open and item.trade_date < query.trade_date
            ),
            default=None,
        )
        previous_close = next(
            (bar for bar in bars if bar.timestamp.astimezone(SHANGHAI).date() == previous_session),
            None,
        )
        price_evidence = tuple(
            record
            for record in price_records
            if record.observed_at is None
            or (calendar_start <= record.observed_at.astimezone(SHANGHAI).date() < query.trade_date)
        )
        gaps: list[SSERuntimeInputGap] = []
        status_review = (
            None if status is None else review_lifecycle_record(
                status, as_of=query.as_of, effective_on_or_before=query.trade_date
            )
        )
        lifecycle_reviews = tuple(
            review_lifecycle_record(event, as_of=query.as_of,
                                    effective_on_or_before=query.trade_date)
            for event in lifecycle_events
        )

        def gap(code: str, explanation: str) -> None:
            gaps.append(SSERuntimeInputGap(code, explanation))

        if calendar_plan is not None:
            gap(
                "calendar_plan_not_authoritative",
                "Ordinary schedule is separate from actual/emergency closures and settlement",
            )
            if calendar_plan.missing_dates:
                gap("calendar_plan_incomplete", "Some planned dates lack usable source evidence")
            planned = {day.trade_date: day.is_open for day in calendar_plan.days}
            if any(
                planned.get(item.trade_date) is not None
                and planned[item.trade_date] != item.is_open
                for item in sessions
            ):
                gap(
                    "calendar_plan_raw_conflict",
                    "Raw sessions disagree with reviewed planned dates",
                )
        calendar_notices: list[ProviderEvidenceRecord] = []
        assertions: dict[date, set[bool]] = {}
        invalid_notice = False
        expired_notice = False
        for notice in notices:
            payload = notice.payload
            try:
                day = date.fromisoformat(str(payload.get("trade_date", "")))
                if payload.get("exchange") != "SSE" or type(payload.get("is_open")) is not bool:
                    raise ValueError("invalid scoped calendar assertion")
                expires = datetime.fromisoformat(str(payload.get("review_expires_at", "")))
                require_timezone(expires, "calendar notice review_expires_at")
            except ValueError:
                calendar_notices.append(notice)
                invalid_notice = True
                continue
            if calendar_start <= day <= query.trade_date:
                calendar_notices.append(notice)
                assertions.setdefault(day, set()).add(payload["is_open"] is True)
                expired_notice = expired_notice or expires <= query.as_of
        if invalid_notice:
            gap("calendar_notice_invalid", "Malformed calendar evidence is retained for review")
        if expired_notice:
            gap("calendar_notice_review_expired", "Retained notice requires a new source review")
        if any(len(values) != 1 for values in assertions.values()) or any(
            session.trade_date in assertions
            and session.is_open not in assertions[session.trade_date]
            for session in sessions
        ):
            gap(
                "calendar_notice_conflict",
                "Explicit notice and stored calendar assertions disagree",
            )
        if calendar_notices:
            gap(
                "calendar_notice_not_authoritative",
                "Notice evidence is partial and does not replace reviewed full-calendar provenance",
            )

        if instrument is None:
            gap("instrument_missing", "No instrument snapshot is visible at decision time")
        elif (
            instrument.exchange not in SSE_EXCHANGE_IDENTIFIERS
            or instrument.currency != "CNY"
            or instrument.category is not InstrumentCategory.EQUITY
        ):
            gap(
                "instrument_scope_unverified",
                "Stored exchange/category/currency does not prove pilot scope",
            )
        if missing_dates:
            gap(
                "calendar_incomplete",
                "Missing dates are unknown, not inferred weekends or holidays",
            )
        current = next((item for item in sessions if item.trade_date == query.trade_date), None)
        if current is None or not current.is_open:
            gap("decision_session_not_open", "An explicitly open decision-date session is required")
        gap(
            "calendar_provenance_unavailable",
            "Stored sessions lack exchange-scoped trust, precision and raw hashes",
        )
        if status is None:
            gap("status_missing", "No effective, PIT-visible security status is available")
        else:
            if (status_review is not None
                    and "legacy_delisted_quote_status" in status_review.reasons):
                gap(
                    "legacy_suspension_status_unverified",
                    "Legacy snapshot used a delisted-quote endpoint; retain but do not authorize",
                )
            if status.status is not SecurityStatus.LISTED or not status.is_tradable:
                gap(
                    "status_not_ordinary",
                    "Preserved security status is outside the ordinary listed pilot",
                )
            if status.trust_level not in {DataTrustLevel.HIGH, DataTrustLevel.VERIFIED}:
                gap(
                    "status_trust_insufficient",
                    "Stored security-status trust is preserved without promotion",
                )
            if status.availability_precision not in {
                AvailabilityPrecision.EXACT,
                AvailabilityPrecision.RETRIEVAL_TIME,
            }:
                gap(
                    "status_precision_insufficient", "Stored availability precision is insufficient"
                )
            try:
                require_sha256(status.raw_data_hash)
            except ValueError:
                gap("status_hash_missing", "Security status requires a valid raw SHA-256 reference")
            if not status.source.strip():
                gap("status_source_missing", "Security status has no source identity")
        gap(
            "lifecycle_coverage_unverified",
            "Positive events or their absence do not prove current ST/suspension/listing phase",
        )
        if lifecycle_events or lifecycle_evidence:
            gap(
                "lifecycle_source_review_required",
                "Retained lifecycle observations need artifact, trust and continuity review",
            )
        if any(
            {"legacy_suspension_normalization", "unconfirmed_akshare_resumption"}.intersection(
                review.reasons
            ) for review in lifecycle_reviews
        ):
            gap(
                "legacy_suspension_history_unverified",
                "Legacy starts/resumption may contain unconfirmed forecast dates; no promotion",
            )
        if any(review.disposition is LifecycleRecordDisposition.QUARANTINED
               for review in (*lifecycle_reviews, *((status_review,) if status_review else ()))):
            gap("lifecycle_record_quarantined",
                "Preserved records failed usability review; no normal-status clearance follows")
        if previous_session is None:
            gap(
                "previous_session_missing",
                "No previous explicitly open session exists in this window",
            )
        if previous_close is None:
            gap(
                "previous_close_missing",
                "No visible unadjusted close matches the previous open session",
            )
        else:
            bound = tuple(
                record for record in price_evidence if matches_daily_bar(record, previous_close)
            )
            if not bound:
                gap(
                    "price_provenance_unavailable",
                    "No exact stored-price/source/availability binding exists",
                )
            if any(
                record.trust_level not in {DataTrustLevel.HIGH, DataTrustLevel.VERIFIED}
                for record in bound
            ):
                gap("price_evidence_trust_insufficient", "Bound evidence retains its source trust")
            if bound:
                gap(
                    "price_artifact_review_required",
                    "A content binding is not independent source or current artifact verification",
                )
            if any(
                record.available_at == previous_close.available_at
                and record.observed_at == previous_close.timestamp
                and not matches_daily_bar(record, previous_close)
                for record in price_evidence
            ):
                gap(
                    "price_evidence_conflict", "Visible evidence disagrees with the exact price row"
                )
        gap(
            "listing_phase_unverified",
            "LISTED or an old listing date cannot establish normal phase or exclude relisting",
        )
        if any(action.effective_date == query.trade_date for action in actions):
            gap(
                "decision_date_action_present",
                "Visible corporate actions require separate reference-price review",
            )
        gap(
            "corporate_action_coverage_unverified",
            "An empty action query cannot prove corporate-action-free status",
        )
        gap(
            "account_lots_not_integrated",
            "No account holdings or settlement confirmation are read or synthesized",
        )
        return SSERuntimeInputSnapshot(
            symbol,
            query,
            calendar_start,
            instrument,
            status,
            sessions,
            missing_dates,
            previous_session,
            previous_close,
            actions,
            tuple(gaps),
            calendar_notices=tuple(calendar_notices),
            price_evidence=price_evidence,
            calendar_plan=calendar_plan,
            lifecycle_events=lifecycle_events,
            lifecycle_evidence=lifecycle_evidence,
            lifecycle_reviews=lifecycle_reviews,
            status_review=status_review,
        )
