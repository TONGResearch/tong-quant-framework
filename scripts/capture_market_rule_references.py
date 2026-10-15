import argparse
from datetime import UTC, datetime
from pathlib import Path

from tong_quant.application.market_rule_references import (
    capture_sse_references,
    load_sse_references,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture and verify pinned official SSE rule sources"
    )
    parser.add_argument(
        "--profile", type=Path, default=Path("config/markets/sse-main-board-2026.toml")
    )
    parser.add_argument(
        "--artifact-root", type=Path, default=Path("data/raw/market-rule-references")
    )
    parser.add_argument(
        "--capture-dir", type=Path, default=Path("data/processed/market-rule-references")
    )
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    capture = capture_sse_references(
        args.profile,
        artifact_root=args.artifact_root,
        capture_dir=args.capture_dir,
        captured_at=datetime.now(UTC),
        source_dir=args.source_dir,
    )
    references = load_sse_references(
        args.profile,
        artifact_root=args.artifact_root,
        capture_path=capture,
    )
    print(capture)
    print(f"reference_hash={references.reference_hash}")
    print("Reference documents verified; market inputs and simulation eligibility remain separate")


if __name__ == "__main__":
    main()
