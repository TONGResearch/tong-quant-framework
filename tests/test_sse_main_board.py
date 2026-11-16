from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError
from tong_quant.domain.enums import (
    Adjustment,
    AvailabilityPrecision,
    DataTrustLevel,
    Market,
    SecurityStatus,
)
from tong_quant.domain.models import Bar, Instrument, InstrumentStatus, TradingSession
from tong_quant.markets.capabilities import (
    MarketRuleCapability,
    MarketRuleCoverageInspector,
    MarketRuleEvidence,
    MarketRuleEvidenceCatalog,
    MarketRuleQuery,
)
from tong_quant.markets.sse_main_board import (
    SSECalculationContext,
    SSEMainBoardEvaluator,
    SSEPositionLot,
    SSEPriceReference,
    calendar_input_hash,
    security_input_hash,
)
from tong_quant.markets.sse_references import (
    SSE_PILOT_SCOPE,
    SSE_PROFILE_VERSION,
    ReviewedRuleDocument,
    SSEReferenceBundle,
    is_sse_main_board_pilot_symbol,
)

NOW = datetime(2026, 10, 16, 2, tzinfo=UTC)
VISIBLE = datetime(2026, 10, 15, tzinfo=UTC)


def _instrument() -> Instrument:
    return Instrument(
        "600000",
        Market.CHINA_A,
        "Synthetic test equity",
        exchange="SSE",
        available_at=VISIBLE,
        source="synthetic fixture",
    )


def _references() -> SSEReferenceBundle:
    # Synthetic contracts exercise calculations; these are not real source observations.
    return SSEReferenceBundle(
        profile_version=SSE_PROFILE_VERSION,
        effective_from=date(2026, 7, 6),
        available_at=VISIBLE,
        review_expires_at=NOW + timedelta(days=30),
        documents=tuple(
            ReviewedRuleDocument(role, f"https://www.sse.com.cn/lawandrules/test/{role}", "a" * 64)
            for role in ("rules", "deferred", "odd_lots")
        ),
        capture_hash="a" * 64,
        trust_level=DataTrustLevel.HIGH,
    )


def _evidence(capability: MarketRuleCapability, digest: str) -> MarketRuleEvidence:
    return MarketRuleEvidence(
        evidence_id=f"synthetic-{capability.value}",
        scope=SSE_PILOT_SCOPE,
        capability=capability,
        rule_version="synthetic-input-v1",
        effective_from=date(2026, 7, 6),
        effective_to=None,
        available_at=VISIBLE,
        source_reference="synthetic test input",
        content_sha256=digest,
        trust_level=DataTrustLevel.HIGH,
        availability_precision=AvailabilityPrecision.EXACT,
    )


def _context() -> SSECalculationContext:
    sessions = tuple(
        TradingSession(Market.CHINA_A, day, True, VISIBLE, "synthetic calendar")
        for day in (date(2026, 10, 15), date(2026, 10, 16))
    )
    context = SSECalculationContext(
        query=MarketRuleQuery(SSE_PILOT_SCOPE, NOW.date(), NOW),
        instrument=_instrument(),
        status=InstrumentStatus(
            _instrument(),
            date(2026, 7, 6),
            SecurityStatus.LISTED,
            True,
            VISIBLE,
            "synthetic status",
            raw_data_hash="b" * 64,
            trust_level=DataTrustLevel.HIGH,
            availability_precision=AvailabilityPrecision.EXACT,
        ),
        status_evidence=_evidence(MarketRuleCapability.SECURITY_STATUS, "b" * 64),
        sessions=sessions,
        calendar_evidence=_evidence(
            MarketRuleCapability.TRADING_CALENDAR, calendar_input_hash(sessions)
        ),
        account_key="synthetic-account",
        listing_phase="normal",
        corporate_action_free=True,
    )
    return replace(
        context,
        status_evidence=replace(
            context.status_evidence,
            content_sha256=security_input_hash(context),
        ),
    )


def test_canonical_exchange_identifier_uses_same_rules_without_rewriting_input() -> None:
    context = _context()
    instrument = replace(context.instrument, exchange="XSHG")
    context = replace(
        context, instrument=instrument, status=replace(context.status, instrument=instrument)
    )
    context = replace(
        context,
        status_evidence=replace(
            context.status_evidence, content_sha256=security_input_hash(context)
        ),
    )
    result = SSEMainBoardEvaluator(_references(), context).buy_quantity(250)
    assert result.value == 200
    assert result.model_version == "sse-main-board-calculation-v1.2-symbol-scope"
    assert context.instrument.exchange == "XSHG"


