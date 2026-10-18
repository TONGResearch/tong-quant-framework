"""Print a bounded, read-only registry-to-file integrity report."""

import argparse
import json
from pathlib import Path

from tong_quant.data.storage.artifact_audit import audit_provider_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    report = audit_provider_artifacts(args.database, args.artifact_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["registered_artifacts_verified"] else 2)


if __name__ == "__main__":
    main()
