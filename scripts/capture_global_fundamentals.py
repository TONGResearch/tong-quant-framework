"""Explicitly capture or read native annual observations; never canonical financial admission."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_fundamental_inputs import read_global_fundamental_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_fundamentals import (
    DATASET,
    YahooFundamentalSnapshotAdapter,
    download_fundamentals,
)
from tong_quant.data.providers.yahoo_identity import TIMEZONES
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--market", choices=[market.value for market in TIMEZONES], required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--as-of")
    args = parser.parse_args()
    if args.capture and (not args.start or not args.end or args.as_of):
        parser.error("capture requires explicit dates and forbids historical as-of")
    if not args.capture and (not args.as_of or args.start or args.end):
        parser.error("read-only mode requires as-of and forbids capture dates")
    market = Market(args.market)
    store = SQLiteStore(args.database, read_only=not args.capture)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    if args.capture:
        request = ProviderDatasetRequest(DATASET, market, args.symbol, datetime.now(UTC),
            {"start_date": args.start, "end_date": args.end})
        capture = download_fundamentals(request)
        captured = datetime.now(UTC)
        request = ProviderDatasetRequest(DATASET, market, args.symbol, captured, request.parameters)
        store.initialize()
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            YahooFundamentalSnapshotAdapter(download=lambda _: capture, clock=lambda: captured),
            request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
    print(json.dumps(json.loads(financial_input_json(read_global_fundamental_inputs(
        store, artifacts, args.symbol, market, as_of=as_of))), sort_keys=True, indent=2))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
