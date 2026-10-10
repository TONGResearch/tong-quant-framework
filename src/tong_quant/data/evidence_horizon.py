import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from tong_quant.data.calibration.models import CalibrationDataset
from tong_quant.data.evidence_bundle import (
    ProviderScopeEvidenceSummary,
    verify_provider_evidence_document,
)
from tong_quant.data.providers.contracts import (
    ProviderContractRunOrigin,
    valid_provider_run_origin_reference,
)
from tong_quant.data.providers.yahoo import YAHOO_DAILY_BARS_DATASET
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    DATABASE_SCHEMA_VERSION,
    FRAMEWORK_VERSION,
    PROVIDER_EVIDENCE_HORIZON_VERSION,
)


class EvidenceHorizonStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


@dataclass(frozen=True, slots=True, order=True)
class RequiredEvidenceScope:
    provider: str
    dataset: str
    market: str
    subject: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (self.provider, self.dataset, self.market, self.subject)
        ):
            raise ValueError("required evidence scope fields cannot be empty")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return self.provider, self.dataset, self.market, self.subject


@dataclass(frozen=True, slots=True)
class EvidenceHorizonPolicy:
    required_scopes: tuple[RequiredEvidenceScope, ...]
    minimum_observation_days: int = 84
    minimum_contract_checks: int = 8
    require_scheduled_provenance: bool = True
    version: str = PROVIDER_EVIDENCE_HORIZON_VERSION

    def __post_init__(self) -> None:
        if not self.required_scopes:
            raise ValueError("evidence horizon policy requires provider scopes")
        if self.required_scopes != tuple(sorted(self.required_scopes)):
            raise ValueError("required evidence scopes must be sorted")
        if len(self.required_scopes) != len(set(self.required_scopes)):
            raise ValueError("required evidence scopes must be unique")
        if min(self.minimum_observation_days, self.minimum_contract_checks) < 1:
            raise ValueError("evidence horizon thresholds must be positive")
        if not self.version.strip():
            raise ValueError("evidence horizon policy version is required")


@dataclass(frozen=True, slots=True)
class EvidenceScopeHorizonAssessment:
    scope: RequiredEvidenceScope
    status: EvidenceHorizonStatus
    observation_days: float
    contract_check_count: int
    remaining_observation_days: float
    remaining_contract_checks: int
    baseline_manifest_id: str | None
    baseline_observation_days: float | None
    expected_periods: int | None
    observed_periods: int | None
    successful_observation_ratio: float | None
    field_coverage_ratio: float | None
    continuity_ratio: float | None
    blockers: tuple[str, ...]
    scheduled_contract_check_count: int | None = None

    def __post_init__(self) -> None:
        counts = (
            self.observation_days,
            self.contract_check_count,
            self.remaining_observation_days,
            self.remaining_contract_checks,
        )
        if min(counts) < 0:
            raise ValueError("evidence horizon counts cannot be negative")
        if (
            self.scheduled_contract_check_count is not None
            and self.scheduled_contract_check_count < 0
        ):
            raise ValueError("scheduled provider check count cannot be negative")
        if self.status is EvidenceHorizonStatus.COMPLETE and self.blockers:
            raise ValueError("complete evidence scope cannot have blockers")
        if self.status is not EvidenceHorizonStatus.COMPLETE and not self.blockers:
            raise ValueError("incomplete evidence scope requires blockers")


@dataclass(frozen=True, slots=True)
class ProviderEvidenceHorizonReport:
    report_id: str
    bundle_id: str
    bundle_as_of: datetime
    assessments: tuple[EvidenceScopeHorizonAssessment, ...]
    missing_tables: tuple[str, ...]
    eligible_for_readiness_reassessment: bool
    blockers: tuple[str, ...]
    policy: EvidenceHorizonPolicy
    framework_version: str = FRAMEWORK_VERSION
    database_schema_version: str = DATABASE_SCHEMA_VERSION
    implementation_version: str = PROVIDER_EVIDENCE_HORIZON_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.bundle_as_of, "provider evidence horizon bundle_as_of")
        if len(self.report_id) != 64 or len(self.bundle_id) != 64:
            raise ValueError("evidence horizon identities must be SHA-256 digests")
        if tuple(item.scope for item in self.assessments) != self.policy.required_scopes:
            raise ValueError("evidence horizon assessments must match policy scopes")
        if self.missing_tables != tuple(sorted(set(self.missing_tables))):
            raise ValueError("evidence horizon missing tables must be sorted and unique")
        expected = _stable_hash(_report_content(self, include_report_id=False))
        if self.report_id != expected:
            raise ValueError("evidence horizon report hash does not match content")
        expected_eligible = not self.blockers and all(
            item.status is EvidenceHorizonStatus.COMPLETE
            for item in self.assessments
        )
        if self.eligible_for_readiness_reassessment != expected_eligible:
            raise ValueError("evidence horizon eligibility is inconsistent")


