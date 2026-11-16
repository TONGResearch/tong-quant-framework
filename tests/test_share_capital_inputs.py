"""Share-count review preserves units and dates without creating valuation authority."""

import json
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tong_quant.data.artifacts import FileSystemArtifactStore
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
from tong_quant.data.share_action_reviews import (
    ShareActionDocumentReview,
    ShareActionKind,
    ShareActionObservation,
    ShareActionScope,
    ShareActionStage,
    inspect_share_action_review,
    parse_share_action_review,
)
from tong_quant.data.share_capital_inputs import (
    ShareCapitalReview,
    inspect_share_capital_review,
    parse_share_capital_review,
)
from tong_quant.data.share_continuity_inputs import inspect_share_continuity
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market

NOW = datetime(2026, 10, 26, 13, 50, tzinfo=UTC)
CAPTURED = NOW - timedelta(minutes=5)
PUBLISHED = datetime(2026, 8, 20, tzinfo=UTC)
PDF = b"%PDF-1.4\nsynthetic share table; not an authenticated filing"


class _Client:
    def search(self, *args, **kwargs):
        return CnInfoQueryResult(({
            "secCode": "002624", "secName": "Synthetic", "orgId": "fixture",
            "announcementId": "1234567890", "announcementTitle": "Half-year report",
            "announcementTime": int(PUBLISHED.timestamp() * 1000),
            "adjunctUrl": "finalpage/2026-08-20/1234567890.PDF",
        },), "f" * 64, 1, 1, 1, False)

    def download_artifact(self, url):
        return CnInfoArtifactDownload(
            ProviderArtifactStatus.CAPTURED, url, url, "application/pdf", PDF, "")


@pytest.fixture
def foundation(tmp_path):
    store = SQLiteStore(tmp_path / "shares.sqlite3")
    store.initialize()
    artifacts = FileSystemArtifactStore(tmp_path / "artifacts")
    adapter = CnInfoDirectEvidenceAdapter(client=_Client(), clock=lambda: CAPTURED)
    request = ProviderDatasetRequest(CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "002624", NOW, {
        "start_date": "2026-08-20", "end_date": "2026-08-20",
        "capture_artifacts": "true", "max_artifacts": "1"})
    source = adapter.fetch(request).artifacts[0]
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: NOW).ingest(
        adapter, request)
    review = ShareCapitalReview(
        "002624", date(2026, 6, 30), NOW, "Synthetic manual review only",
        source.artifact_id, source.content_hash, (36,), "Synthetic after-change share-count column",
        100, 10, 90)
    return store, artifacts, review


def _read(foundation, review=None, as_of=NOW):
    store, artifacts, original = foundation
    return inspect_share_capital_review(store, artifacts, review or original, as_of=as_of)


def test_read_only_binding_keeps_counts_separate_from_current_shares_and_valuation(foundation):
    store, _, _ = foundation
    before = store.path.read_bytes()
    result = _read(foundation)
    assert result["source_bound"] and result["reconciliation"] == "EXACT_AGREEMENT"
    assert result["total_minus_components"] == 0
    assert result["review"]["reported_unit"] == "shares" and result["review"]["currency"] is None
    assert result["review"]["total_shares"] == 100
    assert result["availability_precision"] == "retrieval_time" and result["trust_level"] == "low"
    assert result["available_at"] == NOW and result["source_captured_at"] == CAPTURED
    assert result["current_share_count_status"] == "UNQUALIFIED_CONTINUITY"
    for name in ("valuation_authorized", "investment_scoring_authorized", "validation_authorized",
                 "historical_replay_eligible", "execution_authorized", "readiness_promoted",
                 "canonical_facts_written"):
        assert result[name] is False
    assert result["market_value"] is None
    assert store.path.read_bytes() == before
    assert store.table_count("fundamental_facts") == store.table_count("research_reports") == 0


@pytest.mark.parametrize("field,value", [
    ("reported_unit", "CNY"), ("reported_unit", "percent"), ("reported_unit", "shares_thousand"),
    ("currency", "CNY"), ("source_column", "before_change"),
    ("share_class_scope", "free_float"), ("period_basis", "current_outstanding"),
    ("total_shares", True), ("total_shares", "100"), ("total_shares", 100.5),
    ("total_shares", 0), ("total_shares", -1), ("unrestricted_shares", -1),
    ("total_shares", 10**16), ("source_pages", (True,)), ("source_pages", (1, 1)),
    ("model_version", "self-approved"),
])
def test_units_semantics_and_share_counts_are_explicit_not_inferred(foundation, field, value):
    with pytest.raises(ValueError):
        replace(foundation[2], **{field: value})


