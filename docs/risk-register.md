# Engineering Risk Register

| ID | Severity | Risk | Mitigation | Residual risk |
|---|---|---|---|---|
| R-001 | Critical | Survivorship or future-data leakage creates false validation results. | Strict `available_at`, replay warnings, trust matrix, adjusted-bar rejection. | Historical provider coverage remains incomplete. |
| R-002 | High | Process crash strands notification work. | Expiring leases recover orphaned dispatching records. | A recovered send may duplicate an externally accepted message. |
| R-003 | High | Credentials enter persistent notification data. | Model, repository, and SQLite-entry validation reject credential-like assignments; errors store type names only. | Unlabelled opaque secrets cannot be detected reliably; access controls remain necessary. |
| R-004 | High | Partial multi-table writes corrupt a Research or Validation run. | Atomic final-run transaction boundary. | Older persisted partial runs need separate audit and cleanup policy. |
| R-005 | High | Database is marked current after an incomplete schema change. | Ordered migrations, checksums, and migration-head metadata. | Backup, downgrade, and full post-migration invariant checks are pending. |
| R-006 | High | Orphaned analytical child rows create inconsistent reports. | New dead-letter relation uses an FK; repositories preserve ownership. | Existing tables require staged FK migrations. |
| R-007 | Medium | AKShare endpoint or column drift silently changes normalization. | Raw hashes, schema validation, provider limitations, fake-client tests. | Scheduled live contract monitoring is absent. |
| R-008 | Medium | Notification channels leak provider errors or configuration. | Environment-only credentials and safe error codes. | Third-party channel behavior still requires sandbox verification. |
| R-009 | Medium | Research risk heuristics are mistaken for portfolio authorization. | Artifact naming, disclaimers, execution guards, proposal-only contracts. | Human interpretation and governance remain necessary. |
| R-010 | Critical | Future trading functionality bypasses validation or risk. | Execution disabled and guarded; no Broker, Order, Fill, or Paper Trading implementation in this phase. | Must be re-audited before any trading-related milestone. |
