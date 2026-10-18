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

### Reviewed Recovery Baseline: October 18

Tong approved consolidating the eighteen local continuation slices in a local
Git commit without pushing. The [baseline review](docs/reviewed-baseline-2026-10-18.md)
records scope, installed-wheel/source identity, quality checks and unresolved
acceptance gates. The commit containing that report is the recovery checkpoint;
use Git for its exact identity. The slice-specific uncommitted/test-count notes
below are historical checkpoints, not the current checkout state. A local
commit is not remote/off-device retention. PIT stays UNSUITABLE and production
NOT_READY; execution and notifications stay disabled. Next: approved encrypted
data/artifact recovery and remaining authoritative launch inputs, not live use.

- Provider-neutral evidence contracts and transactional ingestion
- Provider-neutral ingestion now enforces every trust-level ceiling for both
  records and raw artifacts before any persistence, and rejects capabilities
  declared under another provider identity. This repairs the former
  VERIFIED-only check, not source quality or historical completeness. Existing
  stored evidence is not reclassified; see risk `R-036` and debt `TD-037`.
  The October 16 repair adds 52 regression cases; full verification reports
  535 passed / 6 skipped, Ruff and mypy pass, and governance/diff checks pass.
- The [SSE notice evidence slice](docs/sse-calendar-notice-evidence-2026-10-16.md)
  captures 14 explicit dates and source bytes through neutral ingestion. Typed
  reads include them in the same runtime snapshot, preserving MEDIUM trust,
  retrieval-time visibility, conflicts and review expiry. It neither merges
  into the open-only calendar nor proves a complete exchange schedule.
  That slice used `sse-runtime-input-v1.2`; schema is unchanged.
  Notice-slice verification: 558 passed / 6 skipped, Ruff and mypy pass
  (208 source/script files), governance passes 63 checks, and diff checks pass.
- The [daily-price evidence slice](docs/daily-price-evidence-2026-10-16.md)
  now commits unadjusted AKShare bars, exact row/source/availability bindings,
  raw-frame artifacts and audit records in one neutral ingestion transaction.
  Cache reads retain original serialization and verify hashes; snapshot bytes
  must reproduce normalized prices exactly. The real sample adds six new
  bar/evidence observations without overwriting older versions. Its primary
  source matches the earlier fallback's six OHLC/native-volume observations,
  but this is not independent calibration. Trust remains LOW/retrieval-time;
  runtime v1.3 exposes exact matches and unresolved review requirements.
  Price-slice verification: 576 passed / 6 skipped; Ruff, mypy (210 source/script
  files), governance (64 checks), and diff checks pass. No schema change or
  readiness promotion; the three continuation slices remain uncommitted.
- The [ordinary SSE calendar slice](docs/sse-calendar-plan-2026-10-16.md)
  binds the reviewed annual notice, 46 explicit assertions and verified
  effective weekday references to a separate deterministic calendar plan.
  Runtime v1.4 keeps raw sessions unchanged, rechecks annual artifact bytes,
  and preserves unknown/conflicting/expired inputs. The October 1-16 window
  has 7 planned open and 9 planned closed days, not verified actual opening.
  Ordinary-calendar verification: 593 passed / 6 skipped; Ruff, mypy (212 source/script
  files), governance and diff checks pass. Schema/readiness are unchanged;
  all four continuation slices remain uncommitted and unpushed.
- The [suspension evidence repair](docs/suspension-evidence-repair-2026-10-16.md)
  disables the misrouted delisted-quote/current-suspension endpoint and removes
  unconfirmed resumption inference from normalization and AKShare calibration.
  Versioned dated captures now archive source frames and LOW/retrieval-time
  events in one neutral transaction, preserving company metadata. Runtime v1.5
  retains lifecycle evidence and flags legacy records without assuming normal
  ST/suspension/listing status. The real 13-row capture created 13 reported
  starts and zero confirmed resumptions; full status coverage remains open.
  Schema/readiness are unchanged; the five continuation slices are uncommitted
  and unpushed. Suspension-slice verification: 621 passed / 6 skipped; Ruff, mypy (213
  source/script files), governance (66 checks), database integrity and diff
  checks pass.
