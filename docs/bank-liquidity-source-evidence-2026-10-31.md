# Separate Bank Liquidity Source Evidence

## Delivered Slice

WP-LAUNCH-001 retains a real second Maybank PDF and a separate three-row ratio
review through existing interfaces. No runtime/schema/provider/version change:
framework 0.8.0, schema 0.8.2, migration 0010, Financial v0.5.19.

The [official catalogue](https://www.maybank.com/en/investor-relations/financial-overview/annual-reports.page)
lists the [2025 Integrated Annual Report](https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-integrated-annual-report.pdf)
separately from the Financial Statements. Existing bounded transport retained
15,223,093 bytes / 181 pages; no downloader bypass or endpoint broadening. The
catalogue link was inspected online but not retained as verified catalogue
evidence; machine landing-link/issuer-identity flags stay false. Separate Pillar
3 disclosure was inspected as a lead, not ingested under an inaccurate document
kind. No issuer-wide nondisclosure or market-wide coverage claim is made.

## Visual Review

Physical pages 68, 69 and 81 (printed 66, 67, 79) were rendered and visually
inspected from hash-verified bytes. Page 81, Group CFO liquidity indicators:

| Row | Reported percentage | Preserved basis |
| --- | --- | --- |
| Liquidity Coverage Ratio (LCR) | 138.2% | `unknown`: source note describes a rolling 12-month average, unsupported by the current basis enum. |
| Net Stable Funding Ratio (NSFR) | 116.6% | `instant`: manual issuer year-end annotation, not independently qualified. |
| Loan-to-Deposit Ratio (LDR) | 93.8% | `instant`: manual issuer year-end annotation, not independently qualified. |

LCR/NSFR also appear on page 69; same-origin repetition is not independent
calibration. Page 68 explains KPI symbols; page 81 describes restated LCR using
a rolling 12-month average. Retain `marked_restated`, unknown start/operator/
frequency/denominator, not an instant equation or invented annual average.
NSFR funding components and LDR lending/deposit definitions stay unknown.
Group labels do not verify regulatory perimeter; integrated post-dividend
capital indicators cannot replace differently based Financial Statements rows.

New plan: `config/global-document-reviews/maybank-2025-integrated-liquidity.toml`.
Old 31-row monetary/six-row ratio editions remain unchanged. Their Bank revenue
discrepancy stays unresolved. All new rows remain single-review LOW/retrieval-
time, freshness UNASSESSED, definition-required, without canonical metrics,
scoring/replay/validation/execution authority. The one existing immutable ratio
slot can consume this exact receipt; it is not multi-document aggregation. No
real queue/report/InvestmentScore is invented. Cross-receipt arithmetic requires
same-PDF instant inputs, excluding this LCR and other-document year-end balances.

## Provenance And Reproducibility

Subject/market `1155.KL` / `malaysia`; period 2025-12-31 is a manual annotation,
not verified issuer mapping. Publication timestamp remains unknown. Availability
is actual capture/recording, never backdated to the reporting year.

| Identity | Value |
| --- | --- |
| Source availability | `2026-10-30T18:02:16.660050+00:00` |
| Source evidence | `0d7938123db7f38f897346bc5f46ccad3378fe0963d27fed90e9a34e0e78e098` |
| Source envelope SHA-256 | `c6a1a50532d52e13a1c1537dd03ba3af094aae8c6bfeb0b7231ab3fc5df49597` |
| PDF SHA-256 | `93dee5b42f343147e3a576448b677eecf45df7bbe4df317a38f5ba44e8d70d6b` |
| Manual review | `2026-10-30T18:05:27+00:00` |
| Actual recording | `2026-10-30T18:07:29.996936+00:00` |
| Review evidence | `d79517da00302364dcf2db34ce86cb099a7ffd69c4a22b2784db1e9a8623c795` |
| Review envelope SHA-256 | `d80aea234b8c1632d9fdcb7c3ed14293ae071109c0a262718f090fbf63d588a8` |
| Review batch | `3a8e1e3d-81ef-45e2-a85f-737ba2bda8a5` |

At fixed cutoff `2026-10-30T18:07:38+00:00`, repeated one-snapshot reads produce:

| Receipt | Hash |
| --- | --- |
| Integrated source | `1f8269cf46589138cd3a39179dfcba8b61479722e5616a02f714f32b9c0f6af6` |
| Integrated ratios | `a1d4f13b0b5ce5d2a2f3f7f894f541c21778dd268d920de9c1480de49e332f75` |
| Three explicit questions, all DEFINITION_REVIEW_REQUIRED | `016866aa6c361403ea471575dcbe056ddab1f3570a40702227c12f4c0fea8357` |

At old cutoff `2026-10-30T16:47:54+00:00`, new-document readers return missing;
old money/ratio hashes remain `a8570c25c9f8b8ee5e580a0b01a5f1c32f412d320686111d9319e98ad864dc0d`
and `82c4a35aee731691b4cbf59a48f55e97ceb2bec8ae0130e25ade29906020a576`.
Old source-specific plans are not automatically rebound.

Document database `data/processed/global-primary-documents-20261028.sqlite3`
adds one source and one review: 11 evidence/artifact/completed-batch rows each,
zero canonical fundamental facts/reports/signals, no FK errors. Post-write hash
`ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13` remains unchanged
by reads. Price/native DB is unchanged at
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
No tables or migrations added. Preview retained review without recapture:

```sh
.venv/bin/python scripts/review_global_document.py \
  --database data/processed/global-primary-documents-20261028.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --review-plan config/global-document-reviews/maybank-2025-integrated-liquidity.toml \
  --kind ratio --as-of 2026-10-30T18:07:38+00:00
```

Exit 2 means unqualified, not failed ingestion. Preview does not persist. Do
not repeat `--write` to reproduce reads: recording has a new availability time.
Local envelopes/SQLite are Git-ignored; encrypted database-plus-artifact
co-retention remains outstanding. Temporary PDF/page renders are not a backup.

## Checks And Next Boundary

Four new cases cover HK/MY sibling-document isolation, source-parent identity
even for identical PDF bytes, separate ratio receipts, unknown rolling basis,
immutable research binding and latest-failure isolation. Full suite:
**2936 passed / 6 skipped**, 120.89 seconds. The six skips are opt-in network tests;
this turn's real source capture is separate, not blanket provider qualification.
Ruff, mypy (297 files), governance (142 checks) and whitespace checks pass. New
plan passes repository credential validation; scoped tests import no trading,
portfolio or notification layers. Raw database/envelopes are confirmed Git-ignored.
These are scoped checks, not certification of every pre-existing dirty file.

Numeric liquidity evidence now exists for this annual issuer sample, but five
draft bank ratio-policy/three external gaps remain. Next: independent averaging/
formula/perimeter/source review, current-period sources, explicit multi-document
research assembly, admitted sector methodology and real screened Technical +
Financial research/validation. HK/US/China-A coverage is not upgraded by one MY bank.

PIT UNSUITABLE, production NOT_READY, R1-R6 partial, launch ready/not accepted,
disabled defaults persist. No Paper, broker, execution, live order, allocation,
notification or portfolio change; no commit or push.
