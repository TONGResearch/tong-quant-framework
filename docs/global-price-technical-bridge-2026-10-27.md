# Global Price Evidence To Technical Diagnostics

Date: October 27, 2026, Malaysia time. WP-LAUNCH-001 remains ready, not accepted.

## Delivered Boundary

The existing Provider interface and neutral ingestion now accept an explicit
YahooGlobalSnapshotAdapter dataset, `global_equity_price_snapshot`. It retains
one bounded decoded-response envelope and one status observation per capture,
including provider failures, invalid responses and empty observations. This is
not a second provider, canonical daily-bar population or replacement of the old
`global_daily_bars` monitor/calibration dataset. Existing records are not upgraded.
Global snapshot version: `global-equity-price-snapshot-v1`, centrally managed.

Requests explicitly identify market, Yahoo symbol, native currency/exchange,
market timezone and date range. Native equity identity, daily granularity,
aligned arrays, finite positive OHLC, integer nonnegative volume, chronology,
session-date uniqueness and range are checked. Identity matching is a structural
claim, not issuer/share-class qualification. Financial and nonfinancial equities
share this price path; neither receives financial research or a sector score.
Funds and China-A tickers cannot enter this dedicated overseas path.

## Reconstruction And Time

`data.global_price_inputs` reads one SQLite snapshot, chooses the latest visible
capture without favorable fallback, verifies retained bytes and exact rebuilt
record/artifact/registry/completed-batch ownership, and reconstructs ephemeral
Bar values for exploratory calculations. Equal-time captures remain ambiguous.
Malformed/tampered latest captures, failures, incomplete batches, missing files
and optional stale-observation checks withhold the series. Old evidence remains.
The immutable envelope carries the actual capture instant; historical retrieval
is never backdated. Artifact published_at means capture time, not issuer release.

Daily completion is not established by a timestamp. Current exchange-date series
are conservatively withheld, including the New York previous-UTC-date boundary.
This is not a reviewed session-close calendar. Observation age uses the delivered
daily timestamp, not a verified closing instant. Default freshness is UNASSESSED;
an operator-supplied age limit is a diagnostic, not an admitted strategy policy.

Provider-native OHLC adjustment history remains unverified: disabling the
adjusted-close field does not prove original unadjusted historical prices.
The transient Bar adjustment NONE means Tong applied no transformation. These
values must not populate strict-PIT canonical bars or HistoricalReplay, enter
official scored research, or claim source/strategy validation from calculations.

## Operator Entry

`scripts/inspect_global_technical.py` is read-only by default and requires a fixed
as-of. Only explicit `--capture` enables a public-price request and writes to the
existing evidence/artifact/batch stores. Capture requires start/end, currency and
exchange, rejects historical as-of, and pins the cutoff after transport, before
strict ingestion. Credentials and raw transport exception details are not stored.
Sensitive decoded fields are rejected before envelope serialization/persistence.
The shared Yahoo HTTP client now bounds the response before JSON parsing.

The output calls the existing MACD/KDJ, family-confluence, moving-average/
triple-line, setup/invalidation and Granville diagnostics. It does not create a
ResearchQueue, ResearchReport, Signal, Financial assessment or InvestmentScore.
Sentiment/industry confirmation and fundamentals remain NOT_ASSESSED. Exit code
2 is deliberate partial diagnostic status, not a crash or validation success.
Read-only mode neither initializes the database nor requests the network.

Example repeatable read, using a retained capture and its actual cutoff:

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market us --symbol MSFT --as-of 2026-10-27T03:28:48.973599+00:00
```

## Real Public-Data Exercise

Captured October 27, approximately 11:27-11:28 Malaysia time, through Yahoo.
Dates below are delivered daily observation dates, not independently verified
exchange-session completeness. Symbols are integration samples, not selections.

| Market / sample | Requested end | Reconstructed observations | Last delivered date | Result |
| --- | --- | --- | --- | --- |
| US / MSFT | October 26 | Withheld | October 26 in retained response | Current New York date at capture; completion unverified |
| US / MSFT | October 23 | 706 | October 23 | observed_unqualified; exploratory calculations available |
| Hong Kong / 0700.HK | October 26 | 692 | October 26 | observed_unqualified; exploratory calculations available |
| Malaysia / 1155.KL | October 26 | 690 | October 26 | observed_unqualified; exploratory calculations available |

Fixed-cutoff re-reads of all three usable-for-calculation captures produced exact
matching output/input hashes. SQLite hash stayed
`5024aa50b8f3e0faca87204f657901c159182db3b6cea41fb0b97d78f67486d5`.
The separate exploratory database contains 4 evidence records, 4 artifacts and
4 completed batches; zero canonical daily_bars, ResearchReports and Signals.
Files remain ignored local artifacts, not Git records or encrypted recovery.
Their new source bytes/database require encrypted co-retention before portability
or recovery can be claimed.

## Remaining Gates

No trust/PIT promotion: LOW / RETRIEVAL_TIME, PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled. No Paper, broker, execution, Portfolio or
Notification implementation changes. Still required: independent market/source
identity and adjustment/lifecycle/calendar/continuity review, sector-specific
global financial inputs, Style/weekly-monthly/intraday completion, actual official
screened research chain and admitted historical/strategy validation. Three
successful transports are neither global coverage percentages nor accuracy proof.

Synthetic tests cover all three markets, source tampering, actual UTC/cutoff,
future completion, equal-time ambiguity, failures, stale/malformed/current-day
series, credentials, bounded HTTP reads and deterministic read-only CLI output.
Full suite: 2190 passed / 6 skipped, 139.32 seconds; 55 added regressions.
Ruff, mypy (263 files), governance (121 checks), new-path forbidden-import check
and git diff --check pass. The six default-disabled provider/notification network
tests remain skipped; real Yahoo exercises above are separate evidence, not
proof that those skipped integrations passed. No commit or push was performed.
