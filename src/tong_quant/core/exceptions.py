class TongQuantError(Exception):
    """Base exception for expected framework errors."""


class ConfigurationError(TongQuantError):
    """Raised when configuration is unsafe or inconsistent."""


class FutureDataError(TongQuantError):
    """Raised when a decision attempts to use unavailable future data."""


class MarketRuleEvidenceUnavailableError(TongQuantError):
    """Raised when market-rule evidence cannot support a trading calculation."""


class LayerViolationError(TongQuantError):
    """Raised when a module crosses an architecture boundary."""


class ExecutionDisabledError(TongQuantError):
    """Raised when an execution entry point is not explicitly enabled."""


class DataProviderError(TongQuantError):
    """Raised when an external data provider remains unavailable after retries."""


class DataProviderUnavailableError(DataProviderError):
    """Raised with a sanitized reason when provider access is unavailable."""

    def __init__(self, provider: str, reason_code: str) -> None:
        super().__init__(f"{provider} unavailable ({reason_code})")
        self.provider = provider
        self.reason_code = reason_code


class DatabaseIntegrityError(TongQuantError):
    """Raised when database audit, backup, or restore cannot complete safely."""
