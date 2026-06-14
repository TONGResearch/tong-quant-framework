import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    name: str
    environment: str
    base_currency: str


@dataclass(frozen=True, slots=True)
class DataSettings:
    provider: str
    storage_root: Path
    database_path: Path
    cache_root: Path
    cache_ttl_seconds: int
    strict_point_in_time: bool
    default_adjustment: str


@dataclass(frozen=True, slots=True)
class MarketSettings:
    enabled: tuple[str, ...]
    default: str


@dataclass(frozen=True, slots=True)
class RiskSettings:
    max_position_weight: float
    max_sector_weight: float
    max_portfolio_drawdown: float
    risk_per_trade: float


@dataclass(frozen=True, slots=True)
class ExecutionSettings:
    mode: str
    allow_live_orders: bool
    require_manual_approval: bool
    broker: str


@dataclass(frozen=True, slots=True)
class ValidationSettings:
    minimum_observations: int
    require_out_of_sample: bool
    require_walk_forward: bool


@dataclass(frozen=True, slots=True)
class Settings:
    project: ProjectSettings
    data: DataSettings
    market: MarketSettings
    risk: RiskSettings
    execution: ExecutionSettings
    validation: ValidationSettings


def _validate_fraction(name: str, value: float) -> float:
    if not 0 < value <= 1:
        raise ValueError(f"{name} must be in the interval (0, 1]")
    return value


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as config_file:
        return tomllib.load(config_file)


def load_settings(path: Path, *overrides: Path) -> Settings:
    raw = _read_toml(path)
    for override in overrides:
        raw = _merge(raw, _read_toml(override))

    environment = os.getenv("TONG_QUANT_ENVIRONMENT")
    if environment:
        raw = _merge(raw, {"project": {"environment": environment}})

    settings = Settings(
        project=ProjectSettings(**raw["project"]),
        data=DataSettings(
            provider=raw["data"]["provider"],
            storage_root=Path(raw["data"]["storage_root"]),
            database_path=Path(raw["data"]["database_path"]),
            cache_root=Path(raw["data"]["cache_root"]),
            cache_ttl_seconds=raw["data"]["cache_ttl_seconds"],
            strict_point_in_time=raw["data"]["strict_point_in_time"],
            default_adjustment=raw["data"]["default_adjustment"],
        ),
        market=MarketSettings(
            enabled=tuple(raw["market"]["enabled"]),
            default=raw["market"]["default"],
        ),
        risk=RiskSettings(**raw["risk"]),
        execution=ExecutionSettings(**raw["execution"]),
        validation=ValidationSettings(**raw["validation"]),
    )

    _validate_fraction("max_position_weight", settings.risk.max_position_weight)
    _validate_fraction("max_sector_weight", settings.risk.max_sector_weight)
    _validate_fraction("max_portfolio_drawdown", settings.risk.max_portfolio_drawdown)
    _validate_fraction("risk_per_trade", settings.risk.risk_per_trade)
    if settings.market.default not in settings.market.enabled:
        raise ValueError("default market must be enabled")
    if settings.execution.allow_live_orders and settings.execution.mode in {"research", "paper"}:
        raise ValueError("research and paper modes cannot allow live orders")
    if settings.data.cache_ttl_seconds < 0:
        raise ValueError("cache_ttl_seconds cannot be negative")
    return settings
