"""Capture and verify reviewed configuration references, not market-data ingestion."""

import json
import os
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import requests

from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.providers.contracts import ProviderArtifact
from tong_quant.domain.enums import AvailabilityPrecision, DataTrustLevel, Market
from tong_quant.domain.models import require_timezone
from tong_quant.markets.sse_references import (
    SSE_PROFILE_VERSION,
    ReviewedRuleDocument,
    SSEReferenceBundle,
    evidence_hash,
    require_sha256,
    require_sse_url,
)

MAX_REFERENCE_BYTES = 2 * 1024 * 1024


def _profile(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    raw = tomllib.loads(content.decode("utf-8"))
    raw["_content_sha256"] = sha256(content).hexdigest()
    if raw.get("profile_version") != SSE_PROFILE_VERSION:
        raise ValueError("unsupported reference profile")
    documents = raw.get("documents", [])
    if len(documents) != 3 or {item["role"] for item in documents} != {
        "rules",
        "deferred",
        "odd_lots",
    }:
        raise ValueError("reference profile requires all three reviewed documents")
    for document in documents:
        ReviewedRuleDocument(document["role"], document["source_url"], document["content_sha256"])
        filename = document["file_name"]
        if not filename or filename in {".", ".."} or Path(filename).name != filename:
            raise ValueError("reference filenames must be safe basenames")
    return raw


def _fetch(url: str) -> bytes:
    require_sse_url(url)
    with requests.get(url, stream=True, allow_redirects=False, timeout=(5, 20)) as response:
        if response.status_code != 200:
            raise ValueError("official reference fetch failed or redirected")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_REFERENCE_BYTES:
                raise ValueError("reference document exceeds the capture size limit")
            chunks.append(chunk)
        return b"".join(chunks)


def capture_sse_references(
    profile_path: Path,
    *,
    artifact_root: Path,
    capture_dir: Path,
    captured_at: datetime,
    source_dir: Path | None = None,
    fetch: Callable[[str], bytes] = _fetch,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Path:
    require_timezone(captured_at, "captured_at")
    raw = _profile(profile_path)
    store = FileSystemArtifactStore(artifact_root)
    completed_at = captured_at
    records: list[dict[str, str]] = []
    for document in raw["documents"]:
        content = (
            (source_dir / document["file_name"]).read_bytes()
            if source_dir is not None
            else fetch(document["source_url"])
        )
        if not content or len(content) > MAX_REFERENCE_BYTES:
            raise ValueError("reference document is empty or oversized")
        if sha256(content).hexdigest() != document["content_sha256"]:
            raise ValueError("reference source changed; a new source review is required")
        observed_at = max(captured_at, clock())
        require_timezone(observed_at, "source observed_at")
        completed_at = max(completed_at, observed_at)
        artifact = ProviderArtifact(
            artifact_id=evidence_hash(document),
            provider="sse_rule_reference",
            dataset="reviewed_rule_documents",
            market=Market.CHINA_A,
            subject=SSE_PROFILE_VERSION,
            source_identity=document["role"],
            source_reference=document["source_url"],
            published_at=observed_at,
            retrieved_at=observed_at,
            content_hash=document["content_sha256"],
            media_type=document["media_type"],
            availability_precision=AvailabilityPrecision.RETRIEVAL_TIME,
            trust_level=DataTrustLevel(raw.get("trust_level", "unknown")),
            content=content,
        )
        stored = store.put(artifact)
        records.append(
            {
                "role": document["role"],
                "source_url": document["source_url"],
                "content_sha256": document["content_sha256"],
                "storage_key": stored.storage_key,
            }
        )
    payload = {
        "profile_sha256": raw["_content_sha256"],
        "captured_at": max(completed_at, clock()).isoformat(),
        "documents": sorted(records, key=lambda item: item["role"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    capture_dir.mkdir(parents=True, exist_ok=True)
    destination = capture_dir / f"sse-rule-capture-{sha256(encoded).hexdigest()}.json"
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if destination.read_bytes() != encoded:
            raise ValueError("capture manifest contains different bytes") from None
    else:
        with os.fdopen(descriptor, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
    return destination


def load_sse_references(
    profile_path: Path,
    *,
    artifact_root: Path,
    capture_path: Path,
) -> SSEReferenceBundle:
    raw = _profile(profile_path)
    encoded = capture_path.read_bytes()
    digest = sha256(encoded).hexdigest()
    if capture_path.name != f"sse-rule-capture-{digest}.json":
        raise ValueError("capture manifest hash is invalid")
    captured = json.loads(encoded)
    if captured["profile_sha256"] != raw["_content_sha256"]:
        raise ValueError("capture is bound to a different reviewed profile")
    records = captured["documents"]
    if len(records) != 3 or len({record["role"] for record in records}) != 3:
        raise ValueError("capture requires unique document roles")
    by_role = {record["role"]: record for record in records}
    documents: list[ReviewedRuleDocument] = []
    if artifact_root.is_symlink():
        raise ValueError("artifact root must not be a symbolic link")
    root = artifact_root.resolve()
    for document in raw["documents"]:
        record = by_role.get(document["role"])
        if record is None or any(
            record[name] != document[name] for name in ("source_url", "content_sha256")
        ):
            raise ValueError("capture document identity does not match reviewed sources")
        key = Path(record["storage_key"])
        if key.is_absolute() or ".." in key.parts:
            raise ValueError("capture artifact key is unsafe")
        path = root / key
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("capture artifact escapes its storage root")
        if path.stat().st_size > MAX_REFERENCE_BYTES:
            raise ValueError("captured reference exceeds the size limit")
        require_sha256(record["content_sha256"])
        if sha256(path.read_bytes()).hexdigest() != record["content_sha256"]:
            raise ValueError("captured rule-document bytes do not match their hash")
        documents.append(
            ReviewedRuleDocument(
                document["role"],
                document["source_url"],
                document["content_sha256"],
            )
        )
    observed_at = datetime.fromisoformat(captured["captured_at"])
    require_timezone(observed_at, "capture observed_at")
    reviewed_at = raw["reviewed_at"]
    require_timezone(reviewed_at, "reviewed_at")
    return SSEReferenceBundle(
        profile_version=raw["profile_version"],
        effective_from=raw["effective_from"],
        available_at=max(observed_at, reviewed_at),
        review_expires_at=raw["review_expires_at"],
        documents=tuple(documents),
        capture_hash=digest,
        trust_level=DataTrustLevel(raw.get("trust_level", "unknown")),
    )
