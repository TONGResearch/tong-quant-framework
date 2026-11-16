# Native Financial Evidence In Official Research

Work package: WP-LAUNCH-001; status remains ready, not accepted.

## Change

The existing retained overseas financial reader now has an immutable research
input contract, `data.native_financial_inputs.NativeFinancialResearchInput`.
`read_native_financial_research_input` reuses the existing byte/registry/completed
batch verification; it never creates a canonical FundamentalFact or admits a
provider/sector policy. Each document read returns a separate copy. The contract
binds exact subject/market/UTC cutoff, source version and false authority flags.
Unsupported trust/precision, malformed/future receipt clocks, tampering and
non-equity/parallel financial receipts cannot enter ResearchContext.

With an independently admitted Research Queue entry, the existing
FinancialResearchModule includes the original normalized receipt and native
review in the existing ResearchAssessment features. Source IDs/hashes, original
availability, missing/failed/rejected states, requested sector, unqualified
comparisons and unresolved sector questions therefore survive the existing
ResearchReport -> SQLite -> report reconstruction boundary. No alternate report
model, repository, schema migration or provider is introduced. The Financial
module version is `financial-v0.5.14-native-research-binding`.

The context is revalidated at engine and direct module entry, before any run
write. Missing or failed captures remain reportable, not silently dropped.
The receipt's `research_report_created=false` describes the input reader, not a
claim that a separately admitted research run cannot create a report.

## Authority Boundaries

- Public checksums prove internal content consistency, not independent source
  authentication. A caller-created, rehashed receipt cannot authorize a score.
- Official Financial output stays INSUFFICIENT_DATA, score null, confidence zero;
  resulting report/InvestmentAssessment stay INCOMPLETE without InvestmentScore.
- Report reconstruction retaining diagnostic features is not authorization to
  use those observations as PIT historical fundamentals or replay inputs.
- Sector selection remains an unverified request. Nonfinancial, bank, securities,
  insurance and unknown keep distinct questions, not approved financial rubrics.
- Original annual labels/currencies/unknown publication/revision/scope remain
  intact. No generic debt/profit aliases, FX, multiples or source promotion.
- No production queue/report is fabricated for the real exploratory captures.
  Synthetic persisted queues below test contracts only, not real screening.

## Verification Evidence

Read-only real-data check at `2026-10-27T04:20:54+00:00`:

| Subject | Input hash | Outcome |
| --- | --- | --- |
| MSFT | `03b721f1b69a37d97a379c913f67347ccf296d8ceee05f631623bb056d6400de` | Bound, exploratory, no score |
| 0700.HK | `ba54191cbf64907eef78167f94fb729d7f7754bb6524a7984d1bbc132a00430b` | Bound, exploratory, no score |
| 1155.KL | `9aae8481ca75f8d93f8308b75cc6ae32b9c8625f1b06ff72b1c74bd99bdffc60` | Bound, exploratory, no score |

Repeated input JSON is identical for each subject. The existing database hash
stays `0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
No new source request, data publication, production report or score occurred.
LOW/retrieval-time and EVIDENCE_INSUFFICIENT persist.

Regression coverage includes all five profiles/three overseas markets, defensive
copying, exact context/equity/cutoff checks, forged trust/authority/hash/version,
future/naive timestamps and secret keys. Integration cases retain successful,
missing, failed and tampered inputs through report storage/reconstruction and
confirm no InvestmentScore. Queue fixtures are explicitly synthetic. Whole-suite
verification: 2327 passed / 6 skipped in 82.35 seconds, 52 added cases. Ruff, mypy
(270 files), governance (124 checks), scoped forbidden-import review and diff
whitespace checks pass. Six default-disabled provider/notification live tests
remain skipped; real retained reads are separate from source/strategy admission.

## Remaining Work

Actual screened candidates, issuer/sector/accounting definitions and authoritative
release/interim/revision evidence still require qualification; then technical plus
financial conditions require actual historical/out-of-sample validation. This
slice supplies the official research input/output connection, not admission.
The existing ignored raw bytes/database still need encrypted co-retention.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled. No Paper,
Broker, Orders, Portfolio, Notification or live behavior changes.
