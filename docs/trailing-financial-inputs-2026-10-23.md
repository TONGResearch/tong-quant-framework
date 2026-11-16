# Annual Inputs And Reviewed Trailing Arithmetic

Date: 2026-10-23. Work package: WP-LAUNCH-001, ready, not accepted.
Framework 0.8.0, schema 0.8.2, migration head 0010_portfolio_evidence_lineage.
PIT UNSUITABLE; production NOT_READY; execution/notifications disabled.

## Outcome And Boundary

The retained interim sample previously lacked the preceding full-year revenue
and parent profit. Two genuine annual observations are now populated through
the existing reviewed-filing provider-neutral transaction. A separate diagnostic
connects annual and interim amounts without pretending that H1 times two is TTM.

This is **as-reported research arithmetic**, not independently qualified TTM,
an earnings-quality opinion, financial scoring, valuation or a buy/sell decision.
Neither publication-date claims nor current retrieval establish historical truth.

## Contract

`research.financial.trailing` consumes FinancialInputSnapshot only. It supports
China-A nonfinancial group operating revenue and parent-attributable net income,
explicit normalized CNY/calendar-YTD income statements at quarter ends.

- Full-year latest observation: return reported annual amount, no synthetic bridge.
- Interim latest observation: previous full year + current YTD - prior-year YTD.
  The prior YTD must be from the exact current filing, including hash, period,
  column and presentation/revision labels. Never guess quarters or annualize.
- A TrailingEditionReview binds all three full receipt hashes, reviewer,
  limitations, version and timezone-aware review time. Hashes include source,
  period, value, scope, units, revision, evidence/artifact identities and timestamps.
  A changed annotation/value/version needs a new review; matching amounts alone
  cannot reuse an earlier grant. Reviews are after input availability and no later
  than the actual UTC cutoff. They remain manual descriptive permissions only.
- Defaults contain no reviews. Explicit typed FinancialResearchModule injection
  and optional `--trailing-review-plan` on the combined CLI are supported. Factory
  configuration does not auto-admit a review or arbitrary issuer. Review plans
  reject unknown fields, malformed bindings and credential-labelled structures.
- Latest rejected/unsupported/tied inputs are incompatible; never select favorable
  older data. Missing components and missing edition reviews stay distinct and
  visible. A rejected known component cannot hide behind another missing component.
- Preserve signed/zero amounts, covered period, effective availability, input and
  review hashes, evidence references, original trust/precision and warnings. Use
  exact bounded Decimal arithmetic independent of ambient precision. No valuation
  multiple, target price, score, portfolio/notification or trading output exists.
- All original interim valuation-basis diagnostics remain PARTIAL_YEAR; a separate
  derived amount does not rewrite original evidence. Financial reports and
  InvestmentAssessment remain incomplete/unscored even with a numeric result.

## Real Evidence And Reproduction

Official directory query for 002624, 2026-04-28, annual-report category returned
the full report and its summary without truncation. Both PDFs were retained by
the existing direct CNInfo adapter; only the full report supplies numeric facts.

- [2025 annual report](https://static.cninfo.com.cn/finalpage/2026-04-28/1225207318.PDF):
  SHA-256 `8243d61d2a8b7524c544305d7d6add4513724d0c278f6d2eae5d2c6f6ff8b9c6`,
  artifact `990ef7edde280bcf3f5e85e2294d03e2e6c44fb178bb787d42cef4b4b1ed5f31`,
  captured 2026-10-23T14:37:02.928275Z. Manual visual review: PDF pages 7, 80, 81.
  Group 2025 revenue CNY 6,659,558,521.64; parent net profit CNY 730,859,018.92.
  Audited is the filing's audit label, not independent verification of our extraction.
- `config/filing-extractions/002624-2025fy.toml` uses existing v4 amount semantics.
  Review available 2026-10-23T14:41:30Z; original source packets are not rewritten.
  New packet hash `cecfbbf7411afd732191f44f3659e6afbaf8b046fda2125e5bee0972f2eb00c0`.
  Duplicate writes leave two new facts, first batch
  `109a96b2-aa9d-4d86-aab6-574d2a79d7f8`; total retained issuer facts: 17.
- Existing [2026 H1 report](https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF)
  page 7 shows current and prior cumulative amounts. The explicit bridge in
  `config/trailing-reviews/002624-2026h1.toml` is reviewed at 2026-10-23T14:45:14Z.
  Annual audited/interim unaudited editions and unverified original revisions,
  accounting/consolidation comparability remain explicit limitations.
- As-reported bridge for 2025-07-01 through 2026-06-30: parent profit
  CNY 109,215,930.76; revenue CNY 5,719,590,728.16. Both remain LOW/RETRIEVAL_TIME,
  DERIVED_AS_REPORTED_UNQUALIFIED, not qualified valuation inputs. A negative H1
  profit does not by itself establish a negative annual or trailing profit.
- Two read-only combined calls at 2026-10-23T14:47:26Z agree, review hash
  `1763411a8c5b3f32e089e258659d69faffad2bfd42583f194792a8879bcf2b0f`.
  Earlier 14:20:15Z cutoff cannot see the new annual facts, so it emits MISSING
  and no trailing value even when the later review plan is supplied. Without a
  plan the later three-input sample emits EDITION_REVIEW_REQUIRED, not a number.
  Existing 674 daily observations end October 19, not a current quote. Technical
  confluence stays CONFLICTED, ROIC missing and financial policy NOT_ADMITTED.

Pinned read-only reproduction (exit 2 is intentional diagnostic incompleteness):

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent total_assets \
    equity_attributable_to_parent operating_cash_flow roe_weighted_ytd_unannualized roic \
  --as-of 2026-10-23T14:47:26+00:00 \
  --trailing-review-plan config/trailing-reviews/002624-2026h1.toml
```

Registry audit: 16/16 verified, report hash
`cd67e45f8813d6611b78fda54debf5d0f6c3ab5f7401ab2c5befe2bba1dfd98e`.
This is byte verification, not independent source truth or backup verification.
New ignored PDFs/review bytes are outside earlier encrypted backups. Retain
review configs with code and recover database plus artifacts together.

## Database And Versions

No schema change, new table or migration. Existing atomic writes and first-capture
provenance remain intact; review plans are explicit versioned configuration, not
facts or source-trust grants. TRAILING_FINANCIAL_VERSION v1 and Financial Research
v0.5.9 are centralized. Existing review v1-v7 packets/input receipt version remain
unchanged. No Tushare, Portfolio, Notification, broker or execution implementation
change. No commit/push or readiness promotion.

## Next Acceptance Work

Final verification: full Pytest **1677 passed, 6 skipped**, 59.90 seconds,
47 new regression cases; focused trailing/filing/research suite 503 passed.
Ruff passes, mypy passes across 246 files, governance passes 105 checks and
`git diff --check` passes. Six network tests remain opt-in. Temporary SQLite
integration verifies deterministic CLI output without database writes, explicit
review requirement and no report/InvestmentScore authorization. Separate real
capture, idempotency, prior-cutoff and byte-audit checks are documented above.

1. Dated equity market value with exact shares/class/currency/unit/source/action
   semantics and visible availability; do not infer shares from CNY share capital.
2. Separate source/accounting/freshness and sector valuation admission. Descriptive
   trailing arithmetic cannot be fed to PE/PS as an independently approved input.
3. Real hard screens, counter thesis and technical-plus-fundamental OOS/robustness/
   cost/lifecycle validation. No numeric result may override those gates.
