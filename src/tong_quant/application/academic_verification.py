"""Public synthetic reproduction, not market-data or investment validation."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from importlib.metadata import version
from math import isclose
from platform import python_version
from typing import Any

from tong_quant.application.academic_showcase import build_academic_snapshot
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.domain.enums import Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.version import FRAMEWORK_VERSION

PROTOCOL = "academic-synthetic-reproduction-v1"
CUTOFF = datetime(2026, 11, 15, 9, tzinfo=UTC)
SCOPES = ((Market.US, "TQDEMO", "USD"), (Market.HONG_KONG, "0000.HK", "HKD"),
          (Market.MALAYSIA, "TQDEMO.KL", "MYR"))


def academic_fixture(market: Market, *, rising: bool) -> GlobalPriceInputs:
    """96 civil-day observations; the symbols do not assert actual listings/sessions."""
    if type(rising) is not bool:
        raise ValueError("fixture rising mode requires an exact boolean")
    scope = next((row for row in SCOPES if row[0] is market), None)
    if scope is None:
        raise ValueError("unsupported academic fixture market")
    _, symbol, currency = scope
    instrument = Instrument(symbol, market, "Synthetic verification fixture",
                            currency=currency, exchange="SYNTHETIC")
    available = CUTOFF - timedelta(hours=1)
    bars = []
    for index in range(96):
        close = Decimal(20 + index if rising else 20)
        bars.append(Bar(instrument, CUTOFF - timedelta(days=96 - index), available,
            close, close + 1, close - 1, close, Decimal(1000),
            source="synthetic-academic-verification"))
    identity = sha256(financial_input_json({"protocol": PROTOCOL, "market": market.value,
                                          "rising": rising}).encode()).hexdigest()
    observation: dict[str, object] = {
        "evidence_id": identity, "raw_data_hash": None, "available_at": available,
        "status": "synthetic_fixture", "trust_level": "LOW"}
    return GlobalPriceInputs(symbol, market, CUTOFF, "observed_unqualified", tuple(bars),
                             (observation,), identity, "WITHIN_LIMIT", 86400, 604800)


def _kdj_reference(*, rising: bool, observations: int) -> dict[str, float]:
    with localcontext() as context:
        context.prec = 50
        updates, q = observations - 8, Decimal(2) / 3
        k = Decimal(90) - 40 * q ** updates if rising else Decimal(50)
        d = (Decimal(90) - 40 * q ** updates * (1 + Decimal(updates) / 3)
             if rising else Decimal(50))
        return {"k": float(k), "d": float(d), "j": float(3 * k - 2 * d)}


def reference_values(*, rising: bool) -> dict[str, float]:
    """Independent Decimal recurrence/closed forms, with no pandas/indicator calls."""
    if type(rising) is not bool:
        raise ValueError("reference rising mode requires an exact boolean")
    with localcontext() as context:
        context.prec = 50
        fast = slow = Decimal(20)
        signal = Decimal(0)
        dif = Decimal(0)
        for index in range(96):
            close = Decimal(20 + index if rising else 20)
            fast += Decimal(2) / 13 * (close - fast)
            slow += Decimal(2) / 27 * (close - slow)
            dif = fast - slow
            signal += Decimal(2) / 10 * (dif - signal)
        return {"sma5": 113.0 if rising else 20.0,
                "sma10": 110.5 if rising else 20.0,
                "sma20": 105.5 if rising else 20.0,
                "dif": float(dif), "dea": float(signal), "histogram": float(dif - signal),
                **_kdj_reference(rising=rising, observations=96)}


def verify_academic_reproduction() -> dict[str, Any]:
    cases = []
    for market, symbol, _ in SCOPES:
        for rising in (False, True):
            source = academic_fixture(market, rising=rising)
            snapshot = build_academic_snapshot(source)
            daily = snapshot["frames"]["daily"]
            expected = reference_values(rising=rising)
            observed = {f"sma{item['period']}": item["values"][-1]
                        for item in daily["averages"]}
            observed.update(daily["macd"])
            observed.update(daily["kdj"])
            checks = {"independent_formula_reference": all(
                type(observed.get(key)) in {int, float}
                and isclose(observed[key], value, rel_tol=0, abs_tol=1e-9)
                for key, value in expected.items()),
                "repeatable_same_environment": snapshot == build_academic_snapshot(source),
                "identity_preserved": snapshot["subject"] == symbol
                    and snapshot["market"] == market.value,
                "yearly_history_not_invented": snapshot["frames"]["yearly"]["macd"] is None,
                "no_trading_authority": snapshot["execution_authorized"] is False}
            prefixes = []
            for size in (10, 11, 12):
                prefix = build_academic_snapshot(replace(source, bars=source.bars[-size:]))
                prefixes.append({"observations": size,
                    "expected": _kdj_reference(rising=rising, observations=size),
                    "observed": prefix["frames"]["daily"]["kdj"]})
            checks["nonconverged_kdj_references"] = all(
                row["observed"] is not None and all(
                    isclose(row["observed"][key], value, rel_tol=0, abs_tol=1e-9)
                    for key, value in row["expected"].items()) for row in prefixes)
            for label, blocked in (
                ("stale", replace(source, freshness="STALE")),
                ("missing", replace(source, status="missing", bars=(), observations=(),
                                    selected_evidence_id=None, freshness="UNASSESSED")),
                ("suspended", replace(source, bars=(*source.bars[:-1],
                                      replace(source.bars[-1], is_suspended=True))))):
                result = build_academic_snapshot(blocked)
                checks[f"{label}_no_old_good_fallback"] = all(
                    not frame["bars"] and frame["macd"] is None and frame["kdj"] is None
                    for frame in result["frames"].values())
            cases.append({"market": market.value, "subject": symbol,
                "fixture": "rising" if rising else "flat", "row_count": len(source.bars),
                "snapshot_hash": snapshot["snapshot_hash"],
                "expected": expected, "observed": observed, "prefix_kdj": prefixes,
                "checks": checks})
    result = {"protocol": PROTOCOL, "sample_kind": "SYNTHETIC_CONTRACT_FIXTURES_ONLY",
        "environment": {"python": python_version(), "pandas": version("pandas"),
                        "framework": FRAMEWORK_VERSION},
        "status": "CHECKS_PASSED" if all(all(row["checks"].values()) for row in cases)
                  else "CHECKS_FAILED",
        "absolute_tolerance": 1e-9, "cases": cases,
        "real_market_data_used": False, "listing_and_session_validation": "NOT_ESTABLISHED",
        "source_qualified": False, "pit_qualified": False,
        "strategy_performance": "NOT_EVALUATED", "execution_authorized": False}
    return {**result, "report_hash": sha256(financial_input_json(result).encode()).hexdigest()}
