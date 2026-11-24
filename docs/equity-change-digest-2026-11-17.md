# Read-Only Daily Equity Change Digest

Work package: WP-LAUNCH-001. Ready, not accepted. The first bounded increment
of the owner-approved MSFT continuous-research loop is now runnable. This is
a daily price/technical comparison foundation, not the completed recurring loop.

## Contract And Entry

November 24 release-review repair: either explicit cutoff whose UTC conversion
falls outside Python's datetime range is rejected as a sanitized ValueError
before source reads. The CLI returns its existing generic error and exit 2
without echoing the date, a path or traceback, including period/native opt-ins.
Twenty-four added API/CLI cases cover both cutoffs and both UTC bounds across
the price and native entry points. Accepted-date calculations, output versions,
hash semantics, data/source qualification and disabled authorities stay unchanged.

`read_equity_change_digest` reads two explicitly dated retained US/HK/MY Yahoo
equity snapshots in one read-only SQLite transaction. Each original receipt and
full technical output is recomputed and bound using the existing reader and
technical binding. No arbitrary caller JSON, supplied hash or cached label is
accepted as evidence. Actual UTC ordering handles equivalent offsets and DST.
The caller must provide a positive integer maximum observation age; this is not
an independently reviewed exchange-session or production freshness policy.

Offline example using the existing October 27 retained rehearsal database:

```sh
.venv/bin/python scripts/inspect_equity_changes.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT \
  --previous-as-of 2026-10-27T03:28:00+00:00 \
  --as-of 2026-10-27T03:29:00+00:00 \
  --max-observation-age-seconds 604800
```

The seven-day limit is illustrative, not approved freshness. JSON is descriptive
research information. Exit code is always 2, including a successful comparison;
it must not serve as a green readiness or trading signal. There is no capture,
scheduler, notification, official ResearchReport, database initialization or order.
The source database and original artifacts must already exist. Read-only SQLite
may create empty WAL/SHM coordination sidecars; database/artifact bytes and existing
committed WAL frames are pinned, not a claim of zero filesystem metadata changes.

## Interpretation

- NEW_PRICE_OBSERVATIONS: comparable source history has appended observed rows.
  Native-close delta is not total return, investment return or a trading signal.
- NO_NEW_PRICE_OBSERVATIONS: no new market rows, even if retrieval was repeated.
  It is not evidence that the business is unchanged or a position is safe.
- NOT_COMPARABLE: retain failed, stale, missing, ambiguous, tampered or incompatible
  inputs and exact reasons. No older-good fallback or favorable numeric delta.
- Overlap OHLCV revisions, removed/filled historical coverage, source/currency/
  exchange/price-basis changes and changed technical parameters block comparison.
  Uninspected series counts are null, not zero. Count inspection is separately
  labeled and does not mean the economic comparison was admitted.
- Sixteen daily technical fields retain both observations. Missing warmup is
  NOT_EVALUATED, including empty triple-average/Granville events. Once fully
  warmed, a genuinely empty event set can be UNCHANGED. Indicators are correlated
  observations, not independent votes or validated confidence.

All source/PIT, score, validation, historical replay, holding management and
execution authority flags remain false. Fundamentals and multi-timeframe changes
are NOT_ASSESSED; holding method is NOT_VALIDATED. A-share ingestion is not part
of this entry. Existing multi-timeframe diagnostics remain separate.

## Verification

65 focused offline tests pass: US/HK/MY, deterministic receipts and output, compact
JSON, missing/failure/ambiguity/tamper/staleness, unchanged recaptures, source and
parameter differences, historical revisions/coverage, warmup boundaries, UTC/DST,
reader identity rejection, one transaction despite an independent writer, CLI
failure sanitization and original DB/artifact/nonempty committed WAL preservation.
The fixture's 400/1000-day age limits are synthetic, not operational policies.

Retained-data rehearsal uses only the original October 27 03:28/03:29 UTC cutoffs.
MSFT remains NOT_COMPARABLE: earlier current_session_completion_unverified versus
later observed_unqualified is not a favorable market change. Tencent and Maybank
both report NO_NEW_PRICE_OBSERVATIONS. Later reads of each same selected capture
also report no new rows. JSON repeats exactly (6676-6793 bytes), and 54 pinned
existing files retain exact hashes. No network, fresh quote/capture or real DB
data writes occurred; this is old-source compatibility, not current-stock analysis.

Independent read-only AI review found insufficient-warmup empty events incorrectly
marked unchanged, an overstated no-state-change error message, and a nonempty-WAL
coverage gap. All three are repaired with targeted tests. Read-only re-review
confirmed the closures and found no additional actionable issue in scope; the
reviewer did not run the suite or inspect real data independently.

Final stable working-tree pytest: **4493 passed / 6 skipped**, 442.13 seconds.
Ruff, mypy (321 files), governance (183 checks), whitespace and scoped known-pattern
privacy/disabled-default checks pass. All 479 tracked/new Python/config inputs
retain the same before/after fingerprint:
2e9a9f39e794c112a6285c00380bd4b3af40256d7ddce47ac883aa993515fdc8.
Fourteen pending code/doc/config paths include nine pre-existing dirty paths;
they are preserved, not independently certified by this slice. The index remains
empty. No private holdings, database, logs, cache or artifacts were added to Git.
These mixed working-tree tests cannot replace isolated exact-candidate checks/
review required before sync, nor certify all secret patterns or data/strategy quality.

## Next Acceptance And Owner Intent

Next integrate explicitly ended weekly/monthly context and source-bound fundamental
changes; preserve unequal periods, unqualified accounting and update failure as
unassessed. Then reviewed refresh/recovery and predeclared method/OOS evidence.
Do not extend generic infrastructure without a concrete loop blocker.

Strategy and horizon come first. Fundamental suitability may differ for short-term
and long-term research, but data integrity, tradability, validation and portfolio
risk gates cannot be waived. Distinguish market/industry/instrument and large/small
trends; a regime is a contextual variable, not a global all-or-nothing switch.
Institutional-flow observations support hypotheses, never proof of an actor's
identity or intention. This documents research direction, not a runtime policy
relaxation. Do not switch a losing trade's stated horizon after the fact.
Owner risk preferences remain private; any future policy needs an explicit
measurement basis, not an inferred stop percentage. 271 undefined terms and
seven-plus-one remain deferred. No owner action is required for this increment.

PIT UNSUITABLE, production NOT_READY, execution/notifications disabled. No schema,
dependency, framework-default, broker, Paper or trading change; no commit or push.
