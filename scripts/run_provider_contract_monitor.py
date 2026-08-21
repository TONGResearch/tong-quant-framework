import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tong_quant.data.monitoring import (
    ProviderContractMonitor,
    ProviderContractProbe,
    render_provider_contract_markdown,
    serialize_provider_contract,
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
    parser.add_argument(
        "--fail-on-defect",
        action="store_true",
        help="Fail only for implementation/contract defects, not provider downtime.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.lookback_days < 1:
        raise SystemExit("--lookback-days must be positive")

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
    report = ProviderContractMonitor(repository=store).run(probes)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = args.output_dir / "provider-contract-monitor.md"
    json_path = args.output_dir / "provider-contract-monitor.json"
    markdown_path.write_text(
        render_provider_contract_markdown(report), encoding="utf-8"
    )
    json_path.write_text(serialize_provider_contract(report) + "\n", encoding="utf-8")
    print(markdown_path)
    print(json_path)

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


if __name__ == "__main__":
    main()
