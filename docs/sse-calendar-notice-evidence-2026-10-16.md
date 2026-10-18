# SSE Calendar Notice Evidence

## Scope And Sources

This WP-LAUNCH-001 slice uses the existing ProviderEvidenceAdapter, neutral
ingestion transaction, SQLite and content-addressed artifact store. It captures
reviewed notice assertions, not a complete calendar or trading authorization.

The [official September notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml)
displays September 17, 2026 as publication date, despite the different date in
its URL. The [annual notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml)
was also reviewed for date consistency, but its bytes are not captured by this
adapter. This is not cross-provider calibration.

`config/markets/sse-calendar-notice-2026-09.toml` binds reviewed assertions to
the complete source hash and a bounded review window. There is no free-form
news parser, government-workday inference, or weekend inference. A reopening
date is one explicit day, not an open-ended interval. Any changed source bytes,
including page-layout changes, require a new review.

## Real Capture

- Capture: `2026-10-16T04:54:18.560675+00:00` (12:54:18 Malaysia time).
- Provider/dataset/subject: `sse_calendar_notice` /
  `exchange_calendar_notice` / `SSE`.
- Captured assertions: 14 (12 closed dates, two reopening dates).
- Source size: 26,921 bytes; SHA-256:
  `ec3b2fa822161cd8852ed5255b002f40506ebd348f77a4b0c672dcd637387dec`.
- Batch: `c0ee3bbc-daf5-4a4d-ba58-42c22fd2225a`.
- Artifact ID:
  `4c62deab3432424033ff33ff3aae5a1c662fae2c4cb183ae5531a7423b048ab5`.
- Trust/precision: `MEDIUM` / `RETRIEVAL_TIME`, not HIGH or VERIFIED.
- Source publication date is payload metadata only. Evidence `published_at`
  is unset. The required artifact/observation `published_at` uses capture as a
  conservative upper bound, not an authenticated publication clock. No
  evidence is visible before capture; a real pre-capture read returned zero.
- Review deadline: November 15, 2026 at 04:49:40 UTC. This is a project review
  deadline, not legal expiry. Expired evidence remains visible with a warning;
  expired profiles cannot produce new captures.

The stored artifact was independently read back and its SHA-256 verified.
Raw bytes and the operational database are ignored local data, not Git
attachments or a cross-device backup.

## Database And Read Path

No schema rewrite or migration: schema `0.8.2`, head
`0010_portfolio_evidence_lineage`, 64 tables. The capture added 14 provider
records, one artifact, one observation, one batch, one fingerprint, three
limitations and three warnings. Record counts describe reviewed assertions,
not annual coverage or independent raw pages.

Bars (12 observations), calendar rows (8,797), instruments (five snapshots) and
corporate actions (66 observations) were unchanged. Read-only integrity audits
passed before/after ingestion, without foreign-key, checksum or fingerprint
drift. Post-capture audit hash:
`82494620310e0be861be1056d9f18b553f7494aace710160449069ca122b5856`.

MarketDataService exposes typed provider evidence through the existing PIT
query. The runtime reader includes it in the same SQLite snapshot as the
calendar, security and prices. Reader version is `sse-runtime-input-v1.2`;
its content hash now also binds the notice records and warnings.

The real October 1-16 window contains nine notice assertions. Eight of the
nine dates absent from the stored open-only calendar have explicit closure
evidence; October 11 is not proven by this notice. Notice records do not
overwrite or silently merge into the calendar. Conflicts, malformed records
and expired reviews remain visible. Calendar completeness/provenance remains
an unresolved requirement; no trusted calculation context is constructed.

## Operations And Tests

From the PyCharm project directory:

```bash
.venv/bin/python scripts/ingest_data.py --timeout-seconds 60 sse-calendar-notice
.venv/bin/python scripts/inspect_sse_runtime_inputs.py \
  --symbol 600000 --trade-date 2026-10-16 \
  --as-of 2026-10-16T13:00:00+08:00 --calendar-start 2026-10-01
```

The existing parent bounds the worker. Transport permits only official HTTPS
notice paths, no redirects, and at most 2 MiB. Source/profile verification
precedes target database initialization. Exit 2 / `partial` is expected even
for a successful capture: the calendar remains incomplete. Inspect structured
counts and warnings, not exit code alone. The read-only inspector never
fetches, initializes or migrates a database.

Tests cover explicit dates/scope, trust, timestamps, artifact persistence,
idempotence, future rejection before side effects, changed source bytes,
expired review, malformed/conflicting records, deterministic reads, safe CLI
failure before database creation and redirect rejection. Synthetic fixtures
are not evidence of provider quality.

Final verification: 558 passed / 6 skipped; Ruff passed; mypy passed for 208
source/script files; governance passed 63 checks; git diff checks passed.
This slice adds 22 notice tests and one layering test. The preceding trust-gate
repair remains in the same uncommitted working tree; neither slice was pushed.

The adapter is not yet in the five-scope scheduled monitor and cannot count
toward that horizon. Repetition cannot automatically earn trust or continuity.
Remaining work is complete calendar and price provenance, then phase/action
coverage, account/settlement evidence and existing simulation-boundary gates.
PIT stays `UNSUITABLE`; execution and notification stay `disabled`. No Paper,
broker, Order, Trade or Fill implementation is added.
