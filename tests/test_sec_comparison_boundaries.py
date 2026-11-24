"""Existing-reader boundaries for pending record and representation comparisons."""

import runpy
from collections import Counter
from datetime import date, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import pytest

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.sec_period_inputs import SECPeriodSelection


@lru_cache
def _helpers():
    return runpy.run_path(str(Path(__file__).with_name("test_sec_body.py")))


@pytest.fixture
def foundation(tmp_path):
    return _helpers()["foundation"].__wrapped__(tmp_path)


def _unadmitted(document):
    assert document["trust_ceiling"] == "LOW"
    assert document["availability_precision"] == "retrieval_time"
    for name in ("issuer_to_instrument_verified", "sector_classification_verified",
                 "accounting_definitions_admitted", "financial_scoring_authorized",
                 "investment_scoring_authorized", "historical_replay_eligible",
                 "validation_authorized", "execution_authorized", "research_report_created"):
        assert document[name] is False
    for check in document["checks"]:
        assert check["amount_aggregation_authorized"] is False
        assert check["annual_or_quarter_classification"] == "NOT_ADMITTED"
        assert check["statement_and_consolidation_scope"] == "NOT_QUALIFIED"


@pytest.mark.parametrize("namespace", ("2025", "2026"))
@pytest.mark.parametrize("amount", ("120", "121"))
def test_tag_period_and_equal_values_cannot_select_a_qualified_namespace(
    foundation, namespace, amount,
):
    helper = _helpers()
    extra = f'''<ix:nonFraction xmlns:other="http://fasb.org/us-gaap/{namespace}"
        name="other:Revenues" contextRef="c" unitRef="u" decimals="-6"
        scale="6">{amount}</ix:nonFraction>'''
    helper["_capture"](foundation, helper["_xml"](extra=extra))
    document = helper["_periods"](foundation)
    check = document["checks"][0]
    assert check["status"] == ("OBSERVED_SUBSET_UNQUALIFIED" if amount == "120"
                               else "NUMERIC_CONFLICT")
    assert len(check["matching_occurrences"]) == 2
    assert {row["namespace"] for row in check["matching_occurrences"]} == (
        {"http://fasb.org/us-gaap/2025", f"http://fasb.org/us-gaap/{namespace}"})
    assert check["numeric_agreement_within_subset"] is (amount == "120")
    _unadmitted(document)


@pytest.mark.parametrize("start", (date(2025, 1, 1), date(2025, 4, 1)))
def test_same_end_and_value_do_not_make_different_duration_windows_comparable(foundation, start):
    helper = _helpers()
    extra = f'''<xbrli:context id="short"><xbrli:entity><xbrli:identifier
        scheme="http://www.sec.gov/CIK">{helper['CIK']}</xbrli:identifier></xbrli:entity>
        <xbrli:period><xbrli:startDate>{start}</xbrli:startDate>
        <xbrli:endDate>2025-06-30</xbrli:endDate></xbrli:period></xbrli:context>
        <ix:nonFraction name="us-gaap:Revenues" contextRef="short" unitRef="u"
        decimals="-6" scale="6">120</ix:nonFraction>'''
    helper["_capture"](foundation, helper["_xml"](extra=extra))
    document = helper["_periods"](foundation, selections=(
        SECPeriodSelection("Revenues", date(2024, 7, 1), date(2025, 6, 30)),
        SECPeriodSelection("Revenues", start, date(2025, 6, 30))))
    assert {row["duration_calendar_days"] for row in document["checks"]} == {
        365, (date(2025, 6, 30) - start).days + 1}
    assert all(check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
               and check["numeric_agreement_within_subset"] for check in document["checks"])
    for check in document["checks"]:
        assert len(check["matching_occurrences"]) == 1
        row = check["matching_occurrences"][0]
        assert row["native_attributes"]["contextRef"] == (
            "c" if check["period_start"] == date(2024, 7, 1) else "short")
        assert (row["period_start"], row["period_end"]) == (
            check["period_start"].isoformat(), "2025-06-30")
        assert row["value"] == "120000000" and row["status"] == "OBSERVED_UNQUALIFIED"
    _unadmitted(document)


def test_instant_and_duration_with_same_tag_end_and_value_keep_distinct_basis(foundation):
    helper = _helpers()
    extra = f'''<xbrli:context id="point"><xbrli:entity><xbrli:identifier
        scheme="http://www.sec.gov/CIK">{helper['CIK']}</xbrli:identifier></xbrli:entity>
        <xbrli:period><xbrli:instant>2025-06-30</xbrli:instant></xbrli:period></xbrli:context>
        <ix:nonFraction name="us-gaap:Revenues" contextRef="point" unitRef="u"
        decimals="-6" scale="6">120</ix:nonFraction>'''
    helper["_capture"](foundation, helper["_xml"](extra=extra))
    document = helper["_periods"](foundation, selections=(
        SECPeriodSelection("Revenues", date(2024, 7, 1), date(2025, 6, 30)),
        SECPeriodSelection("Revenues", None, date(2025, 6, 30))))
    assert {row["period_basis"] for row in document["checks"]} == {"instant", "duration"}
    assert sorted(row["duration_calendar_days"] or 0 for row in document["checks"]) == [0, 365]
    for check in document["checks"]:
        assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
        assert check["numeric_agreement_within_subset"] is True
        assert len(check["matching_occurrences"]) == 1
        row = check["matching_occurrences"][0]
        assert row["native_attributes"]["contextRef"] == (
            "point" if check["period_start"] is None else "c")
        assert (row["period_start"], row["period_end"]) == (
            check["period_start"].isoformat() if check["period_start"] else None, "2025-06-30")
        assert row["value"] == "120000000" and row["status"] == "OBSERVED_UNQUALIFIED"
    _unadmitted(document)