def test_incomplete_and_conflicting_counts_stay_visible_without_favorable_substitution(foundation):
    review = foundation[2]
    conflict = _read(foundation, replace(review, total_shares=99))
    assert conflict["reconciliation"] == "CONFLICT" and conflict["total_minus_components"] == -1
    incomplete = _read(foundation, replace(review, unrestricted_shares=None))
    assert incomplete["reconciliation"] == "INCOMPLETE"
    assert incomplete["total_minus_components"] is None
    with pytest.raises(ValueError):
        replace(review, total_shares=None, restricted_shares=None, unrestricted_shares=None)


@pytest.mark.parametrize("kind", ["bytes", "registry_size", "registry_path", "subject", "dataset",
                                  "batch_status", "batch_time", "batch_subject", "batch_shape"])
def test_broken_registry_bytes_and_batch_provenance_fail_closed(foundation, kind):
    store, artifacts, review = foundation
    if kind == "bytes":
        path = artifacts.root / "sha256" / review.filing_sha256[:2] / f"{review.filing_sha256}.pdf"
        path.write_bytes(b"synthetic tamper")
    else:
        with store._connect() as connection:
            if kind.startswith("batch_"):
                column, value = {
                    "batch_status": ("status", "failed"),
                    "batch_time": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
                    "batch_subject": ("parameters_json", json.dumps({"subject": "000063"})),
                    "batch_shape": ("parameters_json", "[]"),
                }[kind]
                connection.execute(f"UPDATE ingestion_batches SET {column}=?", (value,))
            else:
                column, value = {
                    "registry_size": ("byte_size", len(PDF) + 1),
                    "registry_path": ("storage_key", "wrong.pdf"),
                    "subject": ("subject", "000063"),
                    "dataset": ("dataset", "unrelated"),
                }[kind]
                connection.execute(f"UPDATE provider_artifacts SET {column}=?", (value,))
    with pytest.raises(ValueError):
        _read(foundation)


def test_unknown_source_trust_is_not_promoted_by_a_manual_review(foundation):
    with foundation[0]._connect() as connection:
        connection.execute("UPDATE provider_artifacts SET trust_level='unknown'")
    assert _read(foundation)["trust_level"] == "unknown"


@pytest.mark.parametrize("kind", ["cutoff", "capture", "batch", "naive"])
def test_review_cannot_be_used_before_it_or_its_source_and_batch_exist(foundation, kind):
    review = foundation[2]
    with pytest.raises(ValueError):
        if kind == "cutoff":
            _read(foundation, as_of=NOW - timedelta(microseconds=1))
        elif kind == "capture":
            _read(foundation, replace(review, reviewed_at=CAPTURED - timedelta(seconds=1)))
        elif kind == "batch":
            _read(foundation, replace(review, reviewed_at=CAPTURED + timedelta(seconds=1)))
        else:
            _read(foundation, as_of=NOW.replace(tzinfo=None))


def test_hashes_bind_the_review_and_actual_utc_cutoff(foundation):
    from zoneinfo import ZoneInfo

    review = foundation[2]
    first = _read(foundation)
    assert first == _read(foundation, as_of=NOW.astimezone(ZoneInfo("Asia/Shanghai")))
    assert first["inspection_hash"] != _read(foundation,
        replace(review, unrestricted_shares=89))["inspection_hash"]
    assert first["review_hash"] != _read(foundation,
        replace(review, source_pages=(37,)))["review_hash"]


def test_report_date_cannot_follow_the_claimed_filing_publication(foundation):
    with pytest.raises(ValueError, match="chronology"):
        _read(foundation, replace(foundation[2], period_end=date(2026, 9, 30)))


def test_future_fold_batch_is_not_visible_despite_equal_local_clock_labels(foundation):
    from zoneinfo import ZoneInfo

    early = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    late = early.replace(fold=1)
    with foundation[0]._connect() as connection:
        connection.execute("UPDATE ingestion_batches SET completed_at=?", (late.isoformat(),))
    with pytest.raises(ValueError, match="chronology"):
        _read(foundation, replace(foundation[2], reviewed_at=early), as_of=early)


