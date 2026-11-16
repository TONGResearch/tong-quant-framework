"""Capture one current equity market-value response; never populate historical prices/facts."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.market_value_reader import MarketValueInputReader
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.eastmoney_market_values import (
    DATASET,
    EastmoneyMarketValueAdapter,
    download_quote,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    # Require the explicit, existing research database; never create a second source of truth.
    if not args.database.is_file():
        parser.error("database must already exist")
    store = SQLiteStore(args.database)
    capture = download_quote(args.symbol)
    captured_at = datetime.now(UTC)
    adapter = EastmoneyMarketValueAdapter(download=lambda _: capture, clock=lambda: captured_at)
    result = ProviderNeutralIngestionService(
        store, artifact_store=FileSystemArtifactStore(args.artifact_root),
    ).ingest(adapter, ProviderDatasetRequest(
        DATASET, Market.CHINA_A, args.symbol, captured_at))
    snapshot = MarketValueInputReader(store, FileSystemArtifactStore(args.artifact_root)).read(
        args.symbol, Market.CHINA_A, as_of=datetime.now(UTC))
    latest = max(snapshot.inspections, key=lambda item: item.record.available_at)
    print(json.dumps({"batch_id": result.batch_id, "capture_records": result.accepted,
                      "status": latest.record.payload["status"],
                      "reasons": latest.record.payload["reasons"],
                      "source_bound": latest.source_bound,
                      "numeric_coverage_verified": False, "valuation_authorized": False,
                      "message": "Capture records include failed attempts; inspect at cutoff"},
                     indent=2))
    if not latest.source_bound or latest.record.payload["status"] != "observed_unqualified":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
