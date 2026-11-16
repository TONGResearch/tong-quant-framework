"""Synthetic visibility clocks are not data-source or strategy qualification."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from itertools import permutations
from zoneinfo import ZoneInfo

import pytest

from tong_quant.domain.enums import EvidenceQuality, ResearchConclusion, ResearchModuleName
from tong_quant.research.base import assessment_from_scores, insufficient_assessment
from tong_quant.research.confidence import (
    combine_confidence,
    confidence_from_evidence,
    report_confidence,
)
from tong_quant.research.models import ConfidenceBreakdown, ResearchAssessment, ResearchEvidence
from tong_quant.version import RESEARCH_CONFIDENCE_VERSION

FIRST = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
SECOND = FIRST.replace(fold=1)


def _evidence(available, name="fixture"):
    return ResearchEvidence(name, ResearchModuleName.POLICY, name, 70,
        FIRST - timedelta(days=1), available, "synthetic", EvidenceQuality.PRIMARY)


def _assessment(**changes):
    result = ResearchAssessment(ResearchModuleName.POLICY, ResearchConclusion.SUPPORTIVE, 70,
        combine_confidence(evidence_quality=100, data_completeness=100,
                           module_agreement=100, point_in_time_integrity=100),
        FIRST, FIRST, ("Synthetic finding",), (), (), (), "synthetic")
    return replace(result, **changes)


def _confidence(kind, evidence, cutoff):
    if kind == "module":
        return confidence_from_evidence(evidence, required_names=frozenset({"fixture"}),
                                        as_of=cutoff, agreement_scores=(70,))
    return report_confidence((_assessment(),), evidence, as_of=cutoff)


@pytest.mark.parametrize("kind", ["module", "report"])
@pytest.mark.parametrize("later", [SECOND, SECOND.replace(minute=15)])
def test_future_repeated_hour_cannot_receive_full_pit_integrity(kind, later):
    assert later.astimezone(UTC) > FIRST.astimezone(UTC)
    result = _confidence(kind, (_evidence(later),), FIRST)
    assert result.point_in_time_integrity == result.confidence == 0
    if kind == "module":
        assert result.data_completeness == result.evidence_quality == 0


@pytest.mark.parametrize("kind", ["module", "report"])
def test_visible_earlier_instant_is_not_rejected_for_later_wall_clock(kind):
    earlier = FIRST.replace(minute=45)
    cutoff = SECOND.replace(minute=15)
    assert earlier.astimezone(UTC) < cutoff.astimezone(UTC)
    result = _confidence(kind, (_evidence(earlier),), cutoff)
    assert result.point_in_time_integrity == 100
    assert result.confidence == 100


@pytest.mark.parametrize("kind", ["module", "report"])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_visibility_boundary_is_exact_to_one_microsecond(kind, delta):
    cutoff = SECOND.astimezone(UTC)
    result = _confidence(kind, (_evidence(cutoff + timedelta(microseconds=delta)),), cutoff)
    assert result.point_in_time_integrity == (100 if delta <= 0 else 0)
    assert result.confidence == (100 if delta <= 0 else 0)


@pytest.mark.parametrize("kind", ["module", "report"])
@pytest.mark.parametrize("zone", ["UTC", "Asia/Kuala_Lumpur", "America/New_York"])
def test_equivalent_timezone_labels_have_identical_confidence(kind, zone):
    record = _evidence(SECOND)
    result = _confidence(kind, (record,), SECOND)
    equivalent = replace(record, observed_at=record.observed_at.astimezone(ZoneInfo(zone)),
                         available_at=record.available_at.astimezone(ZoneInfo(zone)))
    assert _confidence(kind, (equivalent,), SECOND.astimezone(ZoneInfo(zone))) == result
    assert result.method.endswith(RESEARCH_CONFIDENCE_VERSION)


@pytest.mark.parametrize("kind", ["module", "report"])
def test_naive_confidence_cutoff_is_rejected_even_for_empty_evidence(kind):
    with pytest.raises(ValueError, match="timezone"):
        _confidence(kind, (), datetime(2026, 11, 1))


@pytest.mark.parametrize("later", [SECOND, SECOND.replace(minute=15)])
def test_assessment_contract_rejects_future_availability_across_dst_fold(later):
    with pytest.raises(ValueError, match="future data"):
        _assessment(available_at=later)


def test_assessment_contract_accepts_visible_earlier_wall_clock_later_label():
    earlier = FIRST.replace(minute=45)
    cutoff = SECOND.replace(minute=15)
    result = _assessment(evaluated_at=cutoff, available_at=earlier)
    assert result.available_at is earlier  # Preserve the supplied timestamp, not a rewrite.


@pytest.mark.parametrize("kind", ["scored", "insufficient"])
@pytest.mark.parametrize("reverse", [False, True])
def test_base_assessment_maximum_availability_uses_actual_utc(kind, reverse):
    first = _evidence(FIRST.replace(minute=45), "first")
    second = _evidence(SECOND.replace(minute=15), "second")
    evidence = tuple(permutations((first, second)))[reverse]
    kwargs = {"module": ResearchModuleName.POLICY, "evidence": evidence,
        "required_names": frozenset({"first", "second"}), "as_of": SECOND,
        "limitations": ("Synthetic only",), "model_version": "synthetic"}
    result = (assessment_from_scores(**kwargs, scores=(70, 70), findings=("Synthetic",), risks=())
              if kind == "scored" else insufficient_assessment(**kwargs))
    assert result.available_at is second.available_at
    assert result.confidence.point_in_time_integrity == 100
    assert result.confidence.method.endswith(RESEARCH_CONFIDENCE_VERSION)


@pytest.mark.parametrize("kind", ["module", "report"])
def test_empty_confidence_does_not_become_completed_research(kind):
    result = _confidence(kind, (), FIRST)
    assert result.evidence_quality == 0
    assert result.confidence < 1
    assert result.method.endswith(RESEARCH_CONFIDENCE_VERSION)


def test_explicit_legacy_confidence_method_is_not_silently_upgraded():
    original = _assessment().confidence
    old = {**asdict(original), "method": "weighted_geometric_with_weakest_link_cap"}
    restored = ConfidenceBreakdown(**old)
    assert asdict(restored) == old
    assert original.method != restored.method
