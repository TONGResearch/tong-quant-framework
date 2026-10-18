# Unadjusted Daily Price Evidence

## Architecture

This WP-LAUNCH-001 slice migrates unadjusted AKShare equity/index daily bars to
the existing provider-neutral evidence transaction. Other legacy AKShare jobs
are unchanged. The sequence is:

```text
AKShare capture/cache -> raw validation -> normalization -> evidence adapter
    -> snapshot/hash/reconstruction checks
    -> ProviderNeutralIngestionService transaction
       -> batch + fingerprint + evidence + artifact metadata/observation
       -> canonical instrument/bar writes + limitations/warnings
```

The service's optional canonical writer runs inside its existing SQLite unit
of work, not a nested transaction. A later failure rolls back both domain and
audit rows and discards newly created artifact bytes. Existing company
snapshots are preserved; a concurrent currency change rejects the write.
The default artifact root is the database parent's `raw/provider-artifacts`;
an injected ProviderArtifactStore can override it. Absolute storage paths do
not enter evidence payloads or SQLite.

Schema remains `0.8.2`, migration head `0010_portfolio_evidence_lineage`; no
DDL, migration, extra table, or rewrite is added. Framework remains `0.8.0`.

## Exact Binding, Not Automatic Trust

Each record binds market, symbol, asset category, currency, observation and
availability timestamps, OHLCV, nullable turnover, adjustment basis, suspension
flag and endpoint identity. Timestamps have canonical UTC representation.
It carries a content hash and source-bound artifact identity/raw hash.
Matching a close alone, or matching at another availability time, is not enough.

The archived bytes are canonical JSON containing query parameters and the
delivered AKShare DataFrame serialization. They are **not** upstream HTTP
wire bytes, independently authenticated exchange data, or proof that the
provider never revised a price. Query/security/date mismatches reject capture.
Only unadjusted China equity/index data enter this adapter. The separately
retained non-strict adjusted path cannot acquire unadjusted-price evidence.

The archive must match the original RawDataset fingerprint and reproduce the
canonical normalized bars exactly. Serialization precision loss is rejected,
not rounded away. Snapshot size is bounded at 16 MiB. Activity units remain
provider-native/unverified; missing turnover stays unknown, not zero.

DataFrameCache retains original frame JSON because Pandas can add type
metadata when rebuilding a frame. Both source hashing and archive bytes now
use one shared serializer, without changing the previous fingerprint format.
Cache reads/writes check declared hashes and credential-like fields before
use/publication. Hash failures fail closed; `--refresh` is the explicit bypass
of a cache, not a trust upgrade. Atomic cache publication/corruption-as-miss
and independently authenticated retrieval metadata are not implemented here.

## Runtime Inventory

The read-only runtime reader (now `sse-runtime-input-v1.3`) reads price evidence
in its existing MarketDataService/SQLite snapshot. It retains relevant
observations and exposes exact `previous_close_evidence` and evidence IDs.
Conflicting records remain visible. Legacy prices are not assigned provenance
merely because a newly retrieved close happens to match.

A matching record removes the missing-binding diagnosis only. LOW trust
remains LOW; `price_evidence_trust_insufficient` and
`price_artifact_review_required` remain explicit gaps. Metadata/hash matching
does not establish that artifact bytes are currently present/unchanged or
that the original provider is independently reliable. Runtime inspection is
not an authoritative calculation-context builder or trading approval.

## Real Operational Exercise

The existing CLI was run with `--refresh --timeout-seconds 60 daily-bars
600000 20261001 20261015` against the existing local operational database.
It accepted all six source rows. `--refresh` bypasses and does not update the
cache. This capture succeeded through the primary endpoint
`akshare:stock_zh_a_hist`; prior observations used the Tencent fallback.

- Captured: `2026-10-16T05:09:58.556223+00:00` (13:09:58 Malaysia time).
- Batch: `909e1edf-6b56-46c5-9a2f-e13307f978cd`.
- Snapshot bytes: 3,322; SHA-256:
  `03e8f6f69df0b3f8c8f24fb144a44dd0aa9ba3f001d6f7f399c1c65c0d00d69d`.
- Artifact ID:
  `73116e1444d9726607e1e65dbdf835e60628f165c877be3b5b2182e067bf37f8`.
- Actual recorded query basis: `adjustment=none`, equity, six-digit symbol,
  explicit dates, normalization version `akshare-market-data-v2`.
- Six new economic observations and six price evidence records; no records
  were visible before capture. Six distinct trading dates now have 18 retained
  bar observations overall. Existing bare versions are not rewritten.
- One exact October 15 previous-close binding; record:
  `052d29167ddc38bb90393d11c91fe58d0f64e93a16a33bd12e2f04bd2086eb9e`.
- All price evidence remains `LOW` / `RETRIEVAL_TIME`.

The artifact bytes were independently read back and hashed. A read-only
comparison of the six overlapping old/new dates found equal OHLC and native
volume values; the old fallback had unknown turnover, while the primary
response reports turnover. These are different retrievals through one AKShare
transport, not an independent provider-consistency baseline. Missing prior
turnover is not a disagreement with zero or a reason to rewrite history.

Post-ingestion database audit passed, with no FK, checksum or schema drift.
Bars: 12 -> 18; provider records: 14 -> 20; artifacts/observations: 1 -> 2;
batches: 11 -> 12; fingerprints: 7 -> 8; warnings: 18 -> 21;
limitations: 10 -> 13. Other tables were unchanged, including calendar,
company snapshots, corporate actions and all downstream research/trading data.
Audit hash:
`2e464db9b1b5afdf244d3d1f1491be6b51fd61130507096e094585fa4aa8105d`.
Raw snapshots and SQLite remain ignored local data, not Git backup artifacts.

## Verification And Remaining Work

Regression tests exercise exact row/source/availability/artifact identity,
cached idempotence with original serialization, unknown turnover, wrong symbol
and dates, incomplete same-day bars, precision loss, cache corruption, secret
filtering, metadata substitution, conflicting evidence, and full rollback on
canonical or later warning failure. Synthetic fixtures cannot earn trust.

Final verification: 576 passed / 6 skipped; Ruff and mypy passed (210
source/script files), governance passed 64 checks, and diff checks passed.
This slice adds 18 regression cases. The preceding trust/calendar slices and
this slice remain in the local working tree, not committed or pushed.

Required before authoritative use: independent price/source review, complete
exchange calendar, instrument status/phase/action coverage, account/settlement
inputs and existing policy/simulation-boundary binding. Artifact bytes need
coordinated backup, restore and current read-time verification. Reading all
visible price evidence before window filtering also needs indexed range
selection before large historical/revision volumes are operationalized.
PIT stays `UNSUITABLE`; execution/notification stay `disabled`. No Paper,
broker, Order, Trade, Fill, asset-allocation or live implementation is added.
