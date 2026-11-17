"""Opt-in daily display recomputation, not source or strategy qualification."""

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.global_price_inputs import GlobalPriceInputs
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.domain.enums import AssetType
from tong_quant.domain.models import require_timezone
from tong_quant.research.technical.diagnostics import technical_diagnostics
from tong_quant.research.technical.indicators import TechnicalParameters
from tong_quant.version import TECHNICAL_DISPLAY_BINDING_VERSION


def _hash(value: object) -> str:
    return sha256(financial_input_json(value).encode()).hexdigest()


def build_technical_binding(
    snapshot: GlobalPriceInputs, parameters: TechnicalParameters,
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute against original rows; copied hashes alone cannot satisfy this check."""
    if (not isinstance(snapshot, GlobalPriceInputs)
            or not isinstance(parameters, TechnicalParameters)):
        raise ValueError("technical binding requires original snapshot and parameters")
    require_timezone(snapshot.as_of, "technical binding cutoff")
    validate_yahoo_equity_subject(snapshot.market, snapshot.subject)
    reject_sensitive_structure(document)
    if len(financial_input_json(dict(document)).encode()) > 2 * 1024 * 1024:
        raise ValueError("technical binding exceeds display bound")
    if (document.get("research_only") is not True
            or document.get("research_report_created") is not False
            or document.get("readiness_promoted") is not False
            or any(key in document and document[key] is not False for key in (
                "execution_authorized", "validation_authorized", "investment_scoring_authorized",
                "historical_replay_eligible", "financial_scoring_authorized"))):
        raise ValueError("technical binding requires unqualified research diagnostics")
    inputs, diagnostics = document.get("inputs"), document.get("diagnostics")
    if not isinstance(inputs, Mapping) or not isinstance(diagnostics, Mapping):
        raise ValueError("technical binding requires price and diagnostic mappings")
    if any((bar.instrument.symbol, bar.instrument.market, bar.instrument.asset_type) != (
        snapshot.subject, snapshot.market, AssetType.EQUITY) for bar in snapshot.bars):
        raise ValueError("technical binding original bar identity mismatch")
    if (snapshot.status == "observed_unqualified") != bool(snapshot.bars):
        raise ValueError("technical binding snapshot status and rows disagree")
    original = snapshot.document()
    body = {key: value for key, value in inputs.items() if key != "input_hash"}
    if _hash(body) != inputs.get("input_hash"):
        raise ValueError("technical binding price receipt hash mismatch")
    # Only the analysis cutoff may use an equivalent timezone label. Original Bar
    # serialization stays exact; normalizing it would change retained source identity.
    supplied_cutoff = body.get("as_of")
    if isinstance(supplied_cutoff, str):
        supplied_cutoff = datetime.fromisoformat(supplied_cutoff)
    if not isinstance(supplied_cutoff, datetime):
        raise ValueError("technical binding requires aware price cutoff")
    require_timezone(supplied_cutoff, "technical binding price cutoff")
    cutoff = snapshot.as_of.astimezone(UTC)
    if supplied_cutoff.astimezone(UTC) != cutoff:
        raise ValueError("technical binding price cutoff mismatch")
    normalized = {**body, "as_of": cutoff}
    expected = {key: value for key, value in original.items() if key != "input_hash"}
    expected["as_of"] = cutoff
    if financial_input_json(normalized) != financial_input_json(expected):
        raise ValueError("technical binding price snapshot mismatch")
    recomputed = technical_diagnostics(snapshot.bars, parameters, as_of=cutoff)
    if financial_input_json(dict(diagnostics)) != financial_input_json(recomputed):
        raise ValueError("technical binding diagnostic recomputation mismatch")
    receipt = {
        "model_version": TECHNICAL_DISPLAY_BINDING_VERSION,
        "subject": snapshot.subject, "market": snapshot.market.value,
        "as_of": cutoff.isoformat(), "price_input_hash": inputs["input_hash"],
        "source_bars_content_hash": original["bars_content_hash"],
        "supplied_daily_row_count": len(snapshot.bars),
        "parameters_json": financial_input_json(asdict(parameters)),
        "technical_calculations_version": recomputed["technical_calculations_version"],
        "technical_input_hash": recomputed["technical_input_hash"],
        "diagnostics_content_hash": _hash(dict(diagnostics)),
        "technical_input_status": recomputed["technical_input_status"],
        "snapshot_status": snapshot.status,
        "research_only": True, "source_qualified": False, "pit_qualified": False,
        "scoring_authorized": False, "validation_authorized": False,
        "historical_replay_eligible": False, "holding_management_authorized": False,
        "execution_authorized": False,
    }
    return {**receipt, "binding_hash": _hash(receipt)}


def verify_technical_binding(
    document: Mapping[str, Any], snapshot: GlobalPriceInputs,
    parameters: TechnicalParameters,
) -> dict[str, Any]:
    """Read-side recomputation also rejects rehashed but inconsistent caller receipts."""
    expected = build_technical_binding(snapshot, parameters, document)
    supplied = document.get("technical_binding")
    if not isinstance(supplied, Mapping) or financial_input_json(dict(supplied)) != (
        financial_input_json(expected)
    ):
        raise ValueError("technical display binding mismatch")
    return expected
