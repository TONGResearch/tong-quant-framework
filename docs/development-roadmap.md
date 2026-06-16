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

V0.6.2 update: selected AKShare fundamentals, ST/suspended snapshots,
delistings, index membership, and corporate-action rows now populate the
existing PIT structures with ingestion batches, raw hashes, trust levels,
availability precision, provider limitations, and readiness assessments.
Provider-backed completeness remains partial and must be quantified before
historical replay.

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
- Research Score for research-queue prioritization
- Four market policy boundaries: China A, US, Hong Kong, and Malaysia
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
- Single official ResearchReport contract
- Post-research InvestmentAssessment and InvestmentScore
- Mandatory InvestmentAssessmentStatus for score interpretation

Status: implemented in V0.5 and unified in V0.6.1 as a research-only engine.
Provider-backed policy,
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

- Pre-registered outcome definitions
- Historical, walk-forward, and final out-of-sample validation
- Market Regime and thesis validation
- Factor contribution and confidence calibration
- Decision Journal quality separation
- Portfolio research-risk concentration
- Reproducible framework snapshots and database schema versioning
- Survivorship and point-in-time integrity controls

Status: implemented in V0.6 as a research-quality audit layer. It produces
per-module reliability assessments and a REVIEW Signal, never a trade approval.
Order-level event-driven backtesting remains a future, separate milestone.

Exit: a versioned ValidationReport explains reliability, limitations, and
integrity failures without creating an execution decision.

## Milestone 3.1: Historical Replay Source

- ReplayQuery for universe/instrument reconstruction
- HistoricalReplayBuilder for PIT-safe decision and outcome context
- ReplayManifest with input hashes, versions, trust, limitations, and warnings
- ReplayValidationSample with missing flags and replay hash
- ReplayConfidence for reconstruction quality
- ValidationRequest generation from complete replay samples

Status: implemented in V0.6.3 as sample reconstruction only. It does not
simulate orders, allocate portfolios, send notifications, or connect brokers.

## Milestone 3.5: Portfolio And Risk Proposals

- Portfolio consumes InvestmentScore outputs only
- PortfolioCandidate enforces Research and Validation provenance
- PortfolioProposal and PositionProposal remain research artifacts
- RiskAssessment covers concentration, exposure, correlation, volatility,
  drawdown, liquidity, risk budget, and scenario stress
- Cash is supported as a formal allocation bucket
- Fund category is reserved for future architecture

Status: implemented in V0.7 as proposal-only portfolio construction. It does
not create recommendations, trade plans, orders, broker requests, fills, paper
trading, or auto rebalancing.

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
- Funds, ETFs, REITs, bond funds, money-market funds, and asset allocation
- Live QMT/PTrade/IBKR/Moomoo integration
- Fully automatic execution
