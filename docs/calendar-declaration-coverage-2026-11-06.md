# Calendar Declaration Coverage

## November 15 Annual Follow-Up

Explicit include_yearly=True adds calendar-declaration-coverage-v2-optional-year,
year comparisons, full original Bar content hash/count and closed investment
scoring authority. Default v1 week/month output is unchanged. The same strict
date/version/UTC rules apply to years: leap days and market-local year boundaries
matter, unended years withhold percentages, and even 100 percent is conditional
declaration agreement, never source/session/PIT qualification.

Existing --calendar-coverage can now accompany --long-horizon or
--multi-timeframe without also requiring --calendar-periods. These long modes
read declarations from the first year start through the local cutoff in the same
price SQL snapshot. Without a long mode, the original --calendar-periods
requirement and v1 scope remain. No new calendar source, automatic copying,
weekday/holiday inference, database/schema change or capture mode is introduced.

Only this new v2 component plus long observations enables the v5-calendar-gaps
Chinese note. It checks version, cutoff, market/subject, original daily hash/count,
calendar parent hash, unknown legacy trust/precision, future availability and
closed authorities. It summarizes unknown declarations, missing observations on
declared opens, and closed-date contradictions separately. Legacy v1 components
remain on their original display path. No extra grade or investment score follows.

The real retained MSFT price database has zero calendar declarations in the
queried interval. The ended 2023/2024/2025 buckets therefore have respectively
365/366/365 unknown dates; the unended 2026 bucket has 319 through the pinned
November 15 local cutoff. All annual percentages remain null. This is a scoped
database inventory, not provider-wide absence, zero trading days, zero price
coverage or proof that the observed prices are false.

Two new extended JSON runs repeat exactly. Original DB and prior v2 JSON/v4 note
hashes remain unchanged. New private calendar-coverage-analysis.json and
calendar-coverage-note.zh-CN.md are ignored, mode 600, not a Git/encrypted backup.
Coverage receipt: 22594b31d6dccfe46c418e178cfaa6fe91f9968ff611fb54bef122dcba6186c3.
Thirty new synthetic/CLI cases cover annual boundaries, leap years, all distinct
gaps/adverse observations, future calendar data, source-context tampering, missing
prices, three overseas markets and old-output preservation. Full pytest: 4028
passed / 6 skipped in 397.50 seconds; Ruff, mypy (317 files), governance (175
checks), scoped boundary/default/privacy and whitespace checks pass. These are
mixed-workspace checks, not an isolated release or independent source approval.
No financial method, action/adjustment basis or trading gate is
qualified; next is retained-source/venue/operative-calendar integration and
independent review, not filling unknown dates with assumed weekdays.

## Scope And Remaining Source Gate

November 6, existing ready WP-LAUNCH-001 / US delivery U3. A new pure diagnostic
compares original visible daily observations with supplied TradingSession dates.
It complements the calendar-period-observations-v1 receipt without replacing its
OHLCV, the legacy Technical score or historical records. The new derived version
is calendar-declaration-coverage-v1. Framework/schema/migration/defaults do not
change. PIT remains UNSUITABLE and production NOT_READY; no trading is enabled.

This is a coverage comparison, not a qualified exchange calendar. The existing
TradingSession contract lacks exchange identity, independent trust assessment,
original publication precision and retained-source binding. Expose UNKNOWN trust
and UNKNOWN availability precision rather than inventing them from a source name.
A declared available_at is checked against cutoff, not independently verified.
Future qualified calendar ingestion remains a separate source/admission task.

## Comparison Semantics

- Reuse calendar_period_diagnostics for full original daily validation, revisions,
  market-local date boundaries, partial periods and latest-suspension blocks.
- Revalidate supplied calendar rows: explicit market/date/bool/source, aware
  availability, no availability after cutoff, bounded tuple of at most 20,000.
  Reject conflicting equal-time revisions and implicit source merging; select
  the latest actual-UTC visible revision, retaining all rows in the input hash.
- Every compared civil date needs an explicit open or closed declaration.
  Absent weekends/holidays remain unknown. No weekday or exchange rule is assumed.
- Compare only through the market-local cutoff date. Known future schedule dates
  stay listed separately and cannot complete an unended week/month.
- Distinguish unknown calendar dates, missing observations on declared open dates,
  observed prices on declared closed dates and suspended open-date observations.
  Preserve all applicable flags, even when one primary status has precedence.
