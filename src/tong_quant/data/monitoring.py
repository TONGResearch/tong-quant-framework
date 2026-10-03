import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol
from uuid import uuid4

from tong_quant.core.exceptions import DataProviderError
from tong_quant.data.providers.contracts import (
    ProviderCapabilityStatus,
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceAdapter,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel
from tong_quant.version import PROVIDER_CONTRACT_MONITOR_VERSION


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ProviderContractRepository(Protocol):
    def save_provider_contract_run(self, run: ProviderContractRun) -> str: ...


@dataclass(frozen=True, slots=True)
class ProviderContractProbe:
    adapter: ProviderEvidenceAdapter
    request: ProviderDatasetRequest
    required_payload_fields: tuple[str, ...]


@dataclass(slots=True)
class ProviderContractMonitor:
    repository: ProviderContractRepository | None = None
    clock: Callable[[], datetime] = _utc_now
    timer: Callable[[], float] = monotonic

    def run(self, probes: tuple[ProviderContractProbe, ...]) -> ProviderContractRun:
        run_id = str(uuid4())
        started_at = self.clock()
        checks = tuple(self._check(run_id, probe) for probe in probes)
        completed_at = self.clock()
        run = ProviderContractRun(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            status=_overall_status(checks),
            checks=checks,
            implementation_version=PROVIDER_CONTRACT_MONITOR_VERSION,
        )
        if self.repository is not None:
            self.repository.save_provider_contract_run(run)
        return run

    def _check(
        self,
        run_id: str,
        probe: ProviderContractProbe,
    ) -> ProviderContractCheck:
        started = self.timer()
        checked_at = self.clock()
        capability = _capability_for(probe)
        if capability is None:
            return self._unavailable_check(
                run_id,
                probe,
                checked_at,
                started,
                error_code="capability_not_declared",
            )
        if capability.status in {
            ProviderCapabilityStatus.UNAVAILABLE,
            ProviderCapabilityStatus.NOT_TESTED,
        }:
            return self._unavailable_check(
                run_id,
                probe,
                checked_at,
                started,
                error_code=f"capability_{capability.status.value}",
                capability=capability,
            )
        try:
            batch = probe.adapter.fetch(probe.request)
            if (
                batch.provider != probe.adapter.provider_id
                or batch.dataset != probe.request.dataset
                or batch.market != probe.request.market
            ):
                raise ValueError("provider contract batch identity mismatch")
            if any(
                evidence_time is not None
                and evidence_time > probe.request.as_of
                for record in batch.records
                for evidence_time in (
                    record.available_at,
                    record.observed_at,
                    record.published_at,
                )
            ):
                raise ValueError("provider contract returned future decision evidence")
            if capability.trust_level is not DataTrustLevel.VERIFIED and any(
                record.trust_level is DataTrustLevel.VERIFIED
                for record in batch.records
            ):
                raise ValueError("provider contract promoted trust above capability")
            absent_fields = tuple(
                field
                for field in probe.required_payload_fields
                if batch.records
                and any(field not in record.payload for record in batch.records)
            )
            null_value_fields = tuple(
                field
                for field in probe.required_payload_fields
                if batch.records
                and any(
                    field in record.payload and record.payload[field] is None
                    for record in batch.records
                )
            )
            missing_fields = tuple(
                field
                for field in probe.required_payload_fields
                if field in absent_fields or field in null_value_fields
            )
            if not batch.records:
                missing_fields = probe.required_payload_fields
            limitations = tuple(item.description for item in batch.limitations)
            if not batch.records:
                limitations = (*limitations, "Provider returned no normalized evidence")
            elif null_value_fields:
                limitations = (
                    *limitations,
                    "Some normalized records contain null required values",
                )
            status = ProviderContractStatus.HEALTHY
            error_code = ""
            if absent_fields:
                status = ProviderContractStatus.DEFECT
                error_code = "required_fields_missing"
            elif not batch.records:
                status = ProviderContractStatus.DEGRADED
                error_code = "no_normalized_evidence"
            elif null_value_fields:
                status = ProviderContractStatus.DEGRADED
                error_code = "required_values_missing"
            elif capability.status is ProviderCapabilityStatus.DEGRADED:
                status = ProviderContractStatus.DEGRADED
            trust_level = _weakest_trust(
                (capability.trust_level, *(record.trust_level for record in batch.records))
            )
            availability_precision = _weakest_precision(
                (
                    capability.availability_precision,
                    *(record.availability_precision for record in batch.records),
                )
            )
            return ProviderContractCheck(
                check_id=str(uuid4()),
                run_id=run_id,
                provider=probe.adapter.provider_id,
                dataset=probe.request.dataset,
                market=probe.request.market,
                subject=probe.request.subject,
                request_as_of=probe.request.as_of,
                status=status,
                records_observed=len(batch.records),
                trust_level=trust_level,
                availability_precision=availability_precision,
                latency_ms=max((self.timer() - started) * 1000, 0),
                required_fields=probe.required_payload_fields,
                missing_fields=missing_fields,
                limitations=limitations,
                error_code=error_code,
                checked_at=checked_at,
            )
        except (DataProviderError, TimeoutError, OSError) as error:
            return self._unavailable_check(
                run_id,
                probe,
                checked_at,
                started,
                error_code=type(error).__name__,
                capability=capability,
            )
        except Exception as error:
            return ProviderContractCheck(
                check_id=str(uuid4()),
                run_id=run_id,
                provider=probe.adapter.provider_id,
                dataset=probe.request.dataset,
                market=probe.request.market,
                subject=probe.request.subject,
                request_as_of=probe.request.as_of,
                status=ProviderContractStatus.DEFECT,
                records_observed=0,
                trust_level=capability.trust_level,
                availability_precision=capability.availability_precision,
                latency_ms=max((self.timer() - started) * 1000, 0),
                required_fields=probe.required_payload_fields,
                missing_fields=probe.required_payload_fields,
                limitations=tuple(item.description for item in capability.limitations),
                error_code=type(error).__name__,
                checked_at=checked_at,
            )

    def _unavailable_check(
        self,
        run_id: str,
        probe: ProviderContractProbe,
        checked_at: datetime,
        started: float,
        *,
        error_code: str,
        capability: ProviderDatasetCapability | None = None,
    ) -> ProviderContractCheck:
        return ProviderContractCheck(
            check_id=str(uuid4()),
            run_id=run_id,
            provider=probe.adapter.provider_id,
            dataset=probe.request.dataset,
            market=probe.request.market,
            subject=probe.request.subject,
            request_as_of=probe.request.as_of,
            status=ProviderContractStatus.UNAVAILABLE,
            records_observed=0,
            trust_level=(
                DataTrustLevel.UNKNOWN
                if capability is None
                else capability.trust_level
            ),
            availability_precision=(
                AvailabilityPrecision.UNKNOWN
                if capability is None
                else capability.availability_precision
            ),
            latency_ms=max((self.timer() - started) * 1000, 0),
            required_fields=probe.required_payload_fields,
            missing_fields=probe.required_payload_fields,
            limitations=(
                ()
                if capability is None
                else tuple(item.description for item in capability.limitations)
            ),
            error_code=error_code,
            checked_at=checked_at,
        )


def provider_contract_json(run: ProviderContractRun) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat(),
        "status": run.status.value,
        "implementation_version": run.implementation_version,
        "checks": [
            {
                "provider": check.provider,
                "dataset": check.dataset,
                "market": check.market.value,
                "subject": check.subject,
                "request_as_of": check.request_as_of.isoformat(),
                "status": check.status.value,
                "records_observed": check.records_observed,
                "trust_level": check.trust_level.value,
                "availability_precision": check.availability_precision.value,
                "latency_ms": round(check.latency_ms, 3),
                "required_fields": list(check.required_fields),
                "missing_fields": list(check.missing_fields),
                "limitations": list(check.limitations),
                "error_code": check.error_code,
                "checked_at": check.checked_at.isoformat(),
            }
            for check in run.checks
        ],
    }


