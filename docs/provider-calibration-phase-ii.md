# Provider Calibration Phase II

## Scope

Phase II introduces Tushare as the first secondary provider for data-quality
calibration only. It does not provide trading, brokerage, execution, allocation,
or order functionality.

Supported canonical datasets:

- Security lifecycle
- ST status
- Suspension and resumption status
- Delisting records
- Financial publication dates
- Fundamental revision evidence
- CSI300, CSI500, and CSI1000 membership

## Architecture

```text
CalibrationQuery
      |
      +--> AkShareCalibrationAdapter --> canonical snapshot
      |
      +--> TushareCalibrationAdapter --> canonical snapshot
                                      |
                         ProviderCalibrationEngine
                                      |
             consistency report + conflict observations
                                      |
                     DatasetConfidenceAssessment
                                      |
                         PITReadinessAssessment
```

Provider adapters retain source limitations and normalize only fields with a
defensible shared meaning. Raw provider differences are not erased to obtain a
higher agreement score.

## Conflict Registry

Every missing record or mismatched comparison field creates a deterministic
`ProviderConflict` observation. A conflict fingerprint identifies the same
logical disagreement across runs, while each report produces a separate
observation. This preserves recurrence history without duplicating an identical
calibration run.

High-severity conflicts include missing records and disagreements in lifecycle,
status, effective dates, delisting dates, and publication dates. Any high-
severity conflict caps dataset confidence and prevents a `USABLE` PIT result.

## Confidence

Dataset confidence combines:

- Provider consistency: 60%
- Conflict-free ratio: 25%
- Snapshot temporal alignment: 15%

Confidence is evidence for PIT readiness, not a replacement for coverage,
availability precision, revision history, or source trust. Calibration cannot
grant `VERIFIED` trust by itself.

## Tushare Boundaries

The adapter uses `TUSHARE_TOKEN` from the environment only. Tokens are never
stored in models, SQLite, logs, rendered reports, or tests. Calibration remains
disabled by default, and live tests require explicit opt-in.

Relevant official Tushare endpoints:

- `namechange`: historical names and dated ST evidence
- `suspend_d`: daily suspension/resumption records
- `stock_basic`: listing and delisting status
- `disclosure_date`: planned and actual financial disclosure dates
- `income`: actual announcement dates and revision/update evidence
- `index_weight`: monthly index constituents and weights

Endpoint permissions depend on Tushare account points. Permission failures are
provider-access limitations and must not be interpreted as empty historical
datasets.

## Operational Sequence

1. Retrieve equivalent provider snapshots for the same `as_of`.
2. Compare only the dataset's registered canonical fields.
3. Persist the consistency report.
4. Persist every conflict observation.
5. Persist dataset confidence.
6. Apply confidence and critical conflicts to PIT readiness.
7. Require manual review before upgrading a source-policy trust classification.
