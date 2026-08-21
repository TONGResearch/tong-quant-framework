import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from tong_quant.core.exceptions import DataProviderUnavailableError
from tong_quant.data.calibration.base import ProviderCalibrationRepository
from tong_quant.data.calibration.engine import ProviderCalibrationEngine
from tong_quant.data.calibration.models import (
    CalibrationRecord,
    ProviderCalibrationAttempt,
    ProviderCalibrationAttemptStatus,
    ProviderCalibrationOutcome,
    ProviderCalibrationResult,
    ProviderCalibrationSnapshot,
)
from tong_quant.data.providers.contracts import (
    ProviderDatasetRequest,
    ProviderEvidenceAdapter,
)
from tong_quant.data.providers.yahoo import (
    YAHOO_DAILY_BARS_DATASET,
    YahooFinanceEvidenceAdapter,
)
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import DAILY_BAR_CALIBRATION_VERSION

DAILY_BAR_COMPARISON_FIELDS = (
    "instrument_id",
    "session_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "corporate_actions",
    "price_basis",
)


class DailyBarPriceBasis(StrEnum):
    UNADJUSTED = "unadjusted"
    ADJUSTED = "adjusted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DailyBarCalibrationQuery:
    market: Market
    subject: str
    start_date: date
    end_date: date
    as_of: datetime

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "daily bar calibration as_of")
        if not self.subject.strip():
            raise ValueError("daily bar calibration subject is required")
        if self.end_date < self.start_date:
            raise ValueError("daily bar calibration end date cannot precede start date")


@dataclass(frozen=True, slots=True)
class DailyBarCalibrationSnapshot:
    provider: str
    market: Market
    subject: str
    as_of: datetime
    price_basis: DailyBarPriceBasis
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision
    records: tuple[CalibrationRecord, ...]
    input_hash: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "daily bar calibration snapshot as_of")
        if not self.provider.strip() or not self.subject.strip():
            raise ValueError("daily bar calibration snapshot identity is required")
        if len(self.input_hash) != 64:
            raise ValueError("daily bar calibration input hash must be SHA-256")
        keys = tuple(record.key for record in self.records)
        if len(keys) != len(set(keys)):
            raise ValueError("daily bar calibration sessions must be unique")

    def provider_snapshot(self) -> ProviderCalibrationSnapshot:
        return ProviderCalibrationSnapshot(
            provider=self.provider,
            dataset=YAHOO_DAILY_BARS_DATASET,
            as_of=self.as_of,
            records=self.records,
            limitations=self.limitations,
        )


class DailyBarCalibrationSource(Protocol):
    provider_id: str
    price_basis: DailyBarPriceBasis
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision

    def load(self, query: DailyBarCalibrationQuery) -> DailyBarCalibrationSnapshot: ...


class DailyBarSourceUnavailable(RuntimeError):
    def __init__(self, provider_id: str, reason_code: str) -> None:
        super().__init__(reason_code)
        self.provider_id = provider_id
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class UnavailableDailyBarCalibrationSource:
    provider_id: str
    reason_code: str
    price_basis: DailyBarPriceBasis = DailyBarPriceBasis.UNKNOWN
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN

    def load(self, query: DailyBarCalibrationQuery) -> DailyBarCalibrationSnapshot:
        del query
        raise DailyBarSourceUnavailable(self.provider_id, self.reason_code)


