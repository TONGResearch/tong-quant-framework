import argparse
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from tong_quant.application.sse_runtime_inputs import SSERuntimeInputReader
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
    args = parser.parse_args()
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
        data = MarketDataService(SQLiteStore(args.database, read_only=True))
        snapshot = SSERuntimeInputReader(data).read(
            args.symbol,
            MarketRuleQuery(SSE_PILOT_SCOPE, args.trade_date, args.as_of),
            calendar_start=args.calendar_start,
        )
        print(
            json.dumps(snapshot.to_record(), default=str, sort_keys=True, indent=2, allow_nan=False)
        )
        return 2 if snapshot.gaps else 0
    except (ValueError, RuntimeError, sqlite3.Error) as error:
        # Provider/database exception messages can contain paths or sensitive source payloads.
        print(json.dumps({"status": "input_inspection_failed", "error_type": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
