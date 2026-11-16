# Dated Issuer Share-Count Review: October 26

## Scope And Architecture

WP-LAUNCH-001 adds `data.share_capital_inputs.ShareCapitalReview` and a read-only
source-bound inspection. It is an explicit manual annotation of an already
captured CNInfo filing, not a new provider, parallel ingestion path, canonical
FundamentalFact, completed ResearchReport or valuation policy. The existing
ProviderEvidenceAdapter/neutral ingestion architecture and all tables remain
unchanged. No provider SDK or live network is used in this slice.

The combined input CLI accepts optional `--share-capital-review-plan`. It checks
subject/market before use, reads the source registry in the same database
snapshot, verifies the retained PDF hash/size/path/official URL/artifact identity,
and checks completed source-batch ownership and UTC chronology. Review time must
follow capture and source batch completion and must not exceed the requested
cutoff. Omitting the plan is NOT_REQUESTED, not missing data; explicitly supplying
a future/broken/wrong-subject review fails closed rather than hiding the problem.

The receipt binds the complete immutable review, source hash/identity/times,
original batch receipt, actual cutoff and centralized
`issuer-share-count-review-v1` version. LOW/RETRIEVAL_TIME remains the ceiling;
an UNKNOWN source remains UNKNOWN. Stored consistency is not independent issuer,
manual annotation, publication-time or numerical verification. The manual review
plan is Git-managed but **not published as a SQLite evidence record**; no canonical
population or replay-ready historical share timeline is claimed.

## Separate Units And Meanings

- Only explicit whole-share integer counts are admitted to this review contract.
  CNY, percent, thousand-share units, strings, booleans and fractional counts are
  rejected rather than converted or inferred.
- Scope is issuer-total-as-reported, period-end after-change quantities, not
  consolidated-group monetary balances, current outstanding shares, EPS weighted
  averages, treasury-adjusted shares or independently qualified share classes.
- Restricted and unrestricted shares remain separate. Unrestricted is not an
  index free-float measure, a liquidity qualification or a market value.
- Missing components remain incomplete; a nonzero total-minus-components residual
  remains a visible conflict. Exact agreement does not prove issuer accuracy.
- Source-page/unit/column annotations are manual, not automatic PDF semantic
  validation. Selecting the wrong PDF table could still produce an unqualified
  review; independent second review remains required.
- No price multiplication, PE/PB/PS, current-share carry-forward, source promotion,
  scoring, replay, validation, readiness or execution authority is introduced.

## Real Retained 002624 Review

Source: [2026 half-year filing](https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF),
retained PDF hash
`284af037c8a319c67a13ce6ecf0b17fceb29e0c96e902c06b4107b9e605c7691`.
PDF page 36 (printed page 35) was text-inspected and visually rendered; its share
changes table explicitly labels quantities in shares. The after-change column
reports total 1,939,968,404, restricted 112,235,363 and unrestricted 1,827,733,041.
The components sum exactly. This review labels them as the June 30 report-period
end, not an independently established current outstanding-share count.

PDF page 104 (printed page 103), also text/visually checked, labels its book
share-capital note in CNY and shows 2,011,661,461.00. It is deliberately excluded
from the share-count review. Different units cannot be treated as a direct
numerical share-count conflict or solved by guessing par value/treasury treatment.

Source artifact: `39798ad9fe058ac4c36bab4edbe2672bb212986ea76360b5bb6f9ccb8e21dfbf`.
Actual PDF capture: `2026-10-20T11:06:31.079821+00:00`.
Source batch: `52c25af1-cd3a-4195-9cd2-8a9bcecef59c`.
Manual review availability: `2026-10-26T13:46:05+00:00`. Do not backdate the
annotation to the claimed August disclosure or the June report date.

The new `config/share-capital-reviews/002624-2026h1.toml` plan is opt-in.
Reproduce its joint diagnosis using the existing combined CLI, with database
`data/processed/technical-request-20261020.sqlite3`, artifact root
`data/processed/raw/provider-artifacts`, symbol 002624, nonfinancial profile,
cutoff `2026-10-26T13:52:42+00:00`, existing H1 trailing-review plan, requested
revenue/parent-profit/assets/parent-equity/operating-cash/weighted-YTD-ROE/ROIC,
and illustrative 86400-second quote/capture/bar age limits.

Two reads agree: share-count age 118 days, EXACT_AGREEMENT but
UNQUALIFIED_CONTINUITY. Market value is null and all admission flags stay false.
The 678 daily observations still end October 23, technical families remain
CONFLICTED, requested ROIC is missing, Financial policy is NOT_ADMITTED, and no
real ResearchReport or InvestmentScore is invented.

- Review hash:
  `90f5cbc37a7aa715910a6edf12517a59657bfe611afba834a9a1b11ccd630d0e`.
- Share inspection hash:
  `121509133f55c29d091ac6520ab2f7d0627cf8007aea21ce4879bcaa29d2fbd5`.
- Combined input review hash:
  `73d8b229bdb625b8c605fdfc56758ab29efad2cd02116f707c59d0dcd0f2c03a`.
- Real database SHA-256 before/after both reads:
  `a62ab19f429c57d967c1203fbc5edcd8fd8e3531e3eadb4e5aaabfc435232e25`.

No database write/migration or new source capture occurs. Existing totals stay
4071 evidence records, 19 artifacts, 21 batches, 3374 versioned daily rows and
17 facts, with zero real reports/signals. Review/config/source co-retention and
independent-device recovery remain separate requirements.

## Remaining Work

Verification: full pytest **1984 passed / 6 skipped**, 82.26 seconds, adding 37
regressions since the 1947-test checkpoint. The focused share-review suite passes
37 cases: unit/type/scope rejection, missing/conflicting components, source-byte/
registry/batch tampering, future/backdated/DST-fold chronology, UNKNOWN trust,
UTC/hash determinism, strict plans, wrong subjects and read-only opt-in CLI.
Ruff passes, mypy checks 256 files, governance has 113 passing checks and
`git diff --check` passes. Six opt-in live checks remain disabled; no new real
provider-network validation or independently verified annotation is claimed.

Obtain independently reviewed share-class definitions and dated share/action
continuity across issuance, cancellation, buyback and other changes before
matching a later quote. Independent unit/price/sector-policy qualification,
financial admission and real hypothesis/OOS/cost validation remain open. Do not
substitute a fresh current snapshot for historical continuity or a source name
for evidence. PIT remains UNSUITABLE, production NOT_READY, execution and
notifications disabled. Paper/Broker/Portfolio/Notification code stays untouched;
there is no commit or push in this slice.
