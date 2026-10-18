# Tong Quant Architecture Overview

Registered provider-byte portability is checked read-only by
`data.storage.artifact_audit`, exposed through `scripts/audit_provider_artifacts.py`.
It reads one registry snapshot and verifies explicit-root files with bounded
streaming hashes. It neither copies data nor substitutes for database integrity,
encrypted restore drills, provider trust or PIT qualification. See
[artifact portability audit](artifact-portability-2026-10-18.md).

This is the canonical current architecture for the V0.8 research platform and
its engineering-stabilization work. Milestone documents provide detail but must
not override the boundaries in this document.

## Design Decision

Technical, Trend and Pattern share `research.bar_inputs` for visible daily
observation selection and structural validation. Model versions distinguish
corrected N-interval return semantics and duplicate/revision warm-up handling.
This boundary does not infer sessions, source trust or trading authority. See
[research bar integrity and progress](research-bar-integrity-2026-10-18.md).

China A, US, Hong Kong, and Malaysia share the same workflow and domain
contracts. They do not share every market policy or trading rule.

V1.0 remains focused on individual equities. The domain model reserves broader
`Instrument` and `TradableInstrument` language so future versions can add
funds, ETFs, REITs, bond funds, money-market funds, and allocation research
without renaming the current equity workflow.

```text
Provider adapters
      |
Canonical point-in-time data
      |
Discovery -> Hard Screening -> Research Queue -> ResearchReport
                                                    |
                                      InvestmentAssessment + InvestmentScore
                                                    |
                                              ValidationReport
                                                    |
                                       PortfolioProposal + RiskAssessment

ResearchReport / ValidationReport / PortfolioProposal / RiskAssessment
                               |
                     Notification outbox -> Deferred delivery

Universal Signals accompany analytical stages; they do not replace
completed Research, InvestmentScore, or authoritative Validation lineage.

                     Execution remains disabled
      ^
MarketRules + calendar + fees + currency + corporate actions
```

## Market Differences

`MarketRules` is the main boundary for differences such as:

- Settlement and sale eligibility
- Board lot and odd-lot behavior
- Daily price limits and volatility interruptions
- Trading sessions, holidays, and time zones
- Short-selling availability
- Auction and intraday execution rules
- Fees, stamp duty, and currency

The current market-rule helpers reject quantity, sellability, and price-limit
queries until dated evidence and evaluators exist. `markets.capabilities`
inspects versioned evidence for calendar, settlement, quantity, price limits,
and security status within an exact market/exchange/board/account scope.
Intervals use an inclusive start and exclusive end. Future, untrusted, expired,
or overlapping evidence cannot complete coverage. Coverage alone cannot
authorize simulation. The SSE main-board pilot adds reviewed official source
capture and a typed evaluator for ordinary quantity/sellability/daily-band
calculations. Its application-level runtime inventory reads existing PIT data
through MarketDataService in one SQLite read snapshot, preserves explicit
closed dates and corporate-action revisions, and produces hashed input/gap
records. Optional SQLite `read_only=True` uses `mode=ro` and query-only access,
never initializes/migrates or changes journal mode. It is not an authoritative
context builder: reviewed calendar/price provenance, listing-phase/action
coverage, account evidence and full trading restrictions are still missing.
The [real operational sample](operational-data-sample-2026-10-16.md) now fills
an isolated research database through the existing AKShare pipeline. New bars,
calendars and numeric facts retain retrieval visibility; fallback turnover is
unknown when absent, and price/action writes preserve existing company
metadata. The ingestion CLI isolates provider access behind a bounded worker
and reports zero accepted rows as partial. These changes do not migrate old
data, authenticate numeric revisions, or supply trusted calculation context.
The [corporate-action batch parser](corporate-action-mapping-2026-10-16.md)
now corroborates explicit per-basis descriptions with numeric components,
counts accepted input rows separately from events, and persists every row
rejection atomically. Existing PIT-key writes reject conflicting amounts or
metadata; new observations preserve history. New actions are LOW trust,
retrieval-time observations, never automatic price/holding adjustments.
See [the pilot contract and recovery steps](sse-main-board-pilot.md).
Availability precision is separate from trust: unknown, estimated and date-only
timestamps remain incomplete until conservative visibility is established.
Retrieval-time evidence can be used only after capture and keeps that warning.

