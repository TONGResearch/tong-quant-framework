"""Read-only co-display cannot admit accounting, convert currencies or hide failures."""

import json
import runpy
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.global_document_review_inputs import ingest_global_document_review
from tong_quant.data.global_ratio_review_inputs import ingest_global_ratio_review
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers import global_documents as source
from tong_quant.data.providers import yahoo_fundamentals as financial
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.global_document_reviews import (
    GlobalDocumentReview,
    GlobalMonetaryRow,
)
from tong_quant.data.providers.global_ratio_reviews import GlobalRatioReview, GlobalRatioRow
from tong_quant.data.providers.yahoo_snapshot import (
    DATASET,
    TIMEZONES,
    YahooGlobalSnapshotAdapter,
    YahooSnapshotCapture,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.version import EQUITY_HOLDING_DISPLAY_VERSION, GLOBAL_RATIO_DISPLAY_VERSION

NOW = datetime(2026, 10, 28, tzinfo=UTC)
AT = NOW + timedelta(seconds=3)
HK_URL = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf"
MY_URL = ("https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/"
          "maybank-ar2025-financial-statements.pdf")


def _prices(store, artifacts, market, at=NOW, failure=False):
    malaysia = market is Market.MALAYSIA
    subject, currency, exchange = ("1155.KL", "MYR", "KLS") if malaysia else (
        "0700.HK", "HKD", "HKG")
    request = ProviderDatasetRequest(DATASET, market, subject, at, {
        "start_date": "2025-01-01", "end_date": "2026-10-27", "currency": currency,
        "exchange": exchange, "timezone": TIMEZONES[market]})
    start = datetime(2025, 1, 1, 8, tzinfo=UTC)
    prices = [10 + index / 100 for index in range(100)]
    capture = (YahooSnapshotCapture(None, "provider_unavailable") if failure else
        YahooSnapshotCapture({"chart": {"error": None, "result": [{
            "meta": {"symbol": subject, "currency": currency, "exchangeName": exchange,
                "instrumentType": "EQUITY", "exchangeTimezoneName": TIMEZONES[market],
                "dataGranularity": "1d"},
            "timestamp": [int((start + timedelta(days=i)).timestamp()) for i in range(100)],
            "indicators": {"quote": [{"open": prices, "close": prices,
                "high": [p + 1 for p in prices], "low": [p - 1 for p in prices],
                "volume": [10000] * 100}]}}]}}))
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: at), request)


def _source(store, artifacts, market, at=NOW, failure=False, url=None):
    malaysia = market is Market.MALAYSIA
    default_url, subject = (MY_URL, "1155.KL") if malaysia else (HK_URL, "0700.HK")
    url = url or default_url
    request = ProviderDatasetRequest(source.DATASET, market, subject, at, {
        "document_url": url, "landing_url": ("https://www.maybank.com/en/investor-relations/"
            "financial-overview/annual-reports.page") if malaysia else url,
        "issuer_label": "Synthetic issuer", "period_end": "2025-12-31",
        "document_kind": "annual_report"})
    capture = source.DocumentCapture(None if failure else b"%PDF-1.7\nSynthetic",
                                      "http_403" if failure else "")
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: at).ingest(
        source.GlobalDocumentAdapter(market, download=lambda _: capture, clock=lambda: at), request)


def _foundation(tmp_path, market, *, shared=False, missing_review=False):
    prices = SQLiteStore(tmp_path / "prices.sqlite3")
    prices.initialize()
    reviews = prices if shared else SQLiteStore(tmp_path / "reviews.sqlite3")
    if not shared:
        reviews.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "raw")
    _prices(prices, artifacts, market)
    _source(reviews, artifacts, market)
    subject, url = ("1155.KL", MY_URL) if market is Market.MALAYSIA else ("0700.HK", HK_URL)
    if not missing_review:
        receipt = read_global_document_inputs(reviews, artifacts, market, subject, url, as_of=NOW)
        row = GlobalMonetaryRow("native", "Synthetic native amount", "income", "group",
            date(2025, 1, 1), date(2025, 12, 31), "current", "Group 2025",
            "MYR" if market is Market.MALAYSIA else "CNY", "million", "Synthetic million",
            Decimal("123"), "transcribed", "123", 1, "cover", "unknown")
        review = GlobalDocumentReview(market, subject, url, receipt["selected_evidence_id"],
            receipt["captures"][0]["raw_data_hash"], receipt["document_sha256"], NOW,
            NOW + timedelta(seconds=1), "Synthetic single reviewer", date(2025, 12, 31), (row,))
        ingest_global_document_review(reviews, artifacts, review,
                                       clock=lambda: NOW + timedelta(seconds=2))
    return prices, reviews, artifacts, market, subject, url