@dataclass(frozen=True, slots=True)
class FixtureDailyBarCalibrationSource:
    payload: dict[str, object]
    fixture_hash: str

    @classmethod
    def from_path(cls, path: Path) -> "FixtureDailyBarCalibrationSource":
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("daily bar fixture must contain a JSON object")
        return cls(payload=payload, fixture_hash=sha256(raw).hexdigest())

    @property
    def provider_id(self) -> str:
        return _required_text(self.payload, "provider")

    @property
    def price_basis(self) -> DailyBarPriceBasis:
        return DailyBarPriceBasis(_required_text(self.payload, "price_basis"))

    @property
    def trust_level(self) -> DataTrustLevel:
        return DataTrustLevel(_required_text(self.payload, "trust_level"))

    @property
    def availability_precision(self) -> AvailabilityPrecision:
        return AvailabilityPrecision(
            _required_text(self.payload, "availability_precision")
        )

    def load(self, query: DailyBarCalibrationQuery) -> DailyBarCalibrationSnapshot:
        if self.trust_level not in {DataTrustLevel.LOW, DataTrustLevel.UNKNOWN}:
            raise ValueError("offline fixtures cannot claim elevated provider trust")
        if self.availability_precision not in {
            AvailabilityPrecision.RETRIEVAL_TIME,
            AvailabilityPrecision.UNKNOWN,
        }:
            raise ValueError("offline fixtures cannot claim historical PIT precision")
        if Market(_required_text(self.payload, "market")) is not query.market:
            raise ValueError("daily bar fixture market does not match its query")
        if _required_text(self.payload, "subject") != query.subject:
            raise ValueError("daily bar fixture subject does not match its query")
        raw_rows = self.payload.get("bars")
        if not isinstance(raw_rows, list) or any(
            not isinstance(item, dict) for item in raw_rows
        ):
            raise ValueError("daily bar fixture bars must be JSON objects")
        rows = tuple(
            item
            for item in raw_rows
            if query.start_date
            <= date.fromisoformat(_required_text(item, "session_date"))
            <= query.end_date
        )
        raw_limitations = self.payload.get("limitations", [])
        if not isinstance(raw_limitations, list) or any(
            not isinstance(item, str) for item in raw_limitations
        ):
            raise ValueError("daily bar fixture limitations must be strings")
        return build_daily_bar_snapshot(
            provider=self.provider_id,
            market=query.market,
            subject=query.subject,
            as_of=query.as_of,
            price_basis=self.price_basis,
            trust_level=self.trust_level,
            availability_precision=self.availability_precision,
            rows=rows,
            limitations=(
                *tuple(raw_limitations),
                "Offline fixture verifies the contract, not real provider accuracy",
            ),
            upstream_hashes=(self.fixture_hash,),
        )


@dataclass(frozen=True, slots=True)
class YahooDailyBarCalibrationSource:
    adapter: YahooFinanceEvidenceAdapter
    provider_id: str = "yahoo_finance"
    price_basis: DailyBarPriceBasis = DailyBarPriceBasis.UNADJUSTED
    trust_level: DataTrustLevel = DataTrustLevel.LOW
    availability_precision: AvailabilityPrecision = (
        AvailabilityPrecision.RETRIEVAL_TIME
    )

    def load(self, query: DailyBarCalibrationQuery) -> DailyBarCalibrationSnapshot:
        return _load_evidence_snapshot(
            adapter=self.adapter,
            query=query,
            price_basis=self.price_basis,
            trust_level=self.trust_level,
            availability_precision=self.availability_precision,
        )


@dataclass(frozen=True, slots=True)
class EvidenceDailyBarCalibrationSource:
    adapter: ProviderEvidenceAdapter
    price_basis: DailyBarPriceBasis
    trust_level: DataTrustLevel
    availability_precision: AvailabilityPrecision

    @property
    def provider_id(self) -> str:
        return self.adapter.provider_id

    def load(self, query: DailyBarCalibrationQuery) -> DailyBarCalibrationSnapshot:
        return _load_evidence_snapshot(
            adapter=self.adapter,
            query=query,
            price_basis=self.price_basis,
            trust_level=self.trust_level,
            availability_precision=self.availability_precision,
        )


