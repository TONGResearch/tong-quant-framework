import argparse
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tong_quant.data.monitoring import (
    ProviderContractMonitor,
    ProviderContractProbe,
    provider_contract_run_origin_from_environment,
    render_provider_contract_markdown,
    serialize_provider_contract,
)
from tong_quant.data.provider_health import (
    ProviderHealthAssessor,
    ProviderHealthPolicy,
    provider_health_annotations,
    render_provider_health_markdown,
    serialize_provider_health,
)
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.cninfo import (
    CNINFO_DISCLOSURES_DATASET,
    CnInfoEvidenceAdapter,
)
from tong_quant.data.providers.cninfo_direct import (
    CnInfoDirectEvidenceAdapter,
    CnInfoHttpClient,
)
from tong_quant.data.providers.contracts import (
    ProviderContractStatus,
    ProviderDatasetRequest,
)
from tong_quant.data.providers.yahoo import (
    YAHOO_DAILY_BARS_DATASET,
    YahooChartHttpClient,
    YahooFinanceEvidenceAdapter,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor CNInfo and Yahoo provider contracts without upgrading trust"
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/provider-contract-monitor.sqlite3"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/provider-contracts"),
    )
    parser.add_argument("--china-symbol", default="600000")
    parser.add_argument("--us-symbol", default="MSFT")
    parser.add_argument("--hong-kong-symbol", default="0700.HK")
    parser.add_argument("--malaysia-symbol", default="1155.KL")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--health-history-days", type=int, default=84)
    parser.add_argument("--degradation-threshold", type=int, default=3)
    parser.add_argument("--unavailable-threshold", type=int, default=2)
    parser.add_argument("--artifact-retention-days", type=int, default=90)
    parser.add_argument("--owner", default="TONGResearch")
    parser.add_argument(
        "--fail-on-defect",
        action="store_true",
        help="Fail only for implementation/contract defects, not provider downtime.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if min(
        args.lookback_days,
        args.health_history_days,
        args.degradation_threshold,
        args.unavailable_threshold,
        args.artifact_retention_days,
    ) < 1:
        raise SystemExit(
            "provider monitor window, threshold, and retention values must be positive"
        )
    if not args.owner.strip():
        raise SystemExit("--owner must not be empty")

    now = datetime.now(UTC)
    start = (now.date() - timedelta(days=args.lookback_days)).isoformat()
    end = now.date().isoformat()
    store = SQLiteStore(args.database)
    store.initialize()
    akshare = AkShareAdapter(clock=lambda: now, max_attempts=2)
    cninfo = CnInfoEvidenceAdapter(transport=akshare)
    cninfo_direct = CnInfoDirectEvidenceAdapter(
        client=CnInfoHttpClient(max_attempts=2, max_pages=1),
        clock=lambda: now,
    )
    yahoo = YahooFinanceEvidenceAdapter(
        client=YahooChartHttpClient(max_attempts=2),
        clock=lambda: now,
    )
    probes = (
        ProviderContractProbe(
            adapter=cninfo,
            request=ProviderDatasetRequest(
                dataset=CNINFO_DISCLOSURES_DATASET,
                market=Market.CHINA_A,
                subject=args.china_symbol,
                as_of=now,
                parameters={
                    "start_date": start.replace("-", ""),
                    "end_date": end.replace("-", ""),
                },
            ),
            required_payload_fields=("symbol", "title", "announcement_time"),
        ),
        ProviderContractProbe(
            adapter=cninfo_direct,
            request=ProviderDatasetRequest(
                dataset=CNINFO_DISCLOSURES_DATASET,
                market=Market.CHINA_A,
                subject=args.china_symbol,
                as_of=now,
                parameters={
                    "start_date": start,
                    "end_date": end,
                    "capture_artifacts": "false",
                    "max_artifacts": "0",
                },
            ),
            required_payload_fields=(
                "symbol",
                "title",
                "announcement_id",
                "announcement_time",
                "artifact_status",
            ),
        ),
        *_yahoo_probes(
            adapter=yahoo,
            now=now,
            start=start,
            end=end,
            symbols=(
                (Market.US, args.us_symbol),
                (Market.HONG_KONG, args.hong_kong_symbol),
                (Market.MALAYSIA, args.malaysia_symbol),
            ),
        ),
    )
    origin, origin_reference = provider_contract_run_origin_from_environment(
        os.environ
    )
    report = ProviderContractMonitor(repository=store).run(
        probes,
        origin=origin,
        origin_reference=origin_reference,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    monitor_stem = f"provider-contract-run-{report.run_id}"
    markdown_path = args.output_dir / f"{monitor_stem}.md"
    json_path = args.output_dir / f"{monitor_stem}.json"
    _write_idempotent(
        markdown_path,
        render_provider_contract_markdown(report),
    )
    _write_idempotent(json_path, serialize_provider_contract(report) + "\n")
    print(markdown_path)
    print(json_path)

    health = ProviderHealthAssessor(
        repository=store,
        policy=ProviderHealthPolicy(
            history_window_days=args.health_history_days,
            repeated_degradation_threshold=args.degradation_threshold,
            repeated_unavailable_threshold=args.unavailable_threshold,
            artifact_retention_days=args.artifact_retention_days,
            owner=args.owner,
        ),
    ).assess(report)
    health_stem = f"provider-health-{health.report_id}"
    health_markdown_path = args.output_dir / f"{health_stem}.md"
    health_json_path = args.output_dir / f"{health_stem}.json"
    _write_idempotent(
        health_markdown_path,
        render_provider_health_markdown(health),
    )
    _write_idempotent(health_json_path, serialize_provider_health(health) + "\n")
    print(health_markdown_path)
    print(health_json_path)
    for annotation in provider_health_annotations(health):
        print(annotation)

    if args.fail_on_defect and report.status is ProviderContractStatus.DEFECT:
        raise SystemExit("Provider contract monitor found an implementation defect")


def _yahoo_probes(
    *,
    adapter: YahooFinanceEvidenceAdapter,
    now: datetime,
    start: str,
    end: str,
    symbols: tuple[tuple[Market, str], ...],
) -> tuple[ProviderContractProbe, ...]:
    return tuple(
        ProviderContractProbe(
            adapter=adapter,
            request=ProviderDatasetRequest(
                dataset=YAHOO_DAILY_BARS_DATASET,
                market=market,
                subject=symbol,
                as_of=now,
                parameters={"start_date": start, "end_date": end},
            ),
            required_payload_fields=(
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ),
        )
        for market, symbol in symbols
    )


def _write_idempotent(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError("provider monitor output must not be a symbolic link")
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError("provider monitor output identity collision")
        return
    with path.open("x", encoding="utf-8") as output:
        output.write(content)


if __name__ == "__main__":
    main()
