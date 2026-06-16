from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.markets.registry import build_market_rules


def main() -> None:
    settings = load_settings(Path("config/default.toml"))
    rules = build_market_rules(settings.market.default)
    print(f"{settings.project.name} v0.6.3")
    print(f"Environment: {settings.project.environment}")
    print(f"Default market: {rules.market.value}")
    print(f"Execution mode: {settings.execution.mode}")


if __name__ == "__main__":
    main()
