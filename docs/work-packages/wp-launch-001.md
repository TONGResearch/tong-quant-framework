# Work Package: WP-LAUNCH-001

Status: `ready`

## Current implementation slice

The October 18 [reviewed local baseline](../reviewed-baseline-2026-10-18.md)
consolidates the eighteen continuation slices. This is a recoverable code
checkpoint, not acceptance of this package, remote CI, encrypted recovery,
source trust or Paper/live readiness. The historical slice reports retain
their original per-slice verification and checkout-state observations.

- [Research bar integrity](../research-bar-integrity-2026-10-18.md) fixes duplicate
  warm-up, same-observation revision selection, direct-entry context checks and
  Technical N-interval returns/window requirements. Shared input checks reject
  ambiguous/adjusted/nonfinite daily series without deleting raw observations.
  This is not source/session authentication or a launch acceptance pass.

- [Native dependency baseline](../dependency-baseline-2026-10-18.md) adds
  hash-checked native runtime/dev/build locks, exact version drift checks and
  a resolver-report compiler. A fresh venv installation and quality suite now
  supplement the initial reused-dependency smoke test. Scope is macOS arm64 /
  CPython 3.12 / macOS 14+ only; jsonpath source build is explicit. No signing,
  independent target-host, Paper or live acceptance is claimed.
- [Offline deployment preparation](../research-deployment-runbook.md) adds an
  installed research console command, explicit-root configuration and read-only
  host preflight. Runtime/checkout/committed Python bytes must agree; clean Git,
  safe settings, governance and SQLite integrity remain required. Local wheel
  installation was exercised outside checkout; CI smoke checks are configured,
  not yet remotely run. No data, Paper, sandbox or live readiness is promoted.
- [Research input integrity](../research-input-integrity-2026-10-18.md) rejects
  mixed instruments/metrics, future queue/metadata/periods and ambiguous fact
  versions before a run starts. Latest financial diagnostics use period and
  visible revision, not tuple order, with explicit units/trust/precision. This
  does not authenticate accounting semantics or freeze all nested input data.
- [Fundamental fact integrity](../fundamental-fact-integrity-2026-10-18.md)
  rejects silent same-hash semantic conflicts and conflicting batch/concurrent
  writes. Savepoints preserve atomic calls inside caller transactions; new
  explicit versions preserve PIT history. This does not validate native metric
  semantics or authenticate source timing, and legacy facts remain unaudited.
- [Financial numeric hardening](../financial-numeric-hardening-2026-10-17.md)
  repairs legacy zero/nullable/alias handling and rejects inconsistent values
  atomically. It does not resolve unreviewed metric/unit/period semantics or
  convert native observations into eligible fundamentals. Complete the
  evidenced mapping checklist before canonical financial population.
- [Exploratory data expansion](../exploratory-data-expansion-2026-10-16.md)
  adds real 187-date price history and 13,000 native statement observations in
  a separate research database, plus 30 bounded direct CNInfo metadata rows.
  Neutral snapshot capture retains unknown units and retrieval-time values;
  no canonical financial/research/validation completion is claimed. Original
  operational data is unchanged. Next: reviewed metric/unit mapping and source,
  status, universe and action coverage, not direct paper/live enablement.
- The [real SSE coverage manifest](../sse-pilot-coverage-2026-10-16.md) now
  inventories scoped runtime and research inputs in one read-only snapshot.
  The real sample retains six price dates, a 15-bar configured-count deficit
  and 21 requirement codes without favorable inference or readiness promotion.
  Next: extend exploratory history/current financial capture through existing
  ingestion, not backdated historical eligibility. Source time and scoped-
  empty/global-table distinctions remain explicit.
- [Research-content binding](../replay-research-binding-2026-10-16.md) now pins
  full report/evidence/policy contents and visible input inventories in replay
  hashes; nested defects block eligibility without hiding diagnostic samples.
  Request creation rechecks content, derived fields, query cutoffs and manifest
  membership. Evidence writes are immutable/idempotent. Original consumed-input
  and raw-provider provenance remain open; next is a real pilot coverage manifest.
