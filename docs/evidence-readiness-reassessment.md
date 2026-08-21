# Evidence-Backed PIT Readiness Reassessment

`WP-READINESS-001` converts existing data-quality artifacts and operational
history into a deterministic governance report. It does not change provider
trust, effective PIT classification, Historical Replay eligibility, or any
trading boundary.

## Evidence Inputs

The reassessment inventories:

- Phase III framework readiness, gap, AKShare quality, and Tushare capability
  JSON artifacts;
- provider contract checks and longitudinal baseline entries when an
  operational SQLite snapshot is supplied;
- direct CNInfo artifact observations;
- Yahoo/independent-provider calibration attempts;
- provider conflict history and supporting limitation documents.

Missing input files, malformed JSON, stale reports, unavailable providers, and
empty operational histories remain visible. An absent metric remains
`unknown`; it is never converted into observed zero coverage or zero provider
agreement.

## Decision Contract

Each dataset produces:

- current, proposed, and effective readiness classification;
- a mechanical evidence score that is not an investment score;
- explicit gates, blockers, limitations, and immutable artifact references;
- a cause separating insufficient evidence, observed quality failure, external
  provider restriction, mixed causes, or sufficient evidence for review;
- a manual promotion-review eligibility flag.

The effective classification always equals the existing classification. Even a
fully passing synthetic case can only become eligible for a separate human
governance review. It cannot promote itself.

## Conservative Gates

The default policy requires at least:

- fresh source artifacts within 45 days;
- 8 contract checks across 84 observation days;
- a longitudinal baseline with at least 75% continuity and 90% field coverage;
- measurable coverage and consistency from available provider evidence;
- no unresolved high-severity provider conflicts.

`CAUTION` and `USABLE` proposals add progressively stronger coverage,
continuity, consistency, field-completeness, trust, and availability-precision
thresholds. Agreement cannot exceed the declared trust of the evidence.

## Reproducible Command

Run from the repository root with an explicit timestamp:

```bash
.venv/bin/python scripts/reassess_pit_readiness.py \
  --as-of 2026-08-22T00:00:00+00:00 \
  --contract-database data/provider-contract-monitor.sqlite3
```

The output is content-addressed JSON and Markdown under
`docs/generated/evidence-readiness/`. Reports record the exact Git commit,
configuration hash, source-tree hash, migration head, model versions, and input
artifact hashes. Generation is idempotent and fails on an identity collision.

The operational database is opened read-only. No readiness row, trust level,
notification, portfolio artifact, or trading state is written.

## Interpretation

Provider contract health proves that an endpoint currently satisfies a narrow
contract. It does not prove historical continuity, PIT-safe availability, or
cross-provider correctness. Supporting documentation proves an implemented
boundary but does not count as operational observations.

The reassessment must remain fail-closed until representative, retained
evidence exists. Paper Trading, Execution, Broker, Order, Trade, Fill, Asset
Allocation, Auto Rebalancing, and Live Trading remain outside scope.
