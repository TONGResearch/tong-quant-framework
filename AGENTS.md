# Tong Quant Framework Agent Guidance

## Developer Context

- Owner: Tong Li
- Background: Computer Science student at Universiti Putra Malaysia
- Primary environment: PyCharm Professional on macOS Apple Silicon
- Python: 3.12
- Repository owner: TONGResearch
- Current data source: AKShare
- Source of truth: this local PyCharm project and its Git history

## Product Philosophy

The required workflow is:

> Discovery -> Hard Screening -> Research Queue -> Research ->
> Investment Scoring -> Validation -> Execution

Tong Quant is not a pure quantitative, technical-analysis, or AI system. It
combines opportunity discovery, traditional investment research, quantitative
validation, risk management, and controlled execution.

## Non-Negotiable Boundaries

- All upstream engines output the universal `Signal` model.
- Screening, research, strategies, market-regime analysis, events, and AI must
  never create or submit orders.
- Only `tong_quant.execution` may define order models or create orders.
- Risk checks have final veto authority before an order can be submitted.
- Keep data, screening, research, strategy, validation, portfolio, risk, and
  execution layers decoupled.
- Put market-specific behavior behind `MarketRules`, calendars, fee models, and
  provider or broker adapters.
- Never embed A-share assumptions in shared strategy logic.
- Use point-in-time timestamps and reject future data.
- Treat availability precision and data trust as separate concepts.
- Research, Validation, and future HistoricalReplay consumers must inspect
  both `AvailabilityPrecision` and `DataTrustLevel`.
- Do not treat PIT data as replay-ready until a `PITReadinessAssessment`
  supports that conclusion.
- HistoricalReplaySource reconstructs validation samples only. It must not
  backtest orders, allocate capital, connect to brokers, or make trade
  decisions.
- `ReplayConfidence` measures historical reconstruction quality separately
  from research correctness. Weak replay confidence must not be interpreted as
  proof that the research thesis was wrong.
- Missing data must not silently become a favorable result.
- Hard-screen failures cannot be offset by favorable scores.
- Research Score prioritizes research only; it is not an investment decision.
- Screening owns Discovery, Hard Screening, Watchlist, and Research Queue only.
- `research.models.ResearchReport` is the single official research report
  contract.
- Investment Score must consume a completed ResearchReport and must be read
  together with `InvestmentAssessmentStatus`.
- A high Investment Score with low confidence remains a low-confidence
  opportunity; it is not an order or automatic approval.
- Priority, urgency, and confidence are separate Research Queue concepts.
- Every Research Report requires a thesis, counter thesis, and explicit
  falsifiable invalidation conditions.
- Research confidence must consider evidence quality, data completeness,
  module agreement, and point-in-time integrity; do not use simple averaging.
- Policy Research covers regulatory, industrial, fiscal, monetary, and
  geopolitical evidence and remains one variable among several.
- No single factor may determine an investment decision.
- Every decision must be deterministic where practical, explainable, versioned,
  and backtestable.
- Backtest, paper, and live modes should share decision logic.
- AI may assist discovery and research but never authorize a trade.
- Do not add live trading or credentials without explicit user approval.
- Build the MVP before complex strategies or advanced AI.

## Development Style

- Prefer Python standard library and typed, immutable domain models.
- Use `Protocol` or abstract interfaces at external boundaries.
- Add dependencies only when they solve a current requirement.
- Keep provider-specific payloads outside the domain layer.
- Access AKShare only through `tong_quant.data.providers`.
- In strict point-in-time mode, do not ingest provider-adjusted historical bars
  until dated corporate-action factors can reconstruct the adjustment visible
  at each decision time.
- Never overwrite point-in-time facts, security-status history, universe
  membership, or corporate actions silently. Use revisions, raw hashes, and
  ingestion batches to preserve auditability.
- AKShare provider limitations and missing publication timestamps must be
  persisted as warnings instead of hidden inside normalizers.
- Persist normalized market data through `SQLiteStore`; do not write ad hoc
  strategy-specific data files.
- Screening, research, and validation must read historical data through
  `MarketDataService` with an explicit timezone-aware `as_of` timestamp.
- Treat company information and universe snapshots as current snapshots unless
  a dedicated historical security-master source proves otherwise.
- Market regime classifiers consume only normalized `RegimeMetric` inputs.
- Every regime input, bar, and external breadth or volatility metric must have
  `available_at <= as_of`.
- Market Regime is a high-weight decision variable, not a hard trading switch.
- No regime state may automatically approve or reject an opportunity.
- Regime weights and thresholds belong in configuration, not strategy code.
- Trend ATR, trailing, and pyramid outputs are research scenarios only until
  they pass the future Validation Engine.
- A-share Pattern Research must return insufficient data when required
  breadth or intraday evidence is unavailable.
- Validation must distinguish data `as_of` from the actual `requested_at` run
  timestamp.
- Validation outcomes and thresholds must be registered before results are
  evaluated.
- Research correctness and Decision Journal correctness must be measured
  independently.
- Every Validation Run must store Git, framework, configuration, research,
  validation, and database schema versions.
- Final OOS usage limits must be enforced by persistent state, not caller
  convention.
- Portfolio validation may measure research concentration but must not simulate
  portfolio returns or orders.
- Validation outputs only `REVIEW` Signals and must never create trade actions.
- Replay samples with missing data, low trust, ST/suspended/delisted status, or
  provider limitations must remain visible with warnings.
- Portfolio consumes InvestmentScore outputs only and must not bypass Research
  or Validation.
- PortfolioProposal and PositionProposal are research artifacts only. Do not
  use advice-oriented or execution-oriented names for them.
- RiskAssessment may constrain or reject a PortfolioProposal, but it must not
  create orders, broker requests, fills, trades, paper-trading actions, or
  auto-rebalancing instructions.
- Store secrets in environment variables or untracked local configuration.
- Preserve PyCharm as the primary development workflow.
- V1.0 remains equity-focused. Reserve naming and interfaces for future funds,
  ETFs, REITs, money-market funds, bond funds, and allocation research, but do
  not implement fund research, portfolio allocation, or execution before an
  approved milestone.

## Verification

Before considering a change complete:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
```

Add tests for market behavior, timestamp integrity, configuration safety,
layering constraints, and changed decision rules.
