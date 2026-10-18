# Fundamental Fact Integrity - 2026-10-18

Work package: WP-LAUNCH-001 (partial).
Framework 0.8.0; schema 0.8.2; PIT UNSUITABLE; execution disabled.

## Confirmed defect

The fact repository checked differing raw hashes before a bulk
`INSERT OR IGNORE`. An existing row with the same raw hash but different
value, unit, period semantics or trust labels was silently accepted as if it
were an idempotent repeat. Two conflicting new rows in one call also escaped
the precheck. Concurrent writers could both report acceptance while only one
conflicting value remained stored.

The new regression suite first reproduced these failures against the previous
writer. This is a persistence defect, not a provider permission limitation.

## Bounded repair

- Acquire the SQLite writer reservation before checking existing identities.
- Compare every row sharing instrument, metric, period end, publication time,
  revision and availability time. Differing raw hashes still fail explicitly.
- For the same raw hash, verify value, period start, fiscal period, currency,
  unit, source, provider dataset, availability precision and trust level.
  Reject material disagreement rather than ignore or overwrite it.
- Permit numerically equivalent Decimal representations while preserving the
  original stored representation, batch link and ingestion timestamp.
  Retry batch IDs and ingestion clocks are not new economic fact content.
- Insert/check sequentially within one savepoint so same-call conflicts are
  visible and the entire call rolls back on conflict or database rejection.
  If an outer transaction catches the exception, its unrelated prior work
  remains intact; no partial rows from the failed call remain.
- Reject nonfinite input values. Flag invalid legacy stored numerics and
  conflicting legacy hashes without repairing or deleting originals.

The existing return count still means accepted input rows, not newly inserted
rows. No schema, table, index or migration changes are required. No correction
CLI, automatic version increment or trust promotion is introduced. Legitimate
changes must use an explicit new version with separately evidenced timing;
the writer cannot authenticate the claimed publication/availability time.

## Verification

- 26 new cases cover material conflicts, repeat ingestion, in-call conflicts,
  finite values, legacy invalid/conflicting rows, explicit revisions and PIT
  visibility, concurrent independent connections, nested transaction recovery,
  and actual SQLite insertion failure.
- Full pytest: 808 passed, 6 skipped.
- Ruff, mypy (218 source/script files), governance and whitespace checks pass.
- Tests use temporary databases and fixtures only; no operational or
  exploratory database is rewritten. No provider network calls were made.
- Paper Trading, Broker, Execution, Portfolio and Notification remain unchanged.
- No commit or push performed; thirteen continuation slices remain local.

## Remaining Gates

This repairs future fact writes, not historical data quality. Audit existing
facts separately before use; no old record becomes verified after upgrading
code. Reviewed metric/unit/period/consolidation/industry mappings, original
numeric-revision evidence, status/universe/action continuity and a real
validated research chain remain open. Native financial snapshots still must
not become eligible fundamentals by passing numeric parsing alone.

Next bounded work remains source-evidenced canonical mapping for a small
financial subset. No user credential or broker action is needed for this
repository repair. Review accumulated local changes before a separate commit
and remote synchronization.
