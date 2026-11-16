"""Explicit SEC metadata capture or read-only reconstruction; never financial admission."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.sec_submissions import (
    DATASET,
    SECSubmissionsAdapter,
    download_submissions,
)
from tong_quant.data.sec_filing_inputs import read_sec_filing_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--cik", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--as-of")
    args = parser.parse_args()
    if args.capture:
        request = ProviderDatasetRequest(DATASET, Market.US, args.cik, datetime.now(UTC))
        capture = download_submissions(request)
        captured = datetime.now(UTC)
        request = ProviderDatasetRequest(DATASET, Market.US, args.cik, captured)
        store = SQLiteStore(args.database)
        store.initialize()
        artifacts = FileSystemArtifactStore(args.artifact_root)
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            SECSubmissionsAdapter(download=lambda _: capture, clock=lambda: captured), request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
        store = SQLiteStore(args.database, read_only=True)
        artifacts = FileSystemArtifactStore(args.artifact_root)
    print(json.dumps(json.loads(financial_input_json(read_sec_filing_inputs(
        store, artifacts, args.cik, as_of=as_of))), sort_keys=True, indent=2))
    raise SystemExit(2)  # An unqualified diagnostic never signals validation acceptance.


if __name__ == "__main__":
    main()
