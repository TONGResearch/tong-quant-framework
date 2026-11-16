"""Read financial and technical inputs at one cutoff; never a ResearchReport or trade decision."""

import argparse
import json
import tomllib
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.filing_inputs import ReviewedFinancialInputReader
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.market_value_reader import MarketValueInputReader
from tong_quant.data.service import MarketDataService
from tong_quant.data.share_action_reviews import parse_share_action_review
from tong_quant.data.share_capital_inputs import (
    inspect_share_capital_review,
    parse_share_capital_review,
)
from tong_quant.data.share_continuity_inputs import inspect_share_continuity
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import require_timezone
from tong_quant.research.config import research_engine_from_settings
from tong_quant.research.financial.comparisons import financial_comparisons
from tong_quant.research.financial.market_value import (
    MarketValueMatchingPolicy,
    market_value_diagnostics,
)
from tong_quant.research.financial.nonfinancial import nonfinancial_diagnostics
from tong_quant.research.financial.nonfinancial_inputs import (
    NonfinancialInputPolicy,
    assess_nonfinancial_inputs,
)
from tong_quant.research.financial.trailing import (
    parse_trailing_reviews,
    trailing_financial_diagnostics,
)
from tong_quant.research.financial.valuation import valuation_basis_diagnostics
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.quote_alignment import inspect_yahoo_price_alignment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--market", choices=[item.value for item in Market], default="china_a")
    parser.add_argument("--sector-profile", choices=("bank", "nonfinancial", "unknown"),
                        required=True)
    parser.add_argument("--metrics", nargs="+", required=True)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--financial-target-period", type=date.fromisoformat)
    parser.add_argument("--trailing-review-plan", type=Path)
    parser.add_argument("--share-capital-review-plan", type=Path)
    parser.add_argument("--share-continuity-through", type=date.fromisoformat)
    parser.add_argument("--share-action-review-plan", type=Path, action="append", default=[])
    parser.add_argument("--max-quote-age-seconds", type=int)
    parser.add_argument("--max-capture-age-seconds", type=int)
    parser.add_argument("--max-bar-age-seconds", type=int)
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().parents[1] / "config/default.toml")
    args = parser.parse_args()
    if args.financial_target_period is not None and (
        args.market != Market.CHINA_A.value or args.sector_profile != "nonfinancial"
    ):
        parser.error("financial target period currently supports China-A nonfinancial inputs only")
    if args.share_continuity_through is not None and args.share_capital_review_plan is None:
        parser.error("share continuity requires an explicit base share-capital review")
    if args.share_action_review_plan and args.share_continuity_through is None:
        parser.error("share-action reviews require an explicit share-continuity through-date")
    as_of = datetime.fromisoformat(args.as_of)
    require_timezone(as_of, "as_of")
    start = date.fromisoformat(args.start)
    if start > as_of.astimezone(UTC).date():
        parser.error("start must not follow as-of")
    settings = load_settings(args.config)
    matching_policy = MarketValueMatchingPolicy(
        args.max_quote_age_seconds, args.max_capture_age_seconds, args.max_bar_age_seconds)
    trailing_reviews = (parse_trailing_reviews(tomllib.loads(
        args.trailing_review_plan.read_text(encoding="utf-8")))
        if args.trailing_review_plan is not None else ())
    share_review = None
    if args.share_capital_review_plan is not None:
        plan = args.share_capital_review_plan
        if plan.is_symlink() or plan.stat().st_size > 64 * 1024:
            parser.error("unsupported share-capital review plan")
        share_review = parse_share_capital_review(tomllib.loads(plan.read_text(encoding="utf-8")))
        if args.market != Market.CHINA_A.value or share_review.subject != args.symbol:
            parser.error("share-capital review does not match the requested instrument")
    engine = research_engine_from_settings(settings.research)
    document_reviews = []
    for plan in args.share_action_review_plan:
        if plan.is_symlink() or plan.stat().st_size > 64 * 1024:
            parser.error("unsupported share-action review plan")
        item = parse_share_action_review(tomllib.loads(plan.read_text(encoding="utf-8")))
        if args.market != Market.CHINA_A.value or item.subject != args.symbol:
            parser.error("share-action review does not match the requested instrument")
        document_reviews.append(item)
    technical = next(module for module in engine.modules
                     if isinstance(module, TechnicalResearchModule))
    store = SQLiteStore(args.database, read_only=True)
    service = MarketDataService(store)
    with service.read_snapshot():
        inputs = ReviewedFinancialInputReader(
            store, FileSystemArtifactStore(args.artifact_root),
        ).read(args.symbol, Market(args.market), tuple(args.metrics), as_of=as_of,
               sector_profile=args.sector_profile)
        bars = tuple(service.daily_bars(
            args.symbol, Market(args.market), AssetType.EQUITY, start,
            as_of.astimezone(UTC).date(), as_of=as_of,
        ))
        market_values = MarketValueInputReader(
            store, FileSystemArtifactStore(args.artifact_root),
        ).read(args.symbol, Market(args.market), as_of=as_of)
        document = {
            "symbol": args.symbol, "market": args.market, "as_of": as_of,
            "start": start, "research_report_created": False,
            "financial_inputs": inputs.document(),
            "nonfinancial_input_assessment": (assess_nonfinancial_inputs(
                inputs, NonfinancialInputPolicy(
                    settings.research.financial.maximum_report_age_days),
                target_period_end=args.financial_target_period)
                if inputs.market is Market.CHINA_A and inputs.sector_profile == "nonfinancial"
                else {"status": "NOT_APPLICABLE"}),
            "financial_comparisons": [item.document() for item in financial_comparisons(inputs)],
            "nonfinancial_diagnostics": (
                [item.document() for item in nonfinancial_diagnostics(inputs)]
                if inputs.market is Market.CHINA_A and inputs.sector_profile == "nonfinancial"
                else []),
            "observed_bar_rows": len(bars),
            "market_value_inputs": market_values.document(),
            "share_capital_review": (inspect_share_capital_review(
                store, FileSystemArtifactStore(args.artifact_root), share_review, as_of=as_of)
                if share_review is not None else {"status": "NOT_REQUESTED"}),
            "share_continuity_review": (inspect_share_continuity(
                store, FileSystemArtifactStore(args.artifact_root), share_review,
                through=args.share_continuity_through, as_of=as_of,
                document_reviews=tuple(document_reviews))
                if share_review is not None and args.share_continuity_through is not None
                else {"status": "NOT_REQUESTED"}),
            "market_value_diagnostics": market_value_diagnostics(
                market_values, bars, matching_policy),
            "yahoo_price_alignment": inspect_yahoo_price_alignment(
                store, FileSystemArtifactStore(args.artifact_root), args.symbol,
                Market(args.market), bars, as_of=as_of, policy=matching_policy),
            "valuation_basis_diagnostics": (
                [item.document() for item in valuation_basis_diagnostics(inputs)]
                if inputs.market is Market.CHINA_A and inputs.sector_profile == "nonfinancial"
                else []),
            "last_bar_timestamp": bars[-1].timestamp if bars else None,
            "trailing_financial_diagnostics": (
                [item.document() for item in trailing_financial_diagnostics(
                    inputs, trailing_reviews)]
                if inputs.market is Market.CHINA_A and inputs.sector_profile == "nonfinancial"
                else []),
            "technical": technical_diagnostics(bars, technical.parameters, as_of=as_of),
            "screening_status": "NOT_ASSESSED", "financial_scoring_policy": "NOT_ADMITTED",
            "investment_scoring_authorized": False, "validation_authorized": False,
            "execution_authorized": False, "readiness_promoted": False,
            "limitations": (
                "Input diagnostics only; no queue, hard-screen result or report is invented.",
                "Financial source binding is not independent annotation verification or scoring.",
                "Technical families can conflict; unadjusted gaps/actions need separate review.",
                "Same cutoff does not prove matched freshness or full financial coverage.",
            ),
        }
    encoded = financial_input_json(document)
    safe = json.loads(encoded)
    reject_sensitive_structure(safe)
    print(json.dumps({**safe, "input_review_hash": sha256(encoded.encode()).hexdigest()},
                     indent=2, sort_keys=True, allow_nan=False))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
