# Research Input Integrity - 2026-10-18

Work package: WP-LAUNCH-001 (partial).
Framework 0.8.0; schema 0.8.2; PIT UNSUITABLE; execution disabled.

## Findings and Repair

Financial Research previously displayed `facts[-1]` as the latest value. Input
order could therefore select an old period or revision. ResearchContext checked
availability but did not bind bars/facts to the queue candidate or verify that
the metric dictionary key matched the fact. Same-version conflicting facts,
future queue information, future instrument metadata and future report periods
were not independently rejected at this boundary.

ResearchContext now exposes reusable validation that runs at construction and
again before ResearchEngine starts any repository run. Direct Financial
Research evaluation also rechecks it. This catches relevant dictionary changes
after context construction; it is not a deep-immutable or concurrency-safe
snapshot of arbitrary module inputs.

Validation now enforces:

- Candidate, bar and fundamental instrument identity by market/asset type/symbol.
- Matching metric names and finite fundamental values.
- Queue admission, candidate availability, priority calculation and hard-screen
  evaluation/availability no later than the explicit research cutoff.
- Visible instrument metadata and report periods, in addition to existing
  evidence/bar/fact availability checks. The existing Bar domain model already
  prevents an observation timestamp later than its own availability.
- No contradictory material content under one fundamental version. Identical
  numeric repeats with a different ingestion batch remain admissible.

Financial diagnostics select by report period, then availability, revision and
publication time, consistent with the existing storage read contract. Only
semantically identical tied observations may use decimal text as a deterministic
display tiebreaker; conflicting content fails rather than choosing arbitrarily.
Availability is rendered in UTC, and assessment availability includes every
fact used for diagnostics and restatement reporting.

The financial module version is centrally defined as
`financial-v0.5.1-input-integrity`. Diagnostics now expose period, availability,
unit, currency, trust and availability precision beside each latest value.
Unknown quality remains unknown. No detected restatement is explicitly not
proof of complete revision history.

## Verification

- 32 new regression cases cover ordering permutations, mixed instruments,
  metric aliases, nonfinite values, future periods/queue/metadata, conflicting
  versions, context mutation, deterministic duplicates and derived availability.
- The database integration case reads revision history, deliberately reverses
  input order, and persists the correct latest financial diagnostic. Invalid
  mutated input creates no run/report/signal. Facts alone produce an incomplete
  unscored report, not an investment decision.
- Full pytest: 840 passed, 6 skipped; Ruff, mypy (218 source/script files),
  governance and whitespace checks pass.
- No schema migration, operational database write, source capture or network
  call. All new database exercises use temporary fixture databases.
- Paper Trading, Broker, Execution, Portfolio and Notification code unchanged.
- Fourteen continuation slices remain local/uncommitted/unpushed.

## Remaining Boundaries

Identity, timestamps and deterministic selection do not authenticate original
source bytes, accounting units, consolidation basis or metric semantics. The
existing evidence-driven scoring contract is not a numerical fundamental-to-
score implementation, and a displayed diagnostic does not certify its inputs.
Native snapshots remain noncanonical pending reviewed source-evidenced mapping.
No trust, PIT, strategy, simulation or live readiness is promoted.

Other direct module APIs, caller-owned nested mutable data, bar ordering and
exact original-run consumed-input provenance need further review. A pre-run
check must not be described as a deep immutable research snapshot.

Next bounded delivery: verify a small set of financial metric/unit/period and
industry mappings against authoritative retained source evidence before
populating canonical facts. This work requires no immediate user credential or
broker action. Accumulated local changes need separate review before commit
and remote synchronization.