def test_parser_and_combined_cli_use_opt_in_plan_without_database_writes(foundation, tmp_path):
    store, artifacts, review = foundation
    body = asdict(review)
    body.update(period_end=review.period_end.isoformat(),
                reviewed_at=review.reviewed_at.isoformat())
    assert parse_share_capital_review({"review": {**body, "source_pages": [36]}}) == review
    with pytest.raises(ValueError, match="unknown"):
        parse_share_capital_review({"review": {**body, "market_value": 1000}})
    plan = tmp_path / "review.toml"
    plan.write_text("[review]\n" + "\n".join(
        f"{key} = {json.dumps(value)}" for key, value in body.items() if value is not None))
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "002624", "--sector-profile",
            "nonfinancial", "--metrics", "revenue", "--as-of", NOW.isoformat()]
    before = store.path.read_bytes()
    without = subprocess.run(args, capture_output=True, text=True, check=False)
    assert without.returncode == 2, without.stderr
    assert json.loads(without.stdout)["share_capital_review"]["status"] == "NOT_REQUESTED"
    run = subprocess.run(args + ["--share-capital-review-plan", str(plan)],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 2, run.stderr
    result = json.loads(run.stdout)
    checklist = result["nonfinancial_input_assessment"]
    assert checklist["financial_scoring_policy"] == "NOT_ADMITTED"
    assert next(item for item in checklist["checks"] if item["metric"] == "revenue")[
        "status"] == "missing"
    assert result["share_capital_review"]["source_bound"]
    assert result["share_capital_review"]["review"]["total_shares"] == 100
    assert not result["research_report_created"] and not result["execution_authorized"]
    assert store.path.read_bytes() == before
    mismatched = args.copy()
    mismatched[mismatched.index("002624")] = "000063"
    wrong = subprocess.run(mismatched + ["--share-capital-review-plan", str(plan)],
                           capture_output=True, text=True, check=False)
    assert wrong.returncode == 2 and "does not match" in wrong.stderr
    with_continuity = subprocess.run(args + ["--share-capital-review-plan", str(plan),
        "--share-continuity-through", "2026-10-26"], capture_output=True, text=True, check=False)
    assert with_continuity.returncode == 2, with_continuity.stderr
    audit = json.loads(with_continuity.stdout)["share_continuity_review"]
    assert audit["status"] == "PARTIAL_INVENTORY"
    assert audit["current_shares"] is audit["market_value"] is None
    missing_base = subprocess.run(args + ["--share-continuity-through", "2026-10-26"],
                                  capture_output=True, text=True, check=False)
    assert missing_base.returncode == 2 and "requires an explicit base" in missing_base.stderr
    assert store.path.read_bytes() == before


def test_combined_cli_supports_explicit_nonfinancial_period_without_publishing_data(
    foundation,
):
    store, artifacts, _ = foundation
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
            "--artifact-root", str(artifacts.root), "--symbol", "002624", "--sector-profile",
            "nonfinancial", "--metrics", "revenue", "--as-of", NOW.isoformat(),
            "--financial-target-period", "2026-09-30"]
    before = store.path.read_bytes()
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stderr
    body = json.loads(result.stdout)
    assert body["nonfinancial_input_assessment"]["target_period_end"] == "2026-09-30"
    assert body["nonfinancial_input_assessment"]["target_period_basis"] == "explicit"
    assert not body["research_report_created"] and not body["investment_scoring_authorized"]
    args[args.index("nonfinancial")] = "bank"
    unsupported = subprocess.run(args, capture_output=True, text=True, check=False)
    assert unsupported.returncode == 2 and "China-A nonfinancial" in unsupported.stderr
    assert store.path.read_bytes() == before


def _capture_later_disclosure(foundation, *, title="Repurchase completed", identifier="1234567891",
                              at=None, completed=None):
    at = at or NOW + timedelta(minutes=1)
    completed = completed or at

    class LaterClient(_Client):
        def search(self, *args, **kwargs):
            return CnInfoQueryResult(({
                "secCode": "002624", "secName": "Synthetic", "orgId": "fixture",
                "announcementId": identifier, "announcementTitle": title,
                "announcementTime": int(datetime(2026, 9, 5, tzinfo=UTC).timestamp() * 1000),
                "adjunctUrl": f"finalpage/2026-09-05/{identifier}.PDF",
            },), "e" * 64, 1, 1, 1, False)

    store, artifacts, _ = foundation
    adapter = CnInfoDirectEvidenceAdapter(client=LaterClient(), clock=lambda: at)
    request = ProviderDatasetRequest(CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "002624", at, {
        "start_date": "2026-07-01", "end_date": "2026-10-26", "capture_artifacts": "false",
        "max_artifacts": "0"})
    return ProviderNeutralIngestionService(store, artifact_store=artifacts,
        clock=lambda: completed).ingest(adapter, request)


