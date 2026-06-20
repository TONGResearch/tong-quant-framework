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

The current migration head is `0003_provider_calibration_phase_ii`. The public schema
version remains `0.8.0`; this is data-foundation remediation rather than a new
product milestone.

## Transaction Boundary

`SQLiteStore.transaction()` reuses one connection for repository calls and
commits or rolls back the entire unit. Research and Validation final-run writes
use this boundary. Run creation remains separate so a failed run can retain an
explicit audit record.

## Migration Roadmap

1. Keep future migrations append-only and checksum verified.
2. Add pre-migration backup, free-space, integrity, and supported-source checks.
3. Add post-migration `foreign_key_check` and domain invariant checks.
4. Rebuild analytical child tables in small groups to add missing foreign keys;
   do not rewrite the full schema in one release.
5. Define explicit `RESTRICT`, `CASCADE`, or immutable-history behavior before
   adding each relationship.
6. Split the large SQLite module by market data, research, validation, portfolio,
   and notification ownership while retaining one transaction manager.
7. Add downgrade policy. Until then, migrations are forward-only and require a
   backup for production-like datasets.

## Current Limitation

Most pre-existing analytical tables still lack database-enforced foreign keys.
Adding them safely in SQLite requires table reconstruction, data cleanup, and
orphan audits. This stabilization phase intentionally avoids an unsafe global
schema rewrite.
