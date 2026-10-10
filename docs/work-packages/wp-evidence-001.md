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
- New scheduled-run provenance is recorded and independently checked against
  the GitHub Actions event; pre-migration runs stay `unknown` and earn no
  scheduled credit.
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
- A content-addressed archive command now validates the downloaded Actions ZIP,
  reconstructs its evidence bundle and horizon report, checks the embedded
  contract-history SQLite database for corruption, prevents silent overwrite,
  and independently verifies each retained copy. Storage encryption and
  off-device destinations remain operator-owned.
- The October 8 artifact now has two independently reverified durable copies.
  The private local archive manifest `b6dbd469...8e8e` binds artifact
  `4155c322...0fbc`, bundle `5052012a...82c4`, and horizon
  `f06623cb...db63`; both retained files use mode `0600`. The second copy is in
  a separate AES-256 encrypted sparse-bundle in private iCloud Drive. It was
  remounted from its final destination and reverified before CloudDocs reported
  a caught-up state on October 10. Its password and internal archive manifest
  are not stored in the repository.
- The hardened verifier also passed against the retained October 8 archive;
  future archives fail closed when the contract-history database is absent or
  fails SQLite integrity checking.
- On October 10, the retained local ZIP was extracted into an isolated temporary
  directory. The provider-history database passed a read-only source audit and
  `restore-dry-run`; an independent audit of the restored copy matched the
  source audit hash `2b2173cf...329eeba8`, schema fingerprint
  `ad61c67c...1a58`, migration head `0008_provider_calibration_attempts`,
  17 contract runs, 85 checks, 17 baseline manifests, 84 entries, and 764
  inputs. No live database or retained archive file was modified.
- The same procedure is now implemented as the `restore-drill` subcommand of
  `archive_provider_evidence.py`, with tests for nonempty history preservation,
  deterministic path-free output, tamper rejection, and automatic
  temporary-directory cleanup. It passed against the retained October 8 local
  archive with the same audit hash and counts; encrypted off-device recovery
  was then verified separately.
- On October 10, the encrypted iCloud sparse-bundle was mounted from its final
  destination and its retained archive (`884748f2...e875`) passed the same
  isolated `restore-drill`. Source and restored audit hashes matched
  (`2b2173cf...329eeba8`), as did migration head, schema fingerprint, and table
  counts; 17 contract runs, 85 checks, and 17 baseline manifests were recovered.
  The volume was detached afterward. This closes the two-copy restore exercise,
  not the evidence-horizon or PIT-readiness gates.
- Archive verification now cross-checks bundled contract-run, check, and
  baseline-manifest identities against the embedded SQLite history. A
  syntactically valid but stale database snapshot is rejected rather than
  silently treated as complete evidence.
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
- A [scope-level interim review](../provider-evidence-interim-review-2026-10-08.md)
  records the five pre-monitor missing weekly bins, historical failures, source
  limitations, and the absence of calibration and conflict rows in this
  operational snapshot. Empty ledgers are not evidence of provider agreement.
  It also identifies missing scheduled-run provenance as a separate review gate.
- Schema `0.8.1` adds run-origin metadata, and the versioned horizon auditor
  now counts only provenance-qualified scheduled runs toward the 84-day and
  eight-check gates. The retained October 8 report remains verifiable under
  its original policy, while reassessment under the new policy counts its 17
  pre-migration runs as `unknown`. A GitHub run reference still requires
  independent event verification; the current package remains `ready`.
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
