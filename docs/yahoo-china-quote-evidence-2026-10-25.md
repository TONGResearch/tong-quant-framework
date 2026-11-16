# Yahoo China Price Evidence: October 25

WP-LAUNCH-001 remains `ready`, not accepted. Objective: retain a functioning
price-only source without pretending it supplies market capitalization, canonical
daily closes, independently verified source truth or trading permission.

## Source Investigation

- The existing fixed Eastmoney quote probe returned HTTP 502 with 157 bytes,
  no price, shares or market value. A separate request without environment proxy
  use also returned 502; conventional proxy environment variables were absent.
  This does not distinguish provider versus intermediary failure. No new
  Eastmoney observation is archived in this slice; its old failure is retained.
- The existing YahooChartHttpClient returned one 002624.SZ chart result, native
  CNY/SHZ metadata, regularMarketPrice and regularMarketTime. The metadata did
  not provide marketCap or sharesOutstanding. Chart success is price evidence
  only, not coverage of those missing inputs.
- The installed AKShare stock_zh_a_spot_tx implementation points to Tencent's
  public board-ranking endpoint. One bounded-attempt probe returned 200 rows
  and native keys including zxj, zsz and ltsz. This is not a complete universe,
  not verified units/timing and not a quote comparison for 002624. No Tencent
  adapter, normalized market value or calibration result is introduced.

