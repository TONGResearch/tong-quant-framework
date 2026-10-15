# Tong Quant Project Status

This is the canonical short handoff for developers and AI agents. Read it with
`AGENTS.md` and `config/project-governance.toml` before changing code.

## Current Baseline

- Framework version: `0.8.0`
- Database schema version: `0.8.2`
- Migration head: `0010_portfolio_evidence_lineage`
- Current phase: Parallel evidence and controlled launch
- PIT readiness: `UNSUITABLE`
- Production readiness: `NOT_READY`
- Execution default: `disabled`
- Notification default: `disabled`
- Portfolio/Risk model versions: `portfolio-proposal-v0.7.1` / `risk-assessment-v0.7.1`

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
- Portfolio proposals now preserve a typed, persisted research/assessment/
  score/validation evidence chain; repository writes verify that chain against
  authoritative records. A-share sellability and price-limit helpers fail
  closed until effective-dated exchange evidence exists.
- The read-side PortfolioEvidenceGate re-verifies lineage at a decision time
  using explicit freshness, model-version, and configuration requirements;
  cash is exempt from sector/country/theme concentration breaches. This is
  structural research evidence only, not a Paper or live approval.
- Its policy now reads effective project configuration; a reviewed Validation
  configuration hash must be pinned explicitly because the default is empty
  and refuses construction. This provides a controlled policy path, but the
  future simulation boundary must still require it. Paper, PIT, and live
  readiness are unchanged.
- US, Hong Kong, and Malaysia market-rule helpers no longer assume same-day
  sellability or unrestricted prices without dated evidence; they now reject
  those calls until the relevant rule capabilities are supplied.
- Buy/sell quantity normalization for all four markets also rejects calls
  without dated lot and account rules; the generic Instrument lot-size default
  must not become an executable market assumption.
- The [project-wide audit](docs/architecture-audit-2026-10-15.md) repairs lost
  candidate exposure classifications, Portfolio/Risk configuration drift,
  mixed-version proposal reads, stale notification worker acknowledgements,
  and silent same-version bar/calendar replacement. Existing persisted results
  are not rewritten. New Portfolio/Risk model versions distinguish corrected
  research artifacts.
- Market-rule capability coverage now has versioned, PIT-visible declarations,
  exact exchange/board/account scopes, explicit missing/ambiguous states, and
  reproducible evidence hashes.
- The [SSE main-board pilot](docs/sse-main-board-pilot.md) now verifies three
  pinned official documents and calculates ordinary buy increments, confirmed
  settled-lot sellability, odd-lot sell quantities and daily price bands. Its
  typed inputs bind dates, source review, status/classification flags, calendar
  content and calculation hashes. Raw sources are local ignored artifacts
  and can be recaptured on a new device. A read-only runtime input inventory
  now reconstructs stored sessions (including closed dates), status,
  unadjusted previous close and corporate-action observations in one SQLite
  snapshot. It preserves trust and reports missing evidence; it does not
  construct trusted calculation context. On October 16 the default local
  `data/tong_quant.sqlite3` did not exist; the command reported
  `database_missing` without creating it. Reviewed provenance, listing-phase,
  action-coverage and account-lot readers, intraday restrictions and the
  simulation boundary remain incomplete; this does not
  complete `WP-LAUNCH-001` or change PIT/live readiness.

## Controlled Launch Boundary

Paper Trading and broker-native simulation development may now proceed through
the approved work packages below while the 84-day evidence horizon continues in
parallel. Broker work is initially read-only or sandbox-only. Live broker order
submission, unattended trading, live Order/Trade/Fill behavior, Asset
Allocation, Auto Rebalancing, and live execution remain frozen.

The default remains `execution.mode = "disabled"` and
`allow_live_orders = false`. No Paper Trading result or elapsed calendar time
may change those values automatically.

## Next Ready Work

1. `WP-EVIDENCE-001`: representative longitudinal evidence horizon
2. `WP-LAUNCH-001`: execution lineage and market-rule hardening

These packages run in parallel. `WP-LAUNCH-001` must bind every downstream
simulation decision to authoritative Validation, Portfolio, and Risk artifacts;
replace placeholder market-rule assumptions; and preserve the existing
fail-closed live-execution guard. After it completes, `WP-PAPER-001` may become
ready. `WP-BROKER-001` remains planned until the deterministic paper ledger is
complete.

The first `WP-LAUNCH-001` lineage and market-rule hardening slice is described
in [the controlled-launch architecture audit](docs/controlled-launch-architecture-audit-2026-10-15.md).
It does not complete the package or change PIT/live readiness.

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

On the current `0.8.2` code, restoring the retained `0.8.0` snapshot applies
the `0009` and `0010` migrations in the isolated copy, so its post-migration audit hash is
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
`367af4cd...80444`. On October 13, a second independently verified copy was
retained in the AES-256 encrypted private iCloud sparse-bundle. Its archive ID
is `e0b8e0e0...735a0`; verification and an isolated restore drill reproduced
audit hash `9180999a...88711`, migration head `0009`, and matching table counts.
CloudDocs reported the detached sparse-bundle caught up at 15:48 Malaysia time.
The time gate cannot become eligible before approximately January 4, 2027, and
eligibility would still require uninterrupted evidence, an independent
provenance review, and a separate PIT readiness reassessment. PIT readiness
remains `UNSUITABLE`.

The next [scheduled run #20](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38698359370)
completed on October 15 from commit `e6e98d2`, attempt 1. The GitHub schedule
event, artifact digest `053d4704...347733c`, run JSON, and SQLite origin row
were independently matched. The artifact contains 20 contract runs, 100 checks,
and 20 baseline manifests; all five required scopes have 2/8 qualified
scheduled checks across 2.9/84 days. Its evidence bundle and temporary
content-addressed archive passed verification and an isolated restore drill;
the restored copy advanced from schema `0009` to `0010` with matching table
counts. The five pre-existing provider/data-limitation warnings remain, with
no newly observed implementation defect. The calibration-attempt and conflict
ledgers are still empty, so they do not demonstrate provider agreement. The
October 15 artifact still needs durable private-local and encrypted off-device
retention. PIT readiness remains `UNSUITABLE`.

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
