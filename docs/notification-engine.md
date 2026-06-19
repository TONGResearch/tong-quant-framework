# V0.8 Notification Engine

## Purpose

The Notification Engine distributes research information for human review. It
does not authorize actions and has no dependency on trading or execution-side
objects.

Supported artifacts:

- ResearchReport
- ValidationReport
- PortfolioProposal
- RiskAssessment

## Workflow

```text
Artifact -> Renderer -> NotificationRecord -> SQLite outbox
                                                |
                                      later dispatcher claim
                                                |
                                  NotificationMessage -> Channel
                                                |
                                      DeliveryRecord audit
                                                |
                                  terminal failure -> dead letter
```

Generation and delivery are separate operations. `NotificationService` renders
and persists records. `NotificationDispatcher` later claims pending records and
sends only rendered `NotificationMessage` values through channel adapters.

## Modes

- `disabled`: generate nothing and deliver nothing.
- `preview`: persist rendered preview records; dispatcher cannot claim them.
- `enabled`: persist pending records for later dispatcher delivery.

The default is `disabled`.

## Idempotency

The artifact is serialized canonically and hashed with SHA-256. The outbox
deduplication key is SHA-256 over:

```text
artifact_hash + channel + recipient
```

The SQLite unique constraint prevents duplicate notifications for the same
artifact version and destination. A changed artifact creates a new hash and a
new notification record.

## Storage

`notification_outbox` stores immutable artifact identity, rendered content,
dispatch state, attempt counters, and safe error codes.

`notification_deliveries` stores each delivery attempt and provider receipt.
`notification_dead_letters` stores terminal failure metadata and references the
outbox through a foreign key. These tables contain no credential columns.

## Lease And Crash Recovery

Every dispatch claim has a finite lease. A later dispatcher recovers expired
claims after a process crash. Recoverable claims return to retry without hiding
the failed attempt; exhausted claims become dead letters. This gives at-least-once
delivery, not exactly-once delivery. Providers may still need idempotency keys or
reconciliation if a process crashes after an external send succeeds but before
the local receipt commits.

## Security

Telegram, WeChat, and Email adapters read credentials only when sending and
only from environment variables. Provider exceptions are reduced to exception
class names before persistence. Domain, repository, and low-level SQLite entry
points reject assignments containing `token`, `api_key`, `secret`, `password`,
or `webhook_url`. Rendered text applies sensitive-assignment redaction and always
includes:

```text
This is research information only.
It is not investment advice.
It is not an execution instruction.
```

Live provider tests require `TONG_QUANT_RUN_LIVE_NOTIFICATION_TESTS=1` and are
skipped by default. Normal integration tests use a fake channel and no provider
credentials.