- The [shared lifecycle usability slice](docs/lifecycle-usability-review-2026-10-16.md)
  separates reviewable, observation-only and logically quarantined records.
  Runtime v1.6 and lifecycle coverage use the same review policy; invalid,
  legacy or wrong-scope rows cannot improve coverage, and weak trust cannot
  be averaged upward. All originals remain preserved. Local MooMoo UI reading
  timed out; no displayed data, permissions or broker capabilities were
  verified. Framework/schema/readiness and disabled execution are unchanged.
  All six continuation slices remain uncommitted/unpushed; final check results
  and remaining raw-reader/calibration boundaries are recorded in the report.
- [Replay status review](docs/replay-status-review-2026-10-16.md) now applies
  shared usability review at replay and ValidationRequest boundaries. Version
  v0.6.3.2 binds source records/review metadata and rejects invalid/observation-
  only status without dropping adverse-status samples. Reconstruction shares
  one read snapshot; manifest/sample persistence is atomic. Framework/schema
  and real-readiness conclusions are unchanged; all seven slices are local,
  uncommitted and unpushed. Latest verification: 670 passed / 6 skipped; Ruff,
  mypy (214 source/script files), governance (69 checks), database integrity
  and diff/whitespace checks pass.
- The [deployment gap plan](docs/deployment-gap-plan-2026-10-16.md) defines five
  remaining delivery groups, starting with trustworthy launch inputs and one
  real validated strategy chain, then Paper, sandbox/deployment and separately
  approved live work. The local sample has no real research/validation/portfolio
  reports; software test count is not a trading-readiness percentage.
- The [outcome/persistence integrity slice](docs/replay-outcome-integrity-2026-10-16.md)
  advances replay/confidence to v0.6.3.3. Exact UTC calendar endpoints, horizon
  and availability lag replace moving first/last-price windows; start prices
  use decision-time visibility. Missing/unsupported outcomes remain blocked
  samples. The request factory recomputes bound outcomes. New manifest/sample
  writes are immutable, owner-bound, idempotent and atomic, with separate run
  identities but stable economic sample hashes. No schema or real-readiness
  promotion occurs. Latest verification: 699 passed / 6 skipped; Ruff, mypy
  (215 source/script files), governance (70 checks), read-only database audit
  and whitespace checks pass. Eight continuation slices are local/uncommitted/
  unpushed. Upstream full research-content hashing remains open (TD-040).
- AKShare data foundation and quality audit
- [Research-content binding](docs/replay-research-binding-2026-10-16.md) advances
  replay/confidence to v0.6.3.4 and binds full report/evidence/policy content
  plus visible fundamental/screening row inventories. Missing/conflicting or
  future nested evidence blocks eligibility, with diagnostic samples preserved.
  ValidationRequest rechecks content hashes, manifest mapping and derived
  research fields. Evidence writes now reject conflicting identity reuse.
  Correction: report header writes already reject duplicate ids; mutable child
  evidence and duplicate module assessments were the actual defects. Latest
  verification: 744 passed / 6 skipped; Ruff, mypy (216 source/script files),
  governance (71 checks), database audit and whitespace checks pass. No schema
  change or readiness promotion. Nine slices remain local/uncommitted/unpushed.
  Next: real SSE pilot coverage manifest with exact blockers, not fixture-based
  strategy approval. Original-run input lineage/source attestation stays open.
- Optional Tushare capability and calibration adapters
- The [real SSE coverage manifest](docs/sse-pilot-coverage-2026-10-16.md) now
  reads runtime and research inputs in one read-only snapshot. The actual
  Oct 1-15 price window/Oct 16 cutoff has six bound price dates with LOW/
  retrieval-time evidence, a 15-bar deficit against the configured minimum,
  absent scoped status/fundamentals/universe/research and 21 unresolved
  requirement codes, not 21 development phases. Protected optional JSON
  exports remain ignored local data, not a readiness promotion or Git backup.
  Latest verification: 752 passed / 6 skipped; Ruff, mypy (217 source/script
  files), governance (72 checks), database and whitespace checks pass. No
  schema/readiness change; ten slices remain local/uncommitted/unpushed.
  Next: extend explicitly exploratory history and current financial/disclosure
  capture through existing ingestion, without backdating or trust inflation.