def _run(foundation, at=AT, extra=()):
    prices, reviews, artifacts, market, subject, url = foundation
    return subprocess.run([sys.executable, "scripts/inspect_global_technical.py", "--database",
        str(prices.path), "--artifact-root", str(artifacts.root), "--market", market.value,
        "--symbol", subject, "--as-of", at.isoformat(), "--review-database", str(reviews.path),
        "--review-document-url", url, *extra], capture_output=True, text=True)


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
def test_reviewed_filing_combined_hash_includes_holding_context(tmp_path, market):
    foundation = _foundation(tmp_path, market)
    path = tmp_path / "holding.toml"
    path.write_text(f'''[holding]
symbol = "{foundation[4]}"
market = "{market.value}"
currency = "{"MYR" if market is Market.MALAYSIA else "HKD"}"
quantity = "0.1"
reported_average_cost = "10"
observed_at = "{(NOW - timedelta(hours=1)).isoformat()}"
recorded_at = "{NOW.isoformat()}"
investment_intent = "long_term"
loss_review_percent = "30"
maximum_context_age_seconds = 604800
maximum_price_age_seconds = 604800
''')
    baseline = _run(foundation).stdout
    before = {item.path: sha256(item.path.read_bytes()).hexdigest() for item in foundation[:2]}
    result = _run(foundation, extra=("--holding-context", str(path)))
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    assert doc["combined_evidence_version"] == EQUITY_HOLDING_DISPLAY_VERSION
    assert doc["holding_review"]["comparison_status"] == "BLOCKED"
    assert not doc["holding_review"]["holding_management_authorized"]
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert _run(foundation).stdout == baseline
    assert all(sha256(path.read_bytes()).hexdigest() == digest for path, digest in before.items())


def _ratio_sources(foundation):
    _, reviews, artifacts, market, subject, primary_url = foundation
    urls = tuple(primary_url.replace(".pdf", f"-{index}.pdf") if market is Market.MALAYSIA
        else primary_url.replace("01231.pdf", f"0123{index + 1}.pdf") for index in range(1, 4))
    for index, url in enumerate((primary_url, urls[0])):
        if index:
            _source(reviews, artifacts, market, url=url)
        source = read_global_document_inputs(reviews, artifacts, market, subject, url, as_of=NOW)
        row = GlobalRatioRow("native_ratio", "Synthetic ratio", "group",
            "unknown" if index else "instant", None, date(2025, 12, 31), "current", "Group 2025",
            "percent", "%", Decimal("138.2" if index else "106.7"), "transcribed",
            "138.2" if index else "106.7", 1, "1", "unknown",
            "Unqualified rolling 12-month average" if index else "unknown", "unknown", "unknown")
        review = GlobalRatioReview(market, subject, url, source["selected_evidence_id"],
            source["captures"][0]["raw_data_hash"], source["document_sha256"], NOW,
            NOW + timedelta(seconds=1), "Synthetic single reviewer", date(2025, 12, 31), (row,))
        ingest_global_ratio_review(reviews, artifacts, review,
                                   clock=lambda: NOW + timedelta(seconds=2))
    return primary_url, *urls


