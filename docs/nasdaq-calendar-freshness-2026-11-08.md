# Nasdaq Calendar Source Age

## Scope And Contract

November 8, WP-LAUNCH-001: an optional read-side source-age check, not a new
calendar, trading rule, data provider, scheduler or source qualification.
`read_nasdaq_calendar_inputs(..., maximum_source_age_seconds=N)` requires a
positive exact integer. Invalid values fail before database access. The manual
CLI accepts `--max-source-age-seconds N` only with read-only `--as-of`, never
with capture. No default TTL or automatic refresh policy is introduced.

The default reader remains byte/hash-compatible with v1 and reports UNASSESSED.
Consumers needing a source-age check must explicitly opt in; the default is not
freshness approval. The opt-in receipt uses nasdaq-calendar-source-age-v1 while
retaining the original source/parser normalization version and evidence identity.

```text
Existing retained snapshot verification at one cutoff
  -> unique latest capture and completed batches, no favorable fallback
  -> exact UTC elapsed microseconds since original retrieval
  -> BLOCKED_INPUT / WITHIN_CONFIGURED_LIMIT / STALE
  -> hash-bound read receipt, no database writes
```

Only a verified retained original body with successful explicit-table parsing
can be WITHIN_CONFIGURED_LIMIT. Exactly the caller limit is included; one
microsecond over is stale. Completion time, review time, future holiday date and
wall-clock/DST labels cannot rejuvenate a capture. Huge integer limits do not
construct overflowing timedeltas. Cutoffs and source ages use actual UTC instants.

Stale receipts expose status stale_source_capture and no current declarations.
Original rows remain in observed_declarations, with source_status, capture time,
exact age, source/evidence hashes and capture inventory. Unsupported rows also
remain observed but blocked, even when recent. Missing/future, failed, tied,
tampered or incomplete-batch inputs cannot fall back to old favorable data or
invent a zero age. A verified unsupported body may expose its age without approval.

Every opt-in metadata field, including the limit, is included in input_hash.
Within-limit means only caller-defined capture age, not truthful content, complete
calendar, known first publication, actual sessions or PIT/strategy qualification.
LOW / retrieval_time and all existing false authorities remain unchanged.

## Read-Only Retained Evidence Check

The one-hour limit below is illustrative, not an approved operating policy.
The November 7 local diagnostic capture is available at
2026-11-06T16:19:18.502405+00:00. Offline comparisons on November 8:

| Read cutoff (UTC) | Capture age (microseconds) | Freshness | Current / observed rows |
| --- | ---: | --- | --- |
| 2026-11-06T16:19:18.567608+00:00 | 65,203 | WITHIN_CONFIGURED_LIMIT | 12 / 12 |
| 2026-11-06T18:00:00+00:00 | 6,041,497,595 | STALE | 0 / 12 |

Unmodified default v1 receipt hash:
7587663f621bcb9da28618a3aea008f7841f31c2b3ccc20692abfecc9fecf942.
Opt-in within-limit hash:
9ebffee993fc1bd89e9c51970d7e1480fda37b58cbb506be0ca0c9a8951c705f.
Opt-in stale hash:
247bf968116ee7c70896485e7c8c3aff8d4179858c81c11c7f373ddfd4b51c38.

No network request, existing database initialization/migration or retained-byte
rewrite was used. Price, SEC and Nasdaq sample database hashes are rechecked.
Raw databases/bodies remain ignored local evidence, not Git backup.

## Compatibility Limitation Found

The existing source adapter's injectable non-UTC capture clock can produce an
evidence identity different from reconstruction of its UTC envelope. Such records
fail retained-snapshot verification; this update deliberately keeps them blocked,
not silently reidentified, migrated or relabeled fresh. Default/manual captures
already use UTC and are unaffected. A regression test records this limitation;
separate source-normalization/legacy-identity design is needed for non-UTC
producer clocks. Read cutoffs may use any aware timezone, including DST folds.

### Preventive Write Guard

A subsequent November 8 repair now rejects nonzero-offset producer clocks with
an explicit ValueError before a batch, fingerprint, evidence record or artifact
is persisted. The captured response may already have been downloaded in memory;
this is not a pre-network guard. The check does not silently normalize the clock
or claim that old unsupported identities are repaired. Equivalent zero-offset
labels retain the same UTC encoding and identity. Existing UTC receipts and all
read-side source-age semantics remain unchanged, so the v1 source normalization
and source-age versions are not bumped. No successful output format changes.

Six additional synthetic cases cover Malaysia and both repeated New York DST
hours rejected without SQL/raw writes, and three equivalent zero-offset clock
labels with unchanged bytes/IDs. The old-record fixture separately reconstructs
the original legacy batch in tests only; production has no guard bypass or new
compatibility mode. That retained legacy record still fails closed on read.
The Nasdaq suite now has 72 cases. Full regression for this repair: 3649 passed /
6 skipped, 263.17 seconds; Ruff, mypy (313 files), governance (168 checks), scoped
import/credential review and git diff --check pass. Real retained v1 receipt and
three sample database hashes are unchanged. This is mixed-tree verification, not
an isolated release review or real provider/strategy validation; no commit/push.

## Verification And Remaining Gates

Nineteen new synthetic cases plus extensions of six existing failure cases cover
invalid limits before I/O, exact boundaries, missing/future inputs, stale row
retention, latest failures/ties/tampering, unsupported source rows, completion-time
separation, DST folds, deterministic limit-bound hashes, new-capture visibility,
legacy defaults, offline CLI and pre-I/O capture-mode rejection.

Full pytest: 3643 passed / 6 skipped in 274.62 seconds. Ruff, mypy (313 files),
governance (168 checks), scoped runtime import/credential review and git diff
--check pass. Six skipped opt-in network tests are not real provider evidence.
These are mixed-workspace checks, not an isolated publishable candidate review.
Synthetic checks and local reconstruction cannot certify source truth or an investment
strategy. Qualified ordinary/abnormal-session evidence, price-session semantics,
corporate-action basis, independent consistency, technical/fundamental admission
and real validation remain open. No schema, dependency, default or trading changes;
PIT UNSUITABLE, production NOT_READY and launch ready/not accepted persist.
