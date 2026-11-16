"""Capture explicit Nasdaq holiday declarations or reconstruct them offline, never trade."""

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.nasdaq_calendar_inputs import read_nasdaq_calendar_inputs
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.nasdaq_calendar import (
    DATASET,
    NasdaqCalendarAdapter,
    calendar_subject,
    download_calendar,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--max-source-age-seconds", type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--as-of")
    args = parser.parse_args()
    if args.max_source_age_seconds is not None and (
        args.max_source_age_seconds <= 0 or args.capture
    ):
        parser.error("--max-source-age-seconds requires a positive value and read-only --as-of")
    try:
        subject = calendar_subject(args.year)
    except ValueError as error:
        parser.error(str(error))
    if args.capture:
        if args.database.exists():
            parser.error("capture requires a new diagnostic database; existing files are read-only")
        request = ProviderDatasetRequest(DATASET, Market.US, subject, datetime.now(UTC),
                                         {"year": str(args.year)})
        capture = download_calendar(request)
        captured = datetime.now(UTC)
        request = ProviderDatasetRequest(DATASET, Market.US, subject, captured, request.parameters)
        args.database.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(args.database,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except OSError:
            parser.error("new diagnostic database could not be reserved; "
                         "existing files are not reused")
        os.close(descriptor)
        store = SQLiteStore(args.database)
        store.initialize()
        artifacts = FileSystemArtifactStore(args.artifact_root)
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            NasdaqCalendarAdapter(download=lambda _: capture, clock=lambda: captured), request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
        store = SQLiteStore(args.database, read_only=True)
        artifacts = FileSystemArtifactStore(args.artifact_root)
    print(financial_input_json(read_nasdaq_calendar_inputs(
        store, artifacts, args.year, as_of=as_of,
        maximum_source_age_seconds=args.max_source_age_seconds)))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
