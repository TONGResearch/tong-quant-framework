# Read-Only Exact Refresh Reconciliation

WP-LAUNCH-001 adds `data.refresh_reconciliation.inspect_refresh_reconciliation`
and `scripts/inspect_refresh_reconciliation.py`. This checks exact retained receipt
linkage, not source truth, historical PIT readiness, or research approval. It does
not implement reconciliation repair, checkpoint completion or capture.

## Dependency And Read Boundary

Explicit job ID + aware inspection cutoff -> existing read-only SQLite database
-> current schema metadata, migration checksums and physical fingerprint
-> immutable plan/scope + contiguous attempts -> exact linked ingestion batch
-> raw fingerprint + evidence records + artifact observations
-> explicitly referenced artifact registry entries -> secure bounded byte audit.

The ledger repository shares the caller's existing read snapshot for metadata
validation rather than opening a separate connection. All relational reads in
the inspector share one snapshot. Files are not atomic with it; quiesce writers
and repeat before any future recovery acceptance. Database/artifact path components
reject symlinks. This does not defend against a hostile process swapping the
database after its path precheck.

No symbol/date/hash search substitutes for a missing batch association. Selection
follows evidence payload `artifact_id` and captured observations, and checks this
batch's first-registered rows for unreferenced originals. An artifact's
`first_batch_id` may be earlier than this batch; that explicit owner must still
exist and match the capture identity. The selected audit declares
`caller_selected_rows_only`; it does not certify the entire registry or inventory
unregistered files. SHA-256, no-follow, regular-file, size and mutation checks reuse
the existing artifact auditor.

Identical AKShare frame bytes can be observed again with the same artifact ID;
the original registry's first timestamps are not this attempt's observation time.
Current observations keep their own timestamps and exact source identities.

Shared helpers own expected batch parameters and retention classification, so
write-side association and read-side inspection do not invent different
Yahoo/AKShare contracts. Malformed Yahoo status values remain invalid responses,
not unhandled set-construction failures.

## Scope And Results

Supported planned captures: AKShare `a_share_daily`; Yahoo
`global_equity_price_snapshot` and `global_native_fundamental_snapshot`. They remain
LOW/UNKNOWN, retrieval-time evidence. Unsupported contracts and unexpected metadata
remain visible as non-successful diagnostics.

- `LINKED_BYTES_MATCH`: exact retained receipt links and selected bytes match.
- `LINKED_FAILURE_BYTES_MATCH`: failed/empty/provider-restricted snapshot has intact
  links and bytes; it remains failed and the CLI exits nonzero.
- `JOB_MISSING`, `NO_ATTEMPT`, `IN_PROGRESS`, `RECOVERY_REQUIRED`, `NO_LINKED_BATCH`:
  no completed linked inspection; never search other jobs or advance state.
- `ORIGINAL_UNVERIFIABLE`, `NO_REFERENCED_ORIGINAL`, `LIMIT_EXCEEDED`,
  `UNREADABLE_OR_INCONSISTENT`: retain the gap; do not repair, guess or drop it.

The aware cutoff is an upper timestamp bound on the current snapshot, not historical
database reconstruction. Retrieval/publication/observation/local ingestion clocks
are checked without inventing publication knowledge. Non-canonical source timestamp
identities may fail reconstruction conservatively. No source re-normalization,
numeric accounting/canonical bar validation, calendar completeness, authenticity or
adjustment history verification. Coordinated changes to an unsigned database and
its files are not independently authenticated by internally consistent hashes.

## Operational Contract

Required CLI arguments: `--database`, `--artifact-root`, `--job-id`, `--as-of`.
Optional positive limits: `--max-records` (10,000), `--max-file-bytes` (64 MiB),
`--max-total-bytes` (512 MiB). Each selected receipt table/lookup metadata block is
limited to 2 MiB before materialization/parsing. Schema checks still scan database
metadata; this is not a general hostile-database resource sandbox. These are
diagnostic bounds, not disk quotas.
Reports go to stdout only. Exit 0 means only `LINKED_BYTES_MATCH`; exit 1 means a
non-successful diagnostic, exit 2 invalid arguments. No output directory, network,
credentials, capture/retry/repair flag or implicit database creation.

Reports contain fixed codes, counts, safe IDs and hashes, never raw payloads,
source URLs, filesystem paths or exception values. Hashes are deterministic for
the same snapshot, selected bytes, limits and UTC cutoff. All qualification,
checkpoint and authorization flags remain false.

Tests use synthetic captures/temp databases: A-share frame/observation linkage,
three overseas markets, native financial permission failure, missing links, earlier
registry ownership, corrupt/symlink bytes, future times, schema drift, limits, safe
CLI errors and a concurrent SQL writer. Fixtures use a late cutoff to include
real-clock local ingestion audit times; they are not independent provider evidence.

## Verification

37 new synthetic cases. Final full suite: **3235 passed, 6 skipped**, 174.35 seconds.
Ruff and mypy (304 source files) pass; governance has 155 passing checks;
git diff --check and scoped credential/import review pass. Six opt-in real-network
skips do not demonstrate provider availability. Both retained sample database
SHA-256 values match the preceding slice. No original capture, migration of user
databases, commit or push. Additive `readonly-refresh-reconciliation-v1` only;
framework 0.8.0, schema 0.8.3 / migration 0011 and disabled defaults unchanged.

## Remaining Gates

No schema/migration/framework-default/source-policy/trading change. User sample
databases and original archives remain unmodified. PIT UNSUITABLE, production
NOT_READY, R1-R6 partial, launch ready/not accepted. Next: separately review bounded
capacity controls and one-shot capture integration. Completing/resetting jobs,
checkpoint admission, global-reference-safe GC, directory durability, encrypted
restore and scheduler activation remain unmet.
