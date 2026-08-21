# Work Package: WP-DB-001

Status: `completed`

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

## Completion Record

- Added typed read-only integrity reports, verified backup manifests, and
  isolated restore reports.
- Added SQLite online-backup copying through temporary files with atomic
  no-overwrite publication and mode `0600`.
- Audits verify integrity, foreign keys, migration order/checksums, schema
  metadata/fingerprints, table counts, and credential-like schema columns.
- Added `scripts/manage_database.py` with explicit `audit`, `backup`, and
  `restore-dry-run` commands.
- Added interruption, corruption, migration-tampering, no-overwrite, read-only,
  backup, supported forward-migration restore, and command-level tests.
- Added the retention and operator recovery runbook. Encryption, cloud upload,
  automated deletion, and production incident orchestration remain out of
  scope.
