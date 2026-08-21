import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from tong_quant.data.calibration.daily_bars import (
    DailyBarCalibrationCoordinator,
    DailyBarCalibrationQuery,
    DailyBarPriceBasis,
    FixtureDailyBarCalibrationSource,
    UnavailableDailyBarCalibrationSource,
    build_daily_bar_snapshot,
)
from tong_quant.data.calibration.models import (
    ProviderCalibrationAttemptStatus,
    ProviderConflictType,
)
from tong_quant.data.providers import massive
from tong_quant.data.providers.contracts import ProviderDatasetRequest
from tong_quant.data.providers.massive import MassiveEvidenceAdapter, MassiveHttpClient
from tong_quant.data.providers.yahoo import (
    YAHOO_DAILY_BARS_DATASET,
    YahooFinanceEvidenceAdapter,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 6, 20, 12, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"
YAHOO_FIXTURE = FIXTURES / "yahoo_daily_bars.json"
INDEPENDENT_FIXTURE = FIXTURES / "independent_daily_bars.json"


def _query() -> DailyBarCalibrationQuery:
    return DailyBarCalibrationQuery(
        market=Market.US,
        subject="MSFT",
        start_date=datetime(2026, 6, 18).date(),
        end_date=datetime(2026, 6, 19).date(),
        as_of=NOW,
    )


def _fixture(payload: dict[str, object]) -> FixtureDailyBarCalibrationSource:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return FixtureDailyBarCalibrationSource(payload, sha256(raw).hexdigest())


def test_offline_daily_bar_calibration_is_deterministic_and_trust_capped(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()
    coordinator = DailyBarCalibrationCoordinator(store)
    primary = FixtureDailyBarCalibrationSource.from_path(YAHOO_FIXTURE)
    secondary = FixtureDailyBarCalibrationSource.from_path(INDEPENDENT_FIXTURE)

    first = coordinator.run(primary, secondary, _query())
    second = coordinator.run(primary, secondary, _query())

    assert first == second
    assert first.result is not None
    assert first.attempt.status is ProviderCalibrationAttemptStatus.COMPLETED
    assert first.result.report.consistency_score == 100
    assert first.result.report.trust_level is DataTrustLevel.LOW
    assert first.result.confidence.trust_level is DataTrustLevel.LOW
    assert store.table_count("provider_calibration_attempts") == 1
    assert store.table_count("provider_consistency_reports") == 1
    stored = store.latest_provider_calibration_attempt(
        dataset=YAHOO_DAILY_BARS_DATASET,
        primary_provider="yahoo_finance",
        secondary_provider="independent_fixture",
        market=Market.US,
        subject="MSFT",
    )
    assert stored == first.attempt


def test_unavailable_secondary_is_persisted_without_false_report(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()
    outcome = DailyBarCalibrationCoordinator(store).run(
        FixtureDailyBarCalibrationSource.from_path(YAHOO_FIXTURE),
        UnavailableDailyBarCalibrationSource(
            provider_id="massive",
            reason_code="environment_credential_missing",
            price_basis=DailyBarPriceBasis.UNADJUSTED,
        ),
        _query(),
    )

    assert outcome.result is None
    assert outcome.attempt.status is ProviderCalibrationAttemptStatus.UNAVAILABLE
    assert outcome.attempt.unavailable_provider == "massive"
    assert outcome.attempt.reason_code == "environment_credential_missing"
    assert store.table_count("provider_calibration_attempts") == 1
    assert store.table_count("provider_consistency_reports") == 0


def test_adjusted_and_unadjusted_fixtures_are_incompatible(tmp_path: Path) -> None:
    payload = json.loads(INDEPENDENT_FIXTURE.read_text(encoding="utf-8"))
    payload["price_basis"] = "adjusted"
    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()

    outcome = DailyBarCalibrationCoordinator(store).run(
        FixtureDailyBarCalibrationSource.from_path(YAHOO_FIXTURE),
        _fixture(payload),
        _query(),
    )

    assert outcome.result is None
    assert outcome.attempt.status is ProviderCalibrationAttemptStatus.INCOMPATIBLE
    assert outcome.attempt.reason_code == "price_basis_mismatch"
    assert store.table_count("provider_consistency_reports") == 0


def test_empty_secondary_fixture_is_unavailable_not_agreement(tmp_path: Path) -> None:
    payload = json.loads(INDEPENDENT_FIXTURE.read_text(encoding="utf-8"))
    payload["bars"] = []
    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()

    outcome = DailyBarCalibrationCoordinator(store).run(
        FixtureDailyBarCalibrationSource.from_path(YAHOO_FIXTURE),
        _fixture(payload),
        _query(),
    )

    assert outcome.result is None
    assert outcome.attempt.status is ProviderCalibrationAttemptStatus.UNAVAILABLE
    assert outcome.attempt.reason_code == "no_comparable_records"
    assert store.table_count("provider_consistency_reports") == 0


def test_daily_bar_snapshot_rejects_non_positive_prices() -> None:
    with pytest.raises(ValueError, match="OHLC values must be positive"):
        build_daily_bar_snapshot(
            provider="test_provider",
            market=Market.US,
            subject="MSFT",
            as_of=NOW,
            price_basis=DailyBarPriceBasis.UNADJUSTED,
            trust_level=DataTrustLevel.LOW,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            rows=(
                {
                    "session_date": "2026-06-18",
                    "open": "0",
                    "high": "1",
                    "low": "0",
                    "close": "1",
                    "volume": "100",
                    "corporate_actions": [],
                },
            ),
            limitations=(),
        )


def test_daily_bar_conflicts_include_gaps_ohlcv_and_corporate_actions(
    tmp_path: Path,
) -> None:
    payload = json.loads(INDEPENDENT_FIXTURE.read_text(encoding="utf-8"))
    bars = payload["bars"]
    assert isinstance(bars, list)
    first = bars[0]
    assert isinstance(first, dict)
    first["close"] = 482
    first["corporate_actions"] = []
    del bars[1]
    store = SQLiteStore(tmp_path / "calibration.sqlite3")
    store.initialize()

    outcome = DailyBarCalibrationCoordinator(store).run(
        FixtureDailyBarCalibrationSource.from_path(YAHOO_FIXTURE),
        _fixture(payload),
        _query(),
    )

    assert outcome.result is not None
    conflicts = outcome.result.conflicts
    assert any(conflict.field_name == "close" for conflict in conflicts)
    assert any(conflict.field_name == "corporate_actions" for conflict in conflicts)
    assert any(
        conflict.conflict_type is ProviderConflictType.MISSING_SECONDARY
        for conflict in conflicts
    )


class _MassiveClient:
    adjusted = False

    def aggregates(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        del args, kwargs
        return {
            "status": "OK",
            "adjusted": self.adjusted,
            "results": [
                {
                    "t": int(datetime(2026, 6, 18, 13, 30, tzinfo=UTC).timestamp())
                    * 1000,
                    "o": 480,
                    "h": 485,
                    "l": 478,
                    "c": 483,
                    "v": 20_000_000,
                }
            ],
        }

    def dividends(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        del args, kwargs
        return {
            "status": "OK",
            "results": [{"ex_dividend_date": "2026-06-18"}],
        }

    def splits(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        del args, kwargs
        return {"status": "OK", "results": []}


def test_massive_adapter_requires_unadjusted_bars_and_maps_actions() -> None:
    adapter = MassiveEvidenceAdapter(client=_MassiveClient(), clock=lambda: NOW)
    request = ProviderDatasetRequest(
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.US,
        subject="MSFT",
        as_of=NOW,
        parameters={"start_date": "2026-06-18", "end_date": "2026-06-19"},
    )

    batch = adapter.fetch(request)

    assert len(batch.records) == 1
    assert batch.records[0].payload["session_date"] == "2026-06-18"
    assert batch.records[0].payload["price_basis"] == "unadjusted"
    assert batch.records[0].payload["corporate_actions"] == ["dividend"]
    assert batch.records[0].trust_level is DataTrustLevel.LOW
    assert (
        batch.records[0].availability_precision
        is AvailabilityPrecision.RETRIEVAL_TIME
    )

    client = _MassiveClient()
    client.adjusted = True
    with pytest.raises(ValueError, match="not explicitly unadjusted"):
        MassiveEvidenceAdapter(client=client, clock=lambda: NOW).fetch(request)


class _HttpResponse:
    def __init__(self, url: str) -> None:
        self._url = url

    def __enter__(self) -> "_HttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return json.dumps(
            {"status": "OK", "adjusted": False, "results": []}
        ).encode()


def test_massive_http_authentication_never_places_key_in_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "local-massive-test-credential"
    captured: dict[str, str] = {}

    class _Opener:
        def open(self, request: Any, **kwargs: Any) -> _HttpResponse:
            del kwargs
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            return _HttpResponse(request.full_url)

    monkeypatch.setattr(massive, "build_opener", lambda *args: _Opener())

    MassiveHttpClient(api_key=secret, max_attempts=1).aggregates(
        "MSFT",
        start_date="2026-06-18",
        end_date="2026-06-19",
    )

    assert secret not in captured["url"]
    assert "apiKey" not in captured["url"]
    assert captured["authorization"] == f"Bearer {secret}"


class _YahooActionClient:
    def chart(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        del args, kwargs
        timestamp = int(datetime(2026, 6, 18, 13, 30, tzinfo=UTC).timestamp())
        return {
            "chart": {
                "error": None,
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "exchangeName": "NMS",
                            "exchangeTimezoneName": "America/New_York",
                        },
                        "timestamp": [timestamp],
                        "events": {
                            "dividends": {str(timestamp): {"date": timestamp}}
                        },
                        "indicators": {
                            "quote": [
                                {
                                    "open": [480],
                                    "high": [485],
                                    "low": [478],
                                    "close": [483],
                                    "volume": [20_000_000],
                                }
                            ]
                        },
                    }
                ],
            }
        }


def test_yahoo_adapter_exposes_session_basis_and_corporate_actions() -> None:
    request = ProviderDatasetRequest(
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.US,
        subject="MSFT",
        as_of=NOW,
        parameters={"start_date": "2026-06-18", "end_date": "2026-06-19"},
    )

    batch = YahooFinanceEvidenceAdapter(
        client=_YahooActionClient(),
        clock=lambda: NOW,
    ).fetch(request)

    assert batch.records[0].payload["session_date"] == "2026-06-18"
    assert batch.records[0].payload["price_basis"] == "unadjusted"
    assert batch.records[0].payload["corporate_actions"] == ["dividend"]
