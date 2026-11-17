# Replay Endpoint Suspension And UTC Qualification

Work package: WP-LAUNCH-001. Status: ready, not accepted.
Scope: research price-outcome qualification, not a strategy, backtest or execution.

## Confirmed Counterexamples

Offline synthetic direct calls to evaluate_outcome returned a successful 20 percent
close change with a flagged suspended decision endpoint, outcome endpoint or both.
Flat carried prices could also generate a numerical outcome label. Retaining a
last close is useful for diagnosis but does not satisfy the new endpoint policy.
No actual owner result or provider record was demonstrated to be wrong by this
synthetic reproduction.

A second direct-call counterexample used New York's repeated November 1 01:30:
bar availability at fold 1 was one hour after a fold-0 decision cutoff, but native
datetime comparison treated them as equal and produced the same numeric outcome.
This was a direct evaluator defect; the existing bound-reader/request checks have
additional defenses and this audit does not claim every repository leaked it.

## Prospective Outcome Contract

REPLAY_OUTCOME_VERSION advances to
replay-outcome-v2-suspension-utc-endpoints. The price-only target metric and exact
UTC calendar-day window remain; no nearest-day/session or last-good fallback is
added. Changes are:

- An explicitly suspended decision/outcome bar contributes a named blocker.
  A nonboolean is_suspended is unknown/invalid, never coerced into False.
- Visibility compares observation, availability and cutoff as actual UTC instants.
  Availability before the observation adds a separate chronology blocker, even
  when repeated wall-clock labels passed the existing Bar constructor.
- Any blocker withholds numeric value, success and invalidation labels. The
  outcome is NOT_OBSERVABLE, not a negative assessment of the business research.
- Original endpoint contents and hashes remain in outcome_context, along with
  precise reasons and the explicit endpoint policy. Missing endpoints remain
  absent; suspended positive or unchanged closes are not replaced with zero.
- False suspension flags are necessary for this scoped calculation, not proof
  of actual trading, source correctness, full lifecycle/session coverage or fill
  availability. Existing source, calendar, action and execution limitations remain.

HistoricalReplayBuilder already preserves incomplete diagnostic samples and
binds outcome blockers to sample/manifest ineligibility. This slice reuses those
paths without dropping symbols or moving future outcome facts into decision
research. The direct bound-outcome verifier recomputes the same policy, rejecting
validly rehashed suspended bindings that still claim a favorable value.

Existing outcome_missing flags denote missing usable outcomes, not necessarily
missing raw endpoint records. This slice does not redesign missing-data scoring;
the raw bindings/reasons must be read with that flag. An adverse lifecycle status
alone remains distinct from a flagged unusable price endpoint and is not newly
filtered from the universe. No real PIT or source trust score is upgraded.

## Versions And Storage

The centralized outcome version participates in query hashes, dataset versions,
sample/manifest identities and ValidationRequestFactory checks. New v2 results
have distinct identities; stored v1 JSON, hashes and rows are not rewritten or
recertified. Old version-tagged results require explicit reconstruction before
current validation. There is no v1 evaluator fallback in the new code.

Synthetic compatibility tests emulate old version tags and persistence, not a
full old-code interpreter. They verify unchanged stored manifest/sample rows,
separate new identities and current-request rejection of the legacy version.
The research report contract, framework/schema/migration versions, replay/confidence
algorithms and database schema remain unchanged. No real database is migrated or
written by this delivery; all publication/revision exercises use temporary fixtures.

## Verification

New tests cover flagged/unknown suspension endpoints, positive and flat prices,
both endpoint positions, actual-UTC fold boundaries and chronology, equivalent
instants, incomplete sample persistence, deterministic retries, no nearby/old-good
fallback, omitted required-outcome fields, future suspension revisions, rehashed
bindings and synthetic legacy-version immutability/reconstruction.
The 155 replay tests pass, including 33 new cases. An owner-authorized read-only
AI reviewer found no actionable issue in the scoped evaluator/version/tests;
that was static review without tests, network, real databases or source approval.
Final stable-tree pytest: 4257 passed, 6 skipped (406.62 seconds). Ruff, mypy
(319 files), governance (179 checks), whitespace and scoped known-pattern privacy/
import/disabled-default checks pass. All 475 tracked/new Python/config inputs have
unchanged content fingerprints before/after that run. This does not certify
opaque secrets or unrelated/private data. Working-tree tests and scoped review
do not qualify an isolated release candidate or real data.

## Residual Work And Boundaries

Independent price/status/session/corporate-action evidence, lifecycle conflicts,
exchange-session-aware targets, total-return/cost policy, reconstruction-quality
versus missing-usable-outcome scoring and genuine technical/fundamental validation
remain open. No new Paper, Broker, Order, Portfolio, Notification or execution
logic exists. Execution and notifications remain disabled; PIT stays UNSUITABLE
and production NOT_READY. 271 definitions stay deferred. No commit/push occurs
in this slice, and engineering success cannot promote live trading.
