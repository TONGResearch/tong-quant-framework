# Nasdaq Explicit Calendar Source

## November 16 Comparison Display Repair

The real strict-price-age note showed raw closed_date_observation_conflict=False
for dates lacking usable prices or lying in the future. This was not a source
or session grant, but the table label could imply an evaluated absence of risk.
Presentation-only equity-diagnostic-note-v7-nasdaq-comparison-context now replaces
that raw boolean column with distinct states: future/unavailable/out-of-span
unassessed, missing intraday evidence for early closes, candidate date conflict,
or no observed price on that date with an explicit non-completeness warning.

The renderer rejects contradictory/nonboolean comparison flags even with valid
recomputed hashes: an observed date cannot be outside the observation span,
unknown observations cannot assert inside-span coverage, and the conflict flag
must agree with the full-day closure and observed/future states. Hashes are not
source authentication; callers must still use the original retained readers.

Source, age and nasdaq-price-source-review-v1 receipts remain unchanged, including
their original false flags and canonical hashes. Legacy v6 constant/stored notes
remain; newly rendered Nasdaq notes use prospective v7. Default notes without
this optional source component, technical arithmetic and all authority gates
remain unchanged. No schema, source normalization or calendar projection change.

Fifteen new cases cover the display states and rehashed contradictions; focused
tests total 63 passed. Full pytest: 4091 passed / 6 skipped in 402.93 seconds;
Ruff, mypy (318 files), governance (175 checks), scoped import/default/privacy
and whitespace checks pass. These mixed-workspace checks are not source/method
or isolated release admission. Real offline rendering preserves 11 old files
and exact no-Nasdaq v4/v5 notes. Three
new ignored mode-600 *-v7.zh-CN.md files are in the existing private refresh
directory. Strict-price output contains eight unavailable past comparisons and
four future unassessed dates, no raw false-as-success column. Fresh-source output
has eight unverified date absences and four future plans, not complete sessions.
No network, source/PIT/score/holding admission, commit or push.

## November 16 Real Refresh Rehearsal

The existing capture entry point fetched the fixed public HTTPS source to a new
ignored private root data/processed/nasdaq-calendar-20261116. It did not overwrite
the November 7 source or append new records to an old decision database. Capture
available_at is 2026-11-15T16:39:02.668051+00:00 (November 16 in Malaysia), and
read cutoff 2026-11-15T16:39:02.720182+00:00. Twelve explicit declarations are
reconstructed from retained original bytes, with LOW/retrieval_time unchanged.

Old body hash: 59ff10760ec05840b655c0a60314b430d89e8b2eafde70a32a1b29e82e3dfa86.
New body hash: cb4aa27a79a50fe3db6c8be588ae405fc7d870711ec7f21226998a53583d2b52.
The complete parsed declaration lists are equal, not merely their row counts.
Changed response bytes are not evidence of changed trading rules. Repeated
captures of one provider do not establish independent provider consistency.

Private data/processed/msft-calendar-refresh-20261116 contains the deterministic
JSON and Chinese notes for three cases plus rehearsal.json, all mode 600:

| Case | Calendar Source | Prices | Result |
| --- | --- | --- | --- |
| old-cutoff | missing/BLOCKED_INPUT | 971 rows, UNASSESSED | New capture is not visible at the old cutoff |
| updated-source | WITHIN_CONFIGURED_LIMIT | 971 rows, UNASSESSED | 12 declarations co-reviewed, no source/session admission |
| strict-price-age | WITHIN_CONFIGURED_LIMIT | STALE, zero admitted rows | Fresh calendar cannot rejuvenate old prices |

The last two cases use the capture read cutoff above. The first uses the old
2026-11-15T09:13:45.007947+00:00 cutoff and exactly reproduces the earlier base
document after removing the explicitly new source component. Each case repeated
byte-for-byte. Eight pinned DB/WAL/report/capture files retain exact hashes;
their inventory is in the private rehearsal.json. Source and price age limits
of 86400 seconds are illustrative, not an approved production policy. Weekend
wall-clock age alone cannot establish a missed trading-session update or source
failure; do not rewrite timestamps or relax trust to make that example pass.

Three new CLI regressions cover multi-version source refresh, old-cutoff byte
equality, independent price age, newest failure without favorable fallback and
read-side immutability. Full pytest: 4076 passed / 6 skipped in 404.21 seconds;
Ruff, mypy (318 files), governance (175 checks), whitespace and scoped disabled-
default/privacy checks pass. This is mixed-workspace engineering verification,
not isolated release or independent data/method admission. Six skipped opt-in
network tests are not source evidence; the real capture above is separate.
No runtime code, source/model version, migration, default or dependency changes.
No existing capture/raw bytes were replaced, no automatic scheduler was installed,
and no calendar completeness, PIT, scoring or trading authority was granted.
Next: explicit source-update policy and qualified operative/session-aware
freshness, alongside independent source and combined-method validation.

## November 15 Explicit Equity Co-Review

