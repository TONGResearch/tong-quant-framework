"""Synthetic declarations do not qualify source data or validate holding decisions."""

import json
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel
from tong_quant.research.models import ThesisInvalidationCondition
from tong_quant.research.thesis_bindings import (
    ThesisEvidenceReference,
    ThesisMetricBinding,
    ThesisPeriod,
    describe_thesis_binding,
)

NOW = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
PERIOD = ThesisPeriod(date(2026, 7, 1), date(2026, 9, 30))
BINDING = ThesisMetricBinding("us:TEST", "revenue", "SyntheticRevenue", "test-gaap",
                             "synthetic-v1", "group", "nonfinancial", "USD", "USD")
CONDITION = ThesisInvalidationCondition("H1", "Synthetic only", "revenue", "<",
                                        Decimal("10"), "unparsed legacy text", "Synthetic test")


def _reference(**changes):
    values = dict(binding=BINDING, period=PERIOD, evidence_id="synthetic-evidence",
        batch_id="synthetic-batch", provider="synthetic", document_id="synthetic-document",
        document_sha256="a" * 64, input_sha256="b" * 64, revision="original",
        published_at=NOW - timedelta(days=1), available_at=NOW,
        trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME)
    return ThesisEvidenceReference(**(values | changes))


def _describe(evidence=None, **changes):
    return describe_thesis_binding(CONDITION, BINDING, periods=(PERIOD,),
        evidence=(_reference(),) if evidence is None else evidence, **(
            {"decision_as_of": NOW} | changes))


def test_complete_declarations_remain_unqualified_and_leave_old_model_unchanged():
    before = asdict(CONDITION)
    result = _describe()
    assert result == _describe() and asdict(CONDITION) == before
    assert result["binding_status"] == "DECLARED_ONLY"
    assert result["evaluation"] == "NOT_EVALUATED"
    assert result["holding_horizon"] == "NOT_ESTIMATED"
    assert result["source_qualification"] == "NOT_ADMITTED"
    assert result["source_verification"] == "NOT_PERFORMED"
    assert result["window_continuity"] == "NOT_VERIFIED"
    assert all(value is False for key, value in result.items() if key.endswith("_authorized"))
    digest = result.pop("binding_hash")
    assert digest == sha256(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode()).hexdigest()


def test_absent_references_are_missing_not_an_untriggered_condition():
    result = _describe(())
    assert result["missing_period_bindings"] == [{"start": "2026-07-01", "end": "2026-09-30"}]
    assert result["binding_status"] == "INCOMPLETE_OR_CONFLICTED"
    assert result["evaluation"] == "NOT_EVALUATED"


@pytest.mark.parametrize("field,value", [
    ("instrument_id", "us:OTHER"), ("native_tag", "OtherTag"),
    ("namespace", "other-gaap"), ("definition_version", "v2"),
    ("statement_scope", "segment"), ("sector_profile", "bank"),
    ("unit", "USD millions"), ("currency", "MYR"),
])
def test_same_metric_with_different_identity_or_definition_is_not_a_match(field, value):
    result = _describe((_reference(binding=replace(BINDING, **{field: value})),))
    assert result["missing_period_bindings"]
    assert result["references"][0]["binding_issues"] == ["METRIC_DEFINITION_OR_IDENTITY_MISMATCH"]


def test_wrong_period_is_retained_and_cannot_fill_requested_window():
    result = _describe((_reference(period=ThesisPeriod(date(2026, 1, 1), date(2026, 9, 30))),))
    assert result["missing_period_bindings"]
    assert result["references"][0]["binding_issues"] == ["UNREQUESTED_PERIOD"]


def test_dst_fold_future_reference_is_retained_but_excluded():
    zone = ZoneInfo("America/New_York")
    cutoff = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    future = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)
    result = _describe((_reference(available_at=future),), decision_as_of=cutoff)
    assert result["references"][0]["binding_issues"] == ["FUTURE_EVIDENCE_REFERENCE"]
    assert result["missing_period_bindings"]


def test_equivalent_utc_labels_hash_identically():
    assert _describe() == _describe((_reference(available_at=NOW.astimezone(
        ZoneInfo("Asia/Kuala_Lumpur"))),), decision_as_of=NOW.astimezone(
            ZoneInfo("Asia/Kuala_Lumpur")))


