# V0.1 Architecture

## Design Decision

China and global markets share the same workflow and domain contracts. They do
not share every trading rule.

```text
Provider adapters
      |
Canonical point-in-time data
      |
Discovery -> Screening -> Research -> Validation
    |            |           |            |
    +------------+-----------+------------+
                         universal Signals
                               |
                    Portfolio -> Risk veto
                               |
                   Execution creates Order
                               |
                         Broker adapter
      ^
MarketRules + calendar + fees + currency + corporate actions
```

## Market Differences

`MarketRules` is the main boundary for differences such as:

- Settlement and sale eligibility
- Board lot and odd-lot behavior
- Daily price limits and volatility interruptions
- Trading sessions, holidays, and time zones
- Short-selling availability
- Auction and intraday execution rules
- Fees, stamp duty, and currency

The initial `ChinaAShareRules` models only a small safe subset. Board-specific
limits, holidays, commissions, transfer fees, STAR/ChiNext rules, Beijing Stock
Exchange rules, and exact listing-period rules require dedicated reference data
before production use.

## Layer Boundaries

### Data

Provider adapters fetch external data. Normalizers convert it into canonical
models. Strategies never call AKShare, Tushare, or brokers directly.

### Strategy

Strategies consume immutable, point-in-time inputs and return explainable
signals. A signal is not an order.

The same rule applies to discovery, every screening dimension, research,
market-regime classification, value analysis, trend analysis, events, and AI.
Only the execution package may turn an approved Signal into an Order.

### Validation

Validation converts signals into simulated portfolio outcomes using the same
market rules, costs, calendars, and risk checks intended for paper/live modes.

### Risk and Portfolio

Portfolio construction proposes allocation. Risk has veto authority and may
reject or reduce an order.

### Execution

The execution package may create Orders only after an approving risk decision.
Broker adapters accept only those approved Orders. Research and paper modes
cannot send live orders.

## Point-in-Time Contract

Every observation has:

- Observation or event time
- Availability or publication time
- Source

A decision at time `t` may only use records with `available_at <= t`.

## Suggested Future Package Growth

Add concrete modules only when their milestone begins:

- `data/providers/akshare.py`
- `data/calendars/china_a.py`
- `strategies/trend/tong_trend.py`
- `validation/event_driven.py`
- `execution/paper.py`
- `execution/brokers/qmt.py`

This prevents empty framework abstractions from growing faster than working
research code.

## V0.2 Data Foundation

The data foundation now implements the provider, cache, validation,
normalization, SQLite, and point-in-time read boundaries described above. See
`docs/data-foundation.md` for schemas, supported datasets, and limitations.

## V0.3 Market Regime Engine

The regime engine is an analytical layer between point-in-time market data and
future screening, research, portfolio, and strategy systems:

```text
MarketDataService + timestamped external metrics
                    |
              Input Builder
                    |
       Normalized RegimeMetric [-1, 1]
                    |
       Configured weighted classifier
                    |
    MarketRegime + universal WATCH Signal
```

It never creates orders and does not contain a trading strategy. Transition
states remain informational and map to the primary `Sideways` state. See
`docs/market-regime-engine.md`.
