import argparse
import json
from pathlib import Path

from tong_quant.data.evidence_horizon import (
    EvidenceHorizonPolicy,
    evaluate_provider_evidence_horizon,
    render_provider_evidence_horizon_markdown,
    required_provider_evidence_scopes,
    serialize_provider_evidence_horizon,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the per-scope provider evidence horizon without promotion"
    )
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/provider-evidence-horizon"),
    )
    parser.add_argument("--china-symbol", default="600000")
    parser.add_argument("--us-symbol", default="MSFT")
    parser.add_argument("--hong-kong-symbol", default="0700.HK")
    parser.add_argument("--malaysia-symbol", default="1155.KL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = _read_bundle(args.bundle)
    policy = EvidenceHorizonPolicy(
        required_scopes=required_provider_evidence_scopes(
            china_symbol=args.china_symbol,
            us_symbol=args.us_symbol,
            hong_kong_symbol=args.hong_kong_symbol,
            malaysia_symbol=args.malaysia_symbol,
        )
    )
    report = evaluate_provider_evidence_horizon(document, policy=policy)
    stem = f"provider-evidence-horizon-{report.report_id}"
    json_path = args.output_dir / f"{stem}.json"
    markdown_path = args.output_dir / f"{stem}.md"
    _write_idempotent(json_path, serialize_provider_evidence_horizon(report) + "\n")
    _write_idempotent(
        markdown_path,
        render_provider_evidence_horizon_markdown(report),
    )
    print(markdown_path)
    print(json_path)


def _read_bundle(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("provider evidence horizon input must be a regular file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("provider evidence horizon input is malformed") from error
    if not isinstance(document, dict):
        raise ValueError("provider evidence horizon input must be an object")
    return document


def _write_idempotent(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("provider evidence horizon output must not be a symbolic link")
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError("provider evidence horizon output identity collision")
        return
    with path.open("x", encoding="utf-8") as output:
        output.write(content)


if __name__ == "__main__":
    main()
