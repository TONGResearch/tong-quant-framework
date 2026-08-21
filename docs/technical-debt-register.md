# Technical Debt Register

| ID | Priority | Debt | Current control | Exit condition |
|---|---|---|---|---|
| TD-001 | P0 | AKShare cannot reconstruct complete historical publication timing, status history, or universe membership. | Conservative trust levels and warnings. | Verified PIT provider coverage and reconciliation tests. |
| TD-002 | P0 | Corporate-action announcement timing and dated adjustment factors are incomplete. | Strict PIT mode rejects adjusted bars. | Reproducible PIT adjustment-factor pipeline. |
| TD-003 | P1 | Existing analytical tables lack many foreign keys. | Repository contracts and tests. | Staged table rebuilds after orphan audit. |
| TD-004 | P1 | SQLite storage is a large ownership monolith. | Module-level repositories isolate callers. | Split storage modules behind one transaction manager. |
| TD-005 | P1 | Notification delivery is at-least-once after a crash; a provider may receive a duplicate when delivery succeeded but acknowledgement was not persisted. | Deterministic outbox identity and lease recovery. | Provider idempotency keys or delivery reconciliation. |
| TD-006 | P1 | Dead letters require operator review; no scheduler or operational dashboard exists. | Persistent dead-letter audit table. | Defined worker, alerting, replay, and retention procedures. |
| TD-007 | P1 | Runtime framework snapshots remain partly caller supplied. | Stored version and configuration hashes. | Runtime snapshot factory verifies Git state and effective config. |
| TD-008 | P2 | Portfolio and Risk calculations remain explainable heuristics. | Proposal-only semantics; no execution. | Calibration against validated samples, covariance, liquidity, cost, and tail-risk evidence. |
| TD-009 | P2 | Live provider behavior can drift between scheduled checks. | Weekly isolated CNInfo/Yahoo contract monitoring and deterministic fake tests. | Alert ownership, longitudinal SLOs, and calibrated provider fallback policy. |
| TD-010 | P2 | No enforced coverage threshold or property-based PIT tests. | CI runs Pytest, Ruff, and mypy. | Coverage policy plus timestamp and migration property tests. |
| TD-011 | P1 | Legacy `DataIngestionPipeline` remains directly typed to `AkShareAdapter`. | New providers use `ProviderEvidenceAdapter` and `ProviderNeutralIngestionService`. | Migrate remaining AKShare dataset jobs to provider-neutral orchestration without breaking canonical consumers. |
| TD-012 | P2 | Baseline `SCHEMA` still creates the legacy schema on a fresh database. | `0000` baseline, pre-migration physical fingerprint validation, and migration checksums fail closed. | Generate a frozen baseline artifact and make all future DDL migration-owned. |
| TD-013 | P1 | SQLite concurrency behavior is not load-tested and has no documented writer policy. | WAL mode and short transactions reduce contention. | Explicit busy timeout, single-writer operating model, and concurrent connection tests. |
| TD-014 | P2 | Generated readiness evidence can drift from its committed code baseline. | Reports carry timestamps and query scope. | Freeze report manifest with Git commit, config hash, database snapshot hash, and generated artifacts. |
| TD-015 | P1 | CNInfo is currently transported through AKShare and Yahoo uses an unofficial endpoint. | Explicit provenance, conservative trust, retrieval-time limits, and contract monitoring. | Direct CNInfo artifact verification and cross-provider Yahoo calibration with continuity evidence. |
