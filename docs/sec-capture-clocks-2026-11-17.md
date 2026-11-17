# SEC Capture Clock And Retained Identity Hardening

Work package: WP-LAUNCH-001. Status: ready, not accepted.
Scope: existing submissions, company-concept, filing-page and filing-body
producers. No new endpoint, financial fact, strategy or source admission.

## Verified Defect And Fix

All four producers serialize the capture timestamp in their retained envelopes
as UTC, but the shared evidence identifier hashes the original ISO offset.
Synthetic same-instant captures reproduce equal retained bytes with unequal IDs
under nonzero offsets. Readers rebuilding from UTC cannot reproduce those IDs.
Default clocks already use UTC; this is not evidence that owner records or normal
default-clock downloads were corrupted, nor a provider permission failure.

Each producer now requires an aware zero-offset capture clock after download and
clock read, before artifact/evidence/batch construction. Failure responses share
the guard. Equivalent zero-offset zone labels qualify by actual offset; nonzero
offsets and naive clocks fail. Non-UTC request/read cutoffs remain supported.
This is not a pre-fetch network guard or a restriction on publication timestamps.

Source normalization versions, accepted UTC bytes and identifiers are deliberately
unchanged. Shared evidence/observation ID functions are not changed: globally
normalizing them would rewrite historical identities. Old unsupported captures
remain retained and blocked, with no older-good fallback or silent repair.
Rejected new fetches leave no ingestion audit row and do not freshen existing
evidence. Durable pre-fetch attempt/recovery integration remains separate work.

## Verification

- Sixty new synthetic tests cover four producers, naive/Kuala Lumpur/New York
  repeated-clock folds, successful and failed responses, three zero-offset zone
  labels, independent non-UTC request/read cutoffs, and blocked legacy captures
  with or without older good evidence. Temporary stores/artifacts only.
- The legacy fixtures retain original bytes/IDs; read-side rejection preserves
  database/WAL/artifact hashes. An older valid capture remains readable only at
  its own earlier cutoff, not as a substitute for a newer blocked capture.
- Eight frozen-HEAD adapter success/failure comparisons, using current shared
  contracts, preserve exact UTC batches/bytes/IDs. Old nonzero-offset defects
  reproduce and repaired producers reject them. This is not an old environment
  reconstruction or independent provider calibration.
- Read-only real retained MSFT rehearsal at its original November 9 cutoff
  repeats ten period checks with exact old period/body input hashes. Three pinned
  DB/WAL/old JSON files retain their hashes. Catalog source binding succeeds;
  two historical archive pages are observed but neither is usable, preserving
  two gaps. No new capture, freshness, numerical admission or authority follows.
- Scoped read-only AI review caught an invalid synthetic failure code; changing
  it to the existing accepted network_unavailable code made those cases reach
  the intended guard. Re-review confirmed the fix and found no further actionable
  issue in scope. It did not run tests or independently inspect real retained data.

Final stable-tree pytest: **4356 passed / 6 skipped**, 439.16 seconds, including
the 60 new clock regressions. Ruff, mypy (319 source files), governance (181
checks), tracked/untracked whitespace and scoped known-pattern privacy/default
checks pass. All 476 tracked/new Python/config inputs retain the same before/after
content fingerprint (e0114f7659652afa8c26b01f120d91ecb941da363c020067dbbb0992e4e94416).
The 25 pending code/doc/config paths include earlier uncommitted slices; none is
a local database/cache artifact. These are working-tree checks, not an isolated
release candidate, universal secret scan or source/strategy qualification.
Full isolated candidate-tree checks and review remain required before publication.

## Other Producer Audit: Follow-Up, Not Blanket Remediation

The following is a source-only read-side/identity audit plus a shared primitive
round-trip demonstration. Except for the four SEC producers above and the earlier
Yahoo global-snapshot fix, these are NOT per-dataset end-to-end reproductions,
repairs, or evidence of corrupted real observations. Native availability times
must not be normalized indiscriminately. All follow-up needs isolated synthetic
success/failure, serialization, legacy-ID and reader tests before code changes.

| Producer or review | Observation | Evidence boundary / next check |
| --- | --- | --- |
| Yahoo native fundamentals | UTC envelope, original capture-offset evidence ID, UTC reconstruction | Static mismatch; test three markets and failure responses |
| Yahoo China quote | UTC envelope versus original capture ID | Static mismatch; prove valid/unavailable reader paths |
| Eastmoney market values | UTC envelope versus original capture ID | Static mismatch; prove valid/error retained bodies |
| HKEX/Maybank documents | UTC envelope versus original capture ID | Static mismatch; test both document and failure paths |
| AKShare daily/index | Frame/query artifact omits capture clock; storage uses UTC, IDs original offset | Daily reconciler rehash risk; index path separately unproven |
| AKShare statements | Frame omits capture clock; storage UTC versus original retrieval ID | Static rehash risk; prove after storage serialization |
| CNInfo direct | Disclosure ID uses UTC publication; observation ID uses original retrieval | Disclosure identity is not the same defect; audit observation separately |
| SSE calendar notice | HTML omits capture clock; storage UTC versus original capture ID | Current plan does not rehash ID; identity risk, not proved reader rejection |
| Massive | Response hash omits capture; original-offset ID and UTC storage | No retained-byte reconstructor located; audit retention contract first |
| Sina BSE | Availability is max(capture clock, request cutoff) | Non-UTC request can win even with UTC clock; clock guard alone insufficient |
| Legacy Yahoo chart bars | Chart hash omits capture envelope; original-offset ID and UTC storage | Not covered by global-snapshot guard; prove retention round-trip |
| AKShare suspensions | Raw frame omits capture; preflight uses original in-memory capture | Post-storage identity not certified |
| HK/MY manual financial reviews | UTC recorded_at envelope versus original recorded ID | Adjacent static mismatch; no review records changed here |
| CNInfo via AKShare | Intentionally market-local publication time | Not justification for a blanket UTC timestamp restriction |
| AKShare cache | Preserves retrieval ISO offset | Cache round-trip differs from database/artifact round-trip |
| Nasdaq and Yahoo global snapshot | Existing zero-offset capture guards | Scoped prevention only, not source/PIT certification |

Both shared evidence and artifact-observation identifiers hash ISO labels.
UTC storage can therefore expose the mismatch, but a provider that preserves
the original label or uses a separate publication timestamp needs its own contract
analysis. Do not change all clocks/IDs based only on this table. Tushare remains
frozen and was not reviewed or changed.

## Remaining Gates

Provider evidence trust/precision/continuity, corporate actions, qualified
sessions, historical gaps and financial/technical method validation remain open.
Source-bound does not mean independently qualified or fit for a holding/add/sell
judgment. 271 undefined terms remain deferred. No real database writes, schema,
migration, dependency, default, score, Portfolio, Notification, Paper, broker or
execution changes. PIT remains UNSUITABLE, production NOT_READY, execution and
notifications disabled. No commit or push in this slice.
