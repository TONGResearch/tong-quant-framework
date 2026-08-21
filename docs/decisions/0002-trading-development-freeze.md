# ADR 0002: Trading Development Freeze

Status: Accepted

## Decision

Paper Trading, Broker Integration, Orders, Trades, Fills, Live Trading, Asset
Allocation, Auto Rebalancing, and execution-side functionality remain frozen
while critical historical evidence is below the governance promotion gate.

## Rationale

Execution capability built on unsuitable PIT evidence would make mechanical
completeness look like investment reliability. Data continuity, calibration,
database recovery, and validation evidence take priority.

## Exit

Exit requires reviewed PIT readiness of at least `CAUTION` for critical replay
datasets, verified provider-consistency evidence, resolved critical conflicts,
updated risk review, and explicit architecture approval from Tong.
