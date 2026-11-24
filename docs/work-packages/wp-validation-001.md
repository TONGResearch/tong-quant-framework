# Work Package: WP-VALIDATION-001

Status: `completed`

## Scoped Maintenance: November 22, Finite Outcome Comparisons

Under the active WP-LAUNCH-001 hardening scope, an offline registry call reproduced
NaN != 0 returning True and True != 0 being treated as numeric success. A missing
or invalid observation must not become either success or failure evidence.

OutcomeDefinitionRegistry.evaluate now checks both the observed value and the
declared threshold before any comparison. Only exact built-in int/float operands
that pass the finite-number check are accepted. NaN, infinities, bool, missing,
text, unsupported Decimal objects and integers overflowing that check raise
ValueError without a result label; there is no coercion, zero fill or False fallback.
The constructor may still retain a definition that cannot be evaluated; registry
evaluation is not source/definition admission. Unknown IDs retain the existing
KeyError behavior, and the six comparisons over supported operands are unchanged.

This is one existing registry boundary, not a change to the separate replay
evaluator, all ValidationOutcome constructors, business-thesis evidence, strategy
validity or an execution permission. No new API/module/schema/version/config,
default policy, parameter threshold or serialization is introduced; stored rows
and valid numeric output identities are not rewritten. General numeric and
caller-label checks outside this path remain separate work. H3 accounting/source
review proceeds in parallel; this repair cannot settle its overlap relations.

Added 126 synthetic cases: nine invalid operand kinds in both positions across
six operators (108), and negative/zero/positive valid comparisons (18). The red
phase reproduced the old missing rejection before the scoped fix. Related suites:
315 passed, 9.92 seconds. Full working-tree pytest: **4859 passed / 6 skipped**,
493.19 seconds. Ruff, mypy (324 source files), governance (189 checks), whitespace
and scoped known-pattern privacy/manifest/disabled-default checks pass. The 487
Python/config inputs retain the same before/after full-suite fingerprint:
e841b7b4225c029f286571e052168a2a3886b56f8dda1b04982e79439d9e8ede.
Thirty-six pending paths remain, index empty and HEAD unchanged. These checks
include earlier pending work, not an isolated candidate/release or source/method
qualification; pattern screening is not full secret certification.

Authorized read-only AI static review found no confirmed in-scope issue. It
checked the implementation, tests and scoped docs, not execution or real data.
The new valid cases use zero integer thresholds; subclass rejection and finite
numeric extremes have no explicit new cases. Constructor permissiveness and
other numeric consumers remain outside this repair. No reviewer edits, tests,
network, database/raw/credential access, commits or pushes occurred. This does
not reopen acceptance of WP-VALIDATION-001 or claim WP-LAUNCH-001 acceptance.
Execution/notifications remain disabled, PIT UNSUITABLE, production NOT_READY;
no owner data, network capture, commit/push or real trading change.

## Objective

Make Historical Replay data eligibility explicit and fail closed before a
ValidationRequest can be created.

## Scope

- Enforce the existing ReplayQuery minimum trust requirement.
- Require explicit PIT readiness datasets for each replay query.
- Preserve every incomplete sample while blocking silent validation filtering.
- Separate lifecycle-preservation warnings from actual missing data.
- Freeze consumed readiness-assessment hashes in ReplayManifest.
- Select readiness evidence as of replay generation time.

## Inputs

- V0.6.3 Historical Replay contracts.
- PITReadinessAssessment and DataTrustLevel.
- Existing provider limitations and replay confidence evidence.

## Deliverables

- Explainable replay validation-eligibility fields and blockers.
- Fail-closed ValidationRequestFactory enforcement.
- Deterministic tests for trust, readiness, missing data, lifecycle retention,
  and generation-time visibility.
- Backtesting and data-assurance documentation.

## Acceptance Criteria

- `LOW` or `UNKNOWN` minimum trust policies are rejected.
- Missing, `CAUTION`, or `UNSUITABLE` readiness blocks Validation.
- Any incomplete or ineligible sample blocks request creation and remains
  visible in the replay result.
- ST and delisted securities are retained without being counted as missing.
- Readiness evidence newer than replay generation time is not consumed.
- No Execution, Paper Trading, Broker, Order, Portfolio, or Notification code
  changes are introduced.

## Non-Goals

- No trading strategy, portfolio return backtest, fill simulation, broker
  integration, Paper Trading, or live execution.
- No automatic provider trust or PIT readiness promotion.
- No claim that external data can be guaranteed correct.

## Required Verification

- Historical Replay unit tests
- Full Pytest
- Ruff
- mypy
- `git diff --check`
- Governance audit

## Handoff Notes

The software gate is complete. Current project evidence remains `UNSUITABLE`,
so real historical performance claims remain blocked by `WP-EVIDENCE-001`.
