# Suspension Evidence Repair: 2026-10-16

## Findings and corrected semantics

Two implementation defects were found while advancing WP-LAUNCH-001:

1. `AkShareAdapter.suspended_stocks` used `stock_zh_a_stop_em` as a current
   suspension list. The installed implementation and
   [AKShare official interface documentation](https://akshare.akfamily.xyz/data/stock/stock.html)
   identify it as **delisted-market quote data**, not suspended A-share status.
2. Suspension normalization and the separate AKShare calibration path converted
   reported end/expected resumption dates into `TRADING_RESUMED` events. The
   [official dated suspension interface description](https://akshare.akfamily.xyz/data/stock/stock.html)
   and installed source provide no confirmed-resumption guarantee for those
   fields. Forecast metadata must not become factual resumption history.

The old snapshot method now raises an explicit DataProviderError without
network access or writes. It remains callable only to provide a clear
compatibility failure; it cannot silently return a different dataset.
`suspension_events` requires a valid explicit date no later than the capture
date in Asia/Shanghai. Cache parameters carry `akshare-suspension-v2` so old
captures cannot be replayed under new normalization accidentally.

Only valid six-digit identifiers and non-future dated starts normalize to
reported `SUSPENSION_STARTED` observations. Reported end and expected
resumption dates remain separate metadata with resumption unverified. Invalid
identifiers/dates and future starts are rejected, counted and retained in raw
source artifacts. Duplicate normalized keys fail closed for source review.
AKShare calibration now uses the same normalizer instead of recreating the
forecast defect. Tushare code and account requirements were not changed.

These are partial provider assertions, not verified actual/current suspension
status. New events and records are **LOW / RETRIEVAL_TIME**. No result, empty
response or passage of a forecast date proves no ST, no suspension, confirmed
resumption, ordinary listing phase, complete delisting coverage or tradability.

## Architecture

```text
explicit dated stock_tfp_em capture (bounded CLI worker)
  -> raw dataset / schema validation / shared suspension normalizer
  -> AkShareSuspensionEvidenceAdapter
  -> ProviderNeutralIngestionService unit of work
     -> source frame artifact + observation + evidence + batch/fingerprint/warnings
     -> canonical reported start events (same SQLite transaction)

MarketDataService (one existing read snapshot)
  -> lifecycle events + source evidence + retained status
  -> SSERuntimeInputSnapshot v1.5 + explicit legacy/coverage gaps
```

The adapter verifies the raw fingerprint, query/source/version mapping and
reconstructability from archived frame bytes. Credentials are screened before
publication. Artifacts are delivered AKShare frames, not upstream wire bytes,
official issuer statements or authenticated capture metadata. Existing company
snapshots are not replaced with event-derived placeholders. Canonical write
failure rolls back evidence and removes newly created artifact files under
the existing single-worker assumptions; the documented cross-worker artifact
ownership race remains unresolved.

The CLI adds `suspension-events YYYYMMDD` under its existing bounded worker.
Invalid/future CLI dates fail before database creation. Successful capture
still returns **partial / exit 2** because it is not full status coverage.
Empty captures archive their source but do not create normal-status rows.
Acceptance counts describe normalized source observations, not newly inserted
event totals; cached repeats retain the same observation identity.

The runtime inventory does not import provider transports. Lifecycle events
and evidence are read in the same snapshot as calendar, bars and status and
included in its deterministic input hash. It always preserves incomplete
lifecycle coverage, and flags required source review when events exist.
Legacy snapshot dataset `instrument_status_suspended` and unversioned
`stock_tfp_em` lifecycle events remain visible with explicit unverified flags,
even when old rows claim higher trust. No status clearance or market-rule
calculation context is manufactured.

Other legacy read paths and calibration results do not yet share a centralized
quarantine/eligibility contract. Existing rows/reports are neither deleted nor
retrospectively certified. Before historical use, explicitly audit and mark
their provenance eligibility; lost source truth cannot be recovered by code.
The corrected path does not complete ST, confirmed resumption or phase history.

## Real capture

```sh
.venv/bin/python scripts/ingest_data.py --timeout-seconds 40 --refresh \
  suspension-events 20261016
```

- Received 13 rows, accepted 13 reported starts, rejected 0; **zero confirmed
  resumptions and zero current-status rows**. The result correctly remained
  partial. This is observed response coverage, not market-wide coverage.
- Batch: `349cd67d-cb84-43db-893d-fec9cdef07c1`.
- Actual availability: `2026-10-16T05:37:17.131293Z` (13:37 Malaysia).
  Neither query date nor effective date backdates availability.
- Archived source size: 7,872 bytes; the bounded content read verified SHA-256
  `f52896fa6a42a84c62ddcd6339464040b9d1760e54cd6538d49b61ac9b9b5db6`.
- Artifact identity:
  `d656528322ea25396eb42c622e525c2d23d3b2a87e4110758d1c9061e3a283ba`.
- Read-only inspection for observed SSE identifier `600293` at
  `2026-10-16T05:39:38.442362Z` retained one lifecycle event and one source
  evidence record, no confirmed resumption and no current-status record.
  Inventory hash:
  `9284a8f58e2a0cf73c7de6688465eedf4c540b0eab604f144ff779cee4e4dada`.
  This identifier is a diagnostic sample, not an investment selection.

## Database and governance

No schema or migration change: framework `0.8.0`, schema `0.8.2`, head
`0010_portfolio_evidence_lineage`. The real capture adds 13 instrument snapshots,
13 lifecycle rows, 13 provider records, one artifact/observation, one batch,
one fingerprint, three limitations and three warnings. Existing prices,
calendar and action rows are unchanged. Lifecycle starts total 13; provider
records 79, artifacts 4, batches 14. Status history remains empty.

Read-only integrity/checksum/fingerprint/foreign-key audit passed at
`2026-10-16T05:37:49.031275Z`, audit hash
`fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
Local databases, cache and source artifacts stay ignored, not Git backups.
No trading, paper-ledger, broker, portfolio or notification behavior was added.
Execution/notifications remain disabled, PIT `UNSUITABLE`, production
`NOT_READY`. This does not complete WP-LAUNCH-001.

## Verification and continuation

New regression cases cover endpoint misrouting, forecast/end-date semantics,
missing/invalid/future rows, date validation, empty-source preservation,
versioned cache replay, transactional rollback, company metadata, legacy
record retention, duplicate keys, secret filtering, calibration parity,
capture substitution and no-write CLI failures. Layering checks include the
new adapter. Final results: **621 passed, 6 skipped**, Ruff passes, mypy passes
for 213 source/script files, all 66 governance checks pass, and tracked plus
new-file whitespace checks pass. No ignored database/cache/artifact files or
frozen trading/portfolio/notification modules are included in the changes.

Next: explicit legacy-source eligibility auditing, dated ST/listing-phase and
confirmed-resumption evidence, actual exceptional-calendar/action coverage,
then reviewed account/settlement, intraday/cost and simulation bindings.
No Tushare upgrade or real-account credential is required for this slice.
All five continuation slices remain uncommitted and unpushed for review.
