# Nonfinancial Research Input Checklist: October 27, 2026

## Delivered Scope

WP-LAUNCH-001 remains ready, not accepted. Bank diagnostics already had explicit
input definitions and target/age checks; ordinary-company research had arithmetic
diagnostics but no equivalent selected input checklist. Seventeen observations
could be misread as complete current research despite including comparatives,
different periods and unsupported definitions. This slice makes those gaps
machine-readable in the existing Financial path; it does not admit scoring.

PIT remains UNSUITABLE, production NOT_READY, execution/notifications disabled.
Framework/schema/migration head remain 0.8.0 / 0.8.2 /
0010_portfolio_evidence_lineage. No provider/network capture, database/schema,
Paper, broker, Portfolio, Notification or execution change. No commit or push.
Pre-existing dirty checkout changes are preserved, not attributed to this slice.

## Definitions And Semantics

`research.financial.nonfinancial_inputs` adds NonfinancialInputPolicy and
assess_nonfinancial_inputs. The policy covers China-A group nonfinancial input
diagnostics only, not sector classification, a complete company checklist or
bank/broker/insurer applicability. It consumes the existing revalidated
FinancialInputSnapshot, not raw SDK rows or caller numerical scores.

| Selected dimension | Metrics | Required basis |
| --- | --- | --- |
| Growth inputs | revenue, profit_attributable_to_parent | Group current calendar-YTD income, absolute CNY |
| Profitability input | roe_weighted_ytd_unannualized | Group current calendar-YTD weighted ratio, percent/null currency, not annualized |
| Survival inputs | total_assets, total_liabilities, current_liabilities, monetary_funds | Group current period-end balances, absolute CNY |
| Cash-quality inputs | operating_cash_flow, operating_cash_inflow, operating_cash_outflow | Group current calendar-YTD cash flow, absolute CNY |
| Valuation-basis input | equity_attributable_to_parent | Group current period-end parent equity, absolute CNY |

Dimension names describe research inputs, not positive company conclusions.
ROIC/invested-capital and interest-bearing-debt source definitions remain
DEFINITION_NOT_IMPLEMENTED with explicit requested flags. Do not replace these
with ROE, total liabilities, cash ratios or a generic amount with a familiar name.
Signed profit/cash-flow observations are not converted into data failures or
silently erased; financial interpretation still requires a reviewed rubric.
Cycle evidence, recurring earnings/cash drivers, disclosures, industry/news,
financial revisions and dated valuation/action continuity remain separate work.

The checklist preserves these distinct states:

- not_requested, missing;
- rejected, unsupported, ambiguous latest input;
- semantic_mismatch, period_mismatch;
- observed_unqualified, never scoring-approved.

Latest selection uses report period, actual UTC availability, then revision.
Rejected/unsupported latest versions cannot select older favorable observations;
same-instant ties remain ambiguous. No metrics are combined into a financial score.
Each observation hash binds complete inspection content and the assessment binds
the snapshot, exact cutoff, target semantics and policy/definitions.

Default target is the latest visible required metric period, not proof of the
latest issuer filing. An explicit visible calendar-quarter target is supported;
old periods cannot satisfy it. Shanghai report-period age and UTC observation-
availability age remain separate. Availability is not raw source capture time
or accounting freshness. Age limit zero means UNASSESSED; a within-limit
observation remains unqualified. No default age threshold is invented.

## Existing Workflow Integration

The existing `research.financial.maximum_report_age_days` setting now supplies
both bank and nonfinancial policies through research_engine_from_settings.
No configuration key changes. FinancialResearchModule appends the exact checklist
JSON, assessment hash and policy hash to its existing assessment features.
SQLite continues using research_assessments.features_json; no table or schema
migration, second ResearchReport, queue, repository or score model is added.

The combined read-only CLI includes nonfinancial_input_assessment at its common
cutoff. Optional --financial-target-period pins the accounting quarter; unsupported
market/sector combinations fail before the read. Original financial/technical/
share/market-value diagnostics remain present. Exit 2 remains intentional.

