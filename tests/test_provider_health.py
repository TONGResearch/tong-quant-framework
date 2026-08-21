from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.data.baselines import (
    ProviderBaselineQuery,
    ProviderBaselineScope,
    ProviderContractObservation,
)
from tong_quant.data.provider_health import (
    ProviderHealthAssessor,
    ProviderHealthCondition,
    ProviderHealthPolicy,
    ProviderHealthSeverity,
    ProviderHealthStatus,
    provider_health_annotations,
    provider_health_json,
    render_provider_health_markdown,
    serialize_provider_health,
)
from tong_quant.data.providers.contracts import (
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 8, 22, 12, tzinfo=UTC)
SCOPE = ProviderBaselineScope(
    provider="research_provider",
    dataset="daily_bars",
    market=Market.US,
    subject="MSFT",
)


@dataclass
class _Repository:
    observations: tuple[ProviderContractObservation, ...] = ()

    def provider_contract_observations(
        self,
        query: ProviderBaselineQuery,
    ) -> tuple[ProviderContractObservation, ...]:
        del query
        return self.observations


def _check(
    check_id: str,
    status: ProviderContractStatus,
    checked_at: datetime,
    *,
    run_id: str = "current-run",
) -> ProviderContractCheck:
    return ProviderContractCheck(
        check_id=check_id,
        run_id=run_id,
        provider=SCOPE.provider,
        dataset=SCOPE.dataset,
        market=SCOPE.market,
        subject=SCOPE.subject,
        request_as_of=checked_at,
        status=status,
        records_observed=(0 if status is ProviderContractStatus.UNAVAILABLE else 5),
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        latency_ms=25,
        required_fields=("close", "volume"),
        missing_fields=(
            ("close", "volume")
            if status
            in {ProviderContractStatus.UNAVAILABLE, ProviderContractStatus.DEFECT}
            else ()
        ),
        limitations=("research-grade provider",),
        error_code=("ValueError" if status is ProviderContractStatus.DEFECT else ""),
        checked_at=checked_at,
    )


def _observation(
    check_id: str,
    status: ProviderContractStatus,
    checked_at: datetime,
) -> ProviderContractObservation:
    check = _check(check_id, status, checked_at, run_id=f"run-{check_id}")
    return ProviderContractObservation(
        check_id=check.check_id,
        run_id=check.run_id,
        scope=SCOPE,
        request_as_of=check.request_as_of,
        checked_at=check.checked_at,
        status=check.status,
        records_observed=check.records_observed,
        trust_level=check.trust_level,
        availability_precision=check.availability_precision,
        required_fields=check.required_fields,
        missing_fields=check.missing_fields,
        limitations=check.limitations,
        error_code=check.error_code,
        implementation_version="provider-contract-monitor-test",
    )


def _run(check: ProviderContractCheck) -> ProviderContractRun:
    return ProviderContractRun(
        run_id=check.run_id,
        started_at=check.checked_at - timedelta(seconds=1),
        completed_at=check.checked_at,
        status=check.status,
        checks=(check,),
        implementation_version="provider-contract-monitor-test",
    )


def test_healthy_run_without_prior_failure_is_normal_and_deterministic() -> None:
    assessor = ProviderHealthAssessor(_Repository())
    run = _run(_check("healthy", ProviderContractStatus.HEALTHY, NOW))

    first = assessor.assess(run)
    second = assessor.assess(run)

    assert first == second
    assert first.status is ProviderHealthStatus.NORMAL
    assert first.alerts == ()
    assert provider_health_json(first)["boundaries"] == {
        "notification_engine_used": False,
        "external_delivery_used": False,
        "trading_effect": False,
    }


def test_one_off_unavailable_is_informational_not_code_failure() -> None:
    report = ProviderHealthAssessor(_Repository()).assess(
        _run(_check("unavailable", ProviderContractStatus.UNAVAILABLE, NOW))
    )

    alert = report.alerts[0]
    assert report.status is ProviderHealthStatus.WATCH
    assert alert.condition is ProviderHealthCondition.ONE_OFF_UNAVAILABLE
    assert alert.severity is ProviderHealthSeverity.INFO
    assert not alert.acknowledgement_required


