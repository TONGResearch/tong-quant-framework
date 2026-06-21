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
Provider-backed completeness remains partial and must constrain ReplayConfidence
and every historical interpretation.

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

## Milestone 3.6: V0.7.1 Hardening

- Execution defaults to disabled
- ExecutionDisabledGuard protects OrderFactory and Broker entry points
- ExecutionReadinessGate requires explicit validation, portfolio, risk,
  approval, broker, permission, and readiness evidence
- Risk is decoupled from Portfolio through generic RiskPositionInput
- Portfolio/Risk read-side repositories reconstruct proposal artifacts by id
- Version metadata is centralized
- Notification compatibility is research-artifact oriented and has no
  execution dependency

Status: implemented as a pre-V0.8 hardening milestone. It does not implement
Notification Engine, Paper Trading, Execution Engine, brokers, live orders, or
asset allocation.

## Milestone 3.7: V0.8 Notification Engine

- ResearchReport, ValidationReport, PortfolioProposal, and RiskAssessment only
- Disabled, preview, and enabled modes; disabled by default
- SQLite outbox and delivery audit history
- Deterministic artifact/channel/recipient deduplication
- Deferred dispatcher with retry state
- Telegram, WeChat, and Email environment-only credential loading
- Mandatory research-only disclaimer and sensitive-text redaction
- Fake-channel integration coverage; live provider tests opt in explicitly

Status: implemented as a research-information system. It does not implement
Paper Trading, execution, broker connectivity, orders, fills, trades, or auto
rebalancing.

Engineering stabilization adds expiring dispatch leases, orphan recovery,
persistent dead letters, repository-level credential rejection, ordered database
migrations, and atomic Research/Validation final writes. See
`engineering-stabilization-review.md`.

## PIT Data Remediation And Provider Calibration

- Partial historical security lifecycle ingestion with explicit exchange gaps
- Dated CSI300/500/1000 and market-wide snapshots without invented history
- Actual disclosure dates and CNInfo announcement timestamps
- Historical coverage scoring and `USABLE` / `CAUTION` / `UNSUITABLE` readiness
- Generic provider comparison reports for future secondary-source onboarding

Status: implemented as a data-reliability phase before Paper Trading or
Execution. Secondary providers and complete national lifecycle histories remain
future data-acquisition work.

Provider Calibration Phase II adds Tushare as the first secondary adapter,
automatic conflict detection, conflict-history persistence, dataset confidence,
and PIT readiness conflict caps. Live calibration remains opt-in and depends on
local `TUSHARE_TOKEN` permissions; no trust class changes merely because the
adapter exists.

Provider Calibration Phase III adds real-provider orchestration, per-dataset
coverage/trust/precision/consistency/continuity assessments, framework-area
readiness aggregation, reproducible query manifests, and generated Markdown and
JSON dashboards. The first real AKShare run is intentionally classified
`UNSUITABLE`: Tushare was unavailable and several sources remain retrieval-time
snapshots without adequate historical continuity. See
`provider-calibration-phase-iii.md`.

Tushare integration hardening adds environment-only credential validation,
automatic endpoint permission detection, dataset capability mapping, and an
explicit readiness gap report. Missing credentials currently block the real
dual-provider run. Perfect provider agreement would still leave most lifecycle
and universe datasets at `CAUTION`, so historical continuity remediation remains
mandatory before Paper Trading architecture is reconsidered.

AKShare hardening adds an independent normalized-response audit and bounded CSI
constituent downloads. Current runs preserve eight successful dataset groups and
surface three CSI endpoint failures without stale substitution or an unbounded
hang. These operational improvements do not change the overall `UNSUITABLE` PIT
classification.

## Reserved Review: Paper Trading Architecture

- Review hypothetical-ledger ownership and isolation.
- Review PortfolioProposal and RiskAssessment consumption.
- Review approval and Decision Journal linkage.
- Review market rules, calendars, fees, slippage, suspensions, and partial fills.
- Define evidence gates without implementing a simulator.

Entry condition: V0.8 notification boundaries remain isolated and execution
remains disabled by default.

Status: design review only after stabilization evidence. No Paper Trading
implementation is approved.

## Deferred

- Intraday K-line subsystem
- AI news scoring
- Global market providers
- Funds, ETFs, REITs, bond funds, money-market funds, and asset allocation
- Live QMT/PTrade/IBKR/Moomoo integration
- Fully automatic execution
