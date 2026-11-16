# Source-Bound Bank Income Transcription And Arithmetic

## Delivery

WP-LAUNCH-001, HK/MY exploratory financial-input slice. Added optional repeated
`--review-income-sum result=component+component` to the existing global technical
CLI. The sum uses explicit signed transcribed amounts; it never infers an expense
sign, coefficient, omitted zero, tolerance or FX conversion. This is a consistency
check on manual transcription, NOT accounting/source verification or a scoring
policy. No new ResearchReport, provider, schema, canonical facts or trading layer.

Exact retained manual-reader receipts and one requested cutoff bind these checks.
The existing receipt guard rechecks hash, version, identity, UTC chronology and
disabled authority. Parsing the original strict review model and reproducing
all its observations prevents detached/mutated numeric annotations. Source/PDF
verification remains the responsibility of the exact reader, not the checksum.
Inputs are same-income-statement, scope, flow period, column, currency, original
unit/unit label and restatement label. Mismatches, unresolved or missing rows
remain visible with null residuals. Decimal residuals are exact and never rounded.
No combination of successful sums can approve financial or investment scoring.

## Real Maybank Review

Source: retained official-host PDF, physical page 31 / printed page 29 income
statements; page 144 / printed 142 Note 35; page 5 / printed 3 rounded summary.
The local PDF was hash-checked against the current retained source before visual
inspection. This is one manual review, not independent verification or production
PDF extraction. All reported amounts below are as transcribed in this document.

Note 35 describes Group revenue across banking, Islamic Banking Scheme, finance,
insurance/takaful and other activities excluding related-company transactions.
The Bank description includes gross interest, fees, commission, investment,
dividends and other banking/finance income. Neither definition can be inferred
from the name `annualTotalRevenue`; the Yahoo raw annual field remains unmapped.

The new plan `config/global-document-reviews/maybank-2025-income.toml` retains
15 native statement rows in MYR thousands, including signed interest expense and
insurance investment/finance result. Group and Bank columns remain distinct;
parent-attributable profit is not total profit. Only supported explicit monetary
cells were transcribed; dash cells, per-share values and ratios were not made zero.

Four explicitly requested checks in original MYR-thousand units:

| Declared result | Signed components | Result / residual |
|---|---|---|
| Group net interest income | 29,351,194 + (-16,194,182) | 13,157,012 / 0 |
| Group total operating income | 13,157,012 + 8,653,273 + 1,755,748 + 9,019,554 | 32,585,587 / 0 |
| Group net operating income | 32,585,587 + (-2,206,086) | 30,379,501 / 0 |
| Group total profit | 10,513,948 + 317,400 | 10,831,348 / 0 |

These are `ARITHMETIC_AGREES_AS_TRANSCRIBED`, not verified business results,
independent provider agreement, sector admission or an investment judgment.
The statement's Group parent-attributable profit scales to the displayed Yahoo
raw value, but raw-unit/definition/identity/publication/revision blockers remain.
The Yahoo annual revenue value still differs from both issuer income labels;
do not reverse-engineer a formula merely to match its number.

### Same-Document Discrepancy

Bank (not Group) 2025 operating revenue is shown as **34,028 million** in the
rounded summary, while the income statement AND Note 35 show **34,208,230
thousand**. Visual review confirms those are the displayed entries. They must
not be treated as ordinary million-unit rounding or silently corrected. A typo,
edition/context difference or other explanation is not established. This is an
unresolved within-document issue, not independent provider calibration evidence.
Do not use that Bank revenue for scoring until separately resolved. The previous
summary review did not transcribe this particular Bank revenue cell; no existing
stored row is being silently corrected or relabelled.

## Persistence And Reproduction

Reviewed-at annotation: `2026-10-28T15:20:53+00:00`.
Actual new recording: `2026-10-28T15:23:26.503226+00:00`; no backdating.
New evidence: `4739845c6c1e4e4aee8053d801785662a93f32ee8dcd21f5d322b17582b090b2`.
Envelope SHA-256: `588fc0eadfd75677858dcf789e46999b4a78d36fdfa90c6c007ef38d58c8685c`.
PDF SHA-256 remains `2fc421fac71b9f5a9c3063709662a265b9c1fe3c7e29ea842ff2c78eaf041c55`.

