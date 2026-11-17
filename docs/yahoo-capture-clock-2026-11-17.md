# Yahoo Global Snapshot Producer Clock Guard

Work package: WP-LAUNCH-001. Status: ready, not accepted.
This is preventative producer-contract hardening, not a provider or trading feature.

## Verified Defect

The existing Yahoo global-equity snapshot adapter serializes retrieved_at in its
retained envelope as UTC, while provider_evidence_id uses the capture datetime's
original ISO offset. A nonzero-offset injected producer clock therefore creates
the same envelope bytes at the same instant but a different evidence identifier.
Reconstruction from the UTC envelope cannot reproduce the original record.

This was reproduced offline with synthetic responses, not a live Yahoo outage.
The default clock already uses datetime.now(UTC); no claim is made that normal
MSFT/owner observations were corrupted or that account permissions failed.

## Fix And Compatibility

YahooGlobalSnapshotAdapter.fetch now requires an aware, zero-offset capture
clock, following the existing Nasdaq capture precedent. Nonzero offsets raise
a generic clock-contract error before constructing or publishing provider
artifacts, evidence, batches or fingerprints. Failure-response captures use the
same guard. This happens after the injected download and actual capture-clock
read, not before network access or as a fabricated pre-fetch retrieval time.

Zero-offset timezone labels are allowed based on their actual offset, not a
timezone-name allowlist. A London winter clock can qualify; a nonzero summer
offset cannot. Non-UTC request/read cutoffs remain allowed and are distinct from
the producer clock. No market timezone, OHLC, price basis, capability or default
clock changes are introduced.

GLOBAL_PRICE_SNAPSHOT_VERSION and accepted UTC bytes/identifiers remain unchanged
intentionally. Rejecting unsupported new inputs is not normalization of existing
IDs, a new source format or a reason to invalidate previously valid UTC captures.
Generic provider_evidence_id and other providers are not changed in this slice.
No old record is rewritten, deleted, backdated or newly certified.

## Evidence And Tests

- New synthetic tests cover US/HK/MY; naive and nonzero producer clocks; both
  New York repeated-clock folds; zero-offset alternatives; and independently
  non-UTC request/read cutoffs with a correct UTC producer.
- Empty-store rejection leaves diagnostic DB bytes unchanged, the artifact root
  absent and all retention tables empty. Failed responses are covered too.
- Test-only legacy fixtures reproduce the former label/ID mismatch without
  bypassing the new production guard. They remain retained and unreadable, even
  when an older valid capture exists; readers do not fall back favorably.
- Rejected new attempts cannot replace or freshen existing evidence: original
  DB/artifact bytes, capture count, identity and bar availability are preserved.
- An independent offline comparison loads this adapter's source from HEAD with
  current shared contracts. All six US/HK/MY success/failure UTC batches, bytes
  and IDs match the repaired adapter exactly. Old nonzero-offset captures show
  the identity defect; the repaired adapter rejects them. This is not a whole
  old-environment reproduction or independent market-data calibration.
- Scoped owner-authorized read-only AI review found no actionable issue in the
  guard and core clock tests. That review did not run tests or inspect real data.
- A real offline retained-input rehearsal reconstructs the original MSFT/NVDA
  971/752-row snapshots at their old November 15/8 cutoffs. Repeated JSON/notes,
  binding hashes and no-flag output match; six pinned DB/WAL/old JSON files retain
  their hashes. This is unchanged old evidence, not new capture, fresh quotes or
  independent provider confirmation.

There are 39 new clock regressions; the final stable-tree suite passes 4296 tests
with 6 skipped (404.39 seconds). Ruff, mypy (319 files), governance (180 checks),
whitespace and scoped known-pattern privacy/disabled-default checks pass. All 475
tracked/new Python/config inputs have the same before/after content fingerprints.
These are working-tree checks, not an isolated release, universal secret scan or
provider-truth qualification. No new live-provider permission or coverage is tested.

## Remaining Boundaries

Rejecting a fetch before ingestion produces no new ingestion audit row. Existing
data remains existing data, not proof of a successful update; an unattended
worker still needs its separately approved durable pre-fetch attempt/recovery
integration. This guard does not activate that worker, a scheduler or retries.
The error is a producer-clock defect, not a transient provider permission/outage
classification; repeating the same bad clock is not a recovery policy.

Legacy nonzero-offset records remain rejected pending explicit compatibility
review. Other retained producers and historical records still need their own
clock/identity audits. No universal clock or source-quality certification follows.
Yahoo stays LOW/retrieval-time with unverified native price basis, session,
corporate-action and independent consistency limitations. No freshness, PIT,
financial/technical strategy or score promotion. Framework/schema/migrations and
dependencies are unchanged; execution/notifications stay disabled; PIT UNSUITABLE
and production NOT_READY persist. No real database writes, broker/Paper/execution
logic, credentials, commit or push occur in this slice. 271 remains deferred.
