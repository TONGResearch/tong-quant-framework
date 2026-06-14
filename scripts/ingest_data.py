import argparse
from datetime import timedelta
from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers import AkShareAdapter
from tong_quant.data.storage import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest AKShare data into Tong Quant SQLite")
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily = subparsers.add_parser("daily-bars")
    daily.add_argument("symbol")
    daily.add_argument("start_date", help="YYYYMMDD")
    daily.add_argument("end_date", help="YYYYMMDD")
    daily.add_argument("--index", action="store_true")
    daily.add_argument(
        "--adjustment",
        choices=[adjustment.value for adjustment in Adjustment],
        default=Adjustment.NONE.value,
    )

    subparsers.add_parser("calendar")
    company = subparsers.add_parser("company")
    company.add_argument("symbol")
    subparsers.add_parser("universe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(Path("config/default.toml"))
    cache = DataFrameCache(
        settings.data.cache_root,
        timedelta(seconds=settings.data.cache_ttl_seconds),
    )
    pipeline = DataIngestionPipeline(
        AkShareAdapter(cache=cache),
        SQLiteStore(settings.data.database_path),
    )
    pipeline.initialize()

    if args.command == "daily-bars":
        result = pipeline.ingest_daily_bars(
            DailyBarRequest(
                symbol=args.symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                asset_type=AssetType.INDEX if args.index else AssetType.EQUITY,
                adjustment=Adjustment(args.adjustment),
            )
        )
    elif args.command == "calendar":
        result = pipeline.ingest_trading_calendar()
    elif args.command == "company":
        result = pipeline.ingest_company_info(args.symbol)
    else:
        result = pipeline.ingest_a_share_universe()

    print(result)


if __name__ == "__main__":
    main()
