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

`ChinaAShareRules` now fails closed for sellability and price limits until
exchange-calendar, board, dated status, and effective-date evidence is supplied.
Its former next-calendar-day T+1 approximation and static 5% ST / 10% other
price-limit approximation must not be used for Paper Trading. For example,
the Shanghai Stock Exchange changed the main-board risk-warning limit from
5% to 10%, effective 2026-07-06. This alone makes an undated ST rule unsafe
for historical reconstruction. Source:
https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml

Market-specific rules remain a blocking dependency for simulation eligibility.
The selected pilot market needs source-backed, effective-dated fixtures before
its paper fill model may claim realistic market behavior.
