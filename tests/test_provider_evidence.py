import json
import ssl
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.models import ProviderResponse, RawDataset
from tong_quant.data.providers import yahoo
from tong_quant.data.providers.cninfo import (
    CNINFO_DISCLOSURES_DATASET,
    CnInfoEvidenceAdapter,
)
from tong_quant.data.providers.contracts import (
    EvidenceLimitation,
    ProviderCapabilityStatus,
    ProviderDatasetCapability,
    ProviderDatasetRequest,
    ProviderEvidenceBatch,
    ProviderEvidenceRecord,
    provider_evidence_id,
)
from tong_quant.data.providers.yahoo import (
    YAHOO_DAILY_BARS_DATASET,
    YahooChartHttpClient,
    YahooFinanceEvidenceAdapter,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

NOW = datetime(2026, 6, 20, 12, tzinfo=UTC)
RAW_HASH = sha256(b"provider-evidence").hexdigest()


class _CnInfoTransport:
    def fundamental_disclosures(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
        category: str = "",
    ) -> ProviderResponse:
        assert (symbol, start_date, end_date, category) == (
            "600000",
            "20260601",
            "20260620",
            "",
        )
        frame = pd.DataFrame(
            [
                {
                    "代码": "600000",
                    "简称": "浦发银行",
                    "公告标题": "年度报告",
                    "公告时间": "2026-06-19 15:30:00",
                    "公告链接": "https://example.test/cninfo/1",
                }
            ]
        )
        return ProviderResponse(
            dataset=RawDataset(
                dataset="fundamental_publications_disclosure",
                frame=frame,
                retrieved_at=NOW,
                source="akshare:stock_zh_a_disclosure_report_cninfo",
                parameters={},
                raw_data_hash=RAW_HASH,
            ),
            cache_hit=False,
        )


class _YahooClient:
    def chart(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        assert (symbol, start_date, end_date) == ("MSFT", "2026-06-18", "2026-06-20")
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
                        "timestamp": [1781740800],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [480.0],
                                    "high": [485.0],
                                    "low": [478.0],
                                    "close": [483.0],
                                    "volume": [20_000_000],
                                    "adjclose": [999.0],
                                }
                            ]
                        },
                    }
                ],
            }
        }


class _HttpResponse:
    def __enter__(self) -> "_HttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, size: int = -1) -> bytes:
        content = json.dumps({"chart": {"error": None, "result": []}}).encode()
        return content if size < 0 else content[:size]


def test_yahoo_http_client_uses_explicit_ca_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _urlopen(*args: Any, **kwargs: Any) -> _HttpResponse:
        del args
        captured.update(kwargs)
        return _HttpResponse()

    monkeypatch.setattr(yahoo, "urlopen", _urlopen)

    YahooChartHttpClient(max_attempts=1).chart(
        "MSFT",
        start_date="2026-06-18",
        end_date="2026-06-20",
    )

    assert isinstance(captured["context"], ssl.SSLContext)


