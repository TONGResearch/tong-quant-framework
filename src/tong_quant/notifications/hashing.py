import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from tong_quant.portfolio.models import PortfolioProposal
from tong_quant.research.models import ResearchReport
from tong_quant.risk.models import RiskAssessment
from tong_quant.validation.models import ValidationReport

type SupportedArtifact = ResearchReport | ValidationReport | PortfolioProposal | RiskAssessment


def artifact_hash(artifact: SupportedArtifact) -> str:
    payload = json.dumps(
        asdict(artifact),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def notification_dedup_key(
    artifact_hash_value: str,
    channel: str,
    recipient: str,
) -> str:
    payload = f"{artifact_hash_value}:{channel}:{recipient}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return str(value.value)
    raise TypeError(f"unsupported notification hash value: {type(value).__name__}")


__all__ = ["SupportedArtifact", "artifact_hash", "notification_dedup_key"]
