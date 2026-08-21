import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tong_quant.data.baselines import (
    ProviderBaselineBuilder,
    ProviderBaselineQuery,
    ProviderBaselineScope,
    render_provider_baseline_markdown,
    serialize_provider_baseline,
)
from tong_quant.data.providers.cninfo import CNINFO_DISCLOSURES_DATASET
from tong_quant.data.providers.yahoo import YAHOO_DAILY_BARS_DATASET
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immutable longitudinal baseline from stored provider contract checks"
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/provider-contract-monitor.sqlite3"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/provider-contracts"),
    )
    parser.add_argument("--window-days", type=int, default=84)
    parser.add_argument("--interval-days", type=int, default=7)
    parser.add_argument("--china-symbol", default="600000")
    parser.add_argument("--us-symbol", default="MSFT")
    parser.add_argument("--hong-kong-symbol", default="0700.HK")
    parser.add_argument("--malaysia-symbol", default="1155.KL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.window_days < 1 or args.interval_days < 1:
        raise SystemExit("--window-days and --interval-days must be positive")

    now = datetime.now(UTC)
    store = SQLiteStore(args.database)
    store.initialize()
    query = ProviderBaselineQuery(
        period_start=now - timedelta(days=args.window_days),
        period_end=now,
        expected_interval_days=args.interval_days,
        scopes=_default_scopes(
            china_symbol=args.china_symbol,
            us_symbol=args.us_symbol,
            hong_kong_symbol=args.hong_kong_symbol,
            malaysia_symbol=args.malaysia_symbol,
        ),
    )
    manifest = ProviderBaselineBuilder(repository=store).build(query)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = args.output_dir / "provider-contract-baseline.md"
    json_path = args.output_dir / "provider-contract-baseline.json"
    markdown_path.write_text(
        render_provider_baseline_markdown(manifest), encoding="utf-8"
    )
    json_path.write_text(serialize_provider_baseline(manifest) + "\n", encoding="utf-8")
    print(markdown_path)
    print(json_path)


def _default_scopes(
    *,
    china_symbol: str,
    us_symbol: str,
    hong_kong_symbol: str,
    malaysia_symbol: str,
) -> tuple[ProviderBaselineScope, ...]:
    return (
        ProviderBaselineScope(
            provider="cninfo_via_akshare",
            dataset=CNINFO_DISCLOSURES_DATASET,
            market=Market.CHINA_A,
            subject=china_symbol,
        ),
        ProviderBaselineScope(
            provider="yahoo_finance",
            dataset=YAHOO_DAILY_BARS_DATASET,
            market=Market.US,
            subject=us_symbol,
        ),
        ProviderBaselineScope(
            provider="yahoo_finance",
            dataset=YAHOO_DAILY_BARS_DATASET,
            market=Market.HONG_KONG,
            subject=hong_kong_symbol,
        ),
        ProviderBaselineScope(
            provider="yahoo_finance",
            dataset=YAHOO_DAILY_BARS_DATASET,
            market=Market.MALAYSIA,
            subject=malaysia_symbol,
        ),
    )


if __name__ == "__main__":
    main()
