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
class RegimeModelSettings:
    bull_threshold: float
    bear_threshold: float
    transition_bull_threshold: float
    transition_bear_threshold: float
    transition_min_agreement: float
    model_version: str
    weights: dict[str, float]


@dataclass(frozen=True, slots=True)
class MarketRegimeSettings:
    enabled: bool
    china: RegimeModelSettings
    global_market: RegimeModelSettings


@dataclass(frozen=True, slots=True)
class ScoreModelSettings:
    model_version: str
    maximum_component_weight: float
    require_all_components: bool
    weights: dict[str, float]


@dataclass(frozen=True, slots=True)
class ResearchQueueSettings:
    research_weight: float
    urgency_weight: float
    confidence_weight: float


@dataclass(frozen=True, slots=True)
class ScreeningSettings:
    enabled: bool
    research_score: ScoreModelSettings
    research_queue: ResearchQueueSettings


@dataclass(frozen=True, slots=True)
class TechnicalResearchSettings:
    short_ma_period: int
    long_ma_period: int
    position_period: int


@dataclass(frozen=True, slots=True)
class TrendResearchSettings:
    breakout_period: int
    volume_period: int
    atr_period: int
    confirmation_threshold: float


@dataclass(frozen=True, slots=True)
class PatternResearchSettings:
    rising_stocks_threshold: int
    volume_period: int


@dataclass(frozen=True, slots=True)
class ResearchSettings:
    enabled: bool
    model_version: str
    investment_score: ScoreModelSettings
    technical: TechnicalResearchSettings
    trend: TrendResearchSettings
    pattern: PatternResearchSettings


@dataclass(frozen=True, slots=True)
class PortfolioSettings:
    enabled: bool
    model_version: str
    base_currency: str
    minimum_cash_weight: float
    maximum_single_position_weight: float
    target_volatility: float


@dataclass(frozen=True, slots=True)
class RiskSettings:
    max_position_weight: float
    max_sector_weight: float
    max_portfolio_drawdown: float
    risk_per_trade: float
    total_risk_budget: float
    per_position_risk_budget: float
    per_sector_risk_budget: float
    per_theme_risk_budget: float
    maximum_country_weight: float
    maximum_theme_weight: float
    minimum_liquidity_score: float
    maximum_average_correlation: float
    stress_loss_limit: float


@dataclass(frozen=True, slots=True)
class ExecutionSettings:
    mode: str
    allow_live_orders: bool
    require_manual_approval: bool
    broker: str


@dataclass(frozen=True, slots=True)
class NotificationSettings:
    mode: str
    max_attempts: int
    batch_size: int
    lease_timeout_seconds: int
    retry_delay_seconds: int


@dataclass(frozen=True, slots=True)
class ValidationSplitSettings:
    training_days: int
    validation_days: int
    step_days: int
    embargo_days: int


@dataclass(frozen=True, slots=True)
class ValidationRobustnessSettings:
    minimum_windows: int
    maximum_missing_rate: float


@dataclass(frozen=True, slots=True)
class ValidationPortfolioSettings:
    maximum_category_weight: float
    maximum_hhi: float


@dataclass(frozen=True, slots=True)
class ValidationSettings:
    enabled: bool
    model_version: str
    minimum_observations: int
    require_out_of_sample: bool
    require_walk_forward: bool
    fail_on_integrity_error: bool
    splits: ValidationSplitSettings
    robustness: ValidationRobustnessSettings
    portfolio: ValidationPortfolioSettings


