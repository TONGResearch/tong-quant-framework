import argparse
import json
import math
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.cache import DataFrameCache
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.pipeline import DataIngestionPipeline
from tong_quant.data.providers import AkShareAdapter
from tong_quant.data.storage import SQLiteStore
from tong_quant.domain.enums import Adjustment, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest AKShare data into Tong Quant SQLite")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--refresh", action="store_true", help="Bypass cached payloads")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
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
    actions = subparsers.add_parser("corporate-actions")
    actions.add_argument("symbol")
    subparsers.add_parser("universe")
    args = parser.parse_args()
    if not math.isfinite(args.timeout_seconds) or not 0 < args.timeout_seconds <= 300:
        parser.error("timeout must be positive and at most 300 seconds")
    if hasattr(args, "symbol") and (
        len(args.symbol) != 6 or not args.symbol.isascii() or not args.symbol.isdigit()
    ):
        parser.error("symbol must contain six ASCII digits")
    if args.command == "daily-bars":
        try:
            start = datetime.strptime(args.start_date, "%Y%m%d").date()
            end = datetime.strptime(args.end_date, "%Y%m%d").date()
        except ValueError:
            parser.error("dates must be valid YYYYMMDD dates")
        if start > end:
            parser.error("start date cannot follow end date")
        if args.adjustment != Adjustment.NONE.value:
            parser.error("strict PIT ingestion accepts only unadjusted bars")
    return args


def run_worker(args: argparse.Namespace) -> int:
    settings = load_settings(Path("config/default.toml"))
    cache = DataFrameCache(
        settings.data.cache_root,
        timedelta(seconds=settings.data.cache_ttl_seconds),
    )
    pipeline = DataIngestionPipeline(
        AkShareAdapter(cache=None if args.refresh else cache),
        SQLiteStore(args.database or settings.data.database_path),
        strict_point_in_time=settings.data.strict_point_in_time,
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
    elif args.command == "corporate-actions":
        result = pipeline.ingest_corporate_actions(args.symbol)
    else:
        result = pipeline.ingest_a_share_universe()

    complete = result.accepted > 0 and result.rejected == 0
    record = {"status": "completed" if complete else "partial", **asdict(result)}
    reject_sensitive_structure(record, path="ingestion_result")
    print(json.dumps(record, sort_keys=True))
    return 0 if complete else 2


def main() -> int:
    args = parse_args()
    try:
        if args.worker:
            return run_worker(args)
        # Kill/reap the isolated worker on timeout, including endpoints without native timeouts.
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", *sys.argv[1:]],
            capture_output=True,
            text=True,
            timeout=args.timeout_seconds,
            check=False,
        )
        record = json.loads(result.stdout.splitlines()[-1])
        if not isinstance(record, dict) or record.get("status") not in {
            "completed",
            "partial",
            "failed",
        }:
            raise ValueError("invalid worker response")
        reject_sensitive_structure(record, path="ingestion_result")
        if result.returncode != 0 and record["status"] == "completed":
            raise ValueError("worker exit status contradicts completion")
        print(json.dumps(record, sort_keys=True))
        return 0 if result.returncode == 0 and record["status"] == "completed" else 2
    except subprocess.TimeoutExpired:
        print(json.dumps({"status": "failed", "error_type": "ProviderTimeout"}))
        return 2
    except Exception as error:
        # Do not render raw provider exceptions or captured stdout/stderr.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
