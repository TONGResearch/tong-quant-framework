# Engineering Continuity

## Purpose

This protocol makes Tong Quant maintainable when the next developer or AI has a
smaller context window, a lower token budget, or less capable reasoning. Project
state must live in versioned files and executable checks, not conversation
memory.

## Authority Order

When documents disagree, use this order:

1. `config/project-governance.toml` for versions, readiness, freeze, and work state
2. `AGENTS.md` for non-negotiable engineering rules
3. `PROJECT_STATUS.md` for the current short handoff
4. `docs/architecture.md` for module boundaries
5. The selected `docs/work-packages/*.md` file for implementation scope
6. Historical milestone documents for background only

Do not silently reconcile contradictions. Fix the stale document in the same
change or stop with an explicit failed governance check.

## Low-Context Workflow

An agent should work on exactly one work package at a time:

1. Run the governance audit.
2. Confirm that the package status is `ready` and dependencies are complete.
3. Restate the package objective, non-goals, and acceptance criteria.
4. Inspect only the owning modules and adjacent tests first.
5. Make the smallest implementation that satisfies the acceptance criteria.
6. Run package tests, then all required completion checks.
7. Update package status and all affected state documents.
8. Commit one coherent milestone; never mix speculative future features.

Missing credentials, paid endpoints, or provider downtime are external states.
They must produce explicit unavailable evidence, not invented fixtures presented
as real data and not weakened acceptance criteria.

Workflow continuity is also versioned evidence. Pin supported GitHub-hosted
runner images, use official Actions on supported runtimes, and verify runtime
migrations in CI before relying on the next scheduled operational artifact.

## Decision Discipline

- Record architecture decisions in `docs/decisions/`.
- Record work sequencing in `config/project-governance.toml`.
- Record implementation detail in a work-package document.
- Record unresolved risk in `docs/risk-register.md`.
- Record known remediation work in `docs/technical-debt-register.md`.
- Keep generated provider evidence separate from policy decisions.

No score, provider name, successful HTTP response, or passing parser may alone
promote trust or PIT readiness.

## Change Boundaries

Every change should identify:

- Owning module
- Inputs and outputs
- Persistence impact
- PIT impact
- Trust and availability impact
- Failure behavior
- Tests
- Documentation impact
- Explicit non-goals

Any database change requires an ordered migration, checksum, fresh/legacy
convergence test, fingerprint verification, and documentation update.

## Handoff Format

Every unfinished handoff should state:

```text
Work package:
Current status:
Files changed:
Commands run:
Observed results:
Remaining acceptance criteria:
Known blockers:
Safety boundaries rechecked:
```

Do not use vague handoffs such as "continue the provider work." A new agent
should be able to identify the next command and the unmet acceptance criterion
without reading the original chat.

## Promotion Control

The governance audit proves internal consistency only. It does not prove data,
research, validation, production, or trading readiness. Readiness promotion
requires new measured evidence, reviewed documentation, updated risk controls,
and explicit approval. Trading-related development remains frozen throughout
the current phase.
