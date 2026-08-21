import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from tong_quant.data.baselines import (
    ProviderBaselineQuery,
    ProviderBaselineScope,
    ProviderContractObservation,
)
from tong_quant.data.providers.contracts import (
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
)
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    FRAMEWORK_VERSION,
    PROVIDER_CONTRACT_MONITOR_VERSION,
    PROVIDER_HEALTH_POLICY_VERSION,
)


class ProviderHealthCondition(StrEnum):
    IMPLEMENTATION_DEFECT = "implementation_defect"
    ONE_OFF_UNAVAILABLE = "one_off_unavailable"
    REPEATED_UNAVAILABLE = "repeated_unavailable"
    ONE_OFF_DEGRADATION = "one_off_degradation"
    REPEATED_DEGRADATION = "repeated_degradation"
    RECOVERED = "recovered"


class ProviderHealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ProviderHealthStatus(StrEnum):
    NORMAL = "normal"
    WATCH = "watch"
    ACTION_REQUIRED = "action_required"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class ProviderHealthPolicy:
    history_window_days: int = 84
    repeated_degradation_threshold: int = 3
    repeated_unavailable_threshold: int = 2
    artifact_retention_days: int = 90
    owner: str = "TONGResearch"
    version: str = PROVIDER_HEALTH_POLICY_VERSION

    def __post_init__(self) -> None:
        if min(
            self.history_window_days,
            self.repeated_degradation_threshold,
            self.repeated_unavailable_threshold,
            self.artifact_retention_days,
        ) < 1:
            raise ValueError("provider health policy values must be positive")
        if not self.owner.strip() or not self.version.strip():
            raise ValueError("provider health policy owner and version are required")


@dataclass(frozen=True, slots=True)
class ProviderHealthAlert:
    alert_id: str
    alert_fingerprint: str
    scope: ProviderBaselineScope
    condition: ProviderHealthCondition
    severity: ProviderHealthSeverity
    observed_status: ProviderContractStatus
    consecutive_count: int
    related_check_ids: tuple[str, ...]
    first_seen_at: datetime
    last_seen_at: datetime
    owner: str
    acknowledgement_required: bool
    recovery_steps: tuple[str, ...]
    policy_version: str

    def __post_init__(self) -> None:
        if len(self.alert_id) != 64 or len(self.alert_fingerprint) != 64:
            raise ValueError("provider health alert identities must be SHA-256 digests")
        if self.consecutive_count < 1 or not self.related_check_ids:
            raise ValueError("provider health alert requires related observations")
        if len(self.related_check_ids) != len(set(self.related_check_ids)):
            raise ValueError("provider health alert check references must be unique")
        if not self.owner.strip() or not self.recovery_steps or not self.policy_version:
            raise ValueError("provider health alert ownership and recovery are required")
        require_timezone(self.first_seen_at, "provider health first_seen_at")
        require_timezone(self.last_seen_at, "provider health last_seen_at")
        if self.last_seen_at < self.first_seen_at:
            raise ValueError("provider health alert timestamps are inconsistent")
        if self.acknowledgement_required != (
            self.severity
            in {ProviderHealthSeverity.WARNING, ProviderHealthSeverity.CRITICAL}
        ):
            raise ValueError("provider health acknowledgement policy is inconsistent")
        if self.alert_fingerprint != _alert_fingerprint(
            self.scope,
            self.condition,
            self.policy_version,
        ):
            raise ValueError("provider health alert fingerprint is inconsistent")
        if self.alert_id != _stable_hash(
            _alert_content(
                alert_fingerprint=self.alert_fingerprint,
                scope=self.scope,
                condition=self.condition,
                severity=self.severity,
                observed_status=self.observed_status,
                consecutive_count=self.consecutive_count,
                related_check_ids=self.related_check_ids,
                first_seen_at=self.first_seen_at,
                last_seen_at=self.last_seen_at,
                owner=self.owner,
                acknowledgement_required=self.acknowledgement_required,
                recovery_steps=self.recovery_steps,
                policy_version=self.policy_version,
            )
        ):
            raise ValueError("provider health alert hash does not match its content")


