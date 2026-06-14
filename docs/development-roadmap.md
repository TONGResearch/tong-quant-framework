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

## Milestone 2: Minimal Trend Research

- Donchian breakout
- ATR calculation
- Explicit volume confirmation
- Simple market-regime definition
- Explainable four-confirmation signal record

Exit: every signal includes its inputs, reasons, and missing confirmations.

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
