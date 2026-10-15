from pathlib import Path

import pytest

from tong_quant.config.settings import load_settings
from tong_quant.portfolio import PortfolioEvidencePolicy


def test_default_configuration_is_safe() -> None:
    settings = load_settings(Path("config/default.toml"))

    assert settings.market.default == "china_a"
    assert settings.provider_calibration.enabled is False
    assert settings.provider_calibration.primary_provider == "akshare"
    assert settings.provider_calibration.secondary_provider == "tushare"
    assert settings.provider_calibration.fail_on_high_severity_conflict is True
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
    assert settings.portfolio_evidence.validation_configuration_hash == ""
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


def test_portfolio_evidence_policy_requires_reviewed_hash() -> None:
    settings = load_settings(Path("config/default.toml"))

    with pytest.raises(ValueError, match="has not been approved"):
        PortfolioEvidencePolicy.from_settings(settings)


def test_portfolio_evidence_policy_uses_effective_configuration(tmp_path: Path) -> None:
    override = tmp_path / "evidence.toml"
    override.write_text(
        '[portfolio_evidence]\nvalidation_configuration_hash = "' + "a" * 64 + '"\n'
        "maximum_proposal_age_seconds = 3600\n"
        '[portfolio]\nmodel_version = "portfolio-test-v2"\n'
        '[validation]\nmodel_version = "validation-test-v2"\n',
        encoding="utf-8",
    )
    settings = load_settings(Path("config/default.toml"), override)

    policy = PortfolioEvidencePolicy.from_settings(settings)

    assert policy.validation_configuration_hash == "a" * 64
    assert policy.maximum_proposal_age.total_seconds() == 3600
    assert policy.portfolio_model_version == "portfolio-test-v2"
    assert policy.validation_model_version == "validation-test-v2"
    assert policy.risk_model_version == "risk-assessment-v0.7"
    assert len(policy.policy_hash) == 64


@pytest.mark.parametrize(
    "override_text, expected_error",
    [
        ("maximum_risk_age_seconds = 0", "maximum ages must be positive"),
        ('validation_configuration_hash = "not-a-hash"', "must be SHA-256"),
    ],
)
def test_portfolio_evidence_configuration_rejects_invalid_policy(
    tmp_path: Path, override_text: str, expected_error: str
) -> None:
    override = tmp_path / "invalid.toml"
    override.write_text(f"[portfolio_evidence]\n{override_text}\n", encoding="utf-8")

    with pytest.raises(ValueError, match=expected_error):
        load_settings(Path("config/default.toml"), override)
