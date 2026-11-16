"""Reviewed, as-reported trailing amounts; no valuation/scoring qualification."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from enum import StrEnum
from hashlib import sha256

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import (
    CNY_FILING_UNIT_MULTIPLIERS,
    FinancialBindingStatus,
    FinancialFactInspection,
    FinancialInputSnapshot,
    financial_input_json,
)
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import TRAILING_FINANCIAL_VERSION

_METRICS = ("profit_attributable_to_parent", "revenue")
_BASIS = "manual_as_reported_calendar_ytd_bridge"


def trailing_input_hash(entry: FinancialFactInspection) -> str:
    """Bind the full receipt, not just its value, name or caller-chosen evidence id."""
    entry.__post_init__()
    return sha256(financial_input_json(asdict(entry)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class TrailingEditionReview:
    metric: str
    current_input_hash: str
    annual_input_hash: str
    prior_input_hash: str
    reviewed_at: datetime
    reviewer: str
    limitations: tuple[str, ...]
    basis: str = _BASIS
    model_version: str = TRAILING_FINANCIAL_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.reviewed_at, "reviewed_at")
        hashes = (self.current_input_hash, self.annual_input_hash, self.prior_input_hash)
        if (self.metric not in _METRICS or self.basis != _BASIS
                or self.model_version != TRAILING_FINANCIAL_VERSION
                or any(not isinstance(h, str) or len(h) != 64
                       or any(c not in "0123456789abcdef" for c in h) for h in hashes)
                or len(set(hashes)) != 3
                or not isinstance(self.reviewer, str) or not self.reviewer.strip()
                or len(self.reviewer) > 500 or type(self.limitations) is not tuple
                or not 1 <= len(self.limitations) <= 20
                or any(not isinstance(s, str) or not s.strip() or len(s) > 2000
                       for s in self.limitations)):
            raise ValueError("invalid bounded trailing-edition review")
        reject_sensitive_structure(asdict(self), path="trailing_edition_review")

    @property
    def review_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()


def parse_trailing_reviews(document: Mapping[str, object]) -> tuple[TrailingEditionReview, ...]:
    reject_sensitive_structure(document, path="trailing_reviews")
    rows = document.get("reviews")
    if set(document) != {"reviews"} or not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise ValueError("trailing reviews require a bounded reviews list")
    result = []
    keys = {"metric", "current_input_hash", "annual_input_hash", "prior_input_hash",
            "reviewed_at", "reviewer", "limitations"}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != keys
                or any(not isinstance(row[k], str) for k in keys - {"limitations"})
                or not isinstance(row["limitations"], list)):
            raise ValueError("invalid trailing review document")
        result.append(TrailingEditionReview(
            row["metric"], row["current_input_hash"], row["annual_input_hash"],
            row["prior_input_hash"], datetime.fromisoformat(row["reviewed_at"]),
            row["reviewer"], tuple(row["limitations"]),
        ))
    return tuple(result)


class TrailingStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    REVIEW_REQUIRED = "edition_review_required"
    ANNUAL = "reported_annual_unqualified"
    DERIVED = "derived_as_reported_unqualified"


@dataclass(frozen=True, slots=True)
class TrailingFinancialDiagnostic:
    metric: str
    status: TrailingStatus
    as_of: datetime
    snapshot_hash: str
    reasons: tuple[str, ...]
    period_start: date | None = None
    period_end: date | None = None
    value: Decimal | None = None
    available_at: datetime | None = None
    input_hashes: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    trust_levels: tuple[str, ...] = ()
    availability_precisions: tuple[str, ...] = ()
    review_hash: str | None = None
    review_limitations: tuple[str, ...] = ()
    model_version: str = TRAILING_FINANCIAL_VERSION

    def document(self) -> dict[str, object]:
        body = asdict(self)
        return {
            **body, "diagnostic_hash": sha256(financial_input_json(body).encode()).hexdigest(),
            "formula": "previous_full_year + current_ytd - prior_year_ytd; annual uses reported FY",
            "unit": "CNY", "valuation_multiple": None,
            "investment_scoring_authorized": False, "validation_authorized": False,
            "historical_replay_eligible": False, "execution_authorized": False,
            "limitations": (
                "As-reported calendar-year group amounts, not independently qualified TTM.",
                "Manual edition review permits descriptive arithmetic only, not accounting "
                "comparability, original revision/publication proof or source-trust promotion.",
                "Consolidation changes, restatements, accounting changes, recurring earnings, "
                "freshness, dated market value and sector policy need independent review.",
                "No annualization, guessed quarters, favorable fallback or valuation score.",
            ),
        }


def _pick(entries: list[FinancialFactInspection], period: date) -> FinancialFactInspection | None:
    rows = [entry for entry in entries if entry.fact.period_end == period]
    if not rows:
        return None
    key = max((e.fact.available_at.astimezone(UTC), e.fact.revision) for e in rows)
    latest = [e for e in rows if (e.fact.available_at.astimezone(UTC), e.fact.revision) == key]
    if len(latest) != 1:
        raise ValueError(f"Ambiguous latest receipt at {period}")
    return latest[0]


def _current(entry: FinancialFactInspection) -> bool:
    return (entry.source_column == "group_current_period"
            and entry.filing_period_end == entry.fact.period_end
            and entry.comparability is None and entry.issuer_revision_status is None)


def trailing_financial_diagnostics(
    snapshot: FinancialInputSnapshot, reviews: tuple[TrailingEditionReview, ...] = (),
) -> tuple[TrailingFinancialDiagnostic, ...]:
    snapshot.__post_init__()
    cutoff = snapshot.as_of.astimezone(UTC)
    if snapshot.market is not Market.CHINA_A or snapshot.sector_profile != "nonfinancial":
        raise ValueError("trailing diagnostics require China-A group nonfinancial inputs")
    if type(reviews) is not tuple or len(reviews) > 20:
        raise ValueError("trailing reviews must be an immutable bounded tuple")
    for review in reviews:
        review.__post_init__()
    if any(e.fact.available_at.astimezone(UTC) > cutoff
           or e.fact.published_at.astimezone(UTC) > cutoff for e in snapshot.inspections):
        raise ValueError("trailing inputs cannot follow the UTC cutoff")
    results = []
    for metric in _METRICS:
        result = TrailingFinancialDiagnostic(
            metric, TrailingStatus.NOT_REQUESTED, snapshot.as_of, snapshot.input_hash,
            (f"Input not requested: {metric}",),
        )
        if metric not in snapshot.requested_metrics:
            results.append(result)
            continue
        entries = [e for e in snapshot.inspections if e.fact.metric == metric]
        if not entries:
            results.append(replace(result, status=TrailingStatus.MISSING,
                                   reasons=(f"Input missing: {metric}",)))
            continue
        try:
            end = max(e.fact.period_end for e in entries)
            current = _pick(entries, end)
            assert current is not None
            if not _current(current) or end.year < 2:
                raise ValueError("Latest observation is not an explicit current column")
            annual_end = date(end.year - 1, 12, 31)
            prior_end = date(end.year - 1, end.month, end.day)
            annual = current if end.month == 12 and end.day == 31 else _pick(entries, annual_end)
            prior = None if annual is current else _pick(entries, prior_end)
            selected = (current,) if annual is current else tuple(
                e for e in (current, annual, prior) if e is not None)
            for entry in selected:
                fact = entry.fact
                if (entry.status is not FinancialBindingStatus.SOURCE_BOUND
                        or entry.sector_profile != "nonfinancial"
                        or entry.reporting_scope != "group"
                        or entry.statement != "income" or entry.measurement_basis is not None
                        or entry.source_unit not in CNY_FILING_UNIT_MULTIPLIERS
                        or fact.unit != "absolute" or fact.currency != "CNY"
                        or fact.period_start != date(fact.period_end.year, 1, 1)
                        or (fact.period_end.month, fact.period_end.day)
                        not in {(3, 31), (6, 30), (9, 30), (12, 31)}
                        or len(fact.value.as_tuple().digits) > 256
                        or abs(int(fact.value.as_tuple().exponent)) > 200):
                    raise ValueError(
                        "Latest required receipt rejected, unsupported or incompatible")
            if annual is not None and not _current(annual):
                raise ValueError("Annual input is not its explicit current full-year column")
            if prior is not None and (
                prior.source_column != "group_prior_year_period"
                or prior.filing_period_end != end
                or prior.filing_artifact_id != current.filing_artifact_id
                or prior.filing_sha256 != current.filing_sha256
                or prior.audit_status != current.audit_status
                or prior.comparability != "as_presented_same_filing"
                or prior.issuer_revision_status != "unverified"
            ):
                raise ValueError("Prior YTD is not from the exact current filing edition")
            result = replace(
                result, period_end=end,
                input_hashes=tuple(trailing_input_hash(e) for e in selected),
                evidence_ids=tuple(e.evidence_id for e in selected if e.evidence_id),
                trust_levels=tuple(sorted({e.fact.trust_level.value for e in selected})),
                availability_precisions=tuple(sorted({e.fact.availability_precision.value
                                                      for e in selected})),
            )
            if annual is None or (annual is not current and prior is None):
                missing = tuple(label for label, entry in (("previous full year", annual),
                                                          ("same-filing prior YTD", prior))
                                if entry is None)
                results.append(replace(result, status=TrailingStatus.MISSING,
                                       reasons=("Missing " + ", ".join(missing),)))
                continue
            availability = max(e.fact.available_at.astimezone(UTC) for e in selected)
            if annual is current:
                result = replace(result, status=TrailingStatus.ANNUAL, value=current.fact.value,
                                 period_start=current.fact.period_start, available_at=availability,
                                 reasons=("Reported full-year observation; no bridge synthesized",))
            else:
                matching = [r for r in reviews if r.metric == metric and (
                    r.current_input_hash, r.annual_input_hash, r.prior_input_hash)
                    == result.input_hashes]
                if not matching:
                    results.append(replace(result, status=TrailingStatus.REVIEW_REQUIRED,
                                           reasons=("Exact three-input edition review missing",)))
                    continue
                if len(matching) != 1:
                    raise ValueError("Ambiguous edition reviews")
                review = matching[0]
                reviewed = review.reviewed_at.astimezone(UTC)
                if not availability <= reviewed <= cutoff:
                    raise ValueError("Edition review predates an input or follows cutoff")
                assert prior is not None
                with localcontext() as context:
                    context.prec = 1000
                    context.Emax, context.Emin = 999999, -999999
                    value = annual.fact.value + current.fact.value - prior.fact.value
                result = replace(
                    result, status=TrailingStatus.DERIVED, value=value,
                    period_start=prior_end + timedelta(days=1), available_at=reviewed,
                    review_hash=review.review_hash, review_limitations=review.limitations,
                    reasons=("Exact reviewed as-reported FY + YTD - prior YTD arithmetic only",),
                )
            results.append(result)
        except (ValueError, ArithmeticError) as error:
            results.append(replace(result, status=TrailingStatus.INCOMPATIBLE, value=None,
                                   reasons=(str(error),)))
    return tuple(results)
