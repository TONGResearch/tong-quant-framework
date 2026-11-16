"""Explicit catalog-pinned SEC filing body capture or fixed-cutoff subset review."""

import argparse
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.sec_body import SECBodyAdapter, download_body
from tong_quant.data.sec_body_inputs import build_sec_body_request, read_sec_body_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--cik", required=True)
    parser.add_argument("--accession", required=True)
    parser.add_argument("--explain-exclusions", action="store_true",
                        help="read-only structural inventory; never accept excluded values")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--as-of")
    args = parser.parse_args()
    if args.explain_exclusions and args.capture:
        parser.error("exclusion explanation is read-only; capture separately")
    artifacts = FileSystemArtifactStore(args.artifact_root)
    store = SQLiteStore(args.database, read_only=not args.capture)
    if args.capture:
        request = build_sec_body_request(store, artifacts, args.cik, args.accession,
                                         as_of=datetime.now(UTC))
        capture = download_body(request)
        captured = datetime.now(UTC)
        request = replace(request, as_of=captured)
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            SECBodyAdapter(download=lambda _: capture, clock=lambda: captured), request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
    print(financial_input_json(read_sec_body_inputs(store, artifacts, args.cik, args.accession,
        as_of=as_of, explain_exclusions=args.explain_exclusions)))
    raise SystemExit(2)  # An exploratory subset cannot authorize research or trading.


if __name__ == "__main__":
    main()