def required_provider_evidence_scopes(
    *,
    china_symbol: str = "600000",
    us_symbol: str = "MSFT",
    hong_kong_symbol: str = "0700.HK",
    malaysia_symbol: str = "1155.KL",
) -> tuple[RequiredEvidenceScope, ...]:
    scopes = (
        RequiredEvidenceScope(
            "cninfo_direct",
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES.value,
            Market.CHINA_A.value,
            china_symbol,
        ),
        RequiredEvidenceScope(
            "cninfo_via_akshare",
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES.value,
            Market.CHINA_A.value,
            china_symbol,
        ),
        RequiredEvidenceScope(
            "yahoo_finance",
            YAHOO_DAILY_BARS_DATASET,
            Market.HONG_KONG.value,
            hong_kong_symbol,
        ),
        RequiredEvidenceScope(
            "yahoo_finance",
            YAHOO_DAILY_BARS_DATASET,
            Market.MALAYSIA.value,
            malaysia_symbol,
        ),
        RequiredEvidenceScope(
            "yahoo_finance",
            YAHOO_DAILY_BARS_DATASET,
            Market.US.value,
            us_symbol,
        ),
    )
    return tuple(sorted(scopes))


def evaluate_provider_evidence_horizon(
    document: dict[str, object],
    *,
    policy: EvidenceHorizonPolicy | None = None,
    report_version: str = PROVIDER_EVIDENCE_HORIZON_VERSION,
) -> ProviderEvidenceHorizonReport:
    verify_provider_evidence_document(document)
    selected_policy = policy or EvidenceHorizonPolicy(
        required_scopes=required_provider_evidence_scopes()
    )
    summaries = {
        summary.identity: summary
        for summary in _scope_summaries(document.get("scope_summaries"))
    }
    scheduled = (
        _scheduled_scope_observations(document.get("tables"))
        if selected_policy.require_scheduled_provenance
        else {}
    )
    baseline_horizons = _baseline_horizons(document.get("tables"))
    assessments = tuple(
        _assess_scope(
            scope,
            summaries.get(scope.identity),
            baseline_horizons,
            selected_policy,
            scheduled.get(scope.identity),
        )
        for scope in selected_policy.required_scopes
    )
    missing_tables = _string_tuple(document.get("missing_tables"), "missing_tables")
    blockers = tuple(
        [
            *(f"required operational evidence table is missing: {item}" for item in missing_tables),
            *(
                f"required evidence scope is not complete: {'/'.join(item.scope.identity)}"
                for item in assessments
                if item.status is not EvidenceHorizonStatus.COMPLETE
            ),
        ]
    )
    bundle_id = _required_string(document, "bundle_id")
    bundle_as_of = _aware_datetime(_required_string(document, "as_of"), "as_of")
    schema_version = _required_string(document, "database_schema_version")
    eligible = not blockers
    report_without_id = _report_values_content(
        report_id="",
        include_report_id=False,
        bundle_id=bundle_id,
        bundle_as_of=bundle_as_of,
        assessments=assessments,
        missing_tables=missing_tables,
        eligible_for_readiness_reassessment=eligible,
        blockers=blockers,
        policy=selected_policy,
        database_schema_version=schema_version,
        implementation_version=report_version,
    )
    return ProviderEvidenceHorizonReport(
        report_id=_stable_hash(report_without_id),
        bundle_id=bundle_id,
        bundle_as_of=bundle_as_of,
        assessments=assessments,
        missing_tables=missing_tables,
        eligible_for_readiness_reassessment=eligible,
        blockers=blockers,
        policy=selected_policy,
        database_schema_version=schema_version,
        implementation_version=report_version,
    )


def provider_evidence_horizon_json(
    report: ProviderEvidenceHorizonReport,
) -> dict[str, object]:
    return _report_content(report, include_report_id=True)


