"""H3 source labels and arithmetic-looking inputs never establish an FCF definition."""

import runpy
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import pytest

from tong_quant.application.sec_window_inventory import SECWindowPair, read_sec_window_inventory
from tong_quant.data.sec_period_inputs import SECPeriodSelection
from tong_quant.data.storage.sqlite import SQLiteStore

OCF = "NetCashProvidedByUsedInOperatingActivities"
PPE = "PaymentsToAcquirePropertyPlantAndEquipment"
LEASE = ("PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAcquired"
         "InExchangeForFinanceLeaseLiability")
NS = "http://fasb.org/us-gaap/2025"


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_sec_body.py")))


@pytest.fixture
def foundation(tmp_path):
    return _helpers()["foundation"].__wrapped__(tmp_path)


def _selection(tag, *, instant=False):
    return SECPeriodSelection(tag, None if instant else date(2024, 7, 1), date(2025, 6, 30))


def _capture(foundation, *, ppe="50", lease=False):
    extra = f'''<ix:nonFraction name="us-gaap:{PPE}" contextRef="c" unitRef="u"
        decimals="-6" scale="6">{ppe}</ix:nonFraction>'''
    if lease:
        extra += f'''<ix:nonFraction name="us-gaap:{LEASE}" contextRef="c" unitRef="u"
            decimals="-6" scale="6">999</ix:nonFraction>'''
    body = _helpers()["_xml"](extra=extra).replace(b'us-gaap:Revenues', f'us-gaap:{OCF}'.encode())
    _helpers()["_capture"](foundation, body)


def _read(foundation, tags=(OCF, PPE), *, instant=False):
    pairs = tuple(SECWindowPair(_selection(tag, instant=instant), _selection(tag, instant=instant),
                               NS) for tag in tags)
    helper = _helpers()
    return read_sec_window_inventory(SQLiteStore(foundation[0].path, read_only=True), foundation[1],
        helper["CIK"], helper["ACCESSION"], symbol="MSFT",
        as_of=helper["NOW"] + timedelta(seconds=2), pairs=pairs, maximum_capture_age_seconds=3600)


@pytest.mark.parametrize("ppe", ("50", "0", "-50"))
def test_observed_cash_flow_tags_and_signed_amounts_never_authorize_cash_residual(foundation, ppe):
    _capture(foundation, ppe=ppe)
    result = _read(foundation)
    assert result["source_requested_tags"] == sorted((OCF, PPE))
    assert result["source_occurrence_count"] == 2
    assert all(pair["raw_context_status"] == "OBSERVED_UNQUALIFIED" for pair in result["pairs"])
    assert all(pair["economic_comparison_status"] == "NOT_ADMITTED" for pair in result["pairs"])
    assert result["accounting_definitions_admitted"] is False
    assert result["financial_scoring_authorized"] is False
    assert result["holding_management_authorized"] is result["execution_authorized"] is False
    for pair in result["pairs"]:
        for side in (pair["left"], pair["right"]):
            assert side["matching_occurrence_count"] == 1
            assert all("value" not in item for item in side["occurrence_references"])
    assert "free_cash_flow" not in result and "cash_residual" not in result


def test_fcf_alias_cannot_be_filled_from_two_different_native_tags(foundation):
    _capture(foundation)
    result = _read(foundation, tags=("FreeCashFlow",))
    for side in ("left", "right"):
        assert result["pairs"][0][side]["check_status"] == "MISSING_EXACT_PERIOD"
        assert result["pairs"][0][side]["matching_occurrence_count"] == 0
    assert result["pairs"][0]["raw_context_status"] == "BLOCKED"
    assert result["economic_comparison_status"] == "NOT_ADMITTED"


def test_cross_metric_pair_is_not_a_subtraction_formula():
    with pytest.raises(ValueError, match="one exact tag"):
        SECWindowPair(_selection(OCF), _selection(PPE), NS)


def test_instant_request_does_not_substitute_duration_cash_flow(foundation):
    _capture(foundation)
    result = _read(foundation, instant=True)
    assert all(pair["raw_context_status"] == "BLOCKED" for pair in result["pairs"])
    assert all(pair["left"]["check_status"] == "MISSING_EXACT_PERIOD" for pair in result["pairs"])


def test_zero_excluded_count_in_requested_tags_does_not_establish_lease_absence(foundation):
    _capture(foundation, lease=True)
    result = _read(foundation)
    assert result["source_requested_tags"] == sorted((OCF, PPE))
    assert result["source_occurrence_count"] == 2
    assert result["unsupported_source_occurrence_count"] == 0
    assert LEASE not in result["source_requested_tags"]
    assert result["economic_comparison_status"] == "NOT_ADMITTED"
    assert result["accounting_definitions_admitted"] is False
