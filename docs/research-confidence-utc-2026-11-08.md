# Research Confidence UTC Integrity

## Defect And Scope

November 8, existing ready WP-LAUNCH-001 research/validation hardening.
The earlier ResearchContext and condition-review guards already compare actual
UTC instants. This audit found remaining wall-clock comparisons in direct
confidence helpers, shared assessment availability maxima and the assessment
constructor. This is not evidence that a real persisted research run leaked
future information through the existing context guards.

Synthetic reproduction: America/New_York 2026-11-01 01:30 fold=0 is 05:30 UTC;
the same label with fold=1 is 06:30 UTC. The old direct evidence-confidence helper
incorrectly returned 100 for both PIT integrity and confidence on the future
observation at the earlier cutoff. The reverse problem also existed: 01:45 fold=0
precedes 01:15 fold=1, despite their wall-clock ordering. Shared max() could select
the wrong evidence timestamp or incorrectly reject valid historical evidence.

## Repair

- Direct module/report confidence functions require an aware cutoff and compare
  evidence availability in UTC. A future observation makes PIT integrity and
  confidence zero, not a favorable invisible observation or extra vote.
- Shared scored, insufficient and evidence-driven assessment paths select their
  maximum availability by actual UTC instant, retaining the original selected
  timestamp. Tuple order and local clock labels cannot choose an earlier version.
- ResearchAssessment rejects actual future availability even when the two local
  labels compare equal. Earlier visible evidence with a later wall-clock label
  is accepted, not incorrectly marked future.
- No weights, thresholds, indicators, score averaging, weakest-link/geometric
  formula, four-confirmation rules or market-regime policy are changed.

This is a shared research timestamp repair, not proof that every database/domain
timestamp consumer is correct. Confidence based on caller quality labels and
cutoff visibility is not independent source/PIT qualification or data readiness.
Missing/blocked input cannot become a validated buy/sell conclusion.

## Prospective Version And Persistence

Central RESEARCH_CONFIDENCE_VERSION is research-confidence-v2-utc. New confidence
objects carry method
weighted_geometric_with_weakest_link_cap:research-confidence-v2-utc.
The method label records calculation semantics, never authorization. Normal UTC
numeric confidence remains unchanged, but newly generated report/assessment
metadata and content hashes including that metadata may differ deliberately.

Existing stored methods remain explicit on reconstruction; they are not upgraded
by the new default. An old method cannot bypass actual-UTC constructor checks.
No old report IDs, JSON, hashes, evidence timestamps or source normalization
versions are rewritten. Existing confidence JSON carries the version without a
new column or migration. Framework 0.8.0, schema 0.8.3 and migration head
0011_refresh_ledger remain unchanged. No parallel ResearchReport contract.

## Verification

Thirty-four new synthetic cases cover future/equal/visible repeated hours,
exact microsecond boundaries, equivalent UTC/Malaysia/New York representations,
naive cutoffs including empty inputs, assessment guards, permutation-independent
availability, low empty-data confidence and explicit legacy method preservation.
Two of these cases exercise Policy Research -> official ResearchReport -> SQLite
-> existing replay report repository, with current/explicit legacy method labels
and repeated read-only reconstruction. Fixtures do not qualify any real security,
financial evidence, investment score or historical replay sample.

An existing cutoff test now includes constructor-time rejection inside its error
assertion; child-evidence and evaluation-cutoff gates remain exercised. Full
pytest: 3683 passed / 6 skipped, 209.43 seconds. Ruff, mypy (313 files), governance
(169 checks), scoped import/credential review and git diff --check pass. Skipped
external tests are not real provider verification. These mixed-tree checks do not
certify an isolated publishable candidate, genuine research or strategy returns.
No network source is added or captured. Retained price/SEC/calendar sample databases
remain read-only. No broker, order, execution, Paper, portfolio or notification
logic is added; disabled defaults, PIT UNSUITABLE and production NOT_READY persist.

Offline retained MSFT co-display at 2026-10-27T15:25:57.208239+00:00 retains hash
1865f2f15955e4bffb5c9abb9707f1065b52041954d3b2803ed00cb1042cdab7
and CONFLICTED technical alignment. All three sample DB hashes are unchanged.
This old diagnostic does not serialize ConfidenceBreakdown; it is unchanged,
unlike newly generated official confidence metadata. It is not current MSFT
analysis or a validated investment result.

## Next

Continue source/session and financial-method qualification, genuine research
samples and out-of-sample/robustness validation. This closes a helper-level
engineering defect, not launch acceptance or the historical evidence horizon.
Legacy clock compatibility and the reviewed isolated GitHub candidate remain
separate outstanding work; do not push the old unsafe artifact-rollback commit.
