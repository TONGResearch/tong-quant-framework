# Direct CNInfo Artifact Evidence

## Purpose And Boundary

`WP-DATA-002` adds a direct evidence path for China A-share disclosures. It
captures official CNInfo announcement metadata and, when explicitly requested,
the associated public filing document. It performs no filing interpretation,
research scoring, portfolio action, notification delivery, or trading action.

Direct evidence uses provider identity `cninfo_direct`. Evidence transported by
AKShare remains `cninfo_via_akshare`. These identities must never be merged even
when they describe the same announcement.

## Flow

```text
CNInfo public stock directory
  -> bounded announcement query
  -> normalized ProviderEvidenceRecord
  -> optional bounded document download
  -> SHA-256 content-addressed ProviderArtifactStore
  -> one SQLite transaction
       ingestion_batches
       provider_evidence_records
       provider_artifacts
       provider_artifact_observations
       provider_limitations
       data_availability_warnings
```

The direct HTTP client permits only the official HTTPS query, stock-directory,
and `static.cninfo.com.cn/finalpage/` document scope. It enforces timeout,
retry, minimum request interval, page-count, page-size, response-size, redirect
domain, and PDF-payload checks. It never accepts credentials.

## Capture

Metadata-only capture is the safest first check:

```bash
python scripts/capture_cninfo_artifacts.py \
  --symbol 600000 \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --metadata-only
```

Document capture is explicit and bounded:

```bash
python scripts/capture_cninfo_artifacts.py \
  --symbol 600000 \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --max-pages 2 \
  --max-artifacts 10
```

Add `--compare-akshare` to persist a direct-versus-transported consistency
report for the same symbol and period. A comparison result remains calibration
evidence and cannot upgrade trust automatically.

Artifacts default to `data/provider-artifacts/sha256/<prefix>/<hash>.pdf`.
Paths are relative, content-addressed, mode `0600`, and idempotent. SQLite stores
metadata and observation history, not document bytes. If a database transaction
fails after a new file is written, that new file is removed.

## Audit Semantics

- A captured artifact is idempotent by provider, dataset, subject, source
  identity, source URL, and content hash.
- Every requested capture receives an immutable observation with `captured`,
  `missing`, or `unavailable` status.
- The same announcement ID observed at multiple URLs remains visible in its
  observation history.
- Correction/supersession IDs are stored only when CNInfo supplies structured
  relationship evidence. Titles alone never invent a relation.
- Pagination and artifact limits produce explicit warnings. Unfetched files are
  not counted as captured or silently discarded.

## Trust And PIT Policy

Direct records use `AvailabilityPrecision.EXACT` for the official publication
timestamp and currently retain `DataTrustLevel.MEDIUM`. The real 2026-08-21
smoke check proved the current metadata and PDF path, hash, permissions, schema,
and parser behavior. A same-day `300777` comparison matched 3 of 3 announcement
IDs, titles, symbols, and normalized timestamps against `cninfo_via_akshare`
with no conflicts. This deliberately narrow smoke sample did not prove
historical coverage, correction continuity, or long-term contract stability.

No PIT readiness classification changes in this work package. Promotion
requires a representative direct/transported baseline, conflict review,
coverage measurement, and explicit governance approval.

## Operations

The direct metadata probe is included in the scheduled provider contract
monitor with one-page, metadata-only limits. The live integration test remains
disabled unless `TONG_QUANT_LIVE_CNINFO=1` is set.

Review CNInfo's current public-site terms and disclosure before increasing
frequency or scope. Do not reduce the built-in interval below its conservative
minimum or use automation to bypass access controls.
