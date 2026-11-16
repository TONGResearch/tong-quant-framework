"""Synthetic source-bound receipts test calculations, not issuer/source authenticity."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256

import pytest

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.financial.nonfinancial import (
    NonfinancialDiagnosticStatus as Status,
)
from tong_quant.research.financial.nonfinancial import nonfinancial_diagnostics
from tong_quant.research.financial.nonfinancial_inputs import (
    NonfinancialInputPolicy,
    assess_nonfinancial_inputs,
)

NOW = datetime(2026, 10, 22, 10, tzinfo=UTC)
END = date(2026, 6, 30)


def _snapshot(**values):
    defaults = {"total_assets": "100", "total_liabilities": "50", "current_liabilities": "40",
                "monetary_funds": "20", "revenue": "200", "operating_cash_flow": "60",
                "operating_cash_inflow": "100", "operating_cash_outflow": "40"}
    defaults.update(values)
    instrument = Instrument("002624", Market.CHINA_A, "Synthetic fixture", available_at=NOW)
    entries = []
    for metric, value in sorted(defaults.items()):
        statement = ("income" if metric == "revenue" else "cash_flow"
                     if metric.startswith("operating_cash_") else "balance")
        fact = FundamentalFact(
            instrument, metric, END, NOW, NOW, Decimal(value), "Synthetic source",
            period_start=None if statement == "balance" else date(2026, 1, 1),
            currency="CNY", unit="absolute", raw_data_hash="e" * 64,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel.LOW,
        )
        entries.append(FinancialFactInspection(
            fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic receipt, no source approval",),
            reporting_scope="group", sector_profile="nonfinancial",
            evidence_id=sha256(metric.encode()).hexdigest(), review_artifact_id="a" * 64,
            filing_artifact_id="b" * 64, filing_sha256="c" * 64,
            source_pages=(41,), source_unit="CNY", source_column="group_current_period",
            audit_status="unaudited", statement=statement, filing_period_end=END,
        ))
    return FinancialInputSnapshot("002624", Market.CHINA_A, NOW, tuple(sorted(defaults)),
                                  "nonfinancial", "group", tuple(entries))


def _change(snapshot, metric, **changes):
    return replace(snapshot, inspections=tuple(
        replace(entry, **changes) if entry.fact.metric == metric else entry
        for entry in snapshot.inspections))


def _results(snapshot):
    return {item.name: item for item in nonfinancial_diagnostics(snapshot)}


def _checklist(snapshot=None, *, limit=0, target=None):
    return assess_nonfinancial_inputs(snapshot or _snapshot(), NonfinancialInputPolicy(limit),
                                      target_period_end=target)


def _check(result, metric):
    return next(item for item in result["checks"] if item["metric"] == metric)


def test_input_checklist_distinguishes_observed_not_requested_and_unimplemented_definitions():
    result = _checklist()
    assert sum(item["status"] == "observed_unqualified" for item in result["checks"]) == 8
    assert sum(item["status"] == "not_requested" for item in result["checks"]) == 3
    assert result["target_period_end"] == END
    assert result["target_period_basis"] == "latest_visible_required_metric"
    assert _check(result, "revenue")["trust_level"] == "low"
    assert _check(result, "revenue")["availability_precision"] == "retrieval_time"
    assert _check(result, "revenue")["latest_available_age_seconds"] == 0
    assert _check(result, "revenue")["report_age_days"] == 114
    assert _check(result, "revenue")["freshness"] == "unassessed"
    assert {item["metric"] for item in result["unimplemented_definitions"]} == {
        "roic", "interest_bearing_debt"}
    assert all(item["status"] == "definition_not_implemented"
               for item in result["unimplemented_definitions"])
    assert result["financial_scoring_policy"] == "NOT_ADMITTED"
    assert result["source_qualification"] == "NOT_ESTABLISHED"
    for name in ("investment_scoring_authorized", "validation_authorized",
                 "historical_replay_eligible", "execution_authorized"):
        assert result[name] is False


def test_missing_requested_metric_is_not_the_same_as_unimplemented_roic_definition():
    snapshot = _snapshot()
    snapshot = replace(snapshot, requested_metrics=tuple(sorted((
        *snapshot.requested_metrics, "profit_attributable_to_parent", "roic"))))
    result = _checklist(snapshot)
    assert _check(result, "profit_attributable_to_parent")["status"] == "missing"
    assert _check(result, "roe_weighted_ytd_unannualized")["status"] == "not_requested"
    roic = next(item for item in result["unimplemented_definitions"] if item["metric"] == "roic")
    assert roic["requested"] is True and roic["status"] == "definition_not_implemented"


@pytest.mark.parametrize("limit,expected", [
    (0, "unassessed"), (113, "stale"), (114, "within_configured_limit"),
    (115, "within_configured_limit"),
])
def test_nonfinancial_report_age_is_distinct_from_latest_availability_age(limit, expected):
    row = _check(_checklist(limit=limit), "revenue")
    assert row["report_age_days"] == 114 and row["latest_available_age_seconds"] == 0
    assert row["freshness"] == expected and row["status"] == "observed_unqualified"


@pytest.mark.parametrize("bad", [-1, True, 1.5, "114"])
def test_nonfinancial_input_age_policy_rejects_unsupported_values(bad):
    with pytest.raises(ValueError):
        NonfinancialInputPolicy(bad)


@pytest.mark.parametrize("target", [date(2026, 5, 31), date(2026, 12, 31), NOW])
def test_nonfinancial_input_target_requires_visible_calendar_quarter(target):
    with pytest.raises(ValueError, match="target period"):
        _checklist(target=target)


def test_explicit_target_does_not_fall_back_or_declare_latest_filing_complete():
    result = _checklist(target=date(2026, 9, 30))
    assert result["target_period_basis"] == "explicit"
    assert _check(result, "revenue")["status"] == "period_mismatch"
    assert result["investment_scoring_authorized"] is False


@pytest.mark.parametrize("status,expected", [
    (FinancialBindingStatus.REJECTED, "rejected"),
    (FinancialBindingStatus.UNSUPPORTED, "unsupported"),
])
def test_nonfinancial_input_checklist_retains_bad_latest_without_old_fallback(status, expected):
    snapshot = _snapshot()
    old = next(item for item in snapshot.inspections if item.fact.metric == "revenue")
    later = NOW + timedelta(seconds=1)
    bad = replace(old, status=status, fact=replace(old.fact, available_at=later))
    result = _checklist(replace(snapshot, as_of=later, inspections=(*snapshot.inspections, bad)))
    row = _check(result, "revenue")
    assert row["status"] == expected and len(row["observation_hashes"]) == 1


def test_nonfinancial_input_checklist_duplicate_latest_is_ambiguous():
    snapshot = _snapshot()
    row = _check(_checklist(replace(snapshot, inspections=snapshot.inspections * 2)), "revenue")
    assert row["status"] == "ambiguous" and len(row["observation_hashes"]) == 2


def test_nonfinancial_input_checklist_rejects_wrong_ytd_definition():
    snapshot = _snapshot()
    revenue = next(item for item in snapshot.inspections if item.fact.metric == "revenue")
    snapshot = _change(snapshot, "revenue", fact=replace(
        revenue.fact, period_start=date(2026, 2, 1)))
    assert _check(_checklist(snapshot), "revenue")["status"] == "semantic_mismatch"


@pytest.mark.parametrize("scope", [{"market": Market.US}, {"sector_profile": "bank"},
                                  {"sector_profile": "unknown"}])
def test_nonfinancial_checklist_is_not_an_implicit_bank_global_or_sector_classifier(scope):
    snapshot = replace(_snapshot(), inspections=(), **scope)
    with pytest.raises(ValueError, match="China-A group nonfinancial"):
        _checklist(snapshot)


def test_empty_nonfinancial_checklist_keeps_requested_and_unrequested_gaps():
    snapshot = replace(_snapshot(), requested_metrics=("revenue",), inspections=())
    result = _checklist(snapshot)
    assert result["target_period_end"] is None
    assert _check(result, "revenue")["status"] == "missing"
    assert _check(result, "operating_cash_flow")["status"] == "not_requested"
    assert not result["investment_scoring_authorized"]


def test_nonfinancial_checklist_hashes_bind_policy_period_source_and_timezone():
    from zoneinfo import ZoneInfo

    snapshot = _snapshot()
    first = _checklist(snapshot)
    local = replace(snapshot, as_of=NOW.astimezone(ZoneInfo("Asia/Shanghai")))
    assert first == _checklist(local)
    assert first["policy_hash"] != _checklist(limit=114)["policy_hash"]
    assert first["assessment_hash"] != _checklist(target=END)["assessment_hash"]
    changed = _change(snapshot, "revenue", source_pages=(42,))
    assert first["assessment_hash"] != _checklist(changed)["assessment_hash"]


def test_exact_ratios_and_reconciliation_are_deterministic_unscored_and_low_trust():
    snapshot = _snapshot()
    first = nonfinancial_diagnostics(snapshot)
    assert first == nonfinancial_diagnostics(snapshot)
    assert [item.value for item in first] == [Decimal("50.0000"), Decimal("50.0000"),
                                            Decimal("30.0000"), Decimal("0")]
    for item in first:
        assert item.status is Status.DESCRIPTIVE and item.period_end == END
        assert item.snapshot_hash == snapshot.input_hash and item.evidence_ids
        assert item.trust_levels == ("low",) and item.availability_precisions == ("retrieval_time",)
        document = item.document()
        assert not document["investment_scoring_authorized"]
        assert not document["validation_authorized"] and not document["historical_replay_eligible"]
        assert len(document["diagnostic_hash"]) == 64
    with localcontext() as context:
        context.prec = 6
        assert first == nonfinancial_diagnostics(snapshot)


@pytest.mark.parametrize("metric,name", [
    ("total_assets", "liabilities_to_assets_percent"),
    ("current_liabilities", "monetary_funds_to_current_liabilities_percent"),
    ("revenue", "operating_cash_flow_to_revenue_percent"),
])
def test_zero_denominators_do_not_produce_favorable_ratios(metric, name):
    result = _results(_snapshot(**{metric: "0"}))[name]
    assert result.status is Status.NONPOSITIVE_BASE and result.value is None


def test_negative_cash_flow_remains_negative_and_can_reconcile():
    results = _results(_snapshot(operating_cash_inflow="20", operating_cash_flow="-20"))
    assert results["operating_cash_reconciliation_residual"].value == 0
    assert results["operating_cash_flow_to_revenue_percent"].value == Decimal("-10.0000")


@pytest.mark.parametrize("net", ["61", "60.00001"])
def test_inconsistent_cash_flow_keeps_residual_and_withholds_dependent_ratio(net):
    results = _results(_snapshot(operating_cash_flow=net))
    residual = results["operating_cash_reconciliation_residual"]
    assert residual.status is Status.INCONSISTENT and residual.value == Decimal("60") - Decimal(net)
    assert results["operating_cash_flow_to_revenue_percent"].status is Status.INCONSISTENT
    assert results["operating_cash_flow_to_revenue_percent"].value is None
    assert results["liabilities_to_assets_percent"].status is Status.DESCRIPTIVE


@pytest.mark.parametrize("requested", [True, False])
def test_missing_cash_components_are_not_zero_or_cash_quality_approval(requested):
    snapshot = _snapshot()
    missing = "operating_cash_inflow"
    snapshot = replace(snapshot, inspections=tuple(
        entry for entry in snapshot.inspections if entry.fact.metric != missing),
        requested_metrics=tuple(metric for metric in snapshot.requested_metrics
                                if requested or metric != missing))
    results = _results(snapshot)
    assert results["operating_cash_reconciliation_residual"].status is Status.UNAVAILABLE
    assert results["operating_cash_reconciliation_residual"].value is None
    ratio = results["operating_cash_flow_to_revenue_percent"]
    assert ratio.value == 30 and any("unavailable" in reason for reason in ratio.reasons)
    assert not ratio.document()["investment_scoring_authorized"]


@pytest.mark.parametrize("status", [FinancialBindingStatus.REJECTED,
                                    FinancialBindingStatus.UNSUPPORTED])
def test_latest_rejected_component_cannot_fall_back_to_older_favorable_input(status):
    snapshot = _snapshot()
    entry = next(item for item in snapshot.inspections
                 if item.fact.metric == "operating_cash_inflow")
    older = replace(entry, fact=replace(entry.fact, available_at=NOW - timedelta(hours=1),
                                       published_at=NOW - timedelta(hours=1)))
    newer = replace(entry, status=status)
    remaining = tuple(item for item in snapshot.inspections
                      if item.fact.metric != entry.fact.metric)
    snapshot = replace(snapshot, inspections=(*remaining, older, newer))
    results = _results(snapshot)
    assert results["operating_cash_reconciliation_residual"].status is Status.INCOMPATIBLE
    assert results["operating_cash_flow_to_revenue_percent"].value is None


@pytest.mark.parametrize("defect", [
    "different_filing", "different_artifact", "different_audit", "ambiguous", "wrong_period",
    "wrong_statement", "wrong_flow_start", "extreme_number",
])
def test_diagnostic_input_mismatches_fail_closed(defect):
    snapshot = _snapshot()
    entry = next(item for item in snapshot.inspections if item.fact.metric == "total_assets")
    expected = "liabilities_to_assets_percent"
    if defect == "different_filing":
        snapshot = _change(snapshot, "total_assets", filing_sha256="d" * 64)
    elif defect == "different_artifact":
        snapshot = _change(snapshot, "total_assets", filing_artifact_id="d" * 64)
    elif defect == "different_audit":
        snapshot = _change(snapshot, "total_assets", audit_status="audited")
    elif defect == "ambiguous":
        snapshot = replace(snapshot, inspections=(*snapshot.inspections, entry))
    elif defect == "wrong_period":
        snapshot = _change(snapshot, "total_assets", fact=replace(
            entry.fact, period_end=date(2026, 9, 30)), filing_period_end=date(2026, 9, 30))
    elif defect == "wrong_statement":
        snapshot = _change(snapshot, "total_assets", statement="income")
    elif defect == "extreme_number":
        snapshot = _change(snapshot, "total_assets", fact=replace(
            entry.fact, value=Decimal("1e1000")))
    else:
        flow = next(item for item in snapshot.inspections if item.fact.metric == "revenue")
        snapshot = _change(snapshot, "revenue", fact=replace(
            flow.fact, period_start=date(2026, 2, 1)))
        expected = "operating_cash_flow_to_revenue_percent"
    result = _results(snapshot)[expected]
    assert result.status is Status.INCOMPATIBLE and result.value is None


@pytest.mark.parametrize("profile,market", [
    ("bank", Market.CHINA_A), ("unknown", Market.CHINA_A), ("nonfinancial", Market.US),
])
def test_nonfinancial_scope_is_not_implicitly_applied_to_other_sectors_or_markets(profile, market):
    snapshot = replace(_snapshot(), sector_profile=profile, market=market, inspections=())
    with pytest.raises(ValueError, match="China-A group nonfinancial"):
        nonfinancial_diagnostics(snapshot)


def test_future_fact_cannot_enter_diagnostics():
    snapshot = _snapshot()
    entry = snapshot.inspections[0]
    with pytest.raises(ValueError, match="subject/time/semantics mismatch"):
        _change(snapshot, entry.fact.metric,
                fact=replace(entry.fact, available_at=NOW + timedelta(seconds=1)))


def test_changed_bound_input_changes_diagnostic_identity_without_qualifying_trust():
    left = _results(_snapshot())["liabilities_to_assets_percent"]
    right = _results(_snapshot(total_liabilities="51"))["liabilities_to_assets_percent"]
    assert left.document()["diagnostic_hash"] != right.document()["diagnostic_hash"]
    assert left.trust_levels == right.trust_levels == ("low",)


def test_unknown_trust_is_preserved_without_a_numeric_or_source_quality_upgrade():
    snapshot = _snapshot()
    entry = next(item for item in snapshot.inspections if item.fact.metric == "total_assets")
    snapshot = _change(snapshot, "total_assets",
                       fact=replace(entry.fact, trust_level=DataTrustLevel.UNKNOWN))
    result = _results(snapshot)["liabilities_to_assets_percent"]
    assert result.value == 50 and result.trust_levels == ("low", "unknown")
    assert not result.document()["validation_authorized"]


@pytest.mark.parametrize("requested", [True, False])
def test_missing_component_cannot_hide_a_different_rejected_component(requested):
    snapshot = _snapshot()
    missing = "operating_cash_inflow"
    snapshot = replace(snapshot, inspections=tuple(
        entry for entry in snapshot.inspections if entry.fact.metric != missing),
        requested_metrics=tuple(metric for metric in snapshot.requested_metrics
                                if requested or metric != missing))
    snapshot = _change(snapshot, "operating_cash_outflow", status=FinancialBindingStatus.REJECTED)
    results = _results(snapshot)
    check = results["operating_cash_reconciliation_residual"]
    assert check.status is Status.INCOMPATIBLE
    assert "operating_cash_outflow" in check.reasons[0] and missing in check.reasons[0]
    ratio = results["operating_cash_flow_to_revenue_percent"]
    assert ratio.status is Status.INCOMPATIBLE and ratio.value is None
