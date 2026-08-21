import argparse
import json
from pathlib import Path

from tong_quant.governance import audit_project_governance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Tong Quant versions, safety defaults, and work-package state"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_project_governance(args.project_root.resolve())
    if args.json:
        print(
            json.dumps(
                {
                    "consistent": report.is_consistent,
                    "checks": [
                        {
                            "name": check.name,
                            "passed": check.passed,
                            "detail": check.detail,
                        }
                        for check in report.checks
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for check in report.checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
    if not report.is_consistent:
        raise SystemExit("Tong Quant governance audit failed")


if __name__ == "__main__":
    main()
