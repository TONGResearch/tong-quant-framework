# US SEC Exact-Period Inputs

Date: November 6, 2026, Malaysia time. WP-LAUNCH-001, US-first U2 input-contract
slice only. Not admitted financial research, an official report or validation.

## Contract

`data.sec_period_inputs.SECPeriodSelection` is an immutable native tag plus an
explicit start/end date, or a separate instant end date. `read_sec_period_inputs`
uses the existing byte/registry/batch/parent-verified SEC body reader at one SQL
snapshot and cutoff. It returns exact native matching occurrences with source
hashes, parent filing labels, actual captures and unsupported-context counts.
No canonical facts, ResearchReport model, financial alias or database schema is
added. Source normalizers, old receipts and existing output versions stay intact.

Selections use whole calendar dates, never FY, frame, 12M, form or a 365-day
shortcut. 52/53-week date ranges can be observed without labeling them annual;
inclusive day counts are calendar days, not exchange sessions or holding periods.
An instant balance cannot match a flow duration. No nearby-period fallback,
calendar-YTD substitution, annualization, TTM, FX or growth percentage is computed.
Requested dates after the cutoff or filing report-end label are separately
blocked, not shifted to a more favorable observed period.

Exact matching supported occurrences remain separate. Repeated numbers are not
summed or averaged; differing supported values become NUMERIC_CONFLICT and a
matching unsupported occurrence blocks numeric agreement. Unsupported facts
without enough context remain visible as unresolved indices and source counts.
OBSERVED_SUBSET_UNQUALIFIED describes only supported matching occurrences;
unknown contexts prevent any completeness or accounting-qualification claim.
Missing requested contexts do not prove issuer-wide nondisclosure or zero.

Sector is explicit nonfinancial/bank/securities/insurance/unknown context, not a
verified classification or methodology. No ordinary-company cash-flow health
rules are applied to financial firms. All identity/accounting/financial-score/
investment-score/replay/validation/execution flags remain false; LOW trust,
retrieval_time precision and UNASSESSED freshness remain unchanged.

## Optional Entry

The existing global technical CLI accepts repeated `--sec-period` only with
explicit US read-only SEC options and `--fundamentals --sector-profile`.
The latter preserves independent Yahoo missing/failed states; it is not required
to provide usable Yahoo numbers or justify any cross-provider mapping.

Syntax is `NativeTag=START/END` or `NativeTag=@END`. Up to sixteen unique strict
selections are supported; date spelling, order, duplicates and size are checked
before database access. Equivalent selection order is canonicalized, but raw
source occurrences and native labels are not changed.

For the retained historical MSFT example in the delivery plan, append:

```sh
--fundamentals --sector-profile nonfinancial \
--sec-period NetIncomeLoss=2024-07-01/2025-06-30 \
--sec-period NetIncomeLoss=2025-07-01/2026-06-30
```

Only this option uses `US_SEC_PERIOD_DISPLAY_VERSION` v3. The previous no-SEC,
SEC v1 and optional issuer-declaration v2 paths retain their versions/output.
The period reader and other SEC reads share the SEC SQL snapshot; a separate
price database shares only the cutoff, not cross-database atomicity. Original
files are still independently checked, not part of a cross-store transaction.
Exit 2 remains deliberately unqualified diagnostic output, not a crash or pass.

## Real Retained Evidence

Historical cutoff: `2026-10-27T15:25:57.208239+00:00`. Same retained issuer CIK
0000789019 and accession 0001193125-26-323660; this is not current market data.
Six explicit contexts request 2024-07-01/2025-06-30 and 2025-07-01/2026-06-30
for RevenueFromContractWithCustomerExcludingAssessedTax, NetIncomeLoss and
NetCashProvidedByUsedInOperatingActivities. All have supported observations;
matching occurrence counts in canonical order are 1, 1, 3, 3, 2, 2.

The source subset still has 67 unsupported facts, and four selected context
checks retain unresolved tag contexts. None is called complete or admitted.
Changing request order gives the same receipt and combined hash. Both sample
databases are unchanged, with no capture, initialization or migration.

- Period receipt hash:
  `3ae7cc1b5d1b6ae4a9fd234492d9069a3c5ee7443526efb0e6377f14f4c94db4`.
- Combined display hash:
  `77badfb717fc285f7e577fb121542f230964263d7faae3e7e4d441608f1c1292`.
- Previous SEC v1 combined hash remains exactly
  `1865f2f15955e4bffb5c9abb9707f1065b52041954d3b2803ed00cb1042cdab7`.

These hashes identify retained consistency only, not independent source truth or
publication history. Comparative numbers are the captured filing's presentation,
not original historical vintages. No new data or artifacts need publication.

## Verification And Next Admission Contract

Full pytest: **3435 passed / 6 skipped**, 208.66 seconds; 42 new cases. Ruff,
mypy (308 source/script files), governance (162 checks), git diff --check and
scoped import/security review pass. Coverage includes strict selectors, actual
UTC, duration/instant and 52/53-week dates, no annual/quarter inference,
signed/zero values, duplicates/conflicts/unsupported contexts, missing and latest
failed/tampered/future-completed sources, five sector contexts, read-only CLI
determinism and preservation of prior output paths. No forbidden imports were
found in the three touched runtime modules (47 imports). These are engineering
checks of the mixed worktree, not a release candidate, independent source review
or financial-methodology validation; six opt-in external-network tests remain
skipped. No real database changes, credentials, staging, commit or push.

Before financial scoring or the official real-candidate research chain, still
required: independently qualified ticker/share-class and filing identity,
statement/consolidation scope, issuer fiscal definition, current/comparative
column roles, revisions, publication/freshness, accounting and sector policy.
Native NetIncomeLoss is not automatically parent-attributable profit; native
operating cash flow is not FCF, and a bank cannot inherit a generic cash-flow
rule. Valuation additionally needs qualified price/share-class/action/earnings
bases. This slice approves none of those definitions, weights or thresholds.

Next implement the reviewed source/period/sector evidence binding into the
existing Financial Research contract and real screened research path; do not
invent a queue or another ResearchReport. Then execute the separately admitted
validation protocol. Full technical and deployment gaps remain in the US plan.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled persist.
No Paper, Broker, Order, Portfolio, Notification, schema or live-code change;
no commit or push and no release-candidate qualification.
