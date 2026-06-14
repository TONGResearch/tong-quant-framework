# Tong Quant Framework

Personal quantitative investment research platform developed by Tong Li.

## Philosophy

Discover Opportunities -> Screen Opportunities -> Research Opportunities ->
Validate Opportunities -> Execute Opportunities

The framework combines traditional investment research, quantitative validation,
trend analysis, market analysis, and controlled execution. AI assists research
but never directly authorizes trades.

## V0.2 Scope

V0.2 establishes:

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

It intentionally does not implement complex strategies or live brokerage.

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

See `docs/architecture.md`, `docs/data-foundation.md`, and
`docs/development-roadmap.md`.
