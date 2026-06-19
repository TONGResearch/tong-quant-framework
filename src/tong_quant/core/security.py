import re
from collections.abc import Mapping

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(token|api[_-]?key|access[_-]?token|bot[_-]?token|password|secret|"
    r"webhook[_-]?url)\s*[:=]\s*[^\s,;]+"
)


def redact_sensitive_text(value: str) -> str:
    return _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def contains_sensitive_assignment(value: str) -> bool:
    return _SENSITIVE_ASSIGNMENT.search(value) is not None


def reject_sensitive_persistence(values: Mapping[str, str]) -> None:
    for field, value in values.items():
        if contains_sensitive_assignment(value):
            raise ValueError(f"{field} contains credential-like data")


__all__ = [
    "contains_sensitive_assignment",
    "redact_sensitive_text",
    "reject_sensitive_persistence",
]
