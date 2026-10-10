# Provider Evidence Interim Review: 2026-10-08

## Review Boundary

This is a manual review of the retained October 8 provider-monitor artifact,
not a PIT readiness reassessment. The source artifact SHA-256 is
`4155c322e9c4586a0958ffaa9713c6240a255383bf66ed4da83ae93016dd0fbc`;
bundle `5052012a...82c4`, baseline `f46deb91...5097`, and horizon report
`f06623cb...db63` were independently verified. Both the private local copy
and the encrypted off-device copy passed isolated restore drills on October 10.
The bundle boundary is `2026-10-08T08:55:15.105221+00:00`. It represents the
provider-monitor operational database, not every data store in Tong Quant.

## Horizon And Missing Periods

Each required scope has 17 recorded checks spanning 47.2 days. The numeric
eight-check minimum is met, but the fixed 84-day horizon remains 36.8 days
short. The current run model does not distinguish scheduled from manual
triggers, so the count alone cannot certify eight scheduled observations.
Only 7 of 12 expected baseline weeks contain observations (58.3% continuity).
All five scopes share five missing weekly bins: July 16, 23, and 30, and
August 6 and 13, 2026, at the baseline's 08:55 UTC boundary. These bins
precede the first recorded manual monitor run on August 22. They must remain
missing; later checks cannot be assigned to them retroactively.

| Required scope | Historical check outcomes | Field coverage | Trust / availability observed | Current limiting evidence |
|---|---|---:|---|---|
| Direct CNInfo, China A, 600000 | 14 degraded; 3 unavailable | 82.4% | MEDIUM / EXACT | Complete disclosure and correction history is unproven; latest probe captured metadata only. |
| CNInfo via AKShare, China A, 600000 | 15 degraded; 2 unavailable | 88.2% | MEDIUM / EXACT | Transport provenance is explicit, but direct-source parity and historical continuity are unproven. |
| Yahoo, US, MSFT | 17 degraded | 100.0% | LOW / RETRIEVAL_TIME | Unofficial chart endpoint; historical availability, delistings, symbol changes, and revisions are unverified. |
| Yahoo, Hong Kong, 0700.HK | 17 degraded | 100.0% | LOW / RETRIEVAL_TIME | The same endpoint and historical-evidence limitations apply. |
| Yahoo, Malaysia, 1155.KL | 10 degraded; 7 historical defects | 65.7% | LOW / RETRIEVAL_TIME | Earlier null OHLCV placeholders remain in history; the latest check was degraded without an error, not a rewrite of prior defects. |

The baseline calls the CNInfo contract dataset `china_disclosures`; the
evidence bundle maps it to the readiness dataset
`financial_publication_dates`. Field coverage measures required fields in
observed responses. It is not market-wide dataset coverage, historical
continuity, or proof that a provider is PIT-safe. All five latest checks
returned records with no missing required fields or error code, but each
remained degraded for the listed source limitations.

## Calibration And Conflict Visibility

The operational bundle contains the expected ledger tables, but its
`provider_calibration_attempts`, `provider_consistency_reports`,
`provider_conflicts`, `provider_artifact_observations`, and
`provider_evidence_records` tables each contain zero rows. The scheduled
workflow probes contracts and exports its monitor database; it does not
populate those ledgers. Zero conflict rows therefore means **no conflict
evidence in this snapshot**, not zero real provider disagreements. Likewise,
direct and AKShare-transported CNInfo probes are not a completed parity
calibration, and Yahoo's field completeness is not independent confirmation.
Contract-check limitations remain visible even though the separate
`provider_limitations` ledger is empty in this operational snapshot.

## Decision And Follow-Up

- Horizon eligibility remains `false`; framework PIT readiness remains
  `UNSUITABLE`. No provider trust or validation eligibility is promoted.
- Continue scheduled checks and preserve missing bins, unavailable periods,
  historical defects, and source limitations in every later bundle.
- Before accepting a completed horizon, independently verify scheduled-run
  provenance; the current audit counts checks without recording run origin.
- For future readiness review, provide real, versioned cross-provider
  calibration and conflict evidence from an auditable source. An empty
  operational ledger cannot substitute for it; paid Tushare access is not a
  prerequisite to continuing the monitor.
- After every required scope passes the 84-day audit, review its baseline and
  source limitations separately before running PIT readiness reassessment.
  A passed horizon is necessary evidence, not a trading authorization.
