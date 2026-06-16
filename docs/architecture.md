# V0.1 Architecture

## Design Decision

China A, US, Hong Kong, and Malaysia share the same workflow and domain
contracts. They do not share every market policy or trading rule.

V1.0 remains focused on individual equities. The domain model reserves broader
`Instrument` and `TradableInstrument` language so future versions can add
funds, ETFs, REITs, bond funds, money-market funds, and allocation research
without renaming the current equity workflow.

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

V0.6.2 adds conservative PIT population around these contracts:

```text
AKShare raw response
        |
Raw schema validation + payload fingerprint
        |
Availability warning + provider limitation audit
        |
Normalized PIT facts / statuses / memberships / corporate actions
        |
PITReadinessAssessment
```

`AvailabilityPrecision` and `DataTrustLevel` are separate. A record can be
available only at retrieval time while still carrying useful medium-trust
content, or it can have an exact date with low confidence in completeness.
HistoricalReplaySource must not begin until readiness assessments show which
datasets are replay-capable.

## Future Asset Classes

The market package reserves this future structure:

```text
markets/
  china_a/
  us/
  hong_kong/
  malaysia/
  funds/
```

The reserved fund branch is documentation and import-safe package scaffolding
only. It does not contain fund screening, fund research, allocation, orders, or
broker integration.

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
Future Validation
```

Research Queue `priority_score`, `urgency_score`, and `confidence_score` remain
separate values. Research Score helps allocate research attention and remains a
Screening concern. Screening does not own research outcomes or investment
assessment models.

Shared screening orchestration lives in `screening/`. China A, US, Hong Kong,
and Malaysia inject separate market policies for status eligibility, risk
flags, liquidity, and financial-health requirements.

## V0.5 Research Engine

Research consumes V0.4 Research Queue entries and executes only the requested
modules plus their declared dependencies:

```text
Research Queue -> ResearchContext -> Module dependency graph
                                    |
              Policy / Financial / Industry / Value
              Technical / Trend / China A Pattern
                                    |
                  falsifiable ResearchReport
                                    |
                      universal RESEARCH Signal
                                    |
                 InvestmentAssessment + status
                                    |
                       Future Validation
```

Every report contains a thesis, counter thesis, and explicit invalidation
conditions. Confidence combines evidence quality, completeness, module
agreement, and point-in-time integrity with a weakest-link cap. Market Regime
is retained as a research variable rather than a gate. See
`docs/research-engine.md`.

Investment Score is calculated only after a completed `ResearchReport` and
must be interpreted together with `InvestmentAssessmentStatus`. A high score
with low confidence remains a low-confidence opportunity. Incomplete or
insufficient-data assessments do not carry an interpretable score.

## V0.6 Validation Engine

Validation audits stored historical outputs rather than turning research
signals into simulated orders:

```text
Discovery / Screening / Research outputs
                    |
       Pre-registered OutcomeDefinition
                    |
       Point-in-time ValidationSample
                    |
 Historical + Walk-Forward + OOS
 Regime + Thesis + Factor + Accuracy
 Decision Journal + Portfolio Research Risk
                    |
      ValidationReport + REVIEW Signal
```

Research correctness and decision correctness remain separate. Portfolio
validation measures concentration of research attention across country,
industry, theme, and style; it is not portfolio return backtesting.

Every run carries a reproducibility snapshot containing the Git commit,
framework version, configuration hash, research version, validation version,
and database schema version. See `docs/validation-engine.md`.

## V0.6.3 Historical Replay

Historical replay is the bridge from PIT storage to validation samples:

```text
SQLite PIT records
        |
ReplayQuery
        |
HistoricalReplayBuilder
        |
ReplayManifest + ReplayValidationSample
        |
ValidationRequestFactory
        |
Validation Engine
```

ReplayConfidence measures the quality of reconstruction, not research
correctness. ST, suspended, delisted, low-trust, provider-limited, and
incomplete samples remain visible with warnings.

## V0.7 Portfolio And Risk

Portfolio and Risk extend validated research into proposal-only portfolio
construction:

```text
InvestmentAssessment + InvestmentScore + Validation evidence
        |
PortfolioCandidate
        |
PortfolioProposal + PositionProposal
        |
RiskAssessment
```

PortfolioProposal is a research artifact. It is not decision authorization,
execution instruction, or live connectivity request.

RiskAssessment covers concentration, sector, country, theme, correlation,
volatility targeting, drawdown, liquidity, risk budgets, and scenario stress
tests. It can mark a proposal acceptable, conditional, rejected, or incomplete,
but it cannot create orders.