- CNInfo disclosure evidence through explicit AKShare transport provenance
- [Real exploratory expansion](docs/exploratory-data-expansion-2026-10-16.md)
  collected 187 unadjusted dates, 13,000 native rows across three statements
  and 30 direct CNInfo metadata records in a separate research database. Four
  price/financial artifacts passed hash checks; the original business database
  is unchanged. The native financial evidence path uses neutral transactions,
  preserves unknown units/missing values and creates zero canonical facts or
  research/validation reports. Pilot inventory v1.1 exposes native/metadata
  counts separately. Current numerical trend warm-up deficit is zero in the
  exploratory sample, not a strategy or PIT pass. Latest checks: 762 passed /
  6 skipped; Ruff, mypy (218 source/script files), governance (73 checks), both
  database audits and whitespace checks pass. Eleven continuation slices stay
  local/uncommitted/unpushed. Next: reviewed financial metric/unit mapping and
  source/status/universe coverage. Five final acceptance groups remain open;
  no calendar completion date or defensible trading-readiness percentage exists.
- Yahoo US/Hong Kong/Malaysia research-grade daily-bar evidence
- [Financial numeric hardening](docs/financial-numeric-hardening-2026-10-17.md)
  fixes a confirmed legacy zero/alias-selection defect, handles missing values
  without inventing zero, and rejects conflicting/nonfinite numeric inputs.
  Twenty new regression cases include atomic rollback. Legacy ingestion now
  warns explicitly about unreviewed semantic/unit assumptions; real native
  observations remain on the noncanonical capture path. Latest verification:
  782 passed / 6 skipped; Ruff, mypy (218 source/script files), governance and
  whitespace checks pass. No schema, database, trust or readiness change;
  twelve continuation slices remain local/uncommitted/unpushed. Next: review
  evidenced metric/unit/period/industry mappings before canonical population.
- [Fundamental fact integrity](docs/fundamental-fact-integrity-2026-10-18.md)
  now rejects same-hash material disagreements and within-batch/concurrent
  conflicts instead of silently accepting ignored inserts. Writer reservation
  plus a savepoint keeps each call atomic even inside a caller transaction.
  Original values, versions and audit metadata remain unchanged on repeats;
  invalid legacy numerics are flagged, not repaired. Verification: 808 passed /
  6 skipped; Ruff, mypy (218 source/script files), governance and whitespace
  checks pass. No schema/data/readiness promotion or trading-module changes.
  Thirteen continuation slices remain local/uncommitted/unpushed; next is
  evidenced metric/unit/period mapping, not simulation or live enablement.
- [Research input integrity](docs/research-input-integrity-2026-10-18.md)
  binds bars/facts to the candidate and metric, rejects future queue/metadata/
  report periods and conflicting fact versions, and rechecks before a run
  starts. Financial diagnostics select by period and visible version instead
  of input order and expose original trust/unit/availability labels. The
  financial module is `financial-v0.5.1-input-integrity`; no automatic scoring
  or canonical unit mapping is added. Verification: 840 passed / 6 skipped;
  Ruff, mypy (218 source/script files), governance and whitespace checks pass.
  Framework/schema/readiness are unchanged. Fourteen slices remain local/
  uncommitted/unpushed. Native-to-canonical mapping/source review remains next.
