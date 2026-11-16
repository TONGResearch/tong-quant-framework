# HK/MY Primary PDF Evidence Slice

Date: October 28, 2026 (Malaysia). Work package: WP-LAUNCH-001, R2 only.
This is original-document retention, not a financial evaluation or source
qualification. No provider is trusted by default.

## Implementation And Boundaries

Explicit market/subject/document URL and caller annotations -> fixed-host HTTPS
transport -> original PDF bytes inside a JSON evidence envelope -> existing
ProviderNeutralIngestionService -> existing SQLite evidence/artifact/batch tables
and content-addressed files -> exact, fixed-cutoff read reconstruction.

- Dataset: `global_primary_document_snapshot`.
- Version: `GLOBAL_DOCUMENT_VERSION = global-primary-document-snapshot-v1`.
- Providers: `hkex_document` and `maybank_document`. These names mean transport
  provenance, not verified security identity or trust admission. The Malaysia
  scope is **Maybank annual-report PDFs only**, not all Bursa issuers or a Bursa
  API. HKEX scope is the explicitly allowed `www1.hkexnews.hk` SEHK PDF path.
- No new interface, domain report, schema migration, dependency or trading layer.
- `ProviderArtifact.media_type` is application/json because it stores the
  envelope. The separately hashed original PDF is base64-retained byte-for-byte,
  not reconstructed from text. Legacy artifact published_at is capture time with
  RETRIEVAL_TIME, not claimed first issuer publication.
- No redirects, credentials, cookies, browser login, crawler, auto-discovery or
  arbitrary external hosts. Two sequential attempts maximum, 15-second timeout,
  bounded backoff, body 32 MiB / envelope 48 MiB. Only PDF magic is checked; that
  is not PDF structural, audit, accounting or authenticity validation.
- Error codes, not remote error bodies or exception details, are persisted.
  Credential-like assignments in annotations/original bytes are rejected before
  base64 retention. This does not claim universal secret detection inside PDFs.
- Issuer label, routed Yahoo-style subject, document kind and period_end remain
  caller annotations. The landing URL is a reference, not a retained/verified
  catalog. `issuer_to_instrument_verified` and `landing_link_verified` stay false.
- Read mode requires an explicit URL; it does not choose a favorable annual
  edition or declare it current. Latest failed/tied/tampered captures or future
  batch completion for that requested document cannot fall back to older positives.
  Query cutoff comparison uses actual UTC instants. Freshness stays UNASSESSED.
- LOW / RETRIEVAL_TIME and all numeric-extraction, scoring, canonical, validation,
  historical-replay and execution authority remain false. No PDF text/table
  extraction exists in production. Offline visual inspection below is a separate
  manual observation, not a reviewed numeric mapping or independent validation.

## Real Retained Samples

Database: ignored `data/processed/global-primary-documents-20261028.sqlite3`.
Raw root: ignored `data/processed/raw/provider-artifacts`.
Common read cutoff: `2026-10-28T00:09:00+00:00`.

| Context annotation | Transport / report | Bytes | Actual capture UTC |
| --- | --- | --- | --- |
| 0700.HK / Tencent Holdings Limited | HKEX PDF, annual report 2025 | 3,999,857 | 2026-10-28T00:08:48.016301+00:00 |
| 1155.KL / Malayan Banking Berhad | Maybank official PDF, annual financial statements 2025 | 3,415,287 | 2026-10-28T00:08:48.663026+00:00 |

Both records are `captured_pdf_unqualified`. Web discovery identified a Maybank
official landing-page link; this relationship has not been captured in the
database, so the runtime correctly does not claim a verified landing link.
The ListedCompany copy was not captured or compared, and is not an independent
provider merely because it is a separate host. No direct Bursa announcement
capture or publication-time validation has been completed.

Receipts (same cutoff, after the explicit freshness label):

| Item | HKEX/Tencent | Maybank |
| --- | --- | --- |
| Original PDF SHA-256 | `2a7547168077c3d9994af673125e77612e8656bc0f17ad189371d7e4088f4e98` | `2fc421fac71b9f5a9c3063709662a265b9c1fe3c7e29ea842ff2c78eaf041c55` |
| Envelope SHA-256 | `05acb4302f5e521623cdee1bb7b96178654708b84bea13a6c644a1791cbb9e9f` | `af333d824eb8cf23b4b8aef5fad322cf4a77ea639ea09f7fa41796c8e91aa18f` |
| Evidence ID | `a977555c1a3911db6a7ace36c4a90026a3bef4fdcd798a64aa699549628e7730` | `31beea56348d0985b79317e98f902f895174c9c7406eab44104820d1f48ef72e` |
| Read input hash | `fe71beafffb28035cf87309f5323fa23e5f2f6178b1c77d77c75efb7ea0a8ff1` | `22f55739d4f405848b93f7ef6e0b33d32dfb02aea5c63bac7f69a3cd3db44249` |

