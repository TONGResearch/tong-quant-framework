"""Read existing captures and export a non-authorizing numeric spot review."""

import argparse
import json
import tomllib
from dataclasses import fields
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calibration.financial_review import FilingRowReview, corroborate_financial_row
from tong_quant.data.providers.contracts import FINANCIAL_SNAPSHOT_DATASET, ProviderArtifact
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.version import FINANCIAL_CORROBORATION_VERSION


def _review(raw: dict[str, Any], common: dict[str, Any]) -> FilingRowReview:
    values = {**common, **raw}
    if set(values) != {field.name for field in fields(FilingRowReview)}:
        raise ValueError("review plan schema mismatch")
    for key in ("filing_value", "filing_scale", "native_scale_hypothesis"):
        # Quoted decimals only: TOML floats have already lost source precision.
        if not isinstance(values[key], str):
            raise ValueError("review plan decimals must be quoted")
        values[key] = Decimal(values[key])
    values["period_end"] = date.fromisoformat(values["period_end"])
    values["period_start"] = date.fromisoformat(values["period_start"]) if (
        values["period_start"]
    ) else None
    values["reviewed_at"] = datetime.fromisoformat(values["reviewed_at"])
    values["source_pages"] = tuple(values["source_pages"])
    return FilingRowReview(**values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("output exists; overwrite disabled")
    if args.review_plan.is_symlink() or args.review_plan.stat().st_size > 64 * 1024:
        parser.error("unsupported review plan")
    plan_bytes = args.review_plan.read_bytes()
    plan = tomllib.loads(plan_bytes.decode())
    reject_sensitive_structure(plan, path="financial_review_plan")
    as_of = datetime.fromisoformat(args.as_of)
    reviews = tuple(_review(item, plan["common"]) for item in plan["rows"])
    if (not reviews or len(reviews) > 100
            or len({r.canonical_metric for r in reviews}) != len(reviews)):
        parser.error("require 1-100 unique reviewed metrics")
    store = SQLiteStore(args.database, read_only=True)
    service = MarketDataService(store)
    artifact_store = FileSystemArtifactStore(args.artifact_root)
    results = []
    with service.read_snapshot():
        for review in reviews:
            try:
                records = service.provider_evidence(
                    provider="akshare", dataset=FINANCIAL_SNAPSHOT_DATASET,
                    market=Market.CHINA_A, subject=review.subject, as_of=as_of,
                )
                native = next(item for item in records
                              if item.evidence_id == review.native_evidence_id)
                captures = [item for item in store.provider_artifact_history(
                    provider="cninfo_direct", dataset="china_disclosures", subject=review.subject,
                ) if item["content_hash"] == review.filing_sha256
                    and datetime.fromisoformat(item["retrieved_at"]) <= as_of]
                if not captures:
                    raise ValueError("missing filing capture")
                capture = captures[0]
                pdf = artifact_store.read_content(review.filing_sha256, "application/pdf",
                                                  max_bytes=50 * 1024 * 1024)
                filing = ProviderArtifact(
                    artifact_id=capture["artifact_id"], provider=capture["provider"],
                    dataset=capture["dataset"], market=Market(capture["market"]),
                    subject=capture["subject"], source_identity=capture["source_identity"],
                    source_reference=capture["source_reference"],
                    published_at=datetime.fromisoformat(capture["published_at"]),
                    retrieved_at=datetime.fromisoformat(capture["retrieved_at"]),
                    content_hash=capture["content_hash"], media_type=capture["media_type"],
                    availability_precision=AvailabilityPrecision(capture["availability_precision"]),
                    trust_level=DataTrustLevel(capture["trust_level"]), content=pdf,
                )
                native_bytes = artifact_store.read_content(
                    native.raw_data_hash, "application/json", max_bytes=16 * 1024 * 1024,
                )
                results.append(corroborate_financial_row(
                    review, native, native_bytes, filing, as_of=as_of,
                ))
            except (OSError, ValueError, KeyError, TypeError, StopIteration, ArithmeticError):
                results.append({"metric": review.canonical_metric, "status": "INPUT_REJECTED",
                                "canonical_population_authorized": False})
    document = {"scope": "financial_numeric_spot_review", "as_of": as_of.isoformat(),
                "model_version": FINANCIAL_CORROBORATION_VERSION,
                "review_plan_sha256": sha256(plan_bytes).hexdigest(),
                "results": results, "canonical_population_authorized": False,
                "historical_replay_eligible": False, "investment_scoring_authorized": False,
                "validation_authorized": False, "independent_provider_validation": False}
    reject_sensitive_structure(document)
    if args.review_plan.read_bytes() != plan_bytes:
        raise ValueError("review plan changed during evaluation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        args.output.chmod(0o600)
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(args.output)
    raise SystemExit(2)  # Numeric agreement never completes semantic/historical review.


if __name__ == "__main__":
    main()
