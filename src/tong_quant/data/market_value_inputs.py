"""Provider-neutral read contract: observations and source binding, never valuation authority."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.contracts import ProviderEvidenceRecord
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import MARKET_VALUE_INPUT_VERSION


def market_value_record_hash(record: ProviderEvidenceRecord) -> str:
    return sha256(financial_input_json(asdict(record)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class MarketValueInspection:
    record: ProviderEvidenceRecord
    source_bound: bool
    reasons: tuple[str, ...]
    record_hash: str


@dataclass(frozen=True, slots=True)
class MarketValueInputSnapshot:
    symbol: str
    market: Market
    as_of: datetime
    inspections: tuple[MarketValueInspection, ...]
    model_version: str = MARKET_VALUE_INPUT_VERSION

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")
        if (not self.symbol or not isinstance(self.market, Market)
                or type(self.inspections) is not tuple
                or self.model_version != MARKET_VALUE_INPUT_VERSION):
            raise ValueError("invalid market-value snapshot")
        for inspection in self.inspections:
            record = inspection.record
            record.__post_init__()
            if ((record.subject, record.market) != (self.symbol, self.market)
                    or max(record.available_at.astimezone(UTC), record.retrieved_at.astimezone(UTC))
                    > self.as_of.astimezone(UTC)
                    or any(timestamp is not None and timestamp.astimezone(UTC) > (
                        self.as_of.astimezone(UTC))
                           for timestamp in (record.published_at, record.observed_at))
                    or type(inspection.source_bound) is not bool
                    or type(inspection.reasons) is not tuple or not inspection.reasons
                    or inspection.record_hash != market_value_record_hash(record)):
                raise ValueError("market-value identity, timing or receipt mismatch")

    @property
    def input_hash(self) -> str:
        self.__post_init__()
        return sha256(financial_input_json(asdict(self)).encode()).hexdigest()

    def document(self) -> dict[str, object]:
        return {**asdict(self), "input_hash": self.input_hash, "valuation_authorized": False,
                "investment_scoring_authorized": False, "historical_replay_eligible": False,
                "limitations": ("Source binding is stored consistency, not independent units, "
                                "share-class, quote-clock, historical or valuation qualification",)}

    def validate_context(self, *, symbol: str, market: Market, as_of: datetime) -> None:
        self.__post_init__()
        require_timezone(as_of, "research cutoff")
        if (symbol != self.symbol or market is not self.market
                or as_of.astimezone(UTC) != self.as_of.astimezone(UTC)):
            raise ValueError("research market-value snapshot does not match subject/cutoff")
