# ADR 0003: Longitudinal Provider Baselines

Status: Accepted

## Decision

Provider contract history is summarized in immutable, content-addressed
baseline manifests. Every manifest fixes its period, expected cadence, scopes,
implementation version, input hash, source check references, and scope-level
metrics.

Successful observations, required-field coverage, and schedule continuity are
separate measurements. Missing scheduled periods, failed probes, empty
responses, and provider limitations remain visible.

## Rationale

A sequence of successful endpoint calls cannot prove historical continuity or
PIT safety. Separating the metrics prevents provider downtime, missing CI runs,
and schema defects from collapsing into a misleading aggregate score.

## Consequences

- Identical stored observations and query scope produce the same baseline hash.
- Baseline records retain foreign-key references to source contract checks.
- Contract history reports observed trust and availability precision only.
- No baseline may promote `DataTrustLevel`, historical continuity, or PIT
  readiness.
- Trading-related development remains frozen.
