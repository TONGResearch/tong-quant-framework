import re

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|bot[_-]?token|password|secret)"
    r"\s*[:=]\s*[^\s,;]+"
)


def redact_sensitive_text(value: str) -> str:
    return _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def contains_sensitive_assignment(value: str) -> bool:
    return _SENSITIVE_ASSIGNMENT.search(value) is not None


def safe_error_code(error: Exception) -> str:
    return type(error).__name__


__all__ = ["contains_sensitive_assignment", "redact_sensitive_text", "safe_error_code"]
