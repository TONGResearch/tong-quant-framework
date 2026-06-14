# V0.1 Architecture

## Design Decision

China A, US, Hong Kong, and Malaysia share the same workflow and domain
contracts. They do not share every market policy or trading rule.

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
states remain informational and map to the primary `Sideways` state. Regime is
a weighted decision input, never an automatic approval or rejection. See
`docs/market-regime-engine.md`.

## Data Foundation Hardening

Historical research must reconstruct both what a company reported and which
securities were eligible at the decision time:

```text
FundamentalFact revisions -----> point-in-time fundamental query
UniverseMembership ------------> historical candidate universe
InstrumentStatus --------------> historical tradability and classification
```

These records use separate effective and availability timestamps. Effective
dates describe when a fact or status applies; availability timestamps describe
when the system was allowed to know it. Screening must consume these canonical
queries rather than current company snapshots or today's listed-stock universe.

## V0.4 Screening Engine

Screening implements the first complete upstream workflow:

```text
OpportunityCandidate
        |
Ordered Hard Screening ------ failure ------> EXCLUDE Signal
        |
Seven Dimension Assessments
        |
Research Score
        |
Research Queue Entry + RESEARCH Signal
        |
Completed Research
        |
Investment Score + Market Regime contribution
        |
Future Validation
```

Research Queue `priority_score`, `urgency_score`, and `confidence_score` remain
separate values. Research Score helps allocate research attention. Investment
Score is calculated only after research and includes Market Regime as a
high-weight component. Neither score creates orders or bypasses validation.

Shared screening orchestration lives in `screening/`. China A, US, Hong Kong,
and Malaysia inject separate market policies for status eligibility, risk
flags, liquidity, and financial-health requirements.
