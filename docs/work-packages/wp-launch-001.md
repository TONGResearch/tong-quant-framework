# Work Package: WP-LAUNCH-001

Status: `ready`

## Current implementation slice

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

1. Locate or explicitly populate an operational research database via the
   existing ingestion pipeline; do not substitute monitor history or test
   fixtures for operational market inputs.
2. Add independently reviewed exchange-calendar and price-source provenance
   through the existing provider-neutral evidence/artifact contracts. Current
   TradingSession and Bar rows have no trust/precision/raw-hash binding.
3. Establish dated listing-phase and corporate-action coverage evidence.
   No matching event is not evidence of no event; LISTED is not normal phase.
4. Add read-only account-lot and confirmed-settlement provenance only within
   approved package boundaries, then bind verified inputs to calculation
   hashes. No broker connection or paper ledger belongs to this inventory.
5. Complete the existing intraday/cost, policy and simulation-boundary gates.

The repeatable diagnostic is `scripts/inspect_sse_runtime_inputs.py`; see the
pilot document for explicit arguments and exit-code semantics. Its input hash
identifies reconstructed content, not the entire database or a readiness pass.

## Dependencies

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
