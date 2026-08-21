# Work Package: WP-DATA-003

Status: `completed`

## Objective

Calibrate Yahoo daily bars against an independent provider without making the
framework depend on paid credentials.

## Scope

- Define the comparable unadjusted daily-bar contract.
- Implement deterministic offline provider fixtures first.
- Add optional real-provider probes when credentials or public access exist.
- Compare identifiers, sessions, OHLCV fields, gaps, and corporate-action dates.
- Persist disagreement and unavailable-provider evidence.

## Acceptance Criteria

- Calibration runs with offline fixtures and no token.
- Real-provider absence is `unavailable`, never agreement or zero coverage.
- Adjusted and unadjusted series cannot be compared as equivalent.
- Yahoo remains `LOW/RETRIEVAL_TIME` until reviewed evidence supports change.

## Non-Goals

- No requirement to purchase Massive, Finnhub, or another provider.
- No real-time feed, execution, broker, or order work.

## Completion Record

- Added a provider-neutral unadjusted daily-bar calibration contract covering
  instrument identity, exchange session, OHLCV, gaps, and corporate-action
  dates.
- Added deterministic offline Yahoo/independent fixtures with explicit `as_of`;
  fixture evidence cannot claim trust above `LOW` or precision above
  `RETRIEVAL_TIME`.
- Added optional Massive US evidence through official aggregate, dividend, and
  split endpoints. Requests force `adjusted=false`; credentials remain in the
  Authorization header and never enter URLs, reports, logs, or SQLite.
- Added immutable `completed`, `unavailable`, and `incompatible` calibration
  attempts. Missing provider access cannot create a consistency report.
- Added trust-ceiling enforcement so consistency and confidence cannot exceed
  the weakest explicitly supplied provider trust.
- Added fake-client, fixture, migration, conflict, security, and idempotence
  tests. Real Massive evidence remains optional and unverified.
