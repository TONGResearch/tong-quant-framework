# Original Bank Percentage Evidence

## Delivered Slice

WP-LAUNCH-001 adds an independent HK/MY original-percentage contract and retained
read/write path. It does not widen the existing monetary V1 contract, China CNY /
YTD financial model, Financial score or draft bank policy. Original PDF source
pins are required directly; a ratio review never needs dummy monetary rows.

`GlobalRatioRow` preserves native label, Group/Bank/parent annotation, instant /
reported-annual / unknown period basis, explicit dates, current/comparative column,
original percent unit, exact quoted Decimal, unresolved cell status, page/column,
restatement annotation and definition/denominator/regulatory-scope notes. Unknown
notes cannot be empty. Ratios are printed percent values, not fractions: 1.23 is
1.23%, never 0.0123. Negative values and coverage above 100% are permitted; finite
number/size bounds protect storage, not an economic screening threshold. Missing,
unreadable and conflicting cells retain null, never zero. No monetary/FX scaling.

`GlobalRatioReview` -> `GlobalRatioReviewAdapter` -> existing provider-neutral
ingestion/artifacts/SQLite -> `read_global_ratio_review_inputs` at an explicit UTC
cutoff. Provider `global_document_ratio_review`, dataset
`global_document_percentage_review`, version `global-document-ratio-review-v1`.
No new database tables or migration; framework/schema remain 0.8.0 / 0.8.2.

The exact reader verifies raw envelope, reconstructed record/artifact, ingestion
ownership/completion and the current original PDF parent. Latest failures, ties,
tampering, future completion and changed parent cannot select an older favorable
review. Actual review recording is availability, never backdated publication.
Retries retain one evidence identity but append separate ingestion attempt IDs.
Hashes prove retained consistency, not an authenticated author or correct values.

Existing `scripts/review_global_document.py` adds `--kind ratio`; default remains
monetary. Preview does not write; explicit `--write` uses the actual clock and
forbids `--as-of`. Exit 2 is intentional unqualified status, not a failed check.
Every authority flag stays false, trust LOW, precision RETRIEVAL_TIME, freshness
UNASSESSED. Page locations/definitions are single-review annotations, not machine
PDF verification or independent accounting qualification.

## Real Source And Reproduction

Plan: `config/global-document-reviews/maybank-2025-ratios.toml`.
Original Maybank annual-report PDF physical page 5 / printed page 3 was visually
reviewed against the retained PDF SHA
`2fc421fac71b9f5a9c3063709662a265b9c1fe3c7e29ea842ff2c78eaf041c55`.
Five Group 2025 values are transcribed exactly as displayed:

| Original label | Printed % | Period annotation |
| --- | ---: | --- |
| CET1 Capital Ratio | 16.041 | Instant, 2025-12-31 |
| Total Capital Ratio | 19.960 | Instant, 2025-12-31 |
| Net impaired loans (%) | 0.79 | Instant, 2025-12-31 |
| Loan loss coverage (%) | 106.7 | Instant, 2025-12-31 |
| Return on equity | 11.7 | Reported annual, 2025-01-01 to 2025-12-31 |

These are annotations in one financial-summary column. They do not establish
regulatory consolidation, denominator, regulatory basis, averaging method or
cross-provider correspondence. Net impaired loans is NOT gross NPL; loan loss
coverage is NOT an automatically admitted NPL-coverage metric; annual reported
ROE is NOT China weighted YTD ROE. No LCR row was located on this selected page;
no value is invented and no issuer-wide absence is claimed. Existing Bank revenue
summary/statement discrepancy is untouched and unresolved.

Review annotation time: `2026-10-29T13:53:23+00:00`.
Actual recording: `2026-10-29T13:55:40.261275+00:00`.
Evidence ID: `491b05e2939d218daa8da852097745712e90bfe9a120fcb7017d49ceb9a33912`.
Envelope SHA: `f5c08390cbde84fcf997f70a8309083b685b381e3a8ebffdf6ea666f7ac91017`.
Artifact ID: `2e3d5909525cbaaa855b44c3ea55fb5c3be99e40a234aeaa10ab5b0728c899d0`.
Batch ID: `8876acc7-b1c2-4dbd-a7c5-7765c7ec8541`.

Two exact reads at `2026-10-29T13:55:41+00:00` repeat input hash
`1e3cbb84101a292ab9a788a00960dd8dad7719bcbffe3e5cda9bb19e94aa35c1` without
database writes. The old monetary receipt at `2026-10-29T12:11:01+00:00` retains
its 22 rows and exact hash
`4aa54309f31a06aa37bc0de31868fdd26f1b5feec8efda2a2767219c2344ea2c`.
No monetary edition, draft bank plan or historical receipt was rewritten.

Document database now has seven evidence records/artifacts/completed batches,
zero canonical fundamental facts, ResearchReports or signals, and no foreign-key
violations. Its new SHA is
`69d54a7bc32b99b560bc75edbbaec9219e24ba2046c7e4fe127c106e338684e7`;
previous `7e421d69bac246dbcf23476e14b9c3c554f8bde3c9d9703af62a00a037913831` is
historical. Price/native database stays
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
Ignored raw evidence still needs approved encrypted co-retention; neither Git nor
this read test constitutes a backup/restore or independent source calibration.

## Boundaries And Next Work

This delivers an evidence contract, not bank metric qualification. Ratio receipts
are deliberately not accepted by the monetary `ReviewedDocumentResearchInput`;
no implicit conversion, Financial feature binding or checklist credit occurs.
The current draft bank plan still has five ratio requirements and four external
dependencies: a stored percentage alone cannot resolve their meaning or admit a
policy. Not all financial sectors, countries, latest periods or instruments are
covered by this Maybank sample or the existing HKEX/Maybank URL allowlist.

Next bounded slice: explicit source-defined ratio questions and immutable original
ratio receipts in the existing research path, preserving unsupported definitions,
missing LCR and annual/instant scope. Then separately review attributable equity,
freshness, sector/source admission and real screened candidate validation. Do not
give numeric thresholds, weights, buy/sell conclusions or a separate report model
to unqualified source annotations. Do not force unknown bank ratios into China
models or count raw evidence as a closed validation gate.

## Verification

Full suite: **2844 passed / 6 skipped** in 181.47 seconds; 57 new ratio cases.
Ruff passes, mypy passes on 294 source files, all 138 governance checks and
`git diff --check` pass. Scoped runtime imports have no execution, broker, order,
trade, fill, paper, portfolio or notification dependencies. The original review
plan passes credential-structure checks. SQLite/raw-artifact paths remain ignored.
Six real-network opt-in tests stay skipped; this offline reproduction is not
independent source corroboration or proof of current provider availability.

Tests cover percent units/negative/above-100 values, finite/bounded decimals,
null status, scope/period/column distinctions, strict plan/secret rejection,
actual UTC availability and deterministic hashes, wrong source pins, future/tied/
tampered/bad-owner/latest captures, changed original parents, idempotent evidence
with separate attempt audit IDs, preview no-write/backdate rejection, and rejection
by the existing monetary research wrapper. No monetary migration is introduced.

No new external network/provider capture, canonical facts, real queue/report, migration, Portfolio,
Notification, Paper, Broker, Order, Execution or allocation logic. No commit/push.
PIT UNSUITABLE, production NOT_READY, disabled defaults, R1-R6 partial and launch
ready/not accepted remain unchanged.
