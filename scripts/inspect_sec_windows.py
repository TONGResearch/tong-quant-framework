"""Read exact same-filing window context only; no capture, arithmetic or orders."""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Never

from tong_quant.application.sec_window_inventory import (
    SECWindowPair,
    read_sec_source_reference_changes,
    read_sec_window_inventory,
)
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.sec_period_inputs import parse_sec_period_selections
from tong_quant.data.storage.sqlite import SQLiteStore


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid read-only SEC window arguments.\n")


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    for name in ("database", "artifact-root"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("cik", "accession", "symbol", "as-of", "left", "right", "namespace"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--max-capture-age-seconds", type=int, required=True)
    parser.add_argument("--previous-as-of")
    parser.add_argument("--with-selected-capture-identity", action="store_true")
    parser.add_argument("--with-check-gap-state", action="store_true")
    parser.add_argument("--with-record-projections", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        if args.compact and args.previous_as_of is None:
            raise ValueError("compact source view requires both explicit cutoffs")
        if args.with_record_projections and not args.with_check_gap_state:
            raise ValueError("record projections require check-gap state")
        if args.with_check_gap_state and not args.with_selected_capture_identity:
            raise ValueError("check-gap state requires complete selected-capture identity")
        if args.with_selected_capture_identity and args.previous_as_of is None:
            raise ValueError("selected capture identity requires both explicit cutoffs")
        pair = SECWindowPair(parse_sec_period_selections([args.left])[0],
                             parse_sec_period_selections([args.right])[0], args.namespace)
        if args.previous_as_of is None:
            output = read_sec_window_inventory(SQLiteStore(args.database, read_only=True),
                FileSystemArtifactStore(args.artifact_root), args.cik, args.accession,
                symbol=args.symbol, as_of=datetime.fromisoformat(args.as_of), pairs=(pair,),
                maximum_capture_age_seconds=args.max_capture_age_seconds)
        else:
            output = read_sec_source_reference_changes(SQLiteStore(args.database, read_only=True),
                FileSystemArtifactStore(args.artifact_root), args.cik, args.accession,
                symbol=args.symbol, previous_as_of=datetime.fromisoformat(args.previous_as_of),
                as_of=datetime.fromisoformat(args.as_of), pairs=(pair,),
                maximum_capture_age_seconds=args.max_capture_age_seconds,
                with_selected_capture_identity=args.with_selected_capture_identity,
                with_check_gap_state=args.with_check_gap_state,
                with_record_projections=args.with_record_projections, compact=args.compact)
    except (ValueError, TypeError, OverflowError, OSError, sqlite3.Error):
        parser.exit(2, "Read-only SEC window inputs could not be verified.\n")
    print(financial_input_json(output))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