def _load_evidence_snapshot(
    *,
    adapter: ProviderEvidenceAdapter,
    query: DailyBarCalibrationQuery,
    price_basis: DailyBarPriceBasis,
    trust_level: DataTrustLevel,
    availability_precision: AvailabilityPrecision,
) -> DailyBarCalibrationSnapshot:
    try:
        batch = adapter.fetch(
            ProviderDatasetRequest(
                dataset=YAHOO_DAILY_BARS_DATASET,
                market=query.market,
                subject=query.subject,
                as_of=query.as_of,
                parameters={
                    "start_date": query.start_date.isoformat(),
                    "end_date": query.end_date.isoformat(),
                },
            )
        )
    except DataProviderUnavailableError as error:
        raise DailyBarSourceUnavailable(error.provider, error.reason_code) from error
    if (
        batch.provider != adapter.provider_id
        or batch.dataset != YAHOO_DAILY_BARS_DATASET
        or batch.market is not query.market
    ):
        raise ValueError("daily bar evidence batch identity is inconsistent")
    if any(record.available_at > batch.retrieved_at for record in batch.records):
        raise ValueError("daily bar calibration contains future evidence")
    rows = tuple(
        {
            "session_date": record.payload.get("session_date"),
            "open": record.payload.get("open"),
            "high": record.payload.get("high"),
            "low": record.payload.get("low"),
            "close": record.payload.get("close"),
            "volume": record.payload.get("volume"),
            "corporate_actions": record.payload.get("corporate_actions", ()),
        }
        for record in batch.records
    )
    return build_daily_bar_snapshot(
        provider=adapter.provider_id,
        market=query.market,
        subject=query.subject,
        as_of=batch.retrieved_at,
        price_basis=price_basis,
        trust_level=trust_level,
        availability_precision=availability_precision,
        rows=rows,
        limitations=tuple(item.description for item in batch.limitations),
        upstream_hashes=(batch.raw_data_hash,),
    )


@dataclass(frozen=True, slots=True)
class DailyBarCalibrationCoordinator:
    repository: ProviderCalibrationRepository
    engine: ProviderCalibrationEngine = ProviderCalibrationEngine()

    def run(
        self,
        primary: DailyBarCalibrationSource,
        secondary: DailyBarCalibrationSource,
        query: DailyBarCalibrationQuery,
    ) -> ProviderCalibrationOutcome:
        primary_snapshot: DailyBarCalibrationSnapshot | None = None
        secondary_snapshot: DailyBarCalibrationSnapshot | None = None
        try:
            primary_snapshot = primary.load(query)
            secondary_snapshot = secondary.load(query)
        except DailyBarSourceUnavailable as error:
            attempt = _attempt(
                primary=primary,
                secondary=secondary,
                query=query,
                status=ProviderCalibrationAttemptStatus.UNAVAILABLE,
                primary_snapshot=primary_snapshot,
                secondary_snapshot=secondary_snapshot,
                unavailable_provider=error.provider_id,
                reason_code=error.reason_code,
                report_id=None,
                limitations=(
                    "Unavailable provider evidence is not treated as agreement or coverage",
                ),
            )
            outcome = ProviderCalibrationOutcome(attempt=attempt, result=None)
            self.repository.save_provider_calibration_outcome(outcome)
            return outcome

        empty_provider = next(
            (
                snapshot.provider
                for snapshot in (primary_snapshot, secondary_snapshot)
                if not snapshot.records
            ),
            "",
        )
        if empty_provider:
            attempt = _attempt(
                primary=primary,
                secondary=secondary,
                query=query,
                status=ProviderCalibrationAttemptStatus.UNAVAILABLE,
                primary_snapshot=primary_snapshot,
                secondary_snapshot=secondary_snapshot,
                unavailable_provider=empty_provider,
                reason_code="no_comparable_records",
                report_id=None,
                limitations=(
                    "An empty provider snapshot is unavailable evidence, not agreement",
                ),
            )
            outcome = ProviderCalibrationOutcome(attempt=attempt, result=None)
            self.repository.save_provider_calibration_outcome(outcome)
            return outcome

        if (
            primary_snapshot.price_basis is not secondary_snapshot.price_basis
            or primary_snapshot.price_basis is not DailyBarPriceBasis.UNADJUSTED
        ):
            attempt = _attempt(
                primary=primary,
                secondary=secondary,
                query=query,
                status=ProviderCalibrationAttemptStatus.INCOMPATIBLE,
                primary_snapshot=primary_snapshot,
                secondary_snapshot=secondary_snapshot,
                unavailable_provider="",
                reason_code="price_basis_mismatch",
                report_id=None,
                limitations=(
                    "Adjusted and unadjusted daily bars cannot be compared as equivalent",
                ),
            )
            outcome = ProviderCalibrationOutcome(attempt=attempt, result=None)
            self.repository.save_provider_calibration_outcome(outcome)
            return outcome

        left = primary_snapshot.provider_snapshot()
        right = secondary_snapshot.provider_snapshot()
        compared_at = max(primary_snapshot.as_of, secondary_snapshot.as_of)
        trust_ceiling = _weakest_trust(
            primary_snapshot.trust_level,
            secondary_snapshot.trust_level,
        )
        report = self.engine.compare(
            left,
            right,
            fields=DAILY_BAR_COMPARISON_FIELDS,
            compared_at=compared_at,
            trust_ceiling=trust_ceiling,
        )
        conflicts = self.engine.detect_conflicts(
            left,
            right,
            report,
            fields=DAILY_BAR_COMPARISON_FIELDS,
        )
        confidence = self.engine.assess_confidence(
            report,
            conflicts,
            temporal_alignment_score=(
                100
                if abs(
                    (primary_snapshot.as_of - secondary_snapshot.as_of).total_seconds()
                )
                <= 300
                else 50
            ),
        )
        result = ProviderCalibrationResult(report, conflicts, confidence)
        attempt = _attempt(
            primary=primary,
            secondary=secondary,
            query=query,
            status=ProviderCalibrationAttemptStatus.COMPLETED,
            primary_snapshot=primary_snapshot,
            secondary_snapshot=secondary_snapshot,
            unavailable_provider="",
            reason_code="",
            report_id=report.report_id,
            limitations=(
                "Cross-provider agreement does not promote provider trust or PIT readiness",
            ),
        )
        outcome = ProviderCalibrationOutcome(attempt=attempt, result=result)
        self.repository.save_provider_calibration_outcome(outcome)
        return outcome


