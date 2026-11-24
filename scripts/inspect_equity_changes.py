"""Compare explicitly dated retained equity snapshots; never captures or sends orders."""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Never

from tong_quant.application.equity_changes import read_equity_change_digest
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid read-only change arguments; no state changed.\n")


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--market", choices=("us", "hong_kong", "malaysia"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--previous-as-of", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-observation-age-seconds", type=int, required=True)
    parser.add_argument("--with-period-context", action="store_true")
    parser.add_argument("--max-native-capture-age-seconds", type=int)
    args = parser.parse_args()
    try:
        output = read_equity_change_digest(SQLiteStore(args.database, read_only=True),
            FileSystemArtifactStore(args.artifact_root), args.symbol, Market(args.market),
            previous_as_of=datetime.fromisoformat(args.previous_as_of),
            as_of=datetime.fromisoformat(args.as_of),
            maximum_age_seconds=args.max_observation_age_seconds,
            include_period_context=args.with_period_context,
            maximum_native_capture_age_seconds=args.max_native_capture_age_seconds)
    except (ValueError, TypeError, OSError, sqlite3.Error):
        parser.exit(2, "Read-only change inputs could not be verified.\n")
    print(financial_input_json(output))
    raise SystemExit(2)  # Even a numerical comparison is unqualified research information.


if __name__ == "__main__":
    main()
