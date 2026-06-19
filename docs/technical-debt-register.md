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
| TD-009 | P2 | Live provider tests are skipped by default. | Fake adapters and deterministic unit tests. | Scheduled isolated provider-contract monitoring. |
| TD-010 | P2 | No enforced coverage threshold or property-based PIT tests. | CI runs Pytest, Ruff, and mypy. | Coverage policy plus timestamp and migration property tests. |
