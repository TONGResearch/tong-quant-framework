# Calendar Week And Month Observations

## Scope

November 6, existing ready WP-LAUNCH-001 / US delivery U3. Pure calendar-bucket
OHLCV diagnostics now complement, not replace, the existing daily technical
calculations. Framework 0.8.0, schema 0.8.3 and migration head are unchanged.
PIT remains UNSUITABLE, production NOT_READY, execution/notifications disabled.
No source, scoring, strategy, validation or trading admission follows.

## Actual Gap And Contract

The official TechnicalResearchModule currently computes returns over 5 and 21
observation intervals and a configured 252-observation range. These are not true
calendar weekly/monthly candles or a verified 52-week session history. Existing
feature keys and score arithmetic remain compatible, but new assessments expose
explicit proxy-basis fields and calendar_period_scoring_admitted=false.
TECHNICAL_RESEARCH_VERSION advances to technical-v0.5.5-explicit-proxy-basis;
historical stored assessments are not rewritten or retroactively qualified.

The separate calendar_period_diagnostics function accepts original daily Bar
tuples and an explicit aware cutoff. It uses the shared checked selector for
chronology/version/adjustment/source checks, while retaining selected suspension
observations which the active-only return path would filter. Source rows and all
derived results bind one deterministic receipt hash and the separate
calendar-period-observations-v1 version. No canonical bars are inserted.

- Bound rows and period inventories to 20,000; reject unsupported decimal bounds.
- Group by market-local date, Monday-to-Monday weeks and first-to-first months.
  Use New York, Shanghai, Hong Kong or Kuala Lumpur timezones, including DST.
- Reject future observations, availability, ingestion and instrument metadata;
  adjusted series, conflicting versions, multiple timestamps per UTC or local
  date, mixed instrument/source/currency/exchange labels cannot hide in buckets.
- Sum Decimal volume/known turnover without floating-point conversion. Unknown
  turnover is null; explicit zero stays zero. Do not infer monetary units or FX.
- Retain every intervening missing period through the cutoff. Never forward-fill
  prices or fabricate zero volume. A missing current period remains missing.
- Withhold all numeric OHLCV until the calendar period ends at local midnight;
  do not presume Friday close, weekends, holidays, early closing or session count.
- Any selected suspension blocks its period; latest suspension blocks all numeric
  period diagnostics rather than substituting an older active close. A later
  active row is not independently verified lifecycle resumption.
- Calendar ended is not session completeness. Expected sessions and coverage
  percentages remain null; source freshness/trust/adjustment truth are unassessed.

This primitive supports equity observations across all four markets. The existing
global CLI exposes it only for its existing US/HK/Malaysia scopes. It does not
broaden that CLI into an A-share collector, or accept funds/ETF instruments.

## Opt-In Read-Only Display

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT \
  --as-of 2026-10-27T15:25:57.208239+00:00 \
  --calendar-periods \
  --sec-database data/processed/sec-filings-20261027.sqlite3 \
  --sec-cik 0000789019 --sec-accession 0001193125-26-323660
```

This is retained historical evidence, not a current price or stock selection.
Exit code 2 remains the unqualified diagnostic status, not deployment success.
The flag cannot combine with --capture and cannot initialize/migrate/write data.
Without the flag, existing outputs remain unchanged. Existing SEC/review combined
hashes bind the additional receipt when explicitly requested, without replacing
their original source versions or conferring cross-provider consistency.

## Retained Historical Check

At the fixed October 27 cutoff, MSFT supplies 706 daily observations:

- 147 ended weekly buckets with UNVERIFIED coverage, plus one missing week.
- 33 ended monthly buckets with UNVERIFIED coverage, plus one unended month.
- Repeated full JSON and calendar/combined hashes agree; scoring remains false.
- Original no-calendar SEC v1 combined hash remains
  1865f2f15955e4bffb5c9abb9707f1065b52041954d3b2803ed00cb1042cdab7.
- Calendar receipt hash:
  9b3f8d29fc7ef8804d2ac7149a7eef646d060af413889f11385a779c9d199007.
- Opt-in combined hash:
  7363235fa3cc2cce048a0aef29fe8d1358b5e05afa54b4294b8ff82791787f01.
- Both original database byte hashes remain unchanged. No source fetch, new raw
  evidence, database write, real screened queue or official report was invented.

Synthetic tests cover exact OHLCV, decimal precision, explicit zero/unknown
turnover, DST, leap/year-end and market-local boundaries, partial/missing periods,
revision selection/conflicts, suspension preservation, future/adjusted/mixed
inputs, sensitive structure rejection, deterministic hashes and read-only CLI
compatibility across US/HK/Malaysia. Thirty new cases plus existing proxy-label
assertions pass. Full pytest: 3532 passed / 6 skipped, 447.88 seconds; Ruff,
mypy (309 files), governance (164 checks), scoped credential/import review and
git diff --check pass. Six opt-in real network skips do not validate sources.
These checks cover the mixed worktree, not an isolated publishable candidate.

## Remaining Admission Work

The subsequent [declaration coverage comparison](calendar-declaration-coverage-2026-11-06.md)
can now separate missing calendars, missing declared-open observations, closed-date
conflicts and suspensions. It uses legacy market-only declarations with UNKNOWN
trust/precision, not qualified exchange calendars. Calendar v1 receipts stay exact;
this new comparison does not close the source/coverage admission gate below.

Verified exchange-calendar coverage and original bar/source/corporate-action
qualification remain required before true session-complete weekly/monthly trend
policies can replace legacy proxies. Do not score the new buckets, infer a holding
period, or count this as complete U3 or strategy validation. PIT market-cap/style,
qualified market sentiment/industry heat, A-share intraday data, real official
research and out-of-sample validation remain separate gaps. Seven-plus-one is
still deferred. Release packaging, encrypted recovery and the existing unsafe
old GitHub candidate must be addressed independently before synchronization.
