# Research Input UTC Integrity: October 24

Work package: WP-LAUNCH-001, still `ready`, not accepted. Scope: research input
visibility, daily revision identity and financial diagnostic selection. No live,
Paper, broker, allocation, Portfolio or Notification code changes are made.

## Reproduction

A synthetic US observation used America/New_York on November 1, 2026. The decision
cutoff was 01:30 with fold=0 (05:30 UTC), and a bar used 01:30 with fold=1
(06:30 UTC). The shared daily selector accepted the bar despite its actual
observation and availability being 3600 seconds after cutoff.

Python comparisons between datetimes carrying the same zone object can compare
repeated wall-clock labels rather than the actual instants required here.
The same issue affected ResearchContext queue/evidence/fact/metadata visibility,
latest revision ordering and version-key identity. A later 01:15 fold=1 revision
could lose to an earlier 01:45 fold=0 revision. Equal labels could collide in
version maps, and a later suspension could be ignored. These are reproduced
engineering defects, not real future provider observations or performance results.

## Repair

- ResearchContext compares queue admission, candidate discovery/availability,
  research-score time, hard-screen times, observed/available evidence, bar times,
  fundamental publication/availability, instrument metadata and supplied regime
  cutoff using actual UTC instants before a persisted run can start.
- Fundamental version keys use UTC availability/publication instants so distinct
  folds do not alias; conflicting content at one actual version still fails.
- The shared daily selector uses UTC cutoff, timestamp/version keys, revision
  ordering and observation sorting. Availability before actual observation is
  rejected. Original rows remain unchanged; no implicit timezone is substituted.
- Distinct folded observations on one UTC date remain an unsupported intraday
  series, not two versions silently collapsed into a daily bar. Latest suspension
  remains excluded without resurrecting an older active price.
- ResearchEvidence constructor chronology uses UTC, accepting valid later
  availability and rejecting an earlier actual availability with the same label.
- Financial latest-fact selection and assessment availability maxima use UTC;
  technical diagnostic timestamp output and latest-availability maxima use UTC.

This does not change market/session calendars, fundamental reporting-period date
semantics, technical formulas, thresholds, source trust, or scoring admission.
Financial assessments remain unscored with zero confidence and no InvestmentScore.
Market Regime remains a research variable, not a hard trading switch.

## Versions And Persistence

Framework 0.8.0, schema 0.8.2 and migration head
0010_portfolio_evidence_lineage are unchanged. No migration or real database
population is needed. New evaluation semantics are distinguished by:

```text
research-report-v0.5.2-utc-inputs
financial-v0.5.11-utc-inputs
technical-v0.5.3-utc-inputs
technical-calculations-v2-utc-inputs
trend-v0.5.3-utc-inputs
pattern-china-a-v0.5.3-utc-inputs
```

Historical stored reports, input packets and diagnostic hashes are not rewritten
or retrospectively certified. Recomputing diagnostic output with a new algorithm
version may intentionally change its hash; unchanged retained bytes are separate
evidence. Existing market-value capture/input/matching contracts are unchanged.

Synthetic SQLite tests mutate pre-existing contexts at four representative
boundaries. Rejection occurs before research_runs, reports, assessments, evidence
or signals are published, and the pending research queue remains available.
Mock-entry tests cover the other future-input paths. Fixtures do not create
real screened candidates or grant source qualification.

## Verification And Remaining Limits

Focused research/technical/quote/persistence suite: 402 passed in 4.85 seconds.
Full suite: **1796 passed, 6 skipped in 64.00 seconds**, 35 additional cases from
the previous 1761-test checkpoint. Ruff, mypy (251 files), governance (108 checks)
and `git diff --check` pass. Six opt-in provider/notification network tests remain
disabled. Regressions include positive timezone-equivalence controls,
distinct actual versions, true conflicts, chronology, latest suspension and
direct Technical/Trend/Pattern entry points, not only future rejection.

The earlier reproduction suite failed 20 behavior checks before the repair;
its additional financial fixture initially hit the domain constructor's raw
chronology restriction and was corrected to an unambiguous prior publication
date before testing revision selection. All 21 targeted checks then passed.
This is not a repository-wide timezone safety certification: domain/storage,
screening, regime metric construction and other timestamp consumers still need
a separate UTC/DST audit. A later report-level gate cannot substitute for
correct input selection. Source timestamps may themselves be unreliable.

Two read-only runs of the exact 002624 query documented in the preceding
market-value binding note (cutoff `2026-10-23T16:03:52+00:00`, example 86400-second
limits and the same trailing review) agree. Existing 674 bars retain a
CONFLICTED technical state, STALE bar age and the prior unavailable HTTP_502
quote. Financial policy remains NOT_ADMITTED and execution_authorized=false.
No new report or queue is fabricated. The technical algorithm version changes
the combined identity, while the unchanged market-value contract retains its
previous diagnostic hash:

```text
input_review_hash   997eb16321a47b6fd53e9e7b4269a58ceb7e0b7ce61abd36a5eb6a8e76fc9019
technical_hash      6ac3263deb7ea453438ca76da6564601da22ab915ae6c38b38484d1a22e61465
market_value_hash   5a4332e18f1938ed0ac927af7e186e3e63eebb10f3faccf36632becffd26b9d0
```

No new network probe or provider capture is made in this heartbeat. The retained
002624 HTTP_502 observation, stale bars under the prior example age policy and
missing source/sector qualification remain open; new code cannot repair those
external evidence gaps. PIT stays UNSUITABLE, production NOT_READY, execution
and notifications disabled. No commit, push or user credential action is required
by this slice. Continue permitted dated quote-source work, independent unit/
share-class/clock/action review and source-qualified technical-plus-fundamental
validation without claiming that passing tests establish investment reliability.
