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

The scheduled contract-monitor database may contain no rows in some of these
ledgers. A present but empty calibration, conflict, artifact, or readiness
table proves only that the export included that table; it does not prove
provider agreement, historical coverage, or readiness. Review row counts and
the source database's operational scope before interpreting an export.

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

## Durable Archive

Archive a downloaded GitHub Actions ZIP into a private destination only after
checking the digest shown by GitHub or an independently recorded audit:

```bash
python scripts/archive_provider_evidence.py archive \
  --artifact ~/Downloads/provider-contract-ops-<run>-<attempt>.zip \
  --destination ~/Documents/TongQuantEvidenceArchive \
  --verified-at 2026-10-09T20:40:00+08:00 \
  --expected-sha256 <github-artifact-sha256>
```

Verify a retained copy from its content-addressed manifest:

```bash
python scripts/archive_provider_evidence.py verify \
  --manifest ~/Documents/TongQuantEvidenceArchive/provider-evidence-archive-<hash>.json
```

Run a repeatable isolated recovery exercise against the retained copy:

```bash
python scripts/archive_provider_evidence.py restore-drill \
  --manifest ~/Documents/TongQuantEvidenceArchive/provider-evidence-archive-<hash>.json
```

`restore-drill` verifies the manifest, artifact hash, evidence bundle, horizon
report, and embedded SQLite history before extracting only the history database
into a private temporary directory. It uses the existing SQLite restore service
and an independent post-restore audit, checks migration and table-count
preservation, and removes the temporary copy automatically. Its JSON output
contains identities and counts only, not credentials or local paths. A successful
local drill does not prove that a separately encrypted off-device copy can be
opened and restored; repeat the command against that copy after mounting it
without passing its password to Tong Quant.

The archive command rejects symbolic links, path traversal, duplicate ZIP
entries, credential-like JSON or text, digest mismatches, modified bundles,
horizon reports that cannot be reconstructed, and a missing or corrupt provider
contract history SQLite database. The database is checked with SQLite's full
`integrity_check`, and the bundled contract-run, check, and baseline-manifest
identities must exist in the embedded database. This catches an archive whose
main SQLite file omitted still-uncheckpointed WAL records even if both the
database and the evidence bundle are individually valid. The command copies
without silent overwrite, rechecks the copied bytes, and stores the ZIP and
manifest with mode `0600`. The manifest contains filenames and content
identities only, never the source or destination's absolute path. Existing
manifests remain verifiable
after the validator version changes.

The command does not encrypt storage. Run it once for a private local archive
and again for a separately encrypted off-device destination. Matching artifact,
bundle, and horizon identities prove that both copies contain the same reviewed
evidence. Archive IDs may differ when copies are independently verified at
different times.

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
or trading-readiness promotion. Starting with schema `0.8.1`, the horizon
auditor uses only runs recorded as `scheduled` with a syntactically valid GitHub
run reference for its check-count and observed-day gates. Legacy runs remain
`unknown` and do not receive retroactive schedule credit. A human reviewer
must still match each claimed GitHub run ID and attempt to the actual Actions
event and artifact; the stored reference is not an independent attestation.
