# Technical And Style Research Extension

## Status And Boundary

November 6 [calendar observations](calendar-period-diagnostics-2026-11-06.md)
add unscored market-local week/month OHLCV with explicit missing, unended and
suspension states. They are not verified exchange-session candles. Technical's
5/21-interval return and 252-observation positioning proxies remain unchanged,
now explicitly labeled. Coverage qualification and period-trend admission remain
open; this does not complete the style/intraday extension or actual validation.

This document describes the full future research extension. The October 20
[implementation audit](technical-implementation-audit-2026-10-20.md) supersedes
the historical coverage table below for the narrowly approved WP-RESEARCH-002
calculation slice. It does not complete WP-RESEARCH-001 or its data gates.
The full extension does not implement a
trading strategy, create a buy or sell decision, change Portfolio weights,
create an Order, or enable Execution. Consult current governance for ready
work packages; PIT readiness remains `UNSUITABLE`.

The extension belongs inside the existing workflow:

```text
Discovery
  -> Hard Screening
  -> Research Queue
  -> Fundamental / Style / Technical Research
  -> ResearchReport with thesis and counter thesis
  -> InvestmentAssessment
  -> Validation
  -> PortfolioProposal and RiskAssessment
```

## Existing Coverage

| Requested concept | Current coverage | Decision |
|---|---|---|
| Fundamental analysis | Value and Financial Research cover survival, cycle, valuation, growth, revenue, profit, cash flow, debt, ROE, ROIC, and restatements | Keep and strengthen PIT evidence; do not duplicate |
| Moving averages | Technical Research has configurable short/long averages and alignment | Extend the existing module |
| Trend and dynamic risk references | Trend Research has Donchian, volume confirmation, ATR, trailing references, and pyramid scenarios | Reuse ATR primitives; do not create another trend engine |
| Indicator confluence | Research confidence has module agreement, but no technical-family confluence contract exists | Add a family-aware assessment only after the data gate |
| MACD plus KDJ | Not implemented | Add as momentum evidence, not an independent strategy |
| Large/small capitalization | Not implemented | Add as cross-sectional Style Research, subject to PIT market-cap and universe gates |
| Bull/bear candle crossing three averages | Not implemented and the market term is not uniformly defined | Add a parameterized pattern definition, never an unversioned slogan |
| Startup-point capture | Not implemented | Model as a PIT-safe state transition, not a hindsight label |
| Dynamic stop | ATR references exist, but there is no position-aware stop policy | Keep as invalidation scenarios until Paper Trading and position state exist |
| Granville rules | Only basic moving-average alignment exists | Add normalized price/average relationship events, separated by rule family |

## Proposed Module Ownership

```text
research/
  financial/                 existing PIT fundamental evidence
  value/                     existing survival/cycle/valuation/growth synthesis
  style/                     future size and style context
  technical/
    indicators/              future pure MACD and KDJ calculations
    moving_average_events/   future triple-cross and Granville events
    confluence/              future family-aware evidence synthesis
  trend/                     existing breakout, volume, ATR, trailing scenarios
  pattern/                   existing China A microstructure patterns
```

Pure indicator functions must consume only ordered visible bars and return
versioned values. Research modules turn those values into explainable evidence.
Neither layer may emit an execution action.

## Technical Evidence Families

Indicator resonance must not count several transformations of the same price
series as independent evidence. Future confluence uses families:

1. `trend_structure`: moving-average alignment, Granville trend-continuation
   events, triple-average crossing structure, and Donchian context.
2. `momentum`: MACD and KDJ state, slope, crossover, and divergence candidates.
3. `participation`: volume ratio, turnover, breadth, market sentiment, and
   industry heat.
4. `volatility_and_risk`: ATR, gap risk, price-limit risk, and stop distance.
5. `style_and_context`: size percentile, market regime, sector, country, and
   liquidity context.
6. `fundamental_quality`: survival, cash flow, debt, profitability, growth, and
   valuation evidence.

Each family contributes at most one bounded component to confluence. MACD and
KDJ agreeing is one momentum-family observation, not two independent votes.
Fundamentals and market participation provide genuinely different evidence,
but no family can approve an opportunity alone.

The future confluence output is research-only:

```text
TechnicalConfluenceAssessment(
  state=INSUFFICIENT_DATA | CONFLICTED | WATCH | ARMED | CONFIRMED | INVALIDATED,
  bullish_families=(),
  bearish_families=(),
  family_scores={},
  confidence_breakdown=...,
  evidence_ids=(),
  reasons=(),
  limitations=(),
  as_of=...,
  model_version=...
)
```

`CONFIRMED` means only that a versioned research setup met its declared
conditions. It is not a buy decision or execution permission.

## MACD And KDJ

### MACD

The reference definition is:

```text
macd_line = EMA(close, fast_period) - EMA(close, slow_period)
signal_line = EMA(macd_line, signal_period)
histogram = macd_line - signal_line
```

The initial candidate configuration is `12/26/9`, but every parameter and EMA
warm-up rule must be versioned. Required evidence includes line values, slopes,
zero-line state, crossover age, and input-bar hash. A crossover on the current
bar cannot use an incomplete bar.

### KDJ

KDJ conventions differ across platforms. The implementation must freeze one
declared formula rather than claim equivalence with every charting package:

```text
rsv = 100 * (close - lowest_low(n)) / (highest_high(n) - lowest_low(n))
k = smooth(rsv, k_period)
d = smooth(k, d_period)
j = 3 * k - 2 * d
```

The zero-range behavior, seed values, smoothing method, and whether `J` may
leave `[0, 100]` must be explicit. KDJ overbought/oversold states are context,
not automatic reversal predictions.

