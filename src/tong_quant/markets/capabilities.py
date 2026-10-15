"""Dated rule-evidence coverage; completeness does not authorize a simulation."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone

CAPABILITY_CONTRACT_VERSION = "market-rule-capabilities-v1"


class MarketRuleCapability(StrEnum):
    TRADING_CALENDAR = "trading_calendar"
    SETTLEMENT = "settlement"
    QUANTITY = "quantity"
    PRICE_LIMIT = "price_limit"
    SECURITY_STATUS = "security_status"


@dataclass(frozen=True, slots=True)
class MarketRuleScope:
    market: Market
    exchange: str
    board: str
    account_type: str

    def __post_init__(self) -> None:
        if not isinstance(self.market, Market):
            raise ValueError("market-rule scope requires a typed market")
        if any(not value.strip() for value in (self.exchange, self.board, self.account_type)):
            raise ValueError("market-rule scope requires exchange, board, and account type")


@dataclass(frozen=True, slots=True)
class MarketRuleEvidence:
    evidence_id: str
    scope: MarketRuleScope
    capability: MarketRuleCapability
    rule_version: str
    effective_from: date
    effective_to: date | None
    available_at: datetime
    source_reference: str
    content_sha256: str
    trust_level: DataTrustLevel = DataTrustLevel.UNKNOWN
    availability_precision: AvailabilityPrecision = AvailabilityPrecision.UNKNOWN

    def __post_init__(self) -> None:
        require_timezone(self.available_at, "available_at")
        if not isinstance(self.capability, MarketRuleCapability):
            raise ValueError("market-rule evidence requires a typed capability")
        if not isinstance(self.trust_level, DataTrustLevel):
            raise ValueError("market-rule evidence requires a typed trust level")
        if not isinstance(self.availability_precision, AvailabilityPrecision):
            raise ValueError("market-rule evidence requires typed availability precision")
        if any(
            not value.strip()
            for value in (self.evidence_id, self.rule_version, self.source_reference)
        ):
            raise ValueError("market-rule evidence requires identity, version, and source")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("rule effective_to must follow effective_from (exclusive end)")
        if len(self.content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.content_sha256
        ):
            raise ValueError("market-rule evidence requires a lowercase SHA-256 hash")


@dataclass(frozen=True, slots=True)
class MarketRuleQuery:
    scope: MarketRuleScope
    trade_date: date
    as_of: datetime

    def __post_init__(self) -> None:
        require_timezone(self.as_of, "as_of")


class MarketRuleEvidenceReader(Protocol):
    def evidence_for(self, scope: MarketRuleScope) -> tuple[MarketRuleEvidence, ...]: ...


@dataclass(frozen=True, slots=True)
class MarketRuleEvidenceCatalog:
    records: tuple[MarketRuleEvidence, ...] = ()

    def __post_init__(self) -> None:
        if len({record.evidence_id for record in self.records}) != len(self.records):
            raise ValueError("market-rule evidence identities must be unique")

    def evidence_for(self, scope: MarketRuleScope) -> tuple[MarketRuleEvidence, ...]:
        return tuple(record for record in self.records if record.scope == scope)


@dataclass(frozen=True, slots=True)
class MarketRuleCoverage:
    query: MarketRuleQuery
    selected_evidence: tuple[MarketRuleEvidence, ...]
    missing_capabilities: tuple[MarketRuleCapability, ...]
    ambiguous_capabilities: tuple[MarketRuleCapability, ...]
    warnings: tuple[str, ...]
    evidence_hash: str
    contract_version: str = CAPABILITY_CONTRACT_VERSION

    @property
    def complete(self) -> bool:
        return not self.missing_capabilities and not self.ambiguous_capabilities


@dataclass(frozen=True, slots=True)
class MarketRuleCoverageInspector:
    reader: MarketRuleEvidenceReader

    def inspect(self, query: MarketRuleQuery) -> MarketRuleCoverage:
        records = self.reader.evidence_for(query.scope)
        matches: dict[MarketRuleCapability, list[MarketRuleEvidence]] = {
            capability: [] for capability in MarketRuleCapability
        }
        warnings: list[str] = []
        for record in records:
            reason = ""
            if record.scope != query.scope:
                reason = "scope_mismatch"
            elif record.available_at > query.as_of:
                reason = "not_yet_available"
            elif record.effective_from > query.trade_date or (
                record.effective_to is not None and query.trade_date >= record.effective_to
            ):
                reason = "not_effective"
            elif record.trust_level not in {DataTrustLevel.HIGH, DataTrustLevel.VERIFIED}:
                reason = "insufficient_trust"
            elif record.availability_precision not in {
                AvailabilityPrecision.EXACT, AvailabilityPrecision.RETRIEVAL_TIME,
            }:
                reason = "availability_imprecise"
            if reason:
                warnings.append(f"{record.evidence_id}:{reason}")
            else:
                matches[record.capability].append(record)
                if record.availability_precision is AvailabilityPrecision.RETRIEVAL_TIME:
                    warnings.append(f"{record.evidence_id}:retrieval_time_only")

        selected = tuple(
            values[0] for _, values in sorted(matches.items()) if len(values) == 1
        )
        missing = tuple(sorted(capability for capability, values in matches.items() if not values))
        ambiguous = tuple(
            sorted(capability for capability, values in matches.items() if len(values) > 1)
        )
        warnings.extend(f"ambiguous:{capability.value}" for capability in ambiguous)
        warnings.append("Coverage metadata only; dated rule evaluators remain required")
        payload = {
            "contract_version": CAPABILITY_CONTRACT_VERSION,
            "query": asdict(query),
            "records": sorted(
                (asdict(record) for record in records),
                key=lambda item: json.dumps(item, default=str, sort_keys=True),
            ),
        }
        digest = hashlib.sha256(
            json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return MarketRuleCoverage(
            query=query, selected_evidence=selected, missing_capabilities=missing,
            ambiguous_capabilities=ambiguous, warnings=tuple(sorted(set(warnings))),
            evidence_hash=digest,
        )


__all__ = [
    "MarketRuleCapability", "MarketRuleCoverage", "MarketRuleCoverageInspector",
    "MarketRuleEvidence", "MarketRuleEvidenceCatalog", "MarketRuleEvidenceReader",
    "MarketRuleQuery", "MarketRuleScope",
]