def test_cninfo_evidence_ingestion_preserves_source_and_pit_boundary(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    request = ProviderDatasetRequest(
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=NOW,
        parameters={"start_date": "20260601", "end_date": "20260620"},
    )

    result = ProviderNeutralIngestionService(store=store, clock=lambda: NOW).ingest(
        CnInfoEvidenceAdapter(_CnInfoTransport()), request
    )

    assert result.accepted == 1
    assert store.table_count("ingestion_batches") == 1
    assert store.table_count("provider_evidence_records") == 1
    before_publication = store.provider_evidence_as_of(
        provider="cninfo_via_akshare",
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=datetime(2026, 6, 19, 6, tzinfo=UTC),
    )
    after_publication = store.provider_evidence_as_of(
        provider="cninfo_via_akshare",
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
        as_of=NOW,
    )
    assert before_publication == []
    assert len(after_publication) == 1
    assert after_publication[0]["trust_level"] == DataTrustLevel.MEDIUM.value
    assert after_publication[0]["availability_precision"] == (
        AvailabilityPrecision.EXACT.value
    )


def test_yahoo_evidence_is_retrieval_time_only_and_excludes_adjusted_close(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    request = ProviderDatasetRequest(
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.US,
        subject="MSFT",
        as_of=NOW,
        parameters={"start_date": "2026-06-18", "end_date": "2026-06-20"},
    )

    result = ProviderNeutralIngestionService(store=store, clock=lambda: NOW).ingest(
        YahooFinanceEvidenceAdapter(client=_YahooClient(), clock=lambda: NOW),
        request,
    )

    assert result.accepted == 1
    rows = store.provider_evidence_as_of(
        provider="yahoo_finance",
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.US,
        subject="MSFT",
        as_of=NOW,
    )
    assert len(rows) == 1
    assert rows[0]["trust_level"] == DataTrustLevel.LOW.value
    assert rows[0]["availability_precision"] == (
        AvailabilityPrecision.RETRIEVAL_TIME.value
    )
    assert "adjclose" not in rows[0]["payload_json"]


class _FutureEvidenceAdapter:
    provider_id = "synthetic"

    def capabilities(self) -> tuple[ProviderDatasetCapability, ...]:
        return (
            ProviderDatasetCapability(
                provider=self.provider_id,
                dataset="future_test",
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
        observed_at = datetime(2026, 6, 20, 10, tzinfo=UTC)
        retrieved_at = datetime(2026, 6, 20, 11, tzinfo=UTC)
        payload: dict[str, object] = {"value": 1}
        record = ProviderEvidenceRecord(
            evidence_id=provider_evidence_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject=request.subject,
                available_at=observed_at,
                source_reference="synthetic",
                payload=payload,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            observed_at=observed_at,
            available_at=observed_at,
            retrieved_at=retrieved_at,
            source_reference="synthetic",
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
            retrieved_at=retrieved_at,
            source="synthetic",
            parameters={},
            raw_data_hash=RAW_HASH,
            raw_record_count=1,
            records=(record,),
            limitations=(
                EvidenceLimitation(
                    code="synthetic_only",
                    description="synthetic evidence",
                    trust_level=DataTrustLevel.UNKNOWN,
                ),
            ),
        )


class _SensitiveEvidenceAdapter(_FutureEvidenceAdapter):
    def fetch(self, request: ProviderDatasetRequest) -> ProviderEvidenceBatch:
        payload: dict[str, object] = {"api_key": "must-not-persist", "value": 1}
        record = ProviderEvidenceRecord(
            evidence_id=provider_evidence_id(
                provider=self.provider_id,
                dataset=request.dataset,
                market=request.market,
                subject=request.subject,
                available_at=NOW,
                source_reference="synthetic",
                payload=payload,
            ),
            provider=self.provider_id,
            dataset=request.dataset,
            market=request.market,
            subject=request.subject,
            observed_at=NOW,
            available_at=NOW,
            retrieved_at=NOW,
            source_reference="synthetic",
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
            source="synthetic",
            parameters={},
            raw_data_hash=RAW_HASH,
            raw_record_count=1,
            records=(record,),
            limitations=(),
        )


def test_provider_neutral_ingestion_rejects_future_decision_evidence(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    request = ProviderDatasetRequest(
        dataset="future_test",
        market=Market.US,
        subject="TEST",
        as_of=datetime(2026, 6, 20, 9, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="future event data"):
        ProviderNeutralIngestionService(store=store).ingest(
            _FutureEvidenceAdapter(), request
        )

    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("provider_evidence_records") == 0


def test_provider_evidence_repository_rejects_nested_credentials_atomically(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "evidence.sqlite3")
    store.initialize()
    request = ProviderDatasetRequest(
        dataset="future_test",
        market=Market.US,
        subject="TEST",
        as_of=NOW,
    )

    with pytest.raises(ValueError, match="credential"):
        ProviderNeutralIngestionService(store=store, clock=lambda: NOW).ingest(
            _SensitiveEvidenceAdapter(), request
        )

    assert store.table_count("ingestion_batches") == 0
    assert store.table_count("raw_dataset_fingerprints") == 0
    assert store.table_count("provider_evidence_records") == 0