def serialize_provider_evidence_horizon(
    report: ProviderEvidenceHorizonReport,
) -> str:
    return json.dumps(provider_evidence_horizon_json(report), indent=2, sort_keys=True)


def render_provider_evidence_horizon_markdown(
    report: ProviderEvidenceHorizonReport,
) -> str:
    lines = [
        "# Provider Evidence Horizon Audit",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Evidence bundle: `{report.bundle_id}`",
        f"- Bundle as of: `{report.bundle_as_of.isoformat()}`",
        "- Eligible for separate PIT readiness reassessment: "
        f"`{str(report.eligible_for_readiness_reassessment).lower()}`",
        f"- Required horizon: `{report.policy.minimum_observation_days} days`",
        f"- Required scheduled checks per scope: `{report.policy.minimum_contract_checks}`",
        "",
        "## Required Scopes",
        "",
        "| Provider | Dataset | Market | Subject | Status | Days | Checks | Scheduled | "
        "Remaining | Baseline days | Observed/expected | Continuity | "
        "Field coverage |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report.assessments:
        periods = _fraction_text(item.observed_periods, item.expected_periods)
        remaining = (
            f"{item.remaining_observation_days:.1f}d/"
            f"{item.remaining_contract_checks} checks"
        )
        lines.append(
            f"| {item.scope.provider} | {item.scope.dataset} | "
            f"{item.scope.market} | {item.scope.subject} | {item.status.value} | "
            f"{item.observation_days:.1f} | {item.contract_check_count} | "
            f"{item.scheduled_contract_check_count or 0} | "
            f"{remaining} | {_days_text(item.baseline_observation_days)} | "
            f"{periods} | {_ratio_text(item.continuity_ratio)} | "
            f"{_ratio_text(item.field_coverage_ratio)} |"
        )
    lines.extend(["", "## Blocking Conditions", ""])
    lines.extend(f"- {item}" for item in report.blockers)
    if not report.blockers:
        lines.append("- None. The evidence horizon may enter a separate human readiness review.")
    lines.extend(
        [
            "",
            "Completing this horizon does not promote provider trust, PIT readiness, "
            "research validity, or trading readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def _assess_scope(
    scope: RequiredEvidenceScope,
    summary: ProviderScopeEvidenceSummary | None,
    baseline_horizons: dict[str, float],
    policy: EvidenceHorizonPolicy,
    scheduled_observations: tuple[int, float] | None,
) -> EvidenceScopeHorizonAssessment:
    if summary is None:
        return EvidenceScopeHorizonAssessment(
            scope=scope,
            status=EvidenceHorizonStatus.MISSING,
            observation_days=0,
            contract_check_count=0,
            remaining_observation_days=float(policy.minimum_observation_days),
            remaining_contract_checks=policy.minimum_contract_checks,
            baseline_manifest_id=None,
            baseline_observation_days=None,
            expected_periods=None,
            observed_periods=None,
            successful_observation_ratio=None,
            field_coverage_ratio=None,
            continuity_ratio=None,
            blockers=("required provider scope is absent from the evidence bundle",),
            scheduled_contract_check_count=(
                0 if policy.require_scheduled_provenance else None
            ),
        )
    blockers: list[str] = []
    scheduled_count, scheduled_days = scheduled_observations or (0, 0.0)
    observation_days = (
        scheduled_days
        if policy.require_scheduled_provenance
        else summary.observation_days
    )
    gate_count = (
        scheduled_count
        if policy.require_scheduled_provenance
        else summary.contract_check_count
    )
    if observation_days < policy.minimum_observation_days:
        blockers.append(
            f"observation horizon is {observation_days:.1f} days; "
            f"requires at least {policy.minimum_observation_days}"
        )
    if gate_count < policy.minimum_contract_checks:
        blockers.append(
            f"{'scheduled ' if policy.require_scheduled_provenance else ''}"
            f"contract check count is {gate_count}; "
            f"requires at least {policy.minimum_contract_checks}"
        )
    baseline_observation_days = (
        baseline_horizons.get(summary.baseline_manifest_id)
        if summary.baseline_manifest_id is not None
        else None
    )
    baseline_values = (
        summary.baseline_manifest_id,
        baseline_observation_days,
        summary.expected_periods,
        summary.observed_periods,
        summary.successful_observation_ratio,
        summary.field_coverage_ratio,
        summary.continuity_ratio,
    )
    if any(value is None for value in baseline_values):
        blockers.append("longitudinal baseline measurements are incomplete")
    if (
        baseline_observation_days is not None
        and baseline_observation_days < policy.minimum_observation_days
    ):
        blockers.append(
            f"baseline horizon is {baseline_observation_days:.1f} days; "
            f"requires at least {policy.minimum_observation_days}"
        )
    if (
        summary.expected_periods is not None
        and summary.expected_periods < policy.minimum_contract_checks
    ):
        blockers.append(
            f"baseline expected periods are {summary.expected_periods}; "
            f"requires at least {policy.minimum_contract_checks}"
        )
    if (
        summary.observed_periods is not None
        and summary.observed_periods < policy.minimum_contract_checks
    ):
        blockers.append(
            f"baseline observed periods are {summary.observed_periods}; "
            f"requires at least {policy.minimum_contract_checks}"
        )
    return EvidenceScopeHorizonAssessment(
        scope=scope,
        status=(
            EvidenceHorizonStatus.INCOMPLETE
            if blockers
            else EvidenceHorizonStatus.COMPLETE
        ),
        observation_days=observation_days,
        contract_check_count=summary.contract_check_count,
        remaining_observation_days=max(
            0.0, policy.minimum_observation_days - observation_days
        ),
        remaining_contract_checks=max(
            0, policy.minimum_contract_checks - gate_count
        ),
        baseline_manifest_id=summary.baseline_manifest_id,
        baseline_observation_days=baseline_observation_days,
        expected_periods=summary.expected_periods,
        observed_periods=summary.observed_periods,
        successful_observation_ratio=summary.successful_observation_ratio,
        field_coverage_ratio=summary.field_coverage_ratio,
        continuity_ratio=summary.continuity_ratio,
        blockers=tuple(blockers),
        scheduled_contract_check_count=(
            scheduled_count if policy.require_scheduled_provenance else None
        ),
    )


def _scope_summaries(value: object) -> tuple[ProviderScopeEvidenceSummary, ...]:
    if not isinstance(value, list):
        raise ValueError("provider evidence scope summaries must be a list")
    summaries = tuple(_scope_summary(item) for item in value)
    if tuple(item.identity for item in summaries) != tuple(
        sorted(item.identity for item in summaries)
    ):
        raise ValueError("provider evidence scope summaries must be sorted")
    return summaries


def _scope_summary(value: object) -> ProviderScopeEvidenceSummary:
    if not isinstance(value, dict):
        raise ValueError("provider evidence scope summary must be an object")
    return ProviderScopeEvidenceSummary(
        provider=_required_string(value, "provider"),
        dataset=_required_string(value, "dataset"),
        market=_required_string(value, "market"),
        subject=_required_string(value, "subject"),
        first_observed_at=_optional_string(value, "first_observed_at"),
        last_observed_at=_optional_string(value, "last_observed_at"),
        observation_days=_required_float(value, "observation_days"),
        contract_check_count=_required_int(value, "contract_check_count"),
        baseline_manifest_id=_optional_string(value, "baseline_manifest_id"),
        expected_periods=_optional_int(value, "expected_periods"),
        observed_periods=_optional_int(value, "observed_periods"),
        successful_observation_ratio=_optional_float(
            value, "successful_observation_ratio"
        ),
        field_coverage_ratio=_optional_float(value, "field_coverage_ratio"),
        continuity_ratio=_optional_float(value, "continuity_ratio"),
    )


def _scheduled_scope_observations(
    tables: object,
) -> dict[tuple[str, str, str, str], tuple[int, float]]:
    runs = _evidence_table_rows(tables, "provider_contract_runs")
    checks = _evidence_table_rows(tables, "provider_contract_checks")
    scheduled_run_ids: set[str] = set()
    seen_references: set[str] = set()
    for row in runs:
        if row.get("run_origin") != ProviderContractRunOrigin.SCHEDULED.value:
            continue
        run_id = _required_string(row, "run_id")
        reference = _required_string(row, "origin_reference")
        if not valid_provider_run_origin_reference(reference):
            raise ValueError("scheduled provider run origin reference is invalid")
        if reference in seen_references:
            raise ValueError("scheduled provider run origin reference is duplicated")
        seen_references.add(reference)
        scheduled_run_ids.add(run_id)

    scope_times: dict[tuple[str, str, str, str], dict[str, datetime]] = {}
    for row in checks:
        run_id = _required_string(row, "run_id")
        if run_id not in scheduled_run_ids:
            continue
        dataset = _required_string(row, "dataset")
        scope = (
            _required_string(row, "provider"),
            {
                "china_disclosures": "financial_publication_dates",
                "daily_bars": "global_daily_bars",
            }.get(dataset, dataset),
            _required_string(row, "market"),
            _required_string(row, "subject"),
        )
        checked_at = _aware_datetime(
            _required_string(row, "checked_at"), "checked_at"
        )
        run_times = scope_times.setdefault(scope, {})
        previous = run_times.get(run_id)
        if previous is None or checked_at < previous:
            run_times[run_id] = checked_at

    observations = {}
    for scope, run_times in scope_times.items():
        times = sorted(run_times.values())
        observations[scope] = (
            len(times),
            round((times[-1] - times[0]).total_seconds() / 86_400, 6),
        )
    return observations


def _evidence_table_rows(
    tables: object, table_name: str
) -> list[dict[str, object]]:
    if not isinstance(tables, list):
        raise ValueError("provider evidence tables must be a list")
    table = next(
        (
            item
            for item in tables
            if isinstance(item, dict) and item.get("table") == table_name
        ),
        None,
    )
    if table is None:
        return []
    columns = table.get("columns")
    rows = table.get("rows")
    if not isinstance(columns, list) or not all(
        isinstance(column, str) for column in columns
    ):
        raise ValueError("provider evidence table columns are invalid")
    if not isinstance(rows, list):
        raise ValueError("provider evidence table rows are invalid")
    result = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ValueError("provider evidence table row width is invalid")
        result.append(dict(zip(columns, row, strict=True)))
    return result


def _baseline_horizons(value: object) -> dict[str, float]:
    if not isinstance(value, list):
        raise ValueError("provider evidence tables must be a list")
    manifest_table = next(
        (
            item
            for item in value
            if isinstance(item, dict)
            and item.get("table") == "provider_baseline_manifests"
        ),
        None,
    )
    if manifest_table is None:
        return {}
    columns = manifest_table.get("columns")
    rows = manifest_table.get("rows")
    if not isinstance(columns, list) or not all(isinstance(item, str) for item in columns):
        raise ValueError("provider baseline manifest columns are invalid")
    if not isinstance(rows, list) or not all(isinstance(item, list) for item in rows):
        raise ValueError("provider baseline manifest rows are invalid")
    required = ("manifest_id", "period_start", "period_end")
    if any(field not in columns for field in required):
        raise ValueError("provider baseline manifest horizon columns are missing")
    indexes = {field: columns.index(field) for field in required}
    horizons: dict[str, float] = {}
    for row in rows:
        if len(row) != len(columns):
            raise ValueError("provider baseline manifest row width is invalid")
        manifest_id = row[indexes["manifest_id"]]
        period_start = row[indexes["period_start"]]
        period_end = row[indexes["period_end"]]
        if not all(isinstance(item, str) for item in (manifest_id, period_start, period_end)):
            raise ValueError("provider baseline manifest horizon values are invalid")
        start = _aware_datetime(period_start, "baseline.period_start")
        end = _aware_datetime(period_end, "baseline.period_end")
        if end <= start:
            raise ValueError("provider baseline period_end must follow period_start")
        if manifest_id in horizons:
            raise ValueError("provider baseline manifest identity must be unique")
        horizons[manifest_id] = round((end - start).total_seconds() / 86_400, 6)
    return horizons


def _report_content(
    report: ProviderEvidenceHorizonReport,
    *,
    include_report_id: bool,
) -> dict[str, object]:
    return _report_values_content(
        report_id=report.report_id,
        include_report_id=include_report_id,
        bundle_id=report.bundle_id,
        bundle_as_of=report.bundle_as_of,
        assessments=report.assessments,
        missing_tables=report.missing_tables,
        eligible_for_readiness_reassessment=(
            report.eligible_for_readiness_reassessment
        ),
        blockers=report.blockers,
        policy=report.policy,
        framework_version=report.framework_version,
        database_schema_version=report.database_schema_version,
        implementation_version=report.implementation_version,
    )


def _report_values_content(
    *,
    report_id: str,
    include_report_id: bool,
    bundle_id: str,
    bundle_as_of: datetime,
    assessments: tuple[EvidenceScopeHorizonAssessment, ...],
    missing_tables: tuple[str, ...],
    eligible_for_readiness_reassessment: bool,
    blockers: tuple[str, ...],
    policy: EvidenceHorizonPolicy,
    framework_version: str = FRAMEWORK_VERSION,
    database_schema_version: str = DATABASE_SCHEMA_VERSION,
    implementation_version: str = PROVIDER_EVIDENCE_HORIZON_VERSION,
) -> dict[str, object]:
    document: dict[str, object] = {
        "bundle_id": bundle_id,
        "bundle_as_of": bundle_as_of.isoformat(),
        "assessments": [_assessment_document(item) for item in assessments],
        "missing_tables": list(missing_tables),
        "eligible_for_readiness_reassessment": eligible_for_readiness_reassessment,
        "blockers": list(blockers),
        "policy": {
            "minimum_observation_days": policy.minimum_observation_days,
            "minimum_contract_checks": policy.minimum_contract_checks,
            "required_scopes": [_scope_document(item) for item in policy.required_scopes],
            "version": policy.version,
        },
        "framework_version": framework_version,
        "database_schema_version": database_schema_version,
        "implementation_version": implementation_version,
    }
    if policy.require_scheduled_provenance:
        policy_document = document["policy"]
        assert isinstance(policy_document, dict)
        policy_document["require_scheduled_provenance"] = True
    if include_report_id:
        document["report_id"] = report_id
    return document


def _assessment_document(item: EvidenceScopeHorizonAssessment) -> dict[str, object]:
    document: dict[str, object] = {
        "scope": _scope_document(item.scope),
        "status": item.status.value,
        "observation_days": item.observation_days,
        "contract_check_count": item.contract_check_count,
        "remaining_observation_days": item.remaining_observation_days,
        "remaining_contract_checks": item.remaining_contract_checks,
        "baseline_manifest_id": item.baseline_manifest_id,
        "baseline_observation_days": item.baseline_observation_days,
        "expected_periods": item.expected_periods,
        "observed_periods": item.observed_periods,
        "successful_observation_ratio": item.successful_observation_ratio,
        "field_coverage_ratio": item.field_coverage_ratio,
        "continuity_ratio": item.continuity_ratio,
        "blockers": list(item.blockers),
    }
    if item.scheduled_contract_check_count is not None:
        document["scheduled_contract_check_count"] = (
            item.scheduled_contract_check_count
        )
    return document


def _scope_document(item: RequiredEvidenceScope) -> dict[str, str]:
    return {
        "provider": item.provider,
        "dataset": item.dataset,
        "market": item.market,
        "subject": item.subject,
    }


def _stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _required_string(value: dict[str, object], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"provider evidence field {field} must be a non-empty string")
    return item


def _optional_string(value: dict[str, object], field: str) -> str | None:
    item = value.get(field)
    if item is None:
        return None
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"provider evidence field {field} must be a string or null")
    return item


def _required_float(value: dict[str, object], field: str) -> float:
    item = value.get(field)
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise ValueError(f"provider evidence field {field} must be numeric")
    return float(item)


def _required_int(value: dict[str, object], field: str) -> int:
    item = value.get(field)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"provider evidence field {field} must be an integer")
    return item


