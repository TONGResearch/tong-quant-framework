# Global Native Financial Observations And Technical Context

Date: October 27, 2026, Malaysia time. WP-LAUNCH-001 stays ready, not accepted.

## Delivered

YahooFundamentalSnapshotAdapter uses the existing Provider interface for
`global_native_fundamental_snapshot`. It requests seven selected native annual
fields: revenue, net income, operating cash flow, assets, liabilities net minority
interest, stockholders equity and total debt. Source names are preserved, NOT
canonical financial definitions or a complete financial checklist. Version:
`global-native-fundamental-snapshot-v1`, centrally managed.

Endpoint construction and native asOfDate/reportedValue structure were checked
against [yfinance's primary implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/fundamentals.py)
and actual public responses. No yfinance dependency, authenticated cookie,
credential or access-control workaround was introduced. This unofficial source
may change/restrict access; successful transport does not certify future access.
Transport bounds reads before JSON parsing, uses an 8-second timeout, retries
network/429/server failures at most twice and preserves sanitized HTTP failures.
Sensitive/nonfinite/oversized decoded data cannot enter retained envelopes.
Decoded snapshots are not original HTTP bytes or issuer filings.

## Financial Boundaries

- Keep reporting currency independent of quote currency. No FX or PE/PB follows.
- asOfDate is a native period end, not publication/availability; available_at is
  actual capture time. published_at, period_start and issuer_revision stay unknown.
  Source timestamp arrays never become release timestamps.
- Keep native 12M labels and arbitrary fiscal year ends. Do not impose January
  starts, infer YTD/TTM or turn balance-sheet amounts into annual flows.
- Preserve raw numbers, including zero/negative values. Never parse fmt units,
  replace null with zero, or alias net income/debt/equity to admitted parent
  profit/interest-bearing debt/group financial definitions.
- Unknown/duplicate periods or bad latest rows cannot select older favorable
  values. Missing, empty, partial and wholly unusable data have separate states.
- Seven parseable fields are not complete financial research. Caller-requested
  bank/securities/insurance/nonfinancial scope is unverified context, not policy.

No FundamentalFact, ResearchQueue, ResearchReport, InvestmentAssessment or
InvestmentScore is created. LOW / RETRIEVAL_TIME native input diagnostics remain
outside canonical Financial inputs. Source-bound means retained consistency,
not accuracy, independent agreement, revision history, PIT or scoring permission.

## Shared Reconstruction And Entry

`data.retained_snapshot` consolidates decoded-envelope/artifact/evidence/registry/
completed-batch verification for global price and native financial readers.
Adapters still own normalization. `providers.yahoo_identity` shares conservative
symbol routing, not exchange rules or issuer qualification. All three existing
real price-only hashes remain unchanged after extraction; no old source identity,
version or China filing input contract is rewritten. No schema change is needed.
Review reproduced acceptance of a naive stored completion time via the machine's
ambient timezone. Shared verification now explicitly requires timezone-aware
artifact and batch timestamps before UTC comparison. One failing regression
turned passing; this scoped repair does not certify other storage consumers.

`scripts/capture_global_fundamentals.py` defaults to a fixed-cutoff read. Explicit
--capture requires dates and forbids historical as-of; actual capture precedes
strict ingestion. `scripts/inspect_global_technical.py --fundamentals
--sector-profile ...` reads both groups in one SQLite snapshot at one cutoff.
Absent these flags, old price-only output is unchanged. All profiles remain
NOT_ADMITTED; existing FinancialInputSnapshot profiles are not expanded. Matching
currency labels do not qualify valuation. Exit 2 is partial diagnostic status.

Example retained read, not capture or trading instruction:

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market hong_kong --symbol 0700.HK \
  --as-of 2026-10-27T04:20:54+00:00 \
  --fundamentals --sector-profile nonfinancial
```

## Real Exercise

Actual captures: around 12:20 Malaysia time, October 27. Combined fixed cutoff:
`2026-10-27T04:20:54+00:00`. Symbols are integration samples, not stock selections.

| Market / sample | Price rows | Native observations | Parseable latest fields | Latest revenue period | Quote / statement currency |
| --- | --- | --- | --- | --- | --- |
| US / MSFT | 706 | 28 | 7 | 2026-06-30 | USD / USD, same label unverified |
| HK / 0700.HK | 692 | 28 | 7 | 2025-12-31 | HKD / CNY, no FX/valuation |
| MY / 1155.KL | 690 | 28 | 7 | 2025-12-31 | MYR / MYR, same label unverified |

Each combined output repeats exactly at the cutoff. These annual snapshots do
not establish latest interim disclosures, original releases or full requested
historical coverage. The exploratory database gains three financial records/
artifacts/batches, not 84 canonical facts. New ignored bytes/SQLite need encrypted
co-retention before recovery/portability claims. No commit/push was performed.
After capture, SQLite contains 7 evidence/artifact/batch rows and zero canonical
fundamental facts/daily bars, reports or signals. Fixed-cutoff read repetition
leaves its hash unchanged:
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.

## Remaining Work

Authoritative issuer/accounting mappings, actual release/revisions/interim
history, consolidation/units, independent sources and separate sector definitions
still need acceptance. Report ages are diagnostic with freshness UNASSESSED.
No financial strength conclusion, score, confidence model, FX or valuation is
activated. PIT UNSUITABLE; production NOT_READY; execution/notifications disabled.
No Paper, broker, Portfolio, Notification or live-execution changes.
Verification: 2239 passed / 6 skipped, 110.47 seconds, 49 added regressions.
Ruff, mypy (268 files), governance (122 checks), new-path forbidden-import check
and git diff --check pass. Existing global-price regressions and real original
price hashes remain intact. Default-disabled provider/notification network tests
remain skipped; manual real Yahoo captures are separate evidence, not their pass.
