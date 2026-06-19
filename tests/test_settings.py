from pathlib import Path

from tong_quant.config.settings import load_settings


def test_default_configuration_is_safe() -> None:
    settings = load_settings(Path("config/default.toml"))

    assert settings.market.default == "china_a"
    assert settings.execution.mode == "disabled"
    assert settings.execution.allow_live_orders is False
    assert settings.execution.broker == "paper"
    assert settings.market_regime.china.weights["csi_300_trend"] == 0.25
    assert settings.market_regime.china.transition_bull_threshold == 12.0
    assert settings.screening.enabled is True
    assert settings.screening.research_score.weights["industry"] == 0.20
    assert settings.screening.research_queue.urgency_weight == 0.25
    assert settings.research.enabled is True
    assert settings.research.investment_score.weights["market_regime"] == 0.25
    assert settings.research.trend.atr_period == 14
    assert settings.research.pattern.rising_stocks_threshold == 3000
    assert settings.portfolio.enabled is True
    assert settings.portfolio.minimum_cash_weight == 0.05
    assert settings.risk.total_risk_budget == 0.12
    assert settings.risk.per_theme_risk_budget == 0.05
    assert settings.risk.minimum_liquidity_score == 60.0
    assert settings.notifications.mode == "disabled"
    assert settings.notifications.max_attempts == 3
    assert settings.notifications.batch_size == 100
    assert settings.notifications.lease_timeout_seconds == 300
    assert settings.notifications.retry_delay_seconds == 300
    assert settings.validation.enabled is True
    assert settings.validation.splits.embargo_days == 20
    assert settings.validation.portfolio.maximum_category_weight == 0.35


def test_research_override_preserves_default_values() -> None:
    settings = load_settings(
        Path("config/default.toml"),
        Path("config/research.toml"),
    )

    assert settings.project.environment == "research"
    assert settings.data.provider == "akshare"
    assert settings.notifications.mode == "disabled"
    assert settings.execution.mode == "research"
