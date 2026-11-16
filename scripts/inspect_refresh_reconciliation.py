"""Read-only exact refresh receipt inspection; no collection, repair or checkpoint."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Never

from tong_quant.data.refresh_reconciliation import inspect_refresh_reconciliation


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid read-only inspection arguments; no state changed.\n")


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-records", type=int, default=10_000)
    parser.add_argument("--max-file-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=512 * 1024 * 1024)
    args = parser.parse_args()
    try:
        report = inspect_refresh_reconciliation(
            args.database, args.artifact_root, job_id=args.job_id,
            inspected_as_of=datetime.fromisoformat(args.as_of), max_records=args.max_records,
            max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes,
        )
    except (ValueError, TypeError):
        parser.exit(2, "Invalid read-only inspection input; no state changed.\n")
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    # Even intact failure snapshots remain non-successful diagnostics.
    raise SystemExit(0 if report["status"] == "LINKED_BYTES_MATCH" else 1)


if __name__ == "__main__":
    main()