## Layer Boundaries

### Data

Provider adapters fetch external data. Normalizers convert it into canonical
models. Strategies never call AKShare, Tushare, or brokers directly.

`ProviderNeutralIngestionService` checks capability ownership before fetching
and enforces the full `UNKNOWN < LOW < MEDIUM < HIGH < VERIFIED` ceiling for
records and artifacts before filesystem or database publication. Equal or lower
trust is preserved, not promoted or silently clamped. Relaxing PIT timestamp
checks cannot relax trust checks. Availability precision is independent and
does not raise trust. This structural ceiling is not independent provider
verification; new calendar/price evidence still needs reviewed provenance.
The correction does not rewrite or certify previously persisted evidence.

The SSE calendar-notice adapter binds explicit date assertions to a reviewed
source hash, archives raw bytes through the same neutral transaction, and
retains MEDIUM/retrieval-time limitations. A typed MarketDataService read
includes these records in the SSE inventory's existing SQLite snapshot, without
silently changing canonical sessions or constructing trusted context. Conflicts,
malformed assertions and review expiry are visible. See
[the real capture and remaining limits](sse-calendar-notice-evidence-2026-10-16.md).

The transport-free calendar profile and application-level
`SSECalendarPlanBuilder` combine a complete reviewed annual notice with verified
effective weekday rules. This yields a separate deterministic **ordinary
schedule**, not actual exchange operation or settlement. All annual assertions
and current artifact bytes are required; incomplete, expired, future, tampered
or conflicting sources cannot yield favorable inferred dates. The runtime
reader keeps canonical sessions and raw gaps unchanged, includes plan hashes,
and requires an explicit rule capture. No Paper/market-rule calculation consumes
this plan. See [scope, evidence and remaining gates](sse-calendar-plan-2026-10-16.md).

Unadjusted AKShare daily rows now use the same neutral ingestion unit of work
for canonical rows and source-bound frame artifacts. Cache serialization is
preserved, fingerprints are verified, and reconstruction must match normalized
prices exactly. Read-side inventory exposes exact row/source/time/artifact
bindings while preserving LOW trust and unresolved artifact/source review.
See [the price capture and contract](daily-price-evidence-2026-10-16.md).
Other legacy AKShare datasets remain on their existing typed pipeline; this
does not complete the provider migration or independently authenticate prices.

Dated suspension captures now share this neutral ingestion unit of work:
raw delivered-frame artifact + provider evidence + LOW/retrieval-time reported
start events. The current-suspension snapshot API rejects calls because its
former endpoint returned delisted-market quotes. Reported end and expected
resumption dates remain metadata, never confirmed resumptions; AKShare
calibration uses the same normalizer. Runtime v1.5 reads lifecycle/evidence in
the existing SQLite snapshot and preserves legacy/missing-coverage warnings.
Neither event presence nor absence establishes current ST, suspension, normal
listing phase or tradability. See [repair and real capture](suspension-evidence-repair-2026-10-16.md).

`data.lifecycle_review` now owns structural usability review for lifecycle
events/status records. It retains deterministic original-record hashes,
as-of bounds, dispositions and reason codes. Runtime v1.6 includes these
reviews; lifecycle coverage excludes quarantined/out-of-scope records and
cannot average weak trust into a stronger label. This is logical quarantine,
not database deletion, artifact-byte verification or a current-status clearance.
Raw service reads remain preservation APIs and historical calibration reports
are not silently recertified. See [scope and remaining enforcement boundaries](lifecycle-usability-review-2026-10-16.md).

