# Explicit Cross-Receipt Percentage Arithmetic

## Delivered Slice

WP-LAUNCH-001 adds an opt-in Financial research diagnostic over existing immutable
monetary and ratio inputs. It checks caller-proposed `numerator / denominator *
100` equations against an original reported percentage. It does not admit an
issuer formula, metric mapping, consolidation basis, rounding policy, source,
sector methodology, financial score or investment decision.

`ManualRatioIdentity` records explicit original row keys, decimal places,
half-even rounding and a rationale. `RatioArithmeticPlan` pins both review evidence
IDs/envelope hashes, the original PDF hash and plan availability. An explicit new
review edition requires new plan pins. Plans contain no numeric expectations,
health thresholds, weights, tolerances or automatic alias selection. Each ratio
key has one candidate equation per bounded plan; no favorable alternative search.

Existing exact readers -> distinct immutable monetary/ratio receipts -> explicit
pinned plan -> arithmetic diagnostic -> existing Financial features/report JSON
and SQLite reconstruction beside Technical. No new outcome model, data table,
migration, provider adapter or trading dependency. Financial version
`financial-v0.5.19-ratio-arithmetic`; arithmetic version
`global-original-ratio-arithmetic-v1`. Framework/schema remain 0.8.0 / 0.8.2 and
source receipt versions are unchanged.

## Context, Precision And Failure States

Both inputs must validate and have identical subject, market, document URL,
requested sector and actual UTC cutoff. Usable inputs must reference the same
original source evidence/envelope/PDF, source availability instant and report
period. Availability comparisons use actual UTC, not different textual timezone
labels. Plan availability cannot precede either pinned recording or follow the
decision cutoff. Latest source failures remain unusable; no older input fallback
or automatic plan rebinding is allowed. Read both sources within one existing
SQLite read snapshot for a new run; copied receipts are not live source rechecks.

Supported equations use an instant ratio and balance amounts with the same
original currency/unit/unit label, scope/date/column role/restatement annotation.
Full native labels, page/column contexts and notes remain attached. Group/date
agreement is only structural: financial and regulatory Group scope equivalence
is still unverified. Annual ROE and numerator/average-equity inference are not
supported. No implicit FX, monetary scaling, annualization or net/gross alias.

Each check preserves a distinct result: blocked source, missing reviewed row,
unsupported period basis, row-context mismatch, unresolved value, display-precision
mismatch, nonpositive denominator, arithmetic agreement or arithmetic residual.
Unresolved values never become zero. Original ratio precision must match the
explicit decimal-place declaration; a coarser tolerance cannot force agreement.

Python Fraction arithmetic preserves the exact quotient and residual as rational
numerator/denominator strings. Fraction's exact half-even rounding avoids decimal
double rounding; finite display conversion uses a local bounded precision. Exact
and rounded residuals are separate. Positive and negative ties are tested; ambient
Decimal precision cannot change the result. Half-even is an explicit diagnostic
choice, not an independently established issuer convention.

## Research Persistence

`FinancialResearchModule.ratio_arithmetic_plan` requires both input objects or
rejects instead of silently ignoring configuration. The existing Financial
assessment stores plan hash and full diagnostic JSON/hash. Existing HK/MY fixture
reports preserve observed, missing, failed and tampered cases through SQLite
reconstruction with Technical research. Financial remains unscored/confidence
zero, report INCOMPLETE, InvestmentScore absent. All formula/rounding/regulatory/
source/scoring/replay/validation/execution authorities remain false.

No new real queue/report is invented from exploratory sources. Arithmetic
agreement cannot close the draft bank plan's five ratio-policy questions or three
external dependencies. Numeric liquidity/current filing data, independent source
review, sector admission, historical validation and the earlier Bank revenue
summary/statement discrepancy remain unresolved.

## Real Retained Reproduction

Plan: `config/financial-reviews/maybank-2025-ratio-arithmetic.toml`.
Availability annotation: `2026-10-30T16:47:53+00:00`, not issuer publication.
At cutoff `2026-10-30T16:47:54+00:00`, two same-snapshot reads reproduce:

| Explicit candidate | Diagnostic display | Declared places | Result |
| --- | ---: | ---: | --- |
| Note 59 CET1 / Total RWA | 16.041% | 3 | Agrees as transcribed |
| Note 59 Total Capital / Total RWA | 19.960% | 3 | Agrees as transcribed |
| Note 12 Net impaired loans / Net loans | 0.79% | 2 | Agrees as transcribed |

All exact unrounded residuals are nonzero. Rounded display agreement does not
mean exact source equality, a verified formula or healthy bank fundamentals.
No numeric LCR, annual ROE formula, gross NPL or bank score is inferred.

- Monetary input hash: `a8570c25c9f8b8ee5e580a0b01a5f1c32f412d320686111d9319e98ad864dc0d`.
- Ratio input hash: `82c4a35aee731691b4cbf59a48f55e97ceb2bec8ae0130e25ade29906020a576`.
- Plan hash: `a86e8038dfed2ad040f2187b9f343e1668167eae2ecc40747a894a716308c789`.
- Review hash: `9ccae9aa59ff764c77985730548e60fcb9e26af41ebba20ffa0c5214439fb523`.

Both database byte hashes are unchanged. Document DB remains
`e7a694d2638c65676151716376ecc0a4d8dc6dda6c9ce0736cabb71e046c7528`, with
nine retained evidence records and zero canonical facts/reports/signals. Price/
native DB remains `0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
No new capture/ingestion or independent provider calibration occurred. Encrypted
co-retention of earlier ignored evidence is still required.

## Next Work And Boundaries

Next: source-qualified numerator/denominator/regulatory definitions and independent
review of the explicit candidates, separately dated liquidity/latest filings,
then admitted sector/source methodology and real screened research/validation.
Preserve a mismatching or unavailable equation, rather than choosing favorable
inputs. Matching arithmetic cannot replace strategy efficacy or data readiness.

No Portfolio, Notification, Paper, Broker, Order, Execution, live or allocation
implementation. No commit/push. PIT UNSUITABLE, production NOT_READY, disabled
defaults, R1-R6 partial and launch ready/not accepted remain unchanged.

## Verification

Final suite, including the source-availability UTC-equivalence regression:
**2932 passed / 6 skipped** in 128.78 seconds. Forty new arithmetic cases plus
expanded eight-case HK/MY official report storage coverage. Ruff passes, mypy
passes on 297 source files, all 141 governance checks and `git diff --check` pass.
Scoped runtime imports have no execution/broker/order/trade/fill/paper/portfolio/
notification dependencies. Plan credential-structure checks pass and database/
artifact/test-cache paths remain ignored. Six opt-in real-network tests stay
skipped; no current provider permission or independent source test is claimed.

Tests cover source/context/sector/cutoff/parent and stale-pin rejection; exact
currency/unit/scope/period/column/restatement/precision checks; unresolved/missing
rows, unsupported annual ROE, nonpositive denominators, residuals, bounded strict
plans, sensitive annotations, positive/negative half-even ties and ambient Decimal
precision independence. Equivalent source availability offsets compare in UTC.
Configured diagnostics require both receipts, preserve failed inputs, survive
report reconstruction and cannot produce InvestmentScore or canonical facts.
