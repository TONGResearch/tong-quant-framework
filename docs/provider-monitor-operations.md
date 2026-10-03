# Provider Monitor Operations

## Purpose

This runbook governs Tong Quant provider contract health. It turns sanitized
contract checks and longitudinal history into repository-operations artifacts.
It does not use the Notification Engine, deliver external messages, change
provider trust, change PIT readiness, or trigger trading behavior.

## Ownership And Policy

- Default owner: `TONGResearch`
- History window: 84 days
- Repeated degradation threshold: 3 consecutive checks
- Repeated unavailability threshold: 2 consecutive checks
- GitHub Actions artifact retention: 90 days
- Contract-history database: retain until an archive is created and its restore
  is verified; never prune it merely because uploaded artifacts expire

The workflow runs every Monday and Thursday and can be dispatched manually.
Repository operations reports are generated even when the probe identifies a
defect.

## Conditions

| Condition | Severity | Acknowledgement | CI effect |
|---|---|---|---|
| Healthy with no prior failure | None | None | Pass |
| One-off degradation | Info | Not required | Pass |
| One-off unavailability | Info | Not required | Pass |
| Repeated degradation | Warning | Required | Pass |
| Repeated unavailability | Warning | Required | Pass |
| Recovery after unhealthy check | Info | Not required | Pass |
| Implementation or contract defect | Critical | Required | Fail closed |

Unavailable provider access, rate limits, and network downtime are external
availability conditions. A required payload key that is structurally absent,
malformed normalized data, identity mismatches, future decision evidence, and
parser exceptions are implementation defects. Empty normalized responses and
records whose required keys exist but contain null values are degraded data
quality, not parser defects. Their missing-field coverage remains explicit in
the check and baseline. Raw exception messages are never written to reports.

## Artifact Identity

Each run writes immutable, collision-checked files:

- `provider-contract-run-<run_id>.json`
- `provider-contract-run-<run_id>.md`
- `provider-health-<report_hash>.json`
- `provider-health-<report_hash>.md`
- `provider-contract-baseline-<baseline_hash>.json`
- `provider-contract-baseline-<baseline_hash>.md`
- `provider-evidence-bundle-<bundle_hash>.json`
- `provider-evidence-bundle-<bundle_hash>.md`

The GitHub artifact is named
`provider-contract-ops-<github_run_id>-<github_run_attempt>`. Health reports
include framework, contract-monitor, and policy versions; run, check, alert,
stable condition fingerprint, and report identities; owner; retention;
acknowledgement requirement; and recovery steps.

The evidence bundle is a credential-free, content-addressed snapshot of the
operational database as of an explicit timestamp. It preserves contract,
baseline, provider-neutral evidence, artifact observation, calibration,
conflict, confidence, historical-coverage, and PIT-readiness records. Provider
artifact bytes and local `storage_key` values are excluded. Export fails closed
if credential-like assignments or local filesystem paths are detected.

## Acknowledgement

For every warning or critical alert:

1. Open the private GitHub Actions run and download its uniquely named artifact.
2. Verify that the alert ID, fingerprint, and related check IDs match the Job
   Summary.
3. Use the stable fingerprint to find or create a private GitHub issue; add the
   current alert ID to that issue or the fixing pull request.
4. Assign the issue or pull request to the report owner.
5. Link the first later report that shows recovery or the accepted permanent
   provider limitation before closing the issue.

Acknowledgement is an audit action, not permission to weaken a contract, ignore
missing data, promote trust, or resume trading development.

## Recovery

### Implementation Defect

Inspect required fields, adapter parsing, identity checks, and deterministic
fixtures. Fix the implementation and rerun the workflow manually. Do not
change a required field solely to make the check pass.

### Repeated Unavailability

Check provider status and account permissions outside Tong Quant. Preserve the
missing periods. Use only an already approved provider fallback; do not convert
absence into zero coverage or agreement.

### Repeated Degradation

Review the longitudinal baseline, limitation codes, record counts, and field
coverage. Persistent declared limitations remain visible and cannot promote
provider trust or PIT readiness.

### Missing Report

If the health report is absent, treat the workflow itself as failed. Inspect
the probe step, database restore, disk capacity, Python environment, and
artifact upload. Do not delete the history database as a recovery shortcut.

## Local Command

```bash
python scripts/run_provider_contract_monitor.py \
  --database data/provider-contract-monitor.sqlite3 \
  --output-dir provider-contract-artifacts \
  --artifact-retention-days 90 \
  --owner TONGResearch \
  --fail-on-defect
```

Build the longitudinal baseline after the probe:

```bash
python scripts/build_provider_contract_baseline.py \
  --database data/provider-contract-monitor.sqlite3 \
  --output-dir provider-contract-artifacts
```

Export and independently verify the content-addressed evidence snapshot:

```bash
as_of="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
python scripts/export_provider_evidence.py \
  --database data/provider-contract-monitor.sqlite3 \
  --as-of "$as_of" \
  --output-dir provider-contract-artifacts

python scripts/export_provider_evidence.py \
  --verify provider-contract-artifacts/provider-evidence-bundle-<hash>.json
```

The local SQLite file and generated artifacts are operational data and must not
be committed to Git.