def render_provider_contract_markdown(run: ProviderContractRun) -> str:
    document = provider_contract_json(run)
    lines = [
        "# Provider Contract Monitor",
        "",
        f"- Status: `{document['status']}`",
        f"- Started: `{document['started_at']}`",
        f"- Version: `{document['implementation_version']}`",
        "",
        "| Provider | Dataset | Market | Status | Records | Trust | Precision | Error |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for check in run.checks:
        lines.append(
            f"| {check.provider} | {check.dataset} | {check.market.value} | "
            f"{check.status.value} | {check.records_observed} | "
            f"{check.trust_level.value} | {check.availability_precision.value} | "
            f"{check.error_code or '-'} |"
        )
    lines.extend(
        [
            "",
            "Contract health does not upgrade provider trust or PIT readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def serialize_provider_contract(run: ProviderContractRun) -> str:
    return json.dumps(provider_contract_json(run), indent=2, sort_keys=True)


def _capability_for(probe: ProviderContractProbe) -> ProviderDatasetCapability | None:
    matches = tuple(
        capability
        for capability in probe.adapter.capabilities()
        if capability.provider == probe.adapter.provider_id
        and capability.dataset == probe.request.dataset
        and probe.request.market in capability.markets
    )
    return matches[0] if len(matches) == 1 else None


def _overall_status(
    checks: tuple[ProviderContractCheck, ...],
) -> ProviderContractStatus:
    severity = {
        ProviderContractStatus.HEALTHY: 0,
        ProviderContractStatus.DEGRADED: 1,
        ProviderContractStatus.UNAVAILABLE: 2,
        ProviderContractStatus.DEFECT: 3,
    }
    if not checks:
        return ProviderContractStatus.DEGRADED
    return max((check.status for check in checks), key=severity.__getitem__)


def _weakest_trust(values: tuple[DataTrustLevel, ...]) -> DataTrustLevel:
    strength = {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }
    return min(values, key=strength.__getitem__)


def _weakest_precision(
    values: tuple[AvailabilityPrecision, ...],
) -> AvailabilityPrecision:
    strength = {
        AvailabilityPrecision.UNKNOWN: 0,
        AvailabilityPrecision.RETRIEVAL_TIME: 1,
        AvailabilityPrecision.ESTIMATED: 2,
        AvailabilityPrecision.DATE_ONLY: 3,
        AvailabilityPrecision.EXACT: 4,
    }
    return min(values, key=strength.__getitem__)


__all__ = [
    "ProviderContractMonitor",
    "ProviderContractProbe",
    "ProviderContractRepository",
    "provider_contract_json",
    "render_provider_contract_markdown",
    "serialize_provider_contract",
]
