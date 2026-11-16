# Financial Snapshot UTC Integrity: October 27, 2026

## Scope

WP-LAUNCH-001 remains ready, not accepted. This slice repairs a reproduced
financial-input timing defect before technical-plus-fundamental validation.
Framework stays 0.8.0, schema 0.8.2 and migration head unchanged. PIT stays
UNSUITABLE, production NOT_READY, financial scoring unqualified, execution and
notifications disabled. No new provider, canonical dataset, scoring policy or
trading functionality is introduced. No commit or push was made.

## Reproduced Defects

Use the repeated New York local time 2026-11-01 01:30:

- `fold=0` is 05:30 UTC; `fold=1` is 06:30 UTC. Python comparisons using the same
  ZoneInfo instance can compare repeated wall-clock labels rather than distinct
  instants. FinancialInputSnapshot accepted a fact available one hour after its
  cutoff; publication/instrument metadata had the same gap.
- FundamentalFact publication/availability chronology could accept actual reversed
  times, or reject valid forward chronology when the wall clock moved backward.
- Snapshot context binding could alias different folded cutoffs, while rejecting
  the equivalent actual instant written in UTC. Hash/document calls did not
  revalidate mutated visibility.
- Bank/nonfinancial latest selection compared unnormalized availability before
  revision. An older higher-revision favorable value could beat a later rejected
  value; equal-instant duplicate records could also lose their ambiguity across
  timezone spellings.
- Period/filing date bounds used the caller's timezone date, so changing timezone
  labels could change admission at midnight.

The new initial 25-case suite produced 23 failures and two existing downstream
rejections before repairs, using synthetic records only. This is evidence of
software defects, not proof of a real-provider financial restatement or a real
historical investment loss.

## Changes

`domain.models.FundamentalFact` compares availability and publication in UTC.
Original source timestamps remain unchanged. Its other contracts are preserved.

`data.financial_inputs.FinancialInputSnapshot`:

- Revalidates fact/instrument contracts, actual UTC publication/availability/
  metadata visibility and chronology.
- Uses a pinned UTC date for conservative report/filing period bounds. This is
  not an exchange-session calendar or issuer-local fiscal/publication-time policy.
- Revalidates before input hashing/document creation and context binding.
- Binds subject/market and actual UTC cutoff independently of timezone spelling;
  full canonical fact-content comparison remains required.

`research.financial.inputs` and `research.financial.nonfinancial` order versions
by report period, actual UTC availability, then revision. Later rejected or
unsupported inputs cannot fall back. Equal-instant duplicate rows remain ambiguous
and cannot inflate evidence or pick favorable values. Bank report-age diagnostics
retain their separately defined Shanghai-date convention.

Central runtime versions advance:

| Contract | New version |
| --- | --- |
| Financial snapshot | financial-source-inputs-v8-utc |
| Financial assessment | financial-v0.5.12-snapshot-utc |
| Bank input diagnostics | bank-financial-inputs-v2-utc |
| Nonfinancial diagnostics | nonfinancial-cash-balance-diagnostics-v2-utc |

Do not rewrite historical receipts/reports. Existing issuer-filing source packet
versions v1-v7 and their hashes/annotations are unchanged; the new snapshot
version is a runtime read contract, not an issuer filing revision or schema
migration. Historical Financial reports remain original records, not promoted by
reading them with newer code. No new ResearchReport or repository contract exists.

## Verification

Final full pytest: **2081 passed, 6 skipped** in **76.34 seconds**, 31 added
cases against the 2050-test checkpoint. Focused financial/research/integration
suite: 440 passed in 3.27 seconds. Ruff passes; mypy passes for 259 files;
governance passes 116 checks; `git diff --check` passes. Live AKShare, CNInfo,
Tushare and three notification tests remain opt-in and skipped. This slice did
not call provider networks or represent those skipped tests as passing.

New regressions cover future/reversed/forward folded instants, naive mutation,
different/equivalent cutoff identity, hash/document revalidation, direct consumers,
date-label invariance, latest rejection despite older higher revisions, and
same-instant ambiguity. A persisted-research integration case attaches a later
snapshot cutoff to an earlier context and requires rejection before any run,
assessment, report, evidence or Signal write. The existing queue remains visible.
Existing trailing/valuation regressions now test rejection at construction and
again after deliberate mutation, because the shared snapshot blocks earlier.

## Actual Retained Data Check

Two read-only ReviewedFinancialInputReader reconstructions of 002624 at
`2026-10-26T15:24:39Z` used the exploratory database
`data/processed/technical-request-20261020.sqlite3` and artifact root
`data/processed/raw/provider-artifacts`, sector `nonfinancial`, with metrics:

```text
revenue, profit_attributable_to_parent, operating_cash_flow, total_assets,
total_liabilities, current_liabilities, monetary_funds, operating_cash_inflow,
operating_cash_outflow, roe_weighted_ytd_unannualized,
equity_attributable_to_parent, roic
```

Both reads agree: 17 stored observations reconstruct as SOURCE_BOUND, with ROIC
still missing. SOURCE_BOUND describes retained review/byte/batch consistency,
not issuer truth, independent annotation verification or scoring approval.
LOW/retrieval-time evidence is not upgraded. Descriptive ratios remain 40.3136%
liabilities/assets, 93.6261% monetary funds/current liabilities and 23.5295% net
operating cash flow/revenue; the exact cash residual is 0.00 CNY. These are neither
debt clearance nor a financial quality or investment conclusion.

- New exact-query financial snapshot hash:
  `fd699d5b0bd4c71ebc30fcd8d1d0a609b0572815bb9473be2f222ccfa865bf68`.
- Ordered consumed fact-content hash:
  `f0003f0aca793b2e9399df42c3ed8e7d31b75fab250963a2d2f67198aeb7bf3d`.
- SQLite file SHA256 unchanged before/after reads:
  `0800a746c6f6f6354a42deebb2bf62929204a664189adaeb22fc648128ac952b`.
- Database still contains 17 facts, 4094 evidence records, 21 artifacts and
  23 batches; zero real ResearchReports or Signals. No write/migration occurred.

## Boundaries And Next Work

This repair is temporal admission, not absolute source accuracy. Other storage,
screening/regime/domain/read-side temporal paths require independent audit.
Conservative UTC period bounds need separately reviewed local fiscal/session
semantics for broader operational use. Provider coverage, original publication
and revision provenance, dated issuer/share-class/action continuity, independent
source/sector financial policy and actual combined hypothesis validation remain
open. New local data/review plans still require approved encrypted co-retention.
No source/PIT/scoring/Paper/live gate is promoted; no favorable report or score is
invented from a structurally consistent sample. Continue those admitted work
items without treating the provider observation horizon as a software freeze.
