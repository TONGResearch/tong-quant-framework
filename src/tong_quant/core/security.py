import re
from collections.abc import Mapping

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(token|api[_-]?key|access[_-]?token|bot[_-]?token|password|secret|"
    r"webhook[_-]?url)\s*[:=]\s*[^\s,;]+"
)
_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "bot_token",
    "password",
    "secret",
    "token",
    "webhook_url",
}


def redact_sensitive_text(value: str) -> str:
    return _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def contains_sensitive_assignment(value: str) -> bool:
    return _SENSITIVE_ASSIGNMENT.search(value) is not None


def reject_sensitive_persistence(values: Mapping[str, str]) -> None:
    for field, value in values.items():
        if contains_sensitive_assignment(value):
            raise ValueError(f"{field} contains credential-like data")


def reject_sensitive_structure(value: object, *, path: str = "value") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            field = str(key)
            normalized = field.strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_KEYS:
                raise ValueError(f"{path}.{field} is a credential-like field")
            reject_sensitive_structure(nested, path=f"{path}.{field}")
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for index, nested in enumerate(value):
            reject_sensitive_structure(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and contains_sensitive_assignment(value):
        raise ValueError(f"{path} contains credential-like data")


__all__ = [
    "contains_sensitive_assignment",
    "redact_sensitive_text",
    "reject_sensitive_persistence",
    "reject_sensitive_structure",
]
