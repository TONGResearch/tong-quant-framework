# Explicit Native/Manual Financial Candidate Review

## Delivered Scope

WP-LAUNCH-001, exploratory read-only HK/MY slice. The existing
`scripts/inspect_global_technical.py` accepts repeated
`--review-native-pair row_key=native_metric` with both `--fundamentals` /
`--sector-profile` and explicit reviewed-filing options. No pair is inferred.
Default output without candidate arguments remains unchanged.

Exact retained readers still own source/artifact/batch verification and current
parent selection. Candidate review additionally checks receipt hashes, versions,
identity, actual UTC cutoff/capture chronology and disabled authority flags.
Checksums are consistency checks, not authentication. The returned review binds
both receipt hashes, the explicit candidates and every diagnostic. The existing
combined hash also binds this optional review. No new database writes or schema.

For each explicit manual row/native metric, retain exact end-label candidates,
native and manual amounts, native labels, pages, scope, units and periods. Missing,
unresolved, ambiguous or unusable inputs stay visible. A latest bad native metric
cannot select an older usable metric; exact requested periods cannot substitute
another year. Multiple candidate interpretations remain alternatives, not votes.
No nearest-number matching, alias, default mapping, tolerance, FX, subtraction,
equality verdict or independent-provider consistency score is introduced.

The output is `CANDIDATE_REVIEW_ONLY`, never an admitted accounting mapping.
Unknown native flow start, unit, consolidation/attribution, source precision,
revision/publication, issuer binding and independent corroboration remain
explicit blockers. Bank-only scope and later-edition comparatives add their own
warnings. Candidate generation does not resolve any blocker or authorize a score.

## Real Retained Evidence

Both samples use the actual already-recorded local evidence at
`2026-10-28T05:14:00+00:00`. This is historical diagnostic reconstruction, not a
current quote/filing refresh. Two runs each have identical output and preserve
both database byte hashes. Separate databases share a cutoff, not an atomic
cross-database snapshot. Manual amounts below are unqualified scale conversions;
the Yahoo raw unit/definition remains unverified, so these are NOT consistency
judgments or comparable financial facts.

| Subject | Explicit manual candidate | Manual native amount / scale | Yahoo native field / raw value |
|---|---|---|---|
| 0700.HK | Group revenues 2025 | CNY 751766 million | annualTotalRevenue / 751766000000.0 |
| 0700.HK | Group total profit 2025 | CNY 229801 million | annualNetIncome / 224842000000.0 |
| 0700.HK | Group parent-attributable profit 2025 | CNY 224842 million | annualNetIncome / 224842000000.0 |
| 0700.HK | 2024 parent profit in 2025 comparative column | CNY 194073 million | annualNetIncome / 194073000000.0 |
| 1155.KL | Group operating revenue 2025 | MYR 66369 million | annualTotalRevenue / 27863232000.0 |
| 1155.KL | Group net operating income 2025 | MYR 30380 million | annualTotalRevenue / 27863232000.0 |
| 1155.KL | Group attributable profit 2025 | MYR 10514 million | annualNetIncome / 10513948000.0 |
| 1155.KL | Bank-only attributable profit 2025 | MYR 10112 million | annualNetIncome / 10513948000.0 |

Tencent's displayed parent-profit amounts resemble the provider values, but total
profit is a different labelled concept. Maybank's two income labels both differ
from the provider raw value; that is an unresolved accounting-definition issue,
not established provider corruption or a parsing defect. Its rounded summary
cannot justify invented exact precision or a tolerance picked after observation.
Do not force-match by choosing whichever line is closest. Group/Bank selection,
net/gross banking revenue and profit attribution require source-bound review.

Candidate review hashes (same order of arguments as table):

- 0700.HK: `b02c5e1cf36713aec64c502b6ccb67f0d96c11870fb1974319b27f4aef8185a2`
- 1155.KL: `5d84a33af095b582872dbb24bc6ba9a3f643650acb9eff4d6da47a5a4942311e`

Existing price/native database SHA-256:
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
Existing primary-document/review database SHA-256:
`899f4c282eac3d41acc8bc0863cfd712a6c89389a2972de1425bab1ed5ce3de6`.
Ignored databases/raw artifacts still require approved encrypted co-retention;
Git history alone cannot reconstruct them. No commit or push in this slice.

## Reproduction

Use the existing CLI options documented in
`docs/global-review-display-2026-10-28.md`, add `--fundamentals` and the explicit
context-only sector profile, then repeat the candidate arguments below.
The CLI intentionally exits 2 for exploratory results, not validation acceptance.

Tencent candidates:

```text
--review-native-pair group_revenues_2025=annualTotalRevenue
--review-native-pair group_total_profit_2025=annualNetIncome
--review-native-pair group_parent_profit_2025=annualNetIncome
--review-native-pair group_parent_profit_2024_comparative=annualNetIncome
```

Maybank candidates:

```text
--review-native-pair group_operating_revenue_2025=annualTotalRevenue
--review-native-pair group_net_operating_income_2025=annualTotalRevenue
--review-native-pair group_attributable_profit_2025=annualNetIncome
--review-native-pair bank_attributable_profit_2025=annualNetIncome
```

## Acceptance And Next Work

Tests cover equal amounts with incompatible definitions, competing candidates,
currency/period mismatch, missing and unresolved inputs, duplicate/native unknown
periods, latest unusable metric, comparative/standalone warnings, mutated or future
receipts, equivalent timezone instants, deterministic hashes, CLI restrictions,
exact real-reader integration and unchanged SQLite bytes.

Full verification: **2676 passed, 6 skipped** in 113.04 seconds; 44 new cases.
Ruff passes; mypy reports no issues in 290 source files. All 133 governance checks,
scoped forbidden-import inspection and `git diff --check` pass. Six real network
tests remain opt-in/skipped; retained-data reproduction is not a network probe.

Next bounded accounting task: review native banking income definitions against
exact statement lines/notes, retain rejected alternatives, and define an explicit
versioned sector/metric policy before scoring. Do not try additional lines solely
to make numbers match. Then populate actual Discovery/Hard Screening/Research
Queue inputs for official research and pre-registered technical-plus-fundamental
validation, not synthetic candidates or retrospective rules fitted to these values.

R1-R6 remain partial, WP-LAUNCH-001 ready/not accepted, PIT `UNSUITABLE`, production
`NOT_READY`, execution and notifications disabled. This step does not resolve
independent data trust, freshness, historical continuity or strategy effectiveness.
No Paper, Broker, Order, Execution, Portfolio or Notification code was changed.
