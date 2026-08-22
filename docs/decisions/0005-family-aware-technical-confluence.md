# ADR 0005: Family-Aware Technical Confluence

## Status

Accepted as future architecture; implementation deferred by the trading and
data-readiness freeze.

## Context

Tong Quant may evaluate MACD, KDJ, moving-average structure, Granville events,
triple-average candle patterns, volume, ATR, size, and fundamentals. Several of
these are correlated transformations of the same price history. Counting each
as independent confirmation would create false confidence and increase data
snooping risk.

## Decision

- Technical indicators remain ResearchEvidence, never direct trade actions.
- Confluence groups evidence into trend structure, momentum, participation,
  volatility/risk, style/context, and fundamental-quality families.
- Each family contributes at most one bounded component.
- Agreement and contradiction remain separate outputs; disagreement cannot be
  hidden by arithmetic averaging.
- Size is cross-sectional Style Research and requires PIT market cap plus the
  historical eligible universe.
- Triple-average and Granville terminology is converted into explicit,
  versioned predicates.
- Follow-through is observed only after it becomes available and cannot be
  written backward into an earlier setup.
- Dynamic stop values are invalidation references until a future approved
  position-aware layer exists.

## Consequences

The design is more conservative than a simple indicator vote. It requires more
metadata and validation, but it reduces double counting, lookahead, ambiguous
pattern definitions, and accidental execution semantics.
