# Work Package: WP-DATA-002

Status: `planned`

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
