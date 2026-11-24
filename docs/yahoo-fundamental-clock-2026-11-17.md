# Yahoo Native Fundamental Capture Clock Guard

Work package: WP-LAUNCH-001. Status: ready, not accepted.
Started from reviewed GitHub baseline 4774193666113d9163e13ecfa56ca101d4f7a480.

## Defect And Scoped Repair

The native annual fundamental producer serializes retrieved_at and native row
availability as UTC, but the shared evidence identifier includes the original
capture ISO offset. Synthetic US/HK/MY same-instant captures reproduced equal
envelope bytes and normalized payloads with unequal evidence IDs. Reconstruction
from UTC could not reproduce those unsupported identities. Default clocks already
use UTC; this is not evidence that default-clock owner records were corrupted.

YahooFundamentalSnapshotAdapter now requires an aware, actual zero-offset capture
clock after download/clock read and before envelope/artifact/evidence construction.
Success and sanitized failure responses share this guard. Equivalent zero-offset
zone labels qualify; non-UTC request/read cutoffs remain supported. No market
timezone or publication-time rule is changed, and no pre-fetch protection is claimed.

Accepted UTC bytes/IDs and GLOBAL_FUNDAMENTAL_SNAPSHOT_VERSION remain unchanged.
Shared identity functions and existing rows are not normalized or rewritten.
Old unsupported captures remain blocked without an older-good fallback. Rejected
new fetches do not freshen older captures or create an ingestion audit row;
durable pre-fetch attempt/worker recovery integration is still pending.

## Verification

- Seventy-two new synthetic regressions: three markets, success/failure, naive and
  nonzero capture labels, both repeated New York DST folds, three zero-offset
  labels, independent request/read offsets, legacy records with/without a valid
  predecessor, immutable DB/WAL/artifacts, and rejected attempts after good data.
  Non-UTC cutoffs one microsecond before capture reject before retention and
  read no future evidence, including differing local/UTC dates. Equal instants
  remain equivalent across those dates; no market-day inference is introduced.
- Focused native fundamental tests: 187 passed, including the additional cutoff
  cases. Read-side LOW/retrieval_time,
  missing publication/revision semantics and all false admission flags remain.
- Six frozen-HEAD adapter success/failure vectors preserve exact UTC batches,
  envelope bytes and evidence IDs. Old nonzero defects reproduce; repaired
  captures reject them. This uses current shared contracts, not an old environment.
- Real retained MSFT/0700.HK/1155.KL inputs at their original October 27 cutoff
  reconstruct identically with old and current adapters. Each still has 28 native
  observations/seven parseable latest fields. Repeated receipts and binding
  checks agree; five pinned database/WAL/artifact files retain their hashes.
  No network, fresh capture, real DB write or accounting admission occurred.

Scoped read-only AI review found no implementation bug and requested the extra
non-UTC microsecond/local-date negative tests. Those twelve cases were added;
re-review confirmed the gap closed with no further issue in scope. The reviewer
did not run tests or inspect real retained data independently.

Final stable-tree pytest: **4428 passed / 6 skipped**, 406.64 seconds. Ruff, mypy
(319 files), governance (182 checks), whitespace and scoped known-pattern privacy/
disabled-default checks pass. All 476 tracked/new Python/config inputs have the
same before/after fingerprint:
4d9598a0871adfcabe9c6649d90195d0df9b59515052a138a38eadc241af49bc.
Only nine code/doc/config paths changed; no local DB/cache/artifact is included.
These working-tree checks are not an isolated release candidate or universal
secret/source certification. Exact isolated candidate review remains required
before any future commit/push.

## Remaining Boundaries

LOW trust and RETRIEVAL_TIME precision are unchanged. Native annual rows are not
canonical FundamentalFacts, actual publication dates, revision history, interim
coverage or independently verified accounting. Historical snapshots are not fresh
financial evidence; seven parseable fields do not establish financial completeness.
No financial score, holding/add/sell decision, ResearchReport or Validation authority
follows. Other producer risks in the SEC audit remain dataset-specific follow-up;
no blanket UTC rule or shared-ID migration is approved. 271 stays pending definition.

No schema, migration, dependency, framework/default, broker/Paper/Portfolio/
Notification/execution or trading changes. PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled. This slice is not committed or pushed.
