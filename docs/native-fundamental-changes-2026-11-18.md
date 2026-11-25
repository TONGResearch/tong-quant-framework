# Retained Native Fundamental Changes

Work package: WP-LAUNCH-001. Ready, not accepted. Adds source-observation change
context to the MSFT continuous-research loop, not qualified business analysis or
holding decisions. Native LOW/retrieval_time evidence is not canonical accounting.

## Runnable Increment

November 24 release-review follow-up rejects UTC conversion overflow at either
cutoff with ValueError before original source reads. It shares the equity change
entry's sanitized-input boundary; it does not clamp dates, select nearby evidence,
change accepted output/versions or qualify native financial facts. Four direct
native cases and the combined CLI mode cases cover both datetime range edges.

`read_native_fundamental_change_digest` reconstructs two explicitly dated retained
US/HK/MY Yahoo annual receipts through the existing native financial input factory.
The factory checks original bytes, registry, batch and normalized payload; the
new consumer rechecks typed subject/market/actual UTC context. It does not accept
caller JSON or promote a rehashed caller claim into source authentication.

The existing equity change API optionally accepts
`maximum_native_capture_age_seconds`. A positive integer opts into v3 context;
None/omission leaves existing v1 daily or v2 weekly/monthly output exact. CLI uses
`--max-native-capture-age-seconds`. Both native-only and period+native modes remain
read-only, offline and exit 2; this is not readiness or trade success.

Example on original retained evidence, not current-market analysis:

```sh
.venv/bin/python scripts/inspect_equity_changes.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT \
  --previous-as-of 2026-10-27T04:20:54+00:00 \
  --as-of 2026-10-27T04:20:55+00:00 \
  --max-observation-age-seconds 604800 \
  --max-native-capture-age-seconds 3600 --with-period-context
```

Limits in examples are illustrative, not approved production TTLs. Capture age is
not financial period age, filing/publication age or current-interim completeness.
Per-metric period age remains separately labeled. No capture, scheduler, worker,
notification, schema/dependency, shared provider/normalization or execution change.

## Identity And Semantics

Both native reads share one SQLite snapshot. In the combined path, both price
reads and both native reads share the existing outer transaction and the exact
same store/artifact root. No implicit cross-database/root search or fallback.
Price and native component failure states remain separate: good prices cannot
repair missing financial evidence, and native record visibility cannot repair
unavailable prices. Root qualified fundamental comparison remains NOT_ASSESSED.

Compact side receipts retain original native input/raw hashes, capture identity,
UTC availability, explicit capture age/freshness, reported currency labels, seven
latest native records and unassessed fields. Missing/failed/uninspectable source
inventories use null counts. A verified empty native response has zero observed
rows and an explicit no_observations blocker, never zero financial amounts.

Comparison states deliberately describe records, not economics:

- RETAINED_NATIVE_CONTENT_IDENTICAL/DIFFERENT compare the entire observed row
  multiset. Capture availability and row ordering are provenance, not native
  content. Historical changes cannot be hidden by identical latest records.
  Addition/removal counts refer to source rows, including replaced values, not
  counts of filings, business events or new financial periods.
- Each metric separately reports same-period native value identical/changed,
  numeric representation changed, period label advanced/regressed, incompatible
  labels or NOT_COMPARABLE. No amount delta, growth percentage, valuation or
  cross-period arithmetic is introduced. Zero/negative raw values are not divisors.
- Duplicate/latest-invalid/future/non-12M rows cannot fall back to an older good
  period. Partial captures retain per-metric blockers; identical partial source
  content does not certify the unavailable metrics or the issuer's condition.
- Latest source failure, ambiguous/tampered evidence, missing captures or caller
  capture-age failures block comparison. Publication dates, issuer revisions,
  exact flow periods, scope, units and accounting comparability remain unverified.

Same end-date, 12M, currency and unit labels permit descriptive record comparison
only. A changed value is not proof of an issuer restatement; identical values are
not unchanged business or safe holding. No sector classification is inferred
(the existing wrapper uses unknown). All financial/investment scoring, source/PIT,
validation, replay, holding, execution and official-report authorities stay false.

## Verification

### November 25 Retained Failure/Recovery Sequence

Six added integration regressions exercise US/HK/MY fixtures with either a price
capture failure or a native-financial capture failure, followed by an explicitly
ingested successful receipt. They use the existing combined daily/weekly/monthly
and native reader, not a new recovery worker or strategy. They characterize
existing behavior; no runtime repair or new production freshness policy is claimed.

- The failed latest receipt cannot be replaced by an older successful receipt.
  The other component remains separately observable, not a substitute for it.
  Its exact evidence ID is pinned through the fixture's failed ingestion batch;
  provider failure status is checked on both failed sides. Native failures also
  require source_bound=True, distinguishing retained failure from generic rejection.
- After the new receipt, re-reading the earlier explicit cutoffs reproduces the
  entire failed digest exactly. Recovery does not rewrite historical observations.
