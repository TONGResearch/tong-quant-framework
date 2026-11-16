# Bank Research Input And Freshness Diagnostics

Work package: `WP-LAUNCH-001`, still `ready`. October 19, 2026 MYT.
Framework/schema/migration remain `0.8.0` / `0.8.2` /
`0010_portfolio_evidence_lineage`. This is research-input engineering, not a
financial scoring methodology, stock recommendation or launch acceptance.

## Boundary

`ReviewedFinancialInputReader` -> immutable `FinancialInputSnapshot` -> pure
`research.financial.inputs.assess_bank_inputs` -> Financial research diagnostics
or read-only CLI export. No provider SDK imports, database writes, broker,
execution, portfolio, notification or paper-ledger changes.

Scope is explicitly China-A group-bank financial inputs. Other markets/sectors
do not silently inherit this policy. Financial module output remains unscored
and incomplete, including evidence-only inputs and self-authorization metadata.

## Input Contract

Nine named requirements are grouped into earnings, asset quality, profitability,
capital and liquidity. Revenue and parent-attributable profit require CNY
absolute amounts and calendar-year YTD flows. The two supported asset-quality
ratios require group/current-period-end percentages with no currency. Named
weighted YTD nonannualized ROE, YTD net interest margin, core tier-1 capital,
capital adequacy and liquidity coverage remain separate definitions. They must
not be aliased to generic ROE or mixed with parent-only regulatory tables.

The requirements are a versioned diagnostic baseline, not proof of a complete
bank checklist or admission of unsupported extraction contracts. Some future
ratio definitions cannot yet be reconstructed by the source adapter; keep
missing/unsupported outcomes until their units, annualization, consolidation
and periods are independently reviewed. Valuation needs separate dated
price/book/share/action inputs and remains outside this financial-input slice.

Each requirement returns one of NOT_REQUESTED, MISSING, REJECTED, UNSUPPORTED,
AMBIGUOUS, SEMANTIC_MISMATCH, PERIOD_MISMATCH or OBSERVED_UNQUALIFIED.
Latest selection uses visible report period, availability and revision, not
input order or favorable value. Duplicate latest observations are ambiguous.
A rejected/unsupported latest input cannot fall back to older favorable data.
Original observations remain in the receipt; this is not deletion/quarantine.

An explicit target period must be a visible calendar-quarter end. Otherwise
the target is labelled `latest_visible_required_metric`; it does not prove
that the latest issuer report or every revision has been captured. Current
source-column, definition, units, YTD/point basis and target period must match.

## Freshness Is Separate

`research.financial.maximum_report_age_days` is wired through effective Settings
and the existing research factory. Default **0** means UNASSESSED, not unlimited
freshness, not zero-day expiry and not PASS. Positive operator-configured limits
produce WITHIN_CONFIGURED_LIMIT or STALE, separately from source-binding status.
An age limit is not qualified merely because it is configured.

Age is calendar days from the financial period end to the snapshot's decision
date in Asia/Shanghai, not days since download or review and not today's age substituted
into a historical request. A within-limit observation remains unqualified for
scoring. Trust and availability precision remain separate reported values;
none is averaged upward or promoted by an age check.

Equivalent timestamp instants in different timezones produce the same age and
assessment hash; the China calendar timezone is explicit in policy identity.
Policy hash binds the exact requirement definitions, version and age setting.
Assessment hash binds the input receipt hash, policy, cutoff, target semantics
and all per-metric results/observation hashes. Versions:

- Policy/assessment: `bank-financial-inputs-v1`.
- Financial diagnostics: `financial-v0.5.6-bank-input-diagnostics`.
- Existing source packets and financial input receipt version are unchanged.

Changing effective Settings changes configuration identity. Existing validation
hashes/reports cannot silently inherit new settings or authorize this policy.
No data-completeness percentage or InvestmentScore is generated.

## Real Read-Only Sample

Existing exploratory database `data/processed/exploratory-pilot-20261016.sqlite3`;
600000, group bank, cutoff `2026-10-19T15:36:42.950586+00:00`.
The new ignored local export is
`data/processed/financial-reviews/bank-requirements-final-20261019.json`.
The earlier export without explicit calendar-timezone policy identity is
retained separately as a superseded local intermediate, not overwritten.

- Input hash:
  `91e8fc892b13453d22449edd34d85d1f3c03661e32ce1686b05f177b068de7d3`.
- Default policy hash:
  `603ba41bf20ead800f04bf0c171329dd93ae15e184c94823b289aab748c8abd0`.
- Assessment hash:
  `c5fb7f5ec925581f6e75a1065ab50fd518abfbc1d663fb33e33956ed5cb712b5`.

The query reconstructs six source-bound LOW/retrieval-time observations for
four metric names (two YTD metrics also have comparative observations).
Four current checks are OBSERVED_UNQUALIFIED and five named metrics are MISSING
from the canonical query. Missing does not prove the issuer never disclosed
the item. The latest visible required period is March 31, 2026; its age is
202 calendar days at this cutoff. All freshness results are UNASSESSED under
the unconfigured default. No source trust, score, validation or PIT promotion.

Read-only CLI options: `--bank-inputs`, optional
`--bank-max-report-age-days` and `--bank-target-period`. Query metrics remain
explicit; omitted policy metrics produce NOT_REQUESTED, not false coverage.
Bank-only options without `--bank-inputs` and wrong market/sector fail closed.
Exports are new-only, credential screened and mode 0600. Exit 2 is intentional:
even source-bound observations remain partial diagnostics, not ready research.

No canonical facts, reports or provider artifacts were added. Existing fact/
provider/artifact counts remain eight / 13,228 / eleven. No real ResearchReport
or ValidationReport was generated. Operational/exploratory main-file hashes
before and after this slice remain:

- `e95d04db1d09764da7537d796f7d202b813436e7b1d7d196a0eadf5e69aaf2ed`.
- `26ab9455a80cc25b8aed0e7853aa9740a0d8feae42331a01ca7414c108e09b90`.

These are main-file identities, not WAL-aware content or encrypted recovery
verification. New local diagnostics/code are not automatically in the earlier
encrypted snapshot or on GitHub. No commit/push occurred.

## Remaining Work

Independently review and populate named profitability, group capital/liquidity,
freshness and valuation contracts; extend beyond one issuer and report period.
Financial evidence alone does not implement the user's broader Survival/Cycle/
Valuation/Growth or improved Turtle strategy. Policy, industry, macro, technical
and regime evidence remain separate research variables; source diagnostics
cannot approve any of them or a trade.

Current code is not a validated buy/sell engine. Assistant-led stock research
can proceed using current, attributed sources and explicit conditions while
software engineering continues, but must not be presented as a qualified
Tong Quant model result. No exact future price/time or execution is guaranteed.
PIT stays UNSUITABLE, production NOT_READY; live capabilities stay disabled.

Verification: **1183 passed / 6 skipped**, 45.64 seconds, 23 new regression
cases; Ruff and mypy pass on 234 source/script files, governance passes 90
checks, and `git diff --check` passes. The final real assessment hash was
reconstructed again under the final code; no later overwrite or database
population was used. Final handoff is recorded in `PROJECT_STATUS.md`.
No release, remote CI, historical completeness or live authorization is implied.