Replay v0.6.3.4 carries original status/review metadata in decision hashes,
preserves unusable diagnostic samples, and blocks formal validation on invalid
status even when declared trust/readiness looks favorable. The request factory
rechecks current policy, content/instrument/time binding and usability.
Reconstruction uses one SQLite read snapshot; persistence happens afterwards
in one manifest/sample transaction. These structural safeguards do not prove
source truth or real strategy reliability. Exact UTC calendar endpoint prices
now honor horizon/lag and separate visibility cutoffs; missing endpoints do not
shift the window. The request factory recomputes the bound price-only outcome.
Content-addressed manifests and manifest-owned samples reject replacement and
relinking; repository publication is atomic. Full research/evidence/policy
snapshots and visible input inventories now enter sample identity; the request
factory checks nested eligibility, content hashes and derived fields. Evidence
writes reject conflicting identity reuse. Exact original-run context and raw
source attestation, and corporate-action/session-aware outcomes, remain open. See
[the research-content binding repair](replay-research-binding-2026-10-16.md),
[the outcome/immutability repair](replay-outcome-integrity-2026-10-16.md),
[the status-boundary repair](replay-status-review-2026-10-16.md) and
[remaining deployment groups](deployment-gap-plan-2026-10-16.md).

The [SSE pilot coverage manifest](sse-pilot-coverage-2026-10-16.md) composes
existing runtime/data/research readers in one snapshot. It distinguishes
counts, exact price bindings, original trust and unknown session denominators,
lists configured input deficits and preserves missing evidence without
promoting PIT or enabling a strategy. Protected optional exports are new local
metadata files, not another domain persistence path or a backup of source bytes.

Native AKShare financial snapshots now use the same neutral evidence/artifact
transaction, with exact serialized-row binding, LOW/retrieval-time semantics
and unknown canonical metric/accounting unit. They do not populate financial
facts or research scores. The [isolated real expansion](exploratory-data-expansion-2026-10-16.md)
and pilot inventory v1.1 distinguish raw observations, canonical data and
validated research; larger row counts cannot silently advance readiness.
The legacy normalizer now preserves numeric zero and rejects conflicting
value aliases transactionally. Its remaining currency/unit/period assumptions
are explicitly warned, not certified; see the
[reviewed-mapping checklist](financial-numeric-hardening-2026-10-17.md).
Canonical fact persistence now checks all material content under a reserved
writer transaction and call-local savepoint. Same-hash disagreements and
within-call conflicts fail explicitly; retries preserve original content and
audit metadata. See [fact integrity](fundamental-fact-integrity-2026-10-18.md).
This storage guarantee is not source verification or approval of legacy facts.
ResearchContext now revalidates candidate identity, metric binding, visible
queue/metadata/periods and fact consistency before a run starts. Financial
diagnostics select the latest period/visible version deterministically and
retain unit/trust/precision metadata; see
[research input integrity](research-input-integrity-2026-10-18.md).
Caller-owned nested data is not deep-frozen, and accounting/source eligibility
remains a separate gate.

Offline research operations now expose an installed `tong-quant` command and
`application.deployment_preflight`. Preflight composes settings, governance,
installed dependency/source checks and the read-only SQLite integrity service;
it imports no provider SDK, broker, Paper, Portfolio, Notification or Execution
module. Runtime/checkout/commit source hashes and explicit nonauthorization
flags keep host diagnostics distinct from research and trading-readiness gates.
See the [deployment runbook](research-deployment-runbook.md). No service process,
schema migration or automatic recovery is introduced by this command.
Preflight v1.1 additionally composes `application.dependency_lock`: structured
native manifests bind exact requirement text, root specs and build inputs;
installed package versions are checked without SDK imports. Runtime manifest
hashes enter the diagnostic. The resolver-report compiler is an operator tool,
not a runtime dependency resolver or a new persistence path. See the
[native baseline](dependency-baseline-2026-10-18.md) for platform/source-build limits.

Comparable global daily bars use an explicit unadjusted contract:

```text
Yahoo / Massive / deterministic fixture
              |
      ProviderEvidenceAdapter
              |
 exchange session + OHLCV + action dates + price basis
              |
 DailyBarCalibrationCoordinator
              |
 completed | unavailable | incompatible
              |
 SQLite calibration attempt + optional consistency report
```

Agreement is bounded by the weakest declared provider trust. Missing access and
adjusted/unadjusted mismatches never become successful empty comparisons.