The overseas single-equity CLI now accepts --nasdaq-calendar-database,
--nasdaq-calendar-artifact-root, --nasdaq-calendar-year and
--nasdaq-max-source-age-seconds together, with mandatory --as-of, US scope and
no capture. No automatic latest-file/root selection, copying or inference.
Selecting Nasdaq does not authenticate an instrument venue or session mapping.

Application receipt nasdaq-price-source-review-v1 binds the exact price input
hash and unmodified nested source receipt. Optional v6 Chinese output rechecks
actual cutoff, source/subject identities, LOW/retrieval_time, false authorities,
exact source-age arithmetic and future-date labels. Same DB reuses the price
snapshot; separate DBs share a cutoff, not cross-store atomicity. All legacy
default JSON/notes, indicators and coverage percentages remain unchanged.

Only declarations admitted by the retained reader's explicit age check are
compared with observed price dates. Native early-close times remain intact;
future dates are not completed sessions; closed-date observations retain conflict
flags. Missing early-close price dates are not classified as gaps without
price/session/lifecycle qualification. Latest suspension blocks comparison,
never resurrecting older favorable prices. Stale/failed/future/ambiguous inputs
retain observations and limitations without an earlier favorable fallback.
No TradingSession conversion, inferred weekdays/weekends, canonical-calendar
write, coverage-percentage repair or source/PIT/score/holding authority follows.

Real offline MSFT at 2026-11-15T09:13:45.007947+00:00 repeats exactly with unchanged
DB/WAL bytes and old calendar-coverage JSON. The capture at
2026-11-06T16:19:18.502405+00:00 is 752066.505542 seconds old: STALE under the
illustrative 86400-second limit, zero current comparisons, 12 observed declarations.
This one-day limit is not an approved production TTL or proof of false content.
New ignored mode-600 files in data/processed/msft-review-20261115-zgzl_o5o are
nasdaq-source-analysis.json and nasdaq-source-note.zh-CN.md. Review receipt hash:
0f389bb55be0a2fde0dfbe25944263640c8852c5436410938292b79acf63a835.
No network request, source capture or canonical calendar write occurred.

Forty-five synthetic/CLI cases cover same/separate stores, deterministic hashes,
legacy equality, no calendar population, native times, future dates, stale/latest
failures/missing prices/suspension, pre-I/O option rejection and rehashed context,
authority/age tampering. Full pytest: 4073 passed / 6 skipped in 422.94 seconds.
Ruff, mypy (318 files), governance (175 checks), scoped import/default/privacy
and whitespace checks pass. Final whole-project results are in PROJECT_STATUS.
Mixed-tree checks are not independent source approval or isolated release review.
No schema/dependency/default/trading change, commit or push.

## Scope

November 7, Malaysia time, existing ready WP-LAUNCH-001 / US read-only delivery.
The provider-neutral evidence path now supports a bounded, explicit Nasdaq
calendar capture and offline reconstruction, using existing provider contracts,
artifact store, ingestion batches and SQLite repositories. No parallel domain
calendar/report model, schema migration, dependency or trading functionality.

