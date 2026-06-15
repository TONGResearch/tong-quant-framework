# V0.5 Research Engine

## Purpose

V0.5 consumes opportunities that already passed V0.4 hard screening:

```text
Research Queue
      |
Point-in-time ResearchContext
      |
Policy + Financial + Industry + Value + Technical + Trend + Pattern
      |
ResearchReport + ResearchAssessment + RESEARCH Signal
      |
Future Validation
```

The engine evaluates and documents opportunities. It does not backtest, approve
trades, create orders, or connect to brokers.

## Required Report Contract

Every `ResearchReport` must include:

- Thesis
- Counter thesis
- At least one explicit thesis invalidation condition
- Module assessments, findings, risks, limitations, and evidence references
- Research confidence and its four components
- Unresolved questions

Invalidation conditions contain a metric, comparison operator, threshold,
observation window, and rationale. This makes each conclusion falsifiable
instead of turning a narrative into an untestable belief.

## Modules

### Policy

Produces `PolicyAssessment` across:

- Regulatory environment
- Industrial policy
- Fiscal policy
- Monetary policy
- Geopolitical factors

Policy is a dependency of Industry, Value, and Trend research. It remains one
research variable and cannot determine an investment decision by itself.

### Financial

Reviews revenue, profit, cash flow, debt, ROE, and ROIC evidence. It consumes
point-in-time fundamental facts and exposes visible restatement history. The
data service can return both the latest visible fact per reporting period and
the complete revision history visible at the requested `as_of`.

### Industry and Value

Industry covers trend, heat, cycle, and relative strength. Value covers
Survival, Cycle, Valuation, and Growth. Both preserve dependency conclusions as
features so later validation can reconstruct the reasoning chain.

### Technical

Calculates long-term, weekly, monthly, moving-average, and 52-week-position
research from visible daily bars. These are research measurements, not entries
or exits.

### Trend

Implements the research form of the Tong Quant Trend Engine:

- Donchian breakout confirmation
- Volume confirmation
- Market sentiment confirmation
- Industry heat confirmation
- ATR risk references
- Pyramid scenario levels
- Trailing reference for the let-winners-run principle

ATR stops and pyramid levels are hypothetical research geometry only. The
module does not size a live position or issue a buy/sell decision.

### Pattern

The V0.5 Pattern module is China A-share specific. It requires complete
point-in-time market breadth and intraday evidence for rising stocks,
first-board continuation, pullbacks, VWAP, opening price, and volume behavior.
Missing evidence produces `InsufficientData`; non-China markets produce
`NotApplicable`.

## Confidence

Confidence is not a simple average of module scores. It combines:

- Evidence quality
- Data completeness
- Module agreement
- Point-in-time integrity

The implementation uses a weighted geometric calculation with a weakest-link
cap. A weak or failed integrity component therefore limits total confidence
instead of being hidden by strong values elsewhere. Any point-in-time failure
forces confidence to zero.

## Dependency Execution

The engine resolves requested modules and their dependencies in topological
order. Requesting Value automatically runs Policy, Financial, and Industry.
Requesting Trend automatically runs Policy, Industry, and Technical.

Market Regime may be attached to the context and report as a research variable.
It is not a hard gate.

## Persistence

V0.5 adds:

- `research_runs`
- `research_evidence`
- `research_assessments`
- `research_reports`

Queue claiming is atomic: only a `pending` entry can transition to
`in_research`. A completed or incomplete research run transitions the queue
entry to `completed`. The universal Signal is stored in the existing `signals`
table with action `RESEARCH`.

## Current Data Limits

AKShare daily bars and point-in-time fundamentals support part of V0.5.
Provider-backed policy, industry heat, market sentiment, and intraday pattern
evidence remain future ingestion work. V0.5 does not fabricate these inputs;
the affected modules report reduced confidence or insufficient data.
