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

### CNInfo

`CnInfoEvidenceAdapter` captures China A disclosure timing. The current
transport is `AkShareAdapter.fundamental_disclosures`, so provenance is
`cninfo_via_akshare`, trust defaults to `MEDIUM`, and direct-source parity is an
open limitation. Exact announcement timestamps are retained when present;
missing or future timestamps are rejected with warnings.

### Yahoo Finance

`YahooFinanceEvidenceAdapter` captures unadjusted daily bars from Yahoo's
unofficial chart interface for US, Hong Kong, and Malaysia equities. It does not
ingest adjusted close. Evidence defaults to `LOW` trust and
`RETRIEVAL_TIME` availability because historical availability, corrections,
delistings, and symbol continuity are not authoritative.

## Contract Monitoring

`ProviderContractMonitor` checks declared capability, normalized record count,
required payload fields, latency, trust, precision, and limitations. Runs and
checks are persisted separately from evidence ingestion. Exception messages are
not persisted; reports retain only sanitized exception type names.

Run locally:

```bash
python scripts/run_provider_contract_monitor.py --fail-on-defect
```

The GitHub Actions workflow runs weekly and can also be started manually.
External downtime produces `unavailable`; missing records or known provider
limitations produce `degraded`; parser or implementation exceptions produce
`defect`. Only `defect` fails the scheduled job.

Contract health does not upgrade provider trust, coverage, availability
precision, historical continuity, cross-provider consistency, or PIT readiness.

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

The migration head is `0005_provider_evidence_foundation`. New tables are:

- `schema_fingerprints`
- `provider_evidence_records`
- `provider_contract_runs`
- `provider_contract_checks`

The public schema version remains `0.8.0`. This is engineering hardening, not a
new framework feature milestone.

## Remaining Gates

- Run real CNInfo/Yahoo coverage probes over representative symbols and dates.
- Add direct CNInfo raw document capture and parity checks.
- Compare Yahoo against an independent provider before any trust reassessment.
- Measure corrections, delistings, symbol changes, and historical continuity.
- Keep all trading-related development frozen while required replay datasets
  remain below approved PIT readiness.