@pytest.mark.parametrize("symbol", ["600000", "601398", "603093", "605098"])
def test_bounded_main_board_codes_do_not_replace_existing_evidence_checks(symbol):
    assert is_sse_main_board_pilot_symbol(symbol)
    context = _context()
    instrument = replace(context.instrument, symbol=symbol)
    context = replace(context, instrument=instrument,
                      status=replace(context.status, instrument=instrument))
    context = replace(context, status_evidence=replace(
        context.status_evidence, content_sha256=security_input_hash(context)))
    assert SSEMainBoardEvaluator(_references(), context).buy_quantity(250).value == 200
    with pytest.raises(MarketRuleEvidenceUnavailableError):
        SSEMainBoardEvaluator(
            _references(), replace(context, listing_phase="unknown")).buy_quantity(100)


@pytest.mark.parametrize("symbol", [
    "688363", "689009", "900901", "920982", "832982", "000063", "002624",
    "510300", "730000", "602000", "606000", "60000", "6000000", "６０００００", "60000A",
])
@pytest.mark.parametrize("calculation", ["buy", "sellable", "sell", "price_limit"])
def test_symbol_contradictions_cannot_receive_main_board_rules_despite_sse_tags(
    symbol, calculation,
):
    assert not is_sse_main_board_pilot_symbol(symbol)
    context = _context()
    # Deliberately retain otherwise consistent, HIGH-labeled synthetic evidence.
    instrument = replace(context.instrument, symbol=symbol)
    context = replace(context, instrument=instrument,
                      status=replace(context.status, instrument=instrument))
    context = replace(context, status_evidence=replace(
        context.status_evidence, content_sha256=security_input_hash(context)))
    evaluator = SSEMainBoardEvaluator(_references(), context)
    reference = _price()
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="outside.*pilot"):
        if calculation == "buy":
            evaluator.buy_quantity(250)
        elif calculation == "sellable":
            evaluator.sellable_quantity(())
        elif calculation == "sell":
            evaluator.sell_quantity(0, ())
        else:
            evaluator.price_limit(replace(
                reference, bar=replace(reference.bar, instrument=instrument)))


def _lot(quantity: int = 299) -> SSEPositionLot:
    return SSEPositionLot(
        "lot-1",
        _instrument(),
        "synthetic-account",
        quantity,
        VISIBLE.date(),
        VISIBLE + timedelta(hours=16),
        VISIBLE + timedelta(hours=16),
        True,
        "synthetic position record",
        "c" * 64,
        DataTrustLevel.HIGH,
        AvailabilityPrecision.EXACT,
    )


def _price(close: str = "10.05") -> SSEPriceReference:
    value = Decimal(close)
    bar = Bar(
        instrument=_instrument(),
        timestamp=VISIBLE + timedelta(hours=7),
        available_at=VISIBLE + timedelta(hours=8),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("100"),
        source="synthetic unadjusted close",
    )
    return SSEPriceReference(bar, "d" * 64, DataTrustLevel.HIGH, AvailabilityPrecision.EXACT)


@pytest.mark.parametrize(
    "requested, expected", [(0, 0), (99, 0), (250, 200), (1_000_000, 1_000_000)]
)
def test_buy_quantity_uses_dated_profile_not_instrument_default(
    requested: int, expected: int
) -> None:
    result = SSEMainBoardEvaluator(_references(), _context()).buy_quantity(requested)
    assert result.value == expected
    assert len(result.calculation_hash) == 64
    assert not hasattr(result, "order")


@pytest.mark.parametrize("requested", [-1, 1_000_001, True])
def test_invalid_or_oversized_buy_quantity_is_rejected(requested: int) -> None:
    with pytest.raises(ValueError, match="auction quantity"):
        SSEMainBoardEvaluator(_references(), _context()).buy_quantity(requested)


@pytest.mark.parametrize("requested", [0, 99, 100, 199, 200, 299])
def test_full_odd_remainder_may_be_sold_alone_or_with_whole_lots(requested: int) -> None:
    assert (
        SSEMainBoardEvaluator(_references(), _context()).sell_quantity(requested, (_lot(),)).value
        == requested
    )


@pytest.mark.parametrize("requested", [1, 198, 298, 300])
def test_sell_cannot_split_odd_remainder_or_exceed_holdings(requested: int) -> None:
    with pytest.raises(ValueError, match="odd-lot remainder"):
        SSEMainBoardEvaluator(_references(), _context()).sell_quantity(requested, (_lot(),))


def test_whole_lot_balance_cannot_create_an_odd_sell() -> None:
    evaluator = SSEMainBoardEvaluator(_references(), _context())
    with pytest.raises(ValueError, match="odd-lot remainder"):
        evaluator.sell_quantity(201, (_lot(500),))
    with pytest.raises(ValueError, match="odd-lot remainder"):
        evaluator.sell_quantity(1, (_lot(99),))
    assert evaluator.sell_quantity(99, (_lot(99),)).value == 99