@dataclass(frozen=True, slots=True)
class ProviderHealthReport:
    report_id: str
    run_id: str
    evaluated_at: datetime
    status: ProviderHealthStatus
    alerts: tuple[ProviderHealthAlert, ...]
    history_check_ids: tuple[str, ...]
    policy: ProviderHealthPolicy
    framework_version: str = FRAMEWORK_VERSION
    contract_monitor_version: str = PROVIDER_CONTRACT_MONITOR_VERSION
    implementation_version: str = PROVIDER_HEALTH_POLICY_VERSION

    def __post_init__(self) -> None:
        if len(self.report_id) != 64:
            raise ValueError("provider health report ID must be a SHA-256 digest")
        if not self.run_id.strip():
            raise ValueError("provider health report run ID is required")
        require_timezone(self.evaluated_at, "provider health evaluated_at")
        if len(self.history_check_ids) != len(set(self.history_check_ids)):
            raise ValueError("provider health history references must be unique")
        if any(not value.strip() for value in self.history_check_ids):
            raise ValueError("provider health history references cannot be empty")
        if self.status is not _report_status(self.alerts):
            raise ValueError("provider health report status is inconsistent")
        expected = _stable_hash(
            _report_content(
                run_id=self.run_id,
                evaluated_at=self.evaluated_at,
                status=self.status,
                alerts=self.alerts,
                history_check_ids=self.history_check_ids,
                policy=self.policy,
                framework_version=self.framework_version,
                contract_monitor_version=self.contract_monitor_version,
                implementation_version=self.implementation_version,
            )
        )
        if self.report_id != expected:
            raise ValueError("provider health report hash does not match its content")


class ProviderHealthRepository(Protocol):
    def provider_contract_observations(
        self,
        query: ProviderBaselineQuery,
    ) -> tuple[ProviderContractObservation, ...]: ...


@dataclass(frozen=True, slots=True)
class ProviderHealthAssessor:
    repository: ProviderHealthRepository
    policy: ProviderHealthPolicy = ProviderHealthPolicy()

    def assess(self, run: ProviderContractRun) -> ProviderHealthReport:
        if not run.checks:
            raise ValueError("provider health assessment requires contract checks")
        scopes = tuple(sorted({_scope(check) for check in run.checks}))
        if len(scopes) != len(run.checks):
            raise ValueError("provider health assessment requires unique run scopes")
        query = ProviderBaselineQuery(
            period_start=run.completed_at
            - timedelta(days=self.policy.history_window_days),
            period_end=run.completed_at,
            expected_interval_days=1,
            scopes=scopes,
        )
        loaded = self.repository.provider_contract_observations(query)
        if len(loaded) != len({item.check_id for item in loaded}):
            raise ValueError("provider health repository returned duplicate checks")
        if any(
            item.scope not in set(scopes)
            or not query.period_start <= item.checked_at <= query.period_end
            for item in loaded
        ):
            raise ValueError("provider health repository returned out-of-scope history")
        observations = {item.check_id: item for item in loaded}
        for check in run.checks:
            current = _observation_from_check(
                check,
                implementation_version=run.implementation_version,
            )
            stored = observations.get(check.check_id)
            if stored is not None and stored != current:
                raise ValueError("stored provider check does not match the current run")
            observations[check.check_id] = current
        ordered = tuple(
            sorted(observations.values(), key=lambda item: (item.checked_at, item.check_id))
        )
        alerts = tuple(
            sorted(
                (
                    alert
                    for check in run.checks
                    if (
                        alert := _alert_for(
                            check,
                            _history_for_check(ordered, check),
                            self.policy,
                        )
                    )
                    is not None
                ),
                key=lambda item: item.scope,
            )
        )
        history_check_ids = tuple(sorted(observations))
        status = _report_status(alerts)
        content = _report_content(
            run_id=run.run_id,
            evaluated_at=run.completed_at,
            status=status,
            alerts=alerts,
            history_check_ids=history_check_ids,
            policy=self.policy,
            framework_version=FRAMEWORK_VERSION,
            contract_monitor_version=run.implementation_version,
            implementation_version=PROVIDER_HEALTH_POLICY_VERSION,
        )
        return ProviderHealthReport(
            report_id=_stable_hash(content),
            run_id=run.run_id,
            evaluated_at=run.completed_at,
            status=status,
            alerts=alerts,
            history_check_ids=history_check_ids,
            policy=self.policy,
            contract_monitor_version=run.implementation_version,
        )


def provider_health_json(report: ProviderHealthReport) -> dict[str, object]:
    retention_until = report.evaluated_at + timedelta(
        days=report.policy.artifact_retention_days
    )
    return {
        "report_id": report.report_id,
        "run_id": report.run_id,
        "evaluated_at": report.evaluated_at.isoformat(),
        "status": report.status.value,
        "framework_version": report.framework_version,
        "contract_monitor_version": report.contract_monitor_version,
        "implementation_version": report.implementation_version,
        "history_check_ids": list(report.history_check_ids),
        "policy": _policy_document(report.policy),
        "retention": {
            "artifact_retention_days": report.policy.artifact_retention_days,
            "retain_until": retention_until.isoformat(),
            "database_history": "retain_until_archived_and_verified",
        },
        "alerts": [_alert_document(alert) for alert in report.alerts],
        "boundaries": {
            "notification_engine_used": False,
            "external_delivery_used": False,
            "trading_effect": False,
        },
    }


