import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast

import pandas as pd
import tushare as ts

from tong_quant.core.security import redact_sensitive_text
from tong_quant.data.calibration.models import CalibrationDataset
from tong_quant.data.providers.tushare import TushareClient
from tong_quant.domain.models import require_timezone
from tong_quant.version import PROVIDER_CAPABILITY_VERSION


class TushareEnvironmentStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    INVALID = "invalid"
    READY_FOR_PROBE = "ready_for_probe"


class TushareEndpoint(StrEnum):
    STOCK_BASIC = "stock_basic"
    NAMECHANGE = "namechange"
    SUSPEND_D = "suspend_d"
    DISCLOSURE_DATE = "disclosure_date"
    INCOME = "income"
    DIVIDEND = "dividend"
    INDEX_WEIGHT = "index_weight"


class EndpointAccessStatus(StrEnum):
    AVAILABLE = "available"
    PERMISSION_DENIED = "permission_denied"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"
    PROVIDER_ERROR = "provider_error"
    NOT_TESTED = "not_tested"


class DatasetCapabilityStatus(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_TESTED = "not_tested"


@dataclass(frozen=True, slots=True)
class TushareEnvironmentValidation:
    status: TushareEnvironmentStatus
    configured: bool
    credential_source: str
    warnings: tuple[str, ...] = ()
    model_version: str = PROVIDER_CAPABILITY_VERSION


@dataclass(frozen=True, slots=True)
class CapabilityProbeContext:
    as_of: datetime
    ts_code: str
    trade_date: str
    period_end: str
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "capability probe as_of")


@dataclass(frozen=True, slots=True)
class EndpointCapability:
    endpoint: TushareEndpoint
    status: EndpointAccessStatus
    records_observed: int | None
    detail: str
    required_points: str = "unknown"
    exception_detail: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetCapability:
    dataset: CalibrationDataset
    status: DatasetCapabilityStatus
    required_endpoints: tuple[TushareEndpoint, ...]
    unavailable_endpoints: tuple[TushareEndpoint, ...]
    required_points: str
    reason: str


@dataclass(frozen=True, slots=True)
class TushareCapabilityReport:
    generated_at: datetime
    environment: TushareEnvironmentValidation
    probe_scope: dict[str, str]
    endpoints: tuple[EndpointCapability, ...]
    datasets: tuple[DatasetCapability, ...]
    model_version: str = PROVIDER_CAPABILITY_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.generated_at, "capability report generated_at")


_DATASET_ENDPOINTS: dict[CalibrationDataset, tuple[TushareEndpoint, ...]] = {
    CalibrationDataset.SECURITY_LIFECYCLE: (
        TushareEndpoint.NAMECHANGE,
        TushareEndpoint.SUSPEND_D,
        TushareEndpoint.STOCK_BASIC,
    ),
    CalibrationDataset.ST_STATUS: (TushareEndpoint.NAMECHANGE,),
    CalibrationDataset.SUSPENSION_STATUS: (TushareEndpoint.SUSPEND_D,),
    CalibrationDataset.DELISTING_RECORDS: (TushareEndpoint.STOCK_BASIC,),
    CalibrationDataset.FINANCIAL_PUBLICATION_DATES: (
        TushareEndpoint.DISCLOSURE_DATE,
    ),
    CalibrationDataset.FUNDAMENTAL_REVISIONS: (TushareEndpoint.INCOME,),
    CalibrationDataset.CORPORATE_ACTIONS: (TushareEndpoint.DIVIDEND,),
    CalibrationDataset.UNIVERSE_COVERAGE: (TushareEndpoint.STOCK_BASIC,),
    CalibrationDataset.CSI300_MEMBERSHIP: (TushareEndpoint.INDEX_WEIGHT,),
    CalibrationDataset.CSI500_MEMBERSHIP: (TushareEndpoint.INDEX_WEIGHT,),
    CalibrationDataset.CSI1000_MEMBERSHIP: (TushareEndpoint.INDEX_WEIGHT,),
}

_ENDPOINT_REQUIRED_POINTS: dict[TushareEndpoint, str] = {
    TushareEndpoint.STOCK_BASIC: "provider/account-tier dependent",
    TushareEndpoint.NAMECHANGE: "provider/account-tier dependent",
    TushareEndpoint.SUSPEND_D: "provider/account-tier dependent",
    TushareEndpoint.DISCLOSURE_DATE: "2000+ points",
    TushareEndpoint.INCOME: "2000+ points",
    TushareEndpoint.DIVIDEND: "2000+ points",
    TushareEndpoint.INDEX_WEIGHT: "2000 points",
}