def test_same_day_purchase_and_unconfirmed_settlement_are_not_sellable() -> None:
    evaluator = SSEMainBoardEvaluator(_references(), _context())
    same_day = replace(
        _lot(100), purchased_on=NOW.date(), available_at=NOW, settlement_confirmed_at=NOW
    )
    unsettled = replace(_lot(100), settlement_confirmed_at=None)
    assert evaluator.sellable_quantity((same_day,)).value == 0
    assert evaluator.sellable_quantity((unsettled,)).value == 0
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="unsettled"):
        evaluator.sell_quantity(100, (unsettled,))


@pytest.mark.parametrize(
    "change",
    [
        {"account_key": "other-account"},
        {"unrestricted": False},
        {"available_at": NOW + timedelta(seconds=1)},
        {"instrument": replace(_instrument(), symbol="600001")},
        {"instrument": replace(_instrument(), available_at=NOW + timedelta(seconds=1))},
        {"trust_level": DataTrustLevel.LOW},
    ],
)
def test_lot_scope_restrictions_availability_and_trust_fail_closed(
    change: dict[str, object],
) -> None:
    lot = replace(_lot(), **change)  # type: ignore[arg-type]
    with pytest.raises(MarketRuleEvidenceUnavailableError):
        SSEMainBoardEvaluator(_references(), _context()).sellable_quantity((lot,))


@pytest.mark.parametrize(
    "close, lower, upper", [("10.05", "9.05", "11.06"), ("0.01", "0.01", "0.02")]
)
def test_price_band_applies_half_up_rounding_tick_minimum_and_floor(
    close: str,
    lower: str,
    upper: str,
) -> None:
    result = SSEMainBoardEvaluator(_references(), _context()).price_limit(_price(close))
    assert not isinstance(result.value, int)
    assert result.value.lower == Decimal(lower)
    assert result.value.upper == Decimal(upper)


@pytest.mark.parametrize("clear", [None, False])
def test_corporate_action_or_unknown_status_rejects_plain_close(clear: bool | None) -> None:
    context = replace(_context(), corporate_action_free=clear)
    context = replace(
        context,
        status_evidence=replace(
            context.status_evidence,
            content_sha256=security_input_hash(context),
        ),
    )
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="corporate-action"):
        SSEMainBoardEvaluator(_references(), context).price_limit(_price())


def test_future_adjusted_or_low_trust_reference_close_is_rejected() -> None:
    reference = _price()
    evaluator = SSEMainBoardEvaluator(_references(), _context())
    for changed in (
        replace(reference, bar=replace(reference.bar, adjustment=Adjustment.FORWARD)),
        replace(reference, bar=replace(reference.bar, available_at=NOW + timedelta(seconds=1))),
        replace(reference, trust_level=DataTrustLevel.LOW),
        replace(
            reference,
            bar=replace(
                reference.bar,
                instrument=replace(
                    reference.bar.instrument,
                    available_at=NOW + timedelta(seconds=1),
                ),
            ),
        ),
    ):
        with pytest.raises(MarketRuleEvidenceUnavailableError):
            evaluator.price_limit(changed)


def test_weekend_calendar_is_explicit_and_a_missing_day_is_not_inferred_closed() -> None:
    context = _context()
    monday = date(2026, 10, 19)
    sessions = tuple(
        TradingSession(Market.CHINA_A, day, day.day in {16, 19}, VISIBLE, "synthetic calendar")
        for day in (date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 18), monday)
    )
    context = replace(
        context,
        query=MarketRuleQuery(SSE_PILOT_SCOPE, monday, NOW + timedelta(days=3)),
        sessions=sessions,
        calendar_evidence=replace(
            context.calendar_evidence,
            content_sha256=calendar_input_hash(sessions),
        ),
    )
    reference = _price()
    reference = replace(
        reference,
        bar=replace(
            reference.bar,
            timestamp=NOW + timedelta(hours=5),
            available_at=NOW + timedelta(hours=6),
        ),
    )
    assert SSEMainBoardEvaluator(_references(), context).price_limit(reference).value is not None
    incomplete = sessions[:2] + sessions[3:]
    context = replace(
        context,
        sessions=incomplete,
        calendar_evidence=replace(
            context.calendar_evidence,
            content_sha256=calendar_input_hash(incomplete),
        ),
    )
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="calendar has gaps"):
        SSEMainBoardEvaluator(_references(), context).price_limit(reference)


