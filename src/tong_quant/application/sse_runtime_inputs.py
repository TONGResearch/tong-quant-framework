"""Read existing PIT inputs without manufacturing market-rule authority."""

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from tong_quant.core.security import reject_sensitive_structure
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
    model_version: str = SSE_RUNTIME_INPUT_VERSION

    @property
    def input_hash(self) -> str:
        return evidence_hash(asdict(self))

    def to_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            **asdict(self),
            "input_hash": self.input_hash,
            "boundary": "Input inventory only; not PIT readiness or calculation/trading approval",
        }
        reject_sensitive_structure(record, path="sse_runtime_inputs")
        return record


class SSERuntimeInputReader:
    def __init__(self, data: MarketDataService) -> None:
        self._data = data

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
        gaps: list[SSERuntimeInputGap] = []

        def gap(code: str, explanation: str) -> None:
            gaps.append(SSERuntimeInputGap(code, explanation))

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
            gap(
                "price_provenance_unavailable",
                "Stored Bar has no independently reviewed trust/precision/raw-hash binding",
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
        )
