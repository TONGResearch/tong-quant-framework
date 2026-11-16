"""Reviewed issuer values retain manual provenance and conservative PIT visibility."""

import json
import subprocess
import sys
import tomllib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.filing_facts import ingest_filing_extraction, prepare_filing_extraction
from tong_quant.data.filing_inputs import ReviewedFinancialInputReader
from tong_quant.data.financial_inputs import FinancialBindingStatus
from tong_quant.data.ingestion import ProviderNeutralIngestionService
from tong_quant.data.providers.cninfo_direct import (
    CnInfoArtifactDownload,
    CnInfoDirectEvidenceAdapter,
    CnInfoQueryResult,
)
from tong_quant.data.providers.contracts import (
    CNINFO_DISCLOSURES_DATASET,
    ProviderArtifactStatus,
    ProviderDatasetRequest,
)
from tong_quant.data.providers.reviewed_filings import (
    REVIEWED_FILING_DATASET,
    ReviewedFilingAdapter,
    ReviewedFilingRow,
    parse_filing_review,
)
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import AssetType, DataTrustLevel, Market
from tong_quant.domain.models import Instrument
from tong_quant.research.financial.comparisons import (
    FinancialComparisonStatus,
    financial_comparisons,
)
from tong_quant.research.financial.trailing import TrailingEditionReview, trailing_input_hash

NOW = datetime(2026, 10, 18, 16, tzinfo=UTC)
CAPTURED = NOW - timedelta(minutes=5)
PUBLISHED = datetime(2026, 4, 30, tzinfo=UTC)
PDF = b"%PDF-1.4\nsynthetic-not-an-authenticated-financial-statement"


class _Client:
    def search(self, *args, **kwargs):
        return CnInfoQueryResult(({
            "secCode": "600000", "secName": "Fixture bank", "orgId": "fixture",
            "announcementId": "1234567890", "announcementTitle": "Quarterly report",
            "announcementTime": int(PUBLISHED.timestamp() * 1000),
            "adjunctUrl": "finalpage/2026-04-30/1234567890.PDF",
        },), "f" * 64, 1, 1, 1, False)

    def download_artifact(self, url):
        return CnInfoArtifactDownload(
            ProviderArtifactStatus.CAPTURED, url, url, "application/pdf", PDF, "",
        )


def _plan():
    return tomllib.loads(Path("config/filing-extractions/600000-2026q1.toml").read_text())


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "facts.sqlite3")
    store.initialize()
    store.upsert_instruments((Instrument(
        "600000", Market.CHINA_A, "Preserved bank metadata", available_at=PUBLISHED,
        exchange="SSE", industry="bank", lot_size=100, source="original metadata",
    ),))
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    adapter = CnInfoDirectEvidenceAdapter(client=_Client(), clock=lambda: CAPTURED)
    request = ProviderDatasetRequest(
        CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "600000", NOW, {
            "start_date": "2026-04-30", "end_date": "2026-04-30",
            "capture_artifacts": "true", "max_artifacts": "1",
        },
    )
    source = adapter.fetch(request).artifacts[0]
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        adapter, request,
    )
    plan = _plan()
    plan["review"].update({
        "filing_artifact_id": source.artifact_id, "filing_sha256": source.content_hash,
        "reviewed_at": NOW.isoformat(), "reviewer": "synthetic manual test review",
    })
    review = parse_filing_review(plan)
    return store, artifacts, review, source


def test_atomic_fact_evidence_publication_is_idempotent_and_time_bounded(foundation):
    store, artifacts, review, _ = foundation
    before = store.get_instrument("600000", Market.CHINA_A, AssetType.EQUITY, as_of=NOW)
    first = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    second = ingest_filing_extraction(store, artifacts, review, as_of=NOW + timedelta(seconds=1))
    assert first.accepted == second.accepted == 3
    assert store.table_count("fundamental_facts") == 3
    assert store.table_count("provider_artifacts") == 2
    assert store.get_instrument("600000", Market.CHINA_A, AssetType.EQUITY, as_of=NOW) == before
    records = store.provider_evidence(
        provider="cninfo_direct", dataset=REVIEWED_FILING_DATASET,
        market=Market.CHINA_A, subject="600000", as_of=NOW,
    )
    assert len(records) == 3
    assert all(row.available_at == NOW and row.trust_level is DataTrustLevel.LOW for row in records)
    assert all(row.payload["reporting_scope"] == "group" for row in records)
    assert all(not row.payload["native_mapping_authorized"] for row in records)
    service = MarketDataService(store)
    for metric, expected in (("revenue", "46573000000"),
                             ("profit_attributable_to_parent", "17861000000"),
                             ("total_assets", "10305646000000")):
        assert not service.fundamental_facts(
            "600000", Market.CHINA_A, AssetType.EQUITY, metric,
            as_of=NOW - timedelta(microseconds=1),
        )
        (fact,) = service.fundamental_facts(
            "600000", Market.CHINA_A, AssetType.EQUITY, metric, as_of=NOW,
        )
        assert fact.value == Decimal(expected)
        assert fact.raw_data_hash == records[0].raw_data_hash
        assert fact.batch_id == first.batch_id
        assert fact.unit == "absolute" and fact.currency == "CNY"
        assert fact.available_at == NOW and fact.published_at == PUBLISHED
        assert fact.availability_precision.value == "retrieval_time"
        assert fact.trust_level is DataTrustLevel.LOW
    assert store.table_count("research_reports") == store.table_count("validation_reports") == 0


def test_failed_canonical_write_rolls_back_evidence_but_retains_unregistered_packet(
    foundation, monkeypatch,
):
    store, artifacts, review, _ = foundation
    counts = {name: store.table_count(name) for name in (
        "fundamental_facts", "provider_evidence_records", "provider_artifacts", "ingestion_batches",
    )}
    files = {path: sha256(path.read_bytes()).hexdigest()
             for path in artifacts.root.rglob("*") if path.is_file()}
    original = store.upsert_fundamental_facts

    def fail(facts):
        original(facts)
        raise RuntimeError("synthetic failure after canonical writes")

    monkeypatch.setattr(store, "upsert_fundamental_facts", fail)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    assert {name: store.table_count(name) for name in counts} == counts
    for path, digest in files.items():
        assert sha256(path.read_bytes()).hexdigest() == digest
    retained = [path for path in artifacts.root.rglob("*.bin") if path not in files]
    assert len(retained) == 1
    packet = retained[0].read_bytes()
    assert retained[0].stem == sha256(packet).hexdigest()
    assert json.loads(packet)["source_artifact_id"] == review.filing_artifact_id


