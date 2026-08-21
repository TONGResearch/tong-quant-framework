# ADR 0004: Verified SQLite Recovery

Status: Accepted

## Decision

Tong Quant database backups and restore drills must use SQLite's online backup
API. Every operation follows a read-only audit, temporary copy, post-copy audit,
state comparison, and no-overwrite publication sequence.

Active source databases are never restored or replaced in place. A restore
drill targets a new path and may run forward migrations only on its isolated
temporary copy. Older snapshots are eligible only when their ordered migration
prefix, checksums, physical fingerprint, and frozen historical schema-definition
hash can all be authenticated.

## Rationale

Copying a live SQLite main file can omit WAL state, while an unchecked backup
can preserve corruption or a tampered migration ledger. Publishing only a
verified temporary snapshot makes incomplete or interrupted operations visible
and prevents partial files from being mistaken for recoverable databases.

## Consequences

- Existing destination files are never overwritten.
- Integrity, foreign keys, migration checksums, physical fingerprint, and table
  counts are checked before publication.
- Backup files are local mode `0600`; off-device storage must be separately
  approved and encrypted.
- No backup command accepts or transports credentials.
- Downgrade, cloud replication, and automated retention remain out of scope.
