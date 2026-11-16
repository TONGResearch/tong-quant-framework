# US SEC Period Inputs In Official Research

Date: November 6, 2026, Malaysia time. WP-LAUNCH-001 remains ready, not accepted.
This implements an unqualified input-to-report contract, not source/sector
methodology admission, real candidate selection or strategy validation.

## Architecture And Contracts

```text
Retained SEC bytes/catalog/concept evidence
  -> read_sec_period_inputs (unchanged native period receipt)
  -> SECPeriodResearchInput (immutable copied receipt + requested symbol/sector)
  -> existing ResearchContext.validate
  -> existing FinancialResearchModule assessment features
  -> single official ResearchReport + existing atomic SQLite repository
  -> existing report reconstruction with identical retained features
```

`SECPeriodResearchInput` lives with the period contract in data.sec_period_inputs;
the factory is `read_sec_period_research_input`. No second research report or
provider, domain fact, table, migration or capture pathway is introduced.
The copied canonical JSON is bounded to 2 MiB. Oversized inputs are rejected,
never truncated or silently qualified. Version, receipt hash, false authority,
LOW/retrieval_time/UNASSESSED labels, actual UTC cutoffs and parent/capture pins
are revalidated. Matching native rows retain exact entity/tag/period/USD context;
derived statuses, occurrence indices, supported amounts, duplicate/conflict and
unresolved-context constraints are checked again before use.

The public checksum and copied receipt are not authentication or a fresh source
read. Reconstruct inputs for a new cutoff; do not retimestamp an old receipt.
Explicit requested symbol is caller-selected, not proof that the CIK/accession
belongs to that security/share class. All issuer, accounting, score, replay,
validation and execution authority remains false, including recomputed checksums.

The ResearchContext slot is optional and appended to preserve prior positional
constructors. It requires a US Equity and no parallel FinancialInputSnapshot.
Other native/manual/ratio inputs must agree on the requested sector and common
cutoff; their observations stay separate, not merged, aliased, cross-calibrated
or substituted for one another. No bank/nonfinancial policy is inferred.
Context validation runs at construction, direct module evaluation and before
ResearchEngine.start_run; mutated input must fail before repository writes.

## Report And Version Behavior

- `SEC_PERIOD_RESEARCH_INPUT_VERSION`: sec-period-research-input-v1.
- Financial model: financial-v0.5.22-sec-period-inputs. Previous stored model
  versions and reports remain intact; no historical result is requalified.
- Existing SEC source/period/CLI v1/v2/v3 versions and hashes are unchanged.
- Framework 0.8.0, schema 0.8.3 / 0011_refresh_ledger remain unchanged.

Financial assessment features retain the complete receipt, binding hash/version,
requested symbol/sector, source receipt hash/status, unsupported count and false
scoring/identity flags. Missing/failure/unsupported/conflicting states persist.
Assessment availability includes the receipt's exact read cutoff, even when
older facts exist or source data is unavailable. Same wall-clock labels across
DST folds cannot substitute for equal actual instants.

Financial stays INSUFFICIENT_DATA, unscored with confidence zero until separately
admitted policy exists. Technical findings cannot override this condition. The
combined test reports stay INCOMPLETE and produce no InvestmentScore; retained
report reconstruction must preserve that state. No queue is fabricated for
actual captures; integration fixtures are explicitly synthetic contract tests.

## Retained Real Input Exercise

The existing historical MSFT sample at 2026-10-27T15:25:57.208239+00:00 builds a
repeatable immutable input binding for the same six native contexts, preserving
67 unsupported facts and the original unknown contexts. No real Research Queue
or ResearchReport is created. Database bytes stay unchanged; no network request,
initialization, migration, credentials, raw source logs or real-data write occurs.

- Source period receipt hash remains
  `3ae7cc1b5d1b6ae4a9fd234492d9069a3c5ee7443526efb0e6377f14f4c94db4`.
- Requested MSFT/nonfinancial binding hash:
  `58d4178ea9223d2987078de104591cc4c56fc29f7e293667514904b72ad71fac`.

The binding is structural evidence only. It is not a current-source review,
verified equity identity, original historical vintage or a qualified investment.

## Verification And Remaining Work

Full pytest: **3502 passed / 6 skipped**, 216.00 seconds, including 67 new cases.
Ruff, mypy (308 source/script files), governance (163 checks), git diff --check
and scoped security/import review pass. Four changed runtime modules contain no
execution/broker/order/trade/fill/paper/portfolio/notification imports (52 imports
reviewed). These are current mixed-worktree checks, not an exact release candidate
or independent source/financial validation; six opt-in network tests stay skipped.

Tests cover copied receipts,
recomputed-checksum attacks on authority/trust/time/unit/entity/period/amount/
derived statuses, source failures, caller mutation before writes, US/equity/
sector/parallel-input bounds, actual UTC/DST and availability with old facts.
Synthetic SQLite cases combine Technical and Financial research for five sector
contexts and observed/missing/failed/tampered/conflicting sources, reconstruct
the official reports and verify absent scores and canonical financial facts.

Next prioritize independently reviewed issuer/share-class, statement/fiscal/
consolidation/column/revision and sector definitions, then admit methodology
only through explicit review. Build the real Discovery/Hard Screening/Research
Queue chain and actual strategy validation; do not treat synthetic report tests
as those deliveries. Technical completeness, fresh sources and deployment/
encrypted recovery remain open. PIT UNSUITABLE, production NOT_READY and
execution/notifications disabled persist. No Paper/Broker/Order/Portfolio/
Notification/live changes, commit or push; mixed-worktree checks are not release
candidate acceptance or a four-market release.