- Suspensions are adverse observations, not lost data. They count as observed
  dates but cannot authorize a candle or current technical calculation. Latest
  suspension blocks comparable periods; no earlier active-price fallback.
- Compute observed-open-date coverage only for ended periods with every date
  declared, no closed-date contradiction, and at least one declared open date.
  No declared opens gives null, not a fabricated 100 percent. With partial/missing
  calendars or unended periods, percentages stay null. Missing open observations
  may yield a conditional percentage such as 80, never an automatic source grade.
- DATES_MATCH_UNVERIFIED or 100 percent means agreement with supplied declarations
  only. Session completeness, source adjustment basis, scoring, historical replay,
  validation and execution authorities remain false. Pre-listing and other gaps
  require lifecycle interpretation; do not silently discard those instruments.

The new hash binds parent calendar receipt, all calendar rows, source labels,
latest availability, actual UTC cutoff, version, flags and comparisons. Exact
hashes do not authenticate source truth. This contract uses existing domain
models and repositories, not a parallel calendar or research-report model.

## Read-Only CLI

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT \
  --as-of 2026-10-27T15:25:57.208239+00:00 \
  --calendar-periods --calendar-coverage
```

The new flag requires --calendar-periods, which already rejects --capture.
Calendar reads use MarketDataService over the same price-database SQL snapshot,
not an automatically chosen second database or fresh network request. Read from
the earliest displayed period through the local cutoff. When no comparable price
period exists, no calendar query is made; this is not provider-wide absence.
Empty/partial calendars stay visible. Existing no-flag and calendar-only outputs
remain unchanged. Optional SEC/review combined hashes bind the new receipt when
requested. Exit code 2 still means an unqualified diagnostic, not deployability.

## Database Repair

SQLite's calendar reader previously used bool(row["is_open"]), silently turning
2, negative numbers, nonzero fractions or nonempty text into an open date. It now
accepts only integer 0/1 and fails closed otherwise. Calendar writes prevalidate
all input rows and require an actual Python bool before int conversion, so a bad
row cannot be truncated or leave an earlier row in the batch persisted.
Valid calendar records are unchanged. There is no schema migration, corruption
repair, historical overwrite or automatic source/availability qualification.
Legacy malformed rows require a separately reviewed repair, never silent coercion.

## Verification And Next Work

Synthetic tests cover four market-local date systems, absent weekends, missing
calendar versus missing prices, closed-date contradictions, suspension retention,
zero-open/current periods, revision ordering including DST folds, invalid/future/
sensitive inputs, deterministic hashes and source separation. CLI tests cover
US/HK/Malaysia, read-only repeatability, opt-in compatibility and a concurrent
calendar writer: one display keeps the price/calendar snapshot, while the next
display sees the committed declaration. Corrupt SQLite flags and lossy write
conversion fail closed without modifying test databases. Synthetic all-open
fixtures are plumbing examples, not real exchange schedules or source evidence.

The retained October 27 MSFT sample still has 706 observations, but no visible US
calendar rows in its requested database/window: all 148 weekly and 34 monthly
comparisons retain CALENDAR_DATES_MISSING, including any additional unended-period
flags. All compared dates remain unknown; the diagnostic cannot improve source/
PIT qualification. Repeated coverage hash is
483ee5a139be031b7b3e430121b19798e7e5ff2dd484c3fec2e323529fe1bf90;
with the explicit SEC example options, the combined display hash is
cf8265540e6ee8f03b6a2d6d98e8d20a2a00c1d24785e0ce35a9e7d79c42945f.
Both real database byte hashes remain unchanged. The previous no-calendar SEC v1
and calendar-only hashes remain exact. Final quality totals are recorded in
PROJECT_STATUS. Full pytest: 3577 passed / 6 skipped, 251.68 seconds, including
45 new cases. Ruff, mypy (310 files), governance (165 checks), scoped import/
credential review and git diff --check pass. Six default opt-in network skips
are not real source validation. Mixed-worktree checks are not isolated-candidate
validation. No commit or push was made; old candidate packaging/review gates remain.

Next: obtain source-bound US exchange calendar evidence with explicit scope,
availability, trust and independent review; qualify corporate-action/price basis;
then admit separately versioned period-trend policy and run actual research/
out-of-sample validation. This increment does not complete U3, financial-sector
policy, source calibration, real screened research or deployable release review.
