# Bank Financial Input Semantics: October 19, 2026 MYT

Work package: `WP-LAUNCH-001`, still `ready`, not accepted as complete.
Framework `0.8.0`, schema `0.8.2`, migration head
`0010_portfolio_evidence_lineage` remain unchanged. No trading functionality.

## Repair And Boundaries

Reviewed filing ingestion previously supported only group CNY-million amounts.
Reusing that conversion for a bank ratio would multiply a percentage by one
million and attach a currency. A separate, bounded v3 review now supports:

| Metric | Meaning | Stored unit | Stored currency | Time basis |
| --- | --- | --- | --- | --- |
| `nonperforming_loan_ratio` | Reported group nonperforming-loan ratio | `percent` | null | `period_end_ratio` |
| `provision_coverage_ratio` | Reported group loan impairment allowance / nonperforming loans | `percent` | null | `period_end_ratio` |

`1.23` means **1.23 percent**, not `0.0123`, 123 percent, CNY or a change in
percentage points. Coverage can legitimately exceed 100 percent. No automatic
fraction conversion, annualization, monetary growth calculation, or sector
score is inferred. Only current-period-end observations are supported in v3;
prior ratios, flow-period ROE/ROA, TTM and other ratio definitions remain
unsupported. Money and ratio rows cannot share a review plan/unit declaration.
NPL ratios outside 0..100 and negative coverage are rejected structurally.
These checks cannot detect a plausible but incorrect human annotation.

`ReviewedFilingAdapter` continues through `ProviderNeutralIngestionService`:
registered source PDF -> versioned manual review packet -> evidence + facts +
audit in one transaction. `FundamentalFact` uses existing nullable currency and
unit fields. Scope, basis, pages and sector remain in companion evidence and
the typed receipt, not standalone fact-table columns. No new tables or DDL.

`FinancialFactInspection` checks percent/basis/sector/statement/date semantics;
`ReviewedFinancialInputReader` reproduces packets, evidence, facts and registered
bytes/batch ownership at the cutoff. `ResearchContext` binds exact inputs, and
Financial research exposes period/unit/basis diagnostics with **no score**.
The monetary-comparison calculator explicitly leaves ratios unsupported rather
than inventing monetary changes or percentage growth.

## Actual Source And Exploratory Publication

Source: Shanghai Pudong Development Bank 2026-Q1 unaudited report,
[official retained-document URL](https://static.cninfo.com.cn/finalpage/2026-04-30/1225261168.PDF).
Pages 2 and 12 were read and visually reviewed, including date headers and the
group asset-quality discussion. Current group observations are 1.23 percent
NPL and 204.79 percent provision coverage. Parent-only regulatory tables must
not be mixed into this group series. Profitability footnotes explicitly require
separate period/annualization treatment; they are not admitted by this slice.

- Retained PDF SHA256:
  `df6911eb74bd5448fbf7729936979c60391052746db7d0577e4d4803f38d77e1`
- Plan: `config/filing-extractions/600000-2026q1-bank-ratios.toml`.
- Manual review time: `2026-10-19T03:03:05+00:00`.
- Packet version: `reviewed-bank-period-end-ratios-v3`.
- Packet SHA256:
  `bce4522c62399cf7fc870520dbd3b1f1a697b672d675bb7e93d15dd91e24b623`.
- Actual batch: `6f194086-1f78-4410-828e-5dbd41afac9d`, two accepted facts.
- Input receipt version: `financial-source-inputs-v3-bank-ratios`.
- Actual diagnostic cutoff: `2026-10-19T03:05:17.085285+00:00`.
- Input receipt SHA256:
  `f98e40551d8161e19e6f04bb342e01fe81205e776768011afc87aa1674dbc538`.

Only `data/processed/exploratory-pilot-20261016.sqlite3` was populated. It now
has 8 canonical facts, 13,228 provider evidence records and 11/11 registered
artifact files verified against retained bytes. All eight requested existing
observations reconstruct source bindings; four deliberately requested generic
fields (`cash_flow`, `debt`, `roe`, `roic`) remain absent. That gap list is not
an approved bank checklist and is not a readiness percentage. Zero real
ResearchReports or ValidationReports were generated.

New facts stay **LOW / RETRIEVAL_TIME**. Their original revision/publication
accuracy remains unverified; a reader additionally requires visible completed
ingestion, not just the manually recorded review timestamp. A current capture
of a past report is not evidence that its numeric values were known in March
or April. Manual source binding does not authenticate human extraction or
provide an independent second provider.

The existing six monetary facts still reconstruct against their original v1/v2
packet hashes, with the same three descriptive comparisons. Old packets and
evidence identities were not rewritten. The richer receipt and financial
diagnostic model (`financial-v0.5.4-bank-ratio-diagnostics`) are explicitly
versioned; earlier receipt exports remain historical artifacts.

## Integrity And Remaining Work

Both database audits pass. The operational database retains its original audit
identity `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`
and all table counts. Exploratory audit identity is now
`7f66660a3bbd4296a3eb8f077c31121b1d7db8a56a0bcefe62076b6f9e0df1fe`.
Audit identity checks schema/integrity/counts, not all row content; source
packet/evidence verification supplies separate bounded checks.

The new data/code/exports are not covered by the earlier encrypted snapshot.
Independent-device recovery, current encrypted retention, independent annotation
review, representative issuer/history coverage and complete original revisions
remain open. No remote CI, installed-release acceptance, commit or push occurred.

Next bounded work: define an explicit bank research-input policy with distinct
profitability (named ROE basis, YTD/annualized status and preferred dividends),
asset quality, group capital/liquidity and valuation requirements. It must
preserve missing/conflicting evidence and thesis/counter-thesis, not infer bank
quality from two ratios or substitute generic-company FCF/ROIC rules. Numerical
scoring requires separately reviewed methodology and validation; this document
does not approve one. Continue authoritative runtime/calendar/status and
controlled-launch policy gates in parallel. Do not wait for the scheduled
evidence horizon to do approved software engineering.

PIT stays **UNSUITABLE**, production **NOT_READY**; execution/notifications remain
disabled and live orders remain prohibited. This slice does not authorize
Paper Trading, broker integration, asset allocation or real-capital deployment.

## Verification

Full suite: **1140 passed / 6 skipped**, 23 more passing cases than the prior
slice. Ruff passes; mypy passes on 233 source/script files; governance passes
88 checks; `git diff --check` passes. These are local, not remote-CI/release
results. Final handoff is recorded in `PROJECT_STATUS.md`.
Regression coverage includes percent preservation, values above 100 where
valid, monetary/ratio separation, period/basis/scope rejection, unsupported
ROE definitions, future visibility, idempotent facts, tampered-row preservation,
old packet shapes/hashes and high-score-evidence bypass prevention.