- Comparing a failed previous cutoff with a recovered current cutoff remains
  NOT_COMPARABLE for that component, while retaining the new current receipt.
- Comparing the earlier good capture with the new same-content capture observes
  a changed capture identity, not a new market row or a financial improvement.
- All source/PIT/holding/execution authorities remain false across the root,
  native context and period context. No ResearchReport, Signal or FundamentalFact
  is created; database/artifact/committed-WAL byte pins stay exact during reads.

The root comparison_status describes prices only. In particular,
NO_NEW_PRICE_OBSERVATIONS can coexist with a NOT_COMPARABLE native context; it
is not an all-inputs-healthy flag. The root fundamental comparison remains
NOT_ASSESSED and holding method NOT_VALIDATED after a successful retained read.
Synthetic capture times and long fixture age limits do not qualify actual
source freshness, automatic retry, job recovery, market sessions or accounting.
No private source, holdings or live provider is used by these cases. Existing
source/method/OOS and controlled-refresh acceptance gates remain open.

The final related scope passes 226 tests in 71.63 seconds. A full working-tree
run passed 5333 tests, six skipped, in 471.31 seconds before the last assertion
strengthening; it collected the earlier version of these six cases. Do not call
it an exact final-candidate full-suite run. The final focused rerun includes the
strengthened assertions; runtime source is unchanged. Ruff, mypy (328 files),
all 189 governance checks and whitespace checks pass. Independent read-only
static review found that an unavailable native failure could satisfy generic
rejection assertions; the batch-ID/status/source-bound checks above close that
coverage gap. Static follow-up reports no further scoped actionable finding; it
ran no tests and did not inspect real sources or grant publication approval.

The pre-existing academic handoff stays intact. These mixed working-tree checks
cannot replace isolated-candidate verification before reviewed GitHub publication.
No test record is added to Git, and no commit/push or default change occurred.

### Earlier Verification Records

Focused tests cover three markets, deterministic copied-source bindings, original
default modes, same-capture/recapture/order invariance, latest and historical
changes, currency/period labels, duplicates/missing/invalid/future rows, zero and
negative values, stale/failed/tampered/ambiguous/empty states, actual UTC/DST,
age boundaries, exact context, read-only guards, independent-writer snapshots,
nonempty committed WAL/content preservation and sanitized CLI failures. The
combined component-boundary test writes after the second price read but before
the first native read, to distinguish one outer snapshot from two separate ones.
Synthetic long price-age limits are not production policies.

Six retained real v1/v2 comparisons match a frozen pre-slice implementation:
source SHA256 dd4ddbe578e02620769dda4148230a54123699445d2fa472001008678c0fd71d.
At the original October 27 04:20:54/55 UTC cutoffs, v3 repeats exactly for MSFT,
Tencent and Maybank (25563-25669 JSON bytes). Each source still has 28 native
observations and seven parseable latest records; the same selected capture is
not new business evidence. Fifty-four pinned existing DB/artifact/WAL files keep
exact hashes. No network, fresh data, independent confirmation or real DB data
writes occurred. Read-only SQLite may create empty coordination sidecars; this
is not a claim of zero filesystem metadata effects.

383 focused tests pass in 70.30 seconds, including 96 new native-change regressions
and the existing daily, period and native-source suites. Independent read-only AI
review found no confirmed implementation defect and requested cross-component
transaction, native-only/invalid CLI and one-microsecond age-boundary coverage.
Those tests were added; static re-review confirmed closure with no further
actionable issue. The reviewer did not run suites, inspect real data or independently
verify the frozen-source origin/54-file rehearsal. Working-tree checks include
earlier pending work and are not
isolated exact-candidate release checks or universal source/secret certification.

Final stable working-tree pytest: **4624 passed / 6 skipped**, 451.45 seconds.
Ruff, mypy (322 files), governance (185 checks), whitespace and scoped known-pattern
privacy/disabled-default checks pass. All 482 tracked/new Python/config inputs
retain the same before/after fingerprint:
eb769c55090fc59c0ba4789e3c88a53cef2589b1b7cd04dbdda31c3167cc43ad.
Nineteen pending code/doc/config paths include sixteen pre-existing dirty paths;
earlier work is preserved, not independently certified by this slice. The index
remains empty. No private holdings, database, raw artifacts, logs, cache or IDE
outputs were added to Git. Exact isolated candidate checks/review remain required
before a future reviewed sync; no commit or push occurred this turn.

## Remaining Acceptance

Qualified filing-backed period/definition/revision comparison, independently
reviewed freshness/update/recovery and actual predeclared method/OOS evidence
remain open. Native observations cannot stand in for admitted Financial facts or
thesis outcomes. No owner holdings/risk details enter Git. 271 undefined terms
and seven-plus-one remain deferred; no owner action is required for this bounded
increment. PIT UNSUITABLE, production NOT_READY, execution/notifications disabled.
No commit/push, broker/Paper or trading change; the continuous loop is not accepted.