def test_same_version_conflict_is_rejected_and_later_review_preserves_old_view(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    changed_row = replace(review.rows[0], source_value=Decimal("1"))
    changed = replace(review, rows=(changed_row, *review.rows[1:]))
    with pytest.raises(ValueError, match="conflict"):
        ingest_filing_extraction(store, artifacts, changed, as_of=NOW)
    assert store.table_count("fundamental_facts") == 3
    later = NOW + timedelta(seconds=1)
    ingest_filing_extraction(store, artifacts, replace(changed, reviewed_at=later), as_of=later)
    old = store.fundamental_facts("600000", Market.CHINA_A, AssetType.EQUITY, "revenue", as_of=NOW)
    new = store.fundamental_facts(
        "600000", Market.CHINA_A, AssetType.EQUITY, "revenue", as_of=later,
    )
    assert old[0].value == Decimal("46573000000") and new[0].value == Decimal("1000000")


@pytest.mark.parametrize(("value", "expected"), [
    ("0", "0"), ("-1.25", "-1250000"),
    ("12345678901234567890.123456", "12345678901234567890123456"),
])
def test_source_decimals_keep_zero_negative_and_precision(foundation, value, expected):
    store, artifacts, review, _ = foundation
    review = replace(review, rows=(replace(review.rows[0], source_value=Decimal(value)),))
    prepared = prepare_filing_extraction(store, artifacts, review, as_of=NOW)
    assert prepared.facts("")[0].value == Decimal(expected)


@pytest.mark.parametrize("change", [
    {"reporting_scope": "company"}, {"source_unit": "unknown"}, {"currency": "USD"},
    {"source_column": "prior_period"}, {"audit_status": "unknown"},
    {"filing_sha256": "g" * 64}, {"sector_profile": "arbitrary"}, {"rows": ()},
    {"period_end": date(2027, 3, 31)}, {"reviewed_at": NOW.replace(tzinfo=None)},
    {"reviewer": "secret=fixture-not-a-real-credential"},
])
def test_rejects_unsupported_or_ambiguous_review_semantics(foundation, change):
    _, _, review, _ = foundation
    with pytest.raises(ValueError):
        replace(review, **change)


@pytest.mark.parametrize("change", [
    {"source_value": Decimal("NaN")}, {"source_value": Decimal("Infinity")},
    {"source_value": Decimal("1e101")}, {"source_value": 10.0},
    {"source_pages": (True,)}, {"source_pages": (0,)}, {"source_pages": (17, 17)},
    {"source_pages": [17]},
    {"period_start": None}, {"metric": "profit"}, {"statement": "cash_flow"},
])
def test_rejects_invalid_row_values_and_unsupported_mappings(foundation, change):
    _, _, review, _ = foundation
    with pytest.raises(ValueError):
        replace(review.rows[0], **change)


@pytest.mark.parametrize("defect", [
    "future_review", "wrong_filing", "wrong_hash", "missing_source", "tampered_bytes",
    "wrong_subject", "future_capture", "unapproved_url", "identity", "unknown_trust",
])
def test_source_bindings_and_trust_ceiling(foundation, defect):
    store, artifacts, review, source = foundation
    if defect == "unknown_trust":
        batch = ReviewedFilingAdapter(
            review, replace(source, trust_level=DataTrustLevel.UNKNOWN),
        ).fetch(
            ProviderDatasetRequest(REVIEWED_FILING_DATASET, Market.CHINA_A, "600000", NOW),
        )
        assert all(item.trust_level is DataTrustLevel.UNKNOWN for item in batch.records)
        return
    if defect == "future_review":
        review = replace(review, reviewed_at=NOW + timedelta(seconds=1))
    elif defect == "wrong_filing":
        review = replace(review, filing_artifact_id="a" * 64)
    elif defect == "wrong_hash":
        review = replace(review, filing_sha256="a" * 64)
    elif defect == "missing_source":
        with store._connect() as connection:
            connection.execute("DELETE FROM provider_artifact_observations")
    elif defect == "tampered_bytes":
        (next(artifacts.root.rglob("*.pdf"))).write_bytes(b"%PDF-changed")
    else:
        if defect == "wrong_subject":
            source = replace(source, subject="600001")
        elif defect == "future_capture":
            source = replace(source, retrieved_at=NOW + timedelta(seconds=1))
        elif defect == "unapproved_url":
            source = replace(source, source_reference="https://example.com/report.pdf")
        elif defect == "identity":
            source = replace(source, artifact_id="a" * 64)
        with pytest.raises(ValueError):
            ReviewedFilingAdapter(review, source).fetch(
                ProviderDatasetRequest(REVIEWED_FILING_DATASET, Market.CHINA_A, "600000", NOW),
            )
        return
    with pytest.raises((ValueError, FileNotFoundError)):
        prepare_filing_extraction(store, artifacts, review, as_of=NOW)
    assert store.table_count("fundamental_facts") == 0


def test_parser_does_not_accept_spot_review_or_float_values():
    with pytest.raises(ValueError, match="schema mismatch"):
        parse_filing_review(tomllib.loads(Path("config/financial-reviews/600000-2026q1.toml").read_text()))
    plan = _plan()
    plan["rows"][0]["source_value"] = 46573.0
    with pytest.raises(ValueError, match="quoted decimals"):
        parse_filing_review(plan)


def test_cli_preview_write_and_missing_database_are_explicit(foundation, tmp_path):
    store, artifacts, review, _ = foundation
    plan = Path("config/filing-extractions/600000-2026q1.toml").read_text()
    plan = plan.replace("2a5b84236a193ecb68d65af262bebe4189d2f19fd9f849e139febb05581463f1",
                        review.filing_artifact_id)
    plan = plan.replace("df6911eb74bd5448fbf7729936979c60391052746db7d0577e4d4803f38d77e1",
                        review.filing_sha256)
    plan = plan.replace("2026-10-18T15:49:13+00:00", NOW.isoformat())
    review_path = tmp_path / "review.toml"
    review_path.write_text(plan)
    args = [sys.executable, "scripts/ingest_reviewed_filing.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--review-plan", str(review_path),
            "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    process = subprocess.run(args, capture_output=True, text=True, check=False)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["mode"] == "preview"
    assert store.path.read_bytes() == before
    assert store.table_count("fundamental_facts") == 0
    write = subprocess.run([*args, "--write"], capture_output=True, text=True, check=False)
    assert write.returncode == 0, write.stderr
    assert json.loads(write.stdout)["accepted"] == 3
    assert store.table_count("fundamental_facts") == 3
    missing = tmp_path / "missing.sqlite3"
    args[args.index(str(store.path))] = str(missing)
    assert subprocess.run(args, capture_output=True, check=False).returncode != 0
    assert not missing.exists()


def _read_inputs(store, artifacts, *, as_of=NOW, sector="bank", metrics=None):
    return ReviewedFinancialInputReader(store, artifacts).read(
        "600000", Market.CHINA_A,
        metrics or ("revenue", "profit_attributable_to_parent", "total_assets"),
        as_of=as_of, sector_profile=sector,
    )


def test_source_reader_binds_facts_without_writes_or_scoring_approval(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    before = store.path.read_bytes()
    reader = ReviewedFinancialInputReader(SQLiteStore(store.path, read_only=True), artifacts)
    metrics = ("revenue", "profit_attributable_to_parent", "total_assets")
    first = reader.read("600000", Market.CHINA_A, metrics, as_of=NOW, sector_profile="bank")
    second = reader.read("600000", Market.CHINA_A, tuple(reversed(metrics)),
                         as_of=NOW, sector_profile="bank")
    assert first == second and first.input_hash == second.input_hash
    assert first.source_binding_complete
    assert all(entry.status is FinancialBindingStatus.SOURCE_BOUND for entry in first.inspections)
    assert all(entry.reporting_scope == "group" and entry.sector_profile == "bank"
               and entry.audit_status == "unaudited" for entry in first.inspections)
    assert not first.document()["investment_scoring_authorized"]
    assert not first.document()["historical_replay_eligible"]
    assert store.path.read_bytes() == before
    partial = _read_inputs(store, artifacts, metrics=("revenue", "roe", "roic"))
    assert partial.missing_metrics == ("roe", "roic") and not partial.source_binding_complete
    assert len(partial.inspections) == 1
    earlier = _read_inputs(store, artifacts, as_of=NOW - timedelta(microseconds=1))
    assert not earlier.inspections and len(earlier.missing_metrics) == 3


@pytest.mark.parametrize("defect", [
    "value", "currency", "unit", "revision", "fact_batch", "future_fact_batch",
    "failed_batch", "hash_batch", "missing_batch_completion", "wrong_batch_provider",
    "packet_bytes", "pdf_bytes", "packet_key", "packet_size", "packet_trust",
    "packet_batch", "packet_capture", "packet_version", "evidence_value",
    "evidence_trust", "evidence_batch", "missing_evidence", "source_key", "source_size",
    "future_source_batch", "missing_source_observation",
    "wrong_batch_parameters", "wrong_batch_start", "source_subject",
])
def test_source_reader_retains_rejected_facts_after_binding_defects(foundation, defect):
    store, artifacts, review, source = foundation
    result = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    packet = next(artifacts.root.rglob("*.bin"))
    with store._connect() as connection:
        if defect == "value":
            connection.execute("UPDATE fundamental_facts SET value = '999'")
        elif defect == "currency":
            connection.execute("UPDATE fundamental_facts SET currency = 'USD'")
        elif defect == "unit":
            connection.execute("UPDATE fundamental_facts SET unit = 'million'")
        elif defect == "revision":
            connection.execute("UPDATE fundamental_facts SET revision = 1")
        elif defect == "fact_batch":
            connection.execute("UPDATE fundamental_facts SET batch_id = ''")
        elif defect in {"future_fact_batch", "failed_batch", "hash_batch",
                        "missing_batch_completion", "wrong_batch_provider",
                        "wrong_batch_parameters", "wrong_batch_start"}:
            column, value = {
                "future_fact_batch": ("completed_at", (NOW + timedelta(days=1)).isoformat()),
                "failed_batch": ("status", "failed"), "hash_batch": ("raw_response_hash", "a" * 64),
                "missing_batch_completion": ("completed_at", None),
                "wrong_batch_provider": ("provider", "unrelated"),
                "wrong_batch_parameters": ("parameters_json", '{"subject":"600001"}'),
                "wrong_batch_start": ("started_at", (NOW - timedelta(days=1)).isoformat()),
            }[defect]
            connection.execute(f"UPDATE ingestion_batches SET {column} = ? WHERE batch_id = ?",
                               (value, result.batch_id))
        elif defect == "packet_bytes":
            packet.write_bytes(b"{}")
        elif defect == "pdf_bytes":
            next(artifacts.root.rglob("*.pdf")).write_bytes(b"%PDF-changed")
        elif defect in {"packet_key", "packet_size", "packet_trust", "packet_batch",
                        "packet_capture", "packet_version"}:
            source_batch = store.provider_artifact(source.artifact_id)["first_batch_id"]
            column, value = {
                "packet_key": ("storage_key", "incorrect.bin"),
                "packet_size": ("byte_size", 1), "packet_trust": ("trust_level", "verified"),
                "packet_batch": ("first_batch_id", source_batch),
                "packet_capture": ("first_retrieved_at", (NOW + timedelta(days=1)).isoformat()),
                "packet_version": ("model_version", "unrelated-version"),
            }[defect]
            connection.execute(f"UPDATE provider_artifacts SET {column} = ? "
                               "WHERE dataset = ?", (value, REVIEWED_FILING_DATASET))
        elif defect == "evidence_value":
            rows = connection.execute("SELECT evidence_id, payload_json "
                                      "FROM provider_evidence_records "
                                      "WHERE dataset = ?", (REVIEWED_FILING_DATASET,)).fetchall()
            for row in rows:
                payload = json.loads(row["payload_json"])
                payload["value"] = "999"
                connection.execute("UPDATE provider_evidence_records SET payload_json = ? "
                                   "WHERE evidence_id = ?",
                                   (json.dumps(payload), row["evidence_id"]))
        elif defect == "evidence_trust":
            connection.execute("UPDATE provider_evidence_records SET trust_level = 'verified' "
                               "WHERE dataset = ?", (REVIEWED_FILING_DATASET,))
        elif defect == "evidence_batch":
            source_batch = store.provider_artifact(source.artifact_id)["first_batch_id"]
            connection.execute("UPDATE provider_evidence_records SET batch_id = ? "
                               "WHERE dataset = ?", (source_batch, REVIEWED_FILING_DATASET))
        elif defect == "missing_evidence":
            connection.execute("DELETE FROM provider_evidence_records WHERE dataset = ?",
                               (REVIEWED_FILING_DATASET,))
        elif defect in {"source_key", "source_size", "source_subject"}:
            column, value = {
                "source_key": ("storage_key", "incorrect.pdf"),
                "source_size": ("byte_size", 1), "source_subject": ("subject", "600001"),
            }[defect]
            connection.execute(f"UPDATE provider_artifacts SET {column} = ? "
                               "WHERE artifact_id = ?", (value, source.artifact_id))
        elif defect == "future_source_batch":
            source_batch = store.provider_artifact(source.artifact_id)["first_batch_id"]
            connection.execute("UPDATE ingestion_batches SET completed_at = ? WHERE batch_id = ?",
                               ((NOW + timedelta(days=1)).isoformat(), source_batch))
        elif defect == "missing_source_observation":
            connection.execute("DELETE FROM provider_artifact_observations")
    snapshot = _read_inputs(store, artifacts)
    assert len(snapshot.inspections) == 3 and not snapshot.missing_metrics
    assert all(entry.status is FinancialBindingStatus.REJECTED for entry in snapshot.inspections)
    assert not snapshot.source_binding_complete
    assert store.table_count("fundamental_facts") == 3


def test_source_reader_checks_sector_and_preserves_unsupported_sources(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    mismatch = _read_inputs(store, artifacts, sector="nonfinancial")
    assert all(row.status is FinancialBindingStatus.REJECTED for row in mismatch.inspections)
    with store._connect() as connection:
        connection.execute("UPDATE fundamental_facts SET provider_dataset = 'legacy-unreviewed'")
    unsupported = _read_inputs(store, artifacts)
    assert all(row.status is FinancialBindingStatus.UNSUPPORTED for row in unsupported.inspections)
    assert len(unsupported.inspections) == 3


def test_batch_completion_is_required_in_addition_to_claimed_availability(foundation):
    store, artifacts, review, _ = foundation
    later = NOW + timedelta(minutes=1)
    ingest_filing_extraction(store, artifacts, review, as_of=later)
    early = _read_inputs(store, artifacts)
    assert all(row.status is FinancialBindingStatus.REJECTED for row in early.inspections)
    assert _read_inputs(store, artifacts, as_of=later).source_binding_complete


@pytest.mark.parametrize("metrics", [(), ("revenue", "revenue"), ("",)])
def test_source_reader_rejects_ambiguous_query_metrics(foundation, metrics):
    store, artifacts, _, _ = foundation
    with pytest.raises(ValueError):
        ReviewedFinancialInputReader(store, artifacts).read(
            "600000", Market.CHINA_A, metrics, as_of=NOW, sector_profile="bank",
        )


def test_financial_input_cli_preserves_partial_results_and_never_overwrites(foundation, tmp_path):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    output = tmp_path / "source-inputs.json"
    args = [sys.executable, "scripts/inspect_financial_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics", "revenue",
            "roe", "--sector-profile", "bank", "--as-of", NOW.isoformat(), "--output", str(output)]
    before = store.path.read_bytes()
    process = subprocess.run(args, capture_output=True, text=True, check=False)
    assert process.returncode == 2, process.stderr
    document = json.loads(output.read_text())
    assert document["missing_metrics"] == ["roe"]
    assert document["inspections"][0]["status"] == "source_bound_observation"
    assert not document["investment_scoring_authorized"]
    assert not document["source_binding_complete"]
    assert output.stat().st_mode & 0o777 == 0o600
    assert store.path.read_bytes() == before
    assert subprocess.run(args, capture_output=True, check=False).returncode == 2
    assert json.loads(output.read_text()) == document
    comparison_output = tmp_path / "comparison-inputs.json"
    args[args.index(str(output))] = str(comparison_output)
    result = subprocess.run([*args, "--comparisons"], capture_output=True, check=False)
    assert result.returncode == 2
    exported = json.loads(comparison_output.read_text())
    assert all(row["status"] == "unavailable" for row in exported["comparisons"])
    assert all(not row["investment_scoring_authorized"] for row in exported["comparisons"])


def _comparative_reviews(review):
    common = {"filing_period_end": review.period_end,
              "comparability": "as_presented_same_filing", "issuer_revision_status": "unverified"}
    flows = tuple(replace(row, source_value=Decimal({
        "revenue": "45922", "profit_attributable_to_parent": "17598",
    }[row.metric]), period_start=date(2025, 1, 1), source_label=f"Comparative {row.metric}")
                  for row in review.rows if row.statement == "income")
    stock = tuple(replace(row, source_value=Decimal("10081746"),
                          source_label="Comparative assets")
                  for row in review.rows if row.statement == "balance")
    return (
        replace(review, **common, period_end=date(2025, 3, 31),
                source_column="group_prior_year_period", rows=flows),
        replace(review, **common, period_end=date(2025, 12, 31), audit_status="audited",
                source_column="group_prior_year_end", rows=stock),
    )


def _ratio_review(review):
    return replace(
        review, source_unit="percent", currency="not_applicable",
        measurement_basis="period_end_ratio",
        rows=tuple(ReviewedFilingRow(metric, "bank_asset_quality", Decimal(value), None,
                                    (2, 12), "Synthetic group period-end percent observation")
                   for metric, value in (("nonperforming_loan_ratio", "1.23"),
                                         ("provision_coverage_ratio", "204.79"))),
    )


def test_bank_ratios_preserve_percent_not_money_or_fractions_with_source_and_cutoff(foundation):
    store, artifacts, review, _ = foundation
    ratio = _ratio_review(review)
    packet = prepare_filing_extraction(store, artifacts, ratio, as_of=NOW).batch
    assert ratio.model_version == "reviewed-bank-period-end-ratios-v3"
    assert json.loads(packet.artifacts[0].content)["review"]["measurement_basis"] == (
        "period_end_ratio")
    for row in packet.records:
        assert row.payload["currency"] is None and row.payload["unit"] == "percent"
        assert row.payload["value_kind"] == "ratio"
    first = ingest_filing_extraction(store, artifacts, ratio, as_of=NOW)
    second = ingest_filing_extraction(store, artifacts, ratio, as_of=NOW + timedelta(seconds=1))
    assert first.accepted == second.accepted == 2
    assert store.table_count("fundamental_facts") == 2
    metrics = ("nonperforming_loan_ratio", "provision_coverage_ratio")
    snapshot = _read_inputs(store, artifacts, metrics=metrics)
    assert snapshot.source_binding_complete
    assert snapshot.input_hash == _read_inputs(store, artifacts, metrics=metrics).input_hash
    assert [entry.fact.value for entry in snapshot.inspections] == [Decimal("1.23"),
                                                                  Decimal("204.79")]
    for entry in snapshot.inspections:
        assert entry.fact.currency is None and entry.fact.unit == "percent"
        assert entry.fact.period_start is None and entry.fact.available_at == NOW
        assert entry.fact.batch_id == first.batch_id
        assert entry.fact.trust_level is DataTrustLevel.LOW
        assert entry.measurement_basis == "period_end_ratio"
    assert not snapshot.document()["investment_scoring_authorized"]
    assert not snapshot.document()["historical_replay_eligible"]
    assert all(item.status is FinancialComparisonStatus.UNAVAILABLE
               and item.amount_change is None and item.change_percent is None
               for item in financial_comparisons(snapshot))
    assert not _read_inputs(store, artifacts, as_of=NOW - timedelta(microseconds=1),
                            metrics=metrics).inspections
    assert all(entry.status is FinancialBindingStatus.REJECTED
               for entry in _read_inputs(store, artifacts, metrics=metrics,
                                         sector="nonfinancial").inspections)


@pytest.mark.parametrize("change", [
    {"source_unit": "CNY_million"}, {"source_unit": "fraction"}, {"currency": "CNY"},
    {"measurement_basis": None}, {"measurement_basis": "annualized"},
    {"measurement_basis": "ytd_ratio"}, {"sector_profile": "nonfinancial"},
    {"reporting_scope": "parent"}, {"source_column": "group_prior_year_end"},
    {"filing_period_end": date(2026, 6, 30)},
])
def test_bank_ratio_review_rejects_inferred_unit_period_scope_or_annualization(foundation, change):
    _, _, review, _ = foundation
    with pytest.raises(ValueError):
        replace(_ratio_review(review), **change)


def test_ratio_and_monetary_rows_cannot_share_review_units(foundation):
    _, _, review, _ = foundation
    ratio = _ratio_review(review)
    with pytest.raises(ValueError):
        replace(ratio, rows=(*ratio.rows, review.rows[0]))
    with pytest.raises(ValueError):
        replace(review, measurement_basis="period_end_ratio")


@pytest.mark.parametrize("metric,value,start", [
    ("nonperforming_loan_ratio", "101", None),
    ("nonperforming_loan_ratio", "-1", None),
    ("provision_coverage_ratio", "-1", None),
    ("provision_coverage_ratio", "1", date(2026, 1, 1)),
    ("roe", "2.32", None),
])
def test_bank_ratio_row_rejects_invalid_ranges_flow_periods_and_unsupported_definitions(
    metric, value, start,
):
    with pytest.raises(ValueError):
        ReviewedFilingRow(metric, "bank_asset_quality", Decimal(value), start, (2,), "Fixture")


@pytest.mark.parametrize("change", [
    {"unit": "fraction"}, {"currency": "CNY"}, {"value": Decimal("1230000")},
])
def test_bank_ratio_source_reader_preserves_tampered_rows_as_rejected(foundation, change):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _ratio_review(review), as_of=NOW)
    with store._connect() as connection:
        field, value = next(iter(change.items()))
        connection.execute(f"UPDATE fundamental_facts SET {field} = ?", (str(value),))
    snapshot = _read_inputs(store, artifacts, metrics=("nonperforming_loan_ratio",
                                                     "provision_coverage_ratio"))
    assert len(snapshot.inspections) == 2 and not snapshot.missing_metrics
    assert all(entry.status is FinancialBindingStatus.REJECTED for entry in snapshot.inspections)


def test_monetary_packet_shapes_omit_new_ratio_field_for_both_prior_versions(foundation):
    store, artifacts, review, _ = foundation
    for old in (review, *_comparative_reviews(review)):
        packet = prepare_filing_extraction(store, artifacts, old, as_of=NOW).batch
        assert "measurement_basis" not in json.loads(packet.artifacts[0].content)["review"]
        assert all("measurement_basis" not in row.payload for row in packet.records)


def test_committed_bank_plan_parses_with_separate_percentage_semantics():
    plan = tomllib.loads(Path(
        "config/filing-extractions/600000-2026q1-bank-ratios.toml").read_text())
    review = parse_filing_review(plan)
    assert review.measurement_basis == "period_end_ratio" and len(review.rows) == 2
    assert review.rows[1].source_value == Decimal("204.79")


def test_bank_input_cli_preserves_realistic_gaps_and_does_not_mutate_database(foundation, tmp_path):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    ingest_filing_extraction(store, artifacts, _ratio_review(review), as_of=NOW)
    from tong_quant.research.financial.inputs import BANK_INPUT_REQUIREMENTS

    output = tmp_path / "bank-inputs.json"
    args = [sys.executable, "scripts/inspect_financial_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics",
            *(item.metric for item in BANK_INPUT_REQUIREMENTS), "--sector-profile", "bank",
            "--as-of", NOW.isoformat(), "--bank-inputs", "--output", str(output)]
    before = store.path.read_bytes()
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stderr
    report = json.loads(output.read_text())["bank_input_assessment"]
    assert len(report["checks"]) == 9
    assert sum(item["status"] == "observed_unqualified" for item in report["checks"]) == 4
    assert sum(item["status"] == "missing" for item in report["checks"]) == 5
    assert all(item["freshness"] == "unassessed" for item in report["checks"])
    assert not report["investment_scoring_authorized"]
    args[args.index(str(output))] = str(tmp_path / "age-inputs.json")
    result = subprocess.run([*args, "--bank-max-report-age-days", "180"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stderr
    aged = json.loads((tmp_path / "age-inputs.json").read_text())["bank_input_assessment"]
    assert sum(item["freshness"] == "stale" for item in aged["checks"]) == 4
    assert aged["policy_hash"] != report["policy_hash"]
    assert output.stat().st_mode & 0o777 == 0o600
    assert store.path.read_bytes() == before


def test_v1_packet_golden_hash_survives_comparative_contract_expansion(foundation):
    store, artifacts, review, _ = foundation
    packet = prepare_filing_extraction(store, artifacts, review, as_of=NOW).batch
    assert packet.raw_data_hash == (
        "35acd0282da9eb451608d74dccb4ef12d75ae1a28512afe434a22b1796c850a2"
    )
    assert "filing_period_end" not in json.loads(packet.artifacts[0].content)["review"]


def test_comparative_population_retains_six_source_bound_retrieval_time_observations(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    later = NOW + timedelta(minutes=1)
    comparisons = _comparative_reviews(review)
    for comparative in comparisons:
        comparative = replace(comparative, reviewed_at=later)
        ingest_filing_extraction(store, artifacts, comparative, as_of=later)
        ingest_filing_extraction(store, artifacts, comparative, as_of=later)
    assert store.table_count("fundamental_facts") == 6
    old = _read_inputs(store, artifacts)
    new = _read_inputs(store, artifacts, as_of=later)
    assert len(old.inspections) == 3 and len(new.inspections) == 6
    assert new.source_binding_complete
    assert all(row.status is FinancialBindingStatus.SOURCE_BOUND for row in new.inspections)
    assert all(row.fact.trust_level is DataTrustLevel.LOW for row in new.inspections)
    assert all(row.fact.published_at == PUBLISHED for row in new.inspections)
    by_metric = {item.metric: item for item in financial_comparisons(new)}
    expected = {"revenue": ("yoy_ytd", "651000000", "1.4176"),
                "profit_attributable_to_parent": ("yoy_ytd", "263000000", "1.4945"),
                "total_assets": ("since_prior_year_end", "223900000000", "2.2208")}
    for metric, (kind, amount, percentage) in expected.items():
        item = by_metric[metric]
        assert item.status is FinancialComparisonStatus.DESCRIPTIVE and item.kind == kind
        assert item.amount_change == Decimal(amount) and item.change_percent == Decimal(percentage)
        assert not item.document()["investment_scoring_authorized"]
        assert len(item.evidence_ids) == 2
    assert financial_comparisons(new) == financial_comparisons(new)


@pytest.mark.parametrize("field,value", [
    ("filing_period_end", None), ("filing_period_end", date(2024, 3, 31)),
    ("filing_period_end", date(2026, 4, 30)), ("filing_period_end", date(2027, 3, 31)),
    ("comparability", "original_history"), ("issuer_revision_status", "verified_no_restatement"),
    ("source_column", "group_current_period"), ("period_end", date(2025, 6, 30)),
])
def test_comparative_review_rejects_implicit_or_wrong_edition_period_and_revision_claims(
    foundation, field, value,
):
    _, _, review, _ = foundation
    flow, _ = _comparative_reviews(review)
    with pytest.raises(ValueError):
        replace(flow, **{field: value})


def test_comparative_flow_cannot_be_a_single_quarter_or_balance_column(foundation):
    _, _, review, _ = foundation
    flow, stock = _comparative_reviews(review)
    with pytest.raises(ValueError):
        replace(flow, rows=(replace(flow.rows[0], period_start=date(2025, 2, 1)),))
    with pytest.raises(ValueError):
        replace(stock, source_column="group_prior_year_period")
    with pytest.raises(ValueError):
        replace(stock, period_end=date(2025, 9, 30))


@pytest.mark.parametrize("baseline", ["0", "-100"])
def test_nonpositive_comparative_baseline_is_not_a_growth_percentage(foundation, baseline):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    flow, _ = _comparative_reviews(review)
    flow = replace(flow, rows=tuple(replace(row, source_value=Decimal(baseline))
                                   for row in flow.rows))
    ingest_filing_extraction(store, artifacts, flow, as_of=NOW)
    by_metric = {item.metric: item
                 for item in financial_comparisons(_read_inputs(store, artifacts))}
    for metric in ("revenue", "profit_attributable_to_parent"):
        assert by_metric[metric].status is FinancialComparisonStatus.NONPOSITIVE_BASE
        assert by_metric[metric].change_percent is None
        assert by_metric[metric].amount_change is not None


@pytest.mark.parametrize("defect", ["different_filing", "wrong_window", "rejected_latest",
                                    "ambiguous_latest", "missing_comparative", "numeric_bounds"])
def test_descriptive_comparison_rejects_mismatches_and_never_falls_back(foundation, defect):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    flow, _ = _comparative_reviews(review)
    ingest_filing_extraction(store, artifacts, flow, as_of=NOW)
    snapshot = _read_inputs(store, artifacts, metrics=("revenue",))
    prior, current = snapshot.inspections
    if defect == "different_filing":
        prior = replace(prior, filing_sha256="e" * 64)
    elif defect == "wrong_window":
        prior = replace(prior, fact=replace(prior.fact, period_start=date(2025, 2, 1)))
    elif defect == "rejected_latest":
        current = replace(current, status=FinancialBindingStatus.REJECTED)
    elif defect == "numeric_bounds":
        current = replace(current, fact=replace(current.fact, value=Decimal("1e1000")))
    rows = (prior, current)
    if defect == "ambiguous_latest":
        rows = (prior, current, current)
    elif defect == "missing_comparative":
        rows = (current,)
    (item,) = financial_comparisons(replace(snapshot, inspections=rows))
    assert item.status in {
        FinancialComparisonStatus.INCOMPATIBLE, FinancialComparisonStatus.UNAVAILABLE,
    }
    assert item.change_percent is None and item.amount_change is None


@pytest.mark.parametrize("unit,multiplier", [
    ("CNY", "1"), ("CNY_thousand", "1000"), ("CNY_million", "1000000"),
])
@pytest.mark.parametrize("value", ["0", "-118437769.22", "12345678901234567890.123456"])
def test_explicit_monetary_units_preserve_exact_value_and_source_binding(
    foundation, unit, multiplier, value,
):
    from decimal import localcontext

    from tong_quant.version import REVIEWED_FILING_FACTS_VERSION, REVIEWED_MONETARY_FACTS_VERSION

    store, artifacts, review, _ = foundation
    review = replace(review, source_unit=unit, rows=(
        replace(review.rows[0], source_value=Decimal(value)),))
    with localcontext() as context:
        context.prec = 150
        expected = Decimal(value) * Decimal(multiplier)
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    snapshot = _read_inputs(store, artifacts, metrics=("revenue",))
    assert snapshot.source_binding_complete
    assert snapshot.inspections[0].fact.value == expected
    assert snapshot.inspections[0].source_unit == unit
    assert review.model_version == (REVIEWED_FILING_FACTS_VERSION if unit == "CNY_million"
                                    else REVIEWED_MONETARY_FACTS_VERSION)
    assert not snapshot.document()["investment_scoring_authorized"]


def _cash_flow_review(review, *, value="647301141.75", unit="CNY"):
    return replace(review, sector_profile="nonfinancial", source_unit=unit, rows=(
        ReviewedFilingRow("operating_cash_flow", "cash_flow", Decimal(value),
                          date(2026, 1, 1), (1,), "Synthetic group operating cash flow"),))


@pytest.mark.parametrize("value", ["0", "-25.50", "647301141.75"])
def test_cash_flow_is_separate_ytd_fact_and_future_hidden(foundation, value):
    store, artifacts, review, _ = foundation
    review = _cash_flow_review(review, value=value)
    first = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    second = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    assert first.accepted == second.accepted == 1
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("operating_cash_flow",))
    (entry,) = snapshot.inspections
    assert snapshot.source_binding_complete and entry.statement == "cash_flow"
    assert entry.fact.value == Decimal(value) and entry.fact.period_start == date(2026, 1, 1)
    assert entry.fact.trust_level is DataTrustLevel.LOW
    assert entry.fact.unit == "absolute" and entry.fact.currency == "CNY"
    assert not _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("operating_cash_flow",),
                            as_of=NOW - timedelta(microseconds=1)).inspections


@pytest.mark.parametrize("defect", [
    "bank", "unknown_sector", "standalone_quarter", "no_start", "nonstandard_end",
    "generic_cash_flow_alias", "free_cash_flow_alias", "unknown_unit", "ten_thousand_unit",
])
def test_cash_flow_requires_explicit_supported_scope_and_period(foundation, defect):
    _, _, review, _ = foundation
    review = _cash_flow_review(review)
    with pytest.raises(ValueError):
        if defect in {"bank", "unknown_sector"}:
            replace(review, sector_profile="bank" if defect == "bank" else "unknown")
        elif defect in {"standalone_quarter", "no_start"}:
            replace(review, rows=(replace(review.rows[0], period_start=(
                date(2026, 2, 1) if defect == "standalone_quarter" else None)),))
        elif defect == "nonstandard_end":
            replace(review, period_end=date(2026, 2, 28))
        elif defect in {"generic_cash_flow_alias", "free_cash_flow_alias"}:
            replace(review.rows[0], metric=("cash_flow" if defect == "generic_cash_flow_alias"
                                            else "free_cash_flow"))
        else:
            replace(review, source_unit="unknown" if defect == "unknown_unit" else "CNY_10000")


@pytest.mark.parametrize("baseline,status,percent", [
    ("500", FinancialComparisonStatus.DESCRIPTIVE, "30.0000"),
    ("0", FinancialComparisonStatus.NONPOSITIVE_BASE, None),
    ("-500", FinancialComparisonStatus.NONPOSITIVE_BASE, None),
])
def test_same_filing_cash_flow_comparison_uses_converted_amounts_not_source_unit_labels(
    foundation, baseline, status, percent,
):
    store, artifacts, review, _ = foundation
    current = _cash_flow_review(review, value="650000")
    prior = replace(current, period_end=date(2025, 3, 31), source_unit="CNY_thousand",
                    source_column="group_prior_year_period", filing_period_end=date(2026, 3, 31),
                    comparability="as_presented_same_filing", issuer_revision_status="unverified",
                    rows=(replace(current.rows[0], period_start=date(2025, 1, 1),
                                  source_value=Decimal(baseline)),))
    ingest_filing_extraction(store, artifacts, current, as_of=NOW)
    ingest_filing_extraction(store, artifacts, prior, as_of=NOW)
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("operating_cash_flow",))
    (comparison,) = financial_comparisons(snapshot)
    assert comparison.status is status
    assert comparison.current_value == Decimal("650000")
    assert comparison.prior_value == Decimal(baseline) * 1000
    assert comparison.change_percent == (Decimal(percent) if percent else None)
    assert not comparison.document()["investment_scoring_authorized"]


def test_extended_units_keep_legacy_review_packets_unmodified(foundation):
    from tong_quant.version import REVIEWED_COMPARATIVE_FACTS_VERSION, REVIEWED_FILING_FACTS_VERSION

    _, _, review, _ = foundation
    assert review.model_version == REVIEWED_FILING_FACTS_VERSION
    assert "measurement_basis" not in review.document()
    assert "filing_period_end" not in review.document()
    flow, _ = _comparative_reviews(review)
    assert flow.model_version == REVIEWED_COMPARATIVE_FACTS_VERSION
    assert "measurement_basis" not in flow.document()


@pytest.mark.parametrize("defect", ["statement", "scope", "unit", "period"])
def test_cash_flow_receipt_cannot_be_relabelled_as_income_or_non_ytd(foundation, defect):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _cash_flow_review(review), as_of=NOW)
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("operating_cash_flow",))
    (entry,) = snapshot.inspections
    with pytest.raises(ValueError):
        if defect == "statement":
            replace(entry, statement="income")
        elif defect == "scope":
            replace(entry, sector_profile="bank")
        elif defect == "unit":
            replace(entry, source_unit="unknown")
        else:
            replace(entry, fact=replace(entry.fact, period_start=date(2026, 2, 1)))


def test_combined_input_cli_uses_pinned_cutoff_is_read_only_and_keeps_gaps(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _cash_flow_review(review), as_of=NOW)
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics",
            "operating_cash_flow", "roe", "--sector-profile", "nonfinancial", "--as-of",
            NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    document = json.loads(first.stdout)
    assert document == json.loads(second.stdout)
    assert document["observed_bar_rows"] == 0
    assert document["financial_inputs"]["missing_metrics"] == ["roe"]
    assert document["financial_inputs"]["as_of"] == document["as_of"]
    assert not document["research_report_created"] and not document["execution_authorized"]
    assert document["financial_scoring_policy"] == "NOT_ADMITTED"
    assert document["screening_status"] == "NOT_ASSESSED"
    assert store.path.read_bytes() == before


def _nonfinancial_roe_review(review, value="-1.70"):
    return replace(
        review, sector_profile="nonfinancial", source_unit="percent", currency="not_applicable",
        measurement_basis="ytd_unannualized_ratio",
        rows=(ReviewedFilingRow(
            "roe_weighted_ytd_unannualized", "nonfinancial_profitability", Decimal(value),
            date(review.period_end.year, 1, 1), (7,),
            "Synthetic group current calendar-YTD weighted ROE; not annualized or ROIC",
        ),),
    )


@pytest.mark.parametrize("value", ["-1.70", "0", "7.22", "150"])
def test_nonfinancial_roe_is_signed_reported_percent_with_no_money_or_annualization(
    foundation, value,
):
    store, artifacts, original, _ = foundation
    review = _nonfinancial_roe_review(original, value)
    assert review.model_version == "reviewed-nonfinancial-ytd-ratios-v5"
    first = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    second = ingest_filing_extraction(store, artifacts, review, as_of=NOW + timedelta(seconds=1))
    assert first.accepted == second.accepted == 1
    assert store.table_count("fundamental_facts") == 1
    metric = "roe_weighted_ytd_unannualized"
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial", metrics=(metric,))
    (entry,) = snapshot.inspections
    assert snapshot.source_binding_complete
    assert entry.fact.value == Decimal(value) and entry.fact.unit == "percent"
    assert entry.fact.currency is None and entry.source_unit == "percent"
    assert entry.fact.period_start == date(2026, 1, 1)
    assert entry.measurement_basis == "ytd_unannualized_ratio"
    assert entry.fact.available_at == NOW and entry.fact.trust_level is DataTrustLevel.LOW
    assert entry.fact.availability_precision.value == "retrieval_time"
    assert not snapshot.document()["investment_scoring_authorized"]
    assert not snapshot.document()["validation_authorized"]
    assert not snapshot.document()["historical_replay_eligible"]
    assert not _read_inputs(store, artifacts, as_of=NOW - timedelta(microseconds=1),
                            sector="nonfinancial", metrics=(metric,)).inspections
    aliases = _read_inputs(store, artifacts, sector="nonfinancial", metrics=(metric, "roe", "roic"))
    assert aliases.missing_metrics == ("roe", "roic")
    assert all(item.status is FinancialComparisonStatus.UNAVAILABLE
               and item.amount_change is None and item.change_percent is None
               for item in financial_comparisons(snapshot))
    wrong_sector = _read_inputs(store, artifacts, sector="bank", metrics=(metric,))
    assert all(item.status is FinancialBindingStatus.REJECTED for item in wrong_sector.inspections)


@pytest.mark.parametrize("change", [
    {"source_unit": "fraction"}, {"source_unit": "CNY"}, {"currency": "CNY"},
    {"sector_profile": "bank"}, {"sector_profile": "unknown"}, {"reporting_scope": "parent"},
    {"measurement_basis": None}, {"measurement_basis": "annualized"},
    {"measurement_basis": "period_end_ratio"}, {"source_column": "group_prior_year_period"},
    {"period_end": date(2026, 5, 31)}, {"filing_period_end": date(2026, 6, 30)},
    {"comparability": "as_presented_same_filing"}, {"issuer_revision_status": "unverified"},
])
def test_nonfinancial_roe_review_rejects_inferred_scope_period_and_ratio_basis(foundation, change):
    _, _, review, _ = foundation
    with pytest.raises(ValueError):
        replace(_nonfinancial_roe_review(review), **change)


@pytest.mark.parametrize("defect", [
    "missing_start", "standalone_quarter", "generic_roe", "roic", "bank_statement", "money_mix",
    "bank_ratio_mix", "nonfinite",
])
def test_nonfinancial_roe_rows_cannot_hide_aliases_periods_or_mixed_units(foundation, defect):
    _, _, original, _ = foundation
    review = _nonfinancial_roe_review(original)
    row = review.rows[0]
    with pytest.raises(ValueError):
        if defect == "missing_start":
            replace(row, period_start=None)
        elif defect == "standalone_quarter":
            replace(review, rows=(replace(row, period_start=date(2026, 2, 1)),))
        elif defect in {"generic_roe", "roic"}:
            replace(row, metric="roe" if defect == "generic_roe" else "roic")
        elif defect == "bank_statement":
            replace(row, statement="bank_asset_quality")
        elif defect == "money_mix":
            replace(review, rows=(row, original.rows[0]))
        elif defect == "bank_ratio_mix":
            replace(review, rows=(row, _ratio_review(original).rows[0]))
        else:
            replace(row, source_value=Decimal("NaN"))


@pytest.mark.parametrize("change", [
    {"unit": "absolute"}, {"currency": "CNY"}, {"value": "1700000"},
    {"period_start": "2026-02-01"},
])
def test_nonfinancial_roe_tampering_stays_visible_as_rejected(foundation, change):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _nonfinancial_roe_review(review), as_of=NOW)
    with store._connect() as connection:
        column, value = next(iter(change.items()))
        connection.execute(f"UPDATE fundamental_facts SET {column} = ?", (value,))
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("roe_weighted_ytd_unannualized",))
    assert len(snapshot.inspections) == 1 and not snapshot.missing_metrics
    assert snapshot.inspections[0].status is FinancialBindingStatus.REJECTED
    assert not snapshot.source_binding_complete and store.table_count("fundamental_facts") == 1


