"""Current-schema synthetic payloads; fixtures do not establish provider trust."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tong_quant.data.models import RawDataset
from tong_quant.data.normalization import normalize_corporate_actions
from tong_quant.data.normalization.corporate_actions import normalize_corporate_action_batch
from tong_quant.data.quality import validate_raw_dataset
from tong_quant.data.service import MarketDataService
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import (
    AssetType,
    AvailabilityPrecision,
    CorporateActionType,
    DataTrustLevel,
    Market,
)
from tong_quant.domain.models import Instrument

NOW = datetime(2026, 10, 16, tzinfo=UTC)
INSTRUMENT = Instrument(
    "600000", Market.CHINA_A, "Synthetic", available_at=NOW - timedelta(days=10)
)


def row(**changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "除权除息日": "2026-07-16",
        "股权登记日": "2026-07-15",
        "方案进度": "实施分配",
        "现金分红-现金分红比例": "4.20",
        "现金分红-现金分红比例描述": "10派4.20元(含税,扣税后3.78元)",
        "送转股份-送转总比例": None,
        "送转股份-送股比例": None,
        "送转股份-转股比例": None,
    }
    result.update(changes)
    return result


def dataset(*rows: dict[str, object]) -> RawDataset:
    return RawDataset("corporate_actions", pd.DataFrame(rows), NOW, "synthetic", {})


def test_current_schema_cash_is_gross_per_share_and_remains_low_retrieval_trust() -> None:
    raw = dataset(row())
    result = normalize_corporate_action_batch(raw, INSTRUMENT, batch_id="fixture")
    assert result.accepted_rows == result.received == 1
    assert result.rejected_rows == 0 and result.issues == ()
    action = result.actions[0]
    assert action.action_type is CorporateActionType.DIVIDEND
    assert action.cash_amount == Decimal("0.42")
    assert action.effective_date == date(2026, 7, 16)
    assert action.available_at == NOW and action.raw_data_hash == raw.content_hash()
    assert action.trust_level is DataTrustLevel.LOW
    assert action.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME
    assert normalize_corporate_actions(raw, INSTRUMENT, batch_id="fixture") == list(result.actions)


def test_empty_response_is_auditable_but_proves_no_action_coverage() -> None:
    raw = dataset()
    assert validate_raw_dataset(raw).is_valid
    result = normalize_corporate_action_batch(raw, INSTRUMENT, batch_id="fixture")
    assert result.actions == () and result.accepted_rows == result.received == 0


def test_combined_distribution_has_two_events_but_one_accepted_input_row() -> None:
    raw = dataset(
        row(
            **{
                "现金分红-现金分红比例描述": "10送3转增2派4.20元（含税）",
                "送转股份-送转总比例": 5,
                "送转股份-送股比例": 3,
                "送转股份-转股比例": 2,
            }
        )
    )
    result = normalize_corporate_action_batch(raw, INSTRUMENT, batch_id="fixture")
    assert result.accepted_rows == 1 and result.rejected_rows == 0
    assert len(result.actions) == 2
    assert result.actions[0].cash_amount == Decimal("0.42")
    assert result.actions[1].ratio == Decimal("1.5")


@pytest.mark.parametrize(
    "change,code",
    [
        ({"方案进度": "董事会决议通过"}, "not_confirmed_implemented"),
        ({"方案进度": None}, "not_confirmed_implemented"),
        ({"方案进度": pd.NA}, "not_confirmed_implemented"),
        ({"除权除息日": None}, "missing_ex_date"),
        ({"除权除息日": "NaT"}, "invalid_ex_date"),
        ({"除权除息日": "bad date"}, "invalid_ex_date"),
        ({"除权除息日": "07/16/2026"}, "invalid_ex_date"),
        ({"除权除息日": "2026-07-16T12:00:00"}, "invalid_ex_date"),
        ({"除息日": "2026-07-17"}, "conflicting_ex_dates"),
        ({"除权除息日": "2026-11-16"}, "future_effective_date"),
        ({"现金分红-现金分红比例描述": "10派4.20元"}, "gross_tax_basis_missing"),
        ({"现金分红-现金分红比例描述": "10派3.78元(税后)"}, "unsupported_distribution_description"),
        (
            {"现金分红-现金分红比例描述": "10配3派4.20元(含税)"},
            "unsupported_distribution_description",
        ),
        ({"现金分红-现金分红比例描述": "10派4.20派4.20元(含税)"}, "ambiguous_distribution_terms"),
        ({"现金分红-现金分红比例描述": "3派4.20元(含税)"}, "unsupported_share_basis"),
        ({"现金分红-现金分红比例": "3.78"}, "cash_description_conflict"),
        ({"现金分红-现金分红比例": None}, "cash_description_conflict"),
        ({"现金分红-现金分红比例": -1}, "invalid_numeric_value"),
        ({"现金分红-现金分红比例": float("inf")}, "invalid_numeric_value"),
        ({"现金分红-现金分红比例": [4.2]}, "non_scalar_field"),
        ({"送转股份-送转总比例": 5}, "share_description_conflict"),
    ],
)
def test_unsupported_rows_are_visible_rejections_not_guessed_events(
    change: dict[str, object], code: str
) -> None:
    result = normalize_corporate_action_batch(
        dataset(row(**change)), INSTRUMENT, batch_id="fixture"
    )
    assert result.actions == () and result.rejected_rows == 1
    assert result.issues[0].code == code


def test_zero_cash_is_not_missing_and_does_not_create_a_zero_dividend() -> None:
    raw = dataset(
        row(
            **{
                "现金分红-现金分红比例": 0,
                "现金分红-现金分红比例描述": "10转5派0元(含税)",
                "送转股份-送转总比例": 5,
            }
        )
    )
    result = normalize_corporate_action_batch(raw, INSTRUMENT, batch_id="fixture")
    assert len(result.actions) == 1
    assert result.actions[0].ratio == Decimal("1.5")
    missing = row(
        **{
            "现金分红-现金分红比例": None,
            "现金分红-现金分红比例描述": "10转5派0元(含税)",
            "送转股份-送转总比例": 5,
        }
    )
    assert (
        normalize_corporate_action_batch(dataset(missing), INSTRUMENT, batch_id="fixture").actions
        == ()
    )


def test_no_positive_components_and_invalid_net_tax_amount_are_not_events() -> None:
    zero = row(
        **{
            "现金分红-现金分红比例": 0,
            "现金分红-现金分红比例描述": "10派0元(含税)",
        }
    )
    assert (
        normalize_corporate_action_batch(dataset(zero), INSTRUMENT, batch_id="fixture")
        .issues[0]
        .code
        == "no_positive_action"
    )
    bad_net = row(**{"现金分红-现金分红比例描述": "10派4.20元(含税,扣税后5元)"})
    assert (
        normalize_corporate_action_batch(dataset(bad_net), INSTRUMENT, batch_id="fixture")
        .issues[0]
        .code
        == "invalid_tax_amount"
    )


def test_future_instrument_snapshot_cannot_enter_normalized_observation() -> None:
    with pytest.raises(ValueError, match="visible"):
        normalize_corporate_action_batch(
            dataset(row()),
            replace(INSTRUMENT, available_at=NOW + timedelta(seconds=1)),
            batch_id="fixture",
        )


@pytest.mark.parametrize("second_cash", ["4.20", "5.00"])
def test_duplicate_or_conflicting_same_day_events_are_all_rejected(second_cash: str) -> None:
    raw = dataset(
        row(),
        row(
            **{
                "现金分红-现金分红比例": second_cash,
                "现金分红-现金分红比例描述": f"10派{second_cash}元(含税)",
            }
        ),
    )
    result = normalize_corporate_action_batch(raw, INSTRUMENT, batch_id="fixture")
    assert result.actions == () and result.rejected_rows == 2
    assert all(issue.code == "duplicate_or_conflicting_event" for issue in result.issues)


def test_storage_idempotence_conflicts_rollback_and_pit_revision_preservation(
    tmp_path: Path,
) -> None:
    store = SQLiteStore(tmp_path / "actions.sqlite3")
    store.initialize()
    store.upsert_instruments((INSTRUMENT,))
    action = normalize_corporate_action_batch(
        dataset(row()), INSTRUMENT, batch_id="fixture"
    ).actions[0]
    assert store.upsert_corporate_actions((action,)) == 1
    assert store.upsert_corporate_actions((replace(action, cash_amount=Decimal("0.4200")),)) == 0
    other = replace(action, effective_date=date(2026, 7, 17))
    with pytest.raises(ValueError, match="new available_at"):
        store.upsert_corporate_actions((other, replace(action, cash_amount=Decimal("0.5"))))
    assert store.table_count("corporate_actions") == 1
    revision = replace(action, available_at=NOW + timedelta(days=1), cash_amount=Decimal("0.5"))
    assert store.upsert_corporate_actions((revision,)) == 1
    service = MarketDataService(store)

    def visible(as_of: datetime) -> list[Decimal | None]:
        return [
            item.cash_amount
            for item in service.corporate_actions(
                "600000",
                Market.CHINA_A,
                AssetType.EQUITY,
                date(2026, 7, 1),
                date(2026, 7, 31),
                as_of=as_of,
            )
        ]

    assert visible(NOW - timedelta(seconds=1)) == []
    assert visible(NOW) == [Decimal("0.42")]
    assert visible(revision.available_at) == [Decimal("0.42"), Decimal("0.5")]
