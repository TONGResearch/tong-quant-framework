"""Evidence-bound calculations for ordinary SSE main-board A-share research."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError
from tong_quant.domain.enums import (
    Adjustment,
    AssetType,
    AvailabilityPrecision,
    DataTrustLevel,
    InstrumentCategory,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import (
    Bar,
    Instrument,
    InstrumentStatus,
    TradingSession,
    require_timezone,
)
from tong_quant.markets.base import PriceLimit
from tong_quant.markets.capabilities import (
    MarketRuleCapability,
    MarketRuleCoverageInspector,
    MarketRuleEvidence,
    MarketRuleEvidenceCatalog,
    MarketRuleQuery,
)
from tong_quant.markets.sse_references import (
    SSE_EXCHANGE_IDENTIFIERS,
    SSE_PILOT_SCOPE,
    SSEReferenceBundle,
    evidence_hash,
    is_sse_main_board_pilot_symbol,
    require_sha256,
)
from tong_quant.version import SSE_CALCULATION_VERSION

SHANGHAI = ZoneInfo("Asia/Shanghai")
TICK = Decimal("0.01")


def _key(instrument: Instrument) -> tuple[str, str, str]:
    return instrument.market.value, instrument.asset_type.value, instrument.symbol


def _require_trusted(trust: DataTrustLevel, precision: AvailabilityPrecision) -> None:
    if (
        not isinstance(trust, DataTrustLevel)
        or not isinstance(precision, AvailabilityPrecision)
        or trust not in {DataTrustLevel.HIGH, DataTrustLevel.VERIFIED}
        or precision
        not in {
            AvailabilityPrecision.EXACT,
            AvailabilityPrecision.RETRIEVAL_TIME,
        }
    ):
        raise MarketRuleEvidenceUnavailableError(
            "input trust or availability precision is insufficient"
        )


def calendar_input_hash(sessions: tuple[TradingSession, ...]) -> str:
    return evidence_hash(
        [asdict(session) for session in sorted(sessions, key=lambda item: item.trade_date)]
    )


@dataclass(frozen=True, slots=True)
class SSECalculationContext:
    query: MarketRuleQuery
    instrument: Instrument
    status: InstrumentStatus
    status_evidence: MarketRuleEvidence
    sessions: tuple[TradingSession, ...]
    calendar_evidence: MarketRuleEvidence
    account_key: str
    listing_phase: str = "unknown"
    corporate_action_free: bool | None = None


def security_input_hash(context: SSECalculationContext) -> str:
    return evidence_hash(
        {
            "instrument": asdict(context.instrument),
            "status": asdict(context.status),
            "listing_phase": context.listing_phase,
            "corporate_action_free": context.corporate_action_free,
        }
    )


@dataclass(frozen=True, slots=True)
class SSEPositionLot:
    lot_id: str
    instrument: Instrument
    account_key: str
    remaining_quantity: int
    purchased_on: date
    settlement_confirmed_at: datetime | None
    available_at: datetime
    unrestricted: bool
    source_reference: str
    content_sha256: str
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "lot available_at")
        require_sha256(self.content_sha256)
        if type(self.remaining_quantity) is not int or self.remaining_quantity < 0:
            raise ValueError("position lot quantity must be a non-negative integer")
        if not all(
            value.strip() for value in (self.lot_id, self.account_key, self.source_reference)
        ):
            raise ValueError("position lots require identity, account, and source")
        if (
            type(self.unrestricted) is not bool
            or self.available_at.astimezone(SHANGHAI).date() < self.purchased_on
        ):
            raise ValueError("position lots require dated restriction and purchase information")
        if self.settlement_confirmed_at is not None:
            require_timezone(self.settlement_confirmed_at, "settlement_confirmed_at")
            if self.settlement_confirmed_at > self.available_at or (
                self.settlement_confirmed_at.astimezone(SHANGHAI).date() < self.purchased_on
            ):
                raise ValueError("settlement confirmation cannot be future information in a lot")


@dataclass(frozen=True, slots=True)
class SSEPriceReference:
    bar: Bar
    content_sha256: str
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN

    def __post_init__(self) -> None:
        require_sha256(self.content_sha256)


@dataclass(frozen=True, slots=True)
class SSERuleCalculation:
    kind: str
    value: int | PriceLimit
    query: MarketRuleQuery
    reference_hash: str
    coverage_hash: str
    input_hash: str
    calculation_hash: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    model_version: str = SSE_CALCULATION_VERSION


@dataclass(frozen=True, slots=True)
class SSEMainBoardEvaluator:
    references: SSEReferenceBundle
    context: SSECalculationContext

    def _check(self) -> tuple[str, tuple[str, ...]]:
        context, query = self.context, self.context.query
        instrument, status = context.instrument, context.status
        if query.scope != SSE_PILOT_SCOPE:
            raise MarketRuleEvidenceUnavailableError(
                "only SSE main-board cash-account scope is supported"
            )
        if query.as_of.astimezone(SHANGHAI).date() != query.trade_date:
            raise MarketRuleEvidenceUnavailableError(
                "decision time must belong to the requested SSE date"
            )
        if (
            not is_sse_main_board_pilot_symbol(instrument.symbol)
            or instrument.exchange not in SSE_EXCHANGE_IDENTIFIERS
            or instrument.market is not Market.CHINA_A
            or instrument.asset_type is not AssetType.EQUITY
            or instrument.category is not InstrumentCategory.EQUITY
            or instrument.currency != "CNY"
        ):
            raise MarketRuleEvidenceUnavailableError(
                "instrument is outside the ordinary SSE A-share pilot"
            )
        if (
            not context.account_key.strip()
            or instrument.available_at is None
            or (instrument.available_at > query.as_of)
        ):
            raise MarketRuleEvidenceUnavailableError(
                "instrument/account evidence is missing or future"
            )
        if context.listing_phase != "normal":
            raise MarketRuleEvidenceUnavailableError(
                "IPO, relisting, exceptional or unknown phase unsupported"
            )
        if _key(status.instrument) != _key(instrument) or (
            status.status is not SecurityStatus.LISTED
            or not status.is_tradable
            or status.instrument.available_at is None
            or status.instrument.available_at > query.as_of
            or not status.source.strip()
            or status.effective_from > query.trade_date
            or (status.effective_to is not None and status.effective_to < query.trade_date)
            or status.available_at > query.as_of
        ):
            raise MarketRuleEvidenceUnavailableError(
                "dated ordinary tradable security status is required"
            )
        _require_trusted(status.trust_level, status.availability_precision)
        if (
            context.status_evidence.capability is not MarketRuleCapability.SECURITY_STATUS
            or context.calendar_evidence.capability is not MarketRuleCapability.TRADING_CALENDAR
            or context.status_evidence.content_sha256 != security_input_hash(context)
            or status.available_at > context.status_evidence.available_at
            or context.calendar_evidence.content_sha256 != calendar_input_hash(context.sessions)
        ):
            raise MarketRuleEvidenceUnavailableError(
                "security/calendar evidence binding is invalid"
            )
        require_sha256(status.raw_data_hash)
        sessions = {session.trade_date: session for session in context.sessions}
        if len(sessions) != len(context.sessions) or any(
            session.market is not Market.CHINA_A
            or not session.source.strip()
            or session.available_at > query.as_of
            or session.available_at > context.calendar_evidence.available_at
            for session in context.sessions
        ):
            raise MarketRuleEvidenceUnavailableError(
                "calendar contains duplicate, mismatched or future sessions"
            )
        if query.trade_date not in sessions or not sessions[query.trade_date].is_open:
            raise MarketRuleEvidenceUnavailableError(
                "an explicit open current trading session is required"
            )
        coverage = MarketRuleCoverageInspector(
            MarketRuleEvidenceCatalog(
                (
                    *self.references.evidence(as_of=query.as_of),
                    context.status_evidence,
                    context.calendar_evidence,
                )
            )
        ).inspect(query)
        if not coverage.complete:
            raise MarketRuleEvidenceUnavailableError(
                "market-rule evidence coverage is incomplete or ambiguous"
            )
        return coverage.evidence_hash, coverage.warnings

    def _result(
        self,
        kind: str,
        value: int | PriceLimit,
        inputs: object,
        reasons: tuple[str, ...],
    ) -> SSERuleCalculation:
        coverage_hash, warnings = self._check()
        input_hash = evidence_hash({"context": asdict(self.context), "inputs": inputs})
        value_record = asdict(value) if isinstance(value, PriceLimit) else value
        calculation_hash = evidence_hash(
            {
                "model_version": SSE_CALCULATION_VERSION,
                "kind": kind,
                "value": value_record,
                "input_hash": input_hash,
                "coverage_hash": coverage_hash,
                "reference_hash": self.references.reference_hash,
            }
        )
        return SSERuleCalculation(
            kind=kind,
            value=value,
            query=self.context.query,
            reference_hash=self.references.reference_hash,
            coverage_hash=coverage_hash,
            input_hash=input_hash,
            calculation_hash=calculation_hash,
            reasons=reasons,
            warnings=(*warnings, "Research calculation only; no fill or trading authorization"),
        )

    @staticmethod
    def _quantity(quantity: int) -> None:
        if type(quantity) is not int or not 0 <= quantity <= 1_000_000:
            raise ValueError("auction quantity must be an integer between zero and 1000000")

    def buy_quantity(self, requested: int) -> SSERuleCalculation:
        self._quantity(requested)
        return self._result(
            "buy_quantity",
            requested // 100 * 100,
            {"requested": requested},
            ("SSE 2026 sections 3.3.8-3.3.9: 100-share buy increments; maximum 1000000",),
        )

    def sellable_quantity(self, lots: tuple[SSEPositionLot, ...]) -> SSERuleCalculation:
        self._check()
        if len({lot.lot_id for lot in lots}) != len(lots):
            raise ValueError("position-lot identities must be unique")
        sessions = {session.trade_date: session for session in self.context.sessions}
        total = 0
        for lot in lots:
            _require_trusted(lot.trust_level, lot.availability_precision)
            if (
                _key(lot.instrument) != _key(self.context.instrument)
                or lot.instrument.available_at is None
                or lot.instrument.available_at > self.context.query.as_of
                or lot.account_key != self.context.account_key
                or lot.available_at > self.context.query.as_of
                or lot.purchased_on > self.context.query.trade_date
                or not lot.unrestricted
            ):
                raise MarketRuleEvidenceUnavailableError(
                    "lot scope, availability or restrictions unsupported"
                )
            if lot.purchased_on not in sessions or not sessions[lot.purchased_on].is_open:
                raise MarketRuleEvidenceUnavailableError("lot purchase session is unproven")
            if (
                lot.purchased_on < self.context.query.trade_date
                and lot.settlement_confirmed_at is not None
            ):
                total += lot.remaining_quantity
        return self._result(
            "sellable_quantity",
            total,
            [
                asdict(lot)
                for lot in sorted(
                    lots,
                    key=lambda item: item.lot_id,
                )
            ],
            ("Same-day buys excluded; older lots need confirmed settlement and no restrictions",),
        )

    def sell_quantity(self, requested: int, lots: tuple[SSEPositionLot, ...]) -> SSERuleCalculation:
        self._quantity(requested)
        sellable = self.sellable_quantity(lots)
        if any(
            lot.remaining_quantity > 0
            and (
                (lot.purchased_on == self.context.query.trade_date and lot.remaining_quantity % 100)
                or (
                    lot.purchased_on < self.context.query.trade_date
                    and lot.settlement_confirmed_at is None
                )
            )
            for lot in lots
        ):
            raise MarketRuleEvidenceUnavailableError(
                "unsettled or exceptional lot balance needs account review"
            )
        assert isinstance(sellable.value, int)
        remainder = sellable.value % 100
        if requested > sellable.value or requested % 100 not in {0, remainder}:
            raise ValueError(
                "sell quantity exceeds available holdings or splits an odd-lot remainder"
            )
        return self._result(
            "sell_quantity",
            requested,
            {
                "requested": requested,
                "sellable_calculation_hash": sellable.calculation_hash,
            },
            ("SSE odd-lot clarification: the entire odd remainder must be sold together",),
        )

    def price_limit(self, reference: SSEPriceReference) -> SSERuleCalculation:
        self._check()
        _require_trusted(reference.trust_level, reference.availability_precision)
        bar, query = reference.bar, self.context.query
        if self.context.corporate_action_free is not True:
            raise MarketRuleEvidenceUnavailableError(
                "corporate-action status must be explicitly clear"
            )
        if (
            _key(bar.instrument) != _key(self.context.instrument)
            or bar.instrument.available_at is None
            or bar.instrument.available_at > query.as_of
            or bar.adjustment is not Adjustment.NONE
            or bar.available_at > query.as_of
            or not bar.source.strip()
        ):
            raise MarketRuleEvidenceUnavailableError(
                "unadjusted visible reference close is required"
            )
        previous_date = bar.timestamp.astimezone(SHANGHAI).date()
        sessions = {session.trade_date: session for session in self.context.sessions}
        if (
            previous_date >= query.trade_date
            or previous_date not in sessions
            or not sessions[previous_date].is_open
        ):
            raise MarketRuleEvidenceUnavailableError("reference close session is unproven")
        day = previous_date + timedelta(days=1)
        while day < query.trade_date:
            if day not in sessions or sessions[day].is_open:
                raise MarketRuleEvidenceUnavailableError(
                    "reference close is stale or calendar has gaps"
                )
            day += timedelta(days=1)
        close = bar.close
        if not close.is_finite() or close < TICK or close != close.quantize(TICK):
            raise ValueError("reference close must be positive and aligned to the A-share tick")
        lower = (close * Decimal("0.90")).quantize(TICK, rounding=ROUND_HALF_UP)
        upper = (close * Decimal("1.10")).quantize(TICK, rounding=ROUND_HALF_UP)
        if close - lower < TICK:
            lower = close - TICK
        if upper - close < TICK:
            upper = close + TICK
        limits = PriceLimit(lower=max(TICK, lower), upper=max(TICK, upper))
        return self._result(
            "price_limit",
            limits,
            asdict(reference),
            (
                "SSE 2026 sections 3.3.11/13/17: 10% band, half-up tick rounding and floors",
                "Daily band only; continuous-auction price cages and execution are not evaluated",
            ),
        )