@dataclass(frozen=True, slots=True)
class Settings:
    project: ProjectSettings
    data: DataSettings
    market: MarketSettings
    market_regime: MarketRegimeSettings
    screening: ScreeningSettings
    research: ResearchSettings
    portfolio: PortfolioSettings
    risk: RiskSettings
    notifications: NotificationSettings
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

    investment_score_raw = raw["research"].get("investment_score")
    if investment_score_raw is None:
        investment_score_raw = raw["screening"].get("investment_score")
    if investment_score_raw is None:
        raise ValueError("research investment_score configuration is required")

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
        market_regime=MarketRegimeSettings(
            enabled=raw["market_regime"]["enabled"],
            china=RegimeModelSettings(**raw["market_regime"]["china"]),
            global_market=RegimeModelSettings(**raw["market_regime"]["global"]),
        ),
        screening=ScreeningSettings(
            enabled=raw["screening"]["enabled"],
            research_score=ScoreModelSettings(**raw["screening"]["research_score"]),
            research_queue=ResearchQueueSettings(**raw["screening"]["research_queue"]),
        ),
        research=ResearchSettings(
            enabled=raw["research"]["enabled"],
            model_version=raw["research"]["model_version"],
            investment_score=ScoreModelSettings(**investment_score_raw),
            technical=TechnicalResearchSettings(**raw["research"]["technical"]),
            trend=TrendResearchSettings(**raw["research"]["trend"]),
            pattern=PatternResearchSettings(**raw["research"]["pattern"]),
        ),
        portfolio=PortfolioSettings(**raw["portfolio"]),
        risk=RiskSettings(**raw["risk"]),
        notifications=NotificationSettings(**raw["notifications"]),
        execution=ExecutionSettings(**raw["execution"]),
        validation=ValidationSettings(
            enabled=raw["validation"]["enabled"],
            model_version=raw["validation"]["model_version"],
            minimum_observations=raw["validation"]["minimum_observations"],
            require_out_of_sample=raw["validation"]["require_out_of_sample"],
            require_walk_forward=raw["validation"]["require_walk_forward"],
            fail_on_integrity_error=raw["validation"]["fail_on_integrity_error"],
            splits=ValidationSplitSettings(**raw["validation"]["splits"]),
            robustness=ValidationRobustnessSettings(
                **raw["validation"]["robustness"]
            ),
            portfolio=ValidationPortfolioSettings(
                **raw["validation"]["portfolio"]
            ),
        ),
    )

    _validate_fraction("max_position_weight", settings.risk.max_position_weight)
    _validate_fraction("max_sector_weight", settings.risk.max_sector_weight)
    _validate_fraction("max_portfolio_drawdown", settings.risk.max_portfolio_drawdown)
    _validate_fraction("risk_per_trade", settings.risk.risk_per_trade)
    _validate_fraction("minimum_cash_weight", settings.portfolio.minimum_cash_weight)
    _validate_fraction(
        "portfolio maximum_single_position_weight",
        settings.portfolio.maximum_single_position_weight,
    )
    _validate_fraction("portfolio target_volatility", settings.portfolio.target_volatility)
    _validate_fraction("total_risk_budget", settings.risk.total_risk_budget)
    _validate_fraction("per_position_risk_budget", settings.risk.per_position_risk_budget)
    _validate_fraction("per_sector_risk_budget", settings.risk.per_sector_risk_budget)
    _validate_fraction("per_theme_risk_budget", settings.risk.per_theme_risk_budget)
    _validate_fraction("maximum_country_weight", settings.risk.maximum_country_weight)
    _validate_fraction("maximum_theme_weight", settings.risk.maximum_theme_weight)
    _validate_fraction("maximum_average_correlation", settings.risk.maximum_average_correlation)
    _validate_fraction("stress_loss_limit", settings.risk.stress_loss_limit)
    if not 0 <= settings.risk.minimum_liquidity_score <= 100:
        raise ValueError("minimum_liquidity_score must be between 0 and 100")
    if settings.market.default not in settings.market.enabled:
        raise ValueError("default market must be enabled")
    execution_modes = {"disabled", "research", "paper", "semi_automatic", "automatic"}
    if settings.execution.mode not in execution_modes:
        raise ValueError("execution mode is unsupported")
    if settings.execution.allow_live_orders and settings.execution.mode in {
        "disabled",
        "research",
        "paper",
    }:
        raise ValueError("disabled, research, and paper modes cannot allow live orders")
    notification_modes = {"disabled", "preview", "enabled"}
    if settings.notifications.mode not in notification_modes:
        raise ValueError("notification mode is unsupported")
    if settings.notifications.max_attempts <= 0:
        raise ValueError("notification max_attempts must be positive")
    if settings.notifications.batch_size <= 0:
        raise ValueError("notification batch_size must be positive")
    if settings.notifications.lease_timeout_seconds <= 0:
        raise ValueError("notification lease_timeout_seconds must be positive")
    if settings.notifications.retry_delay_seconds <= 0:
        raise ValueError("notification retry_delay_seconds must be positive")
    if settings.data.cache_ttl_seconds < 0:
        raise ValueError("cache_ttl_seconds cannot be negative")
    for regime_model in (
        settings.market_regime.china,
        settings.market_regime.global_market,
    ):
        if not regime_model.weights:
            raise ValueError("market regime weights cannot be empty")
    for score_model in (settings.screening.research_score,):
        if not score_model.weights:
            raise ValueError("screening score weights cannot be empty")
        if not 0 < score_model.maximum_component_weight < 1:
            raise ValueError("maximum_component_weight must be between zero and one")
        total = sum(score_model.weights.values())
        if total <= 0 or any(weight <= 0 for weight in score_model.weights.values()):
            raise ValueError("screening score weights must be positive")
        if max(weight / total for weight in score_model.weights.values()) > (
            score_model.maximum_component_weight
        ):
            raise ValueError("a screening score component exceeds the maximum weight")
    score_model = settings.research.investment_score
    if not score_model.weights:
        raise ValueError("investment score weights cannot be empty")
    if not 0 < score_model.maximum_component_weight < 1:
        raise ValueError("maximum_component_weight must be between zero and one")
    total = sum(score_model.weights.values())
    if total <= 0 or any(weight <= 0 for weight in score_model.weights.values()):
        raise ValueError("investment score weights must be positive")
    if max(weight / total for weight in score_model.weights.values()) > (
        score_model.maximum_component_weight
    ):
        raise ValueError("an investment score component exceeds the maximum weight")
    queue_weights = (
        settings.screening.research_queue.research_weight,
        settings.screening.research_queue.urgency_weight,
        settings.screening.research_queue.confidence_weight,
    )
    if any(weight < 0 for weight in queue_weights) or abs(sum(queue_weights) - 1) > 1e-9:
        raise ValueError("research queue weights must be non-negative and sum to one")
    research_periods = (
        settings.research.technical.short_ma_period,
        settings.research.technical.long_ma_period,
        settings.research.technical.position_period,
        settings.research.trend.breakout_period,
        settings.research.trend.volume_period,
        settings.research.trend.atr_period,
        settings.research.pattern.volume_period,
    )
    if any(period <= 0 for period in research_periods):
        raise ValueError("research lookback periods must be positive")
    if not 0 <= settings.research.trend.confirmation_threshold <= 100:
        raise ValueError("trend confirmation threshold must be between 0 and 100")
    if settings.research.pattern.rising_stocks_threshold <= 0:
        raise ValueError("rising-stocks threshold must be positive")
    if settings.validation.minimum_observations <= 0:
        raise ValueError("validation minimum_observations must be positive")
    validation_periods = (
        settings.validation.splits.training_days,
        settings.validation.splits.validation_days,
        settings.validation.splits.step_days,
    )
    if any(period <= 0 for period in validation_periods):
        raise ValueError("validation split periods must be positive")
    if settings.validation.splits.embargo_days < 0:
        raise ValueError("validation embargo cannot be negative")
    if settings.validation.robustness.minimum_windows <= 0:
        raise ValueError("validation minimum_windows must be positive")
    for name, value in (
        (
            "maximum_missing_rate",
            settings.validation.robustness.maximum_missing_rate,
        ),
        (
            "maximum_category_weight",
            settings.validation.portfolio.maximum_category_weight,
        ),
        ("maximum_hhi", settings.validation.portfolio.maximum_hhi),
    ):
        _validate_fraction(name, value)
    return settings