def validate_tushare_environment(
    environ: Mapping[str, str] | None = None,
) -> TushareEnvironmentValidation:
    environment = os.environ if environ is None else environ
    token = environment.get("TUSHARE_TOKEN")
    if not token:
        return TushareEnvironmentValidation(
            status=TushareEnvironmentStatus.NOT_CONFIGURED,
            configured=False,
            credential_source="environment:TUSHARE_TOKEN",
            warnings=("TUSHARE_TOKEN is not configured",),
        )
    normalized = token.strip()
    placeholders = {"token", "your_token", "replace_me", "changeme"}
    if (
        normalized != token
        or any(character.isspace() for character in normalized)
        or len(normalized) < 16
        or normalized.lower() in placeholders
    ):
        return TushareEnvironmentValidation(
            status=TushareEnvironmentStatus.INVALID,
            configured=True,
            credential_source="environment:TUSHARE_TOKEN",
            warnings=("TUSHARE_TOKEN fails local syntax validation",),
        )
    return TushareEnvironmentValidation(
        status=TushareEnvironmentStatus.READY_FOR_PROBE,
        configured=True,
        credential_source="environment:TUSHARE_TOKEN",
    )


def tushare_client_from_environment(
    environ: Mapping[str, str] | None = None,
) -> tuple[TushareEnvironmentValidation, TushareClient | None]:
    environment = os.environ if environ is None else environ
    validation = validate_tushare_environment(environment)
    if validation.status is not TushareEnvironmentStatus.READY_FOR_PROBE:
        return validation, None
    token = environment["TUSHARE_TOKEN"]
    try:
        return validation, cast(TushareClient, ts.pro_api(token))
    except Exception:
        return (
            TushareEnvironmentValidation(
                status=TushareEnvironmentStatus.INVALID,
                configured=True,
                credential_source="environment:TUSHARE_TOKEN",
                warnings=("Tushare client initialization failed",),
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class TushareCapabilityDetector:
    client: TushareClient | None
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def detect(
        self,
        environment: TushareEnvironmentValidation,
        context: CapabilityProbeContext,
    ) -> TushareCapabilityReport:
        if (
            self.client is None
            or environment.status is not TushareEnvironmentStatus.READY_FOR_PROBE
        ):
            endpoints = tuple(
                EndpointCapability(
                    endpoint=endpoint,
                    status=EndpointAccessStatus.NOT_TESTED,
                    records_observed=None,
                    detail="credential validation did not permit a live probe",
                    required_points=_ENDPOINT_REQUIRED_POINTS[endpoint],
                )
                for endpoint in TushareEndpoint
            )
        else:
            endpoints = self._detect_live(context)
        return TushareCapabilityReport(
            generated_at=self.clock(),
            environment=environment,
            probe_scope={
                "ts_code": context.ts_code,
                "trade_date": context.trade_date,
                "period_end": context.period_end,
                "start_date": context.start_date,
                "end_date": context.end_date,
            },
            endpoints=endpoints,
            datasets=_dataset_capabilities(endpoints),
        )

    def _detect_live(
        self,
        context: CapabilityProbeContext,
    ) -> tuple[EndpointCapability, ...]:
        stock_basic = self._probe(TushareEndpoint.STOCK_BASIC, context)
        if stock_basic.status is EndpointAccessStatus.AUTHENTICATION_FAILED:
            return tuple(
                stock_basic
                if endpoint is TushareEndpoint.STOCK_BASIC
                else EndpointCapability(
                    endpoint=endpoint,
                    status=EndpointAccessStatus.AUTHENTICATION_FAILED,
                    records_observed=None,
                    detail="authentication failed before endpoint probing",
                    required_points=_ENDPOINT_REQUIRED_POINTS[endpoint],
                )
                for endpoint in TushareEndpoint
            )
        return (
            stock_basic,
            *(
                self._probe(endpoint, context)
                for endpoint in TushareEndpoint
                if endpoint is not TushareEndpoint.STOCK_BASIC
            ),
        )

    def _probe(
        self,
        endpoint: TushareEndpoint,
        context: CapabilityProbeContext,
    ) -> EndpointCapability:
        try:
            frame = self._fetch(endpoint, context)
            if not isinstance(frame, pd.DataFrame):
                raise TypeError("Tushare endpoint did not return a DataFrame")
        except Exception as error:
            status, detail, exception_detail, required_points = _classify_provider_error(
                error,
                fallback_required_points=_ENDPOINT_REQUIRED_POINTS[endpoint],
            )
            return EndpointCapability(
                endpoint,
                status,
                None,
                detail,
                required_points=required_points,
                exception_detail=exception_detail,
            )
        return EndpointCapability(
            endpoint=endpoint,
            status=EndpointAccessStatus.AVAILABLE,
            records_observed=len(frame.index),
            detail=(
                "endpoint call succeeded; observed rows do not establish historical coverage"
            ),
            required_points=_ENDPOINT_REQUIRED_POINTS[endpoint],
        )

    def _fetch(
        self,
        endpoint: TushareEndpoint,
        context: CapabilityProbeContext,
    ) -> pd.DataFrame:
        if self.client is None:
            raise RuntimeError("Tushare client is unavailable")
        if endpoint is TushareEndpoint.STOCK_BASIC:
            return self.client.stock_basic(
                list_status="L",
                fields="ts_code,symbol,list_status,list_date,delist_date",
            )
        if endpoint is TushareEndpoint.NAMECHANGE:
            return self.client.namechange(
                ts_code=context.ts_code,
                start_date=context.start_date,
                end_date=context.end_date,
                fields="ts_code,name,start_date,end_date,ann_date,change_reason",
            )
        if endpoint is TushareEndpoint.SUSPEND_D:
            return self.client.suspend_d(
                trade_date=context.trade_date,
                fields="ts_code,trade_date,suspend_timing,suspend_type",
            )
        if endpoint is TushareEndpoint.DISCLOSURE_DATE:
            return self.client.disclosure_date(
                end_date=context.period_end,
                fields="ts_code,ann_date,end_date,actual_date,modify_date",
            )
        if endpoint is TushareEndpoint.INCOME:
            return self.client.income(
                ts_code=context.ts_code,
                start_date=context.start_date,
                end_date=context.end_date,
                fields="ts_code,ann_date,f_ann_date,end_date,report_type,update_flag",
            )
        if endpoint is TushareEndpoint.DIVIDEND:
            return self.client.dividend(
                ts_code=context.ts_code,
                fields="ts_code,ann_date,record_date,ex_date,imp_ann_date",
            )
        return self.client.index_weight(
            index_code="000300.SH",
            start_date=context.start_date,
            end_date=context.end_date,
        )


def render_capability_markdown(report: TushareCapabilityReport) -> str:
    lines = [
        "# Tushare Provider Capability Report",
        "",
        f"Generated at: {report.generated_at.isoformat()}",
        f"Environment: **{report.environment.status.value.upper()}**",
        "Credential source: environment only; credential value is never recorded.",
        "",
        "## Endpoint Capabilities",
        "",
        "| Endpoint | Status | Rows observed | Detail |",
        "|---|---|---:|---|",
    ]
    for endpoint_capability in report.endpoints:
        records = (
            "N/A"
            if endpoint_capability.records_observed is None
            else str(endpoint_capability.records_observed)
        )
        lines.append(
            f"| {endpoint_capability.endpoint.value} | "
            f"{endpoint_capability.status.value} | {records} | "
            f"{endpoint_capability.detail} |"
        )
    lines.extend(
        (
            "",
            "## Endpoint Diagnostics",
            "",
            "| Endpoint | Required points | Exception detail |",
            "|---|---|---|",
        )
    )
    for endpoint_capability in report.endpoints:
        lines.append(
            f"| {endpoint_capability.endpoint.value} | "
            f"{endpoint_capability.required_points} | "
            f"{endpoint_capability.exception_detail or 'None'} |"
        )
    lines.extend(
        (
            "",
            "## Dataset Capabilities",
            "",
            "| Dataset | Status | Required endpoints | Missing endpoints | "
            "Required points | Reason |",
            "|---|---|---|---|---|---|",
        )
    )
    for dataset_capability in report.datasets:
        required = ", ".join(
            item.value for item in dataset_capability.required_endpoints
        )
        unavailable = ", ".join(
            item.value for item in dataset_capability.unavailable_endpoints
        )
        lines.append(
            f"| {dataset_capability.dataset.value} | "
            f"{dataset_capability.status.value} | "
            f"{required} | {unavailable or 'None'} |"
            f" {dataset_capability.required_points} | "
            f"{dataset_capability.reason} |"
        )
    lines.extend(
        (
            "",
            "## Credential Diagnostics",
            "",
            f"- Token detected: {str(report.environment.configured)}",
        )
    )
    if report.environment.warnings:
        lines.extend(("", "## Environment Warnings", ""))
        lines.extend(f"- {warning}" for warning in report.environment.warnings)
    return "\n".join(lines).rstrip() + "\n"


def capability_json(report: TushareCapabilityReport) -> str:
    return json.dumps(asdict(report), default=_json_default, indent=2, sort_keys=True)


def _dataset_capabilities(
    endpoints: tuple[EndpointCapability, ...],
) -> tuple[DatasetCapability, ...]:
    endpoint_by_name = {item.endpoint: item for item in endpoints}
    capabilities = []
    for dataset in CalibrationDataset:
        required = _DATASET_ENDPOINTS[dataset]
        endpoint_capabilities = tuple(endpoint_by_name[endpoint] for endpoint in required)
        statuses = tuple(item.status for item in endpoint_capabilities)
        if all(status is EndpointAccessStatus.AVAILABLE for status in statuses):
            status = DatasetCapabilityStatus.AVAILABLE
        elif all(status is EndpointAccessStatus.NOT_TESTED for status in statuses):
            status = DatasetCapabilityStatus.NOT_TESTED
        elif any(status is EndpointAccessStatus.AVAILABLE for status in statuses):
            status = DatasetCapabilityStatus.PARTIAL
        else:
            status = DatasetCapabilityStatus.UNAVAILABLE
        missing = tuple(
            endpoint
            for endpoint, endpoint_status in zip(required, statuses, strict=True)
            if endpoint_status is not EndpointAccessStatus.AVAILABLE
        )
        capabilities.append(
            DatasetCapability(
                dataset=dataset,
                status=status,
                required_endpoints=required,
                unavailable_endpoints=missing,
                required_points=_merge_required_points(endpoint_capabilities),
                reason=_dataset_reason(endpoint_capabilities),
            )
        )
    return tuple(capabilities)


def _classify_provider_error(
    error: Exception,
    *,
    fallback_required_points: str,
) -> tuple[EndpointAccessStatus, str, str, str]:
    message = str(error).lower()
    sanitized = _safe_exception_detail(error)
    required_points = _extract_required_points(sanitized) or fallback_required_points
    if any(marker in message for marker in ("token不对", "token无效", "invalid token")):
        return (
            EndpointAccessStatus.AUTHENTICATION_FAILED,
            "Tushare authentication failed; credential value was not recorded",
            "authentication failed; provider credential text was redacted",
            required_points,
        )
    if any(marker in message for marker in ("权限", "积分", "permission", "access denied")):
        return (
            EndpointAccessStatus.PERMISSION_DENIED,
            "account permission is insufficient for this endpoint",
            sanitized,
            required_points,
        )
    if any(
        marker in message
        for marker in ("频率", "每分钟", "每小时", "超过", "rate limit", "too many request")
    ):
        return (
            EndpointAccessStatus.RATE_LIMITED,
            "provider rate limit prevented capability detection",
            sanitized,
            required_points,
        )
    if any(
        marker in message
        for marker in (
            "接口不存在",
            "api not found",
            "unknown api",
            "invalid api",
            "字段",
            "field",
            "parameter",
            "unsupported",
        )
    ):
        return (
            EndpointAccessStatus.UNSUPPORTED,
            "endpoint or requested fields appear unsupported by the current Tushare API",
            sanitized,
            required_points,
        )
    return (
        EndpointAccessStatus.PROVIDER_ERROR,
        "endpoint probe failed; no exception text or credential was persisted",
        sanitized,
        required_points,
    )


def _safe_exception_detail(error: Exception) -> str:
    detail = redact_sensitive_text(str(error)).replace("\n", " ").strip()
    if not detail:
        return type(error).__name__
    return detail[:240]


def _extract_required_points(detail: str) -> str | None:
    match = re.search(r"(\d+)\s*(?:积分|points?)", detail, flags=re.IGNORECASE)
    if not match:
        return None
    return f"{match.group(1)} points indicated by provider error"


def _merge_required_points(endpoints: tuple[EndpointCapability, ...]) -> str:
    values = tuple(dict.fromkeys(endpoint.required_points for endpoint in endpoints))
    return ", ".join(values)


def _dataset_reason(endpoints: tuple[EndpointCapability, ...]) -> str:
    unavailable = tuple(
        endpoint for endpoint in endpoints if endpoint.status is not EndpointAccessStatus.AVAILABLE
    )
    if not unavailable:
        return "all required endpoints are available"
    return "; ".join(
        f"{endpoint.endpoint.value}: {endpoint.status.value} ({endpoint.detail})"
        for endpoint in unavailable
    )


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"unsupported capability JSON type: {type(value).__name__}")


__all__ = [
    "CapabilityProbeContext",
    "DatasetCapability",
    "DatasetCapabilityStatus",
    "EndpointAccessStatus",
    "EndpointCapability",
    "TushareCapabilityDetector",
    "TushareCapabilityReport",
    "TushareEndpoint",
    "TushareEnvironmentStatus",
    "TushareEnvironmentValidation",
    "capability_json",
    "render_capability_markdown",
    "tushare_client_from_environment",
    "validate_tushare_environment",
]
