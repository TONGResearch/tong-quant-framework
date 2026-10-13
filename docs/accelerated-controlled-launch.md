# Accelerated Controlled Launch

## Decision

Tong Quant no longer treats the 84-day provider-evidence horizon as a software
development stop. Evidence accumulation and controlled-launch engineering run
in parallel.

This does not lower the evidence standard. It separates three questions:

1. Can the software produce deterministic and auditable research artifacts?
2. Can those artifacts survive a realistic simulation with fees, slippage,
   market rules, reconciliation, and operational failures?
3. Is a specific strategy and dataset mature enough to authorize real capital?

Only the first two questions may be developed while PIT readiness is
`UNSUITABLE`. The third remains fail-closed.

## Delivery Sequence

### Stage 1: Launch hardening

- Preserve authoritative ValidationReport, PortfolioProposal, and
  RiskAssessment lineage through every downstream decision.
- Replace placeholder exchange-calendar, lot-size, settlement, and price-limit
  assumptions required by the selected pilot market.
- Add durable approval, freshness, identity, and configuration checks.
- Keep `execution.mode = "disabled"` and live orders off.

### Stage 2: Deterministic Paper Trading

- Use provider timestamps and only information available at the simulated
  decision time.
- Persist simulated intents, acknowledgements, fills, rejections, positions,
  cash, fees, slippage, and reconciliation differences.
- Model market-specific sessions and constraints.
- Include kill switches, daily-loss limits, notional limits, stale-price
  rejection, duplicate suppression, and restart recovery.

### Stage 3: Broker sandbox and read-only connectivity

- Moomoo OpenD: discover accounts, positions, permissions, and paper accounts
  without unlocking live trading.
- Guojin QMT/PTrade: confirm account entitlement, supported runtime, simulation
  environment, and documented API version before adapter implementation.
- Credentials remain environment or operator managed and never enter SQLite,
  logs, tests, or rendered artifacts.

### Stage 4: Shadow and paper observation

- Run the same decision path on live market timestamps without sending orders.
- Reconcile expected versus simulated fills daily.
- Track latency, stale inputs, rejected actions, turnover, fees, drawdown, and
  operational incidents.
- Continue the independent 84-day provider evidence collection.

### Stage 5: Micro-live review

Micro-live is a separate future approval. It starts with one broker, one market,
manual confirmation, hard capital caps, no leverage, no shorting, and a global
kill switch. It cannot begin from this document alone.

## Pilot Order

1. Moomoo paper accounts on macOS for US or Malaysia equities.
2. Guojin QMT/PTrade simulation after runtime and entitlement verification.
3. A-share live consideration only after effective-dated board rules, exchange
   calendar behavior, T+1 sellability, suspension, ST, and price-limit rules are
   no longer placeholders.

## Non-Negotiable Controls

- Paper objects cannot be submitted through a live Broker interface.
- A missing, stale, conditional, rejected, or mismatched upstream artifact
  fails closed.
- Paper performance is not proof of historical validity or future returns.
- PIT readiness and provider trust remain visible in every run.
- No automatic promotion from Paper to live execution exists.
