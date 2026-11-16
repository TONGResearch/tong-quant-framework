# Nonfinancial Cash And Balance Inputs

October 22, 2026. Bounded research-input follow-up under `WP-LAUNCH-001`, which
remains ready/incomplete. This is neither a financial scoring policy nor a trade.

## Implementation

The existing reviewed-filing adapter now supports five explicit current group
observations: total liabilities, current liabilities, monetary funds, operating
cash inflow and operating cash outflow. These nonnegative amounts require a
nonfinancial profile and current calendar-quarter-end scope. Cash components
require January-start YTD periods. Existing signed net operating cash flow is
unchanged. New generic debt/cash aliases, blank-as-zero and current/comparative
substitution are not supported. Explicit CNY/thousand/million units normalize
through the existing Decimal conversion; no units are inferred from magnitudes.

`research.financial.nonfinancial` consumes exact typed receipts and outputs:

| Diagnostic | Meaning and limits |
|---|---|
| liabilities_to_assets_percent | Total liabilities / total assets; not an interest-bearing-debt ratio. |
| monetary_funds_to_current_liabilities_percent | Gross monetary funds / current liabilities; not unrestricted cash, a cash-equivalent ratio or debt-service clearance. |
| operating_cash_flow_to_revenue_percent | Group YTD net operating cash / revenue; not profit margin, FCF or parent-profit conversion. |
| operating_cash_reconciliation_residual | Inflow - outflow - reported net operating cash; exact CNY residual, never rounded into agreement. |

Only same-period/current-column, same-file artifact/hash and audit-label inputs
can combine. Rejected/unsupported/ambiguous latest rows cannot select older
favorable data. Missing/not-requested inputs stay explicit. Zero/nonpositive
denominators withhold ratios. Component conflicts or incompatibility withhold
the dependent cash ratio; missing components leave any separately calculable
net/revenue ratio explicitly descriptive with an unavailable-check warning.
All required inputs are inspected before classifying a gap: one missing input
cannot hide a different rejected/incompatible component. Such combined cases
remain incompatible and withhold the dependent ratio.

Each output binds input hash, period, evidence IDs, trust/availability labels,
formula, status and diagnostic hash. Neither LOW nor UNKNOWN trust is upgraded.
The existing FinancialResearchModule adds these diagnostics to its existing
ResearchAssessment/ResearchReport features; it remains unscored. A synthetic
official-report test retains a nonzero residual, incomplete status and no
InvestmentScore. The combined CLI reuses the same calculator, not a parallel
report model. No source-dependent logic moves into execution or shared strategy.

Versions: `reviewed-nonfinancial-cash-balance-v6`,
`financial-source-inputs-v6-cash-balance`,
`nonfinancial-cash-balance-diagnostics-v1`,
`financial-v0.5.7-nonfinancial-cash-balance`. Prior v1-v5 source packets are not
rewritten. Pre-change v1-v4 golden hashes remain tested; the real v5 ROE packet
still reconstructs to `69318b0ffd0a9da688367baaea38b6eeac170b25feb8fa6f2552e14b40418c86`.
New receipt/assessment identities distinguish current behavior rather than
retrospectively qualifying stored historical reports.

## Retained Source And Real Result

Source: [Perfect World 2026 half-year report](https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF).
One-based PDF pages 41, 43, 48 and 49 were rendered and visually inspected,
with text extraction as a secondary check. These span the unaudited group
balance/cash statements and adjacent parent-only sections, which were not used
as substitutes. The same source PDF was already retained on October 20; no new
network source capture or second-provider confirmation is claimed.

| Current period amount, CNY | Source value | One-based PDF page |
|---|---:|---:|
| Total liabilities | 4,250,178,510.38 | 43 |
| Current liabilities | 3,763,463,695.25 | 43 |
| Monetary funds | 3,523,584,061.89 | 41 |
| Operating cash inflow, 2026H1 | 3,249,205,144.14 | 48 |
| Operating cash outflow, 2026H1 | 2,601,904,002.39 | 49 |