def build_daily_bar_snapshot(
    *,
    provider: str,
    market: Market,
    subject: str,
    as_of: datetime,
    price_basis: DailyBarPriceBasis,
    trust_level: DataTrustLevel,
    availability_precision: AvailabilityPrecision,
    rows: tuple[dict[str, object], ...],
    limitations: tuple[str, ...],
    upstream_hashes: tuple[str, ...] = (),
) -> DailyBarCalibrationSnapshot:
    require_timezone(as_of, "daily bar snapshot as_of")
    records: list[CalibrationRecord] = []
    for row in rows:
        session = date.fromisoformat(_required_text(row, "session_date"))
        if session > as_of.date():
            raise ValueError("daily bar fixture contains a future session")
        open_price = _decimal(row.get("open"), "open")
        high_price = _decimal(row.get("high"), "high")
        low_price = _decimal(row.get("low"), "low")
        close_price = _decimal(row.get("close"), "close")
        volume = _decimal(row.get("volume"), "volume")
        if min(open_price, high_price, low_price, close_price) <= 0:
            raise ValueError("daily bar OHLC values must be positive")
        if high_price < max(open_price, low_price, close_price):
            raise ValueError("daily bar high is below another OHLC value")
        if low_price > min(open_price, high_price, close_price):
            raise ValueError("daily bar low is above another OHLC value")
        if volume < 0:
            raise ValueError("daily bar volume cannot be negative")
        actions = _actions(row.get("corporate_actions", ()))
        session_text = session.isoformat()
        records.append(
            CalibrationRecord(
                key=f"{market.value}:{subject}:{session_text}",
                fields={
                    "instrument_id": f"{market.value}:{subject}",
                    "session_date": session_text,
                    "open": _decimal_text(open_price),
                    "high": _decimal_text(high_price),
                    "low": _decimal_text(low_price),
                    "close": _decimal_text(close_price),
                    "volume": _decimal_text(volume),
                    "corporate_actions": ",".join(actions),
                    "price_basis": price_basis.value,
                },
            )
        )
    records.sort(key=lambda item: item.key)
    document = {
        "provider": provider,
        "market": market.value,
        "subject": subject,
        "as_of": as_of.isoformat(),
        "price_basis": price_basis.value,
        "trust_level": trust_level.value,
        "availability_precision": availability_precision.value,
        "records": [
            {"key": record.key, "fields": record.fields} for record in records
        ],
        "upstream_hashes": upstream_hashes,
        "model_version": DAILY_BAR_CALIBRATION_VERSION,
    }
    input_hash = sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return DailyBarCalibrationSnapshot(
        provider=provider,
        market=market,
        subject=subject,
        as_of=as_of,
        price_basis=price_basis,
        trust_level=trust_level,
        availability_precision=availability_precision,
        records=tuple(records),
        input_hash=input_hash,
        limitations=tuple(dict.fromkeys(limitations)),
    )


