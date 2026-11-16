# Valuation Basis And Parent Equity

Date: 2026-10-23. Scope: WP-LAUNCH-001 input/research diagnostics only.
Framework 0.8.0, schema 0.8.2 and migration head remain unchanged.
PIT UNSUITABLE, production NOT_READY; execution and notifications disabled.

## Problem And Boundary

The retained 002624 data includes 2026 H1 cumulative revenue/profit, not annual
or TTM earnings. A partial-period loss does not prove annual/TTM losses, and
multiplication by two is not an admissible TTM calculation. Parent-equity book
value must not be replaced by total assets, minority-inclusive equity or the CNY
share-capital line. No dated source-bound equity market-value contract exists
yet; this is an explicit implementation gap, not a provider permission/network
failure. This slice checks denominators, not fair value or investment selection.

## Architecture

Existing retained CNInfo PDF -> reviewed filing v7 -> provider-neutral atomic
ingestion -> FundamentalFact/evidence/artifact -> ReviewedFinancialInputReader
-> FinancialInputSnapshot -> valuation_basis_diagnostics -> existing Financial
ResearchReport features / combined read-only inspection CLI.

- New metric: `equity_attributable_to_parent`, signed absolute CNY, current group
  nonfinancial quarter-end balance with no period start. No alias/proxy permitted.
- A separate additive review version preserves old v1-v6 packet identities.
  Read-side input/Financial versions advance; valuation basis v1 is centralized.
- Three diagnostics inspect annual parent earnings, parent book and annual revenue.
  States: NOT_REQUESTED, MISSING, INCOMPATIBLE, PARTIAL_YEAR, NONPOSITIVE, OBSERVED.
  OBSERVED means unqualified reported denominator, not an admissible valuation.
- Latest period/UTC availability/revision wins; ties or rejected/unsupported latest
  rows do not select favorable older data. Current column, statement, currency,
  scope, filing period and January-start flow semantics must match. A recent
  interim period does not silently fall back to an older annual period.
- Preserve period, signed reported value, evidence reference, trust, precision,
  cutoff, snapshot hash and deterministic diagnostic hash. UTC comparisons reject
  future availability, including same-zone DST folds.
- No annualization, TTM synthesis, PE/PB/PS, market value, tangible-book adjustment,
  target price or score is produced. All downstream authorization flags are false.
  Official Financial reports/InvestmentAssessment remain INCOMPLETE and unscored.

## Real Retained Evidence

Manual visual review of the unaudited 002624 2026 H1 group balance: one-based PDF
page 43, with group/CNY header on page 41. No independent second review.
Source URL: https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF

- PDF SHA-256: `284af037c8a319c67a13ce6ecf0b17fceb29e0c96e902c06b4107b9e605c7691`.
- Parent owners equity: CNY 6,511,874,265.88 at June 30, not total equity
  CNY 6,292,619,553.38 or total assets CNY 10,542,798,063.76.
- Review plan: `config/filing-extractions/002624-2026h1-parent-equity.toml`.
  Available no earlier than manual review at 2026-10-23T14:16:03Z; never backdated
  to the disclosure date. Source remains LOW / RETRIEVAL_TIME.
- New review packet SHA-256:
  `67bf3ff02bab5d3150ab191451b35b7ede78b73ce345c96cd9ef256738150cb0`.
- Duplicate writes leave one parent-equity fact with first batch
  `4392538f-b707-4c48-b787-a9a28a011f2e`; the October 22 cutoff cannot see it.
- Existing v5/v6 real packet hashes were re-previewed unchanged. Existing golden
  v1-v4 packet identities remain regression-covered. Source packets are not
  equivalent to new read-side diagnostic hashes.
- Two existing-database reads at 2026-10-23T14:20:15Z produce the same review hash
  `370f5899c9d60f86aa18b127c7355e823984e140e45f313fe6ba0290aa7085c5`.
  They include 674 prior daily observations ending October 19, not current quotes.
  Interim revenue CNY 2,751,024,838.40 and parent loss CNY -118,437,769.22 remain
  PARTIAL_YEAR. Parent book is OBSERVED/unqualified. ROIC stays missing.
- Registry audit: 13/13 verified, report hash
  `7478e563dc90f0d456f9b061bc5f29d9688959eaf0fd2d7c88431de4d516b937`.
  Byte identity is not issuer truth, independent review or PIT qualification.

## Database And Operations

No new table, column or migration. Existing atomic fact/evidence/artifact/batch
publication and first-provenance idempotency are reused. SQLite, raw PDFs/review
bytes and caches remain ignored; no broker, execution, Portfolio or Notification
implementation changes. The new review bytes are outside earlier encrypted
backup snapshots. Do not claim backup coverage or copy a live SQLite database.
No commit or push is part of this slice.

## Verification

- Full Pytest: 1630 passed, 6 skipped, 55.05 seconds; 42 new regression cases.
  Real AKShare/CNInfo/Tushare and notification network tests remain opt-in.
- Ruff passes; mypy passes across 245 files; `git diff --check` passes.
- Governance passes 104 checks, including disabled defaults and unchanged schema.
- Unit/integration coverage includes signed/zero book, exact amount scaling,
  annual versus Q1/H1/Q3 earnings, partial losses, no total-assets proxy, missing
  versus not-requested, incompatible/ambiguous latest rows, no favorable fallback,
  source/sector binding, cutoff/DST rejection, deterministic read-only CLI and
  incomplete official ResearchReport/InvestmentAssessment without a score.
- The real retained sample now has 15 financial observations. Its one new fact
  retains first provenance after repeated ingestion. Previous-day exclusion,
  pinned-cutoff read agreement and 13/13 registered bytes were checked separately.
  These are engineering/evidence checks, not historical or strategy validation.

## Remaining Work

1. Independently qualify dated equity market value with source, currency, share
   class/capital changes, PIT availability, precision and trust. Do not infer
   shares from CNY share capital or multiply a stale quote by guessed shares.
2. Obtain actual annual inputs or a separately specified, source-edition-aware
   TTM reconstruction. Preserve restatements and missing periods. Historical
   presentation in a later filing is not original historical availability.
3. Admit sector-aware valuation/financial policies and freshness only after
   review; retain technical conflicts, hard-screen gaps and counter theses.
4. Validate technical-plus-fundamental conditions using appropriate historical/
   OOS, corporate-action, lifecycle, cost and liquidity evidence. A diagnostic
   cannot authorize investment scoring, Paper acceptance or live trading.
