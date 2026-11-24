"""Export a self-contained academic workbench from explicitly dated retained inputs."""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Never

from tong_quant.application.academic_showcase import (
    academic_project_context,
    read_academic_snapshot,
    render_academic_showcase,
)
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid academic export arguments.\n")


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--market", choices=("us", "hong_kong", "malaysia"), required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-observation-age-seconds", type=int, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--junit-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.output.expanduser().resolve()
        database = args.database.expanduser().resolve()
        artifact_root = args.artifact_root.expanduser().resolve()
        if (output.suffix.lower() != ".html" or output == database
                or output.is_relative_to(artifact_root)):
            raise ValueError("output must be separate from retained sources")
        snapshot = read_academic_snapshot(SQLiteStore(database, read_only=True),
            FileSystemArtifactStore(artifact_root), args.symbol, Market(args.market),
            as_of=datetime.fromisoformat(args.as_of),
            maximum_age_seconds=args.max_observation_age_seconds)
        context = academic_project_context(args.project_root.expanduser().resolve(),
            args.junit_report.expanduser().resolve() if args.junit_report else None)
        content = render_academic_showcase(snapshot, context)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except (ValueError, TypeError, OSError, sqlite3.Error):
        parser.exit(2, "Academic export inputs could not be verified; no source was updated.\n")
    print("Academic read-only snapshot exported.")


if __name__ == "__main__":
    main()
