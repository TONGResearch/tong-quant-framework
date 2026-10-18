# Research Bar Integrity And Launch Progress

## Repair Scope

WP-LAUNCH-001 input hardening only. Technical, Trend and A-share Pattern
research previously sorted visible rows but counted duplicate observations and
multiple revisions as separate daily bars. Direct calls also bypassed the
ResearchEngine's context recheck. Technical return indexing spanned N-1 rather
than N observation intervals; warm-up could ignore a longer short-MA setting
and lacked explicit return-window requirements. Invalid period settings could
reach empty slices and arithmetic errors.

The shared `research.bar_inputs.research_daily_bars` now:

- Revalidates candidate identity, visibility and context before consumption.
- Rejects mixed source labels, adjusted prices, nonfinite numeric inputs,
  active nonpositive prices and conflicting material content under one
  observation/availability version.
- Counts an observation timestamp once, choosing the latest visible version;
  identical capture retries do not add dates. Original context rows remain
  intact. A latest suspended version cannot fall back to an older active row.
- Rejects multiple observation timestamps on one UTC date instead of silently
  treating intraday bars as daily samples; this is a format boundary, not a
  verified exchange-session calendar.
- Returns sorted nonsuspended observations without deriving missing sessions.

Modules validate positive integer lookbacks. Trend rejects nonfinite/out-of-range
confirmation thresholds. Technical warm-up covers every configured moving
average/position window and the extra baseline required for N-interval returns.
The five-observation-interval proxy uses six observations, not five. Weekly,
monthly and 52-week labels remain daily-observation approximations.

Versions are centralized as `technical-v0.5.1-bar-integrity`,
`trend-v0.5.1-bar-integrity` and `pattern-china-a-v0.5.1-bar-integrity`.
No stored report is rewritten. The framework remains 0.8.0; schema remains
0.8.2 / migration 0010. No dependency, provider fetch, migration, Paper, broker,
portfolio, notification or execution implementation is introduced by this slice.
The four modified-Turtle confirmations remain mandatory informational research
variables; this repair does not make them trading instructions.

## Limits

Verification: 956 passed / 6 skipped; Ruff and mypy pass (224 source/script
files); governance passes 81 checks and whitespace checks pass. Fifty-one
new regression cases cover duplicate/revision warm-up, suspension revisions,
conflicting inputs, future-data rechecks, daily-series ambiguity, lookbacks,
thresholds, order-independent features and corrected return intervals.

Deduplication and version selection cannot prove source trust, correct units,
daily frequency, complete historical sessions, corporate-action coverage or
original-run consumption. Raw bars do not carry independent trust attestations.
Old reports require explicit new runs, not silent recalculation. ResearchContext
still contains caller-owned nested mutable data; pre-entry revalidation is not
a concurrent immutable snapshot. Numeric extreme/overflow stress beyond input
finite checks and authoritative session-aware return semantics remain open.
PIT remains UNSUITABLE and production NOT_READY; live execution remains disabled.

## Remaining Deliverable Groups

| Group | Current acceptance state | Remaining evidence or implementation |
|---|---|---|
| Trustworthy launch inputs | Partial | Reviewed status/phase, calendar, actions, price, account and validation-policy provenance; exact consumed-input binding |
| One real strategy chain | Not accepted | Canonical reviewed fundamentals, one frozen strategy specification, real Research/Score/Validation/Portfolio-risk artifacts, predefined OOS/cost/robustness criteria |
| Deterministic Paper workflow | Planned; launch dependency open | Persistent ledger, market rules, cost/fill simulation, idempotency, crash recovery, reconciliation and kill switch |
| Sandbox and deployment | Host research diagnostics partial; broker package planned | Reviewed clean commit, encrypted data-plus-artifact recovery, independent host, permitted sandbox/read-only API, reconnect and operational checks |
| Live rollout | Frozen; not authorized | Independent data/strategy/risk/operations acceptance, explicit capital/scope limits and separate human approval |

Planning estimates for a **single-market narrowed pilot**, measured as bounded
implementation/review work packages comparable to a productive development
turn: research deployment roughly 2-4 further packages; a continuous local Paper
workflow roughly 8-15 further packages cumulatively. These are planning ranges,
not a promise of prompt count, calendar duration or acceptance. Larger packages
may require multiple turns. Missing provider evidence, operator actions, failed
tests or newly discovered defects can increase them. Multi-market live use has
no defensible remaining-turn estimate. The 84-day provider horizon runs in
parallel and is not a blanket ban on approved software work.

Next priority is review/consolidation of the accumulated local changes and a
reviewed recoverable baseline, alongside the remaining authoritative launch
inputs. Do not automatically mark WP-LAUNCH-001 completed or promote planned
Paper/broker packages simply because software tests pass.
