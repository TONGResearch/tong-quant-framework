"""Capture exactly one older page referenced by a verified local SEC parent catalog."""

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.sec_filing_page import SECFilingPageAdapter, download_page
from tong_quant.data.sec_filing_archive import (
    build_sec_page_request,
    read_sec_filing_archive_inputs,
)
from tong_quant.data.storage.sqlite import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--cik", required=True)
    parser.add_argument("--page", required=True)
    parser.add_argument("--capture", action="store_true", required=True)
    args = parser.parse_args()
    artifacts = FileSystemArtifactStore(args.artifact_root)
    request = build_sec_page_request(SQLiteStore(args.database, read_only=True), artifacts,
        args.cik, args.page, as_of=datetime.now(UTC))
    capture = download_page(request)
    captured = datetime.now(UTC)
    request = replace(request, as_of=captured)
    store = SQLiteStore(args.database)
    ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
        SECFilingPageAdapter(download=lambda _: capture, clock=lambda: captured), request)
    as_of = datetime.now(UTC)
    archive = read_sec_filing_archive_inputs(store, artifacts, args.cik, as_of=as_of)
    print(json.dumps({"as_of": as_of.isoformat(), "page": args.page,
        "archive_status": archive["status"], "input_hash": archive["input_hash"],
        "pages": [{key: row.get(key) for key in ("name", "status", "use_status", "usable")}
                  for row in archive["pages"]], "historical_replay_eligible": False}, indent=2))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
