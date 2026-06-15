# V0.6 Validation Engine

## Purpose

V0.6 audits whether historical Discovery, Screening, and Research outputs were
reliable. It does not approve trades, simulate orders, connect to brokers, or
produce entry and exit decisions.

```text
Historical upstream outputs
        |
Pre-registered outcome definitions
        |
Point-in-time ValidationSample
        |
Historical / Walk-Forward / OOS / Regime / Thesis
Factor Contribution / Research Accuracy
Decision Journal / Portfolio Research Risk
        |
ValidationReport + REVIEW Signal
```

## Time Contract

Validation separates:

- `decision_at`: when the historical research decision existed
- `outcome.observed_at`: when the result occurred
- `outcome.available_at`: when the result could be known
- `as_of`: latest outcome data allowed in the validation
- `requested_at`: when the validation run was executed

The required ordering is:

```text
research.available_at <= decision_at
decision_at <= outcome.observed_at <= outcome.available_at <= as_of
as_of <= requested_at
```

Unresolved or unavailable outcomes remain explicit. Missing values never become
successful observations.

## Pre-Registered Outcomes

Every run stores immutable `OutcomeDefinition` records containing:

- Target metric
- Observation horizon
- Success operator and threshold
- Availability lag
- Benchmark
- Definition version

This prevents selecting a favorable horizon or threshold after results are
known. Outcome definitions and outcomes are persisted separately.

## Validation Modules

### Historical

Measures historical research correctness over resolved point-in-time samples.
Provider-backed historical reconstruction is exposed through a
`HistoricalReplaySource` boundary and remains separate from validation logic.

### Walk-Forward

Creates training and validation windows with an explicit embargo. Configuration
hashes are frozen on every split. Empty windows remain visible and do not
receive a favorable default.

### Out-of-Sample

Requires a pre-registered OOS period and frozen configuration hash. SQLite
atomically tracks an OOS dataset fingerprint and rejects use beyond the
registered maximum.

### Market Regime

Compares research reliability across Bull, Sideways, Bear, and transition
states. Regime remains an explanatory research variable, not a trading gate.

### Thesis

Tracks Supported, Partially Supported, Invalidated, Unresolved, and
Not Observable outcomes. It separately measures whether registered thesis
invalidation conditions detected failed theses.

### Factor Contribution

Uses deterministic factor ablation, score gaps, and outcome correlation.
Results describe incremental research contribution and do not authorize model
selection automatically.

### Research Accuracy

Tracks:

- Research correctness
- Brier score
- Confidence calibration error
- High-confidence failure rate

High-confidence errors receive an explicit reliability penalty.

### Decision Journal

Research quality and decision quality are tracked independently:

```text
Research correct / Decision correct
Research correct / Decision wrong
Research wrong   / Decision correct
Research wrong   / Decision wrong
```

A lucky decision cannot validate incorrect research. Decision records also
reference the framework configuration snapshot used at the time.

### Portfolio Research Risk

This is not portfolio return backtesting. It measures research allocation
concentration across:

- Industry
- Country
- Theme
- Style

Each dimension records maximum category weight, HHI, category weights, and
configured-limit breaches.

## Framework Snapshot

Every run requires and persists:

- Git commit
- Framework version
- Configuration hash
- Research version
- Validation version
- Database schema version

The repository rejects a run when the snapshot schema version differs from the
active SQLite schema. `reproducibility_manifest` copies the snapshot into every
report.

## Outputs

`ValidationAssessment` retains per-module status, confidence, sample size,
metrics, findings, risks, limitations, and integrity checks.

Statuses:

- Reliable
- Conditionally Reliable
- Inconclusive
- Unreliable
- Failed Integrity Check

`ValidationReport` preserves all module assessments. It does not expose an
automatic execution approval.

`ValidationSignal` uses:

```text
stage = validation
action = review
```

## Persistence

V0.6 adds:

- `schema_metadata`
- `validation_runs`
- `validation_oos_usage`
- `validation_splits`
- `validation_observations`
- `validation_outcome_definitions`
- `validation_outcomes`
- `decision_journal`
- `validation_assessments`
- `validation_reports`
- `validation_factor_contributions`
- `validation_accuracy_history`
- `validation_integrity_checks`
- `validation_portfolio_risk`

## Non-Goals

- No order-level backtest
- No portfolio return simulation
- No fill, slippage, or broker model
- No strategy optimization
- No automatic model promotion
- No buy or sell decision
- No Validation-to-Execution shortcut
