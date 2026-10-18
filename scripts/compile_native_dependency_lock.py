"""Convert a pip JSON resolution report into one platform-scoped, hashed lock."""

import argparse
import json
import re
import tomllib
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

from tong_quant.application.dependency_lock import (
    dependency_specification_hash,
    render_native_lock,
)
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.version import DEPENDENCY_LOCK_VERSION, FRAMEWORK_VERSION


def compile_report(root: Path, report: dict[str, Any], profile: str) -> tuple[str, dict[str, Any]]:
    environment = report["environment"]
    if (
        report["version"] != "1" or environment["platform_system"] != "Darwin"
        or environment["platform_machine"] != "arm64" or environment["python_version"] != "3.12"
        or environment["implementation_name"] != "cpython"
    ):
        raise ValueError("unsupported resolver report target")
    with (root / "pyproject.toml").open("rb") as source:
        project = tomllib.load(source)["project"]
    root_name = canonicalize_name(project["name"])
    if root_name != "tong-quant-framework" or project["version"] != FRAMEWORK_VERSION:
        raise ValueError("project identity does not match framework")
    root_items = [
        item for item in report["install"]
        if canonicalize_name(item["metadata"]["name"]) == root_name
    ]
    if len(root_items) != 1 or root_items[0]["metadata"]["version"] != FRAMEWORK_VERSION:
        raise ValueError("resolver root identity mismatch")
    extra = "dev" if profile == "dev" else ""
    selected = set()
    for value in root_items[0]["metadata"].get("requires_dist", []):
        requirement = Requirement(value)
        if requirement.marker is None or requirement.marker.evaluate(
            {**environment, "extra": extra}
        ):
            requirement.marker = None
            selected.add(str(requirement))
    expected = [*project["dependencies"]]
    if profile == "dev":
        expected.extend(project["optional-dependencies"]["dev"])
    if selected != {str(Requirement(value)) for value in expected}:
        raise ValueError("resolver root dependencies do not match the project")
    resolved = {
        canonicalize_name(item["metadata"]["name"]): Version(item["metadata"]["version"])
        for item in report["install"]
    }
    for value in selected:
        requirement = Requirement(value)
        name = canonicalize_name(requirement.name)
        if name not in resolved or resolved[name] not in requirement.specifier:
            raise ValueError("resolver report omits a required root dependency")
    packages = []
    minimum = (0, 0)
    compatible_tags = set(sys_tags())
    for item in report["install"]:
        metadata = item["metadata"]
        name = canonicalize_name(metadata["name"])
        if name == root_name:
            continue
        download = item["download_info"]
        url = urlsplit(download["url"])
        if (
            url.scheme != "https" or url.hostname != "files.pythonhosted.org"
            or url.username is not None or url.password is not None or url.query or url.fragment
            or item.get("is_yanked", False)
        ):
            raise ValueError("unsupported or yanked dependency source")
        filename = Path(unquote(url.path)).name
        version = str(Version(metadata["version"]))
        kind = "wheel" if filename.endswith(".whl") else "sdist"
        if kind == "wheel":
            wheel_name, wheel_version, _, tags = parse_wheel_filename(filename)
            if wheel_name != name or str(wheel_version) != version:
                raise ValueError("wheel identity does not match package metadata")
            if not tags.intersection(compatible_tags):
                raise ValueError("wheel is not compatible with the native interpreter")
            floors = []
            for tag in tags:
                match = re.fullmatch(r"macosx_(\d+)_(\d+)_(?:arm64|universal2)", tag.platform)
                if match:
                    floors.append((int(match[1]), int(match[2])))
            if floors:
                minimum = max(minimum, min(floors))
        elif name != "jsonpath" or version != "0.82.2" or filename != "jsonpath-0.82.2.tar.gz":
            raise ValueError("source build needs a separate dependency review")
        packages.append({
            "name": str(name), "version": version,
            "sha256": download["archive_info"]["hashes"]["sha256"], "kind": kind,
        })
    target = {"system": "Darwin", "machine": "arm64", "python": "3.12",
              "minimum_macos": list(minimum)}
    lock = render_native_lock(packages, profile, target)
    manifest = {
        "model_version": DEPENDENCY_LOCK_VERSION, "profile": profile,
        "framework_version": FRAMEWORK_VERSION, "target": target,
        "dependency_specification_hash": dependency_specification_hash(root, profile),
        "build_lock_sha256": sha256(
            (root / "requirements/build-py312.lock").read_bytes()
        ).hexdigest(),
        "build_input_sha256": sha256((root / "requirements/build.in").read_bytes()).hexdigest(),
        "lock_sha256": sha256(lock.encode()).hexdigest(),
        "packages": sorted(packages, key=lambda item: item["name"]),
    }
    reject_sensitive_structure(manifest)
    return lock, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile one native pip resolution report")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--profile", choices=("runtime", "dev"), required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    created = []
    try:
        root = args.project_root.expanduser().resolve()
        lock, manifest = compile_report(root, json.loads(args.report.read_text()), args.profile)
        output = args.output_dir or root / "requirements"
        output.mkdir(parents=True, exist_ok=True)
        prefix = output / f"{args.profile}-macos-arm64-py312"
        outputs = ((prefix.with_suffix(".lock"), lock),
                   (prefix.with_suffix(".manifest.json"), json.dumps(manifest, indent=2) + "\n"))
        for path, content in outputs:
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
        print(f"Compiled {len(manifest['packages'])} pinned dependencies for {args.profile}")
    except (OSError, ValueError, TypeError, KeyError) as error:
        for path in created:
            path.unlink(missing_ok=True)
        raise SystemExit(f"Lock compilation failed closed: {type(error).__name__}") from None


if __name__ == "__main__":
    main()
