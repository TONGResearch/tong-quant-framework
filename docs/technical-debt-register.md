# Technical Debt Register

Recovery-baseline follow-up (October 18): accumulated hardening is consolidated
as one reviewed local checkpoint with an explicit handoff. Historical slice
notes remain snapshots. Remote synchronization requires separate approval;
ignored data and raw evidence still need approved encrypted recovery. Continue
authoritative launch inputs and one real strategy chain before Paper acceptance.

Research-bar follow-up (October 18): duplicate/revision warm-up, daily-series
ambiguity, module entry checks, invalid lookbacks and Technical return indexing
are repaired in versioned research modules. Complete authoritative session and
action-aware semantics, extreme numeric stress and exact original-input binding
before broader claims. Deep immutable snapshots/concurrent mutation handling
and legacy report reassessment remain open; no automatic re-score is allowed.

Artifact-portability follow-up (October 18): registered provider bytes now have
an explicit-root deterministic read-only audit. The runbook's generic artifact
path was corrected. Complete an approved encrypted DB-plus-files recovery drill,
separately inventory unregistered rule/notice captures, and verify on another
host. This slice does not implement encryption, copying, retention or a global
atomic DB/filesystem snapshot. Existing backup audit hashes alone do not prove
equality of all domain row contents.

| ID | Priority | Debt | Current control | Exit condition |
|---|---|---|---|---|
| TD-001 | P0 | AKShare cannot reconstruct complete historical publication timing, status history, or universe membership. | Conservative trust levels and warnings. | Verified PIT provider coverage and reconciliation tests. |
| TD-002 | P0 | Corporate-action announcement timing and dated adjustment factors are incomplete. | Strict PIT mode rejects adjusted bars. | Reproducible PIT adjustment-factor pipeline. |
| TD-003 | P1 | Existing analytical tables lack many foreign keys. | Repository contracts and tests. | Staged table rebuilds after orphan audit. |
| TD-004 | P1 | SQLite storage is a large ownership monolith. | Module-level repositories isolate callers. | Split storage modules behind one transaction manager. |
| TD-005 | P1 | Notification delivery is at-least-once after a crash; a provider may receive a duplicate when delivery succeeded but acknowledgement was not persisted. | Deterministic outbox identity and lease recovery. | Provider idempotency keys or delivery reconciliation. |
| TD-006 | P1 | Dead letters require operator review; no scheduler or operational dashboard exists. | Persistent dead-letter audit table. | Defined worker, alerting, replay, and retention procedures. |
| TD-007 | P1 | Runtime framework snapshots remain partly caller supplied. | Stored version and configuration hashes. | Runtime snapshot factory verifies Git state and effective config. |
| TD-008 | P2 | Portfolio and Risk calculations remain explainable heuristics. | Proposal-only semantics; no execution. | Calibration against validated samples, covariance, liquidity, cost, and tail-risk evidence. |
| TD-009 | P2 | Live provider behavior can drift between scheduled checks. | Twice-weekly isolated probes, deterministic fakes, owner-assigned health reports, acknowledgement rules, repeated-condition thresholds, and 90-day artifacts. | Accumulate a representative horizon, approve longitudinal SLOs, and calibrate provider fallback policy. |
| TD-010 | P2 | No enforced coverage threshold or property-based PIT tests. | CI runs Pytest, Ruff, and mypy across both `src` and operational `scripts`. | Coverage policy plus timestamp and migration property tests. |
| TD-011 | P1 | Legacy `DataIngestionPipeline` remains directly typed to `AkShareAdapter`. | New providers use `ProviderEvidenceAdapter` and `ProviderNeutralIngestionService`. | Migrate remaining AKShare dataset jobs to provider-neutral orchestration without breaking canonical consumers. |
| TD-012 | P2 | Baseline `SCHEMA` still creates the legacy schema on a fresh database. | `0000` baseline, pre-migration physical fingerprint validation, and migration checksums fail closed. | Generate a frozen baseline artifact and make all future DDL migration-owned. |
| TD-013 | P1 | SQLite concurrency behavior is not load-tested and has no documented writer policy. | WAL, short transactions, and a tested multi-query read snapshot protect authoritative portfolio reconstruction. | Explicit busy-timeout policy, writer operating model, broader contention tests, and exact-content binding at future consumption. |
| TD-014 | P2 | Generated readiness evidence can drift from its committed code baseline. | Reports carry timestamps and query scope. | Freeze report manifest with Git commit, config hash, database snapshot hash, and generated artifacts. |
| TD-015 | P1 | Direct CNInfo and Yahoo/Massive contracts lack representative real continuity baselines. | Distinct provenance, immutable observations/attempts, deterministic calibration, conservative trust, and contract monitoring. | Review sustained CNInfo parity and real Yahoo/Massive agreement, corrections, actions, identifiers, delistings, and missing periods. |
| TD-016 | P1 | The new provider baseline has not yet accumulated a representative observation horizon. | Immutable manifests, input references, separate success/coverage/continuity metrics, per-scope evidence summaries, CI cache, and 90-day content-addressed bundles are active. | Review at least 12 consecutive weeks, account for every missing period, and freeze an accepted evidence snapshot outside ephemeral CI cache. |
| TD-017 | P1 | Verified local recovery exists, but backup scheduling, free-space checks, and recurring retention execution remain manual. | Read-only audit, online backup, isolated restore drill, hashes, row counts, mode `0600`, recovery runbook, and verified AES-256 iCloud rotations for the October 8 and first provenance-qualified October 12 evidence artifacts. | Complete recurring recovery exercises and an approved encrypted off-device rotation schedule without adding cloud credentials to Tong Quant. |
| TD-018 | P2 | Governance verifies explicit markers and files but cannot prove every document is semantically consistent. | Authority order, work packages, CI audit, and mandatory state updates. | Add structured status generation or deeper semantic validation when drift is observed. |
| TD-019 | P1 | Provider artifact files are external to SQLite backup/restore. | Content-addressed storage, immutable metadata, file hashes, safe relative keys, and transaction-failure cleanup. | Add artifact inventory verification and coordinated encrypted backup/restore drills. |
| TD-020 | P1 | Massive calibration is optional and has no committed real evidence baseline. | Missing credentials or permissions persist as `unavailable`; fixtures cannot raise trust. | Accumulate reviewed real comparisons across symbols, actions, gaps, and multiple calendar periods. |
| TD-021 | P1 | Evidence reassessment can consume provider-monitor SQLite history, but no durable representative operational snapshot has completed its full horizon. | A read-only exporter, content-addressed no-overwrite archive, and repeatable isolated restore-drill command verify embedded SQLite history and operational evidence. The October 12 observation has local and encrypted iCloud copies; the October 15 observation passed artifact, temporary archive, and restore verification. Each required scope has 2/8 scheduled checks and 2.9/84 qualified days. | Durably replicate the October 15 artifact, then pass the five-scope horizon audit and preserve at least 12 weeks of checks, baselines, calibration attempts, artifact observations, and conflict history; maintain independent restore review. |
| TD-022 | P1 | MACD, KDJ, Granville, and triple-average event definitions, warm-up rules, and parameter versions are not frozen as research contracts. | A design reservation defines family ownership, explicit event semantics, and conflict preservation. | Approve versioned formulas, market calendars, missing-bar behavior, and invariant tests in `WP-RESEARCH-001`. |
| TD-023 | P0 | Point-in-time market cap and historical eligible-universe evidence are insufficient for unbiased size/style research. | Size is reserved as context only and cannot affect an assessment while evidence is unready. | Verified historical shares, prices, lifecycle state, universe membership, liquidity, and corporate actions pass a reviewed readiness gate. |
| TD-024 | P1 | Portfolio percentages are not yet calibrated by validated edge, covariance, capacity, transaction cost, lot size, or market-specific execution constraints. | Portfolio outputs remain research artifacts and Execution remains disabled. | Complete validated sizing research, constrained optimization review, Paper Trading evidence, and execution-readiness approval. |
| TD-025 | P1 | Replay readiness-dataset declarations are explicit but still caller-owned rather than derived from a central dataset dependency registry. | Queries are hashed, cannot omit all readiness datasets, and fail closed for every declared dependency. | Add a versioned Research/Replay input registry that maps each evidence feature to canonical provider datasets and rejects undeclared transitive dependencies. |
| TD-026 | P0 | Market quantity, sellability, and price-limit rules lack complete runtime exchange, board, settlement, and account evidence. | A reviewed SSE reference profile and limited dated evaluator cover ordinary auction quantities, settled lots, odd remainders and daily bands. A read-only PIT inventory now exposes stored calendar/status/close/action inputs and explicit evidence gaps; unsupported contexts reject calculations. | Populate an operational database through existing ingestion; supply reviewed calendar/price provenance, phase/action coverage and account-lot inputs, remaining intraday/cost constraints, and exact-content simulation binding before market-specific Paper Trading. Extend other markets separately. |
| TD-027 | P0 | Future simulation and execution contracts still need authoritative policy provenance and approval authority. | Portfolio checks verify persisted lineage and freshness; the policy can be sourced from effective settings, but its Validation hash is empty and fails closed by default. Execution remains disabled. | Review and pin a real Validation configuration hash, bind the resulting policy hash to future simulation records, and require separate short-lived approval tied to exact artifacts, market, and broker before any live promotion. |
| TD-028 | P1 | The monitor database exports empty calibration and conflict ledgers; run-origin references still require external verification. | New runs record schedule/manual provenance and GitHub run references; the versioned horizon auditor excludes old `unknown` runs, and the human gate rejects empty ledgers as agreement. Live trading remains frozen while controlled Paper engineering proceeds separately. | Independently verify claimed GitHub events/artifacts and supply real versioned calibration/conflict evidence before PIT reassessment; never infer origins for old runs. |
| TD-029 | P0 | Existing pre-lineage PortfolioProposal rows and future simulation intents lack complete authoritative validation lineage. | New portfolio writes preserve typed evidence; read-side checks reverify lineage and freshness. Live execution remains disabled. | Define legacy-row ineligibility/reconstruction and require the read-side check at the future paper-intent boundary, together with independent PIT and market-rule gates. |
| TD-030 | P0 | Paper Trading has no deterministic ledger, fill model, cost model, restart recovery, or reconciliation implementation. | The paper package is empty and cannot reach a broker; `WP-PAPER-001` remains planned behind launch hardening. | Pass deterministic, idempotency, stale-data, cost, market-rule, recovery, and reconciliation tests without any live submission path. |
| TD-031 | P1 | Risk uses volatility/drawdown/correlation proxies; candidate max_drawdown and scenario targets are not consumed. | Proposal-only semantics, corrected classification routing, validated configuration/input contracts, and versioned outputs. | Define and calibrate portfolio risk estimands, covariance, FX and targeted stress scopes; represent missing data explicitly before authoritative simulation risk use. |
| TD-032 | P1 | Same-version instrument upserts can alter security-master history. | Bar/calendar versions now reject conflicts; security-master snapshots retain available_at but still merge fields at a shared key. | Add per-field provenance and immutable correction semantics with migration and compatibility tests; do not treat generic lot_size as verified evidence. |
| TD-033 | P1 | SQLiteStore exceeds 5,000 lines and owns many domains. | One tested transaction/snapshot manager and ordered, fingerprinted migrations remain authoritative. | Extract domain query/writer ownership in bounded steps while preserving public APIs, migration checksums and one unit of work. |
| TD-034 | P2 | DataFrameCache publication is not atomic and corrupt cache files propagate read errors. | Original frame serialization, declared fingerprints and credential-like fields are now checked on cache reads/writes; exact price reconstruction fails closed. Cache is still research infrastructure, not authenticated PIT storage. | Atomically publish bounded files and make corrupt entries observable cache misses; preserve source timestamp/metadata integrity, raw-content verification and credential restrictions. |
| TD-035 | P1 | Broader corporate-action formats, issuer confirmation and complete coverage remain unverified. | The 26-row mapping defect is fixed for supported gross per-basis descriptions, producing 33 events with LOW/RETRIEVAL_TIME semantics. Rejections are transactional; cache replay inserts zero duplicates and conflicting same-key writes roll back. | Extend only reviewed field/unit grammars, establish issuer/event identity and independent coverage/continuity, and distinguish repeated observations from cumulative adjustments before any adjustment use. |
| TD-036 | P0 | Legacy backdated AKShare market/numeric rows, fabricated-zero turnover and ambiguous corporate-action units may exist in other databases. | New normalization uses retrieval visibility, LOW trust, versioned cache parameters and explicit new action units, without rewriting prior observations. Price/action ingestion stops placeholder company-metadata replacement. | Inventory retained databases and rebuild/mark legacy records ineligible using verified raw provenance; do not infer numeric revisions or canonical action units from old labels. Lost source history cannot be recreated by code. |
| TD-037 | P1 | Previously persisted provider records/artifacts were admitted by a VERIFIED-only ceiling check; declared capability trust is not independently authenticated. | New neutral ingestion rejects every upward trust violation and mismatched capability identity before publication, without silently altering records. | Audit retained record/artifact provenance against the capability version applicable at ingestion. Where that version was not retained, report trust as unverified rather than inferring it from the current adapter; preserve original rows and require separate reviewed reassessment. |
| TD-038 | P1, repaired for new writes | Replacement writes/query-only manifest ids could overwrite or relink replay results. | Replay v0.6.3.3 uses content-addressed run identities, manifest-owned sample ids, insert/compare conflict rejection and atomic repository publication. Exact retries are idempotent; sample content hashes exclude generation time. | Preserve legacy results; past overwrites cannot be recovered automatically. This does not make all upstream artifacts immutable; see TD-040. |
| TD-039 | P0, partially repaired | Exact session alignment, full price-source authentication and corporate-action/cost semantics are not yet proved for historical outcomes. | Exact UTC calendar endpoints replace first/last fallbacks; horizon/lag, decision-visible baseline revisions, bound price content and independent request recomputation are tested. Missing/unsupported inputs remain blocked; PIT remains UNSUITABLE. | Add explicitly versioned exchange-session-aware metrics only with reviewed calendar/source/action coverage. Unadjusted price-only changes are not total investment returns or fills; no real historical strategy validation claim is supported yet. |
| TD-040 | P1, content identity repaired; transitive provenance open | Report-id-only hashing omitted full research/evidence content and original input lineage. Report header writes already rejected duplicate ids; child evidence replacement and repeated module assessment appends were the actual mutable paths. | Replay v0.6.3.4 binds full report/evidence/policy and visible input-row inventories; requests recheck hashes/derived fields and block nested defects. Evidence conflicts require new identities; previous replay snapshots remain intact. | Prove exact original consumed inputs, request/config versions and provider artifact bytes. Reconstructed visible rows do not prove original consumption; hashes cannot authenticate a self-consistent forgery or recover pre-publication lost history. |