def _ratio_options(urls):
    return ("--fundamentals", "--sector-profile", "bank",
            *(option for url in urls for option in ("--review-ratio-document-url", url)))


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
@pytest.mark.parametrize("shared", [False, True])
def test_ratio_display_keeps_documents_distinct_missing_states_and_legacy_output(
    tmp_path, market, shared,
):
    foundation = _foundation(tmp_path, market, shared=shared)
    baseline = _run(foundation).stdout
    urls = _ratio_sources(foundation)
    assert _run(foundation).stdout == baseline  # Opt-in leaves legacy output/hash unchanged.
    before = {store.path: store.path.read_bytes() for store in foundation[:2]}
    first = _run(foundation, extra=_ratio_options(urls))
    second = _run(foundation, extra=_ratio_options((urls[0], *reversed(urls[1:]))))
    assert first.returncode == second.returncode == 2
    assert not first.stderr and not second.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    evidence = doc["reviewed_ratio_evidence"]
    assert evidence["model_version"] == GLOBAL_RATIO_DISPLAY_VERSION
    assert evidence["document_count"] == 4
    assert evidence["snapshot_scope"] == "single_review_database_snapshot"
    assert evidence["primary"]["document_url"] == urls[0]
    assert evidence["primary"]["observations"][0]["unqualified_reported_percent"] == "106.7"
    supplements = evidence["supplemental"]
    assert [item["document_url"] for item in supplements] == sorted(urls[1:])
    observed = next(item for item in supplements if item["document_url"] == urls[1])
    assert observed["observations"][0]["unqualified_reported_percent"] == "138.2"
    assert observed["observations"][0]["period_basis"] == "unknown"
    assert sum(item["status"] == "missing" for item in supplements) == 2
    assert all(item["as_of"] == AT.isoformat() for item in (evidence["primary"], *supplements))
    assert all(evidence[key] is False for key in ("metric_aggregation_authorized",
        "accounting_definition_qualified", "financial_scoring_authorized",
        "investment_scoring_authorized", "historical_replay_eligible", "validation_authorized",
        "execution_authorized"))
    assert doc["diagnostics"]["macd_dif"] is not None
    assert doc["fundamentals_status"] == "missing" and not doc["research_report_created"]
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(store.path.read_bytes() == before[store.path] for store in foundation[:2])


@pytest.mark.parametrize("failed_document", [0, 1])
def test_failed_ratio_document_stays_failed_without_borrowing_other_document(
    tmp_path, failed_document,
):
    foundation = _foundation(tmp_path, Market.MALAYSIA)
    urls = _ratio_sources(foundation)
    _source(foundation[1], foundation[2], Market.MALAYSIA, at=AT, failure=True,
            url=urls[failed_document])
    result = _run(foundation, extra=_ratio_options(urls[:2]))
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    evidence = doc["reviewed_ratio_evidence"]
    documents = (evidence["primary"], *evidence["supplemental"])
    assert documents[failed_document]["status"] == "rejected_or_ambiguous"
    assert not documents[failed_document]["observations"]
    assert documents[1 - failed_document]["source_bound"]
    assert doc["diagnostics"]["macd_dif"] is not None
    assert not evidence["financial_scoring_authorized"]


def test_future_ratio_recording_is_not_backfilled_at_an_older_display_cutoff(tmp_path):
    foundation = _foundation(tmp_path, Market.HONG_KONG)
    urls = _ratio_sources(foundation)
    doc = json.loads(_run(foundation, at=NOW + timedelta(seconds=1),
        extra=_ratio_options(urls[:2])).stdout)
    evidence = doc["reviewed_ratio_evidence"]
    assert evidence["primary"]["status"] == evidence["supplemental"][0]["status"] == "missing"
    assert doc["diagnostics"]["macd_dif"] is not None


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
@pytest.mark.parametrize("configured", [False, True])
def test_document_freshness_opt_in_preserves_separate_ages_and_unassessed_default(
    tmp_path, market, configured,
):
    foundation = _foundation(tmp_path, market)
    urls = _ratio_sources(foundation)
    options = (*_ratio_options(urls[:3]), "--review-freshness")
    if configured:
        config = tmp_path / "freshness.toml"
        config.write_text(Path("config/default.toml").read_text().replace(
            "maximum_report_age_days = 0", "maximum_report_age_days = 1").replace(
            "maximum_source_age_seconds = 0", "maximum_source_age_seconds = 1"))
        options = (*options, "--config", str(config))
    before = {store.path: store.path.read_bytes() for store in foundation[:2]}
    result = _run(foundation, extra=options)
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    checks = doc["reviewed_source_freshness"]["checks"]
    assert len(checks) == 4  # Monetary + primary ratio + observed/missing supplements.
    assert [item["status"] for item in checks] == [
        *("STALE" if configured else "UNASSESSED" for _ in range(3)), "BLOCKED_INPUT"]
    assert checks[0]["source_capture_age_seconds"] == 3
    assert checks[0]["review_recording_age_seconds"] == 1
    assert all(not item["latest_issuer_filing_verified"] for item in checks)
    assert not doc["financial_scoring_authorized"] and not doc["research_report_created"]
    assert not doc["reviewed_ratio_evidence"]["metric_aggregation_authorized"]
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(store.path.read_bytes() == before[store.path] for store in foundation[:2])