### Strategy

Strategies consume immutable, point-in-time inputs and return explainable
signals. A signal is not an order.

The same rule applies to discovery, every screening dimension, research,
market-regime classification, value analysis, trend analysis, events, and AI.
Only the execution package may turn an approved Signal into an Order.

### Validation

Validation audits point-in-time Research and decision outcomes. It does not
simulate orders, fills, Paper Trading, or live execution.

### Risk and Portfolio

Portfolio construction proposes allocation research artifacts. Risk may mark a
PortfolioProposal acceptable, conditional, rejected, or incomplete, but it does
not create or reduce orders.

`PortfolioProposalEngine.from_settings()` configures Portfolio and Risk from
one effective Settings object. Candidate sector/country/theme classifications
flow directly into generic `RiskPositionInput` records and consistent exposure
summaries; holding role and listing market must not replace those fields.
These classifications remain declared research inputs, not independently
verified issuer exposures. Portfolio and Risk model versions are centralized
and checked by governance; the current versions are `v0.7.1`.

Authoritative proposal reconstruction and lineage verification share a SQLite
read snapshot. Risk remains independent of Portfolio domain classes. Risk
estimates are heuristics pending empirical calibration, especially drawdown,
correlation, currency, and multi-theme exposure.

### Execution

Execution is disabled by default. `ExecutionDisabledGuard` and
`ExecutionReadinessGate` fail closed unless future readiness requirements are
explicitly satisfied. Broker adapters remain placeholders and cannot be reached
from Research, Validation, Portfolio, Risk, or Notification code.

## Point-in-Time Contract

Every observation has:

- Observation or event time
- Availability or publication time
- Source

A decision at time `t` may only use records with `available_at <= t`.

## Suggested Future Package Growth

Add concrete modules only when their milestone begins:

- `data/providers/akshare.py`
- `data/calendars/china_a.py`
- `strategies/trend/tong_trend.py`
- `validation/event_driven.py`
- `execution/paper.py`
- `execution/brokers/qmt.py`

This prevents empty framework abstractions from growing faster than working
research code.

## V0.2 Data Foundation

The data foundation now implements the provider, cache, validation,
normalization, SQLite, and point-in-time read boundaries described above. See
`docs/data-foundation.md` for schemas, supported datasets, and limitations.

## V0.3 Market Regime Engine

The regime engine is an analytical layer between point-in-time market data and
future screening, research, portfolio, and strategy systems:

```text
MarketDataService + timestamped external metrics
                    |
              Input Builder
                    |
       Normalized RegimeMetric [-1, 1]
                    |
       Configured weighted classifier
                    |
    MarketRegime + universal WATCH Signal
```

It never creates orders and does not contain a trading strategy. Transition
states remain informational and map to the primary `Sideways` state. Regime is
a weighted decision input, never an automatic approval or rejection. See
`docs/market-regime-engine.md`.

## Data Foundation Hardening

Historical research must reconstruct both what a company reported and which
securities were eligible at the decision time:

```text
FundamentalFact revisions -----> point-in-time fundamental query
UniverseMembership ------------> historical candidate universe
InstrumentStatus --------------> historical tradability and classification
```

These records use separate effective and availability timestamps. Effective
dates describe when a fact or status applies; availability timestamps describe
when the system was allowed to know it. Screening must consume these canonical
queries rather than current company snapshots or today's listed-stock universe.

V0.6.2 adds conservative PIT population around these contracts:

```text
AKShare raw response
        |
Raw schema validation + payload fingerprint
        |
Availability warning + provider limitation audit
        |
Normalized PIT facts / statuses / memberships / corporate actions
        |
PITReadinessAssessment
```

`AvailabilityPrecision` and `DataTrustLevel` are separate. A record can be
available only at retrieval time while still carrying useful medium-trust
content, or it can have an exact date with low confidence in completeness.
HistoricalReplaySource consumes readiness assessments and preserves incomplete
or low-trust reconstruction with warnings; readiness never silently upgrades
provider data.

PIT remediation extends this boundary without introducing trading behavior:

```text
Lifecycle/publication/universe evidence
                 |
HistoricalCoverageEvaluator ---- ProviderCalibrationEngine
                 |                         |
       coverage assessment       consistency report
                 \_________________________/
                              |
             PITReadinessAssessment
             usable | caution | unsuitable
```

Security lifecycle and constituent data accumulate forward from dated
snapshots. Complete historical membership or status intervals are never
invented. Fundamental publication evidence can improve availability timing,
but later revised numeric values are not backfilled into earlier revisions.

Evidence-backed reassessment sits above data collection and below governance:

```text
Phase III artifacts + contract history + baselines + calibration attempts
                              |
                  EvidenceReadinessEvaluator
                              |
       current | proposed | effective classification + blockers
                              |
                  separate human governance review
```

The evaluator is deterministic and content-addressed. Missing values remain
unknown, stale artifacts remain visible, and effective classifications cannot
change automatically. See `docs/evidence-readiness-reassessment.md`.

## Future Asset Classes

The market package reserves this future structure:

```text
markets/
  china_a/
  us/
  hong_kong/
  malaysia/
  funds/
```

The reserved fund branch is documentation and import-safe package scaffolding
only. It does not contain fund screening, fund research, allocation, orders, or
broker integration.

## V0.4 Screening Engine

Screening implements the first complete upstream workflow:

```text
OpportunityCandidate
        |
Ordered Hard Screening ------ failure ------> EXCLUDE Signal
        |
Seven Dimension Assessments
        |
Research Score
        |
Research Queue Entry + RESEARCH Signal
        |
Future Validation
```

Research Queue `priority_score`, `urgency_score`, and `confidence_score` remain
separate values. Research Score helps allocate research attention and remains a
Screening concern. Screening does not own research outcomes or investment
assessment models.

Shared screening orchestration lives in `screening/`. China A, US, Hong Kong,
and Malaysia inject separate market policies for status eligibility, risk
flags, liquidity, and financial-health requirements.

## V0.5 Research Engine

Research consumes V0.4 Research Queue entries and executes only the requested
modules plus their declared dependencies:

```text
Research Queue -> ResearchContext -> Module dependency graph
                                    |
              Policy / Financial / Industry / Value
              Technical / Trend / China A Pattern
                                    |
                  falsifiable ResearchReport
                                    |
                      universal RESEARCH Signal
                                    |
                 InvestmentAssessment + status
                                    |
                       Future Validation
```

Every report contains a thesis, counter thesis, and explicit invalidation
conditions. Confidence combines evidence quality, completeness, module
agreement, and point-in-time integrity with a weakest-link cap. Market Regime
is retained as a research variable rather than a gate. See
`docs/research-engine.md`.

Investment Score is calculated only after a completed `ResearchReport` and
must be interpreted together with `InvestmentAssessmentStatus`. A high score
with low confidence remains a low-confidence opportunity. Incomplete or
insufficient-data assessments do not carry an interpretable score.

## V0.6 Validation Engine

Validation audits stored historical outputs rather than turning research
signals into simulated orders:

```text
Discovery / Screening / Research outputs
                    |
       Pre-registered OutcomeDefinition
                    |
       Point-in-time ValidationSample
                    |
 Historical + Walk-Forward + OOS
 Regime + Thesis + Factor + Accuracy
 Decision Journal + Portfolio Research Risk
                    |
      ValidationReport + REVIEW Signal
```

Research correctness and decision correctness remain separate. Portfolio
validation measures concentration of research attention across country,
industry, theme, and style; it is not portfolio return backtesting.

Every run carries a reproducibility snapshot containing the Git commit,
framework version, configuration hash, research version, validation version,
and database schema version. See `docs/validation-engine.md`.

## V0.6.3 Historical Replay

Historical replay is the bridge from PIT storage to validation samples:

```text
SQLite PIT records
        |
ReplayQuery
        |
HistoricalReplayBuilder
        |
ReplayManifest + ReplayValidationSample
        |
ValidationRequestFactory
        |
Validation Engine
```