October 16 TD-026 progress: the SSE notice adapter now captures 14 explicit
dates and source bytes through neutral ingestion; typed runtime reads retain
MEDIUM/retrieval-time evidence and flag conflict/expiry without changing the
canonical calendar. This is partial source coverage, not resolution of TD-026.
Complete calendar composition, ordinary/emergency-day provenance, price binding,
phase/action coverage and account/settlement evidence are still required. The
adapter is not part of the scheduled five-scope monitor; adding observations
must not redefine or automatically satisfy its existing evidence horizon.

Further TD-026 progress: a reviewed complete annual notice and verified
effective weekday references now produce a separate ordinary SSE schedule.
Every annual assertion and captured notice bytes are required; future,
expired, missing or conflicting inputs stay unknown. This closes ordinary
composition only within the reviewed 2026/July-6-onward scope, not actual
emergency closure, settlement, security status or historical PIT coverage.
The plan does not replace sessions or supply trusted calculation inputs.

Subsequent TD-011/TD-026 progress: unadjusted AKShare equity/index daily bars
now enter the neutral evidence transaction with canonical-row writes and
source-bound frame artifacts. Other typed AKShare jobs remain legacy paths.
The runtime inventory now exposes exact price bindings, but independent source
review and current artifact verification are still open. It currently reads
all visible evidence for a symbol before filtering the runtime window; add
indexed observed-date selection before large historical/revision volumes are
operationalized, without silently dropping incomplete or conflicting records.