def test_document_freshness_without_reviewed_filing_rejects_before_database_access():
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--database", "does-not-exist.sqlite3", "--artifact-root", "does-not-exist",
        "--market", "hong_kong", "--symbol", "0700.HK", "--as-of", AT.isoformat(),
        "--review-freshness"], capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr


@pytest.mark.parametrize("shared", [False, True])
def test_ratio_documents_share_one_review_snapshot_during_competing_source_write(
    tmp_path, monkeypatch, capsys, shared,
):
    from tong_quant.data import reviewed_ratio_inputs

    foundation = _foundation(tmp_path, Market.MALAYSIA, shared=shared)
    urls = _ratio_sources(foundation)
    prices, reviews, artifacts, market, symbol, url = foundation
    original = reviewed_ratio_inputs.read_reviewed_ratio_research_input
    writes = []

    def competing_write(*args, **kwargs):
        receipt = original(*args, **kwargs)
        if args[4] == urls[0] and not writes:
            # A separate connection commits a visible-at-cutoff failure between document reads.
            _source(SQLiteStore(reviews.path), artifacts, market, at=AT, failure=True, url=urls[1])
            writes.append(True)
        return receipt

    monkeypatch.setattr(reviewed_ratio_inputs, "read_reviewed_ratio_research_input",
                        competing_write)
    monkeypatch.setattr(sys, "argv", ["scripts/inspect_global_technical.py", "--database",
        str(prices.path), "--artifact-root", str(artifacts.root), "--market", market.value,
        "--symbol", symbol, "--as-of", AT.isoformat(), "--review-database", str(reviews.path),
        "--review-document-url", url, *_ratio_options(urls[:2])])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path("scripts/inspect_global_technical.py", run_name="__main__")
    assert stopped.value.code == 2 and writes == [True]
    current = json.loads(capsys.readouterr().out)["reviewed_ratio_evidence"]
    assert current["primary"]["source_bound"] and current["supplemental"][0]["source_bound"]
    next_read = json.loads(_run(foundation, extra=_ratio_options(urls[:2])).stdout)
    assert next_read["reviewed_ratio_evidence"]["supplemental"][0]["status"] == (
        "rejected_or_ambiguous")


@pytest.mark.parametrize("urls,fundamentals", [
    ((HK_URL,), False), ((HK_URL, HK_URL), True),
    (tuple(HK_URL.replace("01231.pdf", f"0123{i}.pdf") for i in range(5)), True),
    (("https://example.invalid/file.pdf",), True), ((MY_URL,), True),
    ((HK_URL + "?token=synthetic",), True),
])
def test_invalid_ratio_selection_rejects_before_database_access(urls, fundamentals):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--database", "does-not-exist.sqlite3", "--artifact-root", "does-not-exist",
        "--market", "hong_kong", "--symbol", "0700.HK", "--as-of", AT.isoformat(),
        "--review-database", "does-not-exist.sqlite3", "--review-document-url", HK_URL,
        *(_ratio_options(urls) if fundamentals else ("--review-ratio-document-url", *urls))],
        capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr
    assert "synthetic" not in result.stderr


