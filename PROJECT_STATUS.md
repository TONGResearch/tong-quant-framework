# Tong Quant Project Status

This is the canonical short handoff for developers and AI agents. Read it with
`AGENTS.md` and `config/project-governance.toml` before changing code.

## Current Baseline

- Framework version: `0.8.0`
- Database schema version: `0.8.0`
- Migration head: `0008_provider_calibration_attempts`
- Current phase: Engineering continuity and data readiness
- PIT readiness: `UNSUITABLE`
- Production readiness: `NOT_READY`
- Execution default: `disabled`
- Notification default: `disabled`

## What Exists

- Provider-neutral evidence contracts and transactional ingestion
- AKShare data foundation and quality audit
- Optional Tushare capability and calibration adapters
- CNInfo disclosure evidence through explicit AKShare transport provenance
- Yahoo US/Hong Kong/Malaysia research-grade daily-bar evidence
- Provider-neutral unadjusted daily-bar calibration with deterministic fixtures,
  optional Massive US evidence, trust ceilings, and auditable unavailable or
  incompatible outcomes
- Schema baseline, checksum migrations, and physical fingerprint checks
- Scheduled provider contract monitoring
- Provider health operations with explicit owner, acknowledgement, recovery,
  repeated-condition escalation, content-addressed reports, and 90-day CI
  artifact retention
- Immutable longitudinal provider baselines with separate success, field
  coverage, and schedule-continuity metrics
- Credential-free, content-addressed provider evidence bundles with explicit
  `as_of`, per-scope continuity, deterministic reconstruction, and tamper checks
- Content-addressed, no-overwrite durable evidence archiving with ZIP safety,
  credential screening, SQLite history integrity checks, copied-byte
  verification, and independent manifest revalidation
- Fail-closed per-scope evidence-horizon audits for the five scheduled
  CNInfo/Yahoo scopes, with exact 84-day/eight-check deficits and no automatic
  readiness promotion
- Deterministic evidence-backed PIT readiness reassessment with immutable input
  hashes, explicit missing/stale evidence, cause classification, and no
  automatic promotion
- Direct CNInfo disclosure metadata and content-addressed filing artifacts with
  immutable capture observations and AKShare-transport parity support
- Read-only SQLite integrity audits, verified online backups, and isolated
  no-overwrite restore drills
- Discovery, Screening, Research, Validation, Historical Replay, Portfolio/Risk
  research artifacts, and disabled Notification infrastructure
- Fail-closed Historical Replay data-quality eligibility: explicit readiness
  datasets, minimum trust enforcement, incomplete-sample preservation, and
  readiness evidence hashes before ValidationRequest creation
- CI type-checking covers both the reusable `src` packages and operational
  `scripts` entry points

## Frozen Work

Do not implement Paper Trading, Broker Integration, Order generation, Trade or
Fill models, Live Trading, Asset Allocation, Auto Rebalancing, or execution-side
functionality. The freeze remains until the governance promotion requirement is
met and Tong explicitly approves a new architecture proposal.

## Next Ready Work

1. `WP-EVIDENCE-001`: representative longitudinal evidence horizon

`WP-READINESS-001` completed with 12 reviewed datasets, zero promotion-review
eligible datasets, and unchanged `UNSUITABLE` effective readiness. The next
package must retain and freeze at least 12 weeks of operational evidence before
another reassessment. The October 8 scheduled run completed successfully and
contains 17 checks per required scope across 47.2 days, with 7/12 baseline
periods and 58.3% continuity. Its downloaded artifact, SQLite integrity,
content-addressed bundle, and deterministic horizon reconstruction were
independently verified on October 9. The horizon audit remains ineligible with
36.8 days outstanding. All five required scopes still carry expected
provider/data-limitation degradation, with no new implementation defect in the
latest run. The five stable warnings are acknowledged in
[GitHub issue #1](https://github.com/TONGResearch/tong-quant-framework/issues/1)
without promoting provider trust or PIT readiness. Elapsed calendar time alone
is not evidence, and the package cannot promote trust or PIT readiness
automatically.

On October 10, the October 8 artifact was retained in two independently
verified durable copies: a private local content-addressed archive and a
separate AES-256 encrypted sparse-bundle in private iCloud Drive. The encrypted
copy was detached, remounted from its final destination, and reverified before
CloudDocs reported a caught-up state. This closes the current two-copy storage
gap, but it does not satisfy the outstanding 84-day evidence horizon or promote
PIT readiness.

An isolated restore drill from the private local October 8 archive also passed
on October 10: the restored provider-history database matched the source audit
hash, schema fingerprint, migration head, and table counts. This proves local
archive recoverability only; an independent restore from the encrypted
off-device copy is still outstanding. The drill is now a repeatable
`archive_provider_evidence.py restore-drill` command with fail-closed tests and
credential-free, path-free summary output. Archive verification also rejects
bundled contract-run, check, or baseline identities absent from its embedded
SQLite history.

Planned work must respect dependencies in `config/project-governance.toml`.

Future planned work after the evidence and readiness gates:

- `WP-RESEARCH-001`: family-aware technical confluence and size/style research

This reservation covers MACD, KDJ, parameterized triple-average candle events,
Granville events, startup-state tracking, and dynamic invalidation references.
It is not ready and does not relax the trading-development freeze.

## Provider Policy

No provider is trusted by default. Tong Quant evaluates dataset evidence for
trust, coverage, availability precision, historical continuity, and
cross-provider consistency. Provider health does not imply PIT readiness.

## Agent Startup

1. Read `AGENTS.md`.
2. Read this file.
3. Read `config/project-governance.toml`.
4. Run `python scripts/check_project_governance.py`.
5. Select one `ready` work package and read its document.
6. Inspect the relevant code and tests before editing.

## Required Completion Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src scripts
git diff --check
.venv/bin/python scripts/check_project_governance.py
```

Update this status, governance configuration, relevant work package, risk
register, and technical-debt register when a milestone changes project state.
