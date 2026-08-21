# Work Package: WP-DATA-001

Status: `ready`

## Objective

Create a reproducible longitudinal provider baseline that measures contract
availability, field coverage, and continuity over repeated observations.

## Scope

- Define an append-only baseline manifest for provider contract runs.
- Preserve run date, query scope, implementation version, and input hash.
- Aggregate observations by provider, dataset, market, and subject.
- Measure successful-observation ratio, field coverage, gaps, and continuity.
- Keep provider downtime and empty datasets visible.
- Add retention and export rules for scheduled CI artifacts.

## Inputs

- `ProviderContractRun` and `ProviderContractCheck`
- Existing SQLite contract-monitor tables
- CNInfo via AKShare and Yahoo evidence adapters

## Deliverables

- Longitudinal baseline domain models and repository contract
- Additive migration if new persistence is necessary
- Deterministic Markdown and JSON summary
- Unit and integration tests
- Updated trust/readiness documentation without automatic promotion

## Acceptance Criteria

- Identical stored observations produce an identical baseline hash.
- Missing weeks and failed probes remain visible.
- Coverage and continuity are reported separately from trust.
- At least China A, US, Hong Kong, and Malaysia scopes are supported.
- No provider receives `VERIFIED` trust from contract history alone.

## Non-Goals

- No trading, portfolio, notification, broker, order, or execution changes.
- No automatic PIT readiness promotion.
- No requirement for paid Tushare, Massive, or Finnhub access.

## Required Verification

Run all commands in `PROJECT_STATUS.md` and fake-provider failure tests.
