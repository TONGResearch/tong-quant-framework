# Market-Value Research Binding: October 24

WP-LAUNCH-001 remains `ready`, not accepted. Local date is Asia/Kuala_Lumpur;
the pinned read below is October 23 in UTC. This slice changes research input
integrity and diagnostics only, not source qualification or trading authority.

## Reproduced Defect And Repair

The previous matching result used a quote receipt and close/date comparisons but
did not bind the actual supplied daily-bar content. Two synthetic bar sets with
different opens, identical closes and identical dates produced the same diagnostic
hash. Equal match booleans therefore concealed a changed consumed price input.

The v2 diagnostic binds a canonical sorted inventory of all original supplied bar
rows, including OHLCV, identity, source, adjustment, timestamps and availability,
as `bar_input_hash`. It also binds the explicit matching policy. Bar reordering
and equivalent timezone representations retain deterministic identity; material
bar or policy changes do not. Shared daily-bar validation still rejects adjusted,
ambiguous, wrong-subject and future observations even when no quote is available.
Latest suspension cannot resurrect an older favorable active close.

## Explicit Freshness

`MarketValueMatchingPolicy` separates quote age, capture age and bar age, measured
in integer microseconds against actual UTC instants. Limits are explicit positive
integer seconds; booleans, fractions, strings, zero and negatives are invalid.
Unconfigured limits are `UNASSESSED`, never infinite freshness or approval.
Aggregate precedence is FUTURE, STALE, UNAVAILABLE, UNASSESSED, then
WITHIN_CONFIGURED_LIMIT. Always read individual statuses and source status too:
a recent HTTP failure is not a fresh numeric quote.

Limits are explicit module/CLI parameters, not an admitted default valuation
policy. A wall-clock limit is not a verified exchange-session calendar. Weekend,
holiday, market-close and instrument-specific policy calibration remain open.
Even exact date/price/arithmetic matches within a configured age limit cannot
authorize valuation, financial scoring, validation, replay or execution.

## Official Research Contract

The existing `ResearchContext` accepts an optional `MarketValueInputSnapshot`.
Its receipt must match the exact candidate symbol/market and actual UTC cutoff;
payload mutation must fail before a persisted run starts. Current inputs are
equity-only; fund/ETF extensions remain reserved, not implemented.

`FinancialResearchModule` consumes the source-neutral receipt, not a provider
SDK. Existing `ResearchAssessment.features` stores receipt/bar/policy/diagnostic
hashes, evidence id, per-component states and `market_value_matching_json` with
reasons, trust, availability, exact ages and effective policy. The existing
ResearchReport and SQLite repository persist it; no parallel report type or
schema migration is introduced. Source-bound means retained consistency, not
authenticated truth. Arbitrary hand-constructed receipts are not independent
verification; use the source-verifying reader at real application boundaries.

Financial score stays null, confidence stays zero, report and InvestmentAssessment
stay incomplete, and no InvestmentScore is issued. Real candidates are not
invented or admitted into a queue to make this example pass. Synthetic integration
fixtures alone exercise the complete ingestion/reader/report/database chain.

Versions: financial-v0.5.10-market-value-binding,
market-value-matching-diagnostics-v2-bound-bars,
market-value-matching-policy-v1. Framework 0.8.0, schema 0.8.2 and existing capture/
input v1 contracts remain unchanged; historical rows and hashes are not rewritten.

## Real Read-Only Check

Database: `data/processed/technical-request-20261020.sqlite3`.
Artifact root: `data/processed/raw/provider-artifacts`.
Subject: China-A equity 002624; cutoff: `2026-10-23T16:03:52+00:00`.
Requested metrics: revenue, profit_attributable_to_parent, total_assets,
equity_attributable_to_parent, operating_cash_flow,
roe_weighted_ytd_unannualized, roic. Trailing review:
`config/trailing-reviews/002624-2026h1.toml`.

Two identical combined reads with explicit 86400-second limits produced the
same result; the default unconfigured policy produced a different diagnostic
identity. These 24-hour limits are illustrative diagnostics, not calibrated
research admission. All reads return exit 2 by design for incomplete diagnostics.

- Observed daily rows: 674; latest timestamp: `2026-10-19T07:00:00+00:00`.
- Bar age: 378232000000 microseconds; `STALE` under the example limit.
- Latest retained quote status: `unavailable`, reason `HTTP_502`.
- Capture age: 1649151678 microseconds; within example limit, but quote absent.
- Quote freshness: `UNAVAILABLE`; aggregate freshness: `STALE`, not approval.
- No numeric market value, matched valuation or official real report is created.
- No ingestion/new capture or database/schema write occurs in this slice.

Identities:

```text
input_review_hash       cf3e78f4ea10b236f08a24d23075bf936c595bd4623edf687fe58911a7b75503
diagnostic_hash         5a4332e18f1938ed0ac927af7e186e3e63eebb10f3faccf36632becffd26b9d0
bar_input_hash          6fb2b0a8e407ec9cf86ef518a3a545ce4c797b02ed5fb7d3b887b54f86ba7ec8
policy_hash             2603e40f96707d11bb8a86fa38b791d51fe60bec674f7ec8805455b8b017ebad
default_diagnostic_hash a4c44931ae7438d0063717022b15dc131c7c3f82914e2345c72944a603d685e9
artifact_audit_hash     a5812a28885b03ed1ccd072465684a82cc44d757cb5bd809ff8c7dc55f0c5425
```

Registered artifact bytes verify 17/17, unchanged from the retained failure
capture. A separate bounded public HTTP recheck returned 502 and was not added
as a new archived capture. The local moomoo UI read timed out; no quote was
extracted and no trading/account operation was performed. Neither result proves
an API schema change; source versus gateway cause remains unresolved.

## Remaining Boundaries And Next Work

Obtain a functioning permitted dated quote source, then independently review
native units, quote timing, share classes, FX/corporate actions and financial
edition comparability before source/sector valuation admission. Financial/technical
synthesis and actual strategy validation remain separate unfinished work. Do not
label outage, sample arithmetic or regression success as an investment conclusion.

PIT remains UNSUITABLE, production NOT_READY, execution and notifications disabled.
No broker, Paper, Portfolio, allocation or trading code changes. No commit/push.
Raw evidence/configs still need encrypted co-retention; 17/17 byte consistency
does not prove backup, independent source accuracy or historical availability.

## Verification

Full suite: **1761 passed, 6 skipped in 63.28 seconds**, 32 added cases against
the prior 1729-test checkpoint. Ruff passes, mypy passes for 251 source files,
governance passes 107 checks, and `git diff --check` passes. Six opt-in real
provider/notification network tests stay disabled. Regressions cover changed bar
inputs, age thresholds, invalid limits, UTC/order identity, suspension, missing
quotes, receipt context/mutation, fund exclusion, report persistence and
incomplete/unscored investment assessment. The initial new fund fixture used
an invalid enum member; it was corrected to the existing ETF asset type without
expanding implementation scope. Final full suite includes the corrected case.

Passing synthetic/offline checks is not proof of live source access, source
authentication, historical data qualification or investment performance.
