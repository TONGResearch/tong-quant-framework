"""Conservative AKShare distribution observations, never adjustment factors."""

import re
from collections import Counter
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from tong_quant.data.models import RawDataset
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    CorporateActionType,
    DataTrustLevel,
    InstrumentCategory,
    Market,
)
from tong_quant.domain.models import CorporateAction, Instrument
from tong_quant.version import AKSHARE_CORPORATE_ACTION_VERSION

_NUMBER = r"[0-9]{1,12}(?:\.[0-9]{1,8})?"
_DESCRIPTION = re.compile(
    rf"(?P<base>[0-9]{{1,4}})(?P<terms>(?:(?:送|转增|转|派){_NUMBER})+)元?"
    rf"(?P<tax>\(含税(?:,扣税后(?P<net>{_NUMBER})元)?\))?"
)
_TERM = re.compile(rf"(送|转增|转|派)({_NUMBER})")
_SHARE_COLUMNS = ("送转股份-送转总比例", "送转股份-送股比例", "送转股份-转股比例")
_DATE_LABEL = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ]00:00:00(?:\.0+)?Z?)?")


@dataclass(frozen=True, slots=True)
class CorporateActionRowIssue:
    row: int
    code: str


@dataclass(frozen=True, slots=True)
class CorporateActionNormalization:
    actions: tuple[CorporateAction, ...]
    received: int
    accepted_rows: int
    issues: tuple[CorporateActionRowIssue, ...]
    model_version: str = AKSHARE_CORPORATE_ACTION_VERSION

    @property
    def rejected_rows(self) -> int:
        return self.received - self.accepted_rows


class _RejectedRow(ValueError):
    pass


def _missing(value: Any) -> bool:
    if not pd.api.types.is_scalar(value):
        raise _RejectedRow("non_scalar_field")
    try:
        return value is None or bool(pd.isna(value))
    except (ValueError, TypeError):
        raise _RejectedRow("non_scalar_field") from None


def _number(value: object) -> Decimal | None:
    if _missing(value):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise _RejectedRow("invalid_numeric_value") from None
    if not number.is_finite() or not 0 <= number <= Decimal("1e12"):
        raise _RejectedRow("invalid_numeric_value")
    return number


def _ex_date(row: Mapping[Hashable, object]) -> date:
    dates: list[date] = []
    for name in ("除权除息日", "除息日"):
        value = row.get(name)
        if _missing(value):
            continue
        if not isinstance(value, (str, date, datetime)):
            raise _RejectedRow("invalid_ex_date")
        if isinstance(value, str) and _DATE_LABEL.fullmatch(value.strip()) is None:
            raise _RejectedRow("invalid_ex_date")
        try:
            parsed = pd.Timestamp(value)
            if pd.isna(parsed) or any(
                (parsed.hour, parsed.minute, parsed.second, parsed.microsecond)
            ):
                raise _RejectedRow("invalid_ex_date")
            dates.append(parsed.date())
        except (ValueError, TypeError):
            raise _RejectedRow("invalid_ex_date") from None
    if not dates:
        raise _RejectedRow("missing_ex_date")
    if len(set(dates)) != 1:
        raise _RejectedRow("conflicting_ex_dates")
    return dates[0]