TD-019/TD-013 follow-up: artifact publication/rollback cleanup also needs
concurrency-safe reference ownership before parallel writers share one root.
A failed creator must not delete bytes another committed batch references.
Current single-worker ingestion tests prove transaction rollback, not that
cross-process filesystem/SQLite race is solved.

TD-026/TD-036 follow-up: the suspension endpoint/forecast-inference defects are
repaired for new captures and AKShare calibration; 13 real reported starts now
have archived frame provenance, LOW trust and retrieval-time availability.
Old `instrument_status_suspended` rows and unversioned suspension/resumption
events/calibration reports remain unverified and must be audited before use.
The SSE inventory flags them without deleting originals; other legacy read
paths have not fully adopted shared eligibility/quarantine review. Complete
ST, confirmed resumption, listing phase and temporal coverage remain open.

Further TD-026/TD-036 progress: the reusable lifecycle review contract is now
used by runtime v1.6 and lifecycle coverage. Original records are retained;
invalid/wrong-period/wrong-security evidence cannot raise coverage and mixed
trust uses the weakest retained record. Finish adoption at remaining raw-reader
and historical-report boundaries, with reviewed artifact/issuer provenance;
structural REVIEWABLE is not independent verification. Local broker UI data
has not been captured/verified; screen observations must not become PIT history.