@pytest.mark.parametrize("change", [
    {"source_unit": "fraction"}, {"measurement_basis": "annualized"},
    {"sector_profile": "bank"}, {"statement": "income"},
    {"filing_period_end": date(2025, 12, 31)},
])
def test_nonfinancial_roe_receipt_cannot_be_relabelled(foundation, change):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _nonfinancial_roe_review(review), as_of=NOW)
    (entry,) = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=("roe_weighted_ytd_unannualized",)).inspections
    with pytest.raises(ValueError):
        replace(entry, **change)


@pytest.mark.parametrize("index,expected", [
    (0, "35acd0282da9eb451608d74dccb4ef12d75ae1a28512afe434a22b1796c850a2"),
    (1, "ccb808a3f4c03a7aa417cd3996304e584e28a404f8d546ad637a3581327e1de2"),
    (2, "b044a8484acc33f0691e847f959f9ce214fb8a96889c231b8198ebc64b4462aa"),
    (3, "d8392d5689e4bfeaa02f4a686394ba4a808238cae8b8f2daa178cef30f79765f"),
    (4, "8a6b2454f9ad994292ada984cbba406a44a0e0fab35d34831ca0c2407a887f6e"),
])
def test_nonfinancial_ratio_extension_preserves_all_previous_packet_hashes(
    foundation, index, expected,
):
    store, artifacts, review, _ = foundation
    plans = (review, *_comparative_reviews(review), _ratio_review(review),
             _cash_flow_review(review))
    packet = prepare_filing_extraction(store, artifacts, plans[index], as_of=NOW).batch
    assert packet.raw_data_hash == expected


