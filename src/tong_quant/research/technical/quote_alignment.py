"""Read-only price/bar alignment; calendar agreement is not source qualification."""

from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from hashlib import sha256
from zoneinfo import ZoneInfo

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.yahoo_quote import yahoo_equity_symbol
from tong_quant.data.quote_evidence import inspect_yahoo_quote
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import Bar, require_timezone
from tong_quant.research.bar_inputs import checked_daily_bars
from tong_quant.research.financial.market_value import MarketValueMatchingPolicy
from tong_quant.version import YAHOO_PRICE_ALIGNMENT_VERSION


def inspect_yahoo_price_alignment(
    store: SQLiteStore, artifacts: FileSystemArtifactStore,
    symbol: str, market: Market, bars: tuple[Bar, ...], *, as_of: datetime,
    policy: MarketValueMatchingPolicy | None = None,
) -> dict[str, object]:
    require_timezone(as_of, "price alignment cutoff")
    cutoff = as_of.astimezone(UTC)
    policy = policy or MarketValueMatchingPolicy()
    policy.__post_init__()
    if any((bar.instrument.symbol, bar.instrument.market, bar.instrument.asset_type) != (
        symbol, market, AssetType.EQUITY) for bar in bars):
        raise ValueError("price alignment bar identity mismatch")
    checked = checked_daily_bars(bars, as_of=cutoff)
    if market is Market.CHINA_A and any(bar.instrument.currency != "CNY" for bar in bars):
        raise ValueError("China-A price alignment requires CNY bars")
    # An active old bar must not replace the latest suspended observation.
    latest_raw = max(bars, key=lambda bar: (
        bar.timestamp.astimezone(UTC), bar.available_at.astimezone(UTC)), default=None)
    latest = checked[-1] if checked and latest_raw and not latest_raw.is_suspended else None
    supported = market is Market.CHINA_A
    try:
        yahoo_equity_symbol(symbol)
    except ValueError:
        supported = False
    quote = inspect_yahoo_quote(store, artifacts, symbol, as_of=cutoff) if supported else None
    reasons = [
        "A regular-market snapshot is not a verified daily close or executable quote.",
        "Date/price agreement does not establish cross-provider consistency or truth.",
        "Share counts and market values remain separate missing/unqualified inputs.",
        "Configured ages are elapsed UTC time, not a verified exchange-session policy.",
    ]
    output: dict[str, object] = {
        "symbol": symbol, "market": market.value, "as_of": cutoff,
        "model_version": YAHOO_PRICE_ALIGNMENT_VERSION,
        "quote_observation": quote,
        "comparison_status": "QUOTE_UNAVAILABLE" if supported else "UNSUPPORTED_SCOPE",
        "quote_bar_date_match": None, "quote_bar_price_equal": None,
        "quote_minus_bar_close": None, "residual_status": "NOT_ASSESSED",
        "latest_bar": asdict(latest) if latest else None,
        "bar_status": ("SUSPENDED_LATEST" if latest_raw and latest_raw.is_suspended
                       else "OBSERVED_UNQUALIFIED" if latest else "UNAVAILABLE"),
        "bar_input_hash": sha256(financial_input_json(sorted(
            financial_input_json(asdict(bar)) for bar in bars)).encode()).hexdigest(),
        "matching_policy": asdict(policy), "matching_policy_hash": policy.policy_hash,
        "cross_provider_consistency": "NOT_ASSESSED", "financial_freshness": "NOT_ASSESSED",
        "valuation_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "execution_authorized": False, "readiness_promoted": False, "reasons": reasons,
    }
    times: dict[str, datetime | None] = {
        "quote": None, "capture": None, "bar": latest.timestamp if latest else None,
    }
    if quote is not None and quote["source_bound"]:
        entries = quote["inspections"]
        if not isinstance(entries, list):
            raise ValueError("quote inspection contract changed")
        selected = next(entry for entry in entries if entry["evidence_id"] == quote["evidence_id"])
        times["capture"] = selected["available_at"]
        if quote["status"] == "price_only_unqualified":
            quote_at = datetime.fromisoformat(str(quote["claimed_quote_at"]))
            times["quote"] = quote_at
            if latest is None:
                output["comparison_status"] = "BAR_UNAVAILABLE"
            else:
                zone = ZoneInfo("Asia/Shanghai")
                same_date = quote_at.astimezone(zone).date() == (
                    latest.timestamp.astimezone(zone).date())
                output["quote_bar_date_match"] = same_date
                output["comparison_status"] = ("SAME_DATE_DIFFERENT_PRICE_BASIS" if same_date
                                                else "DIFFERENT_MARKET_DATE")
                if same_date:
                    price = Decimal(str(quote["price"]))
                    precision = max(price.adjusted(), latest.close.adjusted()) - min(
                        int(price.as_tuple().exponent), int(latest.close.as_tuple().exponent)) + 2
                    output["quote_bar_price_equal"] = price == latest.close
                    if precision > 4096:
                        output["residual_status"] = "UNSUPPORTED_NUMERIC_RANGE"
                        reasons.append("Exact price residual exceeds the bounded numeric range.")
                    else:
                        with localcontext() as context:
                            context.prec = max(150, precision)
                            residual = price - latest.close
                        output["quote_minus_bar_close"] = str(residual)
                        output["residual_status"] = "EXACT"
                else:
                    reasons.append("Different market dates: no price conflict or return inferred.")
    for name, limit in (("quote", policy.max_quote_age_seconds),
                        ("capture", policy.max_capture_age_seconds),
                        ("bar", policy.max_bar_age_seconds)):
        observed = times[name]
        delta = cutoff - observed.astimezone(UTC) if observed is not None else None
        age = ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
               if delta is not None else None)
        status = ("UNAVAILABLE" if age is None else "FUTURE" if age < 0 else
                  "UNASSESSED" if limit is None else
                  "WITHIN_CONFIGURED_LIMIT" if age <= limit * 1000000 else "STALE")
        output[f"{name}_age_microseconds"] = age
        output[f"{name}_freshness"] = status
    return {**output, "diagnostic_hash": sha256(financial_input_json(output).encode()).hexdigest()}
