# Tong Quant Framework

Personal quantitative investment research platform developed by Tong Li.

## Philosophy

Discover Opportunities -> Screen Opportunities -> Research Opportunities ->
Validate Opportunities -> Execute Opportunities

The framework combines traditional investment research, quantitative validation,
trend analysis, market analysis, and controlled execution. AI assists research
but never directly authorizes trades.

## V0.5 Scope

V0.5 includes the data foundation, Market Regime Engine, Screening Engine, and:

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
- Investment Score for researched opportunities
- Market Regime as a high-weight Investment Score variable, never a hard switch
- Research Queue consumption with atomic claim protection
- Policy, Financial, Industry, Value, Technical, Trend, and A-share Pattern research
- Mandatory thesis, counter thesis, and falsifiable invalidation conditions
- Confidence based on evidence quality, completeness, agreement, and PIT integrity
- Financial restatement awareness and revision-history access
- Research run, evidence, assessment, report, and Signal persistence

It intentionally does not implement backtesting, trade approval, orders, or
live brokerage.

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
`docs/market-regime-engine.md`, `docs/screening-engine.md`, and
`docs/research-engine.md`, and `docs/development-roadmap.md`.