Central versions:

- NONFINANCIAL_INPUT_POLICY_VERSION: nonfinancial-inputs-v1.
- FINANCIAL_RESEARCH_VERSION: financial-v0.5.13-nonfinancial-checklist.

Source packets, snapshots and old persisted report identities are not rewritten.
All source/scoring/validation/replay/execution grants stay closed. Official report
integration tests retain INCOMPLETE / DATA_BLOCKED with no InvestmentScore, even
when a checklist observation is present and structurally source-bound.

## Actual Read-Only Sample

Two combined CLI reads of retained 002624 data at the fixed historical inspection
cutoff `2026-10-26T15:24:39Z` agree. This is not a fresh quote or current-time
investment analysis. Query all eleven selected metrics plus ROIC:

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent operating_cash_flow total_assets \
    total_liabilities current_liabilities monetary_funds operating_cash_inflow \
    operating_cash_outflow roe_weighted_ytd_unannualized \
    equity_attributable_to_parent roic \
  --as-of 2026-10-26T15:24:39+00:00
```

The retained 17 observations support eleven selected current June 30 inputs,
all observed_unqualified, with period age 118 days. Default freshness remains
unassessed. Source qualification is NOT_ESTABLISHED and financial scoring policy
NOT_ADMITTED. ROIC is requested but its definition is not implemented; the
interest-bearing-debt definition remains unimplemented even when not requested.
Technical confluence remains CONFLICTED; no report, queue success or score is
invented. Eleven structural observations do not establish full research coverage.

Adding `--financial-target-period 2026-09-30` produces eleven period_mismatch
checks. This describes the stored query, not proof that an issuer failed to
publish a Q3 filing. Fetching/reviewing the appropriate filing is separate work.

Receipts for the default exact query above:

- Financial snapshot hash (unchanged by adding the checklist):
  fd699d5b0bd4c71ebc30fcd8d1d0a609b0572815bb9473be2f222ccfa865bf68.
- Policy hash:
  57348a0c5e2a1869863db1a59bbd324f85829585d113d3e6cad9757a3006078c.
- Checklist assessment hash:
  d503c8a56d8274ba0757a762ad5e7ac611244e7d212db7277c43fba5397717d9.
- Combined input hash:
  26bb87b3fa77ec7391415229f41646e3dc1da898d39e92705454c0489d0d8808.
- Explicit September 30 target assessment hash:
  11c913176a39c865420d7b0fc223d708c35960129553511f1a14b78dfe17d17f.
- Exploratory SQLite main-file SHA256, unchanged before/after reads:
  0800a746c6f6f6354a42deebb2bf62929204a664189adaeb22fc648128ac952b.

No database population or new source accuracy claim follows these checks.
Retained source-byte/batch consistency is not independent annotation verification,
provider consistency, original historical publication or encrypted backup.

## Verification And Next Work

Full pytest: **2107 passed, 6 skipped** in **189.16 seconds**, 26 added cases
against the 2081-test checkpoint. Focused changed-policy/research/CLI tests:
225 passed in 18.22 seconds. Ruff passes; mypy passes for 260 source/script
files; governance passes 117 checks; `git diff --check` passes. Live AKShare,
CNInfo, Tushare and three notification tests remain opt-in and skipped, not
reported as successful network checks. No provider call was made this slice.

Tests cover missing/not-requested/undefined distinctions, period and freshness
boundaries, exact UTC version order/ties, latest rejection without fallback,
semantic mismatch, unsupported sectors/markets, deterministic binding, shared
configuration, read-only CLI and SQLite official-report persistence with no
scoring/condition bypass. Live provider and notification tests remain opt-in.

Next: independently review source/sector scoring rubric and required definitions,
complete dated share/action evidence, then run actual registered technical-plus-
fundamental hypothesis validation. Do not let a successful checklist substitute
for those gates. New local data/review plans still need encrypted co-retention;
no live capability is enabled and provider observation is not a software freeze.
