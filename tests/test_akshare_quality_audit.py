import json
from datetime import UTC, datetime

from tong_quant.data.calibration import (
    CalibrationDataset,
    CalibrationQuery,
    CalibrationRecord,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.calibration.readiness_report import PhaseThreeQuerySpec
from tong_quant.data.quality.akshare_audit import (
    AkShareAccessStatus,
    AkShareQualityAuditor,
    HistoricalEvidenceScope,
    akshare_audit_json,
    render_akshare_audit_markdown,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel

NOW = datetime(2026, 6, 21, tzinfo=UTC)


class _StaticSource:
    source_id = "akshare"

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        if query.dataset is CalibrationDataset.FINANCIAL_PUBLICATION_DATES:
            records = (
                CalibrationRecord(
                    "600000:20251231",
                    {"actual_date": "20260420", "ann_date": None},
                ),
            )
        elif query.dataset is CalibrationDataset.CSI300_MEMBERSHIP:
            records = tuple(
                CalibrationRecord(str(index).zfill(6), {"member": True})
                for index in range(3)
            )
        elif query.dataset is CalibrationDataset.SECURITY_LIFECYCLE:
            records = (
                CalibrationRecord(
                    "000001:20260101",
                    {"is_st": True, "effective_date": "20260101"},
                ),
                CalibrationRecord(
                    "000002:20260102:suspension_started",
                    {
                        "event_type": "suspension_started",
                        "effective_date": "20260102",
                    },
                ),
                CalibrationRecord(
                    "000003:20260103",
                    {"delist_date": "20260103"},
                ),
            )
        else:
            records = ()
        return ProviderCalibrationSnapshot(
            provider=self.source_id,
            dataset=query.dataset.value,
            as_of=query.as_of,
            records=records,
            limitations=("test limitation",),
        )


class _FailingSource:
    source_id = "akshare"

    def calibration_snapshot(
        self, query: CalibrationQuery
    ) -> ProviderCalibrationSnapshot:
        del query
        raise RuntimeError("provider unavailable")


def _spec(
    dataset: CalibrationDataset,
    parameters: dict[str, str],
    *,
    expected_records: int | None = None,
) -> PhaseThreeQuerySpec:
    return PhaseThreeQuerySpec(
        query=CalibrationQuery(dataset, NOW, parameters),
        framework_areas=("Validation Inputs",),
        availability_precision=AvailabilityPrecision.DATE_ONLY,
        primary_trust_level=DataTrustLevel.MEDIUM,
        historical_continuity_score=50,
        expected_records=expected_records,
    )


def test_akshare_audit_measures_normalized_quality_without_upgrading_trust() -> None:
    report = AkShareQualityAuditor().audit(
        _StaticSource(),
        (
            _spec(
                CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
                {"period_end": "20251231"},
            ),
            _spec(
                CalibrationDataset.CSI300_MEMBERSHIP,
                {},
                expected_records=3,
            ),
        ),
        generated_at=NOW,
    )

    publication, index = report.datasets
    assert publication.access_status is AkShareAccessStatus.AVAILABLE
    assert publication.required_field_completeness == 100
    assert publication.date_validity == 100
    assert publication.key_uniqueness == 100
    assert publication.evidence_scope is HistoricalEvidenceScope.DATE_SCOPED
    assert len(publication.snapshot_hash or "") == 64
    assert index.expected_record_coverage == 100
    assert index.evidence_scope is HistoricalEvidenceScope.CURRENT_SNAPSHOT


def test_akshare_audit_preserves_empty_dataset_as_observed_empty() -> None:
    report = AkShareQualityAuditor().audit(
        _StaticSource(),
        (_spec(CalibrationDataset.SUSPENSION_STATUS, {"trade_date": "20260619"}),),
        generated_at=NOW,
    )

    audit = report.datasets[0]
    assert audit.access_status is AkShareAccessStatus.EMPTY
    assert audit.record_count == 0
    assert audit.required_field_completeness is None
    assert audit.evidence_scope is HistoricalEvidenceScope.DATE_SCOPED


def test_lifecycle_completeness_accepts_event_specific_contracts() -> None:
    report = AkShareQualityAuditor().audit(
        _StaticSource(),
        (_spec(CalibrationDataset.SECURITY_LIFECYCLE, {}),),
        generated_at=NOW,
    )

    assert report.datasets[0].required_field_completeness == 100


def test_akshare_audit_reports_provider_failure_without_fake_metrics() -> None:
    report = AkShareQualityAuditor().audit(
        _FailingSource(),
        (_spec(CalibrationDataset.UNIVERSE_COVERAGE, {}),),
        generated_at=NOW,
    )

    audit = report.datasets[0]
    assert audit.access_status is AkShareAccessStatus.ERROR
    assert audit.snapshot_hash is None
    assert audit.required_field_completeness is None
    assert "provider unavailable" in audit.limitations[0]


def test_akshare_audit_rendering_is_deterministic() -> None:
    auditor = AkShareQualityAuditor()
    specs = (
        _spec(
            CalibrationDataset.FINANCIAL_PUBLICATION_DATES,
            {"period_end": "20251231"},
        ),
    )
    first = auditor.audit(_StaticSource(), specs, generated_at=NOW)
    second = auditor.audit(_StaticSource(), specs, generated_at=NOW)

    assert first == second
    assert akshare_audit_json(first) == akshare_audit_json(second)
    assert json.loads(akshare_audit_json(first))["akshare_version"]
    assert "AKShare Data Quality Audit" in render_akshare_audit_markdown(first)