- The [exact outcome/immutable replay slice](../replay-outcome-integrity-2026-10-16.md)
  replaces first/last fallback with exact UTC calendar endpoints, horizon/lag
  checks and separate start/outcome visibility. Bound prices are independently
  recomputed at ValidationRequest creation. Immutable manifest-owned sample
  publication is atomic and idempotent; old results are not rewritten. Full
  original-run input binding, exchange-session/action-aware returns and
  authenticated source coverage remain open. No Paper/live work is enabled.
- The [replay status slice](../replay-status-review-2026-10-16.md) binds original
  status and shared review to replay hashes and blocks unreviewable status at
  both replay confidence and ValidationRequest creation. Valid adverse status
  is preserved without a missing-input penalty. One reconstruction snapshot
  and atomic report/sample writes prevent mixed reads and stranded manifests.
  Full source validity and outcome coverage remain open; the subsequent slice
  above repairs new replay publication identity/immutability.
- The [shared lifecycle usability review](../lifecycle-usability-review-2026-10-16.md)
  gives runtime v1.6 and timeline coverage one structural review policy. It
  preserves original records and distinguishes observation-only from logical
  quarantine, excludes wrong-scope/invalid records from scoring, and uses the
  weakest retained trust instead of averaging lifecycle trust upward. This is
  not raw artifact authentication or complete downstream quarantine enforcement.
- The [suspension repair](../suspension-evidence-repair-2026-10-16.md) disables
  the delisted-quote endpoint misused as a current suspension list and removes
  forecast/end-date resumption inference, including AKShare calibration.
  A real dated capture now archives 13 LOW/retrieval-time reported starts and
  source frames atomically; no current status or confirmed resumption is
  created. Runtime v1.5 retains lifecycle observations with explicit legacy
  and coverage gaps. ST/phase/complete status and resumption proof remain open.
- The [ordinary SSE calendar slice](../sse-calendar-plan-2026-10-16.md)
  adds a separate rule-backed schedule, not canonical TradingSession writes.
  A verified annual source and all 46 explicit claims are required; original
  rule capture and bounded raw-byte checks preserve source integrity. Missing,
  future, conflicting or expired inputs remain unknown. Runtime v1.4 retains
  raw gaps and does not promote the derived plan into calculation authority.
- The [price-evidence slice](../daily-price-evidence-2026-10-16.md) now saves
  unadjusted AKShare equity/index rows and exact source/raw-snapshot evidence
  through one neutral ingestion transaction. Original cache serialization is
  retained and checked; artifacts must reconstruct normalized rows exactly.
  Runtime v1.3 exposes exact previous-close matches without promoting LOW
  trust or claiming current artifact verification. The real six-row primary
  capture preserves all earlier fallback observations. Price binding exists;
  independent source/runtime review is still incomplete.
- The [official SSE notice slice](../sse-calendar-notice-evidence-2026-10-16.md)
  captures 14 explicit dates and raw bytes through the existing neutral path.
  Typed MarketDataService reads expose these records in the same runtime
  snapshot. Missing days are not filled; conflicts and review expiry are
  preserved. The real sample has MEDIUM/retrieval-time evidence, not complete
  calendar provenance; reader version advances to v1.2 without schema changes.
- The prerequisite provider-neutral evidence gate now rejects every trust
  promotion above a declared capability, including LOW-to-HIGH, for both
  records and artifacts. Capability provider identity is checked before fetch;
  trust checks run before artifact publication or SQLite writes, even with
  relaxed PIT mode. Fifty trust-matrix cases plus identity/relaxed-PIT tests
  cover this repair. It does not supply missing runtime provenance or
  authenticate a provider's self-declared ceiling. Existing stored rows are
  unchanged and need an explicit provenance audit (`R-036`, `TD-037`).
