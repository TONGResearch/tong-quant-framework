"""Read-only technical diagnostics on existing SQLite bars; never a trading approval."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tong_quant.config.settings import load_settings
from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, Market
from tong_quant.domain.models import require_timezone
from tong_quant.research.config import research_engine_from_settings
from tong_quant.research.technical import TechnicalResearchModule
from tong_quant.research.technical.diagnostics import technical_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().parents[1] / "config/default.toml")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--market", choices=[item.value for item in Market], default="china_a")
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of)
    require_timezone(as_of, "as_of")
    start = date.fromisoformat(args.start)
    if start > as_of.astimezone(UTC).date():
        parser.error("start must not follow as-of")
    settings = load_settings(args.config)
    engine = research_engine_from_settings(settings.research)
    technical = next(module for module in engine.modules
                     if isinstance(module, TechnicalResearchModule))
    service = MarketDataService(SQLiteStore(args.database, read_only=True))
    results = []
    with service.read_snapshot():
        for symbol in args.symbols:
            bars = tuple(service.daily_bars(
                symbol, Market(args.market), AssetType.EQUITY, start,
                as_of.astimezone(UTC).date(), as_of=as_of,
            ))
            results.append({
                "symbol": symbol, "market": args.market, "observed_bar_rows": len(bars),
                "first_observation": bars[0].timestamp.isoformat() if bars else None,
                "last_observation": bars[-1].timestamp.isoformat() if bars else None,
                "diagnostics": technical_diagnostics(bars, technical.parameters, as_of=as_of),
                "limitations": [
                    "Observed dates are not verified exchange sessions or source authentication",
                    "Unadjusted corporate actions, gaps and stale data need independent review",
                    "No financial/sentiment/industry/style qualification or trading decision",
                    "PIT readiness is not promoted by successful calculations",
                ],
            })
    document = {"as_of": as_of.isoformat(), "research_only": True,
                "readiness_promoted": False, "results": results}
    reject_sensitive_structure(document)
    print(json.dumps(document, indent=2, sort_keys=True, allow_nan=False))
    raise SystemExit(2)  # Partial diagnostics, not a successful investment validation.


if __name__ == "__main__":
    main()