def _amounts(row: Mapping[Hashable, object]) -> tuple[Decimal | None, Decimal | None]:
    value = row.get("现金分红-现金分红比例描述")
    if not isinstance(value, str) or len(value) > 256:
        raise _RejectedRow("unsupported_distribution_description")
    text = "".join(value.split()).translate(str.maketrans("（），", "(),"))
    match = _DESCRIPTION.fullmatch(text)
    if match is None:
        raise _RejectedRow("unsupported_distribution_description")
    base = Decimal(match["base"])
    if base not in {Decimal(1), Decimal(10), Decimal(100), Decimal(1000)}:
        raise _RejectedRow("unsupported_share_basis")
    terms: dict[str, Decimal] = {}
    for kind, amount in _TERM.findall(match["terms"]):
        kind = "转" if kind == "转增" else kind
        if kind in terms:
            raise _RejectedRow("ambiguous_distribution_terms")
        terms[kind] = Decimal(amount)
    cash = terms.get("派")
    if cash is not None and match["tax"] is None:
        raise _RejectedRow("gross_tax_basis_missing")
    if cash is not None and match["net"] is not None and Decimal(match["net"]) > cash:
        raise _RejectedRow("invalid_tax_amount")
    cash_column = _number(row.get("现金分红-现金分红比例"))
    if cash is not None and cash_column != cash:
        raise _RejectedRow("cash_description_conflict")
    if cash is None and cash_column not in {None, Decimal(0)}:
        raise _RejectedRow("cash_description_conflict")
    total, gift, transfer = (_number(row.get(name)) for name in _SHARE_COLUMNS)
    described_gift, described_transfer = terms.get("送", Decimal(0)), terms.get("转", Decimal(0))
    shares = described_gift + described_transfer
    if any(
        actual is not None and actual != expected
        for actual, expected in (
            (total, shares),
            (gift, described_gift),
            (transfer, described_transfer),
        )
    ):
        raise _RejectedRow("share_description_conflict")
    if (
        shares > 0
        and total is None
        and ((described_gift > 0 and gift is None) or (described_transfer > 0 and transfer is None))
    ):
        raise _RejectedRow("share_value_not_corroborated")
    # Omitted/missing components do not become explicit zero-action observations.
    return (
        cash / base if cash is not None and cash > 0 else None,
        Decimal(1) + shares / base if shares > 0 else None,
    )


def normalize_corporate_action_batch(
    dataset: RawDataset,
    instrument: Instrument,
    *,
    batch_id: str,
) -> CorporateActionNormalization:
    if (
        instrument.market is not Market.CHINA_A
        or instrument.asset_type is not AssetType.EQUITY
        or instrument.category is not InstrumentCategory.EQUITY
        or instrument.currency != "CNY"
    ):
        raise ValueError("only China A-share CNY equity distributions are supported")
    if instrument.available_at is None or instrument.available_at > dataset.retrieved_at:
        raise ValueError("instrument snapshot must be visible at retrieval time")
    actions: list[CorporateAction] = []
    issues: list[CorporateActionRowIssue] = []
    candidates: list[tuple[int, tuple[CorporateAction, ...]]] = []
    raw_hash = dataset.content_hash()
    for index, row in enumerate(dataset.frame.to_dict(orient="records")):
        try:
            status = row.get("方案进度")
            if not isinstance(status, str) or status.strip() != "实施分配":
                raise _RejectedRow("not_confirmed_implemented")
            effective_date = _ex_date(row)
            if effective_date > dataset.retrieved_at.astimezone(ZoneInfo("Asia/Shanghai")).date():
                raise _RejectedRow("future_effective_date")
            cash, ratio = _amounts(row)
            if cash is None and ratio is None:
                raise _RejectedRow("no_positive_action")
            row_actions: list[CorporateAction] = []
            for kind, cash_amount, share_ratio in (
                (CorporateActionType.DIVIDEND, cash, None),
                (CorporateActionType.SPLIT, None, ratio),
            ):
                if cash_amount is None and share_ratio is None:
                    continue
                row_actions.append(
                    CorporateAction(
                        instrument=instrument,
                        action_type=kind,
                        effective_date=effective_date,
                        available_at=dataset.retrieved_at,
                        source=dataset.source,
                        cash_amount=cash_amount,
                        ratio=share_ratio,
                        currency="CNY" if cash_amount is not None else None,
                        raw_data_hash=raw_hash,
                        batch_id=batch_id,
                        provider_dataset=dataset.dataset,
                        availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
                        trust_level=DataTrustLevel.LOW,
                    )
                )
            candidates.append((index, tuple(row_actions)))
        except _RejectedRow as error:
            issues.append(CorporateActionRowIssue(index, str(error)))
    identities = Counter(
        (action.effective_date, action.action_type)
        for _, candidate_actions in candidates
        for action in candidate_actions
    )
    accepted_rows = 0
    for index, candidate_actions in candidates:
        if any(
            identities[(action.effective_date, action.action_type)] > 1
            for action in candidate_actions
        ):
            issues.append(CorporateActionRowIssue(index, "duplicate_or_conflicting_event"))
            continue
        actions.extend(candidate_actions)
        accepted_rows += 1
    return CorporateActionNormalization(
        tuple(actions),
        len(dataset.frame),
        accepted_rows,
        tuple(sorted(issues, key=lambda item: item.row)),
    )
