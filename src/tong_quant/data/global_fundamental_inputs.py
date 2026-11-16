"""Read retained native overseas financial observations, not admitted Financial inputs."""

from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderDatasetRequest, ProviderEvidenceBatch
from tong_quant.data.providers.yahoo_fundamentals import (
    DATASET,
    LIMITATIONS,
    MAX_BYTES,
    NATIVE_METRICS,
    PROVIDER,
    YahooFundamentalCapture,
    YahooFundamentalSnapshotAdapter,
)
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.retained_snapshot import verify_retained_snapshot
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION


def _rebuild(envelope: dict[str, Any]) -> ProviderEvidenceBatch:
    if envelope["model_version"] != GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION:
        raise ValueError("unsupported native fundamental normalization version")
    captured = datetime.fromisoformat(envelope["retrieved_at"])
    request = ProviderDatasetRequest(DATASET, Market(envelope["market"]), envelope["subject"],
                                     captured, envelope["parameters"])
    capture = YahooFundamentalCapture(envelope["decoded_payload"], envelope["error_code"])
    adapter = YahooFundamentalSnapshotAdapter(download=lambda _: capture, clock=lambda: captured)
    return adapter.fetch(request)


def read_global_fundamental_inputs(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, subject: str, market: Market,
    *, as_of: datetime,
) -> dict[str, Any]:
    require_timezone(as_of, "native fundamental read cutoff")
    validate_yahoo_equity_subject(market, subject)
    output: dict[str, Any] = {"subject": subject, "market": market.value, "as_of": as_of,
        "status": "missing", "source_bound": False, "captures": [], "observations": [],
        "latest": {}, "missing_metrics": list(NATIVE_METRICS), "reporting_currencies": [],
        "usable_native_metric_count": 0,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "freshness": "UNASSESSED", "publication_dates_available": False,
        "revision_history_available": False, "accounting_definitions_admitted": False,
        "financial_scoring_authorized": False, "historical_replay_eligible": False,
        "investment_scoring_authorized": False, "validation_authorized": False,
        "execution_authorized": False, "research_report_created": False,
        "limitations": LIMITATIONS, "model_version": GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION}
    with store.read_snapshot():
        records = MarketDataService(store).provider_evidence(provider=PROVIDER, dataset=DATASET,
            market=market, subject=subject, as_of=as_of)
        ordered = sorted(records, key=lambda item: (item.available_at.astimezone(UTC),
                                                    item.evidence_id))
        output["captures"] = [{"evidence_id": item.evidence_id, "raw_data_hash": item.raw_data_hash,
            "available_at": item.available_at, "status": item.payload.get("status")}
            for item in ordered]
        if ordered:
            latest_time = ordered[-1].available_at.astimezone(UTC)
            latest = [item for item in ordered if item.available_at.astimezone(UTC) == latest_time]
            output["status"] = "rejected_or_ambiguous"
            if len(latest) == 1:
                record = latest[0]
                try:
                    verify_retained_snapshot(store, artifacts, record, as_of=as_of,
                                             max_bytes=MAX_BYTES + 4096, rebuild=_rebuild)
                    output.update(record.payload)
                    output["source_bound"] = True
                    output["selected_evidence_id"] = record.evidence_id
                    output["period_age_days"] = {name: (
                        as_of.astimezone(UTC).date() - date.fromisoformat(row["period_end"])).days
                        for name, row in output["latest"].items() if row.get("period_end")}
                except (ValueError, OSError, KeyError, TypeError, ArithmeticError):
                    pass
    return {**output, "input_hash": sha256(financial_input_json(output).encode()).hexdigest()}
