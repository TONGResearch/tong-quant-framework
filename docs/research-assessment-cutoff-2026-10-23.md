# Research Evaluation-Cutoff Binding

October 23, 2026. Bounded temporal/lineage repair under `WP-LAUNCH-001`, still ready
and incomplete. No Paper, Broker, Execution, Portfolio or Notification changes.

## Reproduced Problem

The candidate-condition entry rejected future assessments but accepted earlier
evaluations without an explicit reuse policy. A synthetic long-term fixture at
`2026-01-02T00:00:00+00:00` combined a financial evaluation from January 1 with
current value/technical modules and returned `VALIDATION_REQUIRED`. These were
synthetic specification scores, not admitted real financial research or trades;
`execution_authorized` remained false. This exposed mixed logical decision
contexts, not a live execution incident.

The condition-free report path also lacked an equivalent check. Python local
datetime comparisons during a repeated daylight-saving hour can treat distinct
instants as equal; comparing only wall-clock labels is insufficient.

## Repair

`research.timing.require_assessment_cutoff` is a shared typed check for:

- Direct `research_condition_features` calls.
- All new `DefaultResearchReportBuilder` builds, even without a condition style.
- The separately supplied PolicyAssessment, not just the assessment tuple.

Every module's `evaluated_at`, interpreted as the logical decision snapshot,
must equal the request cutoff as an actual UTC instant. Assessment availability
and child evidence observation/availability cannot exceed it. Equivalent timezone
representations remain valid and preserve condition hash identity. Both sides of
a repeated New York DST hour remain distinguishable. The report builder also
revalidates ResearchContext before publication.

Historical input observations may legitimately precede the cutoff. The check
does not impose a maximum age or claim their freshness. Reconstruct/evaluate
from the inputs visible at the requested time; merely changing a cached result's
timestamp is not valid re-evaluation. Logical replay time is not wall-clock run
time or proof that the original source was historically available.

## Publication And Versioning

SQLite integration covers no condition style, long-term confirmation and improved
Turtle requests with a deliberately cached technical module. Each run fails
before report/signal publication, records a failed research run with its reason,
returns the queue item to pending and writes no research report, assessment,
evidence or signal. It is an audit-preserving failure, not a completed report,
an InvestmentScore or a trading instruction. Normal fresh incomplete reports
remain persistable through the existing path.

Centralized component versions:

- `RESEARCH_REPORT_VERSION = research-report-v0.5.1-cutoff-bound`.
- `RESEARCH_CONDITIONS_VERSION = research-candidate-conditions-v2-cutoff-bound`.

The single ResearchReport model is unchanged. Only new default outputs use the
new versions. Old reports/conditions remain stored read-only with their original
identities; the repair does not certify or rewrite them. No database migration
or source-data population occurs. Framework/schema remain 0.8.0/0.8.2.

## Remaining Gates

Exact evaluation cutoffs are not complete source/subject/content binding, clock
authentication, data-age policy, independent annotation verification, source trust
or a validated strategy. A caller can still falsely declare a timestamp, so
original consumed-input evidence and future cache protocols need separate review.
Valuation, qualified financial/sector decision conditions, real screening and
strategy validation remain open. PIT stays UNSUITABLE, production NOT_READY and
execution/notifications disabled. No commit/push or readiness promotion.

## Verification

Full pytest: **1588 passed / 6 skipped**, 50.08 seconds, 28 added cases. Focused
research/integration tests pass 231 cases. Ruff passes; mypy reports no issues in
244 source/script files; governance passes 103 checks; `git diff --check` passes.
Skipped tests do not establish real-provider coverage. No remote CI, independent
data review, investment validation or live deployment was performed. Cases cover
prior/future evaluations, both candidate styles, equivalent timezone hash identity,
request-cutoff changes, DST folds including future child data, condition-free
reports, separate policy wrappers and SQLite failure/retry/no-publication behavior.
