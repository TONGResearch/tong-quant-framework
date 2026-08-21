import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tong_quant.core.exceptions import ConfigurationError
from tong_quant.data.calibration.daily_bars import (
    DailyBarCalibrationCoordinator,
    DailyBarCalibrationQuery,
    DailyBarCalibrationSource,
    DailyBarPriceBasis,
    EvidenceDailyBarCalibrationSource,
    FixtureDailyBarCalibrationSource,
    UnavailableDailyBarCalibrationSource,
    YahooDailyBarCalibrationSource,
)
from tong_quant.data.calibration.models import ProviderCalibrationOutcome
from tong_quant.data.providers.massive import MassiveEvidenceAdapter, MassiveHttpClient
from tong_quant.data.providers.yahoo import (
    YahooChartHttpClient,
    YahooFinanceEvidenceAdapter,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate Yahoo unadjusted daily bars without trading logic"
    )
    parser.add_argument("--market", choices=[item.value for item in Market], required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--as-of",
        type=_aware_datetime,
        help="Timezone-aware ISO timestamp; required for deterministic fixture runs",
    )
    parser.add_argument("--yahoo-fixture", type=Path)
    parser.add_argument("--secondary-fixture", type=Path)
    parser.add_argument("--secondary-provider", default="massive")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/yahoo-calibration.sqlite3"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/yahoo-calibration"),
    )
    parser.add_argument("--require-secondary", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    market = Market(args.market)
    if (args.yahoo_fixture is not None or args.secondary_fixture is not None) and (
        args.as_of is None
    ):
        raise SystemExit("--as-of is required when fixture input is used")
    as_of = args.as_of or datetime.now(UTC)
    query = DailyBarCalibrationQuery(
        market=market,
        subject=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        as_of=as_of,
    )
    primary = (
        FixtureDailyBarCalibrationSource.from_path(args.yahoo_fixture)
        if args.yahoo_fixture is not None
        else YahooDailyBarCalibrationSource(
            YahooFinanceEvidenceAdapter(
                client=YahooChartHttpClient(),
                clock=lambda: datetime.now(UTC),
            )
        )
    )
    secondary = _secondary_source(args, query)
    store = SQLiteStore(args.database)
    store.initialize()
    outcome = DailyBarCalibrationCoordinator(store).run(primary, secondary, query)
    document = _document(outcome)
    output = args.output_dir / f"yahoo-calibration-{outcome.attempt.attempt_id}.json"
    _write_idempotent(output, json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(output)
    if args.require_secondary and outcome.result is None:
        raise SystemExit(2)


def _secondary_source(
    args: argparse.Namespace,
    query: DailyBarCalibrationQuery,
) -> DailyBarCalibrationSource:
    if args.secondary_fixture is not None:
        return FixtureDailyBarCalibrationSource.from_path(args.secondary_fixture)
    if args.secondary_provider != "massive":
        return UnavailableDailyBarCalibrationSource(
            provider_id=args.secondary_provider,
            reason_code="secondary_adapter_not_configured",
        )
    if query.market is not Market.US:
        return UnavailableDailyBarCalibrationSource(
            provider_id="massive",
            reason_code="market_not_supported",
        )
    try:
        client = MassiveHttpClient.from_environment()
    except ConfigurationError:
        return UnavailableDailyBarCalibrationSource(
            provider_id="massive",
            reason_code="environment_credential_missing",
            price_basis=DailyBarPriceBasis.UNADJUSTED,
            trust_level=DataTrustLevel.UNKNOWN,
            availability_precision=AvailabilityPrecision.UNKNOWN,
        )
    return EvidenceDailyBarCalibrationSource(
        adapter=MassiveEvidenceAdapter(
            client=client,
            clock=lambda: datetime.now(UTC),
        ),
        price_basis=DailyBarPriceBasis.UNADJUSTED,
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
    )


def _document(outcome: ProviderCalibrationOutcome) -> dict[str, object]:
    attempt = outcome.attempt
    document: dict[str, object] = {
        "attempt_id": attempt.attempt_id,
        "dataset": attempt.dataset,
        "market": attempt.market.value,
        "subject": attempt.subject,
        "as_of": attempt.as_of.isoformat(),
        "status": attempt.status.value,
        "primary_provider": attempt.primary_provider,
        "secondary_provider": attempt.secondary_provider,
        "primary_price_basis": attempt.primary_price_basis,
        "secondary_price_basis": attempt.secondary_price_basis,
        "primary_trust_level": attempt.primary_trust_level.value,
        "secondary_trust_level": attempt.secondary_trust_level.value,
        "primary_availability_precision": (
            attempt.primary_availability_precision.value
        ),
        "primary_input_hash": attempt.primary_input_hash,
        "secondary_availability_precision": (
            attempt.secondary_availability_precision.value
        ),
        "secondary_input_hash": attempt.secondary_input_hash,
        "unavailable_provider": attempt.unavailable_provider,
        "reason_code": attempt.reason_code,
        "limitations": list(attempt.limitations),
        "model_version": attempt.model_version,
    }
    if outcome.result is not None:
        document["comparison"] = {
            "report_id": outcome.result.report.report_id,
            "primary_count": outcome.result.report.primary_count,
            "secondary_count": outcome.result.report.secondary_count,
            "matched_count": outcome.result.report.matched_count,
            "key_overlap_score": outcome.result.report.key_overlap_score,
            "field_match_scores": outcome.result.report.field_match_scores,
            "consistency_score": outcome.result.report.consistency_score,
            "trust_level": outcome.result.report.trust_level.value,
            "conflict_count": len(outcome.result.conflicts),
        }
    return document


def _write_idempotent(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("calibration output must not be a symbolic link")
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError("calibration output hash collision")
        path.chmod(0o600)
        return
    with path.open("x", encoding="utf-8") as output:
        output.write(content)
    path.chmod(0o600)


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--as-of must include a UTC offset")
    return parsed


if __name__ == "__main__":
    main()