def test_nonfinancial_roe_combined_cli_is_read_only_deterministic_and_not_a_report(foundation):
    store, artifacts, review, _ = foundation
    ingest_filing_extraction(store, artifacts, _nonfinancial_roe_review(review), as_of=NOW)
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics",
            "roe_weighted_ytd_unannualized", "roe", "roic", "--sector-profile", "nonfinancial",
            "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    document = json.loads(first.stdout)
    assert document == json.loads(second.stdout)
    assert document["financial_inputs"]["missing_metrics"] == ["roe", "roic"]
    assert document["financial_inputs"]["inspections"][0]["fact"]["value"] == "-1.70"
    assert not document["research_report_created"] and not document["execution_authorized"]
    assert document["screening_status"] == "NOT_ASSESSED"
    assert document["financial_scoring_policy"] == "NOT_ADMITTED"
    assert store.path.read_bytes() == before


def test_committed_nonfinancial_roe_plan_has_explicit_current_period_signed_percent():
    plan = tomllib.loads(Path(
        "config/filing-extractions/002624-2026h1-weighted-roe.toml").read_text())
    review = parse_filing_review(plan)
    assert review.subject == "002624" and review.sector_profile == "nonfinancial"
    assert review.model_version == "reviewed-nonfinancial-ytd-ratios-v5"
    assert review.measurement_basis == "ytd_unannualized_ratio"
    assert review.source_unit == "percent" and review.currency == "not_applicable"
    (row,) = review.rows
    assert row.metric == "roe_weighted_ytd_unannualized" and row.source_value == Decimal("-1.70")
    assert row.period_start == date(2026, 1, 1) and review.period_end == date(2026, 6, 30)
    assert row.source_pages == (7,)


