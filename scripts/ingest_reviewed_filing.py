"""Preview by default; explicitly publish a retained manual issuer-filing review."""

import argparse
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.filing_facts import ingest_filing_extraction, prepare_filing_extraction
from tong_quant.data.providers.reviewed_filings import parse_filing_review
from tong_quant.data.storage.sqlite import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument(
        "--as-of", help="Explicit timezone-aware assessment cutoff; default UTC now",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.review_plan.is_symlink() or args.review_plan.stat().st_size > 64 * 1024:
        parser.error("unsupported review plan")
    plan_bytes = args.review_plan.read_bytes()
    review = parse_filing_review(tomllib.loads(plan_bytes.decode()))
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    # Opening a missing database or upgrading a schema is never implicit here.
    with SQLiteStore(args.database, read_only=True).read_snapshot() as store:
        prepared = prepare_filing_extraction(store, artifacts, review, as_of=as_of)
    document: dict[str, object] = {
        "mode": "write" if args.write else "preview", "subject": review.subject,
        "dataset": prepared.batch.dataset, "raw_data_hash": prepared.batch.raw_data_hash,
        "facts": [{"metric": fact.metric, "value": str(fact.value), "unit": fact.unit,
                   "currency": fact.currency, "available_at": fact.available_at.isoformat(),
                   "trust_level": fact.trust_level.value} for fact in prepared.facts("")],
        "historical_replay_eligible": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "native_mapping_authorized": False,
        "limitations": [item.description for item in prepared.batch.limitations],
    }
    if args.review_plan.read_bytes() != plan_bytes:
        raise ValueError("review plan changed during preparation")
    if args.write:
        result = ingest_filing_extraction(
            SQLiteStore(args.database), artifacts, review, as_of=as_of,
        )
        document["batch_id"] = result.batch_id
        document["accepted"] = result.accepted
    print(json.dumps(document, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
