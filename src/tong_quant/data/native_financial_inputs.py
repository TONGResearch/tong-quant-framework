"""Immutable diagnostic input to official research, never admitted financial facts."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_fundamental_inputs import read_global_fundamental_inputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION

_SECTORS = frozenset({"nonfinancial", "bank", "securities", "insurance", "unknown"})
_DENIED = ("financial_scoring_authorized", "investment_scoring_authorized",
           "historical_replay_eligible", "validation_authorized", "execution_authorized",
           "accounting_definitions_admitted", "research_report_created")


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("native financial input requires explicit timestamps")
    parsed = datetime.fromisoformat(value)
    require_timezone(parsed, "native financial input timestamp")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class NativeFinancialResearchInput:
    """A copied reader receipt plus an unverified requested sector, not authentication.

    Production callers use the reader factory below. Even a fabricated receipt
    with a recomputed public checksum cannot grant scoring or validation authority.
    """

    receipt_json: str
    sector_profile: str

    def __post_init__(self) -> None:
        self.validate_context()

    def document(self) -> dict[str, Any]:
        if not isinstance(self.receipt_json, str) or len(self.receipt_json.encode()) > 2_097_152:
            raise ValueError("native financial receipt outside supported bounds")
        document = json.loads(self.receipt_json)
        if not isinstance(document, dict):
            raise ValueError("native financial receipt must be an object")
        return document

    @property
    def as_of(self) -> datetime:
        return _utc(self.document().get("as_of"))

    def validate_context(self, *, symbol: str | None = None, market: Market | None = None,
                         as_of: datetime | None = None) -> None:
        document = self.document()
        reject_sensitive_structure(document, path="native_financial_research_input")
        body = {key: value for key, value in document.items() if key != "input_hash"}
        if (self.sector_profile not in _SECTORS
                or self.receipt_json != financial_input_json(document)
                or document.get("model_version") != GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION
                or sha256(financial_input_json(body).encode()).hexdigest()
                != document.get("input_hash")
                or document.get("trust_ceiling") != "LOW"
                or document.get("availability_precision") != "retrieval_time"
                or any(document.get(name) is not False for name in _DENIED)):
            raise ValueError("native financial receipt integrity or authority mismatch")
        receipt_market = Market(document["market"])
        validate_yahoo_equity_subject(receipt_market, document["subject"])
        cutoff = self.as_of
        if as_of is not None:
            require_timezone(as_of, "native financial context cutoff")
        if ((symbol is not None and document["subject"] != symbol)
                or (market is not None and receipt_market is not market)
                or (as_of is not None and cutoff != as_of.astimezone(UTC))):
            raise ValueError("native financial research context mismatch")
        for name in ("captures", "observations"):
            rows = document.get(name)
            if not isinstance(rows, list) or len(rows) > 10_000:
                raise ValueError("native financial receipt rows outside supported bounds")
            if any(not isinstance(row, dict) or _utc(row.get("available_at")) > cutoff
                   for row in rows):
                raise ValueError("native financial receipt contains future data")


def read_native_financial_research_input(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, subject: str, market: Market,
    *, as_of: datetime, sector_profile: str,
) -> NativeFinancialResearchInput:
    """Reuse the byte/registry/batch-verified reader without admitting its contents."""
    receipt = read_global_fundamental_inputs(store, artifacts, subject, market, as_of=as_of)
    return NativeFinancialResearchInput(financial_input_json(receipt), sector_profile)