def test_repeated_unavailable_and_degradation_require_acknowledgement() -> None:
    unavailable_history = (_observation(
        "unavailable-1",
        ProviderContractStatus.UNAVAILABLE,
        NOW - timedelta(days=3),
    ),)
    unavailable = ProviderHealthAssessor(_Repository(unavailable_history)).assess(
        _run(_check("unavailable-2", ProviderContractStatus.UNAVAILABLE, NOW))
    )
    unavailable_alert = unavailable.alerts[0]
    assert unavailable.status is ProviderHealthStatus.ACTION_REQUIRED
    assert unavailable_alert.condition is ProviderHealthCondition.REPEATED_UNAVAILABLE
    assert unavailable_alert.consecutive_count == 2
    assert unavailable_alert.acknowledgement_required
    later_unavailable = ProviderHealthAssessor(
        _Repository(
            (
                *unavailable_history,
                _observation(
                    "unavailable-2",
                    ProviderContractStatus.UNAVAILABLE,
                    NOW,
                ),
            )
        )
    ).assess(
        _run(
            _check(
                "unavailable-3",
                ProviderContractStatus.UNAVAILABLE,
                NOW + timedelta(days=3),
            )
        )
    )
    assert (
        later_unavailable.alerts[0].alert_fingerprint
        == unavailable_alert.alert_fingerprint
    )
    assert later_unavailable.alerts[0].alert_id != unavailable_alert.alert_id

    degraded_history = (
        _observation(
            "degraded-1",
            ProviderContractStatus.DEGRADED,
            NOW - timedelta(days=6),
        ),
        _observation(
            "degraded-2",
            ProviderContractStatus.DEGRADED,
            NOW - timedelta(days=3),
        ),
    )
    degraded = ProviderHealthAssessor(_Repository(degraded_history)).assess(
        _run(_check("degraded-3", ProviderContractStatus.DEGRADED, NOW))
    )
    degraded_alert = degraded.alerts[0]
    assert degraded_alert.condition is ProviderHealthCondition.REPEATED_DEGRADATION
    assert degraded_alert.consecutive_count == 3
    assert degraded_alert.severity is ProviderHealthSeverity.WARNING


def test_implementation_defect_is_blocking_without_raw_exception_text() -> None:
    report = ProviderHealthAssessor(_Repository()).assess(
        _run(_check("defect", ProviderContractStatus.DEFECT, NOW))
    )

    alert = report.alerts[0]
    assert report.status is ProviderHealthStatus.BLOCKING
    assert alert.condition is ProviderHealthCondition.IMPLEMENTATION_DEFECT
    assert alert.severity is ProviderHealthSeverity.CRITICAL
    assert alert.acknowledgement_required
    assert "provider rejected secret-value" not in serialize_provider_health(report)
    assert provider_health_annotations(report)[0].startswith("::error")
    assert "Notification Engine" in render_provider_health_markdown(report)
    with pytest.raises(ValueError, match="alert hash"):
        replace(
            alert,
            severity=ProviderHealthSeverity.INFO,
            acknowledgement_required=False,
        )


def test_recovery_is_visible_but_does_not_require_acknowledgement() -> None:
    history = (
        _observation(
            "prior-outage",
            ProviderContractStatus.UNAVAILABLE,
            NOW - timedelta(days=3),
        ),
    )
    report = ProviderHealthAssessor(_Repository(history)).assess(
        _run(_check("recovered", ProviderContractStatus.HEALTHY, NOW))
    )

    alert = report.alerts[0]
    assert report.status is ProviderHealthStatus.WATCH
    assert alert.condition is ProviderHealthCondition.RECOVERED
    assert alert.related_check_ids == ("prior-outage", "recovered")
    assert not alert.acknowledgement_required


def test_repository_history_must_stay_in_scope_and_window() -> None:
    stale = _observation(
        "stale",
        ProviderContractStatus.DEGRADED,
        NOW - timedelta(days=100),
    )
    assessor = ProviderHealthAssessor(
        _Repository((stale,)),
        ProviderHealthPolicy(history_window_days=84),
    )

    with pytest.raises(ValueError, match="out-of-scope history"):
        assessor.assess(_run(_check("current", ProviderContractStatus.HEALTHY, NOW)))


def test_sqlite_history_round_trip_drives_repeated_condition(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "provider-health.sqlite3")
    store.initialize()
    first_check = _check(
        "first",
        ProviderContractStatus.UNAVAILABLE,
        NOW - timedelta(days=3),
        run_id="first-run",
    )
    current_check = _check(
        "current",
        ProviderContractStatus.UNAVAILABLE,
        NOW,
    )
    store.save_provider_contract_run(_run(first_check))
    current_run = _run(current_check)
    store.save_provider_contract_run(current_run)

    report = ProviderHealthAssessor(store).assess(current_run)

    assert report.alerts[0].condition is ProviderHealthCondition.REPEATED_UNAVAILABLE
    assert report.alerts[0].related_check_ids == ("first", "current")
