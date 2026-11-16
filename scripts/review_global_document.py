"""Preview or explicitly persist unqualified overseas monetary/percentage annotations."""

import argparse
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_document_review_inputs import (
    ingest_global_document_review,
    prepare_global_document_review,
    read_global_document_review_inputs,
)
from tong_quant.data.global_ratio_review_inputs import (
    ingest_global_ratio_review,
    prepare_global_ratio_review,
    read_global_ratio_review_inputs,
)
from tong_quant.data.providers.global_document_reviews import parse_global_document_review
from tong_quant.data.providers.global_ratio_reviews import parse_global_ratio_review
from tong_quant.data.storage.sqlite import SQLiteStore


def _ratio_output(args: argparse.Namespace, content: bytes, as_of: datetime,
                  artifacts: FileSystemArtifactStore) -> dict[str, Any]:
    review = parse_global_ratio_review(tomllib.loads(content.decode()))
    batch = prepare_global_ratio_review(SQLiteStore(args.database, read_only=True),
                                        artifacts, review, as_of=as_of)
    if args.review_plan.read_bytes() != content:
        raise ValueError("overseas ratio plan changed during preparation")
    if args.write:
        result = ingest_global_ratio_review(SQLiteStore(args.database), artifacts, review)
        output = read_global_ratio_review_inputs(SQLiteStore(args.database, read_only=True),
            artifacts, review.market, review.subject, review.document_url, as_of=datetime.now(UTC))
        return {**output, "batch_id": result.batch_id, "mode": "write"}
    return {"mode": "preview", **batch.records[0].payload,
            "raw_data_hash": batch.raw_data_hash, "persisted": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--kind", choices=("monetary", "ratio"), default="monetary")
    parser.add_argument("--as-of")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write and args.as_of is not None:
        parser.error("write uses actual recording time; --as-of is preview-only")
    if args.review_plan.is_symlink() or args.review_plan.stat().st_size > 128 * 1024:
        parser.error("unsupported overseas review plan")
    content = args.review_plan.read_bytes()
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    artifacts = FileSystemArtifactStore(args.artifact_root)
    if args.kind == "ratio":
        print(financial_input_json(_ratio_output(args, content, as_of, artifacts)))
        raise SystemExit(2)
    review = parse_global_document_review(tomllib.loads(content.decode()))
    batch = prepare_global_document_review(SQLiteStore(args.database, read_only=True),
                                            artifacts, review, as_of=as_of)
    if args.review_plan.read_bytes() != content:
        raise ValueError("overseas review plan changed during preparation")
    if args.write:
        result = ingest_global_document_review(SQLiteStore(args.database), artifacts, review)
        output = read_global_document_review_inputs(SQLiteStore(args.database, read_only=True),
            artifacts, review.market, review.subject, review.document_url, as_of=datetime.now(UTC))
        output.update(batch_id=result.batch_id, mode="write")
    else:
        output = {"mode": "preview", **batch.records[0].payload,
                  "raw_data_hash": batch.raw_data_hash, "persisted": False}
    print(financial_input_json(output))
    raise SystemExit(2)  # An unqualified manual record is not a decision or scoring approval.


if __name__ == "__main__":
    main()