ReplayConfidence measures the quality of reconstruction, not research
correctness. ST, suspended, delisted, low-trust, provider-limited, and
incomplete samples remain visible with warnings.

## V0.7 Portfolio And Risk

Portfolio and Risk extend validated research into proposal-only portfolio
construction:

```text
InvestmentAssessment + InvestmentScore + Validation evidence
        |
PortfolioCandidate
        |
PortfolioProposal + PositionProposal
        |
RiskAssessment
```

PortfolioProposal is a research artifact. It is not decision authorization,
execution instruction, or live connectivity request.

RiskAssessment covers concentration, sector, country, theme, correlation,
volatility targeting, drawdown, liquidity, risk budgets, and scenario stress
tests. It can mark a proposal acceptable, conditional, rejected, or incomplete,
but it cannot create orders.

## V0.7.1 Hardening

V0.7.1 hardens the boundary before any V0.8 work:

- Execution defaults to `disabled`.
- `ExecutionDisabledGuard` and `ExecutionReadinessGate` protect future
  OrderFactory and Broker entry points.
- Risk consumes generic `RiskPositionInput` objects instead of importing
  Portfolio `PositionProposal`.
- `SQLitePortfolioRepository` can reconstruct PortfolioProposal,
  PositionProposal, RiskAssessment, exposures, and constraints by proposal id.
- Framework and replay metadata use centralized version constants.
- Notification compatibility is limited to research artifacts:
  ResearchReport, ValidationReport, PortfolioProposal, and RiskAssessment.
  Notification code must not import Execution, Order, Broker, Trade, or Fill
  concepts.

## V0.8 Notification Engine

V0.8 adds research-information delivery without changing execution boundaries:

```text
ResearchReport / ValidationReport / PortfolioProposal / RiskAssessment
                               |
                    Artifact-specific renderer
                               |
               NotificationRecord + deterministic dedup key
                               |
                       SQLite notification_outbox
                               |
                     Deferred dispatcher claim
                               |
                  Telegram / WeChat / Email channel
                               |
                 notification_deliveries audit history
```

`disabled` mode produces no records. `preview` persists rendered records that
cannot be dispatched. `enabled` persists pending records; only the separate
dispatcher may claim and deliver them. Channels receive `NotificationMessage`
objects and never receive domain artifacts directly.

The dedup key is derived from artifact hash, channel, and recipient. Provider
credentials are read from environment variables only and never enter rendered
content, SQLite, or delivery errors. Every message contains the mandatory
research-information disclaimer. See `docs/notification-engine.md`.

## Engineering Stabilization

The hardened Notification outbox uses expiring claims. Orphaned dispatching
records return to retry when attempts remain and move to a persistent dead-letter
record after the final attempt. Delivery remains at-least-once: a process crash
after a provider accepts a message but before the receipt commits can cause a
duplicate, so future channels need provider idempotency or reconciliation.

SQLite uses an ordered checksum-verified migration ledger. Research and
Validation final-run writes use one transaction boundary. Existing analytical
foreign keys will be added only through staged table rebuilds after orphan
audits; this phase does not perform a global schema rewrite.

The authoritative AKShare quality classifications are in
`docs/data-trust-matrix.md`. Current snapshots and provider-limited histories
must not be treated as stronger evidence than that matrix allows.

The remediation evidence and calibration rules are documented in
`docs/pit-data-quality-audit.md`, `docs/historical-coverage-matrix.md`, and
`docs/provider-calibration.md`.

## Provider Evidence Hardening

New provider integrations use `ProviderEvidenceAdapter` and
`ProviderNeutralIngestionService`. Capabilities, point-in-time timestamps, raw
hashes, trust, availability precision, and limitations cross one shared
transactional boundary before evidence reaches SQLite. CNInfo disclosure
evidence retains distinct `cninfo_via_akshare` and `cninfo_direct` provenance.
Direct filing bytes use a content-addressed `ProviderArtifactStore`; SQLite
stores immutable metadata and capture observations. Yahoo unadjusted daily bars
remain unofficial, low-trust, retrieval-time evidence.

