# Registered Artifact Portability Audit

## Purpose And Boundary

WP-LAUNCH-001 research deployment hardening, not a trading feature. A Git clone
does not include ignored databases or provider bytes. A verified SQLite backup
contains the artifact registry, not the referenced files. The prior runbook
also named an incorrect generic artifact directory; explicit roots below are
required for these two local datasets.

`data.storage.artifact_audit` / `provider-artifact-audit-v1` reads one SQLite
registry transaction without initialization or migration. Each registered file
must have the expected content-addressed relative key, positive recorded size,
matching actual size and matching SHA-256. POSIX no-follow directory/file
descriptors reject symlinks at every path component; FIFOs are opened nonblocking
and rejected. Reads have record, per-file and total byte budgets. Wrong roots,
empty registries, malformed metadata, missing/damaged files and exceeded limits
cannot return `registered_artifacts_verified=true`.

Reports expose hashed registry references and fixed diagnostic codes only, not
paths, source URLs, raw payloads or exception text. Identical registry metadata
and file results produce identical registry/report hashes. Those hashes bind
only the selected registry fields and results, not the whole database, an
authenticated source identity or a signed release. Missing entries remain in
the report; exceeding the row budget marks the scan incomplete rather than
publishing a misleading truncated success.

## Read-Only Commands

From the PyCharm project directory:

```bash
.venv/bin/python scripts/audit_provider_artifacts.py \
  --database data/tong_quant.sqlite3 \
  --artifact-root data/raw/provider-artifacts

.venv/bin/python scripts/audit_provider_artifacts.py \
  --database data/processed/exploratory-pilot-20261016.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts
```

Exit 0 means all **nonempty registered** entries passed; exit 2 means otherwise.
The commands print JSON and do not write reports, repair files, copy data,
contact providers or inspect credential environment variables.

## Local Observation: October 18, 2026

| Database scope | Registered | Verified | Registry SHA-256 |
|---|---:|---:|---|
| Operational baseline | 4 | 4 | `68a25849d15e28f23113b3622f51da166b6e1a79824da0cf5729fe911f1b29a6` |
| Exploratory pilot | 4 | 4 | `27ea1349bbe91513571b36051de2181fc9ee72475fe781d7a9c7fa38b6e311fb` |

These are eight registry observations, not eight independent providers or
eight complete datasets. No real-data backup or cross-device drill was made
by this slice. Schema remains 0.8.2 / migration 0010. PIT remains UNSUITABLE;
production remains NOT_READY; execution and notifications remain disabled.

## Recovery Checklist And Remaining Gaps

Verification: 905 passed / 6 skipped; Ruff and mypy pass (223 source/script
files); governance passes 80 checks and whitespace checks pass. Twenty-one
new audit tests include missing/damaged files, FIFO/directories, symlinked
components, malformed metadata, credential-like unsafe keys without rendering,
limits, deterministic read-only results and CLI failure on an incorrect root.

1. Choose and approve an encrypted destination; filesystem write permission
   alone does not establish encryption or approval.
2. Quiesce ingestion, then audit the database and registered artifacts. Preserve
   separate inventories of rule/notice captures and any other unregistered data.
3. Use SQLiteBackupService, never filesystem-copy the active SQLite database.
   Retain the verified backup manifest and referenced artifact tree together.
4. Restore to a new isolated path. On the destination run database integrity
   and this artifact audit with the restored registry and relocated explicit
   root. Compare registry/report hashes while preserving the originals.
5. Independently verify non-registry captures, configuration, reviewed Git
   commit and dependency baseline before any manual recovery acceptance.

The DB read snapshot and filesystem reads are not one atomic cross-store
snapshot. Concurrent changes after checking remain possible; controlled
directories, stopped writers and a repeated destination audit are required.
The registry audit is not a replacement for PRAGMA/FK/migration integrity or
full domain-content equality. Metadata-only disclosures without captured
filing bytes are not magically covered. File byte equality proves neither
historical availability, source authenticity, completeness nor encrypted
retention. Off-device retention, independent-host restore and clean committed
release evidence remain open. No Paper, broker or execution authorization is
derived from a passing artifact audit.
