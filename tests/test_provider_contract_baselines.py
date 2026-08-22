import json
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tong_quant.data.baselines import (
    ProviderBaselineBuilder,
    ProviderBaselineManifest,
    ProviderBaselineQuery,
    ProviderBaselineScope,
    ProviderContractObservation,
    provider_baseline_json,
    render_provider_baseline_markdown,
    serialize_provider_baseline,
)
from tong_quant.data.providers.contracts import (
    ProviderContractCheck,
    ProviderContractRun,
    ProviderContractStatus,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market

START = datetime(2026, 1, 1, tzinfo=UTC)
END = START + timedelta(days=28)
GENERATED = END + timedelta(hours=1)


@dataclass
class _BaselineRepository:
    observations: tuple[ProviderContractObservation, ...]
    saved: list[ProviderBaselineManifest] = field(default_factory=list)

    def provider_contract_observations(
        self,
        query: ProviderBaselineQuery,
    ) -> tuple[ProviderContractObservation, ...]:
        return self.observations

    def save_provider_baseline(self, manifest: ProviderBaselineManifest) -> str:
        self.saved.append(manifest)
        return manifest.manifest_id


def _scope(market: Market, subject: str) -> ProviderBaselineScope:
    return ProviderBaselineScope(
        provider="evidence_provider",
        dataset="daily_bars",
        market=market,
        subject=subject,
    )


def test_default_baseline_scopes_include_both_cninfo_evidence_paths(
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_provider_contract_baseline.py",
            "--database",
            str(tmp_path / "baseline.sqlite3"),
            "--output-dir",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    document = json.loads(next(output.glob("*.json")).read_text(encoding="utf-8"))
    scopes = {
        (
            item["scope"]["provider"],
            item["scope"]["dataset"],
            item["scope"]["market"],
            item["scope"]["subject"],
        )
        for item in document["entries"]
    }
    assert scopes >= {
        ("cninfo_direct", "china_disclosures", "china_a", "600000"),
        ("cninfo_via_akshare", "china_disclosures", "china_a", "600000"),
    }


def _query() -> ProviderBaselineQuery:
    return ProviderBaselineQuery(
        period_start=START,
        period_end=END,
        expected_interval_days=7,
        scopes=(
            _scope(Market.CHINA_A, "600000"),
            _scope(Market.US, "MSFT"),
            _scope(Market.HONG_KONG, "0700.HK"),
            _scope(Market.MALAYSIA, "1155.KL"),
        ),
    )


def _observation(
    *,
    check_id: str,
    checked_at: datetime,
    status: ProviderContractStatus,
    records_observed: int,
    missing_fields: tuple[str, ...] = (),
    trust_level: DataTrustLevel = DataTrustLevel.MEDIUM,
) -> ProviderContractObservation:
    return ProviderContractObservation(
        check_id=check_id,
        run_id=f"run-{check_id}",
        scope=_scope(Market.US, "MSFT"),
        request_as_of=checked_at,
        checked_at=checked_at,
        status=status,
        records_observed=records_observed,
        trust_level=trust_level,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        required_fields=("close", "volume"),
        missing_fields=missing_fields,
        limitations=("research-grade source",),
        error_code=("TimeoutError" if status is ProviderContractStatus.UNAVAILABLE else ""),
        implementation_version="provider-contract-monitor-test",
    )


def test_baseline_separates_success_field_coverage_and_continuity() -> None:
    observations = (
        _observation(
            check_id="healthy",
            checked_at=START + timedelta(days=1),
            status=ProviderContractStatus.HEALTHY,
            records_observed=5,
        ),
        _observation(
            check_id="failed",
            checked_at=START + timedelta(days=15),
            status=ProviderContractStatus.UNAVAILABLE,
            records_observed=0,
            missing_fields=("close", "volume"),
        ),
    )
    repository = _BaselineRepository(observations)

    manifest = ProviderBaselineBuilder(
        repository=repository,
        clock=lambda: GENERATED,
    ).build(_query())

    us_entry = next(
        entry for entry in manifest.entries if entry.scope.market is Market.US
    )
    assert us_entry.successful_observation_ratio == 0.5
    assert us_entry.field_coverage_ratio == 0.5
    assert us_entry.continuity_ratio == 0.5
    assert us_entry.failed_check_ids == ("failed",)
    assert us_entry.missing_periods == (
        START + timedelta(days=7),
        START + timedelta(days=21),
    )
    assert dict(us_entry.status_counts) == {"healthy": 1, "unavailable": 1}

    empty_markets = {
        entry.scope.market
        for entry in manifest.entries
        if entry.observation_count == 0
    }
    assert empty_markets == {Market.CHINA_A, Market.HONG_KONG, Market.MALAYSIA}
    assert all(
        entry.continuity_ratio == 0
        for entry in manifest.entries
        if not entry.observation_count
    )


def test_identical_observations_produce_identical_hash_without_trust_promotion() -> None:
    observation = _observation(
        check_id="verified-input",
        checked_at=START + timedelta(days=1),
        status=ProviderContractStatus.HEALTHY,
        records_observed=5,
        trust_level=DataTrustLevel.VERIFIED,
    )
    repository = _BaselineRepository((observation,))
    builder = ProviderBaselineBuilder(repository=repository, clock=lambda: GENERATED)
    first = builder.build(_query())
    builder.clock = lambda: GENERATED + timedelta(days=1)
    second = builder.build(_query())

    assert first.baseline_hash == second.baseline_hash
    assert first.input_hash == second.input_hash
    assert first.generated_at != second.generated_at
    assert serialize_provider_baseline(first) == serialize_provider_baseline(second)
    assert render_provider_baseline_markdown(first) == render_provider_baseline_markdown(
        second
    )
    document = provider_baseline_json(first)
    assert "assessed_trust_level" not in str(document)
    assert "never promotes" in str(document["trust_policy"])
    assert "does not upgrade" in render_provider_baseline_markdown(first)
    tampered_entries = (
        replace(first.entries[0], continuity_ratio=0.25),
        *first.entries[1:],
    )
    with pytest.raises(ValueError, match="hash does not match"):
        replace(first, entries=tampered_entries)


def test_sqlite_baseline_is_immutable_idempotent_and_reconstructable(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "baseline.sqlite3")
    store.initialize()
    check = ProviderContractCheck(
        check_id="check-1",
        run_id="run-1",
        provider="evidence_provider",
        dataset="daily_bars",
        market=Market.US,
        subject="MSFT",
        request_as_of=START + timedelta(days=1),
        status=ProviderContractStatus.DEGRADED,
        records_observed=3,
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        latency_ms=25.0,
        required_fields=("close", "volume"),
        missing_fields=(),
        limitations=("research-grade source",),
        error_code="",
        checked_at=START + timedelta(days=1),
    )
    store.save_provider_contract_run(
        ProviderContractRun(
            run_id="run-1",
            started_at=START,
            completed_at=START + timedelta(minutes=1),
            status=ProviderContractStatus.DEGRADED,
            checks=(check,),
            implementation_version="provider-contract-monitor-test",
        )
    )
    query = ProviderBaselineQuery(
        period_start=START,
        period_end=END,
        expected_interval_days=7,
        scopes=(_scope(Market.US, "MSFT"),),
    )
    builder = ProviderBaselineBuilder(repository=store, clock=lambda: GENERATED)

    first = builder.build(query)
    second = builder.build(query)

    assert first.baseline_hash == second.baseline_hash
    assert store.table_count("provider_baseline_manifests") == 1
    assert store.table_count("provider_baseline_entries") == 1
    assert store.table_count("provider_baseline_inputs") == 1
    stored = store.provider_baseline_manifest(first.manifest_id)
    assert stored is not None
    assert stored["input_hash"] == first.input_hash
    assert store.provider_baseline_entries(first.manifest_id)[0][
        "continuity_ratio"
    ] == 0.25
    assert store.provider_baseline_inputs(first.manifest_id)[0]["check_id"] == "check-1"
