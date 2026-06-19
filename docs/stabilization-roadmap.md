# Recommended Roadmap After Stabilization

This roadmap defines readiness work only. It does not start a new product
version or authorize Paper Trading, Broker Integration, Execution, Asset
Allocation, or automatic orders.

## Gate 1: Operate The Hardened Foundation

- Exercise lease recovery and dead-letter review in deterministic worker tests.
- Define backup, restore, migration dry-run, and database integrity procedures.
- Audit existing databases for orphaned analytical rows.

## Gate 2: Improve PIT Evidence

- Prioritize historical security master, ST/suspension intervals, delisted
  coverage, index constituent entries and exits, filing timestamps, and revisions.
- Reconcile a second provider against AKShare rather than replacing trust labels
  by assumption.
- Build dated corporate-action factors before permitting adjusted histories.

## Gate 3: Calibrate Research And Risk

- Measure ResearchReport and ValidationReport reconstruction coverage.
- Calibrate confidence against missingness and provider trust.
- Replace portfolio-risk heuristics only when historical evidence supports the
  additional complexity.

## Gate 4: Paper Trading Design Review Only

- Define hypothetical ledger ownership and separation from real capital.
- Specify deterministic market-event replay, fees, slippage, partial fills,
  suspensions, price limits, settlement, and corporate actions.
- Define promotion gates and failure criteria.
- Keep all live providers, broker credentials, and execution-side objects out of
  the design review.

No implementation should begin until the earlier gates have evidence and the
user explicitly approves a separate architecture proposal.
