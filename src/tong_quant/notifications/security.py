from tong_quant.core.security import (
    contains_sensitive_assignment,
    redact_sensitive_text,
)


def safe_error_code(error: Exception) -> str:
    return type(error).__name__


__all__ = ["contains_sensitive_assignment", "redact_sensitive_text", "safe_error_code"]
