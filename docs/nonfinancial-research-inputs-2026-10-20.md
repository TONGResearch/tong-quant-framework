# Real Nonfinancial Research Inputs: October 20

## Result And Repairs

WP-RESEARCH-004 advances Tong's technical-plus-fundamental research path. The
real 002624 example now has eight retained financial facts (four current and
four same-filing comparatives) alongside 674 existing daily observations.
This is input integration, not financial scoring, a passed hard screen, a
completed ResearchReport, strategy validation, a buy/sell decision or trading.

- Previously only CNY-million was accepted. Explicit CNY/yuan, CNY-thousand and
  CNY-million now convert to absolute CNY using exact Decimal arithmetic.
  Native-provider units are never inferred from magnitude or familiar names.
- operating_cash_flow/cash_flow is a distinct nonfinancial calendar-YTD net
  operating cash-flow contract, not parent-only cash flow, FCF, profit,
  standalone-quarter data or a generic bank cash-flow score.
- Source-bound same-filing comparisons normalize supported units and support
  cash flow. Group/subject/sector/YTD windows and unverified original-revision
  status still bind them. Nonpositive baselines withhold percentage change.
- inspect_candidate_inputs.py joins checked financial receipts and technical
  bars in one read snapshot at one explicit cutoff. Missing metrics and
  technical conflicts remain visible; screening is NOT_ASSESSED. It invents
  no queue, hard-screen success, report, validation or financial score.

Extended extraction packets use REVIEWED_MONETARY_FACTS_VERSION (v4). Existing
v1 monetary, v2 comparative and v3 bank-ratio packet documents/versions remain
unchanged. Financial-input and comparison diagnostic versions advance; old
snapshots are not silently rewritten or requalified. No schema migration.

## Real Evidence

Source: [Perfect World 2026 half-year report](https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF).
This is a consolidated, unaudited filing. One-based PDF pages differ from printed
numbers by one. Page 41 establishes unaudited/CNY/consolidated scope. Pages 7,
41-42, 45-46 and 48-49 were inspected; summary amounts agree with consolidated
statements. Parent-only profit and cash flow differ and cannot be substituted.

- Capture batch: 52c25af1-cd3a-4195-9cd2-8a9bcecef59c.
- Filing artifact: 39798ad9fe058ac4c36bab4edbe2672bb212986ea76360b5bb6f9ccb8e21dfbf.
- PDF SHA256: 284af037c8a319c67a13ce6ecf0b17fceb29e0c96e902c06b4107b9e605c7691.
- Capture: 2026-10-20T11:06:31.079821Z; manual review: 11:12:08Z, no second reviewer.
- Current facts batch: 8245a90f-3aa3-4208-99b2-116073ae8210 (four facts).
- Prior-YTD batch: 913ef33e-d992-4d64-9be2-29685308bcc7 (three facts).
- Prior-year-end batch: e58553a3-969f-42ec-bd52-a1125d82f23b (one fact).

Three config/filing-extractions/002624-*.toml plans pin pages, columns, units and
bytes. Publication uses neutral evidence/canonical transactions. Visibility is
no earlier than capture/review, LOW/RETRIEVAL_TIME, never backdated to August.
Comparatives are as presented in this later filing, not original 2025 PIT facts.

| Metric, absolute CNY | Current 2026H1/end | Comparative | Descriptive change |
|---|---:|---:|---:|
| Revenue | 2,751,024,838.40 | 3,690,992,631.88 | -25.4665% YTD YoY |
| Profit attributable to parent | -118,437,769.22 | 503,205,318.94 | -123.5367% YTD YoY |
| Net operating cash flow | 647,301,141.75 | 502,214,625.90 | +28.8893% YTD YoY |
| Total assets | 10,542,798,063.76 | 10,468,434,793.94 | +0.7104% since year-end |

Asset changes are not stock returns. Positive operating cash flow cannot erase
losses or prove recurring cash quality. No single metric determines a decision.

## Combined Read And Reproduction

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent operating_cash_flow total_assets roe roic \
  --as-of 2026-10-20T11:14:00+00:00
```

Exit 2 intentionally denotes partial diagnostics. Two runs produced identical
documents/hashes. The official ResearchReport remains the sole report model.
Eight observations are source-bound LOW, while requested ROE/ROIC inputs are
absent. Bars end October 19, not an intraday quote. Trend structure BEARISH,
momentum CONFLICTED, aggregate technical CONFLICTED; bearish startup ARMED.
Granville downside deviation is mean-reversion evidence, not proof of a bottom.
Bearish references are not long-position stops; seven-plus-one stays deferred.

Input-review hash:
10c7bb3ad3854f16dbb99d1e5eda58240623a3d6ab431fa1e5e5d3260b4e1c2b.
Financial-input hash:
7bf547d4925afc9cb508771ca7c50d771bdbd774f04150e0456e59ae46ef722f.

Artifact audit verified 9/9 registered files: four price frames, two new PDFs
and three review packets. Report hash:
5b8a118ac7b9274bbbd2c221ebfadc7086a4ee8d841fde1ca7922deb07865ce7.
Bytes are in the ignored research artifact store, outside earlier encrypted
backups. Git plans do not transport that evidence to another device. Hashes
verify retained consistency, not provider truth, complete backup or PIT quality.

## Gaps And Next Priority

| Gap | Actual state | Required next work |
|---|---|---|
| ROE | Filing discloses it; nonfinancial ratio contract not implemented | Define weighted/annualized basis and period; no generic aliases |
| ROIC | Not established by this extraction | Review capital/profit definitions; never substitute ROE |
| Debt/cash quality | Full statements exist; selected metrics are insufficient | Exact liability/debt/cash definitions and cash-flow drivers |
| Valuation | No admitted dated share-count/valuation context | Price/cap/share evidence and method for loss-making issuers |
| Industry/news/sentiment | Not populated by this example | Source-bound calculations, not caller-supplied favorable scores |
| Screening/Queue | Not assessed by this CLI | Real Discovery/Hard Screening before the official research workflow |
| Financial scoring | No admitted source-bound sector policy | Reviewed rubric, confidence and falsifiable conditions |
| Brokerage profile | 600109 needs securities-company semantics; not implemented here | Do not label it bank/nonfinancial just to reuse this example |
| Validation | Not run/passed | OOS/ablation, costs, actions, gaps, T+1 and failed exits |
| 920982 bars | Known connection and fallback missing-day failures | Verified BSE source/export; do not block other issuers or invent bars |

The six-metric requested subset is not a complete checklist. Same cutoff does
not establish matched freshness. Reviewed observations are not independent
annotation verification or provider calibration. PIT stays UNSUITABLE,
production NOT_READY; execution/notifications disabled, live orders false.
No trading module, schema, commit or push change.

## Verification

Tests cover exact units/precision, zero/negative cash flow, nonfinancial YTD,
no income/FCF alias, same-filing normalized comparisons, legacy packet versions,
PIT visibility, read-only deterministic combined CLI and missing inputs.
The official Financial module still withholds scoring even with cash-flow
receipts. Full suite: **1368 passed / 6 skipped**, 50.04 seconds, including 33
new regression cases. Ruff, mypy (241 source/script files), governance (97
checks) and git diff --check pass. Focused research/source tests pass 341 cases.
The initial full run caught the intentionally temporary ready-package inventory;
after the completed package/status handoff was updated, the final full run
passed. No test failures are waived. No remote CI or independent validation.