- [Offline research deployment preparation](docs/research-deployment-runbook.md)
  adds the installed `tong-quant` command, explicit-root startup and offline
  preflight. Runtime/checkout/commit Python bytes, safe effective configuration,
  dependencies, governance and read-only database integrity are checked without
  authorizing trading. A wheel was installed into an isolated temporary target
  and exercised outside checkout with verified package origin/version. CI smoke
  checks are configured but have not run remotely. Verification: 862 passed /
  6 skipped; Ruff, mypy (219 source/script files), governance and whitespace
  checks pass. Current release preflight remains blocked by uncommitted source
  and dirty Git; database content audit is unchanged. Fifteen continuation
  slices remain local/uncommitted/unpushed. No schema, PIT, production or live
  promotion. Next: reviewed clean-release/dependency/restore evidence alongside
  source-evidenced financial mapping and the existing strategy/Paper gates.
- [Native dependency baseline](docs/dependency-baseline-2026-10-18.md) now pins
  35 runtime / 48 dev packages plus four build tools with artifact hashes and
  scoped manifests. New clean-venv installation, import isolation, installed
  console and version checks passed without borrowing the PyCharm environment.
  Preflight v1.1 checks actual locked versions; macOS arm64/Python 3.12 and
  macOS 14+ scope is explicit, not a universal lock. Verification: 884 passed /
  6 skipped in both environments; Ruff, mypy (221 source/script files),
  governance and whitespace checks pass. Source-build, signing and independent
  host limits remain explicit. Sixteen slices are local/uncommitted/unpushed;
  schema, data, PIT and live readiness remain unchanged. Next: reviewed clean
  release and encrypted restore/artifact portability, alongside strategy inputs.
- [Registered artifact portability](docs/artifact-portability-2026-10-18.md)
  adds a bounded read-only registry/file audit, safe explicit-root reads and
  deterministic reference/report hashes. Both local databases verify 4/4
  registered files; the corrected runbook distinguishes their different roots.
  This is not a full database-content hash, encrypted backup, independent-host
  restore or unregistered-capture inventory. Verification: 905 passed / 6
  skipped; Ruff, mypy (223 source/script files), governance (80 checks) and
  whitespace checks pass. Seventeen continuation slices remain local,
  uncommitted and unpushed. Schema, PIT, production and execution are unchanged.
  Next: consolidate/review the local changes and perform approved encrypted
  recovery, while advancing independently authorized strategy/data inputs.
- [Research bar integrity](docs/research-bar-integrity-2026-10-18.md) now gives
  Technical/Trend/Pattern one checked daily-observation selector. Duplicates
  and revisions cannot inflate warm-up; conflicting versions, intraday-shaped
  input, mixed sources, adjusted and nonfinite inputs fail closed. Direct
  calls recheck context visibility. Technical N-interval returns and window
  requirements are corrected; all three model versions are centralized.
  Verification: 956 passed / 6 skipped, Ruff and mypy (224 source/script files)
  pass; governance passes 81 checks and whitespace checks pass. No source/PIT/
  session authentication or strategy acceptance is claimed. Eighteen slices
  remain local/uncommitted/unpushed. Next: consolidate/review the accumulated
  changes, then establish an approved recoverable baseline and complete
  authoritative launch inputs before the planned Paper package can advance.
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
  `database_missing` without creating it. A subsequent
  [real ingestion exercise](docs/operational-data-sample-2026-10-16.md) created
  a local research sample: six distinct daily bars (12 observed versions),
  8,797 open-date rows and current company information. It also exposed
  backdated availability, fabricated fallback turnover and placeholder
  metadata replacement; new ingestion now fixes those behaviors and preserves
  old observations. Numeric facts no longer inherit earlier visibility/trust
  from matched publication events. The subsequent
  [corporate-action repair](docs/corporate-action-mapping-2026-10-16.md) now
  maps those 26 source rows to 33 research events. Two fresh observations are
  retained; replaying one cached snapshot inserts zero duplicates. Units,
  provider-labelled implementation and ex-dates are checked, with rejected
  rows preserved in audit warnings. All new actions remain LOW/RETRIEVAL_TIME.
  Zero or partial normalization remains partial, not absence of actions. Runtime
  evidence categories remain unresolved. Reviewed provenance, listing-phase,
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
