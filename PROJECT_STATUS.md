# Tong Quant Project Status

This is the canonical short handoff for developers and AI agents. Read it with
`AGENTS.md` and `config/project-governance.toml` before changing code.

## Current Baseline

- Framework version: `0.8.0`
- Database schema version: `0.8.1`
- Migration head: `0009_provider_contract_run_origin`
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
- Provider monitor run-origin metadata: new GitHub-scheduled runs retain an
  auditable run/attempt reference, local or dispatched runs are manual, and
  pre-migration runs remain `unknown`. The current horizon gate counts only
  recorded scheduled runs toward its 84-day/eight-check requirement.
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
independently verified on October 9. The original horizon audit was ineligible
with 36.8 days outstanding under its former all-run count. All five required
scopes still carry expected
provider/data-limitation degradation, with no new implementation defect in the
latest run. The five stable warnings are acknowledged in
[GitHub issue #1](https://github.com/TONGResearch/tong-quant-framework/issues/1)
without promoting provider trust or PIT readiness. Elapsed calendar time alone
is not evidence, and the package cannot promote trust or PIT readiness
automatically.

The October 8 interim scope review found that its original 17-check count did
not encode scheduled versus manual run origin. Migration `0009` preserves those
old runs as `unknown`; a new version of the horizon auditor therefore counts
zero proven scheduled checks in that immutable snapshot. Future scheduled runs
record GitHub run and attempt identifiers for independent review. The new
84-day span starts with the first provenance-qualified scheduled run; the old
36.8-day deficit is not its remaining time. The monitor
database's empty calibration and conflict ledgers are not evidence of
cross-provider agreement.

On October 10, the October 8 artifact was retained in two independently
verified durable copies: a private local content-addressed archive and a
separate AES-256 encrypted sparse-bundle in private iCloud Drive. The encrypted
copy was detached, remounted from its final destination, and reverified before
CloudDocs reported a caught-up state. This closes the current two-copy storage
gap, but it does not satisfy the outstanding 84-day evidence horizon or promote
PIT readiness.

An isolated restore drill from the private local October 8 archive also passed
on October 10: the restored provider-history database matched the source audit
hash, schema fingerprint, migration head, and table counts. An independent
restore drill from the mounted encrypted iCloud copy also passed on October 10:
the restored audit hash matched the source (`2b2173cf...329eeba8`), with 17
contract runs, 85 checks, 17 baseline manifests, and matching table counts.
The encrypted volume was detached after the drill. The drill is now a repeatable
`archive_provider_evidence.py restore-drill` command with fail-closed tests and
credential-free, path-free summary output. Archive verification also rejects
bundled contract-run, check, or baseline identities absent from its embedded
SQLite history. Both retained copies are recoverable, but this does not close
the 84-day evidence-horizon deficit or change PIT readiness.

On the current `0.8.1` code, restoring the retained `0.8.0` snapshot applies
the `0009` migration in the isolated copy, so its post-migration audit hash is
expected to differ from the untouched source. Table counts and historical
records remain intact.

The October 10 post-migration manual Actions smoke test
([run #18](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38065714984))
passed on commit `539b676`. Its downloaded artifact matched the GitHub SHA-256
digest and passed archive verification and an isolated restore drill. The
database is at `0.8.1`/`0009`, with 18 runs, 90 checks, and 18 baselines.
The new run is recorded as `manual` with its GitHub run reference; all five
scopes have zero provenance-qualified scheduled checks. This verifies deployment
and recovery, not the evidence horizon or PIT readiness.

The first provenance-qualified scheduled observation is
[run #19](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38227888290),
completed successfully on October 12 from commit `539b676`. The Actions event,
run JSON, and SQLite row independently agree on `scheduled` origin and GitHub
run `38227888290` attempt 1. Its artifact digest `0c817d5a...cd490` matched the
downloaded ZIP; archive verification and an isolated restore drill recovered
19 runs, 95 checks, and 19 baselines with matching source/restored audit hashes.
Each required scope now has 1/8 provenance-qualified scheduled checks and a
0/84-day qualified observation span. The retained local archive ID is
`367af4cd...80444`. The time gate cannot become eligible before approximately
January 4, 2027, and eligibility would still require uninterrupted evidence,
an independent provenance review, a second durable copy, and a separate PIT
readiness reassessment. PIT readiness remains `UNSUITABLE`.

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