def _continuity(foundation, *, through=date(2026, 10, 26), as_of=None):
    store, artifacts, review = foundation
    return inspect_share_continuity(store, artifacts, review, through=through,
                                     as_of=as_of or NOW + timedelta(minutes=5))


@pytest.mark.parametrize("title,tag", [
    ("回购股份注销实施完成公告", "repurchase"),
    ("员工持股计划实施完毕暨计划终止", "employee_or_restricted_plan"),
    ("限制性股票解除限售公告", "employee_or_restricted_plan"),
    ("可转债转股及股份变动", "issuance_conversion"),
    ("权益分派实施公告", "bonus_split_distribution"),
    ("第六届董事会会议决议", "governance_or_periodic_report"),
    ("关于股本的公告", "share_capital"),
])
def test_title_tags_prioritize_review_not_implemented_actions(foundation, title, tag):
    _capture_later_disclosure(foundation, title=title)
    result = _continuity(foundation)
    entry = next(item for item in result["document_review_items"]
                 if item["record"]["payload"]["title"] == title)
    assert tag in entry["title_review_tags"]
    assert entry["binding_status"] == "METADATA_BATCH_BOUND"
    assert entry["document_review_state"] == "NOT_REVIEWED"
    assert entry["effective_share_change"] == "NOT_ESTABLISHED"
    assert result["current_shares"] is result["market_value"] is None
    assert result["current_share_count_status"] == "UNQUALIFIED_CONTINUITY"
    assert result["historical_coverage"] == "NOT_VERIFIED"
    for name in ("valuation_authorized", "investment_scoring_authorized", "validation_authorized",
                 "historical_replay_eligible", "execution_authorized", "readiness_promoted"):
        assert result[name] is False


def test_no_keyword_or_no_visible_record_cannot_clear_share_continuity(foundation):
    _capture_later_disclosure(foundation, title="Unclassified company update")
    result = _continuity(foundation)
    entry = next(item for item in result["document_review_items"]
                 if item["record"]["payload"]["title"] == "Unclassified company update")
    assert not entry["title_review_tags"] and entry["document_review_state"] == "NOT_REVIEWED"
    missing = _continuity(foundation, through=date(2026, 7, 31))
    assert missing["status"] == "NO_VISIBLE_DISCLOSURE_EVIDENCE"
    assert missing["current_share_count_status"] == "UNQUALIFIED_CONTINUITY"


def test_later_retrieval_of_old_publication_cannot_leak_into_an_earlier_audit(foundation):
    before = _continuity(foundation, as_of=NOW)
    _capture_later_disclosure(foundation)
    assert _continuity(foundation, as_of=NOW) == before
    assert _continuity(foundation)["observed_metadata_versions"] == (
        before["observed_metadata_versions"] + 1)


def test_future_completed_batch_does_not_leak_into_the_earlier_inventory(foundation):
    cutoff = NOW + timedelta(minutes=2)
    before = _continuity(foundation, as_of=cutoff)
    _capture_later_disclosure(foundation, completed=NOW + timedelta(minutes=3))
    assert _continuity(foundation, as_of=cutoff) == before


def test_folded_later_capture_is_not_visible_at_the_equal_earlier_local_clock(foundation):
    from zoneinfo import ZoneInfo

    early = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    late = early.replace(fold=1)
    before = _continuity(foundation, as_of=early)
    _capture_later_disclosure(foundation, at=late)
    assert _continuity(foundation, as_of=early) == before
    assert _continuity(foundation, as_of=late)["observed_metadata_versions"] == (
        before["observed_metadata_versions"] + 1)


