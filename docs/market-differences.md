# Market Differences

Shared analytical engines must not assume that all equity markets behave like
A-shares. Market behavior is supplied through explicit rules and configuration.

## A-Share Areas Requiring Dedicated Rules

- T+1 sale eligibility
- Board-lot and odd-lot handling
- Main board, STAR, ChiNext, Beijing, ST, and special price-limit rules
- Suspensions and resumptions
- Limit-up and limit-down fill feasibility
- Opening and closing auctions
- Lunch break and exchange sessions
- New-listing periods
- Stamp duty, commissions, transfer fees, and minimum fees
- Corporate actions and adjusted-price policy
- Delisting, ST history, and point-in-time investable universes

## Global Market Areas

- Exchange-specific calendars and time zones
- Settlement and same-day trading restrictions
- Fractional shares and board lots
- Short selling and borrow availability
- Currency conversion
- Market, limit, auction, and extended-hours orders
- Volatility interruptions
- Exchange and broker fee schedules

V0.1 contains interfaces and conservative placeholders only. Exact production
rules require source-backed implementation and tests per market.