Primary implementation reference for the Tencent candidate is installed AKShare
`stock/stock_zh_a_tx.py`; its project documents the function in the
[official tutorial](https://github.com/akfamily/akshare/blob/main/docs/tutorial.md).
The current [AKShare stock documentation](https://akshare.akfamily.xyz/data/stock/stock.html)
does not by itself qualify these Tencent native field semantics.

## Bounded Implementation

`data.providers.yahoo_quote.YahooChinaQuoteEvidenceAdapter` implements the
existing ProviderEvidenceAdapter interface for the distinct dataset
`china_equity_quote_observation`. It does not change the global Yahoo daily-bar
adapter's market capabilities or Tushare implementation.

Explicit six-digit SSE/SZSE equity routes map to .SS/.SZ. BSE, funds, already
suffixed tickers, malformed codes and unrelated market/parameter requests are
rejected instead of guessed. A code route is not a dated listing/eligibility
record. Metadata must match the requested ticker, native exchange, CNY, EQUITY
and Asia/Shanghai; boolean, missing, nonpositive, nonfinite, oversized numbers
and future claimed quote epochs cannot become a valid price observation.

Only regular-market metadata is consumed. Historical candle closes, adjusted
closes and incidental marketCap/sharesOutstanding keys are not substituted.
Shares/market values remain null and all investment/valuation/replay/execution
authorization flags remain false. Invalid and unavailable attempts remain
explicit nonnumeric observations, never zero quotes.

The current snapshot comes from the existing Yahoo chart client, one attempt and
a six-second socket timeout. A security-screened, size-bounded decoded JSON
envelope retains payload, actual retrieval time, query date and normalization
version. **This is SDK-decoded reserialization, not original HTTP wire bytes.**
Its byte limit is checked after SDK decoding; the existing chart transport's
unbounded response read, redirects and lack of a whole-call deadline require
separate hardening. Do not present the post-decode bound as full transport safety.
Opaque secret detection is not guaranteed; credential-like fields/assignments
are rejected before persistence. No source authentication uses a user account.

The existing ProviderNeutralIngestionService publishes evidence/artifact/batch
records atomically, preserving LOW trust and RETRIEVAL_TIME availability.
Prefetch completes before pinning the ingestion cutoff; strict PIT is not relaxed
and the source-claimed quote time is never used to backdate availability.

## Read-Side Reconstruction

`data.quote_evidence.inspect_yahoo_quote` reads through MarketDataService in one
snapshot and replays normalization from the retained decoded envelope. It verifies
exact record/content/artifact metadata, evidence/artifact batch ownership, complete
batch status, parameters, hashes and actual UTC chronology at an explicit cutoff.
Rejected observations remain visible. Latest failure, rejection or timestamp ties
cannot fall back to an old favorable quote. The diagnostic hash is deterministic
for the same retained rows and cutoff.

The diagnostic uses existing provider models, not a new ResearchReport or market-
value model. It is not automatically consumed by ResearchContext, financial
scoring, the existing market-value reader, Portfolio or trading code. Snapshot
consistency is not independent verification. Freshness stays UNASSESSED pending
an explicit reviewed session/age policy. Official combined price/fundamental
admission remains separate unfinished work, not an implicit fallback selection.

`scripts/capture_yahoo_quote.py` requires an existing explicit research database
and artifact root. Capture and `--read-only --as-of` inspection are separate;
historical as-of is forbidden during capture. Exit 2 always signals unqualified
diagnostics, including successful storage, not an admitted investment outcome.

## Actual Retained Observation

Database: `data/processed/technical-request-20261020.sqlite3`.
Artifact root: `data/processed/raw/provider-artifacts`.
Subject: 002624 / China-A / native Yahoo 002624.SZ.
Inspection cutoff: `2026-10-25T15:10:07.279497+00:00`.
Native price: 10.0, claimed currency CNY.
Claimed quote time: `2026-10-23T07:04:33+00:00` (15:04:33 Asia/Shanghai).
Status: `price_only_unqualified`; source_bound=true, freshness=UNASSESSED.
It is not a live executable price, verified daily close or valuation numerator.

```text
retained envelope hash 85821b432611bb35fa3c71e9118f9f23d432fd3332905f911460d884a1202996
inspection hash        8015b55412118d4925a58c28e59c00ae987898871093bef4f99d8ac0d05689a3
artifact audit hash    74affbbfd9e4efc4d2a5fed25760779211355901789408c8ce1a2278ea044d34
```

Two fixed-cutoff reads agree; a cutoff at 14:00 UTC on the capture date sees no
observation. The new capture adds one evidence record, one artifact registration
and one ingestion batch: totals 3393, 18 and 20 respectively. Registered files
verify 18/18. Existing 2696 daily-bar rows, 17 fundamental facts and zero research
reports/signals are unchanged. These are inventory counts, not market coverage.
No adjusted/canonical prices, market values, financial reports or real queue
entries are manufactured. The new ignored artifact is outside older encrypted
retention; byte verification is not backup, authenticity or PIT qualification.

## Verification And Next Work

Sixty-six new offline cases cover routing, metadata/number/clock/schema safety,
secret/size filtering, irrelevant adjusted/share fields, atomic/idempotent writes,
cutoff visibility, exact source binding/tamper rejection, failure/tie handling,
batch completion and read-only/capture CLI behavior. Focused suite: 66 passed in
3.76 seconds. Full suite: **1894 passed / 6 skipped**, 63.63 seconds. Ruff passes,
mypy passes for 254 files, governance passes 110 checks, and `git diff --check`
passes. The database/new artifact are Git-ignored; no local evidence is staged.
Real public access and retained-file checks above are separate from offline
regressions. The six opt-in network checks stay disabled by default.

Version: yahoo-china-price-observation-v1. Framework 0.8.0/schema 0.8.2/migration
head remain unchanged. No new tables or rewriting of prior source identities.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled persist.
No commit/push, Paper, broker, orders, allocation or trading changes.

Next: qualify dated share-class-aware shares/market values and their actual
units, quote/session timing, corporate-action and FX context. Bind fresh prices,
fundamental editions and technical inputs at a reviewed common decision cutoff,
then validate the actual candidate conditions. A working price endpoint neither
resolves market-value gaps nor qualifies a buy/sell decision. Tencent native
semantics and provider consistency require their own evidence review; no provider
is trusted by default and Tushare remains optional/frozen.