@pytest.mark.parametrize("defect", ["payload", "batch_hash", "batch_subject", "batch_status"])
def test_rejected_disclosure_binding_stays_visible_without_providing_action_evidence(
    foundation, defect,
):
    store = foundation[0]
    ingestion = _capture_later_disclosure(foundation)
    with store._connect() as connection:
        if defect == "payload":
            row = connection.execute("SELECT payload_json FROM provider_evidence_records "
                                     "WHERE batch_id=?", (ingestion.batch_id,)).fetchone()
            payload = json.loads(row["payload_json"])
            payload["title"] = "Cancellation completed; synthetic tamper"
            connection.execute("UPDATE provider_evidence_records SET payload_json=? "
                               "WHERE batch_id=?",
                               (json.dumps(payload), ingestion.batch_id))
        else:
            column, value = {
                "batch_hash": ("raw_response_hash", "d" * 64),
                "batch_subject": ("parameters_json", json.dumps({"subject": "000063"})),
                "batch_status": ("status", "failed"),
            }[defect]
            connection.execute(f"UPDATE ingestion_batches SET {column}=? WHERE batch_id=?",
                               (value, ingestion.batch_id))
    result = _continuity(foundation)
    rejected = [item for item in result["document_review_items"]
                if item["binding_status"] == "REJECTED"]
    assert len(rejected) == 1 and rejected[0]["binding_reasons"]
    assert rejected[0]["title_review_tags"] == ()
    assert result["current_shares"] is None and result["readiness_promoted"] is False


def test_versions_of_one_announcement_are_not_summed_as_independent_actions(foundation):
    _capture_later_disclosure(foundation, title="Repurchase report")
    _capture_later_disclosure(foundation, title="Repurchase report revised",
                              at=NOW + timedelta(minutes=2))
    result = _continuity(foundation)
    assert result["observed_metadata_versions"] == 3
    assert result["unique_bound_announcements"] == 2
    assert result["title_triaged_announcements"] == 2
    assert result["effective_action_timeline"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("through", [date(2026, 6, 29), date(2026, 10, 27), NOW])
def test_continuity_window_must_be_explicit_and_visible(foundation, through):
    with pytest.raises(ValueError, match="visible date"):
        _continuity(foundation, through=through)


def test_continuity_is_deterministic_read_only_and_changes_with_its_consumed_metadata(foundation):
    from zoneinfo import ZoneInfo

    cutoff = NOW + timedelta(minutes=5)
    before = _continuity(foundation, as_of=cutoff)
    _capture_later_disclosure(foundation)
    database = foundation[0].path.read_bytes()
    result = _continuity(foundation, as_of=cutoff)
    assert result == _continuity(foundation, as_of=cutoff.astimezone(ZoneInfo("Asia/Shanghai")))
    assert result["inspection_hash"] != before["inspection_hash"]
    assert foundation[0].path.read_bytes() == database


def _action_review(foundation):
    base = foundation[2]
    return ShareActionDocumentReview(
        base.subject, NOW, "Synthetic manual annotation only", base.filing_artifact_id,
        base.filing_sha256, (
            ShareActionObservation("Existing shares transferred to plan",
                ShareActionScope.HOLDER_OR_PLAN,
                ShareActionKind.TRANSFER, ShareActionStage.REPORTED_COMPLETED, (1,), 100,
                date(2024, 6, 21)),
            ShareActionObservation("Remaining plan shares reportedly sold; exact date absent",
                ShareActionScope.HOLDER_OR_PLAN, ShareActionKind.DISPOSAL,
                ShareActionStage.REPORTED_COMPLETED, (2,), 50),
            ShareActionObservation("Plan terminated, not issuer shares cancelled",
                ShareActionScope.HOLDER_OR_PLAN, ShareActionKind.PLAN_TERMINATION,
                ShareActionStage.REPORTED_COMPLETED, (2,)),
        ))


def _inspect_actions(foundation, review=None, as_of=NOW):
    return inspect_share_action_review(foundation[0], foundation[1],
                                       review or _action_review(foundation), as_of=as_of)


def test_plan_sales_and_termination_never_establish_issuer_delta_or_current_shares(foundation):
    store = foundation[0]
    before = store.path.read_bytes()
    result = _inspect_actions(foundation)
    assert result["source_bound"] and result["status"] == "MANUALLY_REVIEWED_UNQUALIFIED"
    assert result["trust_level"] == "low" and result["availability_precision"] == "retrieval_time"
    assert result["available_at"] == NOW
    assert result["observations"][0]["effective_date"] == date(2024, 6, 21)
    sale = result["observations"][1]
    assert sale["quantity_shares"] == 50 and sale["quantity_role"] == "holder_or_plan"
    assert sale["effective_date"] is None and sale["effective_date_precision"] == "NOT_REPORTED"
    assert result["issuer_share_delta"] is None
    assert result["current_shares"] is result["market_value"] is None
    assert all(item["issuer_share_delta"] is None for item in result["observations"])
    assert all(result[name] is False for name in (
        "canonical_facts_written", "valuation_authorized", "investment_scoring_authorized",
        "validation_authorized", "historical_replay_eligible", "execution_authorized",
        "readiness_promoted"))
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("quantity_shares", True), ("quantity_shares", 0), ("quantity_shares", -10),
    ("quantity_shares", 0.38), ("quantity_shares", "100"), ("quantity_shares", 10**16),
    ("source_pages", (True,)), ("source_pages", (1, 1)), ("source_pages", []),
    ("effective_date", "2026-06-24"), ("effective_date", NOW),
    ("scope", "holder_or_plan"), ("stage", "reported_completed"),
    ("scope", ShareActionScope.ISSUER_CAPITAL),
    ("kind", ShareActionKind.CANCELLATION), ("kind", ShareActionKind.PLAN_TERMINATION),
    ("reference", " "), ("reference", "password=synthetic-not-a-credential"),
])
def test_action_observations_reject_ambiguous_units_scope_and_unsafe_content(
    foundation, field, value,
):
    item = _action_review(foundation).observations[0]
    with pytest.raises(ValueError):
        replace(item, **{field: value})