def test_multiple_revisions_remain_ambiguous_without_latest_good_fallback():
    old = _reference(evidence_id="old", available_at=NOW - timedelta(hours=1))
    new = _reference(evidence_id="new", revision="revision-1")
    result = _describe((old, new))
    assert result == _describe((new, old))
    assert result["ambiguous_period_bindings"] and len(result["references"]) == 2
    assert result["binding_status"] == "INCOMPLETE_OR_CONFLICTED"


def test_future_revision_cannot_turn_older_matching_reference_into_clean_binding():
    future = _reference(evidence_id="future", revision="new",
                        available_at=NOW + timedelta(seconds=1))
    result = _describe((_reference(), future))
    assert not result["missing_period_bindings"]
    assert result["binding_status"] == "INCOMPLETE_OR_CONFLICTED"
    assert result["evaluation"] == "NOT_EVALUATED"


def test_explicit_gapped_periods_do_not_claim_fiscal_continuity():
    prior = ThesisPeriod(date(2025, 7, 1), date(2025, 9, 30))
    result = describe_thesis_binding(CONDITION, BINDING, periods=(prior, PERIOD),
        evidence=(_reference(period=prior, evidence_id="prior"), _reference()), decision_as_of=NOW)
    assert result["binding_status"] == "DECLARED_ONLY"
    assert result["window_continuity"] == "NOT_VERIFIED"


def test_hash_binds_condition_and_document_revision_without_rewriting_old_definition():
    original = _describe()
    changed = _describe((_reference(document_sha256="c" * 64),))
    condition = replace(CONDITION, observation_window="different declaration")
    other = describe_thesis_binding(condition, BINDING, periods=(PERIOD,),
                                    evidence=(_reference(),), decision_as_of=NOW)
    assert len({item["binding_hash"] for item in (original, changed, other)}) == 3


@pytest.mark.parametrize("trust", list(DataTrustLevel))
def test_trust_claims_do_not_grant_qualification(trust):
    result = _describe((_reference(trust_level=trust),))
    assert result["source_qualification"] == "NOT_ADMITTED"
    assert result["evaluation"] == "NOT_EVALUATED"


@pytest.mark.parametrize("periods", [[], (), (PERIOD, PERIOD),
    (ThesisPeriod(date(2026, 8, 1), date(2026, 10, 1)), PERIOD),
    (PERIOD, ThesisPeriod(date(2026, 9, 30), date(2026, 10, 31))),
    (PERIOD, ThesisPeriod(None, date(2026, 10, 31))),
    (ThesisPeriod(None, date(2027, 1, 1)),)])
def test_unsafe_windows_rejected(periods):
    with pytest.raises(ValueError):
        describe_thesis_binding(CONDITION, BINDING, periods=periods,
                               evidence=(), decision_as_of=NOW)


@pytest.mark.parametrize("change", [
    {"document_sha256": "not-a-hash"}, {"input_sha256": "A" * 64},
    {"evidence_id": ""}, {"revision": ""}, {"provider": "token=synthetic-secret"},
    {"available_at": NOW.replace(tzinfo=None)}, {"published_at": NOW + timedelta(seconds=1)},
    {"trust_level": "HIGH"}, {"availability_precision": "retrieval_time"},
])
def test_malformed_references_rejected(change):
    with pytest.raises(ValueError):
        _reference(**change)


def test_duplicate_ids_and_metric_mismatch_rejected():
    with pytest.raises(ValueError, match="unique"):
        _describe((_reference(), _reference()))
    with pytest.raises(ValueError, match="disagree"):
        describe_thesis_binding(replace(CONDITION, metric="cash"), BINDING,
                               periods=(PERIOD,), evidence=(), decision_as_of=NOW)


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), Decimal("NaN")])
def test_nonfinite_threshold_cannot_be_hashed_as_a_valid_declaration(threshold):
    with pytest.raises(ValueError):
        describe_thesis_binding(replace(CONDITION, threshold=threshold), BINDING,
                               periods=(PERIOD,), evidence=(), decision_as_of=NOW)