def _cash_balance_review(review):
    balances = (("total_liabilities", "50"), ("current_liabilities", "40"),
                ("monetary_funds", "20"))
    flows = (("operating_cash_inflow", "100"), ("operating_cash_outflow", "40"))
    return replace(
        review, sector_profile="nonfinancial", source_unit="CNY",
        rows=tuple(ReviewedFilingRow(metric, "balance", Decimal(value), None, (41, 43),
                                    f"Synthetic current group {metric}")
                   for metric, value in balances) + tuple(
            ReviewedFilingRow(metric, "cash_flow", Decimal(value),
                              date(review.period_end.year, 1, 1), (48, 49),
                              f"Synthetic current group YTD {metric}") for metric, value in flows),
    )


@pytest.mark.parametrize("unit,scale", [("CNY", "1"), ("CNY_thousand", "1000"),
                                      ("CNY_million", "1000000")])
def test_nonfinancial_cash_balance_inputs_normalize_units_and_retain_exact_binding(
    foundation, unit, scale,
):
    store, artifacts, original, _ = foundation
    review = replace(_cash_balance_review(original), source_unit=unit)
    assert review.model_version == "reviewed-nonfinancial-cash-balance-v6"
    first = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    ingest_filing_extraction(store, artifacts, review, as_of=NOW + timedelta(seconds=1))
    assert store.table_count("fundamental_facts") == 5
    metrics = tuple(row.metric for row in review.rows)
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial", metrics=metrics)
    assert snapshot.source_binding_complete and len(snapshot.inspections) == 5
    source_values = {row.metric: row.source_value for row in review.rows}
    for entry in snapshot.inspections:
        assert entry.fact.value == source_values[entry.fact.metric] * Decimal(scale)
        assert entry.fact.unit == "absolute" and entry.fact.currency == "CNY"
        assert entry.fact.available_at == NOW and entry.fact.batch_id == first.batch_id
        assert entry.fact.trust_level is DataTrustLevel.LOW
    assert not _read_inputs(store, artifacts, sector="nonfinancial", metrics=metrics,
                            as_of=NOW - timedelta(microseconds=1)).inspections
    wrong = _read_inputs(store, artifacts, sector="bank", metrics=metrics)
    assert all(entry.status is FinancialBindingStatus.REJECTED for entry in wrong.inspections)


