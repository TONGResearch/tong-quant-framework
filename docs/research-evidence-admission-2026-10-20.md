# Declared Research Evidence Admission

October 20, 2026 MYT. Work package `WP-LAUNCH-001`, still `ready`.
Framework `0.8.0`, schema `0.8.2`, migration head
`0010_portfolio_evidence_lineage` remain unchanged.

## Reproduced Risk

After the Financial-specific guard, Policy/Industry/Value still used the shared
evidence helper. It averaged every numeric module annotation regardless of
declared names. Missing required inputs only reduced confidence; unrelated
high-quality/high-score annotations could raise score and confidence, duplicate
names could count repeatedly, and booleans counted as numeric scores.
This was structural score contamination, not proof of actual trading harm.

Nineteen new regression scenarios ran against the old helper: eighteen failed
and existing future-data rejection passed. Reproductions are synthetic fixture
annotations, not actual investment assessments.

## Repair

`research.base.evidence_driven_assessment` now revalidates context and admits
exactly one numeric observation for every declared scoring name. Empty rubrics,
missing names, duplicate names or boolean/text inputs return INSUFFICIENT_DATA,
no score and zero confidence. Invalid ranges, NaN and infinity fail closed.
No favorable fallback, guessed conversion or duplicate averaging is introduced.

Undeclared annotations are excluded from score and confidence but stay in
original evidence/ids for audit. Ignored/missing/ambiguous/unscorable names are
visible in features. Risks/limitations and latest annotation availability are
retained. Known inputs use deterministic name order; full report identity is
not claimed independent of every annotation order, nor are raw payloads or
caller quality labels authenticated by structural admission.

Direct `assessment_from_scores` paths used by Technical, Trend and Pattern
are unchanged. Financial stays unscored pending separate sector-policy
admission. Complete generic rubric averaging remains a research heuristic,
not a validated investment model or independent source-confidence measure.

Central versions identify new results:

- `declared-research-evidence-v1`.
- `policy-v0.5.1-evidence-admission`.
- `industry-v0.5.1-evidence-admission`.
- `value-v0.5.1-evidence-admission`.

Historical stored reports/annotations are not rewritten or requalified.
Database contracts/tables are unchanged.

## Integration Boundary

A temporary SQLite research queue omits one required Policy input and adds an
unrelated high score. The report/persisted assessment stay incomplete/unscored,
all five annotations remain, and InvestmentAssessment is INCOMPLETE with no
InvestmentScore. The complete original Policy fixture still works. This tests
existing builders, not every hypothetical manually forged report or a new
universal authorization gate.

No provider access or business database writes, real research runs, execution,
broker, orders, fills, paper ledger, portfolio, notification or asset-allocation
changes. No commit/push. Execution/notifications stay disabled, live orders
false, PIT UNSUITABLE and production NOT_READY.

## Remaining Work

Matching names and PRIMARY labels are not source authentication. Source truth,
original-run PIT provenance, rubric design, family correlation, calibrated
weights, direct calculated-score input gates and legacy-report audit remain
separate work. No scoring or data-readiness promotion follows from a complete
rubric. Continue bank definition/population, source/freshness/valuation and
runtime market-rule/policy gates in parallel with the evidence horizon.

Verification: **1207 passed / 6 skipped**, 41.66 seconds, 24 new regression
cases; Ruff/mypy pass (234 source/script files), governance passes 91 checks,
and whitespace checks pass. Final targeted governance/research/persistence
checks pass 163 cases. The handoff is recorded in `PROJECT_STATUS.md`.
Local success is not remote CI, installed release,
independent-host recovery or live acceptance.