@pytest.mark.parametrize("stage", [ShareActionStage.PROPOSED, ShareActionStage.PENDING,
                                   ShareActionStage.UNDETERMINED])
def test_unimplemented_observations_have_no_effective_date_or_delta(foundation, stage):
    review = _action_review(foundation)
    observation = ShareActionObservation(
        "Issuer cancellation proposal, not completed", ShareActionScope.ISSUER_CAPITAL,
        ShareActionKind.CANCELLATION, stage, (1,), 100)
    result = _inspect_actions(foundation, replace(review, observations=(observation,)))
    assert result["observations"][0]["effective_date"] is None
    assert result["observations"][0]["issuer_share_delta"] is None
    with pytest.raises(ValueError, match="effective date"):
        replace(observation, effective_date=date(2026, 6, 24))


@pytest.mark.parametrize("defect", ["future_review", "pre_capture", "pre_completion",
                                   "naive", "publication", "wrong_subject", "wrong_hash"])
def test_action_review_source_and_actual_visibility_fail_closed(foundation, defect):
    review = _action_review(foundation)
    with pytest.raises(ValueError):
        if defect == "future_review":
            _inspect_actions(foundation, as_of=NOW - timedelta(microseconds=1))
        elif defect == "pre_capture":
            _inspect_actions(foundation, replace(
                review, reviewed_at=CAPTURED - timedelta(seconds=1)))
        elif defect == "pre_completion":
            _inspect_actions(foundation, replace(
                review, reviewed_at=CAPTURED + timedelta(seconds=1)))
        elif defect == "naive":
            _inspect_actions(foundation, as_of=NOW.replace(tzinfo=None))
        elif defect == "publication":
            _inspect_actions(foundation, replace(review, observations=(replace(
                review.observations[0], effective_date=date(2026, 9, 1)),)))
        elif defect == "wrong_subject":
            _inspect_actions(foundation, replace(review, subject="000063"))
        else:
            _inspect_actions(foundation, replace(review, filing_sha256="a" * 64))


@pytest.mark.parametrize("defect", ["bytes", "registry", "batch_failed", "batch_subject",
                                   "batch_future", "unknown_trust"])
def test_action_review_reuses_strict_source_binding(foundation, defect):
    store, artifacts, review = foundation
    if defect == "bytes":
        path = artifacts.root / "sha256" / review.filing_sha256[:2] / f"{review.filing_sha256}.pdf"
        path.write_bytes(b"tamper")
    else:
        with store._connect() as connection:
            if defect == "registry":
                connection.execute("UPDATE provider_artifacts SET byte_size=?", (len(PDF) + 1,))
            elif defect == "unknown_trust":
                connection.execute("UPDATE provider_artifacts SET trust_level='unknown'")
            else:
                column, value = {
                    "batch_failed": ("status", "failed"),
                    "batch_subject": ("parameters_json", '{"subject":"000063"}'),
                    "batch_future": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
                }[defect]
                connection.execute(f"UPDATE ingestion_batches SET {column}=?", (value,))
    if defect == "unknown_trust":
        assert _inspect_actions(foundation)["trust_level"] == "unknown"
    else:
        with pytest.raises(ValueError):
            _inspect_actions(foundation)


