# Database Migration Framework

## Current Design

`SQLiteStore.initialize()` creates missing baseline tables and then runs ordered,
immutable migrations from `data/storage/migrations.py`. Applied migrations are
stored in `schema_migrations` with an identifier, checksum, description, and
application time. A checksum mismatch fails closed.

`schema_metadata` records both the public database schema version and the exact
migration head. The stabilization work keeps the public schema at `0.8.0`; the
migration head distinguishes the hardened physical schema without declaring a
new product milestone.

Migration `0000_schema_baseline` registers the pre-ledger schema as an explicit
baseline. It performs no DDL and fails when required legacy tables are absent.

Migration `0001_notification_hardening` adds:

- Notification lease expiration and dead-letter timestamps
- A lease lookup index
- `notification_dead_letters`, linked to the outbox by foreign key

Migration `0002_pit_data_calibration` adds:

- Readiness score, classification, components, and assumptions
- `security_lifecycle_events`
- `fundamental_publication_events`
- `historical_coverage_assessments`
- `provider_consistency_reports`

Migration `0003_provider_calibration_phase_ii` adds:

- `provider_conflicts` with stable fingerprints and per-run observations
- `dataset_confidence_assessments` linked to calibration reports

Migration `0004_schema_fingerprint_ledger` adds:

- A canonical fingerprint of tables, indexes, views, and triggers
- A hash of the baseline `SCHEMA` definition
- Fail-closed validation before any later migration is applied

Migration `0005_provider_evidence_foundation` adds:

- `provider_evidence_records` for provider-neutral, PIT-annotated evidence
- `provider_contract_runs` for scheduled monitor executions
- `provider_contract_checks` for dataset-level health and field-contract results

Migration `0006_provider_contract_baseline` adds:

- `provider_baseline_manifests` for immutable query, version, input-hash, and
  baseline-hash metadata
- `provider_baseline_entries` for scope-level success, field coverage,
  continuity, gaps, trust observations, and limitations
- `provider_baseline_inputs` linking each manifest to its original contract
  checks with `RESTRICT` history semantics

Migration `0007_cninfo_artifact_capture` adds:

- `provider_artifacts` for immutable source/content identity and safe relative
  storage keys
- `provider_artifact_observations` for captured, missing, unavailable, changed
  URL, and relation evidence over time

The current migration head is `0007_cninfo_artifact_capture`. The public
schema version remains `0.8.0`; this is data-foundation remediation rather than
a new product milestone.

`SQLiteStore.initialize()` validates the last recorded physical fingerprint
before baseline creation or pending migrations. It records a new fingerprint
only after the ordered migration set completes. Unmigrated additions, removals,
or changes therefore fail closed instead of being adopted by a new migration
head.

## Transaction Boundary

`SQLiteStore.transaction()` reuses one connection for repository calls and
commits or rolls back the entire unit. Research and Validation final-run writes
use this boundary. Run creation remains separate so a failed run can retain an
explicit audit record.

## Backup And Restore Assurance

`SQLiteIntegrityService` audits databases through a read-only connection. It
checks SQLite integrity, foreign keys, migration order and checksums, schema
metadata, the physical fingerprint ledger, table row counts, and
credential-like schema columns.

`SQLiteBackupService` uses SQLite's online backup API and never publishes a
destination until a temporary snapshot passes the same audit and matches the
source table counts, migration head, and fingerprint. Restore drills copy into
a separate temporary database, run supported forward migrations there, verify
all source table counts, and publish only to a new destination. Existing files
are never overwritten.

See `docs/database-backup-restore.md` for commands, retention, and recovery.

## Migration Roadmap

1. Keep future migrations append-only and checksum verified.
2. Add free-space estimation and automatic pre-migration backup orchestration;
   explicit verified backup and supported-source checks are now available.
3. Extend the implemented post-copy integrity and `foreign_key_check` audit
   with broader domain invariants.
4. Rebuild analytical child tables in small groups to add missing foreign keys;
   do not rewrite the full schema in one release.
5. Define explicit `RESTRICT`, `CASCADE`, or immutable-history behavior before
   adding each relationship.
6. Split the large SQLite module by market data, research, validation, portfolio,
   and notification ownership while retaining one transaction manager.
7. Add downgrade policy. Until then, migrations are forward-only and require a
   verified backup plus isolated restore drill for production-like datasets.

## Current Limitation

Most pre-existing analytical tables still lack database-enforced foreign keys.
Adding them safely in SQLite requires table reconstruction, data cleanup, and
orphan audits. Backup encryption, automated scheduling/retention, free-space
prediction, and downgrade migrations also remain outside the current local
recovery tooling.
