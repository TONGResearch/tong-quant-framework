# Same-Filing Annual Income Comparatives

## Delivered Slice

WP-LAUNCH-001: preserved a new 22-row Maybank manual review containing all
previous 15 statement rows plus seven explicitly transcribed 2024 comparative
rows from the same 2025 filing. The retained PDF was hash-checked and its full
income-statement page visually reviewed (physical 31, printed 29). This remains
a single manual transcription, LOW / RETRIEVAL_TIME, not independent validation.

New source plan: `config/global-document-reviews/maybank-2025-income-comparatives.toml`.
New explicitly pinned draft bank plan:
`config/bank-document-input-plans/maybank-2025-comparatives.toml`.
Old source and bank plans are retained unchanged, not automatically rewritten.

The existing global CLI now accepts repeated
`--review-income-change current_row=prior_row`, only with reviewed filing inputs.
The existing Financial module accepts `manual_income_change_pairs` and stores
the descriptive review JSON/hash in existing report features. Configuring manual
diagnostics without a reviewed input object rejects instead of silently ignoring
the configuration. Financial stays unscored, confidence zero; combined reports
remain INCOMPLETE and cannot create an InvestmentScore.

## Strict Comparison, Limited Meaning

Pairs are explicit and bounded. Both observations must be usable income rows in
the same reviewed filing, with identical native label, consolidation scope,
currency, original unit/unit label and restatement annotation. Current and
comparative column roles must be correct. Exact matching full annual windows are
required, including supported noncalendar fiscal years; standalone quarter/YTD,
misaligned windows or ambiguous leap-day endpoints are not annualized or guessed.
All original row/column/page annotations remain visible.

Amounts change exactly in original source units. Percentages are descriptive,
rounded to four decimals with half-even rounding only when the prior value is
positive. Zero/negative prior values retain amount changes and an explicit
NONPOSITIVE_BASE with no percentage. Missing/conflicting/wrong-scope inputs stay
blocked without choosing another year or a favorable alternative.

These comparisons are as presented in one filing. They are NOT original 2024
vintages, reconciled restatements, verified business growth, independent provider
agreement, source/accounting admission, strategy validation or financial scores.
No canonical metric, FX, valuation multiple or trade decision is introduced.

Comparison model: `global-manual-income-changes-v1`.
Financial model: `financial-v0.5.17-manual-income-changes`.
Existing source packets and default CLI output without new options are unchanged.

## Real Retained Reproduction

Review annotation time: `2026-10-29T12:04:16+00:00`.
Actual recording: `2026-10-29T12:09:18.928534+00:00` (not backdated to 2024).
New evidence: `c07e95065b4d8c19949e60fd5c7affb2c612b6e84803a32f4f5462e663093ba0`.
Envelope SHA: `e2a650753b23e523f0ee25237d426d8d137050a3eb89ea2ddf2a043a5277953c`.
PDF SHA stays `2fc421fac71b9f5a9c3063709662a265b9c1fe3c7e29ea842ff2c78eaf041c55`.

New bank-plan availability annotation: `2026-10-29T12:09:19+00:00`, after its
pinned review recording. Local plan chronology is not authenticated publication.
The older `2026-10-29T11:50:26+00:00` manual receipt remains byte-equivalent in
canonical JSON with input hash
`25dcedea5a2974b7370245791adaf82a6970de9d1f3e41a6c227bd9df7ee0a35`.
At the new cutoff the old plan returns SOURCE_PLAN_BINDING_MISMATCH, not a merge
or favorable fallback. The new plan returns eight unqualified annotation matches,
five ratio contracts still required and four external evidence dependencies.
Closing a review-row gap does not close issuer/source or financial-policy gaps.

Two identical final CLI outputs at `2026-10-29T12:11:01+00:00` preserve both
database byte hashes. Seven source-specific annual pairs yield six descriptive
percentages and one nonpositive-base result. The parent-attributable profit pair
has a descriptive source-unit change of 425275 MYR-thousand and 4.2154%, not an
admitted investment conclusion. Raw output preserves all current/comparative
values and unqualified annotation context; no year is substituted automatically.

- New plan hash: `6c3e189373b40b24685bae2bf3bc4eba6b6927d8f0c288c6952042b165aa7cd2`.
- Input hash: `4aa54309f31a06aa37bc0de31868fdd26f1b5feec8efda2a2767219c2344ea2c`.
- Coverage hash: `56af9039b6c9d1a1e675c7058438d35dab48b592002e463d407155e14fffe0fb`.
- Change review hash: `70904d09758256fd78af90a4af73fb85eb33a23e7f4c62acd4c0bf31ab2f94e3`.
- Combined hash: `cefdb9fdf0f80e05f4a2800b38a0663a6651f52a048a7b48293d21f9fc765a6b`.

Local document database now has six evidence records/artifacts/completed batches
and zero canonical fundamental facts, ResearchReports or signals. Prior records
remain intact; synthetic persisted-report tests do not populate real candidates.
Current document database SHA is
`7e421d69bac246dbcf23476e14b9c3c554f8bde3c9d9703af62a00a037913831`.
Previous `81a136c9344ba4c8c44625e809e02c9ae2a70137b3a602ceabe75a26cb8b28bb` is
historical, not the current recovery baseline. Price/native database stays
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
New ignored data/artifacts still need approved encrypted co-retention; no backup
or cross-device restore claim is supported by this code-only checkpoint.

## Verification And Next Work

Synthetic tests cover annual/current/comparative roles, noncalendar fiscal years,
scope/currency/unit/name/restatement mismatches, incomplete windows, unresolved
values, nonpositive bases, missing rows, latest source failure, bounded explicit
pairs, deterministic hashes, CLI failures and official report reconstruction with
no investment score. Edition tests preserve old-cutoff reads and require new
review pins; copied receipts cannot turn new comparative data into old knowledge.

Full verification: **2787 passed / 6 skipped** in 124.34 seconds; 25 new cases.
Ruff passes, mypy passes on 292 source files, all 137 governance checks and
`git diff --check` pass. Scoped changed runtime imports have no broker, execution,
paper trading, portfolio or notification dependencies. Six opt-in provider
network tests remain skipped; no new provider capture was performed this slice.

Next: separately reviewed HK/MY capital, liquidity, asset-quality and profitability
ratio contracts, attributable equity/detailed valuation inputs, source/sector
admission and actual screened research plus preregistered validation. Do not widen
the China-only monetary/ratio contracts, resolve the known summary discrepancy by
choosing a convenient value, or infer a bank score from profitable annual changes.

No new provider/network request, schema migration, canonical population, Paper,
Broker, Order, Execution, Portfolio, Notification or allocation code. No commit
or push. R1-R6 partial, WP-LAUNCH-001 ready/not accepted, PIT UNSUITABLE,
production NOT_READY and execution/notifications disabled remain unchanged.