The physical database schema is registered by baseline migration and protected
by a canonical fingerprint that is checked before pending migrations. Weekly
provider contract monitoring records access and field health separately from
data evidence. A healthy contract does not upgrade provider trust or PIT
readiness. See `docs/provider-evidence-foundation.md`.

Stored contract checks feed a separate longitudinal baseline builder:

```text
ProviderContractRun + ProviderContractCheck history
                         |
           explicit period + cadence + scopes
                         |
             ProviderBaselineManifest
                 /        |        \
          success    field coverage  continuity
```

Baseline manifests are immutable and content-addressed. Missing scheduled
periods and failed probes remain distinct, and observed trust is reported
without producing a new trust assessment or changing PIT readiness.

The repository-operations path evaluates the latest run against its stored
history without entering the Notification Engine:

```text
ProviderContractRun + prior observations
                    |
          ProviderHealthAssessor
                    |
       ProviderHealthReport (operations only)
          /          |             \
    one-off      repeated       implementation
    condition     condition          defect
```

Only implementation defects fail CI. Repeated degradation or unavailability
requires operator acknowledgement but remains distinct from a code failure.
Reports carry ownership, recovery steps, run/check identities, versions, and
retention metadata. See `docs/provider-monitor-operations.md`.

## Database Engineering Boundary

Database recovery is isolated from domain repositories:

```text
SQLite source (read-only audit)
            |
     SQLite online backup
            |
 same-directory temporary snapshot
            |
 integrity + FK + migration + fingerprint + row-count audit
            |
  no-overwrite destination publication
```

`SQLiteIntegrityService` never initializes or migrates its audited source.
`SQLiteBackupService` may run forward migrations only inside an isolated
restore-drill copy. No active source or existing destination is overwritten.
See `docs/database-backup-restore.md`.

Provider Calibration Phase II adds Tushare behind a canonical calibration
adapter. Consistency reports, individual conflict observations, and dataset
confidence are persisted separately. Credentials remain environment-only, and
calibration is disabled by default. See `docs/provider-calibration-phase-ii.md`.

Execution remains disabled and live orders remain frozen. Controlled-launch
engineering now runs beside provider evidence: `WP-LAUNCH-001` hardens
authority and market rules, followed by a deterministic Paper Trading ledger
and then read-only or provider-native sandbox connectivity. None of these
packages may submit a live order or promote itself to live execution.

## Reserved Technical And Style Research Extension

`WP-RESEARCH-001` reserves a future extension after the longitudinal evidence
and readiness gates. It adds technical and style evidence without creating an
independent indicator-trading stack:

```text
Visible PIT bars + PIT fundamentals + historical eligible universe
                              |
      Technical families + Style context + Fundamental quality
                              |
             conflict-preserving confluence assessment
                              |
                       ResearchReport
                              |
                         Validation
```

MACD and KDJ belong to one momentum family. Moving-average alignment,
Granville events, and triple-average candle events belong to trend structure.
Volume, breadth, and industry heat remain participation evidence. Size is
cross-sectional Style Research and requires PIT market cap plus historical
universe membership. Each family contributes at most once, and no confluence
state is an execution decision. See `docs/technical-research-extension.md`.

The remaining evidence, research, validation, portfolio, operational, broker,
and rollout gates are documented in `docs/execution-readiness-storyboard.md`.

## Historical Replay Data-Quality Gate

Historical Replay keeps reconstruction and research correctness separate, but
only an explicitly eligible reconstruction may become a `ValidationRequest`:

```text
ReplayQuery(required inputs + readiness datasets + minimum trust)
                              |
          PIT reconstruction preserving every subject
                              |
 ReplayConfidence(validation_eligible + blocking reasons)
                              |
      fail-closed ValidationRequestFactory
```

The gate requires visible `USABLE` PIT assessments for every declared dataset,
at least `MEDIUM` trust, no critical missing input, and no silently excluded
sample. ST, suspended, delisting, and delisted subjects remain visible and do
not count as missing merely because their lifecycle state is adverse. Consumed
readiness evidence is selected as of replay generation time and frozen by hash.
See `docs/backtesting-data-assurance.md`.