PDF SHA256: `284af037c8a319c67a13ce6ecf0b17fceb29e0c96e902c06b4107b9e605c7691`.
Source artifact: `39798ad9fe058ac4c36bab4edbe2672bb212986ea76360b5bb6f9ccb8e21dfbf`.
Plan: `config/filing-extractions/002624-2026h1-cash-balance.toml`.
Manual review: `2026-10-22T15:12:43+00:00`, no independent second reviewer.
First facts batch: `38589233-ef03-44bf-8e00-dcd16aea7a32`.
Review packet SHA256: `15b5ffe771923be34f502b2a25277b520d50d521957b3907a98d0f0f412d9cfb`.
Review artifact: `3349f5a7fdb315db89ad7105fc666f50820f368359fb913661b95bf4c744b7dc`.

Five added facts remain LOW/RETRIEVAL_TIME, visible no earlier than actual review;
the reader also checks completed batch chronology. Repeated ingestion retains
exactly five facts and their first-batch provenance, with a separate audit batch.
The October 22 11:14:48Z cutoff cannot see the new observations. Claimed August
publication does not establish original numeric availability or revision history.

At pinned cutoff `2026-10-22T15:16:45+00:00`, the combined input reader reconstructs
14 financial observations with 674 prior daily rows (ending October 19). Results:

- Total liabilities/assets: 40.3136%.
- Gross monetary funds/current liabilities: 93.6261%.
- Net operating cash flow/revenue: 23.5295%.
- Cash reconciliation residual: 0.00 CNY, arithmetic agreement only.

All four are descriptive and retain LOW/retrieval-time labels. ROIC remains
missing from the explicitly requested subset. Full interest-bearing debt,
restricted-cash details, recurring cash drivers and valuation remain unassessed.
Blank short/long-term borrowing lines were not converted into zero debt. The
cash-flow table's cash-equivalent ending amount is not substituted for monetary
funds. Positive cash flow cannot override reported losses or technical conflict.
Technical confluence/momentum stay CONFLICTED and trend structure BEARISH, not
buy/sell instructions. Financial scoring is NOT_ADMITTED; screening NOT_ASSESSED.

## Reproduction And Integrity

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent operating_cash_flow total_assets \
    roe_weighted_ytd_unannualized total_liabilities current_liabilities monetary_funds \
    operating_cash_inflow operating_cash_outflow roic \
  --as-of 2026-10-22T15:16:45+00:00
```

Exit 2 is intentionally partial diagnostics, not a provider failure. Two reads
give identical JSON/hashes without changing database bytes. Input-review hash:
`e9df6977c65cbd9c8f74447709914eee475973213f103e0ceba5cd9645f3bf45`.
Financial-input hash:
`b472e467f9fea6104817b68d4355bae2a38d92800a26074f9928f2c50935332b`.
Registry verifies 12/12 files; artifact audit report hash:
`e63b296834c9d0ae4e6c52fc12a8c2f010a36875fa3452adc0fffc764bbe7d53`.
This verifies retained bytes, not independent annotation truth, full database
integrity, encryption, backup recovery or cross-provider consistency. New bytes
are ignored by Git and remain outside earlier encrypted backups.

## Boundaries And Next Work

No migration/schema rewrite: five facts and their review/evidence/audit records
use existing tables. Framework/schema stay 0.8.0/0.8.2, PIT UNSUITABLE, production
NOT_READY and execution/notifications disabled. No Paper, Broker, Order,
Execution, Portfolio, Notification or asset-allocation changes. No commit/push.

Prioritize named borrowing/lease/restricted-cash definitions, cash-flow drivers,
dated share/valuation inputs and appropriate loss-making-issuer methods, then
source/sector scoring admission and actual screened research/strategy validation.
Ratios are research inputs, not a full checklist or a claim of absolute accuracy.

## Verification

Full pytest: **1560 passed / 6 skipped**, 64.00 seconds, 54 added regression cases.
Ruff passes; mypy reports no issues in 243 source/script files; governance passes
102 checks; `git diff --check` passes. A final focused diagnostic run passes
27 cases, including mixed missing/rejected input priority. The initial 1558-case
full run preceded those final two regressions and is not the completion result.
Skipped tests are not claimed as verified live-provider coverage. No remote CI,
independent financial review or strategy validation was performed. Cases cover
exact units/zero/signed cash flow, scope/period/source mismatches, nonzero
residuals, missing components, no favorable fallback, trust labels, historical
cutoffs, source tampering, old packet identities, incomplete official-report/
InvestmentAssessment propagation and deterministic read-only combined diagnostics.
