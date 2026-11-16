"""Price observations join a cutoff diagnostic, never valuation or trade authority."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_quote import (
    DATASET,
    YahooChinaQuoteEvidenceAdapter,
    YahooQuoteCapture,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType, Market
from tong_quant.domain.models import Bar, Instrument
from tong_quant.research.financial.market_value import MarketValueMatchingPolicy
from tong_quant.research.technical.quote_alignment import inspect_yahoo_price_alignment

NOW = datetime(2026, 10, 25, 8, tzinfo=UTC)
QUOTE = NOW - timedelta(days=2)


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "alignment.sqlite3")
    store.initialize()
    return store, FileSystemArtifactStore(tmp_path / "artifacts")


def _capture(foundation, *, at=NOW, price=10, quote_at=QUOTE, failure=False):
    store, artifacts = foundation
    capture = (YahooQuoteCapture(at.date(), None, "provider_unavailable") if failure else
        YahooQuoteCapture(at.date(), {"chart": {"error": None, "result": [{"meta": {
            "symbol": "002624.SZ", "currency": "CNY", "exchangeName": "SHZ",
            "instrumentType": "EQUITY", "exchangeTimezoneName": "Asia/Shanghai",
            "regularMarketPrice": price, "regularMarketTime": int(quote_at.timestamp()),
        }}]}}))
    service = ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at)
    return service.ingest(
        YahooChinaQuoteEvidenceAdapter(download=lambda _: capture, clock=lambda: at),
        ProviderDatasetRequest(DATASET, Market.CHINA_A, "002624", at))


def _bar(**changes):
    return replace(Bar(Instrument("002624", Market.CHINA_A, "synthetic equity"),
        QUOTE, NOW, Decimal("9"), Decimal("11"), Decimal("8"), Decimal("10"),
        Decimal("100"), source="synthetic_daily"), **changes)


def _read(foundation, bars=(), *, cutoff=NOW, policy=None, symbol="002624", market=Market.CHINA_A):
    return inspect_yahoo_price_alignment(*foundation, symbol, market, bars,
                                          as_of=cutoff, policy=policy)


def test_price_and_daily_close_agreement_never_grants_independent_consistency(foundation):
    _capture(foundation)
    result = _read(foundation, (_bar(),))
    assert result["comparison_status"] == "SAME_DATE_DIFFERENT_PRICE_BASIS"
    assert result["quote_bar_date_match"] and result["quote_bar_price_equal"]
    assert Decimal(result["quote_minus_bar_close"]) == 0
    assert result["cross_provider_consistency"] == result["financial_freshness"] == "NOT_ASSESSED"
    assert result["quote_observation"]["source_bound"]
    for key in ("valuation_authorized", "investment_scoring_authorized", "validation_authorized",
                "historical_replay_eligible", "execution_authorized", "readiness_promoted"):
        assert result[key] is False
    assert result["quote_freshness"] == result["bar_freshness"] == "UNASSESSED"


def test_different_dates_never_become_price_conflict_or_a_fabricated_return(foundation):
    _capture(foundation)
    result = _read(foundation, (_bar(timestamp=QUOTE - timedelta(days=1)),))
    assert result["comparison_status"] == "DIFFERENT_MARKET_DATE"
    assert result["quote_bar_date_match"] is False
    assert result["quote_minus_bar_close"] is result["quote_bar_price_equal"] is None


def test_market_date_uses_shanghai_not_the_utc_calendar_boundary(foundation):
    at = QUOTE.replace(hour=16, minute=30)
    _capture(foundation, quote_at=at)
    bar = _bar(timestamp=at.replace(hour=15))
    assert at.date() == bar.timestamp.date()
    assert _read(foundation, (bar,))["quote_bar_date_match"] is False


def test_explicit_elapsed_age_limits_distinguish_quote_capture_and_bar(foundation):
    _capture(foundation)
    result = _read(foundation, (_bar(),), policy=MarketValueMatchingPolicy(86400, 60, 86400))
    assert result["quote_freshness"] == result["bar_freshness"] == "STALE"
    assert result["capture_freshness"] == "WITHIN_CONFIGURED_LIMIT"
    assert result["quote_age_microseconds"] == 2 * 86400 * 1000000
    boundary = _read(foundation, (_bar(),), policy=MarketValueMatchingPolicy(172800, 60, 172800))
    assert boundary["quote_freshness"] == "WITHIN_CONFIGURED_LIMIT"


def test_missing_price_and_bar_remain_explicit(foundation):
    result = _read(foundation)
    assert result["quote_observation"]["status"] == "missing"
    assert result["comparison_status"] == "QUOTE_UNAVAILABLE"
    assert result["quote_freshness"] == result["capture_freshness"] == "UNAVAILABLE"
    assert result["bar_freshness"] == "UNAVAILABLE"
    _capture(foundation)
    assert _read(foundation)["comparison_status"] == "BAR_UNAVAILABLE"


def test_latest_failure_never_falls_back_to_a_working_price(foundation):
    _capture(foundation)
    later = NOW + timedelta(seconds=1)
    _capture(foundation, at=later, failure=True)
    result = _read(foundation, (_bar(),), cutoff=later)
    assert result["comparison_status"] == "QUOTE_UNAVAILABLE"
    assert result["quote_observation"]["status"] == "unavailable"
    assert result["quote_freshness"] == "UNAVAILABLE"
    assert result["capture_age_microseconds"] == 0
    assert result["quote_minus_bar_close"] is None


def test_latest_tied_capture_never_selects_the_favorable_price(foundation):
    _capture(foundation)
    _capture(foundation, price=11)
    result = _read(foundation, (_bar(),))
    assert result["quote_observation"]["status"] == "rejected_or_ambiguous"
    assert result["comparison_status"] == "QUOTE_UNAVAILABLE"


def test_suspension_does_not_resurrect_an_older_close(foundation):
    _capture(foundation)
    bars = (_bar(timestamp=QUOTE - timedelta(days=1)), _bar(is_suspended=True))
    result = _read(foundation, bars)
    assert result["bar_status"] == "SUSPENDED_LATEST"
    assert result["latest_bar"] is None and result["comparison_status"] == "BAR_UNAVAILABLE"


@pytest.mark.parametrize("change", ["open", "volume", "turnover", "source", "instrument",
                                    "ingested"])
def test_full_bar_identity_changes_even_when_date_close_and_price_match_do_not(foundation, change):
    _capture(foundation)
    bar = _bar()
    edited = {"open": {"open": Decimal("9.5")}, "volume": {"volume": Decimal("101")},
              "turnover": {"turnover": Decimal("1000")}, "source": {"source": "another_source"},
              "instrument": {"instrument": replace(bar.instrument, available_at=QUOTE)},
              "ingested": {"ingested_at": NOW}}[change]
    first = _read(foundation, (bar,))
    second = _read(foundation, (replace(bar, **edited),))
    assert first["quote_bar_price_equal"] == second["quote_bar_price_equal"]
    assert first["diagnostic_hash"] != second["diagnostic_hash"]
    assert first["bar_input_hash"] != second["bar_input_hash"]


@pytest.mark.parametrize("kind", ["symbol", "market", "fund", "currency", "adjusted",
                                  "future_price", "future_availability", "future_metadata"])
def test_bad_scope_adjustment_and_future_bars_fail_closed(foundation, kind):
    bar = _bar()
    changes = {
        "symbol": {"instrument": replace(bar.instrument, symbol="000063")},
        "market": {"instrument": replace(bar.instrument, market=Market.US)},
        "fund": {"instrument": replace(bar.instrument, asset_type=AssetType.ETF)},
        "currency": {"instrument": replace(bar.instrument, currency="USD")},
        "adjusted": {"adjustment": Adjustment.FORWARD},
        "future_price": {"timestamp": NOW + timedelta(seconds=1),
                         "available_at": NOW + timedelta(seconds=1)},
        "future_availability": {"available_at": NOW + timedelta(seconds=1)},
        "future_metadata": {"instrument": replace(bar.instrument,
                                            available_at=NOW + timedelta(seconds=1))},
    }[kind]
    with pytest.raises(ValueError):
        _read(foundation, (replace(bar, **changes),))


@pytest.mark.parametrize("symbol,market", [("920982", Market.CHINA_A), ("AAPL", Market.US)])
def test_unsupported_quotes_do_not_break_other_market_diagnostics(foundation, symbol, market):
    result = _read(foundation, symbol=symbol, market=market)
    assert result["comparison_status"] == "UNSUPPORTED_SCOPE"
    assert result["quote_observation"] is None


def test_utc_equivalence_determinism_row_order_and_no_database_mutation(foundation):
    _capture(foundation)
    bars = (_bar(), _bar(timestamp=QUOTE - timedelta(days=1)))
    before = foundation[0].path.read_bytes()
    first = _read(foundation, bars)
    assert first == _read(foundation, tuple(reversed(bars)),
                           cutoff=NOW.astimezone(ZoneInfo("Asia/Shanghai")))
    assert foundation[0].path.read_bytes() == before
    assert first["diagnostic_hash"] != _read(foundation, bars,
        policy=MarketValueMatchingPolicy(60, 60, 60))["diagnostic_hash"]


def test_combined_cli_uses_retained_price_at_exact_cutoff_without_creating_reports(foundation):
    _capture(foundation)
    store, artifacts = foundation
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "002624", "--sector-profile",
            "nonfinancial", "--metrics", "revenue", "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    run = subprocess.run(args, text=True, capture_output=True, check=False)
    assert run.returncode == 2, run.stderr
    document = json.loads(run.stdout)
    alignment = document["yahoo_price_alignment"]
    assert alignment["as_of"] == document["financial_inputs"]["as_of"] == document["as_of"]
    assert alignment["quote_observation"]["price"] == "10"
    assert document["market_value_inputs"]["inspections"] == []
    assert not document["research_report_created"] and not document["investment_scoring_authorized"]
    earlier = subprocess.run(args[:-1] + [(NOW - timedelta(microseconds=1)).isoformat()],
                             text=True, capture_output=True, check=False)
    assert earlier.returncode == 2, earlier.stderr
    earlier_quote = json.loads(earlier.stdout)["yahoo_price_alignment"]["quote_observation"]
    assert earlier_quote["status"] == "missing"
    assert store.path.read_bytes() == before
    assert store.table_count("research_reports") == store.table_count("signals") == 0


def test_different_same_date_prices_remain_descriptive_not_a_provider_failure(foundation):
    _capture(foundation, price=10.1)
    result = _read(foundation, (_bar(),))
    assert result["quote_bar_price_equal"] is False
    assert result["quote_minus_bar_close"] == "0.1" and result["residual_status"] == "EXACT"
    assert result["cross_provider_consistency"] == "NOT_ASSESSED"


def test_residual_is_exact_but_work_is_bounded_for_extreme_scales(foundation):
    _capture(foundation)
    close = Decimal("0." + "0" * 200 + "1")
    result = _read(foundation, (_bar(open=close, high=close, low=close, close=close),))
    assert result["residual_status"] == "EXACT"
    assert result["quote_minus_bar_close"] == "9." + "9" * 201
    close = Decimal("1e-10000")
    result = _read(foundation, (_bar(open=close, high=close, low=close, close=close),))
    assert result["residual_status"] == "UNSUPPORTED_NUMERIC_RANGE"
    assert result["quote_minus_bar_close"] is None and result["quote_bar_price_equal"] is False


def test_broken_source_bytes_cannot_become_a_usable_comparison(foundation):
    _capture(foundation)
    result = _read(foundation, (_bar(),))
    digest = result["quote_observation"]["inspections"][0]["raw_data_hash"]
    artifacts = foundation[1]
    (artifacts.root / "sha256" / digest[:2] / f"{digest}.bin").write_bytes(b"synthetic tamper")
    result = _read(foundation, (_bar(),))
    assert result["quote_observation"]["status"] == "rejected_or_ambiguous"
    assert result["comparison_status"] == "QUOTE_UNAVAILABLE"
    assert result["quote_minus_bar_close"] is None


def test_future_quote_is_hidden_and_folded_future_bar_is_rejected(foundation):
    _capture(foundation, at=NOW + timedelta(seconds=1))
    assert _read(foundation)["quote_observation"]["status"] == "missing"
    zone = ZoneInfo("America/New_York")
    early = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    late = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)
    with pytest.raises(ValueError, match="future"):
        _read(foundation, (_bar(timestamp=late, available_at=late),), cutoff=early)
