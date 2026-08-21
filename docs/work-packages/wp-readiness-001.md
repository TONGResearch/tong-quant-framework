# Work Package: WP-READINESS-001

Status: `ready`

## Objective

Reassess data readiness from accumulated, independently reviewable evidence
without changing provider trust or PIT classification automatically.

## Dependencies

- `WP-DATA-001`: longitudinal provider baseline
- `WP-DB-001`: verified database recovery
- `WP-DATA-002`: direct CNInfo artifact evidence
- `WP-DATA-003`: independent Yahoo daily-bar calibration
- `WP-OPS-001`: provider health operations

## Scope

- Inventory available contract runs, baseline manifests, direct CNInfo
  observations, Yahoo calibration attempts, and provider limitations.
- Measure observation duration, schedule continuity, field coverage, correction
  visibility, unavailable periods, and unresolved conflicts per dataset.
- Distinguish insufficient observation history from observed poor provider
  quality.
- Produce a reviewed readiness recommendation and explicit evidence gaps.
- Keep current classifications unchanged unless Tong approves a separate
  governance decision supported by the report.

## Minimum Review Gates

- Every input references immutable hashes and implementation versions.
- Missing reports and expired CI artifacts remain visible as gaps.
- Contract health is not treated as provider trust.
- Agreement between two low-trust sources cannot produce verified evidence.
- Retrieval-time data cannot be presented as exact historical availability.
- Datasets without sufficient longitudinal continuity remain `UNSUITABLE` or
  `CAUTION`; they are never silently omitted.

## Deliverables

- Evidence inventory and coverage window by provider/dataset/market.
- Provider health and continuity summary.
- Conflict and limitation summary.
- Proposed `USABLE`, `CAUTION`, or `UNSUITABLE` classification per dataset.
- A gap list and explicit recommendation on whether another data-remediation
  package is required.

## Non-Goals

- No automatic trust or PIT promotion.
- No Paper Trading, Execution, Broker, Order, Trade, Fill, Asset Allocation, or
  Live Trading work.
- No Notification Engine integration or external operational delivery.
