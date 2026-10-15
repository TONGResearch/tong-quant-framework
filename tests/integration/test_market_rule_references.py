import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import pytest

from tong_quant.application.market_rule_references import (
    _fetch,
    capture_sse_references,
    load_sse_references,
)
from tong_quant.core.exceptions import MarketRuleEvidenceUnavailableError

NOW = datetime(2026, 10, 16, tzinfo=UTC)


def _profile(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    bodies = {
        f"https://www.sse.com.cn/lawandrules/test/{role}": f"synthetic {role} fixture".encode()
        for role in ("rules", "deferred", "odd_lots")
    }
    lines = [
        'profile_version = "sse-main-board-2026-v1"',
        "effective_from = 2026-07-06",
        "reviewed_at = 2026-10-15T00:00:00Z",
        "review_expires_at = 2026-11-15T00:00:00Z",
        'trust_level = "high"',
    ]
    for url, body in bodies.items():
        role = url.rsplit("/", 1)[1]
        lines.extend(
            (
                "[[documents]]",
                f"role = {json.dumps(role)}",
                f"source_url = {json.dumps(url)}",
                f'content_sha256 = "{sha256(body).hexdigest()}"',
                f'file_name = "{role}.bin"',
                'media_type = "application/octet-stream"',
            )
        )
    profile = tmp_path / "synthetic-reviewed-profile.toml"
    profile.write_text("\n".join(lines), encoding="utf-8")
    return profile, bodies


def _capture(tmp_path: Path) -> tuple[Path, Path, Path]:
    profile, bodies = _profile(tmp_path)
    artifacts = tmp_path / "artifacts"
    capture = capture_sse_references(
        profile,
        artifact_root=artifacts,
        capture_dir=tmp_path / "captures",
        captured_at=NOW,
        fetch=bodies.__getitem__,
        clock=lambda: NOW,
    )
    return profile, artifacts, capture


def test_verified_capture_round_trip_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    profile, artifacts, capture = _capture(tmp_path)
    references = load_sse_references(profile, artifact_root=artifacts, capture_path=capture)
    assert references.available_at == NOW
    assert len(references.evidence(as_of=NOW)) == 3
    assert len(tuple(artifacts.rglob("*.bin"))) == 3
    profile, bodies = _profile(tmp_path)
    again = capture_sse_references(
        profile,
        artifact_root=artifacts,
        capture_dir=capture.parent,
        captured_at=NOW,
        fetch=bodies.__getitem__,
        clock=lambda: NOW,
    )
    assert again == capture
    assert len(tuple(artifacts.rglob("*.bin"))) == 3


def test_available_at_follows_completed_capture_not_fetch_start(tmp_path: Path) -> None:
    profile, bodies = _profile(tmp_path)
    times = iter(NOW + timedelta(seconds=index) for index in range(1, 5))
    capture = capture_sse_references(
        profile,
        artifact_root=tmp_path / "artifacts",
        capture_dir=tmp_path / "captures",
        captured_at=NOW,
        fetch=bodies.__getitem__,
        clock=lambda: next(times),
    )
    references = load_sse_references(
        profile,
        artifact_root=tmp_path / "artifacts",
        capture_path=capture,
    )
    assert references.available_at == NOW + timedelta(seconds=4)
    with pytest.raises(MarketRuleEvidenceUnavailableError, match="future"):
        references.evidence(as_of=NOW)


def test_changed_official_bytes_require_new_review(tmp_path: Path) -> None:
    profile, _ = _profile(tmp_path)
    with pytest.raises(ValueError, match="new source review"):
        capture_sse_references(
            profile,
            artifact_root=tmp_path / "artifacts",
            capture_dir=tmp_path / "captures",
            captured_at=NOW,
            fetch=lambda url: b"different response",
            clock=lambda: NOW,
        )
    assert not (tmp_path / "captures").exists()


def test_missing_or_tampered_document_fails_closed(tmp_path: Path) -> None:
    profile, artifacts, capture = _capture(tmp_path)
    record = json.loads(capture.read_bytes())["documents"][0]
    artifact = artifacts / record["storage_key"]
    artifact.write_bytes(b"tampered fixture")
    with pytest.raises(ValueError, match="bytes do not match"):
        load_sse_references(profile, artifact_root=artifacts, capture_path=capture)
    artifact.unlink()
    with pytest.raises(FileNotFoundError):
        load_sse_references(profile, artifact_root=artifacts, capture_path=capture)


def test_capture_manifest_and_profile_binding_are_verified(tmp_path: Path) -> None:
    profile, artifacts, capture = _capture(tmp_path)
    original = capture.read_bytes()
    capture.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="manifest hash"):
        load_sse_references(profile, artifact_root=artifacts, capture_path=capture)
    capture.write_bytes(original)
    profile.write_text(profile.read_text() + "\n# altered profile\n", encoding="utf-8")
    with pytest.raises(ValueError, match="different reviewed profile"):
        load_sse_references(profile, artifact_root=artifacts, capture_path=capture)


def test_capture_storage_keys_cannot_escape_artifact_root(tmp_path: Path) -> None:
    profile, artifacts, capture = _capture(tmp_path)
    payload = json.loads(capture.read_bytes())
    payload["documents"][0]["storage_key"] = "../outside.bin"
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    changed = capture.parent / f"sse-rule-capture-{sha256(encoded).hexdigest()}.json"
    changed.write_bytes(encoded)
    with pytest.raises(ValueError, match="unsafe"):
        load_sse_references(profile, artifact_root=artifacts, capture_path=changed)


@pytest.mark.parametrize(
    "url", ["https://example.com/rules", "http://www.sse.com.cn/lawandrules/rule"]
)
def test_reference_fetch_rejects_unapproved_urls_before_network(url: str) -> None:
    with patch("tong_quant.application.market_rule_references.requests.get") as get:
        with pytest.raises(ValueError, match="approved official"):
            _fetch(url)
        get.assert_not_called()


def test_reference_fetch_disables_redirects_and_rejects_http_redirect_response() -> None:
    with patch("tong_quant.application.market_rule_references.requests.get") as get:
        get.return_value.__enter__.return_value.status_code = 302
        with pytest.raises(ValueError, match="redirected"):
            _fetch("https://www.sse.com.cn/lawandrules/test/rules")
        assert get.call_args.kwargs["allow_redirects"] is False
        assert get.call_args.kwargs["timeout"] == (5, 20)
