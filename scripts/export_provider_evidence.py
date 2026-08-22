import argparse
import json
from datetime import datetime
from pathlib import Path

from tong_quant.data.evidence_bundle import (
    ProviderEvidenceBundleExporter,
    provider_evidence_bundle_json,
    render_provider_evidence_bundle_markdown,
    serialize_provider_evidence_bundle,
    verify_provider_evidence_document,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a credential-free provider operational evidence bundle"
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/provider-contract-monitor.sqlite3"),
    )
    parser.add_argument(
        "--as-of",
        type=_aware_datetime,
        help="Timezone-aware ISO timestamp that freezes the evidence boundary",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/provider-evidence"),
    )
    parser.add_argument(
        "--verify",
        type=Path,
        help="Verify an existing bundle instead of exporting a database",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verify is not None:
        _verify_path(args.verify)
        print(args.verify)
        return
    if args.as_of is None:
        raise SystemExit("--as-of is required when exporting a database")
    bundle = ProviderEvidenceBundleExporter().export(
        args.database,
        as_of=args.as_of,
    )
    document = provider_evidence_bundle_json(bundle)
    verify_provider_evidence_document(document)
    stem = f"provider-evidence-bundle-{bundle.bundle_id}"
    json_path = args.output_dir / f"{stem}.json"
    markdown_path = args.output_dir / f"{stem}.md"
    _write_idempotent(
        json_path,
        serialize_provider_evidence_bundle(bundle) + "\n",
    )
    _write_idempotent(
        markdown_path,
        render_provider_evidence_bundle_markdown(bundle),
    )
    print(markdown_path)
    print(json_path)


def _verify_path(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("provider evidence verification input must be a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("provider evidence verification input is malformed") from error
    if not isinstance(document, dict):
        raise ValueError("provider evidence verification input must be an object")
    verify_provider_evidence_document(document)


def _write_idempotent(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("provider evidence output must not be a symbolic link")
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError("provider evidence output identity collision")
        return
    with path.open("x", encoding="utf-8") as output:
        output.write(content)


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--as-of must include a UTC offset")
    return parsed


if __name__ == "__main__":
    main()