Provider: nasdaq_calendar. Dataset: exchange_holiday_snapshot. Subject: NASDAQ:2026
(or another explicitly requested year within supported bounds, if actually on
the page). Model: nasdaq-explicit-holiday-snapshot-v1. The fixed HTTPS source is
[Nasdaq Trader's calendar](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar).

The page is a holiday/early-close schedule, not daily proof of actual openings.
Only listed declarations are parsed. Unlisted weekdays/weekends remain unknown;
no federal/bank holiday substitution, inferred regular open/close, emergency
schedule, settlement or broker-session rule. Research scope is Nasdaq equities;
do not transfer these observations to NYSE, options or other markets.

## Architecture

```text
Fixed public HTTPS URL, TLS verification, no redirects
  -> bounded raw response body / sanitized failure capture
  -> standard-library HTMLParser, explicit year/header/date/status checks
  -> original body in versioned JSON envelope + distinct body/envelope hashes
  -> ProviderNeutralIngestionService
  -> existing batches / provider evidence / artifact registry + retained bytes
  -> fixed-cutoff retained-snapshot verifier and offline reader
```

Transport uses at most two attempts, a 15-second per-attempt timeout, identity
encoding and a 2 MiB response-body bound. It follows no arbitrary URLs, renders
no page scripts, retains no response headers/cookies/credentials and emits only
bounded failure categories. Credential-shaped bodies are rejected before storage.
Original HTML is not printed or committed; source rows remain small annotations.

The parser requires the explicit equity/options schedule heading and exactly one
matching year/Holiday/Status table. Missing/duplicated tables, wrong-year pages,
invalid/duplicate dates, unsupported statuses, oversized cells and nested/script
table markup remain non-successful. Unknown supported-width rows retain native
labels and unqualified status; unsupported layout retains the original body.
No earlier favorable subset or annual-date inference is admitted. Changes to the
live page can require a separately versioned parser update, never silent repair.

Early-close declarations retain their source-local time and America/New_York
timezone rather than becoming a normal full-day is_open flag. A planned future
holiday may be observed now; its event date is not the data's availability date.
The source's actual first-publication timestamp and revision history are unknown.
All visibility begins at capture; envelope publication metadata is a conservative
capture-time bound, not proof of historical release. Current captures cannot
retroactively improve an October decision context.

## Trust And Boundaries

Capabilities remain DEGRADED, LOW trust ceiling, RETRIEVAL_TIME precision and no
historical continuity claim. Official-domain transport, parser success and hashes
are not independent truth or full-history qualification. No provider is trusted
by default; this is one retained source observation awaiting calibration/review.

No write to canonical trading_calendar, instruments, bars, signals, research
reports or scores. All calendar completeness, actual-session verification,
canonical-calendar/scoring/replay/validation/execution authorities remain false.
Framework 0.8.0, schema 0.8.3, migration 0011_refresh_ledger, UNSUITABLE PIT,
NOT_READY production and disabled execution/notifications remain unchanged.
No scheduled refresh, contract-monitor registration, resource-admission worker,
portfolio, broker, Paper Trading or order path is added.

## Manual Diagnostic Entry Point

November 8 adds an optional read-only
[source-age receipt](nasdaq-calendar-freshness-2026-11-08.md) via
`--max-source-age-seconds N`. Omission preserves this v1 output exactly and leaves
freshness UNASSESSED. The flag cannot accompany capture; no default TTL or
automatic collector is introduced. Within-limit is not source/session approval.

```sh
# Capture requires a new, explicitly chosen diagnostic database.
.venv/bin/python scripts/inspect_nasdaq_calendar.py \
  --database data/processed/nasdaq-calendar-20261107.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts --year 2026 --capture

# Offline reconstruction, same exact actual cutoff, never another download.
.venv/bin/python scripts/inspect_nasdaq_calendar.py \
  --database data/processed/nasdaq-calendar-20261107.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts --year 2026 \
  --as-of 2026-11-06T16:19:18.567608+00:00
```

The first command refuses an existing file before networking, and uses exclusive,
no-follow, private file reservation after capture to reject competing creation.
It never initializes/migrates an existing database. Failed reservation retains
the competing file unchanged. A later failure after reservation may leave a
diagnostic file; do not overwrite it automatically. This is a manual bounded
single-database diagnostic, not global resource ownership, quota reservation or
admission of the future refresh worker. Raw retention and DB are separate stores.

The capture example has already been run; repeating it against that same file
will intentionally refuse. Use the second command to inspect it. Exit code 2 is
an unqualified diagnostic, not acceptance. Public source access needs no new API
credential. Lower-level ingestion supports idempotent repeated identical input;
the CLI intentionally does not auto-append or migrate old user files.

## Real Retained Observation

The November 7 capture retained 54,628 response-body bytes and parsed 12 explicit
2026 declarations: 10 full-day closures and two early core closes. The latter
are November 27 and December 24, both source-local 13:00:00. These are schedule
statements, not proof of actual future sessions or current tradability.

- Available at: 2026-11-06T16:19:18.502405+00:00, i.e. November 7 in Malaysia.
- Read cutoff: 2026-11-06T16:19:18.567608+00:00.
- Body SHA-256: 59ff10760ec05840b655c0a60314b430d89e8b2eafde70a32a1b29e82e3dfa86.
- Receipt SHA-256: 7587663f621bcb9da28618a3aea008f7841f31c2b3ccc20692abfecc9fecf942.
- Repeated offline receipts agree. Reading at the old October 27 analysis cutoff
  reports missing/zero declarations; the new source is not backdated.
- Both existing price/SEC database byte hashes remain unchanged. New diagnostic
  DB and raw body are ignored local evidence, not GitHub code backup contents.

Synthetic tests cover source scope, strict parsing and drift, native times,
future schedule versus capture availability, idempotent retained reconstruction,
latest failure/tie/tamper/batch rejection, disabled authorities, bounded/sanitized
transport, offline CLI, exclusive new-file capture and competing file creation.
Forty-seven new synthetic cases pass; full pytest: 3624 passed / 6 skipped,
237.31 seconds. Ruff, mypy (313 files), governance (166 checks), scoped import/
credential review and git diff --check pass. Six opt-in network skips are not
real source verification; the real retained observation is documented separately
above. Mixed-tree tests are not source/strategy qualification or isolated
release-candidate review. No commit or push; existing candidate review gates persist.

## Next

The [regular-session contract](proposals/us-regular-session-calendar-v1.md) now
specifies the next source/policy/price bridge and a newly identified prospective
December hours-transition risk. It is a web-based audit/design, not source capture,
implemented schedule logic or an operative-rule grant. Preserve this v1 source.

Review regular-session weekday/range evidence separately, qualify actual exchange
scope and abnormal closures, and add historical-year source coverage without
backdating capture availability. Only then propose a provenance-preserving bridge
to period coverage. Do not flatten early closes or discard trust/precision into
legacy TradingSession to make the coverage report pass. Corroboration, price/
corporate-action truth, period-trend policy and actual strategy validation remain
open. The source is not yet on automated provider monitoring or refresh schedules.
