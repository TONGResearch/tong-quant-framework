import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.monitoring import (
    ProviderContractMonitor,
    ProviderContractProbe,
    provider_contract_run_origin_from_environment,
    serialize_provider_contract,
)
from tong_quant.data.providers.contracts import (
    ProviderCapabilityStatus,
    ProviderContractRunOrigin,
    ProviderContractStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_evidence_id,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 6, 20, 12, tzinfo=UTC)
OBSERVED = datetime(2026, 6, 20, 10, tzinfo=UTC)
RAW_HASH = sha256(b"contract-monitor").hexdigest()
SECRET = "token-that-must-not-be-persisted"


class _ContractAdapter:
    provider_id = "contract_provider"

    def __init__(
        self,
        failure: Exception | None = None,
        *,
        omit_volume: bool = False,
        null_volume: bool = False,
        empty_records: bool = False,
    ) -> None:
        self.failure = failure
        self.omit_volume = omit_volume
        self.null_volume = null_volume
        self.empty_records = empty_records

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset="daily_bars",
                markets=(Market.US,),
                status=ProviderCapabilityStatus.AVAILABLE,
                trust_level=DataTrustLevel.MEDIUM,
                availability_precision=AvailabilityPrecision.EXACT,
                historical_continuity=True,
                required_parameters=(),
                limitations=(),
            ),
        )

    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        if self.failure is not None:
            raise self.failure
        payload: dict[str, object] = {"close": 100.0, "volume": 10_000}
        if self.omit_volume:
            del payload["volume"]
        if self.null_volume:
            payload["volume"] = None
        record = ProviderEvidenceRecord(
            evidence_id=provider_evidence_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject=request.subject,
                available_at=OBSERVED,
                source_reference="contract:test",
                payload=payload,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            observed_at=OBSERVED,
            available_at=OBSERVED,
            retrieved_at=NOW,
            source_reference="contract:test",
            payload=payload,
            raw_data_hash=RAW_HASH,
            availability_precision=AvailabilityPrecision.EXACT,
            trust_level=DataTrustLevel.MEDIUM,
            limitations=(),
        )
        return ProviderEvidenceBatch(
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            retrieved_at=NOW,
            source="contract:test",
            parameters={},
            raw_data_hash=RAW_HASH,
            raw_record_count=1,
            records=() if self.empty_records else (record,),
            limitations=(),
        )


def _probe(adapter: _ContractAdapter) -> ProviderContractProbe:
    return ProviderContractProbe(
        adapter=adapter,
        request=ProviderDatasetRequest(
            dataset="daily_bars",
            market=Market.US,
            subject="MSFT",
            as_of=NOW,
        ),
        required_payload_fields=("close", "volume"),
    )


def test_contract_monitor_persists_healthy_check_atomically(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "monitor.sqlite3")
    store.initialize()
    timer_values = iter((1.0, 1.025))

    run = ProviderContractMonitor(
        repository=store,
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run((_probe(_ContractAdapter()),))

    assert run.status is ProviderContractStatus.HEALTHY
    assert run.checks[0].latency_ms == pytest.approx(25)
    assert store.table_count("provider_contract_runs") == 1
    assert store.table_count("provider_contract_checks") == 1


def test_scheduled_run_origin_is_persisted_with_github_reference(tmp_path: Path) -> None:
    database = tmp_path / "monitor.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    timer_values = iter((1.0, 1.025))
    reference = "github_actions:TONGResearch/tong-quant-framework:123:1"
    run = ProviderContractMonitor(
        repository=store,
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run(
        (_probe(_ContractAdapter()),),
        origin=ProviderContractRunOrigin.SCHEDULED,
        origin_reference=reference,
    )

    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT run_origin, origin_reference FROM provider_contract_runs WHERE run_id = ?",
            (run.run_id,),
        ).fetchone()
    assert stored == ("scheduled", reference)
    assert '"origin": "scheduled"' in serialize_provider_contract(run)


def test_scheduled_origin_requires_valid_reference() -> None:
    timer_values = iter((1.0, 1.025))
    monitor = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    )

    with pytest.raises(ValueError, match="requires an origin reference"):
        monitor.run(
            (_probe(_ContractAdapter()),),
            origin=ProviderContractRunOrigin.SCHEDULED,
        )


def test_github_run_origin_detection_fails_closed() -> None:
    base = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "TONGResearch/tong-quant-framework",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    assert provider_contract_run_origin_from_environment(
        {**base, "GITHUB_EVENT_NAME": "schedule"}
    ) == (
        ProviderContractRunOrigin.SCHEDULED,
        "github_actions:TONGResearch/tong-quant-framework:123:1",
    )
    assert provider_contract_run_origin_from_environment(
        {**base, "GITHUB_EVENT_NAME": "workflow_dispatch"}
    )[0] is ProviderContractRunOrigin.MANUAL
    assert provider_contract_run_origin_from_environment(
        {**base, "GITHUB_EVENT_NAME": "schedule", "GITHUB_RUN_ID": ""}
    ) == (ProviderContractRunOrigin.UNKNOWN, None)
    assert provider_contract_run_origin_from_environment({}) == (
        ProviderContractRunOrigin.MANUAL,
        None,
    )


def test_contract_monitor_classifies_provider_failure_without_secret_leak() -> None:
    timer_values = iter((1.0, 1.01))
    run = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run(
        (
            _probe(
                _ContractAdapter(
                    DataProviderError(f"remote rejected credential {SECRET}")
                )
            ),
        )
    )

    assert run.status is ProviderContractStatus.UNAVAILABLE
    assert run.checks[0].error_code == "DataProviderError"
    assert SECRET not in serialize_provider_contract(run)


def test_contract_monitor_distinguishes_implementation_defect() -> None:
    timer_values = iter((1.0, 1.01))
    run = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run((_probe(_ContractAdapter(ValueError(f"parser bug {SECRET}"))),))

    assert run.status is ProviderContractStatus.DEFECT
    assert run.checks[0].error_code == "ValueError"
    assert SECRET not in serialize_provider_contract(run)


def test_contract_monitor_treats_missing_required_field_as_defect() -> None:
    timer_values = iter((1.0, 1.01))
    run = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run((_probe(_ContractAdapter(omit_volume=True)),))

    assert run.status is ProviderContractStatus.DEFECT
    assert run.checks[0].missing_fields == ("volume",)
    assert run.checks[0].error_code == "required_fields_missing"


def test_contract_monitor_treats_null_required_value_as_degraded() -> None:
    timer_values = iter((1.0, 1.01))
    run = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run((_probe(_ContractAdapter(null_volume=True)),))

    assert run.status is ProviderContractStatus.DEGRADED
    assert run.checks[0].missing_fields == ("volume",)
    assert run.checks[0].error_code == "required_values_missing"
    assert "null required values" in run.checks[0].limitations[-1]


def test_contract_monitor_treats_empty_response_as_degraded() -> None:
    timer_values = iter((1.0, 1.01))
    run = ProviderContractMonitor(
        clock=lambda: NOW,
        timer=lambda: next(timer_values),
    ).run((_probe(_ContractAdapter(empty_records=True)),))

    assert run.status is ProviderContractStatus.DEGRADED
    assert run.checks[0].missing_fields == ("close", "volume")
    assert run.checks[0].error_code == "no_normalized_evidence"
    assert "no normalized evidence" in run.checks[0].limitations[-1]