def test_exact_pdf_review_is_opt_in_and_does_not_clear_unmatched_documents(foundation):
    store, artifacts, base = foundation
    review = _action_review(foundation)
    without = _continuity(foundation, as_of=NOW)
    assert without["manually_reviewed_announcements"] == 0
    result = inspect_share_continuity(store, artifacts, base, through=date(2026, 10, 26),
                                      as_of=NOW, document_reviews=(review,))
    assert result["manually_reviewed_announcements"] == 1
    assert result["document_review_items"][0]["document_review_state"] == (
        "MANUALLY_REVIEWED_UNQUALIFIED")
    assert result["document_review_items"][0]["effective_share_change"] == "NOT_ESTABLISHED"
    assert not result["unmatched_document_review_hashes"]
    relations = [item["relation_to_base_interval"]
                 for item in result["action_interval_observations"]]
    assert relations == ["AT_OR_BEFORE_BASE", "UNKNOWN_DATE", "UNKNOWN_DATE"]
    assert result["current_shares"] is None and not result["readiness_promoted"]
    with pytest.raises(ValueError, match="unique same-subject"):
        inspect_share_continuity(store, artifacts, base, through=date(2026, 10, 26),
                                as_of=NOW, document_reviews=(review, review))
    unmatched = inspect_share_continuity(store, artifacts, base, through=date(2026, 7, 31),
                                       as_of=NOW, document_reviews=(review,))
    assert unmatched["manually_reviewed_announcements"] == 0
    assert unmatched["unmatched_document_review_hashes"] == (review.review_hash,)


def test_changed_pdf_version_does_not_inherit_older_annotation(foundation):
    class ChangedClient(_Client):
        def download_artifact(self, url):
            return CnInfoArtifactDownload(ProviderArtifactStatus.CAPTURED, url, url,
                "application/pdf", PDF + b"\nchanged content", "")

    store, artifacts, base = foundation
    later = NOW + timedelta(minutes=1)
    request = ProviderDatasetRequest(CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "002624", later, {
        "start_date": "2026-08-20", "end_date": "2026-08-20",
        "capture_artifacts": "true", "max_artifacts": "1"})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: later).ingest(
        CnInfoDirectEvidenceAdapter(client=ChangedClient(), clock=lambda: later), request)
    result = inspect_share_continuity(store, artifacts, base, through=date(2026, 10, 26),
        as_of=later, document_reviews=(_action_review(foundation),))
    assert result["unique_bound_announcements"] == result["manually_reviewed_announcements"] == 1
    assert [item["document_review_state"] for item in result["document_review_items"]] == [
        "MANUALLY_REVIEWED_UNQUALIFIED", "NOT_REVIEWED"]


def test_metadata_only_version_of_same_document_does_not_inherit_review(foundation):
    store, artifacts, base = foundation
    later = NOW + timedelta(minutes=1)
    request = ProviderDatasetRequest(CNINFO_DISCLOSURES_DATASET, Market.CHINA_A, "002624", later, {
        "start_date": "2026-08-20", "end_date": "2026-08-20",
        "capture_artifacts": "false", "max_artifacts": "0"})
    ProviderNeutralIngestionService(store, artifact_store=artifacts, clock=lambda: later).ingest(
        CnInfoDirectEvidenceAdapter(client=_Client(), clock=lambda: later), request)
    result = inspect_share_continuity(store, artifacts, base, through=date(2026, 10, 26),
        as_of=later, document_reviews=(_action_review(foundation),))
    assert result["observed_metadata_versions"] == 2
    assert result["manually_reviewed_announcements"] == 1
    assert [item["document_review_state"] for item in result["document_review_items"]] == [
        "MANUALLY_REVIEWED_UNQUALIFIED", "NOT_REVIEWED"]


def test_later_action_annotation_does_not_relabel_an_earlier_inventory(foundation):
    store, artifacts, base = foundation
    before = _continuity(foundation, as_of=NOW)
    later_review = replace(_action_review(foundation), reviewed_at=NOW + timedelta(minutes=1))
    with pytest.raises(ValueError, match="not visible"):
        inspect_share_continuity(store, artifacts, base, through=date(2026, 10, 26),
                                as_of=NOW, document_reviews=(later_review,))
    assert _continuity(foundation, as_of=NOW) == before