@pytest.mark.parametrize("market", [Market.HONG_KONG, Market.MALAYSIA])
@pytest.mark.parametrize("shared", [False, True])
def test_same_cutoff_display_preserves_original_inputs_and_no_authority(tmp_path, market, shared):
    foundation = _foundation(tmp_path, market, shared=shared)
    before = {store.path: store.path.read_bytes() for store in foundation[:2]}
    first, second = _run(foundation), _run(foundation)
    assert first.returncode == 2 and not first.stderr, first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["diagnostics"]["macd_dif"] is not None
    assert len(doc["reviewed_filing"]["observations"]) == 1
    assert doc["reviewed_filing_status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED"
    assert doc["reviewed_filing"]["as_of"] == AT.isoformat()
    assert doc["review_currency_alignment"] == ("SAME_LABEL_UNVERIFIED"
        if market is Market.MALAYSIA else "DIFFERENT_CURRENCIES_NO_FX")
    assert doc["accounting_field_correspondence"] == "NOT_REVIEWED"
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"
    assert doc["combined_snapshot_scope"] == ("single_database_snapshot" if shared else
                                             "separate_database_snapshots_shared_cutoff")
    assert all(doc[name] is False for name in ("combined_inputs_admitted", "valuation_authorized",
        "financial_scoring_authorized", "investment_scoring_authorized", "validation_authorized",
        "execution_authorized", "research_report_created", "readiness_promoted"))
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(store.path.read_bytes() == before[store.path] for store in foundation[:2])


@pytest.mark.parametrize("missing", [True, False])
def test_missing_or_not_yet_available_review_stays_missing_not_backfilled(tmp_path, missing):
    foundation = _foundation(tmp_path, Market.HONG_KONG, missing_review=missing)
    result = _run(foundation, at=NOW + timedelta(seconds=1))
    assert not result.stderr
    doc = json.loads(result.stdout)
    assert doc["reviewed_filing_status"] == "missing"
    assert doc["reviewed_filing"]["observations"] == []
    assert doc["review_currency_alignment"] == "UNKNOWN"
    assert doc["diagnostics"]["macd_dif"] is not None


def test_latest_price_failure_does_not_borrow_old_quote_currency_or_hide_review(tmp_path):
    foundation = _foundation(tmp_path, Market.HONG_KONG)
    _prices(foundation[0], foundation[2], Market.HONG_KONG, at=AT, failure=True)
    doc = json.loads(_run(foundation).stdout)
    assert doc["inputs"]["status"] == "provider_unavailable"
    assert doc["diagnostics"]["macd_dif"] is None
    assert doc["quote_currency"] is None and doc["review_currency_alignment"] == "UNKNOWN"
    assert doc["reviewed_filing_status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED"


def test_changed_or_failed_current_document_blocks_review_without_hiding_prices(tmp_path):
    foundation = _foundation(tmp_path, Market.HONG_KONG)
    _source(foundation[1], foundation[2], Market.HONG_KONG, at=AT, failure=True)
    doc = json.loads(_run(foundation).stdout)
    assert doc["reviewed_filing_status"] == "rejected_or_ambiguous"
    assert doc["reviewed_filing"]["observations"] == []
    assert doc["diagnostics"]["macd_dif"] is not None
    assert not doc["combined_inputs_admitted"]


def test_manual_review_does_not_fill_missing_native_yahoo_financials(tmp_path):
    foundation = _foundation(tmp_path, Market.HONG_KONG)
    doc = json.loads(_run(foundation, extra=("--fundamentals", "--sector-profile", "bank")).stdout)
    assert doc["fundamentals_status"] == "missing"
    assert doc["financial_review"]["status"] == "INPUT_REJECTED"
    assert doc["sector_policy_status"] == "NOT_ADMITTED"
    assert doc["reviewed_filing_status"] == "MANUAL_TRANSCRIPTION_UNQUALIFIED"
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"


def test_explicit_native_candidate_reuses_exact_readers_without_promoting_combined_output(tmp_path):
    foundation = _foundation(tmp_path, Market.HONG_KONG)
    request = ProviderDatasetRequest(financial.DATASET, Market.HONG_KONG, "0700.HK", NOW, {
        "start_date": "2025-01-01", "end_date": "2025-12-31"})
    capture = financial.YahooFundamentalCapture({"timeseries": {"error": None, "result": [{
        "meta": {"symbol": ["0700.HK"], "type": ["annualTotalRevenue"]},
        "annualTotalRevenue": [{"asOfDate": "2025-12-31", "periodType": "12M",
            "currencyCode": "CNY", "reportedValue": {"raw": 123000000}}]}]}})
    ProviderNeutralIngestionService(foundation[0], artifact_store=foundation[2],
        clock=lambda: NOW).ingest(financial.YahooFundamentalSnapshotAdapter(
            download=lambda _: capture, clock=lambda: NOW), request)
    before = {store.path: store.path.read_bytes() for store in foundation[:2]}
    options = ("--fundamentals", "--sector-profile", "nonfinancial", "--review-native-pair",
               "native=annualTotalRevenue")
    first, second = _run(foundation, extra=options), _run(foundation, extra=options)
    assert first.returncode == 2 and not first.stderr
    assert first.stdout == second.stdout
    doc = json.loads(first.stdout)
    pair_review = doc["native_manual_candidates"]
    assert pair_review["status"] == "CANDIDATE_REVIEW_ONLY"
    assert pair_review["pairs"][0]["status"] == "CONTEXT_UNQUALIFIED"
    assert pair_review["pairs"][0]["numeric_agreement"] is None
    assert doc["accounting_field_correspondence"] == "NOT_REVIEWED"
    assert doc["provider_numeric_consistency"] == "NOT_ASSESSED"
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(store.path.read_bytes() == before[store.path] for store in foundation[:2])


def test_candidate_missing_native_capture_cannot_be_filled_by_manual_value(tmp_path):
    doc = json.loads(_run(_foundation(tmp_path, Market.HONG_KONG), extra=(
        "--fundamentals", "--sector-profile", "bank", "--review-native-pair",
        "native=annualNetIncome")).stdout)
    assert doc["native_manual_candidates"]["status"] == "INPUT_REJECTED"
    assert doc["native_manual_candidates"]["pairs"] == []


def test_manual_income_sum_cli_keeps_missing_components_without_native_data(tmp_path):
    foundation = _foundation(tmp_path, Market.MALAYSIA)
    before = {store.path: store.path.read_bytes() for store in foundation[:2]}
    first = _run(foundation, extra=("--review-income-sum", "native=absent+unavailable"))
    second = _run(foundation, extra=("--review-income-sum", "native=absent+unavailable"))
    assert first.returncode == 2 and not first.stderr and first.stdout == second.stdout
    doc = json.loads(first.stdout)
    assert doc["reviewed_income_arithmetic"]["status"] == "TRANSCRIPTION_ARITHMETIC_ONLY"
    check = doc["reviewed_income_arithmetic"]["checks"][0]
    assert check["status"] == "MISSING_ROW" and check["residual_source_units"] is None
    assert not doc["financial_scoring_authorized"]
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()
    assert all(store.path.read_bytes() == before[store.path] for store in foundation[:2])


@pytest.mark.parametrize("options", [
    ["--review-native-pair", "native=annualNetIncome"],
    ["--review-income-change", "a=a"],
    ["--bank-document-plan", "does-not-exist.toml"],
    ["--bank-document-plan", "does-not-exist.toml", "--fundamentals", "--sector-profile", "bank"],
    ["--fundamentals", "--sector-profile", "bank", "--review-native-pair", "native=roe"],
    ["--fundamentals", "--sector-profile", "bank", "--review-native-pair", "not-a-pair"],
])
def test_invalid_candidate_options_fail_before_database_access(options):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--database", "does-not-exist.sqlite3", "--artifact-root", "does-not-exist",
        "--market", "hong_kong", "--symbol", "0700.HK", "--as-of", AT.isoformat(),
        "--review-database", "does-not-exist.sqlite3", "--review-document-url", HK_URL,
        *options], capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr


def test_income_change_cli_keeps_explicit_missing_prior_without_promoting_source(tmp_path):
    foundation = _foundation(tmp_path, Market.MALAYSIA)
    result = _run(foundation, extra=("--review-income-change", "native=missing_prior"))
    assert result.returncode == 2 and not result.stderr
    doc = json.loads(result.stdout)
    changes = doc["reviewed_income_changes"]
    assert changes["comparisons"][0]["status"] == "MISSING_ROW"
    assert changes["comparisons"][0]["change_percent"] is None
    assert not changes["financial_scoring_authorized"]
    digest = doc.pop("combined_evidence_hash")
    assert digest == sha256(financial_input_json(doc).encode()).hexdigest()


@pytest.mark.parametrize("options", [["--review-database", "missing.sqlite3"],
    ["--review-document-url", HK_URL],
    ["--review-database", "missing.sqlite3", "--review-document-url", HK_URL],
    ["--capture", "--review-database", "missing.sqlite3", "--review-document-url", HK_URL]])
def test_invalid_pairing_and_us_or_capture_review_rejected_before_database_access(options):
    result = subprocess.run([sys.executable, "scripts/inspect_global_technical.py",
        "--database", "does-not-exist.sqlite3", "--artifact-root", "does-not-exist",
        "--market", "us", "--symbol", "MSFT", "--as-of", AT.isoformat(), *options],
        capture_output=True, text=True)
    assert result.returncode == 2 and "error:" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr
