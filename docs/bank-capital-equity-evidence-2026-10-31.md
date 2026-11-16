# Bank Capital, Asset Quality And Attributable Equity Evidence

## Completed Interrupted Slice

WP-LAUNCH-001: completed the October 30 source editions and October 31 validation /
handoff. The interrupted writes were already complete; this continuation did not
repeat ingestion. Existing monetary/ratio V1 contracts, Financial model
financial-v0.5.18-original-ratio-receipts, framework 0.8.0 and schema 0.8.2 stay
unchanged. No new runtime engine, formula, table or migration is introduced.

Source: retained Maybank 2025 financial statements, PDF SHA
`2fc421fac71b9f5a9c3063709662a265b9c1fe3c7e29ea842ff2c78eaf041c55`.
Physical pages 30, 86, 217, 243 and 244 were rendered and visually reviewed, not
just text-searched. This remains single manual transcription, LOW trust /
RETRIEVAL_TIME, not independently verified accounting or provider corroboration.

## New Original Amount Edition

`config/global-document-reviews/maybank-2025-capital-equity.toml` preserves all
22 existing income/current-comparative rows and appends nine point-in-time balance
annotations. All amounts below are original Group-column MYR-thousand values,
not base-currency conversions or admitted canonical metrics:

| Original context | 2025 | 2024 comparative | Physical / printed page |
| --- | ---: | ---: | --- |
| Attributable-equity heading subtotal | 93,444,627 | 93,970,628 | 30 / 28 |
| Non-controlling interests | 3,397,216 | 3,236,509 | 30 / 28 |
| Note 59(c), Total CET1 Capital | 69,954,382 | Not transcribed here | 243 / 241 |
| Note 59(c), Total Capital | 87,042,398 | Not transcribed here | 243 / 241 |
| Note 59(d), Total RWA | 436,091,630 | Not transcribed here | 244 / 242 |
| Note 12(ix), Net impaired loans | 5,081,470 | Not transcribed here | 86 / 84 |
| Note 12(ix), Net loans, advances and financing | 644,366,273 | Not transcribed here | 86 / 84 |

The attributable-equity subtotal has no repeated label on its numeric line; the
review explicitly uses the preceding "Equity attributable to equity holders of
the Bank" heading and identifies the subtotal context in its column annotation.
It is not total equity including NCI, Bank-only equity, regulatory CET1 or an
inferred share count. Capital/RWA rows are explicitly annotated regulatory-note
balances, not financial equity or total assets. Source labels/scopes remain
unqualified; their coexistence does not authorize cross-scope calculations.
Comparatives are as presented in this filing, not original 2024 vintages.

## New Original Percentage Edition

`config/global-document-reviews/maybank-2025-ratio-definitions.toml` has six rows:
the two capital ratios now point to Note 59(b), physical 243, rather than only the
summary; three previous summary observations are unchanged; one separate Note
12(ix) "Ratio of net impaired loans" observation is added at physical 86.
Previous editions remain retained, never overwritten or silently relabelled.

Note 59's Group consolidation exclusion statement is retained as a source note:
insurance/takaful investments and associates are excluded from the capital
adequacy consolidation described there. This is not financial-statement Group
equivalence or independently verified regulatory qualification. Candidate RWA
and capital definitions are explicitly unadmitted; denominator/regulatory-scope
verification flags remain false even when descriptive notes are nonempty.

Note 12 preserves the net impaired-loan basis and the net-loan denominator after
investment-account funding and allowances. Net impaired loans cannot become a
gross NPL alias. Original annual ROE averaging/attribution and loss-coverage
definitions remain unresolved. No ratio formula, rounding tolerance, policy
threshold, banking score or investment conclusion is admitted in this slice.

Physical 217 / printed 215 discusses liquidity management and use of LCR/NSFR.
The selected page supplies no numeric LCR observation for this review. No zero,
assumed 100%, fabricated percentage or issuer-wide nondisclosure claim is made.
Explicit LCR research questions remain MISSING_REVIEWED_ROW; a separate dated
liquidity disclosure/Pillar 3 source still needs locating, capture and review.

## Explicit Plan And Reproduction

`config/bank-document-input-plans/maybank-2025-capital-equity.toml` pins the new
31-row monetary evidence/envelope/PDF. Its 19 source questions yield 11 matched
unqualified annotations, five ratio-contract requirements and three external
dependencies. The old parent-equity external question becomes an explicit
original-heading subtotal question in this new plan; prior equity and separate
NCI questions are added. This fills selected transcription coverage only, not
independent source/sector admission, complete financial research or valuation.

- Monetary recorded_at: `2026-10-30T09:34:14.051053+00:00`.
- Monetary evidence: `cd960b1f8a01123bb49a08ee9f19e67b0c49b8c551cc4156a7ab7d7c38cd2655`.
- Monetary envelope SHA: `82c24ad69af1890f0369244c6ef598f1b89ae9ca607d45fe7db6d88f87aebd5e`.
- Ratio recorded_at: `2026-10-30T09:34:15.513182+00:00`.
- Ratio evidence: `7baa2f03ed448184922ff3aa5c3136991f8431e6794b68cfa9a83518cf8d8ace`.
- Ratio envelope SHA: `82f17fe3ae323bda926dcf7f8d82392f3a06a7d2f92c5af56e757b0e6d50b488`.
- Plan availability annotation: `2026-10-30T09:49:10+00:00`, after recording, not issuer publication.
- Plan hash: `c2a543f84fc2cd3de15af6baecd37b70c2e1ed91e798a06545ce913a5f58392d`.

At fixed cutoff `2026-10-30T09:49:11+00:00`, repeated reads/coverage/questions
are identical and do not change either real database. The old plan returns
SOURCE_PLAN_BINDING_MISMATCH at the new cutoff, never automatic rebinding.

- New monetary input hash: `4f9a7a31d55af4b1040612e371e1313a1838374162503ac00cf007debe84c314`.
- New ratio input hash: `3001692865fd6b91c1895b40ec93cb8c42b4e9ee3075b51556da3c0edb3f7f94`.
- Coverage hash: `94674e28c550e7615aee04fcec22421a8c88eaf37a13dad2d7d5d966178517b5`.
- Six ratio questions plus explicit missing LCR question hash:
  `13feeaf98fd49a02bbcd926d51fc7f306df1dd524170779d2c795108122b5a98`.

Old monetary read at `2026-10-29T12:11:01+00:00` still has 22 rows and hash
`4aa54309f31a06aa37bc0de31868fdd26f1b5feec8efda2a2767219c2344ea2c`.
Old ratio read at `2026-10-29T13:55:41+00:00` still has five rows and hash
`1e3cbb84101a292ab9a788a00960dd8dad7719bcbffe3e5cda9bb19e94aa35c1`.
More detailed notes cannot retrospectively improve earlier knowledge or trust.

Document database now has nine evidence records/artifacts/completed batches,
zero canonical facts/reports/signals and no FK violations. Current SHA:
`e7a694d2638c65676151716376ecc0a4d8dc6dda6c9ce0736cabb71e046c7528`.
Previous `69d54a7bc32b99b560bc75edbbaec9219e24ba2046c7e4fe127c106e338684e7`
is historical. Existing price/native DB remains
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
Ignored data/artifacts still need approved encrypted co-retention; this is not a
new recovery baseline, Git-backed data archive or cross-device restore proof.

## Boundaries And Next Work

Existing report inputs can retain these exact receipts; no real screened queue or
ResearchReport is invented from exploratory captures. Financial remains unscored,
confidence zero, reports incomplete and InvestmentScore absent. PIT UNSUITABLE,
production NOT_READY, disabled defaults, R1-R6 partial and launch ready/not accepted
remain unchanged. No network provider call, strategy, Portfolio, Notification,
Paper, Broker, Order, Execution, live or allocation implementation. No commit/push.

Next: explicit cross-receipt arithmetic questions for source-defined capital and
asset-quality candidates, with original scope/unit/date/edition checks and no
policy credit; separately locate numeric liquidity/current filing evidence and
review sector/source methodology before real research/validation. The known Bank
summary/statement revenue discrepancy and independent corroboration remain open.

## Verification

**2892 passed / 6 skipped** in 144.75 seconds, including 14 source-edition cases.
Ruff passes, mypy passes on 296 source files, all 140 governance checks and
`git diff --check` pass. Three new source/plan documents pass credential-structure
checks. Database/raw-artifact/test-cache paths remain ignored. No runtime import
or trading-layer changes were made in this slice. Six opt-in real-network tests
remain skipped; retained-file reads are not current provider capability probes.

Tests preserve all 22 prior income rows, exact original amount/unit/period/page
annotations, capital-scope notes, distinct net-loan context, explicit new plan
bindings and historical cutoff receipts across UTC/Malaysia offsets. They verify
stale plan rejection, missing LCR, continued false scoring/replay authorities and
absence of canonical facts/reports. Literal plan checks and synthetic source
identities prove software/annotation consistency, not independent numeric accuracy.
No repeated ingestion was necessary; read-only reproduction preserves DB hashes.
