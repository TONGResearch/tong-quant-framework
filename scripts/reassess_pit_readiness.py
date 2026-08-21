import argparse
import subprocess
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from tong_quant.data.evidence_readiness import (
    EvidenceReadinessEvaluator,
    render_evidence_readiness_markdown,
    serialize_evidence_readiness,
)
from tong_quant.data.evidence_sources import (
    EvidenceSourcePaths,
    load_evidence_sources,
)
from tong_quant.data.storage.migrations import MIGRATION_HEAD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reassess PIT readiness from immutable evidence without promotion"
    )
    parser.add_argument(
        "--as-of",
        type=_aware_datetime,
        required=True,
        help="Timezone-aware ISO timestamp used for deterministic freshness checks",
    )
    parser.add_argument("--git-commit")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--readiness-dashboard",
        type=Path,
        default=Path("docs/generated/phase3/framework-data-readiness.json"),
    )
    parser.add_argument(
        "--readiness-gap",
        type=Path,
        default=Path("docs/generated/phase3/pit-readiness-gap-report.json"),
    )
    parser.add_argument(
        "--quality-audit",
        type=Path,
        default=Path("docs/generated/phase3/akshare-data-quality.json"),
    )
    parser.add_argument(
        "--provider-capabilities",
        type=Path,
        default=Path("docs/generated/phase3/tushare-provider-capabilities.json"),
    )
    parser.add_argument(
        "--contract-database",
        type=Path,
        default=Path("data/provider-contract-monitor.sqlite3"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/evidence-readiness"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    git_commit = args.git_commit or _git_commit(root)
    source_paths = EvidenceSourcePaths(
        readiness_dashboard=_resolve(root, args.readiness_dashboard),
        readiness_gap=_resolve(root, args.readiness_gap),
        quality_audit=_resolve(root, args.quality_audit),
        provider_capabilities=_resolve(root, args.provider_capabilities),
        operational_database=_resolve(root, args.contract_database),
        supporting_documents=(
            root / "docs/cninfo-direct-artifacts.md",
            root / "docs/yahoo-daily-bar-calibration.md",
            root / "docs/provider-monitor-operations.md",
        ),
    )
    loaded = load_evidence_sources(source_paths, assessed_at=args.as_of)
    report = EvidenceReadinessEvaluator().evaluate(
        assessed_at=args.as_of,
        git_commit=git_commit,
        configuration_hash=_file_hash(root / "config/project-governance.toml"),
        source_tree_hash=_source_tree_hash(root),
        migration_head=MIGRATION_HEAD,
        artifacts=loaded.artifacts,
        inputs=loaded.inputs,
    )
    output_dir = _resolve(root, args.output_dir)
    stem = f"pit-readiness-evidence-{report.report_id}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    _write_idempotent(json_path, serialize_evidence_readiness(report) + "\n")
    _write_idempotent(
        markdown_path,
        render_evidence_readiness_markdown(report),
    )
    print(markdown_path)
    print(json_path)


def _source_tree_hash(root: Path) -> str:
    paths = (
        root / "src/tong_quant/data/evidence_readiness.py",
        root / "src/tong_quant/data/evidence_sources.py",
        root / "src/tong_quant/data/storage/migrations.py",
        root / "src/tong_quant/version.py",
    )
    digest = sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _file_hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"hash input must be a regular file: {path}")
    return sha256(path.read_bytes()).hexdigest()


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if len(commit) != 40:
        raise ValueError("Git commit must be a full SHA-1 identity")
    return commit


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _write_idempotent(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("evidence readiness output must not be a symbolic link")
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError("evidence readiness output identity collision")
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