Append-only evidence uses the existing neutral transaction and no canonical
callback. Local document database now has five records/artifacts/batches, with
zero fundamental facts, research reports or signals. Old two PDF captures and
both prior four-row reviews remain intact. The older Maybank receipt at
`2026-10-28T05:14:00+00:00` is unchanged:
`a8e3d5d37ea07351120b33159c34c0ae737a225bfa88c7b28343aac561b5aed7`.
At a new cutoff, current reads select the new 15-row review, not an automatic
merge with old summary rows. Old missing keys must not fall back across editions.

New database SHA-256:
`81a136c9344ba4c8c44625e809e02c9ae2a70137b3a602ceabe75a26cb8b28bb`.
Previous database hash `899f4c282eac3d41acc8bc0863cfd712a6c89389a2972de1425bab1ed5ce3de6`
is historical, not the current recovery baseline. Price/native database remains
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
Both hashes are unchanged by the subsequent read-only diagnostic runs.
New ignored raw/database evidence needs approved encrypted co-retention; Git does
not back it up. No commit or push performed.

Two identical CLI runs at `2026-10-28T15:23:27+00:00` bind all four sums and three
explicit native candidate questions (Group statement operating revenue / net
operating income to annualTotalRevenue, parent profit to annualNetIncome):

- Manual input hash: `529ceb19110a4857c5246d6bfc6d50548773de13d012223f38ea42c236cf9d74`.
- Arithmetic review hash: `e6e8b6b0d5e29c2f9cbf98ef1ee85e757db87e0bbd1f0add7edb625162309c98`.
- Combined hash: `897c8e2df36f166c2db2f8f007c937a202d8eef5b2dde0b3b273d817b1f64a30`.

Existing CLI options are in `docs/global-review-display-2026-10-28.md`. Use the
new cutoff and add these explicit sum arguments, retaining the order:

```text
--review-income-sum group_net_interest_income_2025=group_interest_income_2025+group_interest_expense_2025
--review-income-sum group_total_operating_income_2025=group_net_interest_income_2025+group_islamic_income_2025+group_insurance_service_2025+group_other_operating_income_2025
--review-income-sum group_net_operating_income_detail_2025=group_total_operating_income_2025+group_insurance_finance_2025
--review-income-sum group_total_profit_detail_2025=group_parent_profit_detail_2025+group_nci_profit_2025
```

The tool exits 2 for exploratory output. No new provider network capture occurred;
this does not establish current availability, historical publication or PIT data.
Default CLI output without the new option is unchanged. No data was rewritten.

## Verification And Next Boundary

Tests cover signed sums, exact small residuals, missing/unresolved cells, scope,
currency, units, column/period/restatement mismatch, invalid identities, receipt
mutation/chronology, deterministic same-instant output and SQLite read immutability.

Full tests: **2705 passed / 6 skipped** in 103.96 seconds; 29 added cases.
Ruff passes, mypy passes across 290 source files, all 134 governance checks and
`git diff --check` pass. Scoped changed-runtime imports do not depend on Paper,
Broker, Order, Execution, Portfolio or Notification. Six opt-in network tests
remain skipped; the local reproduction is separate from those tests.

Next: separately reviewed source-defined bank metric/sector policy and actual
screened Research Queue inputs, followed by pre-registered technical-plus-financial
validation. Yahoo alias completion is not a requirement to keep developing primary
statement research; no guessed alias or unapproved policy may bypass admission.
Primary-source values still need issuer mapping, independent qualification,
freshness and revision/continuity evidence. The summary/statement issue remains
an explicit unresolved risk rather than an excuse to select a convenient figure.

R1-R6 partial, WP-LAUNCH-001 ready/not accepted, PIT `UNSUITABLE`, production
`NOT_READY`, execution/notifications disabled. No Paper, Broker, Order, Portfolio,
Execution, Notification, live trading or allocation implementation changes.
