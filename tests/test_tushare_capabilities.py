import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from tong_quant.data.calibration import CalibrationDataset
from tong_quant.data.providers import tushare_capabilities
from tong_quant.data.providers.tushare_capabilities import (
    CapabilityProbeContext,
    DatasetCapabilityStatus,
    EndpointAccessStatus,
    TushareCapabilityDetector,
    TushareEndpoint,
    TushareEnvironmentStatus,
    capability_json,
    render_capability_markdown,
    tushare_client_from_environment,
    validate_tushare_environment,
)

NOW = datetime(2026, 6, 20, tzinfo=UTC)
SECRET = "local-test-token-that-must-never-be-rendered"


class _CapabilityClient:
    def __init__(self, denied: set[str] | None = None) -> None:
        self.denied = denied or set()

    def _result(self, endpoint: str) -> pd.DataFrame:
        if endpoint in self.denied:
            raise RuntimeError("抱歉，您没有访问该接口的权限，需要更多积分")
        return pd.DataFrame()

    def stock_basic(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("stock_basic")

    def namechange(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("namechange")

    def suspend_d(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("suspend_d")

    def disclosure_date(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("disclosure_date")

    def income(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("income")

    def dividend(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("dividend")

    def index_weight(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        return self._result("index_weight")


class _AuthenticationFailureClient(_CapabilityClient):
    def stock_basic(self, **kwargs: object) -> pd.DataFrame:
        del kwargs
        raise RuntimeError(f"invalid token {SECRET}")


def _context() -> CapabilityProbeContext:
    return CapabilityProbeContext(
        as_of=NOW,
        ts_code="600000.SH",
        trade_date="20260619",
        period_end="20251231",
        start_date="20260601",
        end_date="20260620",
    )


def test_environment_validation_never_retains_token() -> None:
    validation = validate_tushare_environment({"TUSHARE_TOKEN": SECRET})

    assert validation.status is TushareEnvironmentStatus.READY_FOR_PROBE
    assert SECRET not in repr(validation)


def test_environment_validation_rejects_placeholder_and_whitespace() -> None:
    placeholder = validate_tushare_environment({"TUSHARE_TOKEN": "replace_me"})
    whitespace = validate_tushare_environment(
        {"TUSHARE_TOKEN": " valid-looking-token-with-space "}
    )

    assert placeholder.status is TushareEnvironmentStatus.INVALID
    assert whitespace.status is TushareEnvironmentStatus.INVALID


def test_invalid_environment_never_initializes_tushare_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def _unexpected_client(token: str) -> object:
        nonlocal called
        del token
        called = True
        return object()

    monkeypatch.setattr(tushare_capabilities.ts, "pro_api", _unexpected_client)

    validation, client = tushare_client_from_environment(
        {"TUSHARE_TOKEN": "replace_me"}
    )

    assert validation.status is TushareEnvironmentStatus.INVALID
    assert client is None
    assert called is False


def test_missing_token_skips_live_capability_calls() -> None:
    environment = validate_tushare_environment({})
    report = TushareCapabilityDetector(client=None, clock=lambda: NOW).detect(
        environment, _context()
    )

    assert environment.status is TushareEnvironmentStatus.NOT_CONFIGURED
    assert all(
        endpoint.status is EndpointAccessStatus.NOT_TESTED
        for endpoint in report.endpoints
    )
    assert all(
        dataset.status is DatasetCapabilityStatus.NOT_TESTED
        for dataset in report.datasets
    )


def test_successful_empty_response_proves_access_not_coverage() -> None:
    environment = validate_tushare_environment({"TUSHARE_TOKEN": SECRET})
    report = TushareCapabilityDetector(
        client=_CapabilityClient(), clock=lambda: NOW
    ).detect(environment, _context())

    assert all(
        endpoint.status is EndpointAccessStatus.AVAILABLE
        for endpoint in report.endpoints
    )
    assert all(endpoint.records_observed == 0 for endpoint in report.endpoints)
    assert all(
        dataset.status is DatasetCapabilityStatus.AVAILABLE
        for dataset in report.datasets
    )
    assert "do not establish historical coverage" in report.endpoints[0].detail


def test_permission_detection_maps_endpoints_to_datasets() -> None:
    environment = validate_tushare_environment({"TUSHARE_TOKEN": SECRET})
    report = TushareCapabilityDetector(
        client=_CapabilityClient({"income", "index_weight"}),
        clock=lambda: NOW,
    ).detect(environment, _context())
    endpoints = {item.endpoint: item for item in report.endpoints}
    datasets = {item.dataset: item for item in report.datasets}

    assert (
        endpoints[TushareEndpoint.INCOME].status
        is EndpointAccessStatus.PERMISSION_DENIED
    )
    assert (
        datasets[CalibrationDataset.FUNDAMENTAL_REVISIONS].status
        is DatasetCapabilityStatus.UNAVAILABLE
    )
    assert (
        datasets[CalibrationDataset.CSI300_MEMBERSHIP].status
        is DatasetCapabilityStatus.UNAVAILABLE
    )
    assert (
        datasets[CalibrationDataset.FINANCIAL_PUBLICATION_DATES].status
        is DatasetCapabilityStatus.AVAILABLE
    )


def test_authentication_failure_is_sanitized_and_stops_remaining_probes() -> None:
    environment = validate_tushare_environment({"TUSHARE_TOKEN": SECRET})
    report = TushareCapabilityDetector(
        client=_AuthenticationFailureClient(), clock=lambda: NOW
    ).detect(environment, _context())

    assert all(
        endpoint.status is EndpointAccessStatus.AUTHENTICATION_FAILED
        for endpoint in report.endpoints
    )
    assert SECRET not in capability_json(report)


def test_capability_renderers_do_not_persist_credentials() -> None:
    environment = validate_tushare_environment({"TUSHARE_TOKEN": SECRET})
    report = TushareCapabilityDetector(
        client=_CapabilityClient(), clock=lambda: NOW
    ).detect(environment, _context())

    markdown = render_capability_markdown(report)
    payload = capability_json(report)

    assert SECRET not in markdown
    assert SECRET not in payload
    assert json.loads(payload)["environment"]["configured"] is True
