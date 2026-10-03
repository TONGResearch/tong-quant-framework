# Provider Evidence Foundation

## Scope

This hardening phase adds data infrastructure only. Execution, Paper Trading,
Broker, Order, Live Trading, Asset Allocation, Portfolio, and Notification code
remain unchanged and frozen.

## Architecture

```text
ProviderEvidenceAdapter
  -> ProviderDatasetCapability
  -> ProviderDatasetRequest(as_of)
  -> ProviderEvidenceBatch
  -> strict PIT and trust validation
  -> one SQLite transaction
       ingestion_batches
       raw_dataset_fingerprints
       provider_evidence_records
       provider_limitations
       data_availability_warnings
```

`ProviderEvidenceRecord` stores observed, publication, availability, and
retrieval timestamps separately. It also carries the provider, dataset, market,
subject, raw-data hash, source reference, payload, `DataTrustLevel`,
`AvailabilityPrecision`, and limitations. Strict ingestion rejects evidence
whose event timestamp is later than the request's decision `as_of`.

The evidence ledger is additive. It does not silently overwrite canonical
fundamentals, bars, status histories, research artifacts, or replay samples.
Dataset-specific promotion requires normalization, calibration, and a separate
PIT readiness decision.

## Implemented Providers

### CNInfo Via AKShare

`CnInfoEvidenceAdapter` captures China A disclosure timing. The current
transport is `AkShareAdapter.fundamental_disclosures`, so provenance is
`cninfo_via_akshare`, trust defaults to `MEDIUM`, and direct-source parity is an
open limitation. Exact announcement timestamps are retained when present;
missing or future timestamps are rejected with warnings.

### Direct CNInfo Artifacts

`CnInfoDirectEvidenceAdapter` captures official announcement IDs, publication
timestamps, detail/file URLs, relation evidence, and optional filing bytes under
the distinct provider identity `cninfo_direct`. `FileSystemArtifactStore` writes
content-addressed mode-`0600` files; SQLite stores immutable metadata and every
captured/missing/unavailable observation. Pagination, download counts, domains,
response sizes, retries, and request intervals are bounded.

Direct evidence remains `MEDIUM` trust until representative parity, coverage,
correction continuity, and long-term provider behavior are reviewed. See
`docs/cninfo-direct-artifacts.md`.

### Yahoo Finance

`YahooFinanceEvidenceAdapter` captures unadjusted daily bars from Yahoo's
unofficial chart interface for US, Hong Kong, and Malaysia equities. It does not
ingest adjusted close. Evidence defaults to `LOW` trust and
`RETRIEVAL_TIME` availability because historical availability, corrections,
delistings, and symbol continuity are not authoritative.

Yahoo records now expose exchange-local session date, explicit unadjusted price
basis, and chart-reported corporate-action types. `DailyBarCalibrationCoordinator`
can compare them with any compatible `ProviderEvidenceAdapter`, deterministic
fixtures, or the optional Massive US adapter. Completed, unavailable, and
incompatible attempts remain distinct and auditable. See
`docs/yahoo-daily-bar-calibration.md`.

### Optional Massive Calibration

`MassiveEvidenceAdapter` implements the same daily-bar evidence contract for US
equities. It fetches unadjusted aggregates plus dividend and split dates from
official HTTPS endpoints. `MASSIVE_API_KEY` stays in the Authorization header;
the provider starts at `LOW/RETRIEVAL_TIME`, and no live access is assumed.

## Contract Monitoring

`ProviderContractMonitor` checks declared capability, normalized record count,
required payload fields, latency, trust, precision, and limitations. Runs and
checks are persisted separately from evidence ingestion. Exception messages are
not persisted; reports retain only sanitized exception type names.

Run locally:

```bash
python scripts/run_provider_contract_monitor.py --fail-on-defect
```

The GitHub Actions workflow runs twice weekly and can also be started manually.
External downtime produces `unavailable`; empty results, null required values,
or known provider limitations produce `degraded`; structurally absent required
keys, parser exceptions, or implementation errors produce `defect`. Only
`defect` fails the scheduled job.

