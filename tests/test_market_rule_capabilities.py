from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.markets.capabilities import (
    MarketRuleCapability,
    MarketRuleCoverageInspector,
    MarketRuleEvidence,
    MarketRuleEvidenceCatalog,
    MarketRuleQuery,
    MarketRuleScope,
)


def _query() -> MarketRuleQuery:
    return MarketRuleQuery(
        scope=MarketRuleScope(Market.CHINA_A, "test-exchange", "main", "cash"),
        trade_date=date(2026, 1, 5), as_of=datetime(2026, 1, 5, tzinfo=UTC),
    )


def _records() -> tuple[MarketRuleEvidence, ...]:
    return tuple(
        MarketRuleEvidence(
            evidence_id=f"fixture-{capability.value}", scope=_query().scope,
            capability=capability, rule_version="fixture-v1",
            effective_from=date(2026, 1, 1), effective_to=None,
            available_at=datetime(2026, 1, 1, tzinfo=UTC),
            source_reference="synthetic test fixture; no actual exchange verification",
            content_sha256="a" * 64, trust_level=DataTrustLevel.HIGH,
            availability_precision=AvailabilityPrecision.EXACT,
        )
        for capability in MarketRuleCapability
    )


def test_empty_rule_catalog_preserves_all_required_gaps() -> None:
    coverage = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog()).inspect(_query())
    assert not coverage.complete
    assert set(coverage.missing_capabilities) == set(MarketRuleCapability)
    assert coverage.selected_evidence == ()


def test_rule_coverage_hash_is_order_independent_and_content_bound() -> None:
    records = _records()
    first = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog(records)).inspect(_query())
    second = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog(records[::-1])).inspect(_query())
    changed = (replace(records[0], content_sha256="b" * 64), *records[1:])
    third = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog(changed)).inspect(_query())
    assert first.complete
    assert first.evidence_hash == second.evidence_hash
    assert first.evidence_hash != third.evidence_hash
    assert "dated rule evaluators remain required" in first.warnings[-1]


@pytest.mark.parametrize(
    "change, reason",
    [
        ({"available_at": datetime(2026, 1, 6, tzinfo=UTC)}, "not_yet_available"),
        ({"effective_from": date(2026, 1, 6)}, "not_effective"),
        ({"effective_to": date(2026, 1, 5)}, "not_effective"),
        ({"trust_level": DataTrustLevel.LOW}, "insufficient_trust"),
        ({"trust_level": DataTrustLevel.UNKNOWN}, "insufficient_trust"),
        ({"availability_precision": AvailabilityPrecision.UNKNOWN}, "availability_imprecise"),
        ({"availability_precision": AvailabilityPrecision.DATE_ONLY}, "availability_imprecise"),
        ({"availability_precision": AvailabilityPrecision.ESTIMATED}, "availability_imprecise"),
    ],
)
def test_future_expired_or_untrusted_rules_cannot_complete_coverage(
    change: dict[str, object], reason: str,
) -> None:
    records = _records()
    unavailable = replace(records[0], **change)  # type: ignore[arg-type]
    coverage = MarketRuleCoverageInspector(
        MarketRuleEvidenceCatalog((unavailable, *records[1:]))
    ).inspect(_query())
    assert not coverage.complete
    assert unavailable.capability in coverage.missing_capabilities
    assert f"{unavailable.evidence_id}:{reason}" in coverage.warnings


def test_retrieval_only_rule_evidence_keeps_its_conservative_availability() -> None:
    records = _records()
    retrieved = replace(
        records[0], availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        available_at=_query().as_of,
    )
    inspector = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog((retrieved, *records[1:])))
    current = inspector.inspect(_query())
    historical = inspector.inspect(replace(_query(), as_of=records[0].available_at))
    assert current.complete
    assert f"{retrieved.evidence_id}:retrieval_time_only" in current.warnings
    assert not historical.complete


def test_overlapping_rule_versions_are_ambiguous_instead_of_latest_wins() -> None:
    records = _records()
    overlap = replace(records[0], evidence_id="overlap", rule_version="fixture-v2")
    coverage = MarketRuleCoverageInspector(
        MarketRuleEvidenceCatalog((*records, overlap))
    ).inspect(_query())
    assert not coverage.complete
    assert coverage.ambiguous_capabilities == (overlap.capability,)


def test_effective_date_handover_selects_one_rule_version() -> None:
    records = _records()
    old = replace(records[0], effective_to=_query().trade_date)
    new = replace(
        records[0], evidence_id="new-version", rule_version="fixture-v2",
        effective_from=_query().trade_date,
    )
    coverage = MarketRuleCoverageInspector(
        MarketRuleEvidenceCatalog((old, new, *records[1:])),
    ).inspect(_query())
    assert coverage.complete
    assert new in coverage.selected_evidence
    assert old not in coverage.selected_evidence


@pytest.mark.parametrize("field", ["market", "exchange", "board", "account_type"])
def test_rules_cannot_cross_market_exchange_board_or_account_scope(field: str) -> None:
    alternate = Market.US if field == "market" else "different"
    query = replace(_query(), scope=replace(_query().scope, **{field: alternate}))
    coverage = MarketRuleCoverageInspector(MarketRuleEvidenceCatalog(_records())).inspect(query)
    assert not coverage.complete
    assert set(coverage.missing_capabilities) == set(MarketRuleCapability)


def test_duplicate_evidence_identity_is_rejected() -> None:
    record = _records()[0]
    with pytest.raises(ValueError, match="identities must be unique"):
        MarketRuleEvidenceCatalog((record, record))