def serialize_provider_health(report: ProviderHealthReport) -> str:
    return json.dumps(provider_health_json(report), indent=2, sort_keys=True)


def render_provider_health_markdown(report: ProviderHealthReport) -> str:
    acknowledgement_count = sum(
        alert.acknowledgement_required for alert in report.alerts
    )
    lines = [
        "# Provider Contract Health",
        "",
        f"- Status: `{report.status.value}`",
        f"- Owner: `{report.policy.owner}`",
        f"- Run ID: `{report.run_id}`",
        f"- Report ID: `{report.report_id}`",
        f"- Framework: `{report.framework_version}`",
        f"- Contract monitor: `{report.contract_monitor_version}`",
        f"- Acknowledgements required: `{acknowledgement_count}`",
        f"- Artifact retention: `{report.policy.artifact_retention_days} days`",
        "",
        "| Provider | Dataset | Market | Subject | Condition | Severity | Streak | Ack |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    for alert in report.alerts:
        lines.append(
            f"| {alert.scope.provider} | {alert.scope.dataset} | "
            f"{alert.scope.market.value} | {alert.scope.subject} | "
            f"{alert.condition.value} | {alert.severity.value} | "
            f"{alert.consecutive_count} | "
            f"{'required' if alert.acknowledgement_required else 'not required'} |"
        )
    lines.extend(["", "## Operator Actions", ""])
    for alert in report.alerts:
        lines.append(f"### {alert.scope.provider} / {alert.scope.dataset}")
        lines.append("")
        lines.append(f"- Alert ID: `{alert.alert_id}`")
        lines.append(f"- Alert fingerprint: `{alert.alert_fingerprint}`")
        lines.append(f"- Owner: `{alert.owner}`")
        for step in alert.recovery_steps:
            lines.append(f"- {step}")
        lines.append("")
    lines.extend(
        [
            "This is a repository operations report. It does not use the "
            "Notification Engine, change provider trust, alter PIT readiness, or "
            "trigger trading behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def provider_health_annotations(report: ProviderHealthReport) -> tuple[str, ...]:
    command = {
        ProviderHealthSeverity.INFO: "notice",
        ProviderHealthSeverity.WARNING: "warning",
        ProviderHealthSeverity.CRITICAL: "error",
    }
    return tuple(
        f"::{command[alert.severity]} title=Provider contract health::"
        f"{_github_escape(alert.scope.provider)}/"
        f"{_github_escape(alert.scope.dataset)}/"
        f"{_github_escape(alert.scope.market.value)}/"
        f"{_github_escape(alert.scope.subject)}: "
        f"{alert.condition.value} (streak={alert.consecutive_count}, "
        f"alert={alert.alert_id[:12]}, fingerprint={alert.alert_fingerprint[:12]})"
        for alert in report.alerts
    )


def _alert_for(
    check: ProviderContractCheck,
    observations: tuple[ProviderContractObservation, ...],
    policy: ProviderHealthPolicy,
) -> ProviderHealthAlert | None:
    current = next(
        (item for item in observations if item.check_id == check.check_id),
        None,
    )
    if current is None:
        raise ValueError("provider health history is missing the current check")
    prior = tuple(item for item in observations if item.check_id != check.check_id)
    if check.status is ProviderContractStatus.DEFECT:
        condition = ProviderHealthCondition.IMPLEMENTATION_DEFECT
        severity = ProviderHealthSeverity.CRITICAL
        relevant = _trailing(observations, ProviderContractStatus.DEFECT)
    elif check.status is ProviderContractStatus.UNAVAILABLE:
        relevant = _trailing(observations, ProviderContractStatus.UNAVAILABLE)
        if len(relevant) >= policy.repeated_unavailable_threshold:
            condition = ProviderHealthCondition.REPEATED_UNAVAILABLE
            severity = ProviderHealthSeverity.WARNING
        else:
            condition = ProviderHealthCondition.ONE_OFF_UNAVAILABLE
            severity = ProviderHealthSeverity.INFO
    elif check.status is ProviderContractStatus.DEGRADED:
        relevant = _trailing(observations, ProviderContractStatus.DEGRADED)
        if len(relevant) >= policy.repeated_degradation_threshold:
            condition = ProviderHealthCondition.REPEATED_DEGRADATION
            severity = ProviderHealthSeverity.WARNING
        else:
            condition = ProviderHealthCondition.ONE_OFF_DEGRADATION
            severity = ProviderHealthSeverity.INFO
    elif prior and prior[-1].status is not ProviderContractStatus.HEALTHY:
        condition = ProviderHealthCondition.RECOVERED
        severity = ProviderHealthSeverity.INFO
        relevant = (prior[-1], current)
    else:
        return None
    recovery_steps = _recovery_steps(condition)
    related_check_ids = tuple(item.check_id for item in relevant)
    acknowledgement_required = severity in {
        ProviderHealthSeverity.WARNING,
        ProviderHealthSeverity.CRITICAL,
    }
    alert_fingerprint = _alert_fingerprint(
        _scope(check),
        condition,
        policy.version,
    )
    document = _alert_content(
        alert_fingerprint=alert_fingerprint,
        scope=_scope(check),
        condition=condition,
        severity=severity,
        observed_status=check.status,
        consecutive_count=len(relevant),
        related_check_ids=related_check_ids,
        first_seen_at=relevant[0].checked_at,
        last_seen_at=relevant[-1].checked_at,
        owner=policy.owner,
        acknowledgement_required=acknowledgement_required,
        recovery_steps=recovery_steps,
        policy_version=policy.version,
    )
    return ProviderHealthAlert(
        alert_id=_stable_hash(document),
        alert_fingerprint=alert_fingerprint,
        scope=_scope(check),
        condition=condition,
        severity=severity,
        observed_status=check.status,
        consecutive_count=len(relevant),
        related_check_ids=related_check_ids,
        first_seen_at=relevant[0].checked_at,
        last_seen_at=relevant[-1].checked_at,
        owner=policy.owner,
        acknowledgement_required=acknowledgement_required,
        recovery_steps=recovery_steps,
        policy_version=policy.version,
    )


def _trailing(
    observations: tuple[ProviderContractObservation, ...],
    status: ProviderContractStatus,
) -> tuple[ProviderContractObservation, ...]:
    selected: list[ProviderContractObservation] = []
    for observation in reversed(observations):
        if observation.status is not status:
            break
        selected.append(observation)
    return tuple(reversed(selected))


def _history_for_check(
    observations: tuple[ProviderContractObservation, ...],
    check: ProviderContractCheck,
) -> tuple[ProviderContractObservation, ...]:
    scope = _scope(check)
    current = next(item for item in observations if item.check_id == check.check_id)
    prior = tuple(
        item
        for item in observations
        if item.scope == scope
        and item.check_id != check.check_id
        and item.checked_at <= check.checked_at
    )
    return (*prior, current)


def _scope(check: ProviderContractCheck) -> ProviderBaselineScope:
    return ProviderBaselineScope(
        provider=check.provider,
        dataset=check.dataset,
        market=check.market,
        subject=check.subject,
    )


def _observation_from_check(
    check: ProviderContractCheck,
    *,
    implementation_version: str,
) -> ProviderContractObservation:
    return ProviderContractObservation(
        check_id=check.check_id,
        run_id=check.run_id,
        scope=_scope(check),
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
        implementation_version=implementation_version,
    )


def _report_status(alerts: tuple[ProviderHealthAlert, ...]) -> ProviderHealthStatus:
    severities = {alert.severity for alert in alerts}
    if ProviderHealthSeverity.CRITICAL in severities:
        return ProviderHealthStatus.BLOCKING
    if ProviderHealthSeverity.WARNING in severities:
        return ProviderHealthStatus.ACTION_REQUIRED
    if ProviderHealthSeverity.INFO in severities:
        return ProviderHealthStatus.WATCH
    return ProviderHealthStatus.NORMAL


def _report_content(
    *,
    run_id: str,
    evaluated_at: datetime,
    status: ProviderHealthStatus,
    alerts: tuple[ProviderHealthAlert, ...],
    history_check_ids: tuple[str, ...],
    policy: ProviderHealthPolicy,
    framework_version: str,
    contract_monitor_version: str,
    implementation_version: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "evaluated_at": evaluated_at.isoformat(),
        "status": status.value,
        "alerts": [_alert_document(alert) for alert in alerts],
        "history_check_ids": history_check_ids,
        "policy": _policy_document(policy),
        "framework_version": framework_version,
        "contract_monitor_version": contract_monitor_version,
        "implementation_version": implementation_version,
    }


def _alert_document(alert: ProviderHealthAlert) -> dict[str, object]:
    return {
        "alert_id": alert.alert_id,
        **_alert_content(
            alert_fingerprint=alert.alert_fingerprint,
            scope=alert.scope,
            condition=alert.condition,
            severity=alert.severity,
            observed_status=alert.observed_status,
            consecutive_count=alert.consecutive_count,
            related_check_ids=alert.related_check_ids,
            first_seen_at=alert.first_seen_at,
            last_seen_at=alert.last_seen_at,
            owner=alert.owner,
            acknowledgement_required=alert.acknowledgement_required,
            recovery_steps=alert.recovery_steps,
            policy_version=alert.policy_version,
        ),
    }


def _alert_content(
    *,
    alert_fingerprint: str,
    scope: ProviderBaselineScope,
    condition: ProviderHealthCondition,
    severity: ProviderHealthSeverity,
    observed_status: ProviderContractStatus,
    consecutive_count: int,
    related_check_ids: tuple[str, ...],
    first_seen_at: datetime,
    last_seen_at: datetime,
    owner: str,
    acknowledgement_required: bool,
    recovery_steps: tuple[str, ...],
    policy_version: str,
) -> dict[str, object]:
    return {
        "alert_fingerprint": alert_fingerprint,
        "scope": _scope_document(scope),
        "condition": condition.value,
        "severity": severity.value,
        "observed_status": observed_status.value,
        "consecutive_count": consecutive_count,
        "related_check_ids": list(related_check_ids),
        "first_seen_at": first_seen_at.isoformat(),
        "last_seen_at": last_seen_at.isoformat(),
        "owner": owner,
        "acknowledgement_required": acknowledgement_required,
        "recovery_steps": list(recovery_steps),
        "policy_version": policy_version,
    }


def _scope_document(scope: ProviderBaselineScope) -> dict[str, str]:
    return {
        "provider": scope.provider,
        "dataset": scope.dataset,
        "market": scope.market.value,
        "subject": scope.subject,
    }


def _policy_document(policy: ProviderHealthPolicy) -> dict[str, object]:
    return {
        "history_window_days": policy.history_window_days,
        "repeated_degradation_threshold": policy.repeated_degradation_threshold,
        "repeated_unavailable_threshold": policy.repeated_unavailable_threshold,
        "artifact_retention_days": policy.artifact_retention_days,
        "owner": policy.owner,
        "version": policy.version,
    }


def _alert_fingerprint(
    scope: ProviderBaselineScope,
    condition: ProviderHealthCondition,
    policy_version: str,
) -> str:
    return _stable_hash(
        {
            "scope": _scope_document(scope),
            "condition": condition.value,
            "policy_version": policy_version,
        }
    )


def _recovery_steps(condition: ProviderHealthCondition) -> tuple[str, ...]:
    if condition is ProviderHealthCondition.IMPLEMENTATION_DEFECT:
        return (
            "Acknowledge the failed GitHub Actions run before the next scheduled probe",
            "Inspect required fields, adapter parsing, and the sanitized contract artifact",
            "Fix and rerun the monitor; do not weaken the contract to make the check pass",
        )
    if condition is ProviderHealthCondition.REPEATED_UNAVAILABLE:
        return (
            "Acknowledge the repeated provider outage or permission restriction",
            "Confirm provider capability and endpoint status outside Tong Quant",
            "Preserve the gap and evaluate an approved provider fallback",
        )
    if condition is ProviderHealthCondition.REPEATED_DEGRADATION:
        return (
            "Acknowledge the persistent limitation in the current Actions run",
            "Review the longitudinal baseline and provider limitation codes",
            "Do not promote trust or PIT readiness without independent evidence",
        )
    if condition is ProviderHealthCondition.ONE_OFF_UNAVAILABLE:
        return (
            "Allow the next scheduled probe to distinguish transient downtime",
            "Escalate only if the unavailable streak reaches policy threshold",
        )
    if condition is ProviderHealthCondition.ONE_OFF_DEGRADATION:
        return (
            "Record the declared limitation without treating it as a code defect",
            "Review again if degradation persists across the policy threshold",
        )
    return (
        "Confirm the next scheduled run remains healthy",
        "Keep prior failure observations for audit and continuity analysis",
    )


def _github_escape(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def _stable_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ProviderHealthAlert",
    "ProviderHealthAssessor",
    "ProviderHealthCondition",
    "ProviderHealthPolicy",
    "ProviderHealthReport",
    "ProviderHealthRepository",
    "ProviderHealthSeverity",
    "ProviderHealthStatus",
    "provider_health_annotations",
    "provider_health_json",
    "render_provider_health_markdown",
    "serialize_provider_health",
]
