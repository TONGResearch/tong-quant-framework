# Reviewed Issuer Filing Facts: October 18

## Delivered Scope

WP-LAUNCH-001 now has a narrow route from a retained issuer PDF to auditable
financial observations in the existing `fundamental_facts` table. This is a
separate **manual issuer extraction**, not approval of the earlier AKShare
numeric spot review or automatic native-field mapping. No provider is trusted
by default; these facts remain LOW / RETRIEVAL_TIME and are not qualified for
historical replay, investment scoring or validation.

The dedicated plan `config/filing-extractions/600000-2026q1.toml` records the
reviewer, original PDF artifact id/hash, group/current-period column, CNY-million
unit, unaudited status, bank profile, period and source page/label for each row.
The retained [issuer report](https://static.cninfo.com.cn/finalpage/2026-04-30/1225261168.PDF)
was rechecked visually on PDF pages 15, 17 and 18. Values are manual annotations,
not authenticated by software PDF extraction or an independent second review.

| Metric | Source CNY million | Stored CNY absolute | Period |
|---|---:|---:|---|
| revenue | 46,573 | 46,573,000,000 | January-March 2026 |
| profit_attributable_to_parent | 17,861 | 17,861,000,000 | January-March 2026 |
| total_assets | 10,305,646 | 10,305,646,000,000 | March 31, 2026 |

All use the group column. Parent-attributable profit is deliberately not
renamed to generic `profit`. This bank example does not qualify general-company
cash-flow, debt, ROIC or growth scoring. It is not an issuer recommendation.

## Architecture

```text
registered CNInfo PDF capture + verified retained bytes
           + dedicated immutable manual extraction review
 -> ReviewedFilingAdapter -> ProviderNeutralIngestionService
 -> one SQLite transaction:
       ingestion audit + review-packet artifact/evidence + FundamentalFact
 -> MarketDataService explicit-as_of reads
 -X-> automatic Research/InvestmentScore, validation or execution
```

- `data.providers.reviewed_filings` implements the existing provider contract.
  Only group/current-period CNY-million revenue, parent-attributable profit and
  assets are supported. Unknown/company-only units, periods, ambiguous mappings,
  future inputs, source/request mismatches, unsupported URLs and hash changes
  fail closed. Decimal conversion preserves precision, zero and negatives.
- `data.filing_facts` requires existing visible instrument metadata and its
  registered source capture. It never creates a placeholder company or updates
  instrument metadata. Source reads share one snapshot; neutral persistence
  joins evidence, review packet, facts and audit atomically. Failed publication
  rolls back rows and removes the newly created packet file.
- `scripts/ingest_reviewed_filing.py` defaults to read-only preview. Publication
  requires `--write`, an existing database/source capture and a dedicated plan.
  It does not initialize or migrate a database. An explicit aware `--as-of`
  enables reproducible assessment cutoffs; default is current UTC. A cutoff
  supplied for fixtures is not proof of a real-world clock or approval.
- `reviewed-group-filing-facts-v1` is centrally versioned. Framework 0.8.0,
  schema 0.8.2, migration 0010 and all 64 tables are unchanged. No dependencies,
  trading, Portfolio or Notification changes were introduced.

The raw hash binds a retained JSON review packet, which references the exact
original PDF capture/hash and contains all manual semantics. It does not claim
to be the original PDF hash. Group scope, statement, source column, audit/sector
annotations and downstream-denial flags live in companion provider evidence.
The legacy FundamentalFact contract/table has no dedicated consolidation-scope
column: a consumer must reconstruct/reverify this evidence before assuming
scope, applicability or eligibility. A raw row alone is not research approval.

## Time, Revisions And Trust

Availability is the later of the source capture and manual review, never the
financial period end or a historic publication date. `published_at` retains
the source's claimed disclosure time, not an independently verified timestamp;
availability precision remains RETRIEVAL_TIME. Revision 0 is this local initial
observation, not proof that the issuer never restated the report.

An exact retry preserves the first fact/batch metadata without adding duplicate
facts. Altering the same version's material content fails. A genuinely later
manual review can create a new visible version, preserving the earlier view;
this mechanism is not recovered issuer revision history. UNKNOWN source trust
stays UNKNOWN; other labels are capped at LOW. These observations cannot satisfy
the independent-provider horizon or raise dataset PIT readiness.

## Actual Local Results

- Target: `data/processed/exploratory-pilot-20261016.sqlite3` only.
- Batch: `856c77ab-f089-4f5f-ac14-59e1d119bae8`.
- Review/fact availability: `2026-10-18T15:49:13+00:00`.
- Raw review-packet SHA-256:
  `bc7ddc18728f4714db39bcb58387f09451d8d54fb3aceca904745b256561388a`.
- Fundamental facts: 0 -> 3; provider evidence: 13,220 -> 13,223; registered
  artifacts: 7 -> 8. All eight files pass bounded hash verification.
- Real explicit-as_of reads return no sampled facts one microsecond before
  availability and exactly one per metric at availability. Both database
  integrity audits pass. Operational audit identity remains
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
- ResearchReport and ValidationReport counts remain zero. No scores, strategy
  validation, simulation, trade decisions or orders were generated.

Forty new regression cases cover bindings, future data, unknown/unsupported
semantics, decimals, immutable review fields, low/unknown trust, transaction
failure after fact writes, artifact cleanup, exact retries, conflicting/later
versions, preserved issuer metadata, rejected spot plans and CLI preview/write/
missing-database behavior. Full local verification: **1043 passed / 6 skipped**;
Ruff and mypy pass (229 source/script files). Final governance/whitespace results
are recorded in PROJECT_STATUS; no remote CI or installed release is claimed.

## Remaining Gates And Next Work

Keep native AKShare unit/scope/revision questions open. Expand reviewed issuer
periods and relevant metrics, with explicit comparative-column and restatement
semantics rather than assuming a current report proves its original historic
version. Add a typed research-facing source-binding/applicability read boundary
before promoting raw table presence into scored evidence. Bank and nonfinancial
research requirements remain distinct. An end-to-end real research/validation
chain and authoritative status/universe/action/runtime inputs are still missing.

New review data and code are not included in the earlier encrypted recovery
snapshot. Ignored source data is not uploaded by Git; independent-device
recovery and off-device retention need separate verification. No new commit or
push was performed. PIT remains UNSUITABLE, production NOT_READY and execution/
notifications disabled. This completes a bounded data slice, not the launch
work package, historical qualification, Paper acceptance or live authorization.
