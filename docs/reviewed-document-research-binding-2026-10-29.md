# Reviewed Document Inputs In Official Research

## Delivery And Boundaries

WP-LAUNCH-001 remains ready, not accepted. This slice connects existing HK/MY
source-pinned manual observations to the existing official ResearchContext and
Financial assessment. No parallel ResearchReport, financial metric aliases,
scoring policy, provider, schema or trading path is introduced.

`read_global_document_review_inputs` -> immutable
`ReviewedDocumentResearchInput` -> existing `ResearchContext` ->
`FinancialResearchModule` diagnostic features -> existing SQLite report storage
and reconstruction. Technical assessment may use the same context/cutoff.
The input is a copied canonical JSON receipt, not a new research outcome model.

The factory invokes the exact retained reader, preserving current parent, source
bytes, artifact ownership, batch chronology and latest-failure checks at the
requested snapshot. Subsequent context validation checks receipt consistency,
not live database changes or independent source truth. A later business run must
read inputs again at its cutoff; do not relabel an old snapshot as fresh data.
Cross-database factories share a cutoff but do not imply an atomic combined read.

## Input Integrity

- Bound to exact subject, supported market/document URL and actual UTC cutoff.
- LOW trust and RETRIEVAL_TIME remain separate, unchanged labels.
- All canonical population, accounting, independent review, issuer identity,
  scoring, replay, validation and execution authorities remain false.
- Successful receipts require one selected latest capture, matching recording
  time, strict original manual-review model and exactly reproduced observations.
- Missing/rejected receipts preserve their state and cannot contain usable rows.
- Claimed manual review time cannot exceed actual recording/capture availability;
  captures cannot exceed the requested cutoff. No historical publication is inferred.
- Receipt JSON is copied/bounded and revalidated before direct evaluation or
  persisted run creation; symbol, market, cutoff and non-equity mismatches reject.
- Manual and native overseas receipts may coexist with the same requested sector
  label, but this does not verify that classification or map either dataset.
  Conflicting labels and parallel canonical financial receipts reject explicitly.

Public checksums and caller metadata cannot authenticate a fabricated receipt or
promote its authority. The exact-reader factory is the production construction
path; even a fabricated self-consistent receipt cannot produce financial scores.

## Official Output And Versioning

Financial features retain the complete manual receipt JSON/hash, source status,
unqualified source binding, row count, requested sector and LOW/retrieval labels.
Missing and failed observations are retained, not replaced by Yahoo values or
older reviews. Native and manual bodies stay distinct; quote/reporting currencies,
Group/Bank scope, total/attributable profit and comparative editions remain visible.

Financial score stays null, confidence zero, sector policy NOT_ADMITTED. A report
including Financial stays INCOMPLETE and InvestmentAssessment cannot produce an
InvestmentScore. Existing thesis, counter-thesis, invalidation, screening/queue
and validation boundaries remain in place. No report is manufactured from a raw
capture merely because the new input contract can be constructed.

Financial model version changes from `financial-v0.5.14-native-research-binding`
to `financial-v0.5.15-reviewed-document-binding`. Prior source packet versions,
receipts, historical reports and database schema remain unchanged. Existing
assessment feature JSON is sufficient for persistence; no migration or data write.

## Verification

Synthetic integration tests cover HK nonfinancial and MY bank contexts with
Technical + Financial in one official report, with native data missing and manual
data observed, missing, current-parent failed or artifact-tampered. Report storage
and reconstruction preserve receipt features and INCOMPLETE/no-score results.
Synthetic queues, sources and daily bars are contract fixtures, not evidence of
real screening acceptance, market calendars, provider trust or strategy returns.

Unit tests cover copied receipts, explicit unqualified sector labels, matching
timezone instants, future/naive timestamps, changed observations, unknown versions,
capture ties, authority escalation, identity/fund mismatches, conflicting sector
contexts and rejection before run writes. Test-fixture numeric types and receipt
JSON comparison were corrected during development, not provider or market logic.

Two real retained reader-factory reproductions use cutoff
`2026-10-28T15:23:27+00:00`, not the current run time as a fabricated historical
publication or live refresh. 0700.HK retains four manual observations; 1155.KL
retains 15. Each also retains 28 native Yahoo observations separately. No real
screened queue or ResearchReport was invented or persisted for these samples.
Receipt hashes and both database byte hashes remain unchanged by these reads.

- 0700.HK receipt: `7052f41fb90d096b18541a97e32a16f66edbfe56c33b815fabe5e0737e038ed8`.
- 1155.KL receipt: `529ceb19110a4857c5246d6bfc6d50548773de13d012223f38ea42c236cf9d74`.
- Document database: `81a136c9344ba4c8c44625e809e02c9ae2a70137b3a602ceabe75a26cb8b28bb`.
- Price/native database: `0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.

Full verification: **2738 passed / 6 skipped** in 111.90 seconds, 33 new tests.
Ruff passes, mypy reports no issues in 291 source files, all 135 governance checks
and `git diff --check` pass. Scoped runtime imports do not depend on execution,
broker, orders, paper trading, portfolio or notification. Six opt-in provider
network tests remain skipped; local reconstruction is not a live availability probe.

The known Maybank summary/statement discrepancy remains unresolved; this input
binding does not repair or approve it. Newer primary evidence still needs approved
encrypted co-retention, not merely Git code history. No commit or push performed.

## Next Bounded Bank Work

Review a source-defined bank metric policy before admitting financial scoring.
The following are research design questions, not approved weights/thresholds or
current regulatory definitions:

| Dimension | Required review |
|---|---|
| Survival | Explicit group capital, liquidity and asset-quality measures; units, applicable regulatory basis and period; no generic cash-flow failure rule |
| Cycle | Separately defined net-interest, Islamic, insurance and credit-cycle observations with exact periods; no forced generic revenue alias |
| Valuation | Dated instrument/share-class/action/currency evidence plus reviewed attributable earnings/equity; no automatic PB/PE from an unqualified snapshot |
| Growth | Comparable issuer editions and consolidation, recurring/one-off context and available revisions; no forecast guarantee or score from a single annual change |

Policy, industry, macro and Market Regime remain separate research variables,
not automatic gates. Populate actual Discovery/Hard Screening/Research Queue
inputs, source/sector admission and preregistered technical-plus-fundamental
validation next; do not substitute synthetic fixtures or an arbitrary ranking.
Primary-statement research need not wait for all Yahoo aliases, but it must not
bypass issuer qualification or approve unreviewed scoring rules.

R1-R6 remain partial; PIT UNSUITABLE, production NOT_READY, execution and
notifications disabled. Paper, Broker, Order, Execution, Portfolio, Notification,
live trading and allocation code are outside this slice.
