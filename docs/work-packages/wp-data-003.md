# Work Package: WP-DATA-003

Status: `planned`

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
