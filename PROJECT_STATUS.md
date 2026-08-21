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
- Direct CNInfo disclosure metadata and content-addressed filing artifacts with
  immutable capture observations and AKShare-transport parity support
- Read-only SQLite integrity audits, verified online backups, and isolated
  no-overwrite restore drills
- Discovery, Screening, Research, Validation, Historical Replay, Portfolio/Risk
  research artifacts, and disabled Notification infrastructure

## Frozen Work

Do not implement Paper Trading, Broker Integration, Order generation, Trade or
Fill models, Live Trading, Asset Allocation, Auto Rebalancing, or execution-side
functionality. The freeze remains until the governance promotion requirement is
met and Tong explicitly approves a new architecture proposal.

## Next Ready Work

1. `WP-READINESS-001`: evidence-backed PIT readiness reassessment

All current data foundation and provider-operations packages are complete. The
readiness reassessment may recommend another remediation package; it cannot
promote trust or PIT readiness automatically.

Planned work must respect dependencies in `config/project-governance.toml`.

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
.venv/bin/mypy src
git diff --check
.venv/bin/python scripts/check_project_governance.py
```

Update this status, governance configuration, relevant work package, risk
register, and technical-debt register when a milestone changes project state.
