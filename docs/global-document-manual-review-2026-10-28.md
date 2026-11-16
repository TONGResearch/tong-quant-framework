# Source-Pinned Overseas Monetary Review

Date: October 28, 2026 (Malaysia). WP-LAUNCH-001 / R2 only. No trading authority.

## Delivered

Independent overseas transcription contract, strict plan parser, provider-neutral
evidence persistence, exact retained reconstruction, preview/write CLI, tests and
two real manual plans. No relaxation of the existing China-only CNY/calendar-YTD
extraction contract; no new official research-report or canonical fact model.

Version: `GLOBAL_DOCUMENT_REVIEW_VERSION = global-document-manual-review-v1`.
Provider: `global_document_manual_review`; dataset:
`global_document_monetary_review`. This is the reviewer identity namespace,
not another independent market-data provider or a calibration vote.

## Contract And Time Semantics

`GlobalDocumentReview` pins market, subject, explicit document URL, source evidence
ID, source envelope/PDF hashes and actual source availability. It declares a
reviewer, claimed reviewed_at, report-end annotation and a bounded immutable row
tuple. Parent lookup reconstructs the current unique retained PDF and compares
all pins and the report-end annotation at one SQLite snapshot/cutoff.

Each `GlobalMonetaryRow` preserves native label, statement, Group/Bank/parent
scope, exact start/end, current/comparative column, column text, currency, explicit
unit/label, quoted Decimal value, raw cell text, one-based physical PDF page,
separate printed page label and restatement annotation. No generic revenue,
net-income or parent-profit alias is inferred. Current column must match the
filing-end annotation; comparatives must precede it. Balance observations have
no flow start; income/cash-flow observations require one. Duplicate identities/
contexts, future periods, unsupported currencies/units and credential-like
content are rejected. Negative monetary values are not automatic hard failures.

Scope is bounded monetary observations in CNY/HKD/MYR/USD, unit/thousand/million;
not ratios, per-share amounts, FX, growth, TTM, sector policy or financial scores.
`unqualified_scaled_amount` uses exact Decimal arithmetic, but does not establish
accounting comparability or greater precision than a rounded financial summary.
Unsupported units are outside this version, never guessed. Known source units
are required even for unresolved numeric cells.

Cell states: transcribed, missing, unreadable, conflicting. Only transcribed
cells may have a Decimal. Other states retain raw annotations with null source/
scaled value, never zero or an older favorable value. TOML uses a quoted empty
source_value for an unresolved cell; JSON receipts retain null. Page existence,
printed-page/column/unit accuracy and raw-text/value agreement remain manual
annotations, not machine-verified PDF extraction or a second review.

**Claimed review time is not database availability.** Explicit write records an
actual UTC recording time, no earlier than claimed review and source capture;
that time drives evidence, artifact and batch availability. CLI `--as-of` is
preview-only and cannot be combined with `--write`. A preview uses a hypothetical
recording cutoff and clearly says `persisted=false`; its hash is not the later
persisted identity. Completion time must also be visible before a read can use
the record. Neither source/report dates nor claimed review time are publication.

Preparation checks current source pins immediately before neutral ingestion.
There is no claim of one transaction spanning source inspection and ingestion;
a concurrent source recapture can invalidate the stored review. Every read
rechecks source pins in one snapshot, so stale/changed/failed/tied/tampered
sources, bad review artifacts and future completion cannot promote observations
or fall back to an older favorable review. Historical explicit cutoffs remain
reproducible; revisions are not silently deleted or rebound.

## Real Samples And Receipts

The already retained, checksum-bound PDF pages were visually inspected. Plans:

- `config/global-document-reviews/tencent-2025-income.toml`: four native rows,
  physical PDF page 130 / printed 129. Revenue, total profit and parent-
  attributable profit stay distinct; the fourth row is a prior-year comparative
  as presented in this later filing. Reporting currency CNY, not the HKD counter.
