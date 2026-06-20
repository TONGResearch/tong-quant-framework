# V0.2 Data Foundation

## Pipeline

```text
AKShare -> Raw schema validation -> Normalization -> Domain validation -> SQLite
              |
         compressed local cache
```

## Supported Data

- China A-share unadjusted daily bars
- China stock-index daily bars
- China trading dates
- Current A-share universe
- Current basic company information
- Point-in-time fundamental fact persistence contract
- Historical universe membership and security-status persistence contract
- V0.6.2 audited ingestion batches, raw payload hashes, provider limitations,
  and availability warnings
- V0.6.2 conservative PIT population for selected AKShare fundamentals,
  instrument-status snapshots, index membership, and corporate actions
- Security lifecycle events for suspension/resumption, partial ST history, and
  delisting evidence
- Fundamental publication events with date-only or exact availability evidence
- Historical coverage assessments and provider consistency reports
- Provider conflict observations and calibrated dataset confidence assessments

## Point-in-Time Rules

Daily bars use:

- `timestamp`: market close on the trading date
- `available_at`: one minute after market close
- `ingested_at`: when Tong Quant retrieved the record

Queries require a timezone-aware `as_of` value and only return records where
`available_at <= as_of`. Revised versions are retained and the newest version
available at that time is selected.

Strict point-in-time ingestion rejects provider-generated forward-adjusted and
backward-adjusted histories. Those series may incorporate corporate actions
that occurred after an earlier research date. Adjusted historical prices may
only be enabled after Tong Quant stores dated corporate-action factors and can
reconstruct the adjustment visible at each historical decision time.

Company information and the A-share universe are current snapshots. They are
stored with their retrieval time and must not be treated as historical company
fundamentals or historical index membership.

Fundamental facts use separate observation and availability fields:

- `period_start` and `period_end`: accounting period represented by the fact
- `published_at`: issuer or source publication time
- `available_at`: earliest time Tong Quant permits the fact to influence a decision
- `revision`: version number for restatements and corrections
- `raw_data_hash`: provider payload fingerprint
- `batch_id`: ingestion batch that introduced the record
- `availability_precision`: exact, date-only, estimated, retrieval-time, or unknown
- `trust_level`: verified, high, medium, low, or unknown

Historical queries select only facts with `available_at <= as_of` and return
the latest version that was visible at that time. A later restatement therefore
cannot replace the value seen by an earlier backtest.

Availability precision and trust level are intentionally separate. A dataset can
have a precise date but low trust, or retrieval-time availability with medium
trust. Research, Validation, and future HistoricalReplay code must inspect both.

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

## V0.6.2 PIT Population

V0.6.2 fills existing structures where AKShare provides usable history, while
recording limitations whenever publication time or historical intervals are not
reliable.

Implemented conservative ingestion:

- Financial statements from AKShare financial endpoints into
  `fundamental_facts`
- Current ST and suspended snapshots into `instrument_status_history`
- Delisting records into `instrument_status_history`
- CSI index membership into `universe_memberships`
- Dividend and split-like corporate action rows into `corporate_actions`
- Raw dataset fingerprints and ingestion batches for every new dataset
- Data availability warnings when exact publication time is unavailable

PIT remediation adds dated suspension/resumption evidence, Shenzhen ST
name-change evidence, delisting events, market-wide and CSI snapshot
accumulation, actual disclosure dates, and exact CNInfo announcement evidence.
Complete national ST history, true relisting history, and historical CSI
entry/exit ledgers remain unavailable from the current provider.

Strict point-in-time mode still rejects provider-adjusted bars. Corporate
actions are stored for audit and future reconstruction, but they do not yet
enable adjusted historical price usage.

## PIT Readiness

`PITReadinessAssessment` quantifies whether a dataset is ready for future
historical replay. It records:

- Coverage ratio
- DataTrustLevel
- Missing critical fields
- Warnings
- `ready_for_historical_replay`
- Readiness score and `usable`, `caution`, or `unsuitable` classification
- Coverage, trust, availability, revision, continuity, and provider-consistency
  component scores
- Explicit assumptions

HistoricalReplaySource is implemented and consumes this readiness assessment.
Low readiness lowers replay confidence and preserves warnings; it does not
silently discard the sample or reinterpret the dataset as PIT-safe.

## SQLite Tables

- `instruments`
- `daily_bars`
- `trading_calendar`
- `fundamental_facts`
- `instrument_status_history`
- `universe_memberships`
- `corporate_actions`
- `ingestion_batches`
- `raw_dataset_fingerprints`
- `data_availability_warnings`
- `provider_limitations`
- `pit_readiness_assessments`
- `security_lifecycle_events`
- `fundamental_publication_events`
- `historical_coverage_assessments`
- `provider_consistency_reports`
- `provider_conflicts`
- `dataset_confidence_assessments`
- `historical_replay_manifests`
- `historical_replay_samples`
- `portfolio_proposals`
- `position_proposals`
- `risk_assessments`
- `portfolio_exposures`
- `portfolio_constraints`
- `notification_outbox`
- `notification_deliveries`
- `notification_dead_letters`
- `schema_migrations`
- `signals`
- `screening_results`

Portfolio and risk tables persist research artifacts only. They do not contain
orders, fills, broker requests, or execution instructions.

## Cache

Raw provider responses are stored as compressed JSON table files under
`data/cache`. Cache keys include the dataset and all request parameters. The
default expiry is 24 hours and is configurable in `config/default.toml`.

## Known Limitations

- AKShare is an aggregation library backed by third-party websites; upstream
  schemas and availability can change.
- Provider ingestion for historical fundamentals, status changes, delistings,
  and universe membership is partial and provider-limited. Exact issuer
  publication timestamps are not always available through AKShare.
- Current company information must still not be used as point-in-time
  historical fundamentals.
- Exact exchange holidays beyond the ingested source are not synthesized.
- Point-in-time-safe corporate-action and adjustment-factor ingestion is not
  implemented. Strict mode therefore accepts unadjusted bars only.

The dataset-by-dataset classification is maintained in
`docs/data-trust-matrix.md` and takes precedence over broad statements of
support in this document.
