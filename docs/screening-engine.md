# V0.4 Screening Engine

## Philosophy

Tong Quant does not rank the entire market and buy the highest-scoring stocks.

```text
Discovery
-> Hard Screening
-> Research Queue
-> Research Score
-> Research
-> Investment Score
-> Validation
-> Execution
```

Scoring supports decisions after candidates have passed hard screening. It
does not create opportunities and cannot offset a hard failure.

## Discovery Contract

`OpportunityCandidate` records:

- Instrument and discovery source
- Discovery and availability timestamps
- Thesis and supporting evidence
- Urgency and confidence
- Optional tags

All candidates must be visible at the screening `as_of` timestamp.

## Hard Screening

Rules run in order and stop at the first failure:

1. Data quality
2. Security lifecycle and tradability
3. Hard risk flags
4. Historical liquidity
5. Point-in-time financial health

A failure emits an `EXCLUDE` Signal and no score is calculated. Thresholds and
required data are market-policy concerns, not shared engine assumptions.

## Market Policies

The shared engine supports:

- China A
- US
- Hong Kong
- Malaysia

Each market owns status exclusions, hard risk flags, liquidity requirements,
and financial-health requirements. The V0.4 defaults intentionally avoid
inventing unvalidated numerical thresholds; provider-backed calibration is a
future validation task.

## Seven Dimensions

- News
- Industry
- Survival
- Growth
- Valuation
- Positioning
- Macro

Macro evidence may include rates, inflation, credit, liquidity, currency, and
policy conditions. Generic evaluators normalize already timestamped evidence;
provider-specific analytical models are not fabricated in V0.4.

## Research Queue

Every admitted entry retains three distinct values:

- `priority_score`: scheduling priority
- `urgency_score`: time sensitivity
- `confidence_score`: reliability of discovery evidence

Default priority combines Research Score, urgency, and confidence, while
preserving all three values separately.

Each screening run returns both primary V0.4 products:

- `Watchlist`: candidates that passed every hard screen
- `Research Queue`: admitted candidates with research scheduling metadata

## Two Scores

### Research Score

Calculated immediately after hard screening from the seven dimensions. Its only
purpose is to prioritize qualified candidates for research.

### Investment Score

Calculated only after research is completed. It evaluates researched
opportunities before validation.

Market Regime is a 25% default Investment Score component. It is deliberately
high weight but remains below the maximum single-component limit. It cannot
approve, reject, or create an order by itself.

## Persistence

V0.4 adds:

- `research_queue`
- `screening_scorecards`

Hard results continue to use `screening_results`, while universal Signals use
the existing `signals` table.

## Non-Goals

- No full-market factor ranking
- No buy or sell decisions
- No strategy implementation
- No AI authority over hard screening
- No automatic validation approval
- No orders or broker integration
