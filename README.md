# Tong Quant Framework

Personal quantitative investment research platform developed by Tong Li.

## Philosophy

Discover Opportunities -> Screen Opportunities -> Research Opportunities ->
Validate Opportunities -> Execute Opportunities

The framework combines traditional investment research, quantitative validation,
trend analysis, market analysis, and controlled execution. AI assists research
but never directly authorizes trades.

## V0.7 Scope

V0.6 includes the data foundation, Market Regime, Screening, Research, and:

- Clean package architecture
- Shared market-independent interfaces
- Explicit A-share and global market rules
- Canonical point-in-time data models
- A universal Signal contract for every analytical engine
- Dedicated screening, market-regime, and notification modules
- TOML-based configuration
- Testing and future-data-leakage guardrails
- AKShare A-share and index daily-data adapters
- A-share trading calendar and company-information ingestion
- Raw-response caching and data-quality validation
- Versioned SQLite storage
- Point-in-time-safe historical queries
- Explainable China and global Market Regime Engines
- Bull, Transition to Bull, Sideways, Transition to Bear, and Bear states
- Configurable factor weights, thresholds, and confidence scoring
- Point-in-time-safe regime input builders for historical replay
- Discovery-candidate contracts
- Ordered hard-screening rules with immediate rejection
- Separate China A, US, Hong Kong, and Malaysia screening policies
- Seven screening dimensions, including Macro
- Research Queue persistence
- Separate priority, urgency, and confidence scores
- Research Score for queue prioritization
- `ResearchReport` as the single official research report contract
- Post-research Investment Assessment and Investment Score
- Mandatory `InvestmentAssessmentStatus` for score interpretation
- Market Regime as a high-weight Investment Score variable, never a hard switch
- Research Queue consumption with atomic claim protection
- Policy, Financial, Industry, Value, Technical, Trend, and A-share Pattern research
- Mandatory thesis, counter thesis, and falsifiable invalidation conditions
- Confidence based on evidence quality, completeness, agreement, and PIT integrity
- Financial restatement awareness and revision-history access
- Research run, evidence, assessment, report, and Signal persistence
- Investment assessment and score persistence
- Pre-registered historical outcome definitions
- Historical, walk-forward, and final out-of-sample validation
- Market Regime, thesis, factor contribution, and research-accuracy validation
- Independent Decision Journal and research-quality tracking
- Country, industry, theme, and style research-concentration validation
- Git, framework, configuration, research, validation, and schema snapshots
- Atomic OOS usage-limit enforcement
- Universal `REVIEW` Validation Signal
- Conservative point-in-time data population for selected AKShare datasets
- Explicit `DataTrustLevel` and `AvailabilityPrecision` metadata
- Audited ingestion batches, raw dataset fingerprints, and availability warnings
- Corporate action, provider limitation, and PIT readiness persistence
- PIT-safe HistoricalReplaySource with manifest and sample replay hashes
- ReplayConfidence to separate weak reconstruction from weak research
- PortfolioProposal and PositionProposal research artifacts
- RiskAssessment with risk budgets and scenario stress tests
- Fund and asset-allocation extension points reserved without implementation

It intentionally does not implement order-level backtesting, trade approval,
orders, execution logic, or live brokerage.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
python -m tong_quant
```

Example ingestion:

```bash
python scripts/ingest_data.py calendar
python scripts/ingest_data.py company 600000
python scripts/ingest_data.py daily-bars 600000 20240101 20241231
python scripts/ingest_data.py daily-bars 000001 20240101 20241231 --index
```

See `docs/architecture.md`, `docs/data-foundation.md`,
`docs/market-regime-engine.md`, `docs/screening-engine.md`,
`docs/research-engine.md`, `docs/validation-engine.md`, and
`docs/development-roadmap.md`. The current cross-project risk review is
`docs/project-review-v0.6.md`.
