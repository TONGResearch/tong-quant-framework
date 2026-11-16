"""Explicit native XBRL concept capture or fixed-cutoff read, never financial scoring."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.sec_concept import (
    DATASET,
    SECConceptAdapter,
    concept_subject,
    download_concept,
)
from tong_quant.data.sec_concept_inputs import read_sec_concept_inputs
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--cik", required=True)
    parser.add_argument("--taxonomy", choices=("us-gaap", "ifrs-full"), required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--include-older-pages", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--as-of")
    args = parser.parse_args()
    subject = concept_subject(args.cik, args.taxonomy, args.tag)
    if args.capture:
        request = ProviderDatasetRequest(DATASET, Market.US, subject, datetime.now(UTC))
        capture = download_concept(request)
        captured = datetime.now(UTC)
        request = ProviderDatasetRequest(DATASET, Market.US, subject, captured)
        store = SQLiteStore(args.database)
        store.initialize()
        artifacts = FileSystemArtifactStore(args.artifact_root)
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            SECConceptAdapter(download=lambda _: capture, clock=lambda: captured), request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
        store = SQLiteStore(args.database, read_only=True)
        artifacts = FileSystemArtifactStore(args.artifact_root)
    document = read_sec_concept_inputs(store, artifacts, args.cik, args.taxonomy, args.tag,
                                       as_of=as_of, include_older_pages=args.include_older_pages)
    print(json.dumps(json.loads(financial_input_json(document)), sort_keys=True, indent=2))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
