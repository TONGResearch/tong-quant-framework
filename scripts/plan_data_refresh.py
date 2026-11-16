"""Print an offline explicit-watchlist refresh plan; never collect or schedule data."""

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Never

from tong_quant.data.refresh_plan import (
    MAX_CONFIG_BYTES,
    build_refresh_plan,
    parse_refresh_watchlist,
)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "Invalid offline refresh arguments; no data collected.\n")


def _git_identity(root: Path) -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
        timeout=5, check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all"],
        cwd=root, capture_output=True, timeout=5, check=True,
    ).stdout
    return revision, bool(status)


def main() -> None:
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--watchlist", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        path = args.watchlist
        if path.is_symlink() or not path.is_file():
            raise ValueError("watchlist must be an existing regular file")
        with path.open("rb") as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise ValueError("watchlist exceeds byte bound")
        if not re.fullmatch(r"[0-9TtZz:+.\-]{20,40}", args.as_of):
            raise ValueError("explicit ISO timestamp is required")
        watchlist = parse_refresh_watchlist(raw.decode("utf-8"))
        revision, dirty = _git_identity(Path(__file__).resolve().parents[1])
        plan = build_refresh_plan(watchlist, planned_as_of=datetime.fromisoformat(args.as_of),
                                  git_commit=revision, git_dirty=dirty)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        parser.exit(2, "Invalid offline refresh input or unavailable Git identity; "
                    "no data collected.\n")
    print(json.dumps(plan, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
