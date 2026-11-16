# Native Financial Changes And Sector Research Questions

Date: October 27, 2026, Malaysia time. WP-LAUNCH-001 remains ready, not accepted.

## Scope

`research.financial.native_review` consumes the existing retained native-financial
reader receipt and adds exploratory amount changes plus sector-specific research
questions to `inspect_global_technical.py --fundamentals --sector-profile ...`.
Version: `global-native-financial-review-v1-exploratory`. It is not a new
ResearchReport, ResearchAssessment, admission policy, financial score or strategy.
The official Research/InvestmentAssessment/Validation contracts are unchanged.

## Receipt And Calculation Boundaries

The pure review checks the full receipt checksum, model version, subject/market,
actual UTC cutoff, unique latest capture, row availability and false admission
flags. The CLI obtains this receipt through byte/registry/completed-batch
reconstruction, not user annotations. A public checksum is not independent
authentication; forged/recomputed checksums can never authorize scoring, source
qualification, replay, validation or execution. Direct calls are exploratory only.

Changes use the two most recent distinct source period labels for each selected
native metric, not tuple order or a favorable older value. Both must be unique,
usable, same-currency/provider-raw-unit, labelled 12M and one calendar year apart
with matching month/day. Unknown periods, duplicates, latest/previous rejected
rows, currency/unit changes, missing/irregular years and future periods withhold
changes rather than fill the gap. Matching labels do not prove exact flow periods
or comparable accounting. Fiscal year-end is not assumed to be December 31.

Decimal arithmetic shows signed native amount changes. A percentage is withheld
for zero/negative prior values; no annualization, TTM, FX, valuation multiple,
ROE/ROIC or score is calculated. Amounts remain provider-reported raw units.
These are unqualified native amount comparisons, not verified revenue/earnings
growth, investment returns or predictions. The original China same-filing
comparison contract is not relaxed or reused under false global/CNY semantics.

## Sector Questions, Not A Trading Rubric

Each profile exposes Survival/Cycle/Valuation/Growth prerequisites with status
UNASSESSED and sector_policy_status NOT_ADMITTED. These are research questions,
not accepted thresholds, regulatory definitions, hard screens or scoring weights.

| Caller profile | Examples of questions still requiring source/sector review |
| --- | --- |
| Nonfinancial | Cash restrictions, debt maturity/definitions, recurring earnings, industry demand, dated shares/actions, comparable growth and invested capital |
| Bank | Asset quality, capital/liquidity, funding, credit cycle, bank earnings/impairment and equity definitions |
| Securities | Capital/liquidity, balance-sheet/market risk, revenue mix and risk-adjusted expansion |
| Insurance | Insurance capital/liability risks, underwriting, investment/insurance earnings split and accounting comparability |
| Unknown | Verify issuer business and sector first; do not infer a policy from a ticker |

Negative native operating cash flow or net income in a nonfinancial profile adds
a business-context review prompt only. It never rejects the issuer or generates
a sell signal. Financial profiles do not inherit ordinary-company cash-flow
interpretation; all signed raw values remain visible without a generic bank
failure flag. Caller profile is not verified sector classification.

All reviews retain financial_condition_state EVIDENCE_INSUFFICIENT and false
financial/investment scoring, validation, replay and execution authority. Positive
technical alignment or positive native changes cannot compensate for missing
accounting, source, publication/revision, interim, industry or validation evidence.
Market Regime is not turned into a switch. No orders or actual official reports
are created; no financial policy or draft weights are activated.

## Real Read-Only Exercise

Used the previously retained US/HK/MY snapshots, not new provider/network captures,
at `2026-10-27T04:20:54+00:00`. Each combined output repeats exactly.

| Integration sample | Native revenue comparison labels | Native amount change % | Interpretation |
| --- | --- | --- | --- |
| MSFT | 2025-06-30 to 2026-06-30 | 17.7887 | Unqualified USD field change, not verified business growth |
| 0700.HK | 2024-12-31 to 2025-12-31 | 13.8596 | Unqualified CNY field change; HKD quote remains separate |
| 1155.KL | 2024-12-31 to 2025-12-31 | -0.6363 | Unqualified MYR field change, not a bank-strength conclusion |

All three remain EVIDENCE_INSUFFICIENT / NOT_ADMITTED. Price and financial input
receipt hashes are not rewritten. SQLite bytes remain unchanged at
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
No schema, provider, data capture, canonical fact, Paper/Broker/Portfolio/
Notification/execution, commit or push change. Ignored source bytes still require
the earlier encrypted co-retention work; this read does not provide a backup.

## Remaining Acceptance

Actual issuer/sector accounting and period definitions, authoritative source
review, original releases/revisions/interims, price/share/action/currency bases,
official screened candidate/research chain and strategy validation remain open.
The new questions/changes expose that work; they do not complete it. PIT stays
UNSUITABLE, production NOT_READY and execution/notifications disabled.
Verification: 2275 passed / 6 skipped, 83.28 seconds, 36 added regressions.
Ruff, mypy (269 files), governance (123 checks), new-path forbidden-import check
and git diff --check pass. Tests cover all three markets, receipt/hash/context/
UTC rejection, latest/previous invalid or ambiguous rows, fiscal/currency/unit
changes, nonpositive baselines, sector-specific negative-cash-flow boundaries
and deterministic CLI output. Default-disabled real provider/notification tests
remain skipped; no source or strategy is qualified by software success.
