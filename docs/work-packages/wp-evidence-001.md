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

- The twice-weekly private GitHub Actions monitor is configured; the first
  manual run completed successfully on 2026-08-22 and preserved its run
  artifact.
- Credential-free, content-addressed JSON and Markdown bundle export is
  implemented and wired into scheduled monitoring.
- A content-addressed horizon audit now enforces the 84-day/eight-check gate
  separately for direct CNInfo, AKShare-transported CNInfo, and Yahoo US/Hong
  Kong/Malaysia scopes. It reports exact deficits and requires complete
  baseline measurements without promoting trust or PIT readiness.
- The scheduled workflow now retains and publishes the horizon audit beside
  each evidence bundle.
- Deterministic reconstruction, future-boundary rejection, tamper detection,
  secret rejection, local-path rejection, and missing-table visibility are
  covered by automated tests.
- CI type-checking covers the provider evidence, calibration, and capture
  command-line entry points in `scripts` as well as the reusable packages.
- The October 1 Actions artifact was downloaded and independently verified on
  October 3. Artifact digest `bd8f441e...d832`, evidence bundle
  `53ed8e12...aeb2`, and horizon report `dc1e0469...f6b8` all passed integrity
  verification.
- The October 5 and October 8 scheduled runs completed successfully. The
  October 8 job summary reports 17 checks per required scope across 47.2 days,
  7/12 observed baseline periods, 58.3% continuity, and 36.8 days remaining.
  Report `f06623cb...db63` remains ineligible for PIT readiness reassessment.
- The October 8 artifact was downloaded and independently verified on October
  9. Artifact digest `4155c322...0fbc`, evidence bundle `5052012a...82c4`, and
  horizon report `f06623cb...db63` matched the Actions summary. SQLite integrity
  returned `ok`, bundle verification passed, and an independent horizon rebuild
  reproduced the same report ID.
- All five required scopes remain under repeated-degradation warnings. Field
  coverage is 82.4% for direct CNInfo, 88.2% for CNInfo via AKShare, 100% for
  Yahoo Hong Kong and US, and 65.7% for Yahoo Malaysia. These observations do
  not promote trust or readiness.
- Every check in the latest run returned records with no missing required
  fields and no error code. CNInfo remains degraded because complete historical
  disclosure and correction continuity are unproven. Yahoo remains degraded
  because it is unofficial, `LOW` trust, and `RETRIEVAL_TIME` precision. No new
  implementation defect was found.
- The five stable warning fingerprints were acknowledged on October 9 in
  [GitHub issue #1](https://github.com/TONGResearch/tong-quant-framework/issues/1):
  `5a1b7e3c...de8a`, `2582d3b1...d68a`, `252493b4...e8c7b`,
  `28f7bcbc...1160`, and `ce3df88b...a492`. The acknowledgement records
  acceptance of the visible limitation only; it does not promote trust or
  readiness. The issue remains open until a recovery report or an explicitly
  accepted permanent limitation is recorded.
- Historical Malaysia Yahoo checks exposed null OHLCV placeholder rows. Future
  checks classify present-but-null required values as degraded data quality;
  structurally absent payload keys remain fail-closed defects. Historical
  defects are preserved and are not rewritten.
- This work package stays `ready` until a later verified bundle passes every
  per-scope horizon gate and receives independent durable-copy review.

## Non-Goals

- No Paper Trading, Execution, Broker, Order, Trade, Fill, Asset Allocation,
  Auto Rebalancing, Portfolio optimization, or Live Trading work.
- No dependency on a Tushare account upgrade.
- No provider trust promotion based only on endpoint availability or agreement.
- No Notification Engine integration.
