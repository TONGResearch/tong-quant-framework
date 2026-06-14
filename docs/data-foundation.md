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

The trading calendar is operational reference data. Historical dates are marked
available from the beginning of their trading date, but source corrections are
not reconstructed before Tong Quant first ingests them.

## SQLite Tables

- `instruments`
- `daily_bars`
- `trading_calendar`
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
- V0.2 does not create a historical security-master or delisting database.
- Current company information must not be used as point-in-time historical
  fundamentals.
- Exact exchange holidays beyond the ingested source are not synthesized.
