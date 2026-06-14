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

> Discovery -> Hard Screening -> Research Queue -> Scoring -> Research ->
> Validation -> Execution

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
- Missing data must not silently become a favorable result.
- Hard-screen failures cannot be offset by favorable scores.
- Research Score prioritizes research only; it is not an investment decision.
- Investment Score supports researched opportunities before validation; it is
  not an order or automatic approval.
- Priority, urgency, and confidence are separate Research Queue concepts.
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
- Store secrets in environment variables or untracked local configuration.
- Preserve PyCharm as the primary development workflow.

## Verification

Before considering a change complete:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
```

Add tests for market behavior, timestamp integrity, configuration safety,
layering constraints, and changed decision rules.