def test_action_review_rejects_future_fold_despite_equal_local_labels(foundation):
    from zoneinfo import ZoneInfo

    early = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    with pytest.raises(ValueError, match="not visible"):
        _inspect_actions(foundation, replace(_action_review(foundation),
                                             reviewed_at=early.replace(fold=1)), as_of=early)


@pytest.mark.parametrize("effective,relation", [
    (date(2026, 6, 30), "AT_OR_BEFORE_BASE"),
    (date(2026, 7, 1), "WITHIN_INTERVAL"),
    (date(2026, 8, 1), "AFTER_THROUGH"),
])
def test_review_dates_are_not_all_treated_as_incremental_post_base_changes(
    foundation, effective, relation,
):
    store, artifacts, base = foundation
    review = _action_review(foundation)
    review = replace(review, observations=(replace(
        review.observations[0], effective_date=effective),))
    result = inspect_share_continuity(store, artifacts, base, through=date(2026, 7, 31),
                                      as_of=NOW, document_reviews=(review,))
    assert result["action_interval_observations"][0]["relation_to_base_interval"] == relation
    assert result["action_interval_observations"][0]["issuer_share_delta"] is None
    assert result["current_shares"] is None


def test_action_parser_rejects_unknown_fields_and_preserves_no_date(foundation):
    review = _action_review(foundation)
    body = json.loads(json.dumps(asdict(review), default=str))
    for row in body["observations"]:
        if row["effective_date"] is None:
            del row["effective_date"]
    parsed = parse_share_action_review({"review": body})
    assert parsed == review
    for document in ({"review": {**body, "issuer_share_delta": 0}},
                     {"review": {**body, "observations": [{
                         **body["observations"][0], "total_shares": 100}]}}):
        with pytest.raises(ValueError, match="unknown"):
            parse_share_action_review(document)
    with pytest.raises(ValueError, match="duplicate"):
        replace(review, observations=(review.observations[0], review.observations[0]))


def test_action_hashes_are_read_only_deterministic_and_bind_semantics(foundation):
    from zoneinfo import ZoneInfo

    before = foundation[0].path.read_bytes()
    review = _action_review(foundation)
    first = _inspect_actions(foundation)
    assert first == _inspect_actions(foundation, as_of=NOW.astimezone(ZoneInfo("Asia/Shanghai")))
    changed = replace(review, observations=(replace(review.observations[0], quantity_shares=99),))
    assert first["inspection_hash"] != _inspect_actions(foundation, changed)["inspection_hash"]
    assert first["review_hash"] != changed.review_hash
    assert foundation[0].path.read_bytes() == before


def test_combined_cli_explicit_action_plan_is_read_only_and_never_creates_report(
    foundation, tmp_path,
):
    import tomllib

    store, artifacts, base = foundation
    base_plan = tmp_path / "base.toml"
    body = json.loads(json.dumps(asdict(base), default=str))
    base_plan.write_text("[review]\n" + "\n".join(
        f"{key} = {json.dumps(value)}" for key, value in body.items() if value is not None))
    review = _action_review(foundation)
    plan = tmp_path / "actions.toml"
    header = {key: value for key, value in asdict(review).items() if key != "observations"}
    content = "[review]\n" + "\n".join(
        f"{key} = {json.dumps(value, default=str)}" for key, value in header.items())
    for observation in review.observations:
        content += "\n[[review.observations]]\n" + "\n".join(
            f"{key} = {json.dumps(value, default=str)}"
            for key, value in asdict(observation).items() if value is not None)
    plan.write_text(content)
    assert parse_share_action_review(tomllib.loads(content)) == review
    args = [sys.executable, "scripts/inspect_candidate_inputs.py", "--database", str(store.path),
        "--artifact-root", str(artifacts.root), "--symbol", "002624", "--sector-profile",
        "nonfinancial", "--metrics", "revenue", "--as-of", NOW.isoformat(),
        "--share-capital-review-plan", str(base_plan), "--share-action-review-plan", str(plan)]
    before = store.path.read_bytes()
    missing = subprocess.run(args, capture_output=True, text=True, check=False)
    assert missing.returncode == 2 and "through-date" in missing.stderr
    run = subprocess.run(args + ["--share-continuity-through", "2026-10-26"],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 2, run.stderr
    result = json.loads(run.stdout)
    assert result["share_continuity_review"]["manually_reviewed_announcements"] == 1
    assert not result["research_report_created"] and not result["execution_authorized"]
    assert store.path.read_bytes() == before
