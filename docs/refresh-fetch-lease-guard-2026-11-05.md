# Committed Fetch Lease Guard

WP-LAUNCH-001 implements SQLiteRefreshRepository.validate_fetch_lease. This is
one read-side ownership check, not a worker, resource lock or capture authority.
No existing ingestion/CLI entry is wired to it in this slice. Callers must still
complete the one-shot admission and resource/cooperative-writer contract before
future download integration.

## Contract

The new method requires a typed RefreshLease, the exact current job generation,
worker and nonce, running job/attempt, FETCHING phase, current schema metadata
and a plan reconstructible under the current static runtime contract. Check time
in UTC with updated_at <= now < lease_expires_at. Equality at expiry is rejected;
no extension, renewal, retry or state mutation occurs. Successful checking returns
None, not a permission token, eligibility flag, receipt or Signal.

SQLiteStore.has_active_connection exposes only a context-local boolean. The fetch
guard rejects an ambient SQLiteStore-managed read snapshot OR transaction, so
it cannot mistake old snapshot values or this context's uncommitted writes for
fresh committed ownership. It then opens a separate read-only SQLiteStore and
reads metadata/job/attempt in one new snapshot. Schema metadata validation is
shared with repository construction without changing constructor behavior.

The property tracks read_snapshot/transaction, not arbitrary borrowed connections
or manually issued BEGIN statements. It is not a global writer detector.
Independent store instances and other processes can have active contexts; their
uncommitted values are not read. Callers must independently avoid network access
inside any manually managed SQL transaction; this API cannot certify that.
The guard is a committed point-in-time check, not continuous ownership. A writer
can invalidate the lease after the check. Recheck at later capture/retention/commit
handoffs; a previously successful check cannot authorize a late result.

The existing validate_live_lease method remains RETAINING-only and retains its
transaction-compatible behavior for ingestion. Do not substitute one phase guard
for the other, or force existing atomic retention code into the new fetch-side
ambient-context restriction.

## Scope Of Assurance

This check does not authenticate all migration checksums/physical schema, source
code approval, database path identity, provider permission, resource capacity,
transport bounds or original bytes. It does not reserve space, lock storage,
terminate children, initiate network calls or guarantee no other writer exists.
Database/source/deployment auditing remains a separate admission prerequisite.
Missing databases are never initialized or recreated. Error values contain no
caller identifiers; a future operational renderer must still suppress unexpected
SQLite exception text rather than logging raw errors.

No data tables, migrations, record-model versions or defaults change. Constructor
metadata checks are factored into one private helper; existing retention guards
and atomic batch association are not refactored. The SQLiteStore property does
not expose a writable connection or change transaction ownership.

## Test Evidence

Synthetic temporary databases only. Coverage includes all five example scopes
(four markets plus the native-financial scope), exact expiry boundaries, UTC
equivalence, naive/backward clocks, wrong identities, terminal failure, phase
separation, current metadata/plan drift, ambient context rejection, read-only
store use, one fresh read-only connection, closure and absent-DB non-creation.

Real child processes independently change a cached parent's attempt to RETAINING,
expire it, or fail/retry into generation two. The parent guard rejects the old
claim; only the newly committed current fetching lease can pass. These are local
ledger/fencing tests, not provider observations or crash-safe storage acceptance.

31 new cases / 104 focused checks pass. Full working-tree suite: **3307 passed /
6 skipped**, 161.37 seconds. Ruff and mypy (306 files), governance (158 checks),
git diff --check and scoped credential/dependency review pass. Six opt-in network
skips are not provider availability evidence. Both retained sample DB hashes
remain unchanged. These working-tree checks do not qualify the old or a future
repaired GitHub candidate for publication.

## Remaining Work

Next: cooperative resource ownership and descriptor/fork recovery tests, then
bounded capture-once integration with current capacity checks, actual size/time/
staging/DB budgets and exact receipts. No collector, schedule, checkpoint advance
or automatic re-claim exists from this guard. Legacy unleased ingestion remains
outside this check. The GitHub candidate repair/review blocker remains separate;
main-worktree tests are not exact repaired-candidate release validation.

PIT UNSUITABLE, production NOT_READY, R1-R6 partial; WP-LAUNCH-001 stays ready/not
accepted. Execution/notification defaults remain disabled. No trading functionality,
real archive scan, provider call, user-DB migration, commit or push is introduced.