Real-pilot coverage follow-up: the scoped manifest quantifies the current
six-date history and configured 15-bar count deficit, retains absent financial/
universe/status inputs, and separates exact bindings from source trust.
These measurements do not resolve TD-026/TD-039/TD-040. Expand exploratory
history and current financial observations through existing ingestion, then
prove original-time availability, phase/action continuity, financial units,
source authenticity and exact research consumption before eligibility claims.

Financial-data follow-up: new neutral native snapshots avoid the legacy
normalizer's assumptions. Before routing real native data into canonical
facts, review currency/unit assumptions, metric/statement identity, consolidation/period
basis and revision linkage. Native records are evidence for that review, not
eligible growth/valuation inputs or proof that original historical revisions exist.
The October 17 numeric repair preserves zero, handles nullable/blank values
and rejects conflicting aliases with atomic rollback. It does not repair
old stored facts or resolve the remaining semantic assumptions.
The October 18 fact-writer repair rejects same-hash material disagreement,
conflicting rows in one batch, nonfinite values and concurrent conflicts.
Call-local savepoints prevent partial writes when callers catch an exception.
An explicit later version preserves earlier PIT views, but the writer does
not authenticate source timing or automatically correct old records. Separate
legacy audits and a reviewed correction workflow remain open before reprocessing
canonical facts; never repair them by overwrite.

