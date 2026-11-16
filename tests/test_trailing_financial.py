"""Synthetic, unqualified edition receipts exercise trailing arithmetic boundaries."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from hashlib import sha256
from zoneinfo import ZoneInfo

import pytest

from tong_quant.data.financial_inputs import (
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import FundamentalFact, Instrument
from tong_quant.research.financial.trailing import (
    TrailingEditionReview,
    parse_trailing_reviews,
    trailing_financial_diagnostics,
    trailing_input_hash,
)
from tong_quant.research.financial.trailing import (
    TrailingStatus as Status,
)

CAPTURE = datetime(2026, 10, 23, 10, tzinfo=UTC)
REVIEW = CAPTURE + timedelta(hours=1)
NOW = REVIEW + timedelta(hours=1)
METRIC = "profit_attributable_to_parent"


def _snapshot(end=date(2026, 6, 30), current="-10", annual="100", prior="30"):
    instrument = Instrument("002624", Market.CHINA_A, "Synthetic", available_at=CAPTURE)
    roles = ((end, current, "group_current_period"),
             (date(end.year - 1, 12, 31), annual, "group_current_period"),
             (date(end.year - 1, end.month, end.day), prior, "group_prior_year_period"))
    entries = []
    for index, (period, value, column) in enumerate(roles):
        fact = FundamentalFact(
            instrument, METRIC, period, CAPTURE, CAPTURE, Decimal(value), "Synthetic source",
            period_start=date(period.year, 1, 1), currency="CNY", unit="absolute",
            raw_data_hash=sha256(str(index).encode()).hexdigest(),
            trust_level=DataTrustLevel.LOW,
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
        )
        entries.append(FinancialFactInspection(
            fact, FinancialBindingStatus.SOURCE_BOUND, ("Synthetic receipt only",),
            reporting_scope="group", sector_profile="nonfinancial",
            evidence_id=sha256(f"evidence{index}".encode()).hexdigest(),
            review_artifact_id=sha256(f"review{index}".encode()).hexdigest(),
            filing_artifact_id=("a" if index == 1 else "b") * 64,
            filing_sha256=("c" if index == 1 else "d") * 64, source_pages=(7,),
            source_unit="CNY", source_column=column,
            audit_status="audited" if index == 1 else "unaudited", statement="income",
            filing_period_end=period if index == 1 else end,
            comparability="as_presented_same_filing" if index == 2 else None,
            issuer_revision_status="unverified" if index == 2 else None,
        ))
    return FinancialInputSnapshot("002624", Market.CHINA_A, NOW, (METRIC,),
                                  "nonfinancial", "group", tuple(entries))


def _review(snapshot):
    return TrailingEditionReview(
        METRIC, *(trailing_input_hash(e) for e in snapshot.inspections), REVIEW,
        "Synthetic test reviewer", ("Manual as-reported arithmetic, not independent review",),
    )


def _result(snapshot, reviews=()):
    return trailing_financial_diagnostics(snapshot, reviews)[0]


@pytest.mark.parametrize("end,start", [(date(2026, 3, 31), date(2025, 4, 1)),
                                      (date(2026, 6, 30), date(2025, 7, 1)),
                                      (date(2026, 9, 30), date(2025, 10, 1))])
@pytest.mark.parametrize("current,annual,prior,expected", [
    ("-10.25", "100.11", "30.01", "59.85"), ("-80", "100", "30", "-10"),
    ("-70", "100", "30", "0"),
])
def test_exact_signed_trailing_arithmetic_is_review_bound_and_diagnostic_only(
    end, start, current, annual, prior, expected,
):
    snapshot = _snapshot(end, current, annual, prior)
    review = _review(snapshot)
    unreviewed = _result(snapshot)
    assert unreviewed.status is Status.REVIEW_REQUIRED and unreviewed.value is None
    result = _result(snapshot, (review,))
    assert result.status is Status.DERIVED and result.value == Decimal(expected)
    assert result.period_start == start and result.period_end == end
    assert result.available_at == REVIEW and result.review_hash == review.review_hash
    assert len(result.input_hashes) == len(result.evidence_ids) == 3
    assert result.trust_levels == ("low",) and result.availability_precisions == ("retrieval_time",)
    body = result.document()
    assert body["valuation_multiple"] is None
    for key in ("investment_scoring_authorized", "validation_authorized",
                "historical_replay_eligible", "execution_authorized"):
        assert body[key] is False
    with localcontext() as context:
        context.prec = 3
        assert _result(snapshot, (review,)) == result
    reordered = replace(snapshot, inspections=tuple(reversed(snapshot.inspections)))
    assert _result(reordered, (review,)).value == result.value


def test_reported_annual_is_not_synthesized_or_annualized():
    original = _snapshot()
    annual = original.inspections[1]
    result = _result(replace(original, inspections=(annual,)))
    assert result.status is Status.ANNUAL and result.value == Decimal("100")
    assert result.period_start == date(2025, 1, 1) and result.review_hash is None
    assert len(result.input_hashes) == 1


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("defect", ["value", "revision", "source", "pages"])
def test_exact_review_cannot_authorize_changed_receipts(index, defect):
    snapshot = _snapshot()
    review = _review(snapshot)
    entries = list(snapshot.inspections)
    entry = entries[index]
    changes = {"value": {"value": Decimal("999")}, "revision": {"revision": 1},
               "source": {"raw_data_hash": "f" * 64}}
    entries[index] = (replace(entry, source_pages=(8,)) if defect == "pages"
                      else replace(entry, fact=replace(entry.fact, **changes[defect])))
    result = _result(replace(snapshot, inspections=tuple(entries)), (review,))
    assert result.status is Status.REVIEW_REQUIRED and result.value is None


@pytest.mark.parametrize("reviewed", [CAPTURE - timedelta(seconds=1), NOW + timedelta(seconds=1)])
def test_review_must_not_predate_inputs_or_follow_cutoff(reviewed):
    snapshot = _snapshot()
    result = _result(snapshot, (replace(_review(snapshot), reviewed_at=reviewed),))
    assert result.status is Status.INCOMPATIBLE and result.value is None


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("status", [FinancialBindingStatus.REJECTED,
                                  FinancialBindingStatus.UNSUPPORTED])
def test_bad_required_receipt_stays_visible_and_blocks_even_with_missing_component(index, status):
    snapshot = _snapshot()
    entries = list(snapshot.inspections)
    entries[index] = replace(entries[index], status=status)
    if index == 1:
        entries.pop(2)  # Missing comparative cannot mask a rejected annual component.
    result = _result(replace(snapshot, inspections=tuple(entries)))
    assert result.status is Status.INCOMPATIBLE and result.value is None


@pytest.mark.parametrize("index", [1, 2])
def test_missing_required_component_does_not_guess_a_quarter_or_annualize(index):
    snapshot = _snapshot()
    result = _result(replace(snapshot, inspections=tuple(
        e for i, e in enumerate(snapshot.inspections) if i != index)))
    assert result.status is Status.MISSING and result.value is None


def test_missing_not_requested_and_ambiguous_receipts_remain_distinct():
    snapshot = _snapshot()
    assert _result(replace(snapshot, inspections=())).status is Status.MISSING
    assert trailing_financial_diagnostics(snapshot)[1].status is Status.NOT_REQUESTED
    duplicate = replace(snapshot, inspections=(*snapshot.inspections, snapshot.inspections[0]))
    assert _result(duplicate).status is Status.INCOMPATIBLE
    review = _review(snapshot)
    assert _result(snapshot, (review, review)).status is Status.INCOMPATIBLE


@pytest.mark.parametrize("change", [{"filing_sha256": "f" * 64},
                                    {"filing_artifact_id": "f" * 64},
                                    {"statement": "balance"}])
def test_comparative_must_match_current_filing_edition(change):
    snapshot = _snapshot()
    entries = list(snapshot.inspections)
    entries[2] = replace(entries[2], **change)
    result = _result(replace(snapshot, inspections=tuple(entries)))
    assert result.status is Status.INCOMPATIBLE and result.value is None


def test_latest_bad_revision_cannot_fall_back_to_an_older_good_annual():
    snapshot = _snapshot()
    annual = snapshot.inspections[1]
    bad = replace(annual, status=FinancialBindingStatus.REJECTED,
                  fact=replace(annual.fact, available_at=REVIEW, revision=1))
    result = _result(replace(snapshot, inspections=(*snapshot.inspections, bad)))
    assert result.status is Status.INCOMPATIBLE and result.value is None


def test_future_inputs_and_dst_fold_cannot_authorize_a_trailing_amount():
    original = _snapshot()
    with pytest.raises(ValueError):
        replace(original, as_of=CAPTURE - timedelta(seconds=1))
    zone = ZoneInfo("America/New_York")
    decision = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    future = decision.replace(fold=1)
    first = original.inspections[0]
    entry = replace(first, fact=replace(first.fact, published_at=decision, available_at=future))
    with pytest.raises(ValueError, match="financial snapshot"):
        replace(original, as_of=decision, inspections=(entry,))
    folded = replace(original, as_of=decision)
    object.__setattr__(folded, "inspections", (entry,))
    with pytest.raises(ValueError, match="financial snapshot"):
        trailing_financial_diagnostics(folded)


def test_review_parser_roundtrip_and_hash_is_timezone_normalized():
    review = _review(_snapshot())
    body = asdict(review)
    body.pop("basis")
    body.pop("model_version")
    body["reviewed_at"] = review.reviewed_at.isoformat()
    body["limitations"] = list(review.limitations)
    assert parse_trailing_reviews({"reviews": [body]}) == (review,)
    assert replace(review, reviewed_at=review.reviewed_at.astimezone(
        ZoneInfo("Asia/Shanghai"))).review_hash == review.review_hash
    assert replace(review, limitations=("Another explicit limitation",)).review_hash != (
        review.review_hash)


@pytest.mark.parametrize("defect", ["extra", "missing", "secret", "blank", "bad_hash"])
def test_review_documents_reject_unknown_fields_credentials_and_bad_bindings(defect):
    review = _review(_snapshot())
    body = asdict(review)
    body.pop("basis")
    body.pop("model_version")
    body["reviewed_at"] = review.reviewed_at.isoformat()
    body["limitations"] = list(review.limitations)
    if defect == "extra":
        body["auto_approve"] = True
    elif defect == "missing":
        del body["prior_input_hash"]
    elif defect == "secret":
        body["api_key"] = "synthetic-noncredential-placeholder"
    elif defect == "blank":
        body["limitations"] = []
    else:
        body["annual_input_hash"] = "bad"
    with pytest.raises(ValueError):
        parse_trailing_reviews({"reviews": [body]})
