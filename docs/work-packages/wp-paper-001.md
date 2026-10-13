# Work Package: WP-PAPER-001

Status: `planned`

## Objective

Build a deterministic, persistent, auditable Paper Trading ledger that exercises
the future execution workflow without reaching a live broker.

## Dependencies

- `WP-LAUNCH-001`: execution lineage and market-rule hardening

## Scope

- Simulated intent, acknowledgement, rejection, fill, position, cash, fee,
  slippage, and reconciliation models.
- SQLite persistence with idempotency and restart recovery.
- Market-session, lot-size, settlement, liquidity, and stale-price controls.
- Portfolio and account-level risk limits plus a global kill switch.
- Deterministic replay from the same inputs, configuration, and clock.
- Daily operator report and reconciliation evidence.

## Acceptance Gates

- No Paper object implements or wraps the live Broker submission protocol.
- No missing or future data can create a favorable fill.
- Duplicate events cannot duplicate positions or cash movements.
- Fees and slippage are explicit and versioned.
- Crash recovery and reconciliation tests pass.

## Non-Goals

- No live broker submission.
- No automatic promotion to real capital.
- No performance guarantee.
