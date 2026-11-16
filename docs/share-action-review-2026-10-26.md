# Manual Share-Action Document Review: October 26, 2026

## Scope And Outcome

WP-LAUNCH-001 remains ready, not accepted. This slice closes a read-side gap:
the continuity inventory could list titles/PDF captures but could not consume a
specific manual body review. It now accepts explicit versioned document-review
plans. It does not populate a canonical corporate-action ledger or authorize
financial scoring, validation, Paper or live trading. PIT remains UNSUITABLE,
production NOT_READY, execution and notifications disabled.

No data capture, database/schema migration, provider SDK change, Portfolio,
Notification, Paper, broker or execution change occurred. This slice makes no
claim that all accumulated dirty checkout changes originated here. No commit or
push was made.

## Contracts And Dependencies

`data.share_action_reviews` owns immutable manual document observations:

- Explicit issuer-capital, holder/plan or undetermined scope.
- Explicit transfer, disposal, plan termination, cancellation, issuance,
  split/bonus or undetermined kind, with compatible scope checks.
- Proposed, pending, reported-completed or undetermined stage. Reported-completed
  is a manual description of the filing, not independently verified implementation.
- Page/reference labels and optional positive integer whole-share quantities.
  Quantities retain their declared scope, never an inferred signed issuer delta.
- An exact effective date only for reported-completed observations, no later than
  claimed document publication. Missing dates remain null/NOT_REPORTED; publication,
  confirmation receipt and review dates cannot silently substitute for execution.
- Actual aware review time, reviewer, exact artifact/hash and centralized model
  version. Unknown fields, unsupported units, fractional/boolean quantities,
  incompatible scopes, duplicate references and credential-like assignments fail.

`data.reviewed_filing_source` shares the existing share-count reader's retained
CNInfo checks: exact bytes/hash/size/path, registry identity, approved official URL,
issuer/market/dataset, first capture and completed batch ownership/UTC chronology.
Binding successful old share-count reviews preserves their receipt shape/hash.
The helper does not independently authenticate issuer content or page annotations.

`data.share_continuity_inputs` inventory v2 consumes supplied action reviews in
the same read snapshot. Only bound captured metadata with the exact announcement,
PDF hash/URL and publication instant gains MANUALLY_REVIEWED_UNQUALIFIED. Metadata-
only/changed-PDF versions remain NOT_REVIEWED. Duplicate artifact review plans fail
rather than choose a favorable interpretation. Unmatched reviews remain visible.
Observation dates are labelled AT_OR_BEFORE_BASE, WITHIN_INTERVAL, AFTER_THROUGH or
UNKNOWN_DATE; these are diagnostic interval labels, never share-ledger entries.

```text
retained CNInfo bytes + registry + completed batch + explicit manual plan
  -> shared reviewed_filing_source binder
  -> share_action_reviews inspection (LOW/retrieval-time; UNKNOWN preserved)
  -> share_continuity_inputs v2 + base share-count review + UTC cutoff
  -> existing combined candidate input diagnostic
```

This is not a new Provider, database write path, ResearchReport, queue, score or
trading signal. Every issuer_share_delta/current_shares/market_value stays null;
all canonical-publication/admission/readiness flags stay false. No quantity is
aggregated and no zero issuer delta is inferred from absence of cancellation.

## Actual Retained Document

Manual text and visual review covered both pages of 002624 announcement
`1225547650`, the 2023 employee-plan completion/termination disclosure:

- Official retained source:
  `https://static.cninfo.com.cn/finalpage/2026-09-05/1225547650.PDF`.
- PDF SHA256:
  `d93419f4c3d7108b43c691e6ab9961dbe732bd28cfc63cd414c07b5c6fa22719`.
- Artifact ID:
  `52b1876663bdf88ca53c689cb942b098cd62edf9f66d823c4a89aedbf48a2b3f`.
- Claimed publication: `2026-09-04T16:00:00Z` (September 5 Shanghai date).
  The body is dated September 4; these dates are not exact final-sale timestamps.
- Actual capture: `2026-10-26T14:10:23.888107Z`.
  Batch `a25c4706-255d-4bd2-9471-e0846cbe2a57` completed
  `2026-10-26T14:10:23.899331Z`.
- Manual review availability: `2026-10-26T15:24:39Z`.
  Independent second review is pending.
- Explicit plan:
  `config/share-capital-reviews/002624-2023-employee-plan-termination.toml`.

