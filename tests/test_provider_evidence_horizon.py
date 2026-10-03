import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tong_quant.data.baselines import (
    ProviderBaselineBuilder,
    ProviderBaselineQuery,
    ProviderBaselineScope,
)
from tong_quant.data.evidence_bundle import (
    ProviderEvidenceBundleExporter,
    provider_evidence_bundle_json,
    serialize_provider_evidence_bundle,
)
from tong_quant.data.evidence_horizon import (
    EvidenceHorizonStatus,
    evaluate_provider_evidence_horizon,
    render_provider_evidence_horizon_markdown,
    required_provider_evidence_scopes,
)
from tong_quant.data.providers.cninfo import CNINFO_DISCLOSURES_DATASET
from tong_quant.data.providers.contracts import (
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
)
from tong_quant.data.providers.yahoo import YAHOO_DAILY_BARS_DATASET
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

START = datetime(2026, 5, 1, tzinfo=UTC)
END = START + timedelta(days=84)
SCOPES = (
    ProviderBaselineScope(
        provider="cninfo_direct",
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
    ),
    ProviderBaselineScope(
        provider="cninfo_via_akshare",
        dataset=CNINFO_DISCLOSURES_DATASET,
        market=Market.CHINA_A,
        subject="600000",
    ),
    ProviderBaselineScope(
        provider="yahoo_finance",
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.HONG_KONG,
        subject="0700.HK",
    ),
    ProviderBaselineScope(
        provider="yahoo_finance",
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.MALAYSIA,
        subject="1155.KL",
    ),
    ProviderBaselineScope(
        provider="yahoo_finance",
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=Market.US,
        subject="MSFT",
    ),
)


def test_complete_required_scopes_are_eligible_for_separate_readiness_review(
    tmp_path: Path,
) -> None:
    document = _bundle_document(tmp_path / "complete.sqlite3", SCOPES)

    report = evaluate_provider_evidence_horizon(document)

    assert report.eligible_for_readiness_reassessment
    assert report.blockers == ()
    assert len(report.assessments) == 5
    assert all(
        item.status is EvidenceHorizonStatus.COMPLETE for item in report.assessments
    )
    assert all(item.observation_days == 84 for item in report.assessments)
    assert all(item.contract_check_count == 8 for item in report.assessments)
    assert all(item.baseline_observation_days == 84 for item in report.assessments)
    assert all(item.observed_periods == 8 for item in report.assessments)
    markdown = render_provider_evidence_horizon_markdown(report)
    assert "does not promote provider trust" in markdown


def test_missing_scope_cannot_be_hidden_by_dataset_aggregate(tmp_path: Path) -> None:
    document = _bundle_document(tmp_path / "missing.sqlite3", SCOPES[:-1])

    report = evaluate_provider_evidence_horizon(document)

    missing = next(
        item for item in report.assessments if item.scope.subject == "MSFT"
    )
    assert not report.eligible_for_readiness_reassessment
    assert missing.status is EvidenceHorizonStatus.MISSING
    assert missing.remaining_observation_days == 84
    assert missing.remaining_contract_checks == 8


def test_short_scope_reports_exact_remaining_horizon(tmp_path: Path) -> None:
    database = tmp_path / "short.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    dates = tuple(START + timedelta(days=14 * index) for index in range(7))
    _save_contract_history(store, SCOPES, dates)
    ProviderBaselineBuilder(repository=store, clock=lambda: END).build(
        ProviderBaselineQuery(
            period_start=START,
            period_end=END,
            expected_interval_days=14,
            scopes=SCOPES,
        )
    )
    document = provider_evidence_bundle_json(
        ProviderEvidenceBundleExporter().export(database, as_of=END)
    )

    report = evaluate_provider_evidence_horizon(document)

    assert not report.eligible_for_readiness_reassessment
    assert all(item.status is EvidenceHorizonStatus.INCOMPLETE for item in report.assessments)
    assert all(item.observation_days == 84 for item in report.assessments)
    assert all(item.remaining_contract_checks == 1 for item in report.assessments)


