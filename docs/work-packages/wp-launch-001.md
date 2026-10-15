# Work Package: WP-LAUNCH-001

Status: `ready`

## Current implementation slice

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
- Remaining before this package can complete: review and pin an authoritative
  validation configuration hash, versioned market-rule capability declarations,
  pilot-market fixtures, and binding the structural check to the future
  simulation-intent boundary.
  No simulation or live trading is authorized by this partial slice.

## Objective

Remove the known authority, lineage, and market-rule gaps that would make even
Paper Trading misleading, while preserving the live-execution freeze.

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
