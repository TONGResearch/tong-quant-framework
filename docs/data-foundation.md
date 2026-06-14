# V0.2 Data Foundation

## Pipeline

```text
AKShare -> Raw schema validation -> Normalization -> Domain validation -> SQLite
              |
         compressed local cache
```

## Supported Data

- China A-share unadjusted, forward-adjusted, and backward-adjusted daily bars
- China stock-index daily bars
- China trading dates
- Current A-share universe
- Current basic company information
- Point-in-time fundamental fact persistence contract
- Historical universe membership and security-status persistence contract

## Point-in-Time Rules

Daily bars use:

- `timestamp`: market close on the trading date
- `available_at`: one minute after market close
- `ingested_at`: when Tong Quant retrieved the record

Queries require a timezone-aware `as_of` value and only return records where
`available_at <= as_of`. Revised versions are retained and the newest version
available at that time is selected.

Company information and the A-share universe are current snapshots. They are
stored with their retrieval time and must not be treated as historical company
fundamentals or historical index membership.

Fundamental facts use separate observation and availability fields:

- `period_start` and `period_end`: accounting period represented by the fact
- `published_at`: issuer or source publication time
- `available_at`: earliest time Tong Quant permits the fact to influence a decision
- `revision`: version number for restatements and corrections

Historical queries select only facts with `available_at <= as_of` and return
the latest version that was visible at that time. A later restatement therefore
cannot replace the value seen by an earlier backtest.

Historical security reconstruction uses two independent records:

- `universe_memberships`: when a security belonged to an index, exchange-wide,
  or custom research universe
- `instrument_status_history`: listed, suspended, ST, delisting, or delisted
  state, tradability, and historical industry

Membership and tradability are intentionally separate. A security may belong
to a historical universe while being suspended or otherwise not tradable.

The trading calendar is operational reference data. Historical dates are marked
available from the beginning of their trading date, but source corrections are
not reconstructed before Tong Quant first ingests them.

## SQLite Tables

- `instruments`
- `daily_bars`
- `trading_calendar`
- `fundamental_facts`
- `instrument_status_history`
- `universe_memberships`
- `signals`
- `screening_results`

Signals and screening results exist to provide the future persistence contract.
V0.2 does not implement screening or trading strategies.

## Cache

Raw provider responses are stored as compressed JSON table files under
`data/cache`. Cache keys include the dataset and all request parameters. The
default expiry is 24 hours and is configurable in `config/default.toml`.

## Known Limitations

- AKShare is an aggregation library backed by third-party websites; upstream
  schemas and availability can change.
- Provider ingestion for historical fundamentals, status changes, delistings,
  and universe membership is not implemented yet. The canonical models,
  storage, and point-in-time read contracts now exist.
- Current company information must still not be used as point-in-time
  historical fundamentals.
- Exact exchange holidays beyond the ingested source are not synthesized.
