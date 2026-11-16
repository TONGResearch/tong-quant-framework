# Multi-Document Original Ratios In Research

## Delivered Boundary

WP-LAUNCH-001 extends the existing ResearchContext, Financial assessment and single
official ResearchReport path. An optional immutable `supplemental_ratio_inputs`
tuple carries up to three distinct original-document ratio receipts alongside the
existing primary `reviewed_ratio_inputs`. No new report, provider, storage table,
migration, scoring rule, trading capability or dependency is introduced.

Financial version is `financial-v0.5.20-multi-document-ratios`. Framework/schema
remain 0.8.0 / 0.8.2, migration head 0010. Existing stored reports are not rewritten
or requalified. New evaluations have the new version even without supplements.
The optional empty tuple adds no supplemental feature keys to legacy contexts.

## Contract And Failure Handling

- Supplements require a primary receipt. Its identity and existing questions/
  arithmetic plans remain authoritative for that exact primary document only.
- Only a tuple of ReviewedRatioResearchInput values is accepted. At most three
  supplements, four total documents. Duplicate document URLs reject, including
  repeated primary/alternate editions or missing receipts for the same URL.
- Every input revalidates immutable canonical JSON, hash, model, false authority,
  observations, ownership and actual UTC cutoff before direct evaluation/run
  writes. All instruments must be the same equity; parallel canonical financial
  receipts remain disallowed. Native/monetary/primary/supplemental requested
  sector labels must agree, without qualifying the sector classification.
- Existing exact readers retain current-parent/artifact/batch/source checks.
  Read all documents in one SQLite read snapshot for a new context. Copied
  receipts are not live source rechecks; reread every receipt for a new cutoff.
- Missing, failed and rejected supplemental inputs remain visible, including
  their URLs, hashes, warnings, periods, original row keys and false authorities.
  A healthy primary cannot erase an unhealthy supplement or vice versa.
- Receipt documents are sorted by URL for deterministic feature serialization;
  tuple permutation cannot change an assessment. Native row keys need be unique
  within each source, not across documents. Identical labels/keys do not merge
  values, dates, definitions or consolidation bases.

The existing Financial features preserve the unchanged primary receipt plus
`supplemental_ratio_receipts_json`, document count, requested sector and explicit
NOT_ADMITTED / aggregation-false / scoring-false flags. The full receipt includes
its source evidence/envelope/PDF identities and exact availability. Assessment
availability includes every receipt's read cutoff, including missing/failure
states; old raw facts cannot backdate a multi-document assessment.

Primary row questions never search supplements for missing keys. The existing
same-PDF ratio arithmetic plan still binds only its explicitly pinned primary
ratio/monetary inputs. Supplemental rolling-average LCR cannot be substituted
for an instant ratio, averaged from year-end balances, or mixed into a favorable
equation. All Financial assessments remain insufficient, score None, confidence
zero; reports INCOMPLETE and InvestmentScore absent. More retained documents do
not constitute independent calibration, complete history or sector admission.

## Coverage

36 new HK/MY cases exercise official Technical + Financial report persistence,
SQLite reconstruction, unscored InvestmentAssessment, distinct values sharing a
row key, unknown rolling basis, missing documents, primary-only feature behavior,
canonical ordering, maximum accepted bound, tuple/type/bound/duplicate/sector/
symbol/market/cutoff rejection and post-construction tampering before run writes.
Latest source failure on either document is reread at one new cutoff and cannot
revive an old receipt or replace missing primary questions with supplemental rows.
Synthetic queues and source bytes test contracts only, not real screening
admission, source quality, market coverage, strategy results or validation.

The real Maybank six-row Financial Statements receipt and separate three-row
Integrated Annual Report receipt are reread together at fixed cutoff
`2026-10-30T18:07:38+00:00`, preserving separate inputs. Both reproduce without
network access, ingestion or database writes. No real queue/report is invented
merely to demonstrate this new context slot. Source timestamps, notes and LOW /
RETRIEVAL_TIME labels remain unchanged.

Exact primary receipt hash at that cutoff:
`9b9be7e6e0caaca85088ca9e00d0015a51d558e17668e79ce0f03cfc531d6fa9`;
supplemental integrated receipt:
`a1d4f13b0b5ce5d2a2f3f7f894f541c21778dd268d920de9c1480de49e332f75`.

Database hash stays
`ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13`;
11 evidence/artifact/completed-batch rows, zero canonical facts/reports/signals.
No new raw artifacts or schema changes this turn. The earlier retained files
still need encrypted database-plus-artifact co-retention for cross-device recovery.

Verification: 36 new focused cases pass; full suite **2972 passed / 6 skipped**
in 124.15 seconds. Ruff, mypy (297 files), governance (143 checks), scoped import /
existing source-plan credential checks, retained DB hash and diff checks pass.
The six skips are opt-in real-network cases. No new network qualification or
whole-dirty-checkout secret certification is claimed.

## Next Acceptance Work

This closes the software gap preventing one report from retaining both original
ratio documents. It does not close the five bank ratio-policy or three external
source-plan dependencies. Next: latest-period and independently qualified
source/definition/perimeter evidence, explicit document selection in the read-only
delivery interface, admitted sector methodology and real screened Technical +
Financial research/validation. Nonfinancial and four-market acceptance must remain
separate; a Malaysian bank fixture is not evidence of complete global coverage.

PIT UNSUITABLE, production NOT_READY, R1-R6 partial, WP-LAUNCH-001 ready/not
accepted; execution/notification disabled and allow_live_orders false. No Paper,
broker, live order, allocation, portfolio or notification implementation; no
automatic commit or push.
