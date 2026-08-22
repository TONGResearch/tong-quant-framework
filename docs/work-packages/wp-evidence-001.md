# Work Package: WP-EVIDENCE-001

Status: `ready`

## Objective

Accumulate and freeze a representative longitudinal provider-evidence horizon
without depending on paid Tushare access or introducing trading functionality.

## Dependencies

- `WP-READINESS-001`: evidence-backed PIT readiness reassessment
- `WP-OPS-001`: provider health operations
- `WP-DATA-002`: direct CNInfo artifact evidence
- `WP-DATA-003`: independent Yahoo daily-bar calibration

## Scope

- Preserve at least 12 consecutive weeks of scheduled provider contract checks
  for direct CNInfo, AKShare-transported CNInfo, and Yahoo US/Hong Kong/Malaysia
  evidence.
- Account explicitly for every scheduled missing period, unavailable endpoint,
  degraded response, implementation defect, and recovery.
- Export a credential-free, content-addressed evidence bundle from the
  operational SQLite database instead of committing a local database file.
- Include contract runs, baseline manifests, artifact observations, calibration
  attempts, provider conflicts, model versions, source hashes, and observation
  windows.
- Verify that exported row counts and hashes reconstruct the readiness-relevant
  operational summary deterministically.
- Refresh Phase III artifacts only from real provider evidence; unavailable
  commercial providers remain explicit limitations.
- Re-run `WP-READINESS-001` evaluation after the minimum horizon is complete.

## Minimum Review Gates

- Observation horizon is at least 84 days with at least 8 scheduled checks per
  required provider/dataset/market scope.
- CI artifacts and caches are not the sole durable copy of evidence.
- Export contains no credentials, raw environment diagnostics, or local paths.
- Missing periods remain visible and cannot be backfilled with synthetic
  success records.
- Provider health, source agreement, and data trust remain separate concepts.
- No automatic PIT or trust promotion occurs after export.

## Deliverables

- Credential-free operational evidence export format and command.
- Deterministic export/reconstruction tests.
- Twelve-week continuity and field-coverage baseline.
- Missing-period, provider-limitation, and conflict review.
- Refreshed evidence-backed PIT readiness report.

## Current Progress

- The twice-weekly private GitHub Actions monitor is active; the first manual
  run completed successfully on 2026-08-22 and preserved its run artifact.
- Credential-free, content-addressed JSON and Markdown bundle export is
  implemented and wired into scheduled monitoring.
- Deterministic reconstruction, future-boundary rejection, tamper detection,
  secret rejection, local-path rejection, and missing-table visibility are
  covered by automated tests.
- The minimum 84-day observation horizon remains incomplete. This work package
  stays `ready` and PIT readiness must not be promoted from implementation
  completion alone.

## Non-Goals

- No Paper Trading, Execution, Broker, Order, Trade, Fill, Asset Allocation,
  Auto Rebalancing, Portfolio optimization, or Live Trading work.
- No dependency on a Tushare account upgrade.
- No provider trust promotion based only on endpoint availability or agreement.
- No Notification Engine integration.
