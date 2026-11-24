# Tong Quant Framework

Personal quantitative investment research platform developed by Tong Li.

Current project state and the next approved work packages are in
`PROJECT_STATUS.md`. Run `python scripts/check_project_governance.py` before
starting a new milestone.

For the Chinese owner philosophy, seven technical research groups, actual
implementation gaps, and cross-device recovery checklist, read
[the project handoff](docs/PROJECT_HANDOFF.zh-CN.md). Local uncommitted code and
ignored research data do not automatically exist on GitHub or another device.

## Philosophy

Discover Opportunities -> Screen Opportunities -> Research Opportunities ->
Validate Opportunities -> Execute Opportunities

The framework combines traditional investment research, quantitative validation,
trend analysis, market analysis, and controlled execution. AI assists research
but never directly authorizes trades.

## V0.8 Scope

The framework includes the data foundation, Market Regime, Screening,
Research, Validation, Historical Replay, Portfolio, Risk, Notification, and
hardening boundaries:

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
- AKShare/Tushare provider calibration with auditable conflict history
- Phase III dataset and framework-area PIT readiness dashboards
- Secure Tushare endpoint capability detection and readiness gap reporting
- Independent AKShare normalized-data quality auditing with bounded CSI timeouts
- Checksum-verified baseline migration and fail-closed physical schema fingerprint
- Provider-neutral evidence ingestion with trust and availability metadata
- CNInfo disclosure evidence through explicit AKShare transport provenance
- Yahoo Finance provider-native global daily-bar observations with conservative
  trust and an unverified adjustment basis
- Provider-neutral Yahoo daily-bar calibration with deterministic fixtures,
  fail-closed unavailable/incompatible attempts, and optional Massive evidence
- Scheduled CNInfo/Yahoo provider contract monitoring and audit persistence
- Provider health escalation for one-off, repeated, defective, and recovered
  contract states without Notification Engine coupling
- PIT-safe HistoricalReplaySource with manifest and sample replay hashes
- ReplayConfidence to separate weak reconstruction from weak research
- PortfolioProposal and PositionProposal research artifacts
- RiskAssessment with risk budgets and scenario stress tests
- Fund and asset-allocation extension points reserved without implementation
- `ExecutionDisabledGuard` and `ExecutionReadinessGate` fail closed by default
- Default execution mode is `disabled`
- Risk consumes generic `RiskPositionInput`, not Portfolio-specific models
- Portfolio/Risk read-side repositories reconstruct research artifacts by id
- Framework, database, research, validation, and replay versions are centralized
- Notification compatibility is artifact-oriented: ResearchReport,
  ValidationReport, PortfolioProposal, and RiskAssessment only
- Notification mode defaults to `disabled`, with explicit `preview` and
  `enabled` modes
- SQLite outbox separates notification generation from later delivery
- Artifact hashes and channel/recipient deduplication make generation idempotent
- Telegram, WeChat, and Email adapters read credentials from environment
  variables only
- Every rendered message carries a research-only, no-advice, no-execution
  disclaimer

It intentionally does not implement Paper Trading, order-level backtesting,
trade approval, orders, execution logic, live brokerage, or auto rebalancing.

## Quick Start

### Academic Research Workbench

For an independent review without private data, start with the
[academic verification guide](docs/academic-verification-guide.md):

```bash
python scripts/verify_academic_reproduction.py --output verification.json
```

This runs six explicitly synthetic cases across US/HK/MY routes, checks SMA/MACD/
KDJ against separate numerical references and tests blocked-input behavior.
It is offline after dependency installation; it does not qualify real listings,
market data, trading sessions or strategy performance. The actual exporter below
is subject-parameterized, but each generated page is a fixed single-stock snapshot,
not a live all-market terminal. This export path does not yet admit A-shares/Japan.

An offline English workbench presents retained observations, evidence lineage,
local engineering checks and system architecture. It reuses the existing research
formulas and original read-only source reconstruction; it is not a fabricated
profit dashboard, a second official ResearchReport, or a live-trading interface.

```bash
python scripts/export_academic_showcase.py \
  --database data/processed/msft-review-20261115-zgzl_o5o/snapshot.sqlite3 \
  --artifact-root data/processed/msft-review-20261115-zgzl_o5o/raw \
  --market us --symbol MSFT \
  --as-of 2026-11-15T09:13:45.007947+00:00 \
  --max-observation-age-seconds 604800 \
  --output data/processed/academic-showcase/index.html
```

The example requires the original local retained sample, which is not on GitHub.
The seven-day limit is illustrative, not a production freshness policy. Open the
exported HTML directly in a browser; no server, account, network or frontend
installation is required. Optional `--junit-report` displays an actual local pytest
JUnit record, explicitly separate from strategy-performance validation. Existing
output files are never overwritten. See [academic showcase notes](docs/academic-showcase-2026-11-24.md).

### Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
python -m tong_quant
```

Offline installation diagnostics, including from another working directory:

```bash
python -m tong_quant status --project-root /absolute/path/to/TongQuant_v1
python -m tong_quant preflight --project-root /absolute/path/to/TongQuant_v1
```

The installed wheel also exposes `tong-quant`. Preflight never enables trading
or promotes data readiness; an uncommitted checkout fails closed. See the
[research deployment runbook](docs/research-deployment-runbook.md) for package,
data portability and rollback boundaries.

Example ingestion:

```bash
python scripts/ingest_data.py calendar
python scripts/ingest_data.py company 600000
python scripts/ingest_data.py daily-bars 600000 20240101 20241231
python scripts/ingest_data.py daily-bars 000001 20240101 20241231 --index
python scripts/run_data_readiness.py
python scripts/run_provider_contract_monitor.py
python scripts/build_provider_contract_baseline.py
python scripts/manage_database.py audit --database data/tong_quant.sqlite3
python scripts/capture_cninfo_artifacts.py \
  --symbol 600000 --start-date 2026-01-01 --end-date 2026-03-31 \
  --metadata-only
python scripts/run_yahoo_calibration.py \
  --market us --symbol MSFT \
  --start-date 2026-06-18 --end-date 2026-06-19 \
  --as-of 2026-06-20T12:00:00+00:00 \
  --yahoo-fixture tests/fixtures/yahoo_daily_bars.json \
  --secondary-fixture tests/fixtures/independent_daily_bars.json \
  --require-secondary
```

Tushare cross-provider calibration is opt-in and requires an environment
variable. Use `--require-secondary` when the run must fail instead of silently
falling back to AKShare-only evidence:

```bash
export TUSHARE_TOKEN="<your token>"
python scripts/run_data_readiness.py --tushare-capability-only
python scripts/run_data_readiness.py --require-secondary
```

See `docs/architecture.md`, `docs/data-foundation.md`,
`docs/provider-evidence-foundation.md`,
`docs/provider-monitor-operations.md`,
`docs/cninfo-direct-artifacts.md`,
`docs/yahoo-daily-bar-calibration.md`,
`docs/database-backup-restore.md`,
`docs/engineering-continuity.md`,
`docs/provider-calibration-phase-iii.md`,
`docs/market-regime-engine.md`, `docs/screening-engine.md`,
`docs/research-engine.md`, `docs/validation-engine.md`,
`docs/notification-engine.md`, and `docs/development-roadmap.md`. The current
cross-project risk review is
`docs/project-review-v0.6.md`.
