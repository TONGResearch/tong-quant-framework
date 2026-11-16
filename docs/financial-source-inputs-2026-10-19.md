# Source-Bound Financial Research Inputs: October 19 MYT

## Bounded Delivery

WP-LAUNCH-001 now connects reviewed financial observations to a typed,
read-only research input boundary. It does not approve financial scoring,
historical replay, validation, Paper or live operation. All three real facts
remain LOW / RETRIEVAL_TIME. No new facts or business reports were written.
This document uses Malaysia dates; the actual diagnostic cutoff below is UTC.

## Architecture And Ownership

```text
MarketDataService explicit-as_of facts (one SQLite read snapshot)
 + registered source PDF + retained review packet
 + reproduced evidence/fact content + completed ingestion ownership
 -> ReviewedFinancialInputReader
 -> immutable FinancialInputSnapshot / FinancialFactInspection
 -> ResearchContext exact-consumed-fact/cutoff checks
 -> FinancialResearchModule diagnostic assessment, not scored evidence
```

- `data.financial_inputs` owns provider-independent immutable diagnostics.
  Hashes include complete facts, evidence/source references, requested metrics,
  scope, sector, statuses, missing inputs and model version. Missing metrics
  are derived from the requested set; present-but-rejected observations remain
  present. A source-binding pass is not financial/data-set completeness.
- `data.filing_inputs` verifies the currently supported reviewed-filing source.
  It reconstructs values and evidence through the existing extraction adapter;
  verifies packet/PDF bytes, registry metadata/keys/sizes, fact content, evidence
  content, batch ownership/provider/dataset/raw hash/parameters/start time and
  completed timestamps; checks requested versus annotated sector. Original
  provider publication claims are not independently authenticated.
- `SQLiteStore` gains two narrow read-only lookups: `ingestion_batch` and
  `provider_artifact`. Existing write ownership and schema are unchanged.
- `ResearchContext.financial_inputs` is optional for compatibility. When
  supplied it must match the exact consumed facts, instrument and cutoff,
  including after caller mutation. Research imports only the neutral contract,
  not the concrete filing adapter, file store or SQLite reader.
- Financial research with supplied fundamentals is now explicitly diagnostic:
  raw values and accompanying numeric/rubric evidence cannot authorize their
  own scoring. Score stays absent and confidence zero until a separate approved
  financial admission/scoring policy exists. Findings, values, revision notices
  and supplied evidence are retained for inspection. Legacy evidence-only
  research without fundamental inputs remains unchanged; this is not a global
  authentication gate for every ResearchEvidence in every module.
- Module features expose the input hash, requested gaps, binding state, scope,
  sector, audit status and filing reference. The bank profile explicitly lacks
  a qualified scoring policy and must not inherit generic-company ROIC/FCF/
  debt assumptions. A requested missing metric is not an approved bank checklist.

`financial-source-inputs-v1` is centrally versioned. Financial assessment
version advances to `financial-v0.5.2-source-inputs`; old stored assessments
are not rewritten or retrospectively qualified. Framework 0.8.0, schema 0.8.2,
migration 0010 and all 64 tables remain unchanged. No dependencies, strategy,
Portfolio, Notification, Paper, broker or execution changes were made.

## Status Semantics

| Status | Meaning |
|---|---|
| source_bound_observation | Stored fact/evidence/files/annotations/batches reproduce consistently. Not independent review of the source or manual annotations. |
| source_binding_rejected | A source, packet, fact, sector, batch or file check failed. The original observation remains visible. |
| unsupported_source | The fact's dataset has no verifier here. Not a statement that its value is false. |

Batch completion must be visible by the requested cutoff, even if a fact's
claimed availability is earlier. This conservative read rule does not rewrite
old timestamps. It checks recorded chronology, not an authenticated real-world
clock. Malformed canonical rows or database/schema errors can abort the read;
they are not silently converted into favorable missing-data results.

The deterministic input hash proves stored-content identity only. A consistent
forgery, false manual annotation, lost original revision or untrusted caller
cannot become an independently verified source by hashing. Reconstructed
inputs are not proof of the exact original inputs used by every historical run.

## Real Read-Only Observation

At `2026-10-18T16:11:19.453003+00:00`, the reader inspected the existing 600000
bank/group observations. Revenue, parent-attributable profit and total assets
each reproduced as `source_bound_observation`, retaining their LOW trust.
The explicitly requested `cash_flow`, `debt`, `roe` and `roic` remain missing.
`source_binding_complete=false`; all scoring/replay/validation authorizations
are false. Parent-attributable profit is not relabeled to generic profit.

- Retained local diagnostic:
  `data/processed/financial-reviews/source-inputs-final-20261019.json`.
- Input hash:
  `079647bd66bf1e568912514da8e553f13b9f07f60e4d630b699b9ad87e6d22be`.
- The final reader independently reconstructed this same hash and three source
  bindings from the same query/database, with missing metrics unchanged.
- Both database integrity audits passed; operational audit identity remains
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`,
  exploratory audit identity remains
  `c3e7770f1e12289383a6688363ebe747315778cd55030f3d2e9aa3e70b9b85ea`.
  These audit identities are integrity/schema/count checks, not row-content
  hashes. Databases retain 0/3 operational/exploratory facts and zero real
  ResearchReports/ValidationReports. No production source was written.

## Operator And Verification

`scripts/inspect_financial_inputs.py` requires an existing database, explicit
artifact root, symbol, requested metrics and sector profile. `--as-of` accepts
an aware cutoff; default is current UTC. It never initializes a database or
downloads provider data. Optional credential-screened JSON exports use a new
mode-0600 file and refuse overwrite. Exit 2 intentionally denotes partial,
non-authorizing diagnostics even when all requested bindings pass.

Full local verification: **1096 passed / 6 skipped**, including 53 new regression
cases; Ruff and mypy pass (232 source/script files). Final governance/whitespace
results are recorded in PROJECT_STATUS. Tests include changed files, fact/
evidence/registry tampering, false/missing/future batch completion, wrong batch
parameters/start/ownership, unsupported sources and sector mismatches,
deterministic query-order hashing, missing versus rejected records, read-only
CLI/no-overwrite exports, exact context matching and attempted high-score bypass.

Next expand explicitly reviewed comparable periods/relevant financial inputs,
define sector-appropriate non-trading research calculations and a separately
reviewed scoring policy. Preserve comparative-column/revision lineage and do
not backdate today's disclosures into historical availability. The global PIT
and runtime/strategy acceptance gaps remain open; evidence accumulation runs
in parallel, not as a substitute for software delivery.

New diagnostics/source data are ignored local files and not retained in the
earlier encrypted snapshot or uploaded by Git. Full historical consumed-input
provenance and independent-device recovery remain open. No new commit/push or
remote-CI/installed-release acceptance is claimed. PIT remains UNSUITABLE,
production NOT_READY, execution and notifications disabled.
