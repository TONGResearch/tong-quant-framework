# Work Package: WP-RESEARCH-001

Status: `planned`

## Objective

Implement PIT-safe, explainable Technical Confluence and Size/Style Research
after the longitudinal evidence and readiness gates permit new research work.

## Scope

- Add pure, versioned MACD and KDJ indicator calculations.
- Add parameterized bullish/bearish candle-body crossing-three-average events.
- Add PIT-safe setup-state transitions without backward follow-through labels.
- Add Granville moving-average relationship events by rule family.
- Add Style Research using PIT market capitalization and historical universe
  percentiles.
- Add family-aware confluence that caps correlated technical evidence.
- Reuse existing Fundamental, Value, Trend, ATR, Industry, Policy, and Market
  Regime research rather than duplicating them.

## Inputs

- Completed `WP-EVIDENCE-001` representative evidence horizon.
- Reviewed post-horizon PIT readiness for bars, lifecycle, universe,
  fundamentals, corporate actions, and market-cap history.
- Existing ResearchContext, ResearchEvidence, ResearchAssessment, and
  ResearchReport contracts.
- Market-specific configuration with frozen calculation and warm-up rules.

## Deliverables

- Pure indicator and moving-average event functions.
- TechnicalConfluenceAssessment and StyleAssessment research contracts.
- Research module integration with no execution dependency.
- Deterministic unit and integration tests.
- PIT replay fixtures with future-data and incomplete-bar rejection.
- Validation factor names and ablation-ready evidence outputs.
- Updated architecture and research documentation.

## Acceptance Criteria

- MACD/KDJ calculations match frozen reference fixtures and document seed,
  smoothing, warm-up, and zero-range behavior.
- Confluence counts each evidence family once and preserves conflicts.
- Triple-average setup follow-through never enters the original decision
  context.
- Size buckets use the historical eligible universe and PIT market cap.
- Missing lifecycle, universe, market-cap, or required bar evidence produces
  `INSUFFICIENT_DATA`.
- Dynamic stops remain research invalidation references, not orders or
  guaranteed fill assumptions.
- No module imports Execution, Broker, Order, Trade, Fill, Paper Trading,
  Notification, or Portfolio.

## Non-Goals

- No strategy profitability claim before Validation.
- No whole-market highest-score purchase rule.
- No Portfolio optimization or position sizing change.
- No Paper Trading, broker integration, Order, Trade, Fill, Live Trading,
  automatic execution, or auto rebalancing.
- No readiness promotion based on indicator availability.

## Required Verification

- Indicator reference and property tests
- PIT and no-lookahead tests
- Correlated-evidence and conflict tests
- Market-specific tests
- Pytest
- Ruff
- mypy
- `git diff --check`
- Governance audit

## Handoff Notes

This package must remain `planned` while `WP-EVIDENCE-001` is incomplete or
critical input datasets remain below the separately approved readiness gate.
Read `docs/technical-research-extension.md` before changing status.