- The [project-wide audit](../architecture-audit-2026-10-15.md) records the
  current fixes, residual risks, dependency map, and continuation plan.
- Portfolio and Risk factories read the same effective Settings; candidate
  sector/country/theme classifications are preserved. Model versions advance
  to `v0.7.1` so old results cannot silently acquire corrected semantics.
- Authoritative portfolio reconstruction and lineage checks use one read
  snapshot. Risk inputs reject unnormalized or duplicate position sets, and
  acceptable risk cannot carry unresolved breaches or required adjustments.
- Versioned market-rule evidence coverage is implemented with exact
  market/exchange/board/account scopes, PIT visibility, half-open effective
  intervals, trust checks, deterministic hashes, and ambiguity rejection.
  The [SSE main-board pilot](../sse-main-board-pilot.md) now adds reviewed,
  hash-verified official source capture and dated ordinary-equity calculations.
  A read-only runtime inventory now reads stored calendar/security/close/action
  inputs through MarketDataService in one snapshot and reports exact gaps.
  It preserves closed dates, low trust and exceptional statuses; it cannot
  manufacture trusted context, normal-listing status or action-free flags.
  Reviewed runtime provenance, account readers and full simulation integration
  are still absent. The default local business database was missing in the
  October 16 inspection; no database was initialized for this diagnostic.
- The [subsequent real sample](../operational-data-sample-2026-10-16.md) now
  populates that operational path through the existing pipeline. New market
  ingestion uses actual retrieval visibility, preserves company metadata and
  unknown turnover, and rejects silent success when normalization accepts no
  rows. Matched publication metadata cannot backdate numeric values. Source
  corrections do not authenticate legacy rows; reviewed context remains open.
- The [corporate-action repair](../corporate-action-mapping-2026-10-16.md)
  now maps the 26-row real payload to 33 research events using corroborated
  units, provider implementation labels and explicit ex-dates. Row rejections
  and event counts are transactional audit data. Same-key conflicts reject
  writes; cached replay inserts zero duplicates. Legacy units are not migrated
  and all new actions stay LOW/RETRIEVAL_TIME; this is not coverage completion.
- Portfolio candidates and proposals carry typed, persisted ResearchReport,
  InvestmentAssessment, InvestmentScore, and ValidationReport lineage.
- Repository writes verify authoritative identity, status, value, timestamp,
  configuration hash, and validation model version before saving the proposal
  and its children in one transaction. Reusing a proposal identifier is rejected
  rather than silently replacing persisted evidence.
- Conditional validation and low-confidence investment assessments cannot
  produce an unconditional proposal.
- A read-side PortfolioEvidenceGate rechecks authoritative lineage at the
  decision timestamp, with an explicit age/version/configuration policy and
  deterministic policy hash. Passing this structural check is not Paper or
  live-trading authorization.
- The policy can now be constructed from effective project settings. The
  checked Portfolio and Validation model versions come from their settings;
  age limits and the Risk model version are explicit configuration. The
  validation configuration hash is empty by default, so this construction
  fails closed until a reviewed run hash is pinned in an override. Changing
  the pinned hash changes the deterministic policy hash and requires review.
- Cash remains visible in exposure reports but no longer breaches sector,
  country, or theme concentration caps merely because it is a large buffer.
  Existing proposals and RiskAssessments are not rewritten; they need new
  proposal identities and fresh verification before future simulation use.
- A-share sellability and price-limit calls now fail closed when dated rule
  evidence is absent.
- US, Hong Kong, and Malaysia sellability and price-limit calls also fail
  closed. Their former same-day-sell and unrestricted-price defaults were not
  backed by account-specific settlement or effective-dated exchange evidence.
