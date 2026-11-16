"""Synthetic structural receipts do not qualify bank research or source trust."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tong_quant.config.settings import FinancialResearchSettings, load_settings
from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.config import research_engine_from_settings
from tong_quant.research.financial import FinancialResearchModule
from tong_quant.research.financial.inputs import (
    BANK_INPUT_REQUIREMENTS,
    BankInputFreshness,
    BankInputPolicy,
    BankInputStatus,
    assess_bank_inputs,
)

NOW = datetime(2026, 10, 19, 6, tzinfo=UTC)
METRICS = tuple(sorted(item.metric for item in BANK_INPUT_REQUIREMENTS))


def _snapshot():
    fact = FundamentalFact(
        Instrument("600000", Market.CHINA_A, "Synthetic bank", industry="bank"),
        "revenue", date(2026, 3, 31), datetime(2026, 4, 30, tzinfo=UTC), NOW,
        Decimal("100"), "synthetic only", period_start=date(2026, 1, 1),
        currency="CNY", unit="absolute", trust_level=DataTrustLevel.LOW,
        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
    )
    entry = FinancialFactInspection(
        fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic, not real source verification",),
        reporting_scope="group", sector_profile="bank", evidence_id="a" * 64,
        review_artifact_id="b" * 64, filing_artifact_id="c" * 64, filing_sha256="d" * 64,
        source_pages=(17,), source_unit="CNY_million", source_column="group_current_period",
        audit_status="unaudited", statement="income", filing_period_end=fact.period_end,
    )
    return FinancialInputSnapshot("600000", Market.CHINA_A, NOW, METRICS,
                                   "bank", "group", (entry,))


def _revenue(result):
    return next(item for item in result.checks if item.metric == "revenue")


def test_zero_age_is_unassessed_not_a_freshness_pass_and_never_scores():
    snapshot = _snapshot()
    first = assess_bank_inputs(snapshot, BankInputPolicy())
    row = _revenue(first)
    assert row.status is BankInputStatus.OBSERVED_UNQUALIFIED
    assert row.report_age_days == 202 and row.freshness is BankInputFreshness.UNASSESSED
    assert row.trust_level == "low" and row.availability_precision == "retrieval_time"
    assert sum(item.status is BankInputStatus.MISSING for item in first.checks) == 8
    assert first.document() == assess_bank_inputs(snapshot, BankInputPolicy()).document()
    assert first.target_period_basis == "latest_visible_required_metric"
    assert not first.document()["investment_scoring_authorized"]
    assert not first.document()["historical_replay_eligible"]
    assert not first.document()["validation_authorized"]


@pytest.mark.parametrize("limit,freshness", [
    (201, BankInputFreshness.STALE), (202, BankInputFreshness.WITHIN_LIMIT),
    (203, BankInputFreshness.WITHIN_LIMIT),
])
def test_age_uses_report_period_not_current_capture_and_includes_boundary(limit, freshness):
    row = _revenue(assess_bank_inputs(_snapshot(), BankInputPolicy(limit)))
    assert row.report_age_days == 202 and row.freshness is freshness
    assert row.status is BankInputStatus.OBSERVED_UNQUALIFIED


def test_historical_as_of_uses_its_own_period_age():
    original = _snapshot()
    entry = original.inspections[0]
    cutoff = datetime(2026, 5, 1, tzinfo=UTC)
    snapshot = replace(original, as_of=cutoff, inspections=(
        replace(entry, fact=replace(entry.fact, available_at=cutoff)),))
    assert _revenue(assess_bank_inputs(snapshot, BankInputPolicy(31))).report_age_days == 31


def test_equivalent_timezone_instants_use_the_same_china_market_date_and_hash():
    snapshot = _snapshot()
    cutoff = datetime(2026, 10, 18, 17, tzinfo=UTC)
    snapshot = replace(snapshot, as_of=cutoff, inspections=(replace(
        snapshot.inspections[0], fact=replace(snapshot.inspections[0].fact, available_at=cutoff)),))
    local = replace(snapshot, as_of=cutoff.astimezone(ZoneInfo("Asia/Shanghai")))
    first = assess_bank_inputs(snapshot, BankInputPolicy(202))
    second = assess_bank_inputs(local, BankInputPolicy(202))
    assert _revenue(first).report_age_days == 202
    assert first.document()["assessment_hash"] == second.document()["assessment_hash"]


def test_not_requested_is_distinct_from_requested_but_missing():
    snapshot = replace(_snapshot(), requested_metrics=("revenue",))
    result = assess_bank_inputs(snapshot, BankInputPolicy())
    assert sum(item.status is BankInputStatus.NOT_REQUESTED for item in result.checks) == 8
    assert not any(item.status is BankInputStatus.MISSING for item in result.checks)


@pytest.mark.parametrize("status,expected", [
    (FinancialBindingStatus.REJECTED, BankInputStatus.REJECTED),
    (FinancialBindingStatus.UNSUPPORTED, BankInputStatus.UNSUPPORTED),
])
def test_latest_rejected_or_unsupported_record_does_not_fall_back(status, expected):
    snapshot = _snapshot()
    good = snapshot.inspections[0]
    bad = replace(good, status=status, fact=replace(
        good.fact, available_at=NOW + timedelta(seconds=1)))
    snapshot = replace(snapshot, as_of=NOW + timedelta(seconds=1), inspections=(good, bad))
    result = assess_bank_inputs(snapshot, BankInputPolicy())
    assert _revenue(result).status is expected and len(result.checks) == 9


def test_duplicate_latest_is_explicitly_ambiguous_not_extra_evidence():
    snapshot = _snapshot()
    result = assess_bank_inputs(replace(snapshot, inspections=snapshot.inspections * 2),
                                BankInputPolicy())
    assert _revenue(result).status is BankInputStatus.AMBIGUOUS
    assert len(_revenue(result).observation_hashes) == 2


def test_wrong_ytd_definition_and_target_period_remain_visible():
    snapshot = _snapshot()
    entry = snapshot.inspections[0]
    wrong = replace(entry, fact=replace(entry.fact, period_start=date(2026, 2, 1)))
    changed = assess_bank_inputs(replace(snapshot, inspections=(wrong,)), BankInputPolicy())
    assert _revenue(changed).status is BankInputStatus.SEMANTIC_MISMATCH
    result = assess_bank_inputs(snapshot, BankInputPolicy(), target_period_end=date(2026, 6, 30))
    assert _revenue(result).status is BankInputStatus.PERIOD_MISMATCH
    assert result.target_period_basis == "explicit"


def test_inferred_nonquarter_filing_cannot_pass_calendar_quarter_semantics():
    snapshot = _snapshot()
    entry = snapshot.inspections[0]
    wrong = replace(entry, filing_period_end=date(2026, 2, 28),
                    fact=replace(entry.fact, period_end=date(2026, 2, 28)))
    result = assess_bank_inputs(replace(snapshot, inspections=(wrong,)), BankInputPolicy())
    assert _revenue(result).status is BankInputStatus.SEMANTIC_MISMATCH


@pytest.mark.parametrize("period", [date(2026, 4, 30), date(2027, 3, 31), NOW])
def test_invalid_target_periods_fail_closed(period):
    with pytest.raises(ValueError, match="target period"):
        assess_bank_inputs(_snapshot(), BankInputPolicy(), target_period_end=period)


@pytest.mark.parametrize("value", [-1, True, 1.5, "180"])
def test_invalid_age_policy_and_settings_fail_closed(value):
    with pytest.raises(ValueError):
        BankInputPolicy(value)
    with pytest.raises(ValueError):
        FinancialResearchSettings(value)


def test_policy_hash_includes_age_and_results_bind_exact_receipt():
    snapshot = _snapshot()
    first = assess_bank_inputs(snapshot, BankInputPolicy())
    assert first.policy_hash != BankInputPolicy(180).policy_hash
    assert first.document()["assessment_hash"] != assess_bank_inputs(
        snapshot, BankInputPolicy(180)).document()["assessment_hash"]
    changed = replace(snapshot, inspections=(replace(snapshot.inspections[0], source_pages=(18,)),))
    assert first.input_hash != assess_bank_inputs(changed, BankInputPolicy()).input_hash
    assert not {"score", "investment_score", "action", "order"}.intersection(first.document())


def test_china_bank_policy_is_not_implicitly_applied_to_other_sectors_or_markets():
    snapshot = _snapshot()
    for query in (replace(snapshot, market=Market.US, inspections=()),
                  replace(snapshot, sector_profile="nonfinancial", inspections=())):
        with pytest.raises(ValueError, match="China-A"):
            assess_bank_inputs(query, BankInputPolicy())


def test_settings_factory_wires_effective_age_policy(tmp_path):
    default = load_settings(Path("config/default.toml"))
    assert default.research.financial.maximum_report_age_days == 0
    override = tmp_path / "age.toml"
    override.write_text("[research.financial]\nmaximum_report_age_days=180\n")
    settings = load_settings(Path("config/default.toml"), override)
    engine = research_engine_from_settings(settings.research)
    financial = next(item for item in engine.modules if isinstance(item, FinancialResearchModule))
    assert financial.bank_input_policy.maximum_report_age_days == 180
    assert financial.nonfinancial_input_policy.maximum_report_age_days == 180
