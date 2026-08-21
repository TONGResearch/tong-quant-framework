# Work Package: WP-DB-001

Status: `ready`

## Objective

Prove that a Tong Quant SQLite database can be backed up, restored, migrated,
and integrity-checked without silent schema or audit-history loss.

## Scope

- Use SQLite's backup API for consistent snapshots.
- Verify schema fingerprint, migration checksums, foreign keys, and integrity.
- Add a dry-run restore procedure using a separate destination.
- Define retention and operator recovery documentation.
- Test interrupted and corrupted backup failure behavior.

## Deliverables

- Typed backup/integrity service
- Read-only audit command and explicit backup command
- Deterministic tests with temporary databases
- Backup/restore runbook

## Acceptance Criteria

- Restore reproduces table counts, migration head, and schema fingerprint.
- Corruption or migration mismatch fails closed.
- Existing source databases are never overwritten by default.
- Commands do not include or copy credentials outside approved encrypted storage.

## Non-Goals

- No cloud database migration.
- No production deployment system.
- No trading-related implementation.

## Required Verification

Run all commands in `PROJECT_STATUS.md` plus restore and corruption tests.