@pytest.mark.parametrize("amount", ("120", "999"))
def test_supported_agreement_does_not_resolve_excluded_matching_contexts(foundation, amount):
    helper = _helpers()
    extra = f'''<xbrli:context id="segment"><xbrli:entity><xbrli:identifier
        scheme="http://www.sec.gov/CIK">{helper['CIK']}</xbrli:identifier><xbrli:segment/>
        </xbrli:entity><xbrli:period><xbrli:startDate>2024-07-01</xbrli:startDate>
        <xbrli:endDate>2025-06-30</xbrli:endDate></xbrli:period></xbrli:context>
        <ix:nonFraction name="us-gaap:Revenues" contextRef="segment" unitRef="u"
        decimals="-6" scale="6">{amount}</ix:nonFraction>'''
    helper["_capture"](foundation, helper["_xml"](extra=extra))
    document = helper["_periods"](foundation)
    check = document["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["numeric_agreement_within_subset"] is True
    assert check["unresolved_tag_contexts_present"] is True
    assert check["unresolved_tag_occurrence_indices"]
    assert document["unsupported_fact_occurrence_count"] == 1
    _unadmitted(document)


@pytest.mark.parametrize("unusable", (False, True))
def test_later_retrieval_cannot_make_old_period_an_original_historical_vintage(
    foundation, unusable,
):
    helper = _helpers()
    helper["_capture"](foundation)
    before = helper["_periods"](foundation, at=helper["NOW"] - timedelta(microseconds=1))
    assert before["status"] == "SOURCE_UNAVAILABLE"
    assert all(row["status"] == "SOURCE_UNAVAILABLE" for row in before["checks"])
    if unusable:
        helper["_capture"](foundation, error="http_403", at=helper["NOW"] + timedelta(seconds=3))
    after = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=3))
    assert after["status"] == ("SOURCE_UNAVAILABLE" if unusable else "SOURCE_SUBSET_REVIEW")
    _unadmitted(before)
    _unadmitted(after)


def test_fixed_cutoff_only_vector_changes_receipt_identity_not_source_or_selected_facts(foundation):
    helper = _helpers()
    helper["_capture"](foundation)
    left = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=2))
    right = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=3))
    assert (left["input_hash"], right["input_hash"]) == (
        "9610b56d3d4aec4d34d90c8895b60322f40de6df493d399efc7f48add8cb65d5",
        "3945d49e326217162a18f836b2bbe6a235efc4659fd6cc3bfb71a5f7a3368eaa")
    assert left["as_of"] != right["as_of"]
    for key in ("source_evidence_id", "source_captures", "source_parent_binding",
                "source_body_sha256", "checks", "selected_fact_occurrence_count",
                "unsupported_fact_occurrence_count"):
        assert left[key] == right[key]
    assert left["source_body_sha256"] == (
        "8af69f6ab481f9244682577dac2203c2097f3291c4d7fac3299c400edb983fbe")
    assert sha256(financial_input_json(left["checks"]).encode()).hexdigest() == (
        "acb804c8a8f7e5a59aad2b9aa7a9dc8ebecea9123bd7c9fdad239751baa5012e")
    _unadmitted(left)
    _unadmitted(right)


@pytest.mark.parametrize("length", (511, 512, 513, 1024))
def test_retained_raw_text_is_a_bounded_preview_not_full_numeric_input(length):
    helper = _helpers()
    row = helper["_review"](helper["_xml"](text="1" * length))["facts"][0]
    assert row["raw_text"] == "1" * min(length, 512)
    assert row["status"] == "UNSUPPORTED_FACT"
    assert row["value"] is None
    assert row["reason"] == "numeric text exceeds bounds"


@pytest.mark.parametrize("length", (127, 128, 129))
def test_stripped_numeric_text_limit_is_independent_of_preview_bound(length):
    helper = _helpers()
    text = "0" * (length - 3) + "120"
    row = helper["_review"](helper["_xml"](text=text))["facts"][0]
    assert len(text) == length
    assert row["raw_text"] == text
    if length <= 128:
        assert row["status"] == "OBSERVED_UNQUALIFIED"
        assert row["value"] == "120000000" and row["reason"] is None
    else:
        assert row["status"] == "UNSUPPORTED_FACT" and row["value"] is None
        assert row["reason"] == "numeric text exceeds bounds"


