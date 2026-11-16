"""Bounded per-endpoint AKShare diagnostics. No persistence or trading authorization."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.models import DailyBarRequest
from tong_quant.data.providers.akshare import AkShareAdapter

DEFAULT_ENDPOINTS = ("stock_zh_a_hist", "stock_zh_a_hist_tx")
ENDPOINTS = (*DEFAULT_ENDPOINTS, "stock_zh_a_daily")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument("--endpoint", choices=ENDPOINTS, help=argparse.SUPPRESS)
    parser.add_argument("--include-sina", action="store_true",
                        help="Probe Sina separately; never use it as an ingestion fallback")
    parser.add_argument("--timeout-seconds", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 60:
        parser.error("timeout must be between 1 and 60 seconds")
    if len(args.symbol) != 6 or not args.symbol.isascii() or not args.symbol.isdigit():
        parser.error("symbol must contain six ASCII digits")
    request = DailyBarRequest(args.symbol, args.start_date, args.end_date)
    if args.endpoint:
        result = AkShareAdapter(timeout_seconds=min(args.timeout_seconds, 5)).probe_daily_endpoint(
            request, endpoint=args.endpoint,
        )
        reject_sensitive_structure(result)
        print(json.dumps(result, sort_keys=True))
        return 0
    results = []
    for endpoint in ENDPOINTS if args.include_sina else DEFAULT_ENDPOINTS:
        try:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), args.symbol,
                 args.start_date, args.end_date, "--endpoint", endpoint,
                 "--timeout-seconds", str(args.timeout_seconds)],
                capture_output=True, text=True, timeout=args.timeout_seconds, check=False,
            )
            result = json.loads(completed.stdout)
            if (completed.returncode != 0 or not isinstance(result, dict)
                    or result.get("endpoint") != endpoint or result.get("symbol") != args.symbol
                    or result.get("start_date") != args.start_date
                    or result.get("end_date") != args.end_date
                    or result.get("coverage_qualified") is not False
                    or result.get("status") not in {
                        "available", "empty", "failed", "contract_mismatch",
                    }):
                raise ValueError("worker diagnostic unavailable")
            reject_sensitive_structure(result)
        except subprocess.TimeoutExpired:
            result = {"endpoint": endpoint, "status": "worker_timeout",
                      "category": "bounded_worker_timeout", "coverage_qualified": False}
        except (ValueError, TypeError):
            result = {"endpoint": endpoint, "status": "worker_failed",
                      "category": "diagnostic_unavailable", "coverage_qualified": False}
        results.append(result)
    print(json.dumps({"provider": "akshare", "symbol": args.symbol,
                      "research_only": True, "probes": results}, indent=2, sort_keys=True))
    return 2  # Access diagnostics do not qualify a historical dataset.


if __name__ == "__main__":
    raise SystemExit(main())
