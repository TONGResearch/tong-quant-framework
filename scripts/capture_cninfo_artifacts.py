import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.calibration.coordinator import ProviderCalibrationCoordinator
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.cninfo import (
    CNINFO_DISCLOSURES_DATASET,
    CnInfoEvidenceAdapter,
)
from tong_quant.data.providers.cninfo_direct import (
    CnInfoDirectEvidenceAdapter,
    CnInfoHttpClient,
    cninfo_calibration_snapshot,
)
from tong_quant.data.providers.contracts import (
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture direct CNInfo disclosure evidence without trading logic"
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--category-code", default="")
    parser.add_argument("--database", type=Path, default=Path("data/cninfo.sqlite3"))
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("data/provider-artifacts"),
    )
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--max-artifacts", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--compare-akshare", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


@dataclass(frozen=True, slots=True)
class _FetchedAdapter:
    capabilities_value: tuple[ProviderDatasetCapability, ...]
    batch: ProviderEvidenceBatch

    @property
    def provider_id(self) -> str:
        return self.batch.provider

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return self.capabilities_value

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if request.dataset != self.batch.dataset or request.market != self.batch.market:
            raise ValueError("pre-fetched CNInfo batch does not match the request")
        return self.batch


def main() -> None:
    args = parse_args()
    if not 0 <= args.max_artifacts <= 100:
        raise SystemExit("--max-artifacts must be between 0 and 100")
    if not 1 <= args.max_pages <= 100:
        raise SystemExit("--max-pages must be between 1 and 100")
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        raise SystemExit("--output already exists; overwrite is disabled")

    as_of = datetime.now(UTC)
    request = ProviderDatasetRequest(
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject=args.symbol,
        as_of=as_of,
        parameters={
            "start_date": args.start_date,
            "end_date": args.end_date,
            "category_code": args.category_code,
            "capture_artifacts": str(not args.metadata_only).lower(),
            "max_artifacts": str(args.max_artifacts),
        },
    )
    direct = CnInfoDirectEvidenceAdapter(
        client=CnInfoHttpClient(max_pages=args.max_pages),
        clock=lambda: datetime.now(UTC),
    )
    direct_batch = direct.fetch(request)
    store = SQLiteStore(args.database)
    store.initialize()
    result = ProviderNeutralIngestionService(
        store=store,
        artifact_store=FileSystemArtifactStore(args.artifact_dir),
    ).ingest(
        _FetchedAdapter(direct.capabilities(), direct_batch),
        request,
    )

    comparison: dict[str, object] | None = None
    if args.compare_akshare:
        transported = CnInfoEvidenceAdapter(
            AkShareAdapter(clock=lambda: datetime.now(UTC), max_attempts=2)
        ).fetch(request)
        calibration = ProviderCalibrationCoordinator(repository=store).run_snapshots(
            cninfo_calibration_snapshot(direct_batch, as_of=as_of),
            cninfo_calibration_snapshot(transported, as_of=as_of),
            fields=("symbol", "title", "published_at"),
            compared_at=as_of,
        )
        comparison = {
            "report_id": calibration.report.report_id,
            "matched_count": calibration.report.matched_count,
            "direct_count": calibration.report.primary_count,
            "akshare_transport_count": calibration.report.secondary_count,
            "consistency_score": calibration.report.consistency_score,
            "conflict_count": len(calibration.conflicts),
        }

    document = {
        "provider": direct_batch.provider,
        "dataset": direct_batch.dataset,
        "subject": args.symbol,
        "batch_id": result.batch_id,
        "received": result.received,
        "accepted": result.accepted,
        "captured_artifacts": len(direct_batch.artifacts),
        "artifact_observations": len(direct_batch.artifact_observations),
        "limitations": [item.code for item in direct_batch.limitations],
        "comparison": comparison,
    }
    rendered = json.dumps(document, indent=2, sort_keys=True)
    if args.output is None:
        print(rendered)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output_file:
        output_file.write(rendered + "\n")
    args.output.chmod(0o600)
    print(args.output)


if __name__ == "__main__":
    main()
