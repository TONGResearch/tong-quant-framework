from pathlib import Path

from tong_quant.config.settings import load_settings


def test_default_configuration_is_safe() -> None:
    settings = load_settings(Path("config/default.toml"))

    assert settings.market.default == "china_a"
    assert settings.execution.mode == "paper"
    assert settings.execution.allow_live_orders is False
    assert settings.execution.broker == "paper"
    assert settings.market_regime.china.weights["csi_300_trend"] == 0.25
    assert settings.market_regime.china.transition_bull_threshold == 12.0


def test_research_override_preserves_default_values() -> None:
    settings = load_settings(
        Path("config/default.toml"),
        Path("config/research.toml"),
    )

    assert settings.project.environment == "research"
    assert settings.data.provider == "akshare"
    assert settings.execution.mode == "research"