def test_different_unsupported_suffixes_can_leave_all_matching_rows_identical(foundation):
    helper = _helpers()
    first = helper["_xml"](text="1" * 512 + "2")
    second = helper["_xml"](text="1" * 512 + "3")
    assert first != second
    helper["_capture"](foundation, first)
    previous = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=2))
    helper["_capture"](foundation, second, at=helper["NOW"] + timedelta(seconds=3))
    current = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=4))
    assert previous["source_body_sha256"] == sha256(first).hexdigest()
    assert current["source_body_sha256"] == sha256(second).hexdigest()
    assert previous["source_body_sha256"] != current["source_body_sha256"]
    assert previous["checks"] == current["checks"]
    check = current["checks"][0]
    assert check["status"] == "UNSUPPORTED_MATCHING_OCCURRENCE"
    assert check["numeric_agreement_within_subset"] is None
    assert len(check["matching_occurrences"]) == 1
    row = check["matching_occurrences"][0]
    assert row["raw_text"] == "1" * 512
    assert row["value"] is None and row["reason"] == "numeric text exceeds bounds"
    assert financial_input_json(previous["checks"]) == financial_input_json(current["checks"])
    _unadmitted(previous)
    _unadmitted(current)


@pytest.mark.parametrize("leading_spaces", (511, 512, 513))
def test_numeric_parser_uses_full_stripped_text_not_the_retained_preview(leading_spaces):
    helper = _helpers()
    rows = [helper["_review"](helper["_xml"](text=" " * leading_spaces + text))["facts"][0]
            for text in ("120", "121")]
    assert rows[0]["raw_text"] == rows[1]["raw_text"] == (" " * leading_spaces + "120")[:512]
    assert [row["value"] for row in rows] == ["120000000", "121000000"]
    assert all(row["status"] == "OBSERVED_UNQUALIFIED" and row["reason"] is None for row in rows)


@pytest.mark.parametrize("kind", ("markup", "character_reference", "attribute_spacing"))
def test_lexical_xml_changes_can_leave_complete_parser_occurrences_identical(foundation, kind):
    helper = _helpers()
    first = helper["_xml"](text="<span>120</span>" if kind == "markup" else "120")
    if kind == "markup":
        second = helper["_xml"](text="<b>120</b>")
    elif kind == "character_reference":
        second = helper["_xml"](text="12&#48;")
    else:
        second = first.replace(b'unitRef="u"', b' unitRef="u" ')
    assert first != second
    helper["_capture"](foundation, first)
    previous = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=2))
    helper["_capture"](foundation, second, at=helper["NOW"] + timedelta(seconds=3))
    current = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=4))
    assert previous["source_body_sha256"] != current["source_body_sha256"]
    assert previous["checks"] == current["checks"]
    check = current["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["numeric_agreement_within_subset"] is True
    assert len(check["matching_occurrences"]) == 1
    row = check["matching_occurrences"][0]
    assert row["raw_text"] == "120" and row["value"] == "120000000"
    _unadmitted(previous)
    _unadmitted(current)


def test_original_normalized_strings_remain_distinct_despite_subset_numeric_agreement(foundation):
    helper = _helpers()
    extra = '''<ix:nonFraction name="us-gaap:Revenues" contextRef="c" unitRef="u"
        decimals="-6" scale="6">120.00</ix:nonFraction>'''
    helper["_capture"](foundation, helper["_xml"](text="120.0", extra=extra))
    document = helper["_periods"](foundation)
    check = document["checks"][0]
    assert check["status"] == "OBSERVED_SUBSET_UNQUALIFIED"
    assert check["numeric_agreement_within_subset"] is True
    assert [row["value"] for row in check["matching_occurrences"]] == [
        "120000000.0", "120000000.00"]
    assert len({row["value"] for row in check["matching_occurrences"]}) == 2
    _unadmitted(document)


def test_record_order_changes_preserve_multiplicity_not_a_deduplicated_set(foundation):
    helper = _helpers()

    def content(values):
        extra = "".join(f'''<ix:nonFraction name="us-gaap:Revenues" contextRef="c"
            unitRef="u" decimals="-6" scale="6">{value}</ix:nonFraction>'''
                        for value in values[1:])
        return helper["_xml"](text=values[0], extra=extra)

    helper["_capture"](foundation, content(("120", "120", "121")))
    previous = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=2))
    helper["_capture"](foundation, content(("121", "120", "120")),
                       at=helper["NOW"] + timedelta(seconds=3))
    current = helper["_periods"](foundation, at=helper["NOW"] + timedelta(seconds=4))
    rows = [document["checks"][0]["matching_occurrences"] for document in (previous, current)]
    assert [row["value"] for row in rows[0]] != [row["value"] for row in rows[1]]
    for document, occurrences in zip((previous, current), rows, strict=True):
        assert document["checks"][0]["status"] == "NUMERIC_CONFLICT"
        assert document["checks"][0]["numeric_agreement_within_subset"] is False
        assert len(occurrences) == document["selected_fact_occurrence_count"] == 3
        assert Counter(row["value"] for row in occurrences) == {
            "120000000": 2, "121000000": 1}
        assert len({row["value"] for row in occurrences}) == 2
        _unadmitted(document)