@pytest.mark.parametrize("metric,statement,start", [
    ("total_liabilities", "balance", None), ("current_liabilities", "balance", None),
    ("monetary_funds", "balance", None),
    ("operating_cash_inflow", "cash_flow", date(2026, 1, 1)),
    ("operating_cash_outflow", "cash_flow", date(2026, 1, 1)),
])
def test_new_cash_balance_amounts_are_not_signed_net_flows(foundation, metric, statement, start):
    with pytest.raises(ValueError):
        ReviewedFilingRow(metric, statement, Decimal("-1"), start, (41,), "Synthetic")


@pytest.mark.parametrize("change", [
    {"sector_profile": "bank"}, {"sector_profile": "unknown"}, {"source_unit": "unknown"},
    {"reporting_scope": "parent"}, {"period_end": date(2026, 4, 30)},
    {"filing_period_end": date(2026, 6, 30)}, {"source_column": "group_prior_year_end"},
])
def test_new_cash_balance_review_requires_explicit_nonfinancial_current_scope(foundation, change):
    _, _, original, _ = foundation
    with pytest.raises(ValueError):
        replace(_cash_balance_review(original), **change)


@pytest.mark.parametrize("metric,statement", [
    ("debt", "balance"), ("free_cash", "balance"), ("short_term_borrowings", "balance"),
    ("monetary_funds", "income"), ("operating_cash_inflow", "income"),
])
def test_no_generic_debt_cash_alias_or_inferred_blank_borrowing_amount(metric, statement):
    with pytest.raises(ValueError):
        ReviewedFilingRow(metric, statement, Decimal("0"), None, (41,), "Synthetic")


