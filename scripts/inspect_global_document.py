"""Explicit primary PDF capture or offline receipt reconstruction; no numeric extraction."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_inputs import read_global_document_inputs
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.global_documents import (
    DATASET,
    PROVIDERS,
    GlobalDocumentAdapter,
    download_document,
    validate_request,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--market", choices=[market.value for market in PROVIDERS], required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--document-url", required=True)
    parser.add_argument("--landing-url")
    parser.add_argument("--issuer-label")
    parser.add_argument("--period-end")
    parser.add_argument("--document-kind", choices=("annual_report", "annual_financial_statements"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--as-of")
    args = parser.parse_args()
    market = Market(args.market)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    if args.capture:
        if any(getattr(args, name) is None for name in (
            "landing_url", "issuer_label", "period_end", "document_kind")):
            parser.error("capture requires explicit issuer/period/kind/landing annotations")
        parameters = {name: getattr(args, name) for name in (
            "document_url", "landing_url", "issuer_label", "period_end", "document_kind")}
        request = ProviderDatasetRequest(DATASET, market, args.subject,
                                         datetime.now(UTC), parameters)
        validate_request(request)
        capture = download_document(request)
        captured = datetime.now(UTC)
        request = ProviderDatasetRequest(DATASET, market, args.subject, captured, parameters)
        store = SQLiteStore(args.database)
        store.initialize()
        ProviderNeutralIngestionService(store, artifact_store=artifacts).ingest(
            GlobalDocumentAdapter(market, download=lambda _: capture, clock=lambda: captured),
            request)
        as_of = datetime.now(UTC)
    else:
        as_of = datetime.fromisoformat(args.as_of)
        require_timezone(as_of, "as_of")
        store = SQLiteStore(args.database, read_only=True)
    print(financial_input_json(read_global_document_inputs(store, artifacts, market, args.subject,
                                                           args.document_url, as_of=as_of)))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