- All four markets' buy/sell quantity helpers now fail closed too. The former
  A-share buy helper could accept the generic Instrument default lot size of
  one, and the global helpers rounded with an unverified stored lot size.
  These context-free helpers remain disabled. The separate typed SSE pilot
  requires verified reference documents and dated runtime evidence; its
  calculation output cannot authorize a simulated quantity by itself.
- Remaining before this package can complete: review and pin an authoritative
  validation configuration hash, supply reviewed runtime pilot inputs and
  remaining intraday/cost restrictions, and bind the structural check and
  exact calculation hashes to the future simulation-intent boundary.
  No simulation or live trading is authorized by this partial slice.

## Objective

Remove the known authority, lineage, and market-rule gaps that would make even
Paper Trading misleading, while preserving the live-execution freeze.

## Next bounded implementation

1. Retain and extend the corrected real corporate-action sample without
   treating supported positive events as full coverage. Unsupported syntax,
   legacy units and issuer confirmation remain explicit gaps. Do not
   substitute monitor history or fixtures for operational inputs.
2. Add independently reviewed exchange-calendar and price-source provenance
   through the existing provider-neutral evidence/artifact contracts.
   Legacy TradingSession and Bar rows lack complete provenance bindings. The
   partial notice alone cannot compose ordinary days. A separate annual-notice
   and weekday-rule builder now reconstructs the ordinary schedule; actual
   exceptional closures and independent price review remain open.
   New unadjusted prices now carry exact raw-snapshot bindings; legacy rows
   cannot inherit them merely from equal closes.
3. Establish dated listing-phase and corporate-action coverage evidence.
   No matching event is not evidence of no event; LISTED is not normal phase.
   Partial suspension source capture now exists, but does not establish current
   status or complete ST/resumption/phase coverage. Audit retained legacy
   suspension snapshots, inferred resumptions and calibration outputs before
   considering them eligible evidence.
   Shared runtime/coverage review now exists; immutable originals and reports
   still need full provenance reconstruction, and unadapted raw readers must
   not treat a structural review result as historical validation approval.
4. Add read-only account-lot and confirmed-settlement provenance only within
   approved package boundaries, then bind verified inputs to calculation
   hashes. No broker connection or paper ledger belongs to this inventory.
5. Complete the existing intraday/cost, policy and simulation-boundary gates.

The repeatable diagnostic is `scripts/inspect_sse_runtime_inputs.py`; see the
pilot document for explicit arguments and exit-code semantics. Its input hash
identifies reconstructed content, not the entire database or a readiness pass.

## Dependencies

October 18 portability hardening adds a bounded read-only provider-artifact
registry/file audit. Both operational and exploratory registries verify 4/4
files against their different explicit roots. This does not complete encrypted
backup, independent-host recovery, full capture inventory or any acceptance
gate. See `docs/artifact-portability-2026-10-18.md`. Schema and PIT are unchanged.

- `WP-VALIDATION-001`: historical replay data-quality eligibility gate

## Scope

- Replace free-form validation status strings with versioned domain states.
- Preserve ValidationReport identities from PortfolioCandidate through
  PortfolioProposal and RiskAssessment.
- Verify identity, status, version, freshness, and configuration binding before
  creating any downstream simulation intent.
- Introduce effective-dated market-rule capability declarations.
- Fail closed when exchange calendar, settlement, board, suspension, ST, or
  price-limit evidence required by a market is unavailable.
- Keep `ExecutionDisabledGuard` authoritative for every live OrderFactory and
  Broker entry point.

## Acceptance Gates

- Conditional or unreliable validation cannot be interpreted as accepted.
- Artifact identifiers alone are insufficient; repositories must verify the
  referenced record and state.
- A-share placeholder T+1 and price-limit logic cannot authorize simulated or
  live execution.
- Tests cover stale, missing, mismatched, conditional, and rejected evidence.
- No live credential, live order, or broker submission path is introduced.

## Non-Goals

- No live trading.
- No broker order submission.
- No automatic strategy promotion.
- No reduction in PIT or provider trust requirements.