### Confluence Interpretation

- MACD and KDJ bullish together may strengthen momentum evidence.
- A bullish MACD and overextended KDJ can be `CONFLICTED`, not averaged away.
- Momentum confluence requires a separate trend-structure or participation
  family before reaching `ARMED` or `CONFIRMED`.
- Every component must be ablated separately during Validation to measure
  incremental contribution and redundancy.

## Triple-Average Candle Pattern

The colloquial China-market term is ambiguous. The future contract uses the
explicit names `bullish_body_crosses_ma_cluster` and
`bearish_body_crosses_ma_cluster`.

For configured periods `(p1, p2, p3)`, the bullish candidate requires:

```text
close > open
open <= min(MA_p1, MA_p2, MA_p3)
close >= max(MA_p1, MA_p2, MA_p3)
```

The bearish candidate is the exact directional inverse. The commonly cited
`5/10/20` periods are only an initial research configuration. Other definitions
must be separate configuration versions, never silently substituted.

Optional setup evidence is evaluated separately:

- normalized MA-cluster width;
- MA slopes and prior trend;
- candle body and upper/lower shadow ratios;
- volume ratio and turnover;
- distance from the cluster in ATR units;
- market breadth and industry heat;
- price-limit, ST, suspension, and liquidity conditions.

One candle cannot prove a startup. The state model is:

```text
WATCH -> ARMED -> CONFIRMED
   |        |          |
   +------> INVALIDATED
   +------> EXPIRED
```

`WATCH` and `ARMED` use only data visible at the current `as_of`. Follow-through
bars can move a prior setup to `CONFIRMED` only when those bars later become
available. They must never be copied backward into the original decision
context.

## Dynamic Invalidation And Stop Research

Before a real position exists, the system may produce stop references only:

- `structural_reference`: below/above the signal candle and MA cluster;
- `atr_reference`: entry reference plus or minus a configurable ATR multiple;
- `trailing_reference`: monotonic highest/lowest close since confirmation plus
  or minus an ATR multiple;
- `thesis_reference`: a fundamental or industry invalidation condition;
- `time_reference`: setup expiry when follow-through does not occur.

The future assessment preserves every candidate reference and explains which
one is binding under a frozen validation configuration. It must account for A
share T+1, limit-down inability to exit, suspension, gaps, and slippage. A stop
level is not a guaranteed fill price.

## Granville Research Events

Granville-style rules are normalized into eight event identifiers around a
configurable reference moving average:

- four bullish events: upward cross after MA stabilization, pullback through a
  rising MA, support above a rising MA, and extreme downside deviation;
- four bearish events: the directional inverses.

Trend-continuation events and extreme-deviation mean-reversion events belong to
different subfamilies. They cannot be treated as interchangeable confirmations.
Each event records MA period/type, MA slope, price cross, normalized distance,
event age, and supporting/contradicting evidence. The often cited 200-day MA is
a research configuration, not a universal constant.

## Size And Style Research

Large/small capitalization is cross-sectional context, not a single-stock
technical signal. A future `StyleAssessment` requires:

- PIT free-float and total market capitalization with `available_at`;
- the historical eligible universe at the same `as_of`;
- market-specific percentile breakpoints, never one global currency threshold;
- sector and country neutral comparisons where appropriate;
- liquidity, listing-age, ST, suspension, delisting, and price-limit controls;
- explicit exposure and capacity limits in Portfolio/Risk.

The output should describe `size_percentile`, `size_bucket`, liquidity/capacity,
and historical context. It must not rank the whole market and buy the smallest
names. Small-cap exposure remains unacceptable when PIT universe or market-cap
history is missing.

## Fundamental Integration By Horizon

Fundamentals remain primary research evidence, but their role varies:

| Horizon | Fundamental role |
|---|---|
| Long-term ownership | Full Survival, Cycle, Valuation, Growth, Financial, Industry, and Policy assessment |
| Medium-term trend | Survival and liquidity are protective gates; growth, industry, valuation, and policy are supporting or contradicting evidence |
| China A short-term pattern research | ST/delisting/fraud/liquidity/data-quality failures remain hard exclusions; slower fundamentals remain context rather than an intraday trigger |

No technical confluence can offset a hard-screen failure. A technically strong
company with insufficient PIT fundamentals remains low-confidence or
insufficient-data, not silently upgraded.

## Validation Contract

Implementation is not accepted until Validation can evaluate:

- every component alone and the full confluence;
- incremental contribution and correlated-factor redundancy;
- walk-forward and final out-of-sample performance with embargoes;
- parameter stability across nearby values and market subperiods;
- China A and overseas markets separately;
- large/small-cap, sector, regime, and liquidity breakdowns;
- delisted, ST, suspended, and unavailable records without silent removal;
- corporate actions, T+1, price limits, fees, slippage, and failed exits;
- setup expiration, false breakouts, gaps, and stop non-executability.

The final out-of-sample set cannot be repeatedly reused for parameter selection.
Any family with weak incremental contribution is removed or down-weighted even
if its standalone chart looks persuasive.

## External Method References

- TA-Lib MACD reference: <https://ta-lib.org/functions/macd.html>
- TA-Lib Stochastic reference: <https://ta-lib.org/functions/stoch.html>
- Kenneth French size and factor data: <https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_Library.html>
- IFTA technical handbook with Granville rule overview: <https://ifta.org/wp-content/uploads/2018/05/technicalhandbook_2018_NTAA.pdf>
- Founder Securities investor-education example for the `5/10/20` triple-line
  definition: <https://www.foundersc.com/invEduBaseDynamicFz/8610411.jhtml>

These references define calculations or common terminology. They do not prove
profitability in Tong Quant markets.
