"""Capture/inspect price-only Yahoo evidence; never a daily close or valuation admission."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.yahoo_quote import (
    DATASET,
    YahooChinaQuoteEvidenceAdapter,
    download_quote,
    yahoo_equity_symbol,
)
from tong_quant.data.quote_evidence import inspect_yahoo_quote
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--as-of")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("database must already exist")
    if args.as_of is not None and not args.read_only:
        parser.error("as-of applies only to read-only inspection; never backdate a capture")
    yahoo_equity_symbol(args.symbol)
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    require_timezone(as_of, "inspection cutoff")
    store = SQLiteStore(args.database, read_only=args.read_only)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    if not args.read_only:
        capture = download_quote(args.symbol)
        captured = datetime.now(UTC)
        adapter = YahooChinaQuoteEvidenceAdapter(download=lambda _: capture, clock=lambda: captured)
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            adapter, ProviderDatasetRequest(DATASET, Market.CHINA_A, args.symbol, captured))
        as_of = datetime.now(UTC)
    print(json.dumps(json.loads(financial_input_json(inspect_yahoo_quote(
        store, artifacts, args.symbol, as_of=as_of))), indent=2, sort_keys=True))
    # Even a source-bound price is an unqualified observation, never readiness success.
    raise SystemExit(2)


if __name__ == "__main__":
    main()
