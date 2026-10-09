import argparse
from datetime import datetime
from pathlib import Path

from tong_quant.data.evidence_archive import (
    archive_provider_evidence_artifact,
    verify_provider_evidence_archive,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive and independently verify provider evidence artifacts"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    archive = subcommands.add_parser("archive")
    archive.add_argument("--artifact", type=Path, required=True)
    archive.add_argument("--destination", type=Path, required=True)
    archive.add_argument("--verified-at", type=_aware_datetime, required=True)
    archive.add_argument("--expected-sha256")

    verify = subcommands.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "verify":
        manifest = verify_provider_evidence_archive(args.manifest)
        print(manifest.archive_id)
        return
    result = archive_provider_evidence_artifact(
        args.artifact,
        args.destination,
        verified_at=args.verified_at,
        expected_sha256=args.expected_sha256,
    )
    print(result.artifact_path)
    print(result.manifest_path)


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--verified-at must include a UTC offset")
    return parsed


if __name__ == "__main__":
    main()
