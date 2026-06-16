import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any


def stable_hash(value: object) -> str:
    encoded = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _canonical(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def stable_json(value: object) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
    canonical = _canonical(value)
    if not isinstance(canonical, (dict, list, str, int, float, bool)) and canonical is not None:
        raise TypeError("value is not JSON serializable")
    return canonical


__all__ = ["stable_hash", "stable_json"]