def test_short_baseline_cannot_reuse_an_older_raw_observation_span(
    tmp_path: Path,
) -> None:
    database = tmp_path / "short-baseline.sqlite3"
    store = SQLiteStore(database)
    store.initialize()
    dates = tuple(START + timedelta(days=12 * index) for index in range(8))
    _save_contract_history(store, SCOPES, dates)
    ProviderBaselineBuilder(repository=store, clock=lambda: END).build(
        ProviderBaselineQuery(
            period_start=START + timedelta(days=14),
            period_end=END,
            expected_interval_days=10,
            scopes=SCOPES,
        )
    )
    document = provider_evidence_bundle_json(
        ProviderEvidenceBundleExporter().export(database, as_of=END)
    )

    report = evaluate_provider_evidence_horizon(document)

    assert not report.eligible_for_readiness_reassessment
    assert all(item.observation_days == 84 for item in report.assessments)
    assert all(item.contract_check_count == 8 for item in report.assessments)
    assert all(item.baseline_observation_days == 70 for item in report.assessments)
    assert all(
        any("baseline horizon is 70.0 days" in blocker for blocker in item.blockers)
        for item in report.assessments
    )


def test_audit_script_writes_content_addressed_reports(tmp_path: Path) -> None:
    database = tmp_path / "script.sqlite3"
    document = _bundle_document(database, SCOPES)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"

    first = subprocess.run(
        [
            sys.executable,
            "scripts/audit_provider_evidence_horizon.py",
            "--bundle",
            str(bundle_path),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [
            sys.executable,
            "scripts/audit_provider_evidence_horizon.py",
            "--bundle",
            str(bundle_path),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    report_document = json.loads(next(output.glob("*.json")).read_text(encoding="utf-8"))
    assert report_document["eligible_for_readiness_reassessment"] is True
    assert len(list(output.iterdir())) == 2


def test_default_required_scope_identity_matches_scheduled_monitor() -> None:
    assert tuple(item.identity for item in required_provider_evidence_scopes()) == (
        ("cninfo_direct", "financial_publication_dates", "china_a", "600000"),
        (
            "cninfo_via_akshare",
            "financial_publication_dates",
            "china_a",
            "600000",
        ),
        ("yahoo_finance", "global_daily_bars", "hong_kong", "0700.HK"),
        ("yahoo_finance", "global_daily_bars", "malaysia", "1155.KL"),
        ("yahoo_finance", "global_daily_bars", "us", "MSFT"),
    )


def _bundle_document(
    database: Path,
    scopes: tuple[ProviderBaselineScope, ...],
) -> dict[str, object]:
    store = SQLiteStore(database)
    store.initialize()
    dates = tuple(START + timedelta(days=12 * index) for index in range(8))
    _save_contract_history(store, scopes, dates)
    ProviderBaselineBuilder(repository=store, clock=lambda: END).build(
        ProviderBaselineQuery(
            period_start=START,
            period_end=END,
            expected_interval_days=11,
            scopes=scopes,
        )
    )
    bundle = ProviderEvidenceBundleExporter().export(database, as_of=END)
    assert serialize_provider_evidence_bundle(bundle)
    return provider_evidence_bundle_json(bundle)


def _save_contract_history(
    store: SQLiteStore,
    scopes: tuple[ProviderBaselineScope, ...],
    dates: tuple[datetime, ...],
) -> None:
    for run_index, checked_at in enumerate(dates):
        run_id = f"run-{run_index}"
        checks = tuple(
            _contract_check(run_id, run_index, scope_index, scope, checked_at)
            for scope_index, scope in enumerate(scopes)
        )
        store.save_provider_contract_run(
            ProviderContractRun(
                run_id=run_id,
                started_at=checked_at,
                completed_at=checked_at,
                status=ProviderContractStatus.HEALTHY,
                checks=checks,
                implementation_version="provider-contract-monitor-test",
            )
        )


def _contract_check(
    run_id: str,
    run_index: int,
    scope_index: int,
    scope: ProviderBaselineScope,
    checked_at: datetime,
) -> ProviderContractCheck:
    is_cninfo = scope.dataset == CNINFO_DISCLOSURES_DATASET
    return ProviderContractCheck(
        check_id=f"check-{run_index}-{scope_index}",
        run_id=run_id,
        provider=scope.provider,
        dataset=scope.dataset,
        market=scope.market,
        subject=scope.subject,
        request_as_of=checked_at,
        status=ProviderContractStatus.HEALTHY,
        records_observed=10,
        trust_level=DataTrustLevel.MEDIUM if is_cninfo else DataTrustLevel.LOW,
        availability_precision=(
            AvailabilityPrecision.EXACT
            if is_cninfo
            else AvailabilityPrecision.RETRIEVAL_TIME
        ),
        latency_ms=10,
        required_fields=("title",) if is_cninfo else ("close", "volume"),
        missing_fields=(),
        limitations=(),
        error_code="",
        checked_at=checked_at,
    )
