# Work Package: WP-DATA-002

Status: `completed`

## Objective

Capture direct CNInfo filing artifacts and metadata so China disclosure timing
can be verified independently of the AKShare transport layer.

## Scope

- Direct-source capability and rate-limit detection
- Filing URL, publication timestamp, retrieval timestamp, and content hash
- Raw artifact metadata without storing credentials
- Correction and supersession links where evidence exists
- Cross-check against `cninfo_via_akshare`

## Acceptance Criteria

- Direct and transported provenance remain distinct.
- Duplicate artifacts are idempotent by content and source identity.
- Missing files and changed URLs remain auditable.
- Trust changes require measured parity and coverage review.

## Non-Goals

- No automatic financial interpretation or trade decision.
- No invented numeric revision history.
- No bypass of CNInfo terms, rate limits, or access controls.

## Completion Record

- Added the `cninfo_direct` provider with HTTPS-only official endpoint/domain
  boundaries, bounded pagination, request pacing, retries, timeouts, and file
  size limits.
- Added immutable provider artifact and capture-observation contracts, a
  content-addressed mode-`0600` filesystem store, and transactional SQLite
  metadata persistence.
- Added migration `0007_cninfo_artifact_capture` with artifact identity,
  retrieval history, missing/unavailable status, relation evidence, and foreign
  keys to ingestion batches.
- Added direct-versus-`cninfo_via_akshare` calibration snapshots using the
  existing ProviderCalibration engine. No parity result promotes trust.
- Added deterministic fake-client tests plus an opt-in live metadata check.
- Verified a real bounded metadata request and one public PDF capture on
  2026-08-21, plus a 3/3 same-day announcement match against the AKShare
  transport. This proves the current contract path, not historical continuity.