@pytest.mark.parametrize("change", [
    {"value": "51"}, {"unit": "percent"}, {"currency": "USD"},
    {"period_start": "2026-01-01"},
])
def test_new_balance_fact_tampering_is_rejected_but_preserved(foundation, change):
    store, artifacts, original, _ = foundation
    ingest_filing_extraction(store, artifacts, _cash_balance_review(original), as_of=NOW)
    with store._connect() as connection:
        column, value = next(iter(change.items()))
        connection.execute(f"UPDATE fundamental_facts SET {column} = ? WHERE metric = ?",
                           (value, "total_liabilities"))
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial", metrics=("total_liabilities",))
    assert snapshot.inspections[0].status is FinancialBindingStatus.REJECTED
    assert store.table_count("fundamental_facts") == 5 and not snapshot.missing_metrics


def test_cash_balance_combined_cli_exposes_reconciliation_without_admitting_scores(foundation):
    store, artifacts, original, _ = foundation
    ingest_filing_extraction(store, artifacts, replace(original, sector_profile="nonfinancial"),
                             as_of=NOW)
    ingest_filing_extraction(store, artifacts, _cash_flow_review(original, value="60"), as_of=NOW)
    ingest_filing_extraction(store, artifacts, _cash_balance_review(original), as_of=NOW)
    metrics = ("revenue", "total_assets", "total_liabilities", "current_liabilities",
               "monetary_funds", "operating_cash_flow", "operating_cash_inflow",
               "operating_cash_outflow", "roic")
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics", *metrics,
            "--sector-profile", "nonfinancial", "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    document = json.loads(first.stdout)
    assert document == json.loads(second.stdout) and store.path.read_bytes() == before
    results = {item["name"]: item for item in document["nonfinancial_diagnostics"]}
    assert results["operating_cash_reconciliation_residual"]["value"] == "0"
    assert all(item["status"] == "descriptive_only" for item in results.values())
    assert not any(item["investment_scoring_authorized"] for item in results.values())
    assert document["financial_inputs"]["missing_metrics"] == ["roic"]
    assert document["financial_scoring_policy"] == "NOT_ADMITTED"
    assert not document["research_report_created"] and not document["execution_authorized"]


