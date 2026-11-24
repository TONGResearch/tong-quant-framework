# Optional Weekly And Monthly Change Context

Work package: WP-LAUNCH-001. Ready, not accepted. Extends the existing read-only
daily change digest, not a second official report or a completed monitoring loop.

## Runnable Increment

`scripts/inspect_equity_changes.py --with-period-context` and the strict boolean
`read_equity_change_digest(include_period_context=True)` add a versioned v2
weekly/monthly context. Omission/false keeps the v1 daily document and hash exact.
No formula, calendar, raw source, database schema, dependency or default changes.
The opt-in still exits 2: descriptive, unqualified output is not readiness success.

Example using the retained rehearsal database, not today's market:

```sh
.venv/bin/python scripts/inspect_equity_changes.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT \
  --previous-as-of 2026-10-27T03:29:00+00:00 \
  --as-of 2026-10-27T03:29:01+00:00 \
  --max-observation-age-seconds 604800 --with-period-context
```

The seven-day age limit is illustrative, not an approved production/session policy.
Only existing US/HK/MY source snapshots are consumed. No network, capture, worker,
notification, owner holdings, accounting admission, Paper or broker access is added.

## Comparison Rules

The original two source reads remain in one SQLite transaction. Period calculations
reuse those exact immutable snapshots, not a second query or supplied report JSON.
Existing long_horizon_diagnostics/calendar_period_diagnostics recompute receipts,
source-content/calendar/input hashes and SMA/MACD/KDJ on calendar-ended observations.
Weekly SMA periods are 13/26/52; monthly 6/12/24; existing technical parameters
remain research defaults, not optimized or approved trading rules.

Per-side compact summaries retain original hashes/parameters/cutoff, usable count,
last ended start/close, actual source dates/availability/lag, open-period starts,
gap counts/examples, available indicator values and their individual statuses.
No full duplicated daily or calendar series is emitted. Missing source inventories
have null period counts, not zero ended weeks/months. No older-good fallback.

- SAME_ENDED_PERIOD: compare only same-frequency observations with the same ended
  period. Available indicators may be unchanged/changed; insufficient warmup is
  NOT_EVALUATED even if both values are null.
- PERIOD_END_ADVANCED: the local calendar boundary passed. This can occur with no
  new price row or new capture. Different ended-period indicators are NOT_ALIGNED,
  not improved/deteriorated or same-period changes. Unavailable values remain
  NOT_EVALUATED. The calendar-ended count is not a new market-observation count.
- NOT_COMPARABLE: inherit every daily source/freshness/parameter/revision blocker
  and retain missing/no-ended-period/period-gap/suspension states. No indicator
  change table or assessed new-ended count. A valid latest period cannot repair
  an earlier missing ended period by stitching around it.

Open periods do not enter indicators. Market-local midnight boundaries, not a
fixed UTC week or an assumed Friday close, determine calendar end. A US DST
fallback week can span 169 UTC hours. Ended does not mean verified complete
exchange candles: within-period coverage and first-period truncation remain
unknown. Unknown dates, suspensions, splits/dividends and tradability are not
resolved by this comparison. Yearly diagnostics are recomputed internally by the
existing helper but are not exposed as a yearly change feature in this slice.

Cross-timeframe decision remains NOT_EVALUATED. Source/PIT/holding/execution
authority remains false; root score/validation/replay flags stay false. Multiple
timeframes and related indicators are correlated, never independent votes or
extra confidence. Fundamentals remain NOT_ASSESSED, holding method NOT_VALIDATED.

## Verification

206 focused tests pass, including 35 new opt-in regressions and the existing daily,
long-horizon and calendar-period suites. The focused scope covers opt-in
determinism/binding, US/HK/MY exact weekly/monthly rollovers, US DST, unchanged
closed indicators when only an open-period row is added, unavailable/ambiguous/
tampered/stale inputs, revisions/parameters/currency changes, historical gaps,
warmup, invalid opt-in, equivalent UTC instants, independent-writer snapshot
consistency, nonempty committed WAL/content preservation and the offline CLI.
Synthetic daily fixtures include calendar dates, not verified exchange sessions;
long age limits are test admission only. Latest suspension with retained rows also
keeps inventory counts null. Frozen pre-slice source SHA256 is
9f0375ef62d1ba7a6e0668e22f95e598bd134bbdab0e88aa6913d9a0425e6f92;
three fixed synthetic API/CLI byte hashes repeat across independent temporary DBs
and constrain default/explicit-false API and three-market default CLI tests.
Full checks/review are recorded below.

Six real retained October 27 comparisons preserve exact v1 JSON against a frozen
copy of the pre-slice daily implementation. Repeated v2 JSON is exact (12802-17202
bytes), and 54 pinned existing DB/artifact/WAL files retain their hashes. MSFT's
03:28/03:29 pair remains noncomparable at both frequencies because the earlier
price inputs were blocked. Later same-capture MSFT and both Tencent/Maybank pairs
report SAME_ENDED_PERIOD, not business stability or safe holdings. No fresh capture,
current quote, independent confirmation or source/PIT upgrade occurred. Read-only
SQLite may create empty coordination sidecars; this is not a zero-metadata claim.

Working-tree tests include earlier pending work; they are not isolated exact-tree
release checks or broad secret/source certification. No commit or push this turn.

Independent read-only AI review found a latest-suspension inventory falsely marked
evaluated with zero counts, plus a v1 baseline test that only compared current
code to itself. The inventory now follows the underlying diagnostic status;
latest suspension preserves retained rows but inventory counts remain null.
Fixed pre-slice synthetic API/CLI byte hashes close the compatibility coverage
gap. Re-review checked 18 pure-memory state cases across three markets and found
no further actionable issue. The reviewer did not independently inspect the real
54-file rehearsal/frozen-source origin or run focused/full suites. This is scoped
engineering review, not source/PIT, strategy or production qualification.

Final stable working-tree pytest: **4528 passed / 6 skipped**, 519.42 seconds.
Ruff, mypy (321 files), governance (184 checks), whitespace and scoped known-pattern
privacy/disabled-default checks pass. All 480 tracked/new Python/config inputs
retain the same before/after fingerprint:
87b40a535e38496a4bb05474c384838ecb7f98c3cd6f7e2624336e2f62582fe9.
Sixteen pending code/doc/config paths include fourteen pre-existing dirty paths;
earlier work is preserved, not independently certified by this slice. The index
remains empty; no private holdings, database, raw artifacts, cache, logs or IDE
outputs were added to Git. Exact isolated-candidate checks/review are still
required before a later reviewed sync; no commit or push occurred this turn.

## Next Step

Next add source-bound fundamental changes with explicit period/definition/revision
compatibility and unassessed accounting gaps, followed by reviewed update/recovery
and actual predeclared method/OOS evidence. Do not infer hold/add/sell thresholds
or migrate deferred 271/seven-plus-one definitions. No owner action is needed for
this bounded increment. PIT UNSUITABLE, production NOT_READY, execution and
notifications disabled; continuous-loop and WP-LAUNCH acceptance remain open.
