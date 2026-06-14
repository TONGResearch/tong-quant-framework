# V0.3 Market Regime Engine

## Purpose

The Market Regime Engine classifies market conditions without creating trades.
It is designed as a future master switch for screening, research, validation,
risk, and strategy systems.

## States

- `Bull`
- `TransitionToBull`
- `Sideways`
- `TransitionToBear`
- `Bear`

Transition states are informational and their `primary_state` is `Sideways`.
The engine emits a universal `WATCH` Signal, never an Order. No state acts as a
hard trading switch: Market Regime is a high-weight input to layered research,
investment scoring, and validation.

## Output

`MarketRegime` contains:

- State and primary state
- Confidence from 0 to 100
- Weighted score from -100 to 100
- Timestamp and model version
- Per-factor values, weights, contributions, and explanations
- Human-readable reasons sorted by contribution importance

## China Model

Inputs:

- CSI 300 trend
- CSI All Share trend
- Number of rising stocks
- Market turnover
- Market breadth

Index trends are calculated from point-in-time daily bars. Breadth and turnover
inputs must be supplied as timestamped external metrics until V0.2 storage is
extended with daily market-statistics tables.

## Global Model

Inputs:

- Major index trend
- Market breadth
- Volatility
- Relative strength against a configured benchmark

The interfaces support US, Hong Kong, Malaysia, and future global markets.

## Scoring

Each input is normalized to `[-1, 1]`, where positive values support bullish
conditions and negative values support bearish conditions. Configured weights
produce a score in `[-100, 100]`.

Default boundaries:

- Bull: score at least `25`
- Transition to Bull: score at least `12`, below Bull, with at least 60% positive factors
- Sideways: neither directional boundary is met
- Transition to Bear: score at most `-12`, above Bear, with at least 60% negative factors
- Bear: score at most `-25`

Weights and boundaries are configured in `config/default.toml`.

Confidence combines distance inside the selected state and factor agreement.
It is a model-confidence score, not a return forecast or probability of profit.

## Point-in-Time Safety

- Every metric carries `available_at`.
- Every classification requires an explicit timezone-aware `as_of`.
- Metrics with `available_at > as_of` are rejected.
- Index bars are read through `MarketDataService`.
- Historical replay uses the same pure classifiers as current evaluation.

## Limitations

- Breadth and turnover historical ingestion are not part of V0.3.
- Default weights and thresholds are initial research parameters, not validated
  trading rules.
- Future validation must test stability across markets, periods, and parameter
  ranges before any downstream system treats regimes as production controls.