def test_committed_cash_balance_plan_is_explicit_group_current_period_and_cny():
    review = parse_filing_review(tomllib.loads(Path(
        "config/filing-extractions/002624-2026h1-cash-balance.toml").read_text()))
    assert review.model_version == "reviewed-nonfinancial-cash-balance-v6"
    assert review.subject == "002624" and review.period_end == date(2026, 6, 30)
    assert review.source_unit == "CNY" and review.sector_profile == "nonfinancial"
    assert len(review.rows) == 5
    values = {row.metric: row.source_value for row in review.rows}
    assert values["total_liabilities"] == Decimal("4250178510.38")
    assert values["monetary_funds"] == Decimal("3523584061.89")
    assert values["operating_cash_inflow"] - values["operating_cash_outflow"] == (
        Decimal("647301141.75"))


@pytest.mark.parametrize("value", ["-80.25", "0", "80.25"])
@pytest.mark.parametrize("unit,scale", [("CNY", "1"), ("CNY_thousand", "1000"),
                                      ("CNY_million", "1000000")])
def test_parent_equity_signed_source_binding_and_first_provenance_are_preserved(
    foundation, value, unit, scale,
):
    store, artifacts, original, _ = foundation
    metric = "equity_attributable_to_parent"
    review = replace(original, sector_profile="nonfinancial", source_unit=unit, rows=(
        ReviewedFilingRow(metric, "balance", Decimal(value), None, (41, 43),
                          "Synthetic group parent owners equity"),))
    assert review.model_version == "reviewed-nonfinancial-parent-equity-v7"
    first = ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    ingest_filing_extraction(store, artifacts, review, as_of=NOW + timedelta(seconds=1))
    assert store.table_count("fundamental_facts") == 1
    (entry,) = _read_inputs(store, artifacts, sector="nonfinancial",
                            metrics=(metric,)).inspections
    assert entry.status is FinancialBindingStatus.SOURCE_BOUND
    assert entry.fact.value == Decimal(value) * Decimal(scale)
    assert entry.fact.batch_id == first.batch_id and entry.fact.available_at == NOW
    assert entry.fact.trust_level is DataTrustLevel.LOW
    assert not _read_inputs(store, artifacts, sector="nonfinancial", metrics=(metric,),
                            as_of=NOW - timedelta(microseconds=1)).inspections
    assert _read_inputs(store, artifacts, sector="bank", metrics=(metric,)).inspections[
        0].status is FinancialBindingStatus.REJECTED


@pytest.mark.parametrize("change", [
    {"sector_profile": "bank"}, {"sector_profile": "unknown"},
    {"source_column": "group_prior_year_end"}, {"period_end": date(2026, 4, 30)},
    {"reporting_scope": "parent"}, {"filing_period_end": date(2026, 6, 30)},
])
def test_parent_equity_requires_current_nonfinancial_group_scope(foundation, change):
    _, _, original, _ = foundation
    review = replace(original, sector_profile="nonfinancial", rows=(ReviewedFilingRow(
        "equity_attributable_to_parent", "balance", Decimal("-1"), None, (43,), "Fixture"),))
    with pytest.raises(ValueError):
        replace(review, **change)


def test_parent_equity_combined_cli_is_readonly_and_does_not_compute_valuation(foundation):
    store, artifacts, original, _ = foundation
    metric = "equity_attributable_to_parent"
    review = replace(original, sector_profile="nonfinancial", source_unit="CNY", rows=(
        ReviewedFilingRow(metric, "balance", Decimal("-80"), None, (43,), "Synthetic"),))
    ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    ingest_filing_extraction(store, artifacts, replace(original, sector_profile="nonfinancial"),
                             as_of=NOW)
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics", metric,
            "profit_attributable_to_parent", "revenue", "--sector-profile", "nonfinancial",
            "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    body = json.loads(first.stdout)
    results = {item["name"]: item for item in body["valuation_basis_diagnostics"]}
    assert results["parent_book_basis"]["status"] == "nonpositive_denominator"
    assert results["annual_earnings_basis"]["status"] == "partial_year_not_annual_or_ttm"
    assert all(item["valuation_multiple"] is None for item in results.values())
    assert not body["research_report_created"] and not body["investment_scoring_authorized"]


def test_parent_equity_plan_does_not_substitute_assets_or_minority_inclusive_equity():
    review = parse_filing_review(tomllib.loads(Path(
        "config/filing-extractions/002624-2026h1-parent-equity.toml").read_text()))
    assert review.model_version == "reviewed-nonfinancial-parent-equity-v7"
    (row,) = review.rows
    assert row.metric == "equity_attributable_to_parent"
    assert row.source_value == Decimal("6511874265.88") and row.period_start is None
    assert row.source_pages == (41, 43) and review.source_unit == "CNY"


def test_trailing_cli_reconstructs_receipts_review_and_arithmetic_without_writes(
    foundation, tmp_path,
):
    store, artifacts, original, _ = foundation
    current = replace(original, sector_profile="nonfinancial")
    prior, _ = _comparative_reviews(current)
    annual = replace(current, period_end=date(2025, 12, 31), audit_status="audited", rows=tuple(
        replace(row, period_start=date(2025, 1, 1), source_value=Decimal("60000"))
        for row in current.rows if row.statement == "income"))
    for review in (current, prior, annual):
        ingest_filing_extraction(store, artifacts, review, as_of=NOW)
    snapshot = _read_inputs(store, artifacts, sector="nonfinancial", metrics=("revenue",))
    by_period = {entry.fact.period_end: entry for entry in snapshot.inspections}
    review = TrailingEditionReview(
        "revenue", *(trailing_input_hash(by_period[d]) for d in (
            current.period_end, annual.period_end, prior.period_end)),
        NOW, "Synthetic manual bridge", ("No independent qualification",),
    )
    plan = tmp_path / "review.toml"
    values = {"metric": review.metric, "current_input_hash": review.current_input_hash,
              "annual_input_hash": review.annual_input_hash,
              "prior_input_hash": review.prior_input_hash,
              "reviewed_at": NOW.isoformat(), "reviewer": review.reviewer,
              "limitations": list(review.limitations)}
    plan.write_text("[[reviews]]\n" + "\n".join(
        f"{key} = {json.dumps(value)}" for key, value in values.items()), encoding="utf-8")
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "600000", "--metrics", "revenue",
            "--sector-profile", "nonfinancial", "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    unreviewed = subprocess.run(args, capture_output=True, text=True, check=False)
    assert unreviewed.returncode == 2, unreviewed.stderr
    body = json.loads(unreviewed.stdout)
    assert body["trailing_financial_diagnostics"][1]["status"] == "edition_review_required"
    args += ["--trailing-review-plan", str(plan)]
    first = subprocess.run(args, capture_output=True, text=True, check=False)
    second = subprocess.run(args, capture_output=True, text=True, check=False)
    assert first.returncode == second.returncode == 2, first.stderr
    assert first.stdout == second.stdout and store.path.read_bytes() == before
    body = json.loads(first.stdout)
    result = body["trailing_financial_diagnostics"][1]
    expected = Decimal("60000") + Decimal("46573") - Decimal("45922")
    assert Decimal(result["value"]) == expected * Decimal("1000000")
    assert result["review_hash"] == review.review_hash
    assert result["status"] == "derived_as_reported_unqualified"
    assert not body["research_report_created"] and not body["investment_scoring_authorized"]
    assert not result["validation_authorized"] and not body["execution_authorized"]


def test_annual_plan_preserves_explicit_full_year_group_income_and_cny_units():
    review = parse_filing_review(tomllib.loads(Path(
        "config/filing-extractions/002624-2025fy.toml").read_text()))
    assert review.model_version == "reviewed-monetary-filing-facts-v4"
    assert review.subject == "002624" and review.period_end == date(2025, 12, 31)
    assert review.sector_profile == "nonfinancial" and review.source_unit == "CNY"
    assert review.audit_status == "audited" and len(review.rows) == 2
    assert all(row.period_start == date(2025, 1, 1) for row in review.rows)
    assert {row.metric: row.source_value for row in review.rows} == {
        "revenue": Decimal("6659558521.64"),
        "profit_attributable_to_parent": Decimal("730859018.92"),
    }
