import argparse
import json
from pathlib import Path

from tong_quant import __version__
from tong_quant.config.settings import load_settings
from tong_quant.markets.registry import build_market_rules


def main() -> None:
    parser = argparse.ArgumentParser(description="Tong Quant research operations")
    parser.add_argument("command", choices=("status", "preflight"), nargs="?", default="status")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--config-override", type=Path, action="append", default=[])
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    if args.command == "preflight":
        if args.project_root is None:
            parser.error("preflight requires an explicit --project-root")
        from tong_quant.application.deployment_preflight import run_deployment_preflight

        report = run_deployment_preflight(
            args.project_root, config_path=args.config,
            overrides=args.config_override, database=args.database,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(0 if report["offline_preflight_passed"] else 2)
    if args.database is not None:
        parser.error("--database is supported only for preflight")
    root = args.project_root or Path.cwd()
    config = args.config or Path("config/default.toml")
    if not config.is_absolute():
        config = root / config
    overrides = [path if path.is_absolute() else root / path for path in args.config_override]
    try:
        settings = load_settings(config, *overrides)
    except (OSError, ValueError, TypeError, KeyError):
        raise SystemExit(
            "Configuration unavailable or invalid; provide an explicit --config"
        ) from None
    rules = build_market_rules(settings.market.default)
    print(f"{settings.project.name} v{__version__}")
    print(f"Environment: {settings.project.environment}")
    print(f"Default market: {rules.market.value}")
    print(f"Notification mode: {settings.notifications.mode}")
    print(f"Execution mode: {settings.execution.mode}")


if __name__ == "__main__":
    main()
