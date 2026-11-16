"""Read retained overseas prices into exploratory technical diagnostics; capture is explicit."""

import argparse
import json
import tomllib
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from tong_quant.application.calendar_review import read_nasdaq_price_review
from tong_quant.application.equity_note import render_equity_note
from tong_quant.application.holding_review import build_holding_review, parse_holding_context
from tong_quant.config.settings import load_settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_review_inputs import read_global_document_review_inputs
from tong_quant.data.global_fundamental_inputs import read_global_fundamental_inputs
from tong_quant.data.global_price_inputs import read_global_price_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.global_documents import validate_document_url
from tong_quant.data.providers.sec_body import body_subject
from tong_quant.data.providers.yahoo_snapshot import (
    DATASET,
    TIMEZONES,
    YahooGlobalSnapshotAdapter,
    download_snapshot,
)
from tong_quant.data.reviewed_document_inputs import ReviewedDocumentResearchInput
from tong_quant.data.reviewed_ratio_inputs import (
    ReviewedRatioResearchInput,
    read_reviewed_ratio_research_input,
)
from tong_quant.data.sec_body_inputs import read_sec_body_inputs
from tong_quant.data.sec_filing_inputs import read_sec_issuer_claims
from tong_quant.data.sec_period_inputs import (
    SECPeriodSelection,
    parse_sec_period_selections,
    read_sec_period_inputs,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import TradingSession, require_timezone
from tong_quant.research.config import research_engine_from_settings
from tong_quant.research.financial.document_bank import (
    bank_document_input_coverage,
    parse_bank_document_plan,
)
from tong_quant.research.financial.document_freshness import (
    DocumentFreshnessPolicy,
    review_document_freshness,
)
from tong_quant.research.financial.native_pairs import (
    parse_income_changes,
    parse_income_sums,
    parse_native_pairs,
    review_income_changes,
    review_income_sums,
    review_native_pairs,
)
from tong_quant.research.financial.native_review import review_native_financials
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.technical.calendar_coverage import calendar_coverage_diagnostics
from tong_quant.research.technical.calendar_periods import calendar_period_diagnostics
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.long_horizon import long_horizon_diagnostics
from tong_quant.research.trend import TrendResearchModule
from tong_quant.version import (
    EQUITY_HOLDING_DISPLAY_VERSION,
    GLOBAL_RATIO_DISPLAY_VERSION,
    GLOBAL_REVIEW_DISPLAY_VERSION,
    US_SEC_DISPLAY_VERSION,
    US_SEC_IDENTITY_DISPLAY_VERSION,
    US_SEC_PERIOD_DISPLAY_VERSION,
    US_SEC_SOURCE_ROOT_VERSION,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--market", choices=[market.value for market in TIMEZONES], required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--holding-context", type=Path,
                        help="read-only local owner annotation, not verified broker positions")
    parser.add_argument("--trend-observations", action="store_true",
                        help="read-only price/volume geometry; never full Turtle confirmation")
    parser.add_argument("--long-horizon", action="store_true",
                        help="read-only ended month/year observations; not verified candles")
    parser.add_argument("--multi-timeframe", action="store_true",
                        help="read-only week/month/year indicators with source date alignment")
    parser.add_argument("--as-of")
    parser.add_argument("--max-observation-age-seconds", type=int)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--calendar-periods", action="store_true",
                        help="read-only calendar week/month observations, not scored session bars")
    parser.add_argument("--calendar-coverage", action="store_true",
                        help="compare same-database calendar declarations with calendar-periods")
    parser.add_argument("--nasdaq-calendar-database", type=Path)
    parser.add_argument("--nasdaq-calendar-artifact-root", type=Path)
    parser.add_argument("--nasdaq-calendar-year", type=int)
    parser.add_argument("--nasdaq-max-source-age-seconds", type=int)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--currency")
    parser.add_argument("--exchange")
    parser.add_argument("--fundamentals", action="store_true")
    parser.add_argument("--sec-database", type=Path,
                        help="read retained SEC evidence only; requires explicit CIK/accession")
    parser.add_argument("--sec-artifact-root", type=Path,
                        help="explicit SEC raw root; no copying or fallback")
    parser.add_argument("--sec-cik")
    parser.add_argument("--sec-accession")
    parser.add_argument("--sec-identity", action="store_true",
                        help="compare retained SEC ticker declarations; not identity approval")
    parser.add_argument("--sec-period", action="append", default=[],
                        help="exact native TAG=START/END or TAG=@END; no fiscal/score approval")
    parser.add_argument("--review-database", type=Path)
    parser.add_argument("--review-document-url")
    parser.add_argument("--review-freshness", action="store_true",
                        help="display separate report/source/review ages under configured limits")
    parser.add_argument("--review-ratio-document-url", action="append", default=[],
                        help="explicit primary ratio URL first, then up to three supplemental URLs")
    parser.add_argument("--review-native-pair", action="append", default=[],
                        help="explicit row_key=native_metric candidate, not an admitted mapping")
    parser.add_argument("--review-income-sum", action="append", default=[],
                        help="explicit result=component+component sum of signed manual income rows")
    parser.add_argument("--bank-document-plan", type=Path)
    parser.add_argument("--review-income-change", action="append", default=[])
    parser.add_argument("--sector-profile", choices=(
        "nonfinancial", "bank", "securities", "insurance", "unknown"))
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().parents[1] / "config/default.toml")
    args = parser.parse_args()
    nasdaq_options = (args.nasdaq_calendar_database, args.nasdaq_calendar_artifact_root,
                      args.nasdaq_calendar_year, args.nasdaq_max_source_age_seconds)
    nasdaq_requested = any(value is not None for value in nasdaq_options)
    if nasdaq_requested:
        if not all(value is not None for value in nasdaq_options):
            parser.error("Nasdaq review requires database, artifact root, year and source age")
        if args.market != Market.US.value or args.capture or args.as_of is None:
            parser.error("Nasdaq review is US read-only and requires explicit --as-of")
        if (not 2000 <= args.nasdaq_calendar_year <= 2100
                or args.nasdaq_max_source_age_seconds <= 0):
            parser.error("Nasdaq review requires year 2000..2100 and positive source age")
        if (args.nasdaq_calendar_database.resolve() == args.database.resolve()
                and args.nasdaq_calendar_artifact_root.resolve() != args.artifact_root.resolve()):
            parser.error("one database requires one explicit artifact root")
    if args.multi_timeframe and args.capture:
        parser.error("multi-timeframe observations are read-only; capture separately")
    if args.long_horizon and args.capture:
        parser.error("long-horizon observations are read-only; capture separately")
    holding_context = None
    if args.holding_context is not None:
        if args.capture:
            parser.error("holding review is read-only; capture separately")
        try:
            if args.holding_context.is_symlink() or args.holding_context.stat().st_size > 16384:
                parser.error("unsupported holding context file")
            holding_context = parse_holding_context(tomllib.loads(
                args.holding_context.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, KeyError):
            parser.error("invalid local holding context; no private input values are displayed")
        if holding_context.symbol != args.symbol or holding_context.market.value != args.market:
            parser.error("holding context must match the requested equity and market")
    if args.format == "markdown" and args.capture:
        parser.error("markdown display is read-only; capture explicitly before rendering")
    if args.trend_observations and args.capture:
        parser.error("trend observations are read-only; capture separately")
    if args.calendar_coverage and not (
        args.calendar_periods or args.long_horizon or args.multi_timeframe
    ):
        parser.error("calendar coverage requires --calendar-periods in read-only mode")
    if args.calendar_periods and args.capture:
        parser.error("calendar period display is read-only; capture is not supported")
    sec_options = (args.sec_database, args.sec_cik, args.sec_accession)
    sec_requested = any(value is not None for value in sec_options)
    if args.sec_artifact_root is not None and not sec_requested:
        parser.error("SEC artifact root requires explicit SEC evidence options")
    if args.sec_identity and not sec_requested:
        parser.error("SEC identity review requires explicit SEC evidence options")
    period_selections: tuple[SECPeriodSelection, ...] = ()
    if args.sec_period:
        if not sec_requested or not args.fundamentals or args.sector_profile is None:
            parser.error("SEC periods require explicit SEC evidence, fundamentals and sector")
        try:
            period_selections = parse_sec_period_selections(args.sec_period)
        except (ValueError, TypeError):
            parser.error("invalid SEC periods; require bounded unique TAG=START/END or TAG=@END")
    if sec_requested:
        if not all(value is not None for value in sec_options):
            parser.error("SEC display requires sec-database, sec-cik and sec-accession together")
        if args.market != Market.US.value or args.capture:
            parser.error("SEC display is US read-only; capture is not supported")
        if (args.sec_artifact_root is not None
                and args.sec_database.resolve() == args.database.resolve()
                and args.sec_artifact_root.resolve() != args.artifact_root.resolve()):
            parser.error("one database requires one explicit artifact root")
        try:
            body_subject(args.sec_cik, args.sec_accession)
        except ValueError:
            parser.error("SEC display requires an explicit valid CIK and accession")
    if (args.review_database is None) != (args.review_document_url is None):
        parser.error("review evidence requires both review-database and review-document-url")
    if args.review_freshness and args.review_database is None:
        parser.error("review freshness requires an explicit reviewed filing")
    if args.review_database is not None and (args.capture or args.market == Market.US.value):
        parser.error("review evidence is HK/MY read-only; capture and US review are not supported")
    if args.fundamentals != (args.sector_profile is not None):
        parser.error("fundamentals requires an explicit sector profile; it does not admit a policy")
    ratio_urls = args.review_ratio_document_url
    if ratio_urls:
        if args.review_database is None or not args.fundamentals:
            parser.error("ratio display requires reviewed filing, fundamentals and explicit sector")
        if len(ratio_urls) > 4 or len(set(ratio_urls)) != len(ratio_urls):
            parser.error("ratio display requires at most four unique document URLs")
        try:
            for url in ratio_urls:
                validate_document_url(Market(args.market), url)
        except ValueError as error:
            parser.error(str(error))
        ratio_urls = [ratio_urls[0], *sorted(ratio_urls[1:])]
    bank_plan = None
    if args.bank_document_plan is not None:
        if args.review_database is None or args.sector_profile != "bank":
            parser.error("bank document plan requires reviewed filing and explicit bank context")
        try:
            if (args.bank_document_plan.is_symlink()
                    or args.bank_document_plan.stat().st_size > 128 * 1024):
                parser.error("unsupported bank document plan file")
            bank_plan = parse_bank_document_plan(tomllib.loads(args.bank_document_plan.read_text()))
        except OSError as error:
            parser.error(f"cannot read bank document plan: {type(error).__name__}")
        except (ValueError, TypeError, KeyError) as error:
            parser.error(str(error))
    if args.review_native_pair:
        if not args.fundamentals or args.review_database is None:
            parser.error("native candidates require fundamentals and explicit reviewed filing")
        try:
            parse_native_pairs(args.review_native_pair)
        except ValueError as error:
            parser.error(str(error))
    if args.review_income_sum:
        if args.review_database is None:
            parser.error("income sums require explicit reviewed filing")
        try:
            parse_income_sums(args.review_income_sum)
        except ValueError as error:
            parser.error(str(error))
    if args.review_income_change:
        if args.review_database is None:
            parser.error("income changes require an explicit reviewed filing")
        try:
            parse_income_changes(args.review_income_change)
        except ValueError as error:
            parser.error(str(error))
    if args.max_observation_age_seconds is not None and args.max_observation_age_seconds <= 0:
        parser.error("maximum observation age must be positive")
    if args.capture and (args.as_of is not None or not all(
        (args.start, args.end, args.currency, args.exchange)
    )):
        parser.error("capture requires explicit dates/currency/exchange and no historical as-of")
    if not args.capture and (args.as_of is None or any(
        (args.start, args.end, args.currency, args.exchange)
    )):
        parser.error("read-only mode requires as-of; capture arguments are not allowed")
    settings = load_settings(args.config)
    market = Market(args.market)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    store = SQLiteStore(args.database, read_only=not args.capture)
    if args.capture:
        request = ProviderDatasetRequest(DATASET, market, args.symbol, datetime.now(UTC), {
            "start_date": args.start, "end_date": args.end, "currency": args.currency,
            "exchange": args.exchange, "timezone": TIMEZONES[market]})
        capture = download_snapshot(request)
        captured = datetime.now(UTC)
        # Pin actual capture first; never weaken ingestion PIT checks to hide elapsed time.
        request = ProviderDatasetRequest(DATASET, market, args.symbol, captured, request.parameters)
        store.initialize()
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            YahooGlobalSnapshotAdapter(download=lambda _: capture, clock=lambda: captured), request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
    engine = research_engine_from_settings(settings.research)
    module = next(item for item in engine.modules if isinstance(item, TechnicalResearchModule))
    reviewed = None
    sec_review = None
    sec_identity = None
    sec_periods = None
    calendar_display = None
    calendar_coverage = None
    calendar_source_review = None
    ratio_receipts = []
    shared_database = args.review_database is not None and (
        args.review_database.resolve() == args.database.resolve())
    with store.read_snapshot():
        snapshot = read_global_price_inputs(store, artifacts, args.symbol, market, as_of=as_of,
                                           maximum_age_seconds=args.max_observation_age_seconds)
        if args.calendar_periods:
            calendar_display = calendar_period_diagnostics(
                snapshot.bars, market=market, as_of=as_of)
        if args.calendar_coverage:
            yearly_coverage = args.long_horizon or args.multi_timeframe
            coverage_periods = calendar_period_diagnostics(
                snapshot.bars, market=market, as_of=as_of, include_yearly=True
            ) if yearly_coverage else calendar_display
            assert coverage_periods is not None
            frames = coverage_periods["weekly"] + coverage_periods["monthly"] + (
                coverage_periods["yearly"] if yearly_coverage else [])
            sessions: tuple[TradingSession, ...] = ()
            if frames:
                sessions = tuple(MarketDataService(store).trading_sessions(market,
                    min(date.fromisoformat(frame["period_start_date"]) for frame in frames),
                    as_of.astimezone(ZoneInfo(TIMEZONES[market])).date(), as_of=as_of))
            calendar_coverage = calendar_coverage_diagnostics(
                snapshot.bars, sessions, market=market, as_of=as_of,
                include_yearly=yearly_coverage)
        if nasdaq_requested:
            same_calendar_database = (
                args.nasdaq_calendar_database.resolve() == args.database.resolve())
            calendar_store = store if same_calendar_database else SQLiteStore(
                args.nasdaq_calendar_database, read_only=True)
            calendar_source_review = read_nasdaq_price_review(snapshot, calendar_store,
                FileSystemArtifactStore(args.nasdaq_calendar_artifact_root),
                args.nasdaq_calendar_year,
                maximum_source_age_seconds=args.nasdaq_max_source_age_seconds,
                shared_database=same_calendar_database)
        fundamentals = (read_global_fundamental_inputs(
            store, artifacts, args.symbol, market, as_of=as_of) if args.fundamentals else None)
        if sec_requested:
            sec_shared_database = args.sec_database.resolve() == args.database.resolve()
            sec_artifacts = (artifacts if args.sec_artifact_root is None else
                             FileSystemArtifactStore(args.sec_artifact_root))
            sec_store = store if sec_shared_database else SQLiteStore(
                args.sec_database, read_only=True)
            with sec_store.read_snapshot():
                sec_review = read_sec_body_inputs(sec_store, sec_artifacts, args.sec_cik,
                    args.sec_accession, as_of=as_of)
                if args.sec_identity:
                    sec_identity = read_sec_issuer_claims(sec_store, sec_artifacts, args.sec_cik,
                        symbol=args.symbol, as_of=as_of)
                if period_selections:
                    sec_periods = read_sec_period_inputs(sec_store, sec_artifacts, args.sec_cik,
                        args.sec_accession, as_of=as_of, selections=period_selections,
                        sector_profile=args.sector_profile)
        if args.review_database is not None:
            review_store = store if shared_database else SQLiteStore(
                args.review_database, read_only=True)
            with review_store.read_snapshot():
                reviewed = read_global_document_review_inputs(review_store, artifacts, market,
                    args.symbol, args.review_document_url, as_of=as_of)
                ratio_receipts = [read_reviewed_ratio_research_input(
                    review_store, artifacts, args.symbol, market, url,
                    as_of=as_of, sector_profile=args.sector_profile).document()
                    for url in ratio_urls]
    document = {"inputs": snapshot.document(), "research_only": True,
        "diagnostics": technical_diagnostics(snapshot.bars, module.parameters, as_of=as_of),
        "fundamentals_status": "NOT_ASSESSED", "trend_four_confirmations": "NOT_ASSESSED",
        "research_report_created": False, "readiness_promoted": False}
    if args.trend_observations:
        trend = next(item for item in engine.modules if isinstance(item, TrendResearchModule))
        document["trend_price_observations"] = trend.price_observations(
            snapshot.bars, as_of=as_of)
    if args.long_horizon or args.multi_timeframe:
        document["long_horizon"] = long_horizon_diagnostics(
            snapshot.bars, market=market, as_of=as_of,
            weekly_sma_periods=(13, 26, 52) if args.multi_timeframe else None)
    if calendar_display is not None:
        document["calendar_periods"] = calendar_display
    if calendar_coverage is not None:
        document["calendar_coverage"] = calendar_coverage
    if calendar_source_review is not None:
        document["nasdaq_calendar_review"] = calendar_source_review
    if fundamentals is not None:
        quote_currency = snapshot.bars[-1].instrument.currency if snapshot.bars else None
        currencies = fundamentals["reporting_currencies"]
        document.update(fundamentals=fundamentals, fundamentals_status=fundamentals["status"],
            requested_sector_profile=args.sector_profile, sector_policy_status="NOT_ADMITTED",
            financial_review=review_native_financials(fundamentals, subject=args.symbol,
                market=market, as_of=as_of, sector_profile=args.sector_profile),
            quote_currency=quote_currency, currency_alignment=("UNKNOWN" if not quote_currency
                or not currencies else "SAME_LABEL_UNVERIFIED" if currencies == [quote_currency]
                else "DIFFERENT_CURRENCIES_NO_FX"), valuation_authorized=False)
    if holding_context is not None:
        try:
            document["holding_review"] = build_holding_review(
                holding_context, snapshot, module.parameters)
        except (ValueError, TypeError, KeyError, ArithmeticError):
            parser.error("holding review rejected incompatible identity, timing or price inputs")
    if sec_review is not None:
        document.update(
            sec_filing=sec_review, sec_filing_status=sec_review["status"],
            requested_sec_cik=args.sec_cik, requested_sec_accession=args.sec_accession,
            issuer_to_instrument_verified=False,
            issuer_pairing_status="CALLER_SELECTED_UNVERIFIED",
            accounting_field_correspondence="NOT_REVIEWED",
            provider_numeric_consistency="NOT_ASSESSED",
            sec_freshness_status="UNASSESSED",
            combined_snapshot_scope=("single_database_snapshot" if sec_shared_database
                else "separate_database_snapshots_shared_cutoff"),
            combined_evidence_version=US_SEC_DISPLAY_VERSION,
            combined_inputs_admitted=False, valuation_authorized=False,
            financial_scoring_authorized=False, investment_scoring_authorized=False,
            historical_replay_eligible=False, validation_authorized=False,
            execution_authorized=False,
            combined_limitations=(
                "Explicit CIK/accession selection does not verify the ticker/share-class pairing",
                "SEC same-accession numeric agreement is same-origin, not provider calibration",
                "Yahoo native fields are not mapped to SEC facts or compared numerically",
                "Filing/report labels and capture cutoffs are not original publication history",
                "Selected filing is not proven latest; source/report freshness is unassessed",
                "Separate databases share a cutoff, not an atomic cross-database snapshot",
                "Missing/failed/conflicting evidence remains visible; no score or decision grant",
            ))
        if sec_identity is not None:
            document.update(sec_issuer_claims=sec_identity,
                            combined_evidence_version=US_SEC_IDENTITY_DISPLAY_VERSION)
        if sec_periods is not None:
            document.update(sec_period_inputs=sec_periods,
                            combined_evidence_version=US_SEC_PERIOD_DISPLAY_VERSION)
        if args.sec_artifact_root is not None:
            document["sec_source_selection"] = {
                "model_version": US_SEC_SOURCE_ROOT_VERSION,
                "artifact_root_selection": "EXPLICIT_SEC_ROOT",
                "shared_artifact_root": (
                    args.sec_artifact_root.resolve() == args.artifact_root.resolve()),
                "source_root_binding_verified": False,
                "cross_store_atomicity_verified": False,
                "automatic_fallback_allowed": False,
                "source_admission_authorized": False,
            }
        if holding_context is not None:
            document["combined_evidence_version"] = EQUITY_HOLDING_DISPLAY_VERSION
        document["combined_evidence_hash"] = sha256(
            financial_input_json(document).encode()).hexdigest()
    if reviewed is not None:
        quote_currency = snapshot.bars[-1].instrument.currency if snapshot.bars else None
        currencies = sorted({row["currency"] for row in reviewed["observations"]})
        document.update(reviewed_filing=reviewed, reviewed_filing_status=reviewed["status"],
            review_reporting_currencies=currencies, quote_currency=quote_currency,
            review_currency_alignment=("UNKNOWN" if not quote_currency or not currencies
                else "SAME_LABEL_UNVERIFIED" if currencies == [quote_currency]
                else "DIFFERENT_CURRENCIES_NO_FX"),
            accounting_field_correspondence="NOT_REVIEWED",
            provider_numeric_consistency="NOT_ASSESSED",
            combined_snapshot_scope=("single_database_snapshot" if shared_database
                else "separate_database_snapshots_shared_cutoff"),
            combined_evidence_version=GLOBAL_REVIEW_DISPLAY_VERSION,
            combined_inputs_admitted=False, valuation_authorized=False,
            financial_scoring_authorized=False, investment_scoring_authorized=False,
            validation_authorized=False, execution_authorized=False,
            combined_limitations=(
                "Co-display does not establish issuer, accounting, period or field correspondence",
                "Currency label agreement does not authorize valuation, FX or numeric comparison",
                "Separate databases share a cutoff, not an atomic cross-database snapshot",
                "Keep independent missing/failed/stale states; no score or decision promotion",
            ))
        if args.review_native_pair and fundamentals is not None:
            document["native_manual_candidates"] = review_native_pairs(fundamentals, reviewed,
                candidates=args.review_native_pair, subject=args.symbol, market=market, as_of=as_of)
        if args.review_income_sum:
            document["reviewed_income_arithmetic"] = review_income_sums(reviewed,
                identities=args.review_income_sum, subject=args.symbol, market=market, as_of=as_of)
        if bank_plan is not None:
            bound = ReviewedDocumentResearchInput(financial_input_json(reviewed), "bank")
            try:
                document["bank_document_inputs"] = bank_document_input_coverage(bound, bank_plan)
            except ValueError as error:
                parser.error(str(error))
        if args.review_income_change:
            bound = ReviewedDocumentResearchInput(financial_input_json(reviewed),
                                                   args.sector_profile or "unknown")
            document["reviewed_income_changes"] = review_income_changes(
                bound, pairs=args.review_income_change)
        if ratio_receipts:
            document["reviewed_ratio_evidence"] = {
                "model_version": GLOBAL_RATIO_DISPLAY_VERSION,
                "primary": ratio_receipts[0], "supplemental": ratio_receipts[1:],
                "document_count": len(ratio_receipts),
                "requested_sector": args.sector_profile, "sector_policy": "NOT_ADMITTED",
                "snapshot_scope": "single_review_database_snapshot",
                "metric_aggregation_authorized": False, "accounting_definition_qualified": False,
                "financial_scoring_authorized": False, "investment_scoring_authorized": False,
                "historical_replay_eligible": False, "validation_authorized": False,
                "execution_authorized": False,
                "limitations": (
                    "Documents stay distinct; no field merging or favorable fallback",
                    "Equal labels or values do not establish period or regulatory equivalence",
                    "Rolling averages cannot be substituted for year-end instant ratios",
                    "Shared-cutoff co-display is not an official ResearchReport or validation",
                ),
            }
        if args.review_freshness:
            freshness_policy = DocumentFreshnessPolicy(
                maximum_report_age_days=settings.research.financial.maximum_report_age_days,
                maximum_source_age_seconds=settings.research.financial.maximum_source_age_seconds)
            inputs: tuple[ReviewedDocumentResearchInput | ReviewedRatioResearchInput, ...] = (
                ReviewedDocumentResearchInput(financial_input_json(reviewed),
                                              args.sector_profile or "unknown"),
                *(ReviewedRatioResearchInput(financial_input_json(receipt), args.sector_profile)
                  for receipt in ratio_receipts),
            )
            document["reviewed_source_freshness"] = {
                "policy_hash": freshness_policy.policy_hash, "diagnostic_only": True,
                "checks": [review_document_freshness(receipt, freshness_policy)
                           for receipt in inputs],
            }
        if holding_context is not None:
            document["combined_evidence_version"] = EQUITY_HOLDING_DISPLAY_VERSION
        document["combined_evidence_hash"] = sha256(
            financial_input_json(document).encode()).hexdigest()
    reject_sensitive_structure(document)
    print(render_equity_note(document) if args.format == "markdown" else
          json.dumps(json.loads(financial_input_json(document)), sort_keys=True,
                     indent=2, allow_nan=False))
    raise SystemExit(2)  # Exploratory output is never validation acceptance.


if __name__ == "__main__":
    main()
