# Work Package: WP-LAUNCH-001

Status: `ready`

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
