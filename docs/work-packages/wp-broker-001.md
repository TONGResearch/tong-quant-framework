# Work Package: WP-BROKER-001

Status: `planned`

## Objective

Add read-only and provider-native sandbox connectivity after the deterministic
Paper Trading ledger is complete.

## Dependencies

- `WP-PAPER-001`: deterministic paper trading ledger

## Scope

- Moomoo OpenD capability, account, position, permission, and paper-account
  discovery on macOS.
- Guojin QMT/PTrade entitlement, runtime, API-version, and simulation checks.
- Safe timeout, retry, reconnect, heartbeat, and reconciliation contracts.
- Environment-only credentials with repository-level persistence rejection.
- Explicit separation between paper/sandbox and live account identifiers.

## Acceptance Gates

- Default configuration cannot unlock or submit a live order.
- Read-only diagnostics never require a trading password in Tong Quant storage.
- Account-environment mismatches fail closed.
- Network integration tests are disabled by default.

## Non-Goals

- No live order submission.
- No unattended trading.
- No live credential persistence.