@pytest.mark.parametrize("phase", ["unknown", "ipo_first_five", "relisting"])
def test_exceptional_listing_phases_are_not_given_ordinary_rules(phase: str) -> None:
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="phase unsupported"):
        SSEMainBoardEvaluator(_references(), replace(_context(), listing_phase=phase)).buy_quantity(
            100
        )


@pytest.mark.parametrize(
    "status", [SecurityStatus.SUSPENDED, SecurityStatus.SPECIAL_TREATMENT, SecurityStatus.DELISTED]
)
def test_st_suspended_or_delisted_stock_is_outside_pilot(status: SecurityStatus) -> None:
    context = _context()
    context = replace(context, status=replace(context.status, status=status, is_tradable=False))
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="security status"):
        SSEMainBoardEvaluator(_references(), context).buy_quantity(100)


def test_missing_status_hash_calendar_binding_or_wrong_board_is_rejected() -> None:
    context = _context()
    for changed in (
        replace(context, status=replace(context.status, raw_data_hash="c" * 64)),
        replace(context, sessions=context.sessions[:1]),
        replace(
            context, query=replace(context.query, scope=replace(SSE_PILOT_SCOPE, board="star"))
        ),
    ):
        with pytest.raises(MarketRuleEvidenceUnavailableError):
            SSEMainBoardEvaluator(_references(), changed).buy_quantity(100)


def test_reference_capture_future_and_review_expiry_are_rejected() -> None:
    evaluator = SSEMainBoardEvaluator(
        replace(_references(), available_at=NOW + timedelta(seconds=1)), _context()
    )
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="future or review expired"):
        evaluator.buy_quantity(100)
    evaluator = SSEMainBoardEvaluator(replace(_references(), review_expires_at=NOW), _context())
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="future or review expired"):
        evaluator.buy_quantity(100)


def test_calculation_hash_is_deterministic_and_changes_with_input() -> None:
    evaluator = SSEMainBoardEvaluator(_references(), _context())
    assert (
        evaluator.buy_quantity(250).calculation_hash == evaluator.buy_quantity(250).calculation_hash
    )
    assert (
        evaluator.buy_quantity(250).calculation_hash != evaluator.buy_quantity(299).calculation_hash
    )


def test_classification_flags_cannot_reuse_unmodified_security_evidence() -> None:
    context = replace(_context(), corporate_action_free=False)
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="binding is invalid"):
        SSEMainBoardEvaluator(_references(), context).buy_quantity(100)


def test_profile_does_not_apply_before_official_effective_date() -> None:
    as_of = datetime(2026, 7, 5, 2, tzinfo=UTC)
    references = replace(_references(), available_at=as_of - timedelta(days=1))
    coverage = MarketRuleCoverageInspector(
        MarketRuleEvidenceCatalog(
            references.evidence(as_of=as_of),
        )
    ).inspect(MarketRuleQuery(SSE_PILOT_SCOPE, date(2026, 7, 5), as_of))
    assert coverage.selected_evidence == ()
    assert not coverage.complete


def test_sse_date_uses_shanghai_time_instead_of_utc_calendar_date() -> None:
    context = _context()
    context = replace(
        context,
        query=replace(
            context.query,
            as_of=datetime(2026, 10, 15, 16, 30, tzinfo=UTC),
        ),
    )
    assert SSEMainBoardEvaluator(_references(), context).buy_quantity(100).value == 100


def test_explicit_closed_weekday_and_confirmed_settlement_bound_sellability() -> None:
    context = _context()
    # A synthetic closed Monday is deliberate; this is not a real exchange holiday assertion.
    sessions = tuple(
        TradingSession(
            Market.CHINA_A,
            date(2026, 10, day),
            day in {16, 20},
            VISIBLE,
            "synthetic holiday fixture",
        )
        for day in range(16, 21)
    )
    tuesday = NOW + timedelta(days=4)
    context = replace(
        context,
        query=MarketRuleQuery(SSE_PILOT_SCOPE, tuesday.date(), tuesday),
        sessions=sessions,
        calendar_evidence=replace(
            context.calendar_evidence,
            content_sha256=calendar_input_hash(sessions),
        ),
    )
    lot = replace(
        _lot(),
        purchased_on=date(2026, 10, 16),
        settlement_confirmed_at=tuesday - timedelta(hours=1),
        available_at=tuesday,
    )
    assert SSEMainBoardEvaluator(_references(), context).sellable_quantity((lot,)).value == 299
    closed_day = replace(
        context,
        query=MarketRuleQuery(
            SSE_PILOT_SCOPE,
            date(2026, 10, 19),
            tuesday - timedelta(days=1),
        ),
    )
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="open current"):
        SSEMainBoardEvaluator(_references(), closed_day).buy_quantity(100)
