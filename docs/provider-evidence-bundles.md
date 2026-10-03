# Provider Evidence Bundles

## Purpose

A provider evidence bundle freezes the operational evidence needed to review
provider reliability without committing a mutable SQLite database, downloaded
artifact bytes, credentials, or machine-local paths. It is a data-governance
artifact only. It cannot promote provider trust, PIT readiness, or trading
readiness.

## Contents

The export snapshots existing ledgers for:

- schema and migration identity;
- ingestion batches and provider limitations;
- provider-neutral evidence and source hashes;
- provider contract runs and checks;
- longitudinal baseline manifests, entries, and inputs;
- direct artifact metadata and retrieval observations;
- calibration attempts, consistency reports, and provider conflicts;
- dataset confidence, historical coverage, and PIT readiness assessments.

Rows later than the explicit export `as_of` are excluded using each ledger's
operational timestamp. Baseline child rows are included only when their parent
manifest is visible. Incomplete ingestion batches and batches completed after
the boundary are excluded because their final state was not yet knowable.
Missing expected tables remain explicit limitations.

The bundle excludes provider artifact `storage_key` values and artifact bytes.
It rejects credential-like fields or assignments and absolute local filesystem
paths before output is created.

## Identity And Verification

Each table has a deterministic row hash after canonical sorting. The whole JSON
document has a SHA-256 bundle identity derived from every exported value except
the identity field itself. Verification checks:

- the bundle hash;
- each table row count and row hash;
- canonical row ordering;
- deterministic reconstruction of dataset summaries;
- credential and local-path policy.

The same database snapshot, `as_of`, framework version, schema version, and
implementation version produce the same identity.

## Commands

```bash
python scripts/export_provider_evidence.py \
  --database data/provider-contract-monitor.sqlite3 \
  --as-of 2026-08-22T12:00:00+00:00 \
  --output-dir provider-contract-artifacts
```

Verify a copied bundle independently:

```bash
python scripts/export_provider_evidence.py \
  --verify provider-contract-artifacts/provider-evidence-bundle-<hash>.json
```

Audit the required provider/dataset/market/subject scopes against the fixed
84-day and eight-check gate:

```bash
python scripts/audit_provider_evidence_horizon.py \
  --bundle provider-contract-artifacts/provider-evidence-bundle-<hash>.json \
  --output-dir provider-contract-artifacts
```

The audit verifies the bundle before evaluating it. It reports every required
scope separately, including exact remaining days and checks, baseline period
coverage, observed/expected periods, continuity, and field coverage. A dataset
aggregate cannot compensate for a missing country or provider scope. The scheduled
provider-monitor workflow writes this report into the same retained artifact
and publishes its Markdown summary to the GitHub Actions run summary.

Generated operational bundles and local SQLite files remain untracked. A
durable private archive must retain at least two independently verified copies
before the 90-day GitHub Actions artifact expires.

## Readiness Gate

`WP-EVIDENCE-001` requires at least 84 days and eight scheduled observations for
every required provider/dataset/market scope. Missing periods, provider
limitations, failures, low-trust evidence, and retrieval-time precision remain
visible. Reaching the time horizon does not by itself make a dataset `USABLE`;
the separate PIT readiness reassessment must consume the accumulated evidence.
The horizon report's eligibility flag means only that the evidence may enter
that separate human review. It is not a trust, research, validation, portfolio,
or trading-readiness promotion.
