# Database Backup And Restore Runbook

## Safety Boundary

Tong Quant database recovery is evidence preservation, not trading
functionality. The tooling never connects to providers, notifications, brokers,
orders, or execution.

Never copy a live SQLite database with `cp`. WAL-backed writes may not be fully
represented in the main file. Use SQLite's online backup API through the
commands below.

The tools enforce these rules:

- audits open the database read-only;
- source and destination must differ;
- destinations must not already exist;
- backup and restore work through same-directory temporary files;
- a destination is published only after integrity, foreign-key, migration,
  schema-fingerprint, and row-count checks pass;
- published database files use mode `0600`;
- command arguments never accept credentials.

## Read-Only Audit

```bash
python scripts/manage_database.py audit \
  --database data/tong_quant.sqlite3 \
  --output reports/database-audit.json
```

The audit checks:

- `PRAGMA integrity_check`;
- `PRAGMA foreign_key_check`;
- ordered migration IDs and checksums;
- migration-head metadata;
- stored and computed physical schema fingerprints;
- the baseline schema-definition hash;
- table row counts;
- absence of credential-like schema columns.

A failed audit exits non-zero but still emits its structured report when an
output path is supplied. Audits do not initialize or migrate the source.

## Verified Backup

Choose a new timestamped path on a FileVault-protected or otherwise approved
encrypted volume:

```bash
python scripts/manage_database.py backup \
  --database data/tong_quant.sqlite3 \
  --destination backups/tong-quant-2026-08-21T2200.sqlite3 \
  --output backups/tong-quant-2026-08-21T2200.manifest.json
```

Keep the database and manifest together. The manifest records the source and
backup audit hashes, SHA-256 file hash, schema fingerprint, migration head, file
size, and row-count comparison.

The command never overwrites an existing destination or report. Pick a new
path instead of deleting evidence from a prior run.

## Restore Drill

Restore only into a new isolated destination:

```bash
python scripts/manage_database.py restore-dry-run \
  --backup backups/tong-quant-2026-08-21T2200.sqlite3 \
  --destination restore-drills/tong-quant-2026-08-21.sqlite3 \
  --output restore-drills/tong-quant-2026-08-21.report.json
```

The drill audits the backup, restores through the SQLite backup API, runs
supported forward migrations on the isolated temporary copy, audits it again,
verifies all source data-table counts and nondecreasing migration-ledger counts,
and only then publishes the drill database. It never changes the backup or the
active source database.

An older backup is accepted only when its migration ledger is a checksum-valid
prefix and both its physical fingerprint and frozen historical schema-definition
hash are recognized. Pre-ledger or unknown historical schemas fail closed.

## Recovery Procedure

1. Stop all writers using the affected database.
2. Preserve the affected database and any `-wal`/`-shm` files for diagnosis.
3. Audit candidate backups and select the newest passing manifest/database
   pair.
4. Run `restore-dry-run` into a new path on the target encrypted volume.
5. Compare migration head, schema fingerprint, table counts, and hashes in the
   generated reports.
6. Run the full Tong Quant test and governance commands against the code version
   that will open the restored database.
7. Change application configuration to the restored path only after manual
   review. Never replace the damaged source in place.
8. Retain the damaged source, selected backup, manifest, and restore report
   until the incident is closed.

## Retention Policy

For research databases with meaningful history, the recommended minimum is:

- one verified backup before every schema migration;
- seven daily backups;
- eight weekly backups;
- twelve monthly backups;
- one separately encrypted off-device copy for irreplaceable evidence.

Retention deletion is intentionally not automated. Review hashes, destination
encryption, free space, and required evidence before removing a backup.

## Limitations

- Tong Quant does not implement backup encryption or cloud upload. The operator
  must choose an approved encrypted destination.
- SQLite backups contain provider artifact metadata but not files under
  `data/provider-artifacts`. Preserve that content-addressed directory on an
  encrypted volume and verify its hashes separately before declaring a complete
  evidence recovery.
- Credential-like schema columns are rejected, but opaque unlabelled secret
  values cannot be detected reliably. Credentials must never be persisted in
  the source database.
- Downgrade migrations are not supported. Restore drills move recognized older
  snapshots forward on an isolated copy only.
- Automatic scheduling, off-device replication, retention deletion, free-space
  prediction, and production incident orchestration remain future operations
  work.
