import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tong_quant.data.cache import DataFrameCache
from tong_quant.data.calibration import (
    CalibrationDataset,
    CalibrationQuery,
    MemoizedCalibrationSource,
    PhaseThreeCalibrationRunner,
    PhaseThreeQuerySpec,
    ProviderCalibrationCoordinator,
    dashboard_json,
    render_dashboard_markdown,
)
from tong_quant.data.providers.akshare import AkShareAdapter
from tong_quant.data.providers.calibration import AkShareCalibrationAdapter
from tong_quant.data.providers.tushare import TushareCalibrationAdapter
from tong_quant.data.providers.tushare_capabilities import (
    CapabilityProbeContext,
    DatasetCapabilityStatus,
    TushareCapabilityDetector,
    capability_json,
    render_capability_markdown,
    tushare_client_from_environment,
)
from tong_quant.data.quality.akshare_audit import (
    AkShareQualityAuditor,
    akshare_audit_json,
    render_akshare_audit_markdown,
)
from tong_quant.data.readiness_gap import (
    build_readiness_gap_report,
    gap_report_json,
    render_gap_markdown,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run real-provider calibration and generate a PIT dashboard"
    )
    parser.add_argument("--database", type=Path, default=Path("data/tong_quant.sqlite3"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/phase3"))
    parser.add_argument("--symbol", default="600000")
    parser.add_argument("--trade-date")
    parser.add_argument("--period-end")
    args = parser.parse_args()

    as_of = datetime.now(UTC)
    trade_date = args.trade_date or (as_of.date() - timedelta(days=1)).strftime("%Y%m%d")
    period_end = args.period_end or f"{as_of.year - 1}1231"
    month_start = as_of.date().replace(day=1).strftime("%Y%m%d")
    end_date = as_of.date().strftime("%Y%m%d")

    cache = DataFrameCache(
        Path("data/cache/provider-calibration-phase3"),
        timedelta(hours=24),
        clock=lambda: as_of,
    )
    primary = MemoizedCalibrationSource(
        AkShareCalibrationAdapter(
            AkShareAdapter(cache=cache, clock=lambda: as_of, max_attempts=2)
        )
    )
    environment, tushare_client = tushare_client_from_environment()
    capability_report = TushareCapabilityDetector(
        client=tushare_client,
        clock=lambda: as_of,
    ).detect(
        environment,
        CapabilityProbeContext(
            as_of=as_of,
            ts_code=_ts_code(args.symbol),
            trade_date=trade_date,
            period_end=period_end,
            start_date=month_start,
            end_date=end_date,
        ),
    )
    has_calibration_capability = any(
        dataset.status is DatasetCapabilityStatus.AVAILABLE
        for dataset in capability_report.datasets
    )
    secondary = (
        TushareCalibrationAdapter(client=tushare_client, max_attempts=2)
        if tushare_client is not None and has_calibration_capability
        else None
    )

    store = SQLiteStore(args.database)
    store.initialize()
    specs = _query_specs(
        as_of=as_of,
        symbol=args.symbol,
        trade_date=trade_date,
        period_end=period_end,
        month_start=month_start,
        end_date=end_date,
    )
    dashboard = PhaseThreeCalibrationRunner(
        ProviderCalibrationCoordinator(store)
    ).run(
        primary,
        secondary,
        specs,
        secondary_unavailable_reason=(
            "; ".join(environment.warnings)
            or "No Tushare calibration dataset is fully available"
        ),
    )
    gap_report = build_readiness_gap_report(dashboard, capability_report)
    akshare_audit = AkShareQualityAuditor().audit(
        primary,
        specs,
        generated_at=as_of,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = args.output_dir / "framework-data-readiness.md"
    json_path = args.output_dir / "framework-data-readiness.json"
    markdown_path.write_text(render_dashboard_markdown(dashboard), encoding="utf-8")
    json_path.write_text(dashboard_json(dashboard) + "\n", encoding="utf-8")
    capability_markdown_path = args.output_dir / "tushare-provider-capabilities.md"
    capability_json_path = args.output_dir / "tushare-provider-capabilities.json"
    capability_markdown_path.write_text(
        render_capability_markdown(capability_report), encoding="utf-8"
    )
    capability_json_path.write_text(
        capability_json(capability_report) + "\n", encoding="utf-8"
    )
    gap_markdown_path = args.output_dir / "pit-readiness-gap-report.md"
    gap_json_path = args.output_dir / "pit-readiness-gap-report.json"
    gap_markdown_path.write_text(render_gap_markdown(gap_report), encoding="utf-8")
    gap_json_path.write_text(gap_report_json(gap_report) + "\n", encoding="utf-8")
    akshare_markdown_path = args.output_dir / "akshare-data-quality.md"
    akshare_json_path = args.output_dir / "akshare-data-quality.json"
    akshare_markdown_path.write_text(
        render_akshare_audit_markdown(akshare_audit), encoding="utf-8"
    )
    akshare_json_path.write_text(
        akshare_audit_json(akshare_audit) + "\n", encoding="utf-8"
    )
    print(markdown_path)
    print(json_path)
    print(capability_markdown_path)
    print(capability_json_path)
    print(gap_markdown_path)
    print(gap_json_path)
    print(akshare_markdown_path)
    print(akshare_json_path)


def _query_specs(
    *,
    as_of: datetime,
    symbol: str,
    trade_date: str,
    period_end: str,
    month_start: str,
    end_date: str,
) -> tuple[PhaseThreeQuerySpec, ...]:
    research_validation = ("Research Inputs", "Validation Inputs")
    lifecycle_areas = ("Security Lifecycle", *research_validation)
    universe_areas = (
        "Universe Membership",
        "Market Regime Inputs",
        *research_validation,
    )
    return (
        _spec(
            CalibrationDataset.SECURITY_LIFECYCLE,
            as_of,
            {"trade_date": trade_date},
            lifecycle_areas,
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.MEDIUM,
            35,
        ),
        _spec(
            CalibrationDataset.ST_STATUS,
            as_of,
            {},
            lifecycle_areas,
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.MEDIUM,
            50,
        ),
        _spec(
            CalibrationDataset.SUSPENSION_STATUS,
            as_of,
            {"trade_date": trade_date},
            lifecycle_areas,
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.MEDIUM,
            20,
        ),
        _spec(
            CalibrationDataset.DELISTING_RECORDS,
            as_of,
            {},
            lifecycle_areas,
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.MEDIUM,
            55,
        ),
        _spec(
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
            as_of,
            {"period_end": period_end},
            ("Fundamentals", *research_validation),
            AvailabilityPrecision.DATE_ONLY,
            DataTrustLevel.MEDIUM,
            70,
            revision_score=60,
        ),
        _spec(
            CalibrationDataset.FUNDAMENTAL_REVISIONS,
            as_of,
            {
                "symbol": symbol,
                "start_date": f"{as_of.year - 2}0101",
                "end_date": end_date,
            },
            ("Fundamentals", *research_validation),
            AvailabilityPrecision.EXACT,
            DataTrustLevel.HIGH,
            55,
            revision_score=70,
        ),
        _spec(
            CalibrationDataset.CORPORATE_ACTIONS,
            as_of,
            {"symbol": symbol},
            ("Corporate Actions", *research_validation),
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.MEDIUM,
            55,
            revision_score=25,
        ),
        _spec(
            CalibrationDataset.UNIVERSE_COVERAGE,
            as_of,
            {},
            universe_areas,
            AvailabilityPrecision.RETRIEVAL_TIME,
            DataTrustLevel.LOW,
            25,
        ),
        _index_spec(
            CalibrationDataset.CSI300_MEMBERSHIP,
            as_of,
            month_start,
            end_date,
            expected_records=300,
            framework_areas=universe_areas,
        ),
        _index_spec(
            CalibrationDataset.CSI500_MEMBERSHIP,
            as_of,
            month_start,
            end_date,
            expected_records=500,
            framework_areas=universe_areas,
        ),
        _index_spec(
            CalibrationDataset.CSI1000_MEMBERSHIP,
            as_of,
            month_start,
            end_date,
            expected_records=1000,
            framework_areas=universe_areas,
        ),
    )


def _spec(
    dataset: CalibrationDataset,
    as_of: datetime,
    parameters: dict[str, str],
    framework_areas: tuple[str, ...],
    precision: AvailabilityPrecision,
    trust: DataTrustLevel,
    continuity: float,
    *,
    revision_score: float = 0,
) -> PhaseThreeQuerySpec:
    return PhaseThreeQuerySpec(
        query=CalibrationQuery(dataset, as_of, parameters),
        framework_areas=framework_areas,
        availability_precision=precision,
        primary_trust_level=trust,
        historical_continuity_score=continuity,
        revision_score=revision_score,
    )


def _index_spec(
    dataset: CalibrationDataset,
    as_of: datetime,
    start_date: str,
    end_date: str,
    *,
    expected_records: int,
    framework_areas: tuple[str, ...],
) -> PhaseThreeQuerySpec:
    return PhaseThreeQuerySpec(
        query=CalibrationQuery(
            dataset,
            as_of,
            {"start_date": start_date, "end_date": end_date},
        ),
        framework_areas=framework_areas,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        primary_trust_level=DataTrustLevel.LOW,
        historical_continuity_score=25,
        expected_records=expected_records,
    )


def _ts_code(symbol: str) -> str:
    normalized = symbol.zfill(6)
    if normalized.startswith(("6", "9")):
        suffix = "SH"
    elif normalized.startswith(("4", "8")):
        suffix = "BJ"
    else:
        suffix = "SZ"
    return f"{normalized}.{suffix}"


if __name__ == "__main__":
    main()