`ProviderHealthAssessor` evaluates each run against 84 days of stored history.
It distinguishes one-off unavailability/degradation, repeated conditions,
implementation defects, and recovery. Warning and critical reports identify an
owner, acknowledgement requirement, related checks, and recovery steps. This is
repository operations data and has no dependency on `tong_quant.notifications`.
See `docs/provider-monitor-operations.md`.

Contract health does not upgrade provider trust, coverage, availability
precision, historical continuity, cross-provider consistency, or PIT readiness.

## Longitudinal Baseline

`ProviderBaselineBuilder` reads stored contract checks and creates an immutable,
content-addressed manifest for an explicit time window, cadence, and set of
provider/dataset/market/subject scopes. It reports three separate concepts:

- successful-observation ratio for provider responses containing evidence;
- required-field coverage across attempted checks;
- schedule continuity across expected observation periods.

Missing periods, unavailable/defect checks, empty responses, observed trust,
availability precision, and provider limitations remain visible. The baseline
does not calculate a promoted trust level and cannot change PIT readiness.
Generation time is retained in SQLite audit metadata but excluded from rendered
summaries, so identical inputs and query scope produce byte-stable JSON and
Markdown.

Run locally after one or more contract monitor runs:

```bash
python scripts/build_provider_contract_baseline.py \
  --database data/provider-contract-monitor.sqlite3
```

Scheduled CI restores and saves a small SQLite history cache, publishes
run-identified contract files plus content-addressed health and baseline files,
and retains the uniquely named artifact for 90 days. Health findings are copied
to the private Actions Job Summary. If a probe identifies an implementation
defect, baseline generation and artifact upload still run before the job fails
closed.

Every scheduled run also exports a credential-free, content-addressed
operational evidence bundle. The bundle is read-only with respect to SQLite,
freezes an explicit `as_of` boundary, excludes local artifact storage paths and
bytes, and can reconstruct its dataset summaries from its table snapshots.
Credential-like values, local paths, hash mismatches, and summary tampering fail
verification. See `docs/provider-evidence-bundles.md`.

### Initial Live Contract Baseline

The read-only probe on 2026-08-21 observed:

- CNInfo via AKShare: 2 complete disclosure records for `600000`
- Yahoo US: 6 complete daily-bar records for `MSFT`
- Yahoo Hong Kong: 6 complete daily-bar records for `0700.HK`
- Yahoo Malaysia: 6 complete daily-bar records for `1155.KL`

All checks remain `degraded` by policy because their declared provider
limitations still apply. The first Yahoo attempt exposed a macOS Python CA-chain
failure; `YahooChartHttpClient` now uses the explicitly declared `certifi` CA
bundle. This fixed transport compatibility without weakening TLS validation.

## Database

The migration head is `0008_provider_calibration_attempts`. Provider evidence,
artifact, and baseline tables are:

- `schema_fingerprints`
- `provider_evidence_records`
- `provider_artifacts`
- `provider_artifact_observations`
- `provider_contract_runs`
- `provider_contract_checks`
- `provider_baseline_manifests`
- `provider_baseline_entries`
- `provider_baseline_inputs`
- `provider_calibration_attempts`

Evidence bundle export introduces no table or migration. It reads the existing
operational, historical-coverage, and PIT-readiness ledgers.

The public schema version remains `0.8.0`. This is engineering hardening, not a
new framework feature milestone.

## Remaining Gates

- Accumulate and review representative CNInfo/Yahoo baselines across multiple
  calendar periods.
- Accumulate direct CNInfo/AKShare-transport parity and correction-continuity
  evidence; the capture and comparison contracts are implemented.
- Accumulate real Yahoo/Massive comparisons before any trust reassessment; the
  deterministic and fail-closed calibration mechanism is implemented.
- Measure corrections, delistings, symbol changes, and historical continuity.
- Keep all trading-related development frozen while required replay datasets
  remain below approved PIT readiness.
