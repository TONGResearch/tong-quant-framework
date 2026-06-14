# Tong Quant Framework Product Vision

Owner: Tong Li

Tong Quant Framework is a personal quantitative investment research platform.

Its philosophy is:

> Discover Opportunities -> Screen Opportunities -> Research Opportunities ->
> Validate Opportunities -> Execute Opportunities

The framework is neither a pure quantitative trading system, a pure
technical-analysis system, nor a pure AI system. It identifies potentially
attractive opportunities first and then applies traditional investment
research, quantitative validation, market analysis, risk controls, and
controlled execution.

## Markets

- China Market Engine: A-shares, with long-term and short-term workflows
- Global Market Engine: US, Hong Kong, Malaysia, and future markets

Shared engines are reused across markets. Exchange-specific behavior remains
inside market rules, calendars, fee models, data adapters, and broker adapters.

## Long-Term Investing

Value research dimensions:

1. Survival
2. Cycle
3. Valuation
4. Growth

Technical research covers weekly and monthly trends, long-term moving averages,
52-week highs, and reasonable entry positioning.

## Short-Term Investing

The future Tong Quant Trend Engine is based on a modified Turtle framework.
Breakout, volume, market sentiment, and industry heat must all confirm a signal.
Donchian breakout, ATR risk control, ATR stops, pyramiding, and letting winners
run are retained. Blind and price-only breakout decisions are rejected.

The future K-line subsystem is specific to A-share short-term trading and must
not be generalized to overseas markets without separate validation.

## Shared Engines

- Opportunity Discovery
- Screening: news, industry, survival, growth, valuation, and positioning
- Research
- Validation
- Market Regime: bull, sideways, and bear
- Risk
- Portfolio
- Events
- AI-assisted analysis
- Notifications
- Execution

All analytical engines output universal Signals. Only Execution creates Orders.
AI assists screening and research but never directly decides trades.

## Development Priorities

1. Clean architecture before strategy speed
2. No future-data leakage
3. Explainable and backtestable decisions
4. Risk management before returns
5. Market-specific behavior made explicit
6. MVP before complex strategies or advanced AI