Research-boundary follow-up (October 18): context validation and financial
latest-version selection now reject mixed subjects/metrics, future queue/
metadata/periods and ambiguous fact content. Financial diagnostics expose
units/trust/precision and include fact availability. This does not resolve
source-evidenced accounting mappings or implement numerical fundamental scoring.
Further hardening must review bar ordering/duplicate bars, direct module APIs,
deep immutability and exact consumed-input provenance. A mutable nested context
rechecked at run entry is not a concurrency-safe frozen research snapshot.

Deployment follow-up (October 18): wheel/console smoke coverage and offline
preflight now exist; source bytes must match the explicit commit and checkout.
Dependency ranges are still not locked. Complete clean-host reproducibility,
reviewed artifact retention/signing, verified encrypted DB/source-artifact
portability and target-host recovery before a production release. The current
local wheel is a temporary research test artifact, not a release candidate.

Native dependency follow-up: runtime/dev/build pins, package hashes, manifest
binding and actual version checks now exist for macOS arm64/Python 3.12.
The fresh venv install and full suite close the borrowed-site-packages test
gap. Linux/Windows/Intel profiles, signed release/wheelhouse retention and
independent-machine recovery remain open. jsonpath source build is constrained
but not claimed sandboxed or byte-reproducible. Linux CI does not consume the
macOS lock; add native target verification before expanding supported hosts.
