# Financial Scoring Admission Repair

Date: October 19, 2026 MYT. Work package: `WP-LAUNCH-001`, still `ready`.

## Adoption Status

This repair is now applied to the primary PyCharm working tree after the tool
approval service recovered. All twelve target-file baselines, the patch hash
and read-only application check were verified before approval/application.
Previous permission failures and isolated checks remain preparation history,
not the current adoption state. No staging, commit, push, deployment or business
database write occurred. Primary-workspace checks were repeated below;
temporary-copy success alone is not installed-package or remote-CI acceptance.

Framework remains `0.8.0`, schema `0.8.2`, migration head
`0010_portfolio_evidence_lineage`. No schema or database data changes.

## Reproduced Defect

The old Financial module's no-score guard applied only if fundamental facts or
a financial receipt were present. Empty facts and no receipt selected the
legacy numerical-evidence averaging path instead. Six synthetic PRIMARY
annotations labelled with generic financial names produced a supportive score
and full confidence without an admitted source/sector policy. A single
unrelated numeric annotation could also produce a supportive financial score.
These were in-memory regression reproductions, not real issuer assessments.

## Bounded Repair

Remove the Financial module's legacy scoring branch. Until a separately
reviewed source-bound sector scoring policy is admitted, every new Financial
assessment returns `INSUFFICIENT_DATA`, `score=None`, confidence zero and an
explicit `financial_scoring_authorized=false`. This includes empty inputs,
evidence-only inputs, source-bound diagnostics, bank/nonfinancial/unknown
industries and caller-supplied self-authorization metadata.

Supplied evidence/ids, fact diagnostics, availability, source receipts and
descriptive comparisons remain available for research. They cannot authorize
themselves. No opt-in flag, permissive fallback, fabricated policy or new
investment scoring implementation is introduced. No historical record is
deleted, rewritten or retrospectively reclassified.

The financial diagnostic version becomes
`financial-v0.5.5-scoring-admission`; packet/input versions and their existing
identities remain unchanged. Financial scoring remains a future decision-
support layer, not removed from Tong Quant's architecture.

## Report And Persistence Effects

The existing report builder already marks a report incomplete when a required
Financial assessment is insufficient. This also holds when Value Research
requests Financial as a dependency. The existing InvestmentAssessment builder
then returns INCOMPLETE with no InvestmentScore. Regression tests verify both
routes; they do not claim every hypothetical directly constructed report is
independently authorized. SQLite tests preserve evidence and explicit no-score
features in an incomplete persisted research report.

No execution, broker, paper ledger, portfolio, notification, order, live
trading or asset-allocation code changes. All live capabilities remain disabled.

## Verification And Remaining Risks

Nineteen newly added regression cases failed against the old isolated source
before the repair, then passed with it. One additional persistence case covers
evidence-only inputs. The test-import location was checked explicitly, and the
full-suite environment pins the isolated source for child processes as well.
Final full-suite and static-check results are recorded with the patch handoff.

Isolated full suite: **1160 passed / 6 skipped**, 49.28 seconds; 20 additional
cases relative to the primary source's last 1140-pass baseline. Ruff and mypy
pass (233 source/script files); governance passes 89 checks. The patch must
also passed whitespace and application checks against its exact primary-source
base before adoption. These isolated results are not substituted for the new
primary-workspace verification.

Primary PyCharm full suite: **1160 passed / 6 skipped**, 50.72 seconds. Ruff
and mypy pass on 233 source/script files, governance passes 89 checks and
`git diff --check` passes. Runtime import was verified under the primary
project's `src`, with the new financial version. Neither test success nor
normal approval authorizes deployment, financial scoring, PIT or live trading.

Before/after main-file SHA256 values are unchanged:

- Operational database:
  `e95d04db1d09764da7537d796f7d202b813436e7b1d7d196a0eadf5e69aaf2ed`.
- Exploratory database:
  `26ab9455a80cc25b8aed0e7853aa9740a0d8feae42331a01ca7414c108e09b90`.

These are main-file byte identities, not WAL-aware logical-content verification
or a new encrypted restore drill. No business ingestion or real research run
was performed. Database/artifact/cache paths remain ignored, nothing is staged,
and no commit or push occurred. New local source changes still require separate
review/commit and current encrypted retention; old backups are not made current
by adopting code.

This repair closes financial use of arbitrary annotation averages. Other
modules still use the shared evidence-scoring helper, whose required-name
filtering and caller quality labels need separate review before any global
semantic change. Old stored reports need explicit provenance review. No scored
bank policy, freshness policy, issuer-history completeness, independent trust
or original revision evidence is created here. Source-bound LOW observations
remain LOW; PIT stays UNSUITABLE, production NOT_READY.

Next: implement the separate bank research-input/gap policy, not numerical
scoring or live trading. Preserve capture age versus financial-period age, explicit ratio/
annualization/scope semantics and missing/rejected/unsupported distinctions.
