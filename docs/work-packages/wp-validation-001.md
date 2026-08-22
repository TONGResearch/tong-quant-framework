# Work Package: WP-VALIDATION-001

Status: `completed`

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
