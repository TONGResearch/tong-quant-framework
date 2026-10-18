import argparse
import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from tong_quant.application.market_rule_references import load_sse_references
from tong_quant.application.sse_calendar_plan import SSECalendarPlanBuilder
from tong_quant.application.sse_pilot_coverage import SSEPilotCoverageReader
from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
from tong_quant.config.settings import load_settings
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calendar_evidence import SSECalendarNoticeProfile
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.models import require_timezone
from tong_quant.markets.capabilities import MarketRuleQuery
from tong_quant.markets.sse_references import SSE_PILOT_SCOPE


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect existing PIT inputs; never create or migrate a database"
    )
    parser.add_argument("--database", type=Path, default=Path("data/tong_quant.sqlite3"))
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-date", type=date.fromisoformat, required=True)
    parser.add_argument("--as-of", type=datetime.fromisoformat, required=True)
    parser.add_argument("--calendar-start", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--pilot-coverage", action="store_true", help="Inspect real pilot research-input coverage"
    )
    parser.add_argument("--universe", default="china_a_all")
    parser.add_argument("--config", type=Path, default=Path("config/default.toml"))
    parser.add_argument("--config-override", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, help="New JSON file, only with --pilot-coverage")
    parser.add_argument(
        "--rule-capture", type=Path, help="Explicit verified capture; enables calendar plan"
    )
    parser.add_argument(
        "--rule-profile", type=Path, default=Path("config/markets/sse-main-board-2026.toml")
    )
    parser.add_argument(
        "--rule-artifact-root", type=Path, default=Path("data/raw/market-rule-references")
    )
    parser.add_argument(
        "--calendar-profile",
        type=Path,
        default=Path("config/markets/sse-calendar-notice-2026-year.toml"),
    )
    parser.add_argument("--artifact-root", type=Path, default=Path("data/raw/provider-artifacts"))
    args = parser.parse_args()
    if args.output is not None and not args.pilot_coverage:
        parser.error("--output requires --pilot-coverage")
    try:
        require_timezone(args.as_of, "as_of")
        if not args.database.is_file():
            print(
                json.dumps(
                    {
                        "status": "database_missing",
                        "boundary": "No database was created; no readiness or trading approval",
                    }
                )
            )
            return 2
        store = SQLiteStore(args.database, read_only=True)
        data = MarketDataService(store)
        builder = None
        if args.rule_capture is not None:
            builder = SSECalendarPlanBuilder(
                load_sse_references(
                    args.rule_profile,
                    artifact_root=args.rule_artifact_root,
                    capture_path=args.rule_capture,
                ),
                SSECalendarNoticeProfile.load(args.calendar_profile),
                FileSystemArtifactStore(args.artifact_root),
            )
        query = MarketRuleQuery(SSE_PILOT_SCOPE, args.trade_date, args.as_of)
        if args.pilot_coverage:
            record = SSEPilotCoverageReader(
                store, load_settings(args.config, *args.config_override), calendar_builder=builder
            ).read(args.symbol, query, calendar_start=args.calendar_start, universe=args.universe)
            rendered = json.dumps(record, sort_keys=True, indent=2, allow_nan=False)
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    output.write(rendered + "\n")
                print(args.output)
            else:
                print(rendered)
            return 2  # Inventory cannot grant research-validation or simulation readiness.
        snapshot = SSERuntimeInputReader(data, calendar_builder=builder).read(
            args.symbol,
            query,
            calendar_start=args.calendar_start,
        )
        print(
            json.dumps(snapshot.to_record(), default=str, sort_keys=True, indent=2, allow_nan=False)
        )
        return 2 if snapshot.gaps else 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        # Provider/database exception messages can contain paths or sensitive source payloads.
        print(json.dumps({"status": "input_inspection_failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