def _optional_float(value: dict[str, object], field: str) -> float | None:
    item = value.get(field)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise ValueError(f"provider evidence field {field} must be numeric or null")
    return float(item)


def _optional_int(value: dict[str, object], field: str) -> int | None:
    item = value.get(field)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"provider evidence field {field} must be an integer or null")
    return item


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"provider evidence field {field} must be a string list")
    result = tuple(value)
    if result != tuple(sorted(set(result))):
        raise ValueError(f"provider evidence field {field} must be sorted and unique")
    return result


def _aware_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"provider evidence field {field} is not ISO datetime") from error
    require_timezone(parsed, f"provider evidence {field}")
    return parsed


def _ratio_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def _fraction_text(numerator: int | None, denominator: int | None) -> str:
    if numerator is None or denominator is None:
        return "N/A"
    return f"{numerator}/{denominator}"


def _days_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}"


__all__ = [
    "EvidenceHorizonPolicy",
    "EvidenceHorizonStatus",
    "EvidenceScopeHorizonAssessment",
    "ProviderEvidenceHorizonReport",
    "RequiredEvidenceScope",
    "evaluate_provider_evidence_horizon",
    "provider_evidence_horizon_json",
    "render_provider_evidence_horizon_markdown",
    "required_provider_evidence_scopes",
    "serialize_provider_evidence_horizon",
]