def _attempt(
    *,
    primary: DailyBarCalibrationSource,
    secondary: DailyBarCalibrationSource,
    query: DailyBarCalibrationQuery,
    status: ProviderCalibrationAttemptStatus,
    primary_snapshot: DailyBarCalibrationSnapshot | None,
    secondary_snapshot: DailyBarCalibrationSnapshot | None,
    unavailable_provider: str,
    reason_code: str,
    report_id: str | None,
    limitations: tuple[str, ...],
) -> ProviderCalibrationAttempt:
    primary_hash = "" if primary_snapshot is None else primary_snapshot.input_hash
    secondary_hash = "" if secondary_snapshot is None else secondary_snapshot.input_hash
    combined_limitations = tuple(
        dict.fromkeys(
            (
                *(primary_snapshot.limitations if primary_snapshot else ()),
                *(secondary_snapshot.limitations if secondary_snapshot else ()),
                *limitations,
            )
        )
    )
    attempt_as_of = max(
        (
            snapshot.as_of
            for snapshot in (primary_snapshot, secondary_snapshot)
            if snapshot is not None
        ),
        default=query.as_of,
    )
    document = {
        "dataset": YAHOO_DAILY_BARS_DATASET,
        "market": query.market.value,
        "subject": query.subject,
        "primary_provider": primary.provider_id,
        "secondary_provider": secondary.provider_id,
        "as_of": attempt_as_of.isoformat(),
        "status": status.value,
        "primary_price_basis": primary.price_basis.value,
        "secondary_price_basis": secondary.price_basis.value,
        "primary_input_hash": primary_hash,
        "secondary_input_hash": secondary_hash,
        "report_id": report_id,
        "unavailable_provider": unavailable_provider,
        "reason_code": reason_code,
        "limitations": combined_limitations,
        "model_version": DAILY_BAR_CALIBRATION_VERSION,
    }
    attempt_id = sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ProviderCalibrationAttempt(
        attempt_id=attempt_id,
        dataset=YAHOO_DAILY_BARS_DATASET,
        market=query.market,
        subject=query.subject,
        primary_provider=primary.provider_id,
        secondary_provider=secondary.provider_id,
        as_of=attempt_as_of,
        status=status,
        primary_price_basis=primary.price_basis.value,
        secondary_price_basis=secondary.price_basis.value,
        primary_trust_level=primary.trust_level,
        secondary_trust_level=secondary.trust_level,
        primary_availability_precision=primary.availability_precision,
        secondary_availability_precision=secondary.availability_precision,
        primary_input_hash=primary_hash,
        secondary_input_hash=secondary_hash,
        report_id=report_id,
        unavailable_provider=unavailable_provider,
        reason_code=reason_code,
        limitations=combined_limitations,
        model_version=DAILY_BAR_CALIBRATION_VERSION,
    )


def _required_text(values: dict[str, object], field: str) -> str:
    value = str(values.get(field, "")).strip()
    if not value:
        raise ValueError(f"daily bar field {field} is required")
    return value


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"daily bar field {field} must be numeric")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"daily bar field {field} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"daily bar field {field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")


def _actions(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ValueError("daily bar corporate actions must be a sequence")
    actions = tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
    return actions


def _weakest_trust(
    left: DataTrustLevel,
    right: DataTrustLevel,
) -> DataTrustLevel:
    strength = {
        DataTrustLevel.UNKNOWN: 0,
        DataTrustLevel.LOW: 1,
        DataTrustLevel.MEDIUM: 2,
        DataTrustLevel.HIGH: 3,
        DataTrustLevel.VERIFIED: 4,
    }
    return left if strength[left] <= strength[right] else right


__all__ = [
    "DAILY_BAR_COMPARISON_FIELDS",
    "DailyBarCalibrationCoordinator",
    "DailyBarCalibrationQuery",
    "DailyBarCalibrationSnapshot",
    "DailyBarCalibrationSource",
    "DailyBarPriceBasis",
    "DailyBarSourceUnavailable",
    "EvidenceDailyBarCalibrationSource",
    "FixtureDailyBarCalibrationSource",
    "UnavailableDailyBarCalibrationSource",
    "YahooDailyBarCalibrationSource",
    "build_daily_bar_snapshot",
]
