# Engineering Stabilization Review

## Scope

This phase improves reliability, auditability, and data honesty across the V0.8
research platform. It adds no trading strategy, Paper Trading, Broker,
Execution, Order, Fill, automatic rebalancing, or asset-allocation behavior.

## Changes

### Notification Hardening

- Dispatch claims carry an explicit lease expiration.
- Expired claims return to retry when attempts remain.
- Expired final attempts and permanent failures enter a persistent dead-letter
  table.
- Credential-like assignments are rejected by domain, repository, and low-level
  SQLite persistence boundaries.
- Delivery errors remain reduced to safe exception class names.

### Database Engineering

- Ordered migrations are recorded with immutable checksums.
- The exact migration head is stored separately from the public schema version.
- Research and Validation final-run persistence is atomic.
- The new dead-letter relationship uses an enforced foreign key.
- Existing-table foreign keys are deferred to staged, audited rebuilds.

### PIT Audit

Every active AKShare dataset is classified in `data-trust-matrix.md`. No dataset
has been silently promoted. Current company, universe, ST, suspension, financial,
and index-constituent data remain retrieval-time knowledge unless stronger
historical evidence is integrated.

### Documentation

`architecture.md` is the canonical current architecture. Historical V0.6 review
notes are explicitly marked as superseded where later milestones resolved them.

## Maturity Assessment

Tong Quant is a credible research-platform prototype with strong domain
boundaries, reproducibility contracts, and improving operational persistence.
It is not capital-ready. Data provenance and historical completeness remain the
main limit on research validity; execution remains intentionally disabled.

| Area | Assessment |
|---|---|
| Architecture boundaries | Strong for a personal research platform |
| Notification reliability | Hardened baseline; operational worker controls still pending |
| Database integrity | Improving; migrations and transactions exist, legacy FKs remain |
| PIT data quality | Explicitly classified but materially incomplete |
| Validation and replay | Structurally capable; confidence limited by source data |
| Portfolio and Risk | Research-grade heuristics only |
| Trading readiness | Not ready and intentionally disabled |

## Paper Trading Architecture Review

Design review may begin only after migration backups, dead-letter operations,
PIT provider priorities, and validation calibration gates are accepted. A future
design must remain downstream of Research, Validation, Portfolio, and Risk; use
the same deterministic decision contracts; maintain a separate hypothetical
ledger; model market rules, fees, liquidity, slippage, and partial fills; and
contain no live broker adapter. This is a readiness boundary, not an
implementation proposal or approval.