| Observation | Whole shares | Reported exact date | Relation to June 30 base |
| --- | ---: | --- | --- |
| Repurchase-account shares transferred into plan | 14,650,000 | 2024-06-21 | At/before base |
| Plan shares transferred into personal accounts | 7,325,000 | 2026-06-24 | At/before base |
| Remaining plan shares reportedly sold | 7,325,000 | Not reported | Unknown |
| Plan liquidation/distribution and termination | Not a share quantity | Not reported | Unknown |

June 25 is receipt of confirmation, not the June 24 transfer date. The plan's
reported percentages are rounded and cannot be inverted into exact total shares.
Holder transfers/disposal and plan termination do not establish issuer cancellation,
nor independently prove zero issuer change. This late review cannot enter an older
historical decision. Other documents, earlier notices/corrections, share-class
semantics and complete effective-date continuity remain unverified.

## Real Read-Only Reproduction

Run from the PyCharm project using the retained exploratory database/artifact root:

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent operating_cash_flow \
    equity_attributable_to_parent roe_weighted_ytd_unannualized roic \
  --as-of 2026-10-26T15:24:39+00:00 \
  --trailing-review-plan config/trailing-reviews/002624-2026h1.toml \
  --share-capital-review-plan config/share-capital-reviews/002624-2026h1.toml \
  --share-continuity-through 2026-10-26 \
  --share-action-review-plan \
    config/share-capital-reviews/002624-2023-employee-plan-termination.toml
```

Exit 2 remains intentional for unqualified input diagnostics. Two executions at
this cutoff agree: 25 metadata versions, 21 unique bound announcements, one
manually reviewed announcement and no unmatched supplied review. Only the exact
captured-PDF version gains that label; 20 unique documents remain unreviewed for
the action inventory. Counts do not measure trusted historical coverage. Technical
confluence is CONFLICTED, sector financial policy NOT_ADMITTED, ROIC still missing.
Default quote/capture/bar freshness limits are UNASSESSED. No report/score is invented.

Reproducibility receipts for this exact query/config/source snapshot:

- Manual review hash:
  `156f43318d620abc4f8c8c39edd8b0469d25a1661f764dc94820a7d286dfa790`.
- Manual inspection hash:
  `7ed46577118c4010717c1932a3399c09bb7f87ec66a6b056514288e0e8cd67eb`.
- Continuity inventory hash:
  `bf54ca45170216462e6512da574bf58e475cf0ea55172151a177e0bb8289d826`.
- Combined input hash:
  `dce1d6c979df26e36f9f8835cfb4b05e619b7904ef7c9814174d14cbf6b70c7e`.
- SQLite file SHA256, unchanged before/after reads:
  `0800a746c6f6f6354a42deebb2bf62929204a664189adaeb22fc648128ac952b`.

At cutoff `2026-10-26T14:16:26Z`, explicit use of this later review fails closed.
The older share-count-only receipt at `2026-10-26T13:52:42Z` still equals
`121509133f55c29d091ac6520ab2f7d0627cf8007aea21ce4879bcaa29d2fbd5`.
Inventory v2 changes receipt semantics intentionally; do not rewrite old v1 reports.

## Verification And Remaining Work

Full pytest: **2050 passed, 6 skipped** in **91.50 seconds**, 46 added cases
against the prior 2004-test checkpoint. Ruff passes; mypy passes for 259 files;
governance passes 115 checks; `git diff --check` passes. Live AKShare, CNInfo,
Tushare and three notification network tests remain deliberately skipped.
Focused share/count/continuity/action-review suite: 103 passed in 9.71 seconds.
Regressions include scope/unit/stage/date validation, exact PDF/registry/batch
rejection, actual UTC/folded cutoff checks, unknown trust preservation, changed
PDF/metadata-only noninheritance, unmatched/duplicate reviews, interval boundaries,
read-only determinism and opt-in combined CLI integration. Real source inspection
is separate from these synthetic tests; no network test is represented as passing.

Tests use synthetic fixtures, not real provider access or issuer authentication.
Actual retained-PDF inspection is a separate limited manual exercise. Database
totals remain 4094 evidence records, 21 artifacts, 23 batches, 3374 versioned daily
rows and 17 fundamental facts, with zero real reports/signals. Stored consistency
is not independent accuracy, full backup or readiness approval. New ignored source
bytes/database plus Git-managed plans need approved encrypted co-retention.

Next priorities: independent dated issuer/share-class/action review (including
pre-window notices and corrections), a reviewed source-bound sector financial
policy, then real technical-plus-fundamental hypothesis validation. Keep missing
data and conflicting technical evidence visible rather than manufacturing a buy/
sell conclusion or prolonging provider observation as a development prerequisite.
