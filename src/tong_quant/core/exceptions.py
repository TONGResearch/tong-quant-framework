class TongQuantError(Exception):
    """Base exception for expected framework errors."""


class ConfigurationError(TongQuantError):
    """Raised when configuration is unsafe or inconsistent."""


class FutureDataError(TongQuantError):
    """Raised when a decision attempts to use unavailable future data."""


class LayerViolationError(TongQuantError):
    """Raised when a module crosses an architecture boundary."""


class DataProviderError(TongQuantError):
    """Raised when an external data provider remains unavailable after retries."""
