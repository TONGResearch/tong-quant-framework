import hashlib
import json
from collections.abc import Mapping
from datetime import datetime

from tong_quant.validation.models import FrameworkSnapshot, ValidationValue


def stable_configuration_hash(configuration: Mapping[str, ValidationValue]) -> str:
    payload = json.dumps(configuration, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def framework_snapshot(
    *,
    git_commit: str,
    framework_version: str,
    configuration: Mapping[str, ValidationValue],
    research_version: str,
    validation_version: str,
    database_schema_version: str,
    captured_at: datetime,
) -> FrameworkSnapshot:
    return FrameworkSnapshot(
        git_commit=git_commit,
        framework_version=framework_version,
        configuration_hash=stable_configuration_hash(configuration),
        research_version=research_version,
        validation_version=validation_version,
        database_schema_version=database_schema_version,
        captured_at=captured_at,
    )


__all__ = ["framework_snapshot", "stable_configuration_hash"]