- `config/global-document-reviews/maybank-2025-summary.toml`: four native rows,
  physical page 5 / printed 3. Operating revenue versus net operating income,
  and Group versus Bank attributable profit remain separate. MYR million,
  explicitly annotated as a rounded summary, not full-statement raw precision.

Both plans say single Codex manual transcription, no independent second review.
No complete auditor/notes review, issuer/security admission, restatement lineage
or latest interim coverage is claimed. No factual investment conclusion follows.

Database: ignored `data/processed/global-primary-documents-20261028.sqlite3`;
artifact root: ignored `data/processed/raw/provider-artifacts`.
Fixed read cutoff: `2026-10-28T05:14:00+00:00`.

| Receipt | Tencent | Maybank |
| --- | --- | --- |
| Actual recorded_at UTC | 2026-10-28T05:13:23.862213+00:00 | 2026-10-28T05:13:25.136491+00:00 |
| Review envelope SHA-256 | `fce543c71ac3f2584ece0a11a5d2c03e31e961e9434642e38478d6aaae1243e1` | `22204f1befcb9466aafa26a2d23421257d845b1b52a8775a6e96fcd4e9925758` |
| Review evidence ID | `9c0b52d5d1f03c09a192e6b308e24b978587150174782084d4c7655e7518b69d` | `291aaaddb94cedab823fa27473d4227cd292ec018041c17a67b26e77d5bf1bde` |
| Read input hash | `e953db7e47341ee0d0da52163f62357b5183ef0bc5648917f8683ae8d1a46a97` | `a8e3d5d37ea07351120b33159c34c0ae737a225bfa88c7b28343aac561b5aed7` |

Four evidence records/artifacts/completed batches total: two original PDFs plus
two review envelopes with eight observations. Zero canonical fundamental facts,
research reports or signals. SQLite integrity passes. Repeated reads preserve
database bytes and the two earlier fixed-cutoff primary-document hashes.
Database SHA-256 after writes:
`899f4c282eac3d41acc8bc0863cfd712a6c89389a2972de1425bab1ed5ce3de6`.
New ignored database/artifacts still require encrypted co-retention; Git alone
cannot reproduce the data. The source-only milestone's old database hash is a
historical checkpoint, not the new post-review hash.

## Operation And Next Step

```sh
.venv/bin/python scripts/review_global_document.py \
  --database data/processed/global-primary-documents-20261028.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --review-plan config/global-document-reviews/tencent-2025-income.toml
```

Default preview does not initialize a database, persist evidence or populate
facts. Explicit `--write` stores unqualified evidence at actual recording time.
Exit 2 denotes a diagnostic, not an order or scoring approval. For historical
reads use `read_global_document_review_inputs` with the documented fixed cutoff;
do not overwrite claimed review time to reuse an old favorable result.

Next: separately reviewed native-field/accounting correspondence and read-only
technical/financial presentation, keeping mismatched total/attributable profit,
scope, rounding, periods and currency visible. No automatic Yahoo/native alias,
independent consistency claim or financial scoring. Real screened candidates,
admitted sector policy and actual strategy validation still precede decisions.
Four-market R1-R6 acceptance remains partial, not complete after eight rows.

PIT UNSUITABLE; production NOT_READY. All canonical, scoring, independent-review,
source-location, issuer-identity, validation/replay/execution flags remain false.
No schema migration, new dependency, Paper/Broker/Portfolio/Notification/live
change, commit or push. Full quality results are recorded in PROJECT_STATUS.md.

## Verification

Full suite: **2619 passed / 6 skipped**, 116.38 seconds; 44 added cases. Ruff,
mypy (289 source files), governance (130 checks) and `git diff --check` pass.
Scoped AST checks find zero forbidden imports across three runtime files / 41
imports. New tests cover scope/unit/period/decimal rules, unresolved cells,
source pins, actual availability versus claimed review time, preview-only CLI
cutoffs, source recapture/failure, newest bad review rejection, tampering, ties,
future completion, exact reconstruction and checked-in plan schemas. No real
credentials or new dependencies were introduced. Default-disabled network tests
remain skipped; no provider network capture was performed in this slice.
