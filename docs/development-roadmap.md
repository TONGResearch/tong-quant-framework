# Development Roadmap

## Milestone 0: Foundation

- Package scaffold and configuration
- Domain models and core protocols
- MarketRules boundary
- Timestamp and future-data tests
- CI checks

Exit: package installs, tests pass, and no live-order path exists.

## Milestone 1: A-Share Daily Data

- AKShare provider adapter
- Symbol master and delisting history
- Trading calendar
- Raw and normalized storage
- Adjustment-factor policy
- Data-quality report

Exit: a reproducible daily dataset can be rebuilt for a fixed universe and date.

Status: implemented in V0.2. Historical security-master reconstruction and
corporate-action datasets remain future data milestones.

## Milestone 1.5: Market Regime Engine

- China factors: CSI 300, CSI All Share, rising stocks, turnover, and breadth
- Global factors: major index trend, breadth, volatility, and relative strength
- Five-state output with informational transition states
- Configurable scoring and confidence
- Point-in-time input construction and historical replay

Status: implemented in V0.3. Strategy gating remains a future consumer and is
not implemented here.

## Milestone 1.75: Screening Engine

- Discovery-candidate contract
- Ordered hard screening with immediate rejection
- Research Queue with separate priority, urgency, and confidence
- Seven dimensions: News, Industry, Survival, Growth, Valuation, Positioning,
  and Macro
- Separate Research Score and Investment Score
- Four market policy boundaries: China A, US, Hong Kong, and Malaysia
- Market Regime as a weighted variable, not a hard switch
- SQLite persistence for queue entries and scorecards

Status: implemented in V0.4 as an explainable, point-in-time-safe framework.
Concrete provider-backed dimension models remain future research work.

## Milestone 1.9: Research Engine

- Policy, Financial, Industry, Value, Technical, Trend, and Pattern modules
- Dependency-aware module execution
- Mandatory thesis, counter thesis, and invalidation conditions
- Evidence-quality, completeness, agreement, and point-in-time confidence
- Financial restatement awareness
- Atomic Research Queue claiming
- Research run, evidence, assessment, report, and Signal persistence

Status: implemented in V0.5 as a research-only engine. Provider-backed policy,
sentiment, industry heat, and intraday evidence remain future data work.
Backtesting and trade approval remain outside this milestone.

## Milestone 2: Minimal Trend Research

- Donchian breakout
- ATR calculation
- Explicit volume confirmation
- Simple market-regime definition
- Explainable four-confirmation signal record

Exit: provider-backed trend evidence is calibrated and ready for validation.

Status: the explainable research framework is implemented in V0.5. Calibration
and historical validation remain future work.

## Milestone 3: Validation

- Event-driven daily backtest
- T+1, suspensions, limit rules, costs, and slippage
- Walk-forward and out-of-sample split
- Parameter sensitivity report
- Survivorship-bias controls

Exit: a versioned validation report decides pass or reject.

## Milestone 4: Paper Trading

- Paper broker
- Risk veto and drawdown halt
- Order lifecycle and reconciliation
- Telegram notification

Exit: stable paper operation with no live credentials.

## Deferred

- Intraday K-line subsystem
- AI news scoring
- Global market providers
- Live QMT/PTrade/IBKR/Moomoo integration
- Fully automatic execution
