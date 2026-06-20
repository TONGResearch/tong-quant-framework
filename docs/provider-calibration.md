# Provider Calibration Framework

## Boundary

Provider calibration compares normalized research data. It does not select
stocks, produce Signals, allocate capital, create orders, or contact brokers.

Providers implement `ProviderCalibrationSource` and return a
`ProviderCalibrationSnapshot` containing:

- Provider and canonical dataset identity
- Point-in-time `as_of`
- Stable record keys
- Canonical comparable fields
- Provider limitations

## Comparison

`ProviderCalibrationEngine` computes:

1. Primary and secondary record counts
2. Matched, primary-only, and secondary-only keys
3. Symmetric key-overlap score
4. Per-field exact canonical match scores
5. Weighted consistency score: 60% key overlap and 40% field agreement
6. Deterministic comparison hash

Consistency maps to trust conservatively:

- At least 95: HIGH
- At least 80: MEDIUM
- At least 50: LOW
- Below 50: UNKNOWN

Calibration alone never creates `VERIFIED` trust. Verification additionally
requires provenance, historical coverage, revision behavior, and temporal
availability evidence.

## Persistence

`provider_consistency_reports` stores the report, scores, limitations, model
version, and comparison hash. Repeating the same normalized comparison is
idempotent.

## Phase II

Tushare is the first secondary provider. `CalibrationQuery` defines the dataset,
point-in-time `as_of`, and non-secret request parameters. AKShare and Tushare
adapters independently produce canonical snapshots before comparison.

Automatic conflict detection classifies missing records and value mismatches,
persists conflict history, and produces a `DatasetConfidenceAssessment`.
High-severity conflicts prevent PIT readiness from becoming `USABLE`. See
`provider-calibration-phase-ii.md`.

## Secondary Provider Onboarding Gate

Before any provider affects trust scores, it must demonstrate
stable identifiers, timestamp semantics, revision policy, raw payload hashing,
rate-limit behavior, and deterministic normalization. Credentials remain outside
SQLite and source control.