Two evidence records, two artifacts and two completed batches; zero canonical
fundamental facts, research reports or signals. Integrity check passes. Read
repetition preserves input hashes and SQLite bytes. Database SHA-256:
`e636ab7a53ce84c6e34bf051995226a061d42a0c9d4506e9a41db53d734d91cf`.
No other evidence database was written. New raw/database files remain ignored by
Git and need encrypted co-retention; a code push alone cannot recover them.

## Manual Source Review And Next Mapping Checklist

Retained bytes were checksum-verified, decoded outside the repository and rendered
offline with bundled PDFium. Observed page counts: 282 and 305, not completeness
of historical disclosures. Physical pages are one-based below; printed labels
are separate and must not be confused by a future extractor.

| Sample | Observed page / issue | Required handling before future numeric mapping |
| --- | --- | --- |
| Tencent | Cover: HKD counter 700 and RMB counter 80700; physical page 130 / printed 129 shows consolidated income, RMB million, with current and comparative columns | Separate counter, quote currency, reporting currency and share-class evidence; distinguish total profit, parent-attributable profit and non-IFRS measures; preserve reporting period, unit, scope and exact column |
| Maybank | Physical page 5 / printed 3 separates Group/Bank, current/prior columns, amount, percentage and sen-per-share labels; prior-year restatement note appears | Do not join subsidiary Maybank Philippines/Indonesia/Singapore data to Malaysian listed parent; preserve group versus bank, unit and version labels; bank operating revenue and net operating income are distinct; ordinary-company debt/cash-flow rules cannot stand in for bank analysis |

These are extraction hazards and review requirements, not approved accounting
policy, scoring weights or security identity. No numeric value was promoted from
this manual review. Pages/columns/units, complete notes, auditor scope and the
latest interim edition require dedicated review. Bank capital-ratio definitions
and dividend-adjustment basis must be read explicitly, never inferred from a
generic percentage label. Financial scoring remains closed.

Next bounded deliverable: a separately versioned, source-hash/page/column/period/
unit-bound review contract for overseas observations, preserving unknown and
conflicting values. Do not relax the China-only CNY/calendar-YTD extraction model
to accept these PDFs. Keep official ResearchReport unique and require real
screened candidates plus independently admitted sector policy and validation
before any research-decision release. Preserve all four markets and financial
subsectors; two PDFs do not accept R2 or R1-R6.

## Use And Verification

```sh
.venv/bin/python scripts/inspect_global_document.py \
  --database data/processed/global-primary-documents-20261028.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market hong_kong --subject 0700.HK \
  --document-url https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf \
  --as-of 2026-10-28T00:09:00+00:00
```

Read mode is offline/read-only; capture is separate and requires explicit
issuer/period/kind/landing annotations. Exit 2 reports an unqualified diagnostic,
not an execution approval. Read status and limitations rather than equating it
with an implementation crash. SQLite WAL mode can require writable SHM/WAL
sidecar access even for a query-only connection; sandbox permission renewal was
needed for the manual read check. No immutable-mode shortcut or database rewrite
was introduced to suppress that operational requirement.

Focused tests cover bounded transport/retries, errors, URL/market/path scope,
sensitive content, exact bytes, idempotence, manual labels, deterministic offline
reads, UTC cutoffs, future completion, latest failure/tie/tamper, provider mismatch
and explicit CLI modes. Manual real captures are not default-disabled live tests.
Full verification: **2575 passed / 6 skipped** in 297.07 seconds, 45 added cases.
Ruff passes, mypy passes for 286 source files, governance passes 129 checks and
`git diff --check` passes. AST review of the three new runtime files checks 46
imports with zero forbidden execution/broker/order/trade/fill/paper/portfolio/
notification dependencies. New database/artifacts are Git-ignored. The six
default-disabled network tests remain skipped; manual captures are separate.

PIT UNSUITABLE; production NOT_READY. No commit/push, Paper, Broker, Order,
Portfolio, Notification, allocation or live changes. Execution remains disabled.

## Primary References

- [HKEX Tencent filing](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf)
- [Tencent financial-report index](https://www.tencent.com/investors/financial-reports/)
- [Maybank official annual-report index](https://www.maybank.com/en/investor-relations/financial-overview/annual-reports.page)
- [Maybank official financial statements](https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-financial-statements.pdf)
- [Maybank IR announcement mirror](https://maybank.listedcompany.com/news.html/id/2605866)

Web observations are pointers, not retained catalog evidence or a second review.
No universal PIT safety, provider independence or dataset trust is inferred.
