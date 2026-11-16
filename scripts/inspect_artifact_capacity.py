"""Read-only explicit-budget artifact capacity preflight; never collect or delete."""

import argparse
import json
from pathlib import Path
from typing import Never

from tong_quant.data.artifact_capacity import ArtifactCapacityPolicy, inspect_artifact_capacity


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid read-only capacity arguments; no state changed.\n")


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--maximum-artifact-bytes", required=True, type=int)
    parser.add_argument("--maximum-retained-bytes", required=True, type=int)
    parser.add_argument("--minimum-free-bytes", required=True, type=int)
    parser.add_argument("--staging-headroom-bytes", required=True, type=int)
    parser.add_argument("--planned-artifact-bytes", required=True, type=int)
    parser.add_argument("--maximum-scan-entries", type=int, default=10_000)
    parser.add_argument("--maximum-depth", type=int, default=16)
    args = parser.parse_args()
    try:
        policy = ArtifactCapacityPolicy(
            args.maximum_artifact_bytes, args.maximum_retained_bytes,
            args.minimum_free_bytes, args.staging_headroom_bytes,
            args.maximum_scan_entries, args.maximum_depth,
        )
        report = inspect_artifact_capacity(
            args.artifact_root, policy=policy, planned_artifact_bytes=args.planned_artifact_bytes,
        )
    except (ValueError, TypeError):
        parser.exit(2, "Invalid read-only capacity input; no state changed.\n")
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    raise SystemExit(0 if report["status"] == "WITHIN_DECLARED_LIMITS" else 1)


if __name__ == "__main__":
    main()
