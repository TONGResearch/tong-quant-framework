# One-Shot Refresh Admission And Recovery Contract V1

Date: 2026-11-05, Asia/Kuala_Lumpur. WP-LAUNCH-001 design delivery only.
Status: contract specified; runtime implementation and operational acceptance
pending. No collector, lock, reservation, migration or schedule is activated.

Same-day follow-up: [fetch-side read guard](../refresh-fetch-lease-guard-2026-11-05.md)
is implemented separately. The original required API below is no longer entirely
missing; resource ownership, collector integration and acceptance remain pending.

Later same-day follow-up: [one prepared local lock](../prepared-resource-ownership-2026-11-05.md)
now implements the first ownership primitive. It neither provisions coordinator
files nor maps/acquires a complete resource set; broader integration remains pending.

## Why Another Boundary Is Needed

The durable ledger fences a job, not all storage writers. Read-only capacity
preflight does not reserve bytes. A deterministic synthetic counterexample now
checks two concurrent preflights: retained bytes 800, per-artifact plan 100,
retained limit 950. Both independently project 900 and pass, although both
artifacts together would reach 1000. Neither preflight writes files or grants
collection authority. This is expected diagnostic behavior, not provider evidence
or a defect repaired by relabeling the result as an enforced quota.

The November 4 sync review also found old candidate 8794b57 still contains the
shared-original rollback bug. The local repair is uncommitted; its working-tree
tests cannot qualify that candidate. A reviewed publishable code baseline is a
separate deployment gate, not something storage admission can waive.

## Smallest Implementable Scope

- One explicit immutable refresh job and its exact planned scope; no universe
  expansion, scheduler, market-close inference or source fallback.
- Existing AKShare daily-equity and Yahoo price/native-annual snapshot bridges
  only when their individual capture contracts can satisfy the declared bounds.
  An unsupported bridge remains blocked, not silently implemented by the worker.
- An already initialized/current-schema dedicated or reviewed restored database
  and explicit artifact root. No silent user-DB initialization or migration.
- One cooperating supervisor per declared resource set. Existing legacy ingestion,
  cache writers and manual capture commands are NOT coordinated today; they must
  be quiesced or separately integrated before a controlled run is admitted.
- No ResearchReport, scoring, validation-eligibility, portfolio, notification,
  broker, order, paper-trading or execution edge. Retained observations remain
  unqualified. No new Signal substitutes for the operational attempt ledger.

## Proposed Admission Inputs

The future orchestrator must pin job ID, expected row version, scope/plan hashes,
worker ID, attempt policy, reviewed runtime code identity and configuration hash.
Pin actual artifact-root and database resource identities, explicit byte budgets,
maximum wire/decoded/frame/artifact sizes, memory/deadline limits and staging,
cache and database/WAL allowances. Credentials remain environment-only and never
enter identities, receipts or exception strings.

Root reference hashes describe device/inode/metadata, not portable paths or
ownership authentication. Reports from another root, before lock creation, from
an earlier attempt or with changed policy/code cannot be reused as admission.
Caller-provided labels, an old Git commit plus dirty flag, or a passing preflight
alone are insufficient. No default production budgets are chosen by this design.

## Admission Sequence

1. Validate the exact reviewed scope, code/config contracts and existing database
   metadata in read-only mode. Registration may already have created a queued
   job, but this operation must never create a database to make validation pass.
2. Acquire exclusive, nonblocking advisory ownership of ALL declared cooperating
   resources before capacity inspection. Resource ordering must be deterministic
   when database/artifact/cache devices differ, avoiding lock-order deadlocks.
   Busy ownership returns ROOT_BUSY without network access or a consumed provider
   attempt. A single artifact lock does not coordinate other roots sharing a DB.
3. Under that ownership, bind current resource identities and re-run complete
   database/schema checks, capacity scans and volume-space checks. Include retained
   orphan/temp bytes;
   no deletion, favorable partial totals or deduplication discount. Artifact-only
   preflight cannot certify database/WAL, cache, memory or temporary-volume space.
   Keep the original preflight's reservation/quota/authority flags false; advisory
   ownership is separate operational evidence, not permission to relabel it.
4. If resources are unknown/blocked, leave the job queued and return a safe
   operational diagnostic. Do not classify resource shortage as a provider outage
   or fabricate a failed provider response. No capacity-reservation table is
   proposed for the initial exclusively serialized resource set.
5. Claim the job using its current expected row version; a concurrent claim or
   changed scope aborts before fetch. Persist the attempt BEFORE network access.
   Use a fresh UTC clock after potentially slow scans. Never hold a SQLite write
   transaction across network access or a filesystem wait.
6. Recheck current FETCHING ownership immediately before download and at each
   subsequent handoff. The existing validate_live_lease method is RETAINING-only;
   the new validate_fetch_lease read guard is the appropriate explicit phase check,
   not a substitute for resource ownership or subsequent handoff fencing.
   The capture deadline plus retention margin must fit the finite attempt
   lease. Do not renew/extend leases without a separately versioned contract.
7. Capture ONCE through a bounded provider bridge. An SDK-native request timeout
   or post-download size check is not a transport, decoder or memory bound.
   Enforce limits before oversized buffers/frames and declared staging overflow;
   disable or explicitly budget SDK caches. Unsupported bounds block that bridge.
   Child transports may not publish artifacts, mutate shared caches or use SQLite.
8. Validate the complete captured batch, actual sizes, scope, source provenance,
   hash and UTC chronology. Retain the actual capture/availability time; no
   pre-fetch cutoff/backdating and no widened PIT policy to hide elapsed time.
   Pin a separate actual retention cutoff no earlier than the capture, preserving
   the original query scope; never freeze the clock to pass an old request cutoff.
   Start RETAINING with the exact captured hash through the existing repository.
9. Pass a fixed captured-batch adapter into neutral ingestion with refresh_lease;
   its fetch must return that exact batch, not download again. Recheck lease and
   resource ownership before publication and before commit. The existing atomic
   DB batch/evidence/attempt association remains the only receipt-write boundary.
10. Inspect that exact linked batch and explicit originals under retained ownership.
    LINKED_FAILURE_BYTES_MATCH remains a failed snapshot. Even LINKED_BYTES_MATCH
    does not complete/reset a job, advance a checkpoint or admit research/PIT.
11. Stop/reap every child transport before releasing ownership. Persist no invented
    success if receipt inspection or post-commit reporting fails. Release descriptors,
    not published content, then return fixed safe codes and exact receipt hashes.

## Proposed Ownership Rules

Use local POSIX descriptor-based advisory locking in the first implementation;
unsupported/network/distributed-filesystem semantics require separate acceptance.
A fixed private zero-length lock inode must be shared by every cooperating writer.
Reject symlinks, special files, wrong ownership, unsafe permissions and unexpected
hard links. Open through a no-follow root descriptor and recheck identity after
acquisition. No credentials, PID file, response body or user path in lock contents.

Do not unlink/recreate a lock file to clear BUSY: that can split ownership across
two inodes. An expired SQLite lease does not release another live process's OS
lock. Fail closed rather than steal it. Hold ownership through capacity checks,
bounded fetch, publication, commit and receipt inspection. This serializes only
cooperating writers; unrelated processes, OS snapshots and user quotas can still
exhaust space. Allocation failures must remain visible; no hard-quota claim.

Keep coordinator lock inodes separate from SQLite data and artifact files. Merge
roles that name the same device/inode/file-type resource, then sort those physical
keys, never caller path order. Aliased resources are not independent budgets.
All cooperating callers need the same explicitly approved coordinator location;
matching keys with different lock files do not coordinate. The initial MVP may
reject aliased/multi-root layouts instead of claiming unsupported coordination.
The complete lock set must be acquired or released without claiming/fetching.
Do not derive lock identities from mutable root_reference_hash timestamps: create
the coordinator first, use stable physical ownership identity, then generate fresh
capacity metadata. Authorized publication can change directory times without
changing ownership; recheck device/inode and coordinator binding separately.

Close-on-exec alone does NOT prevent inheritance across fork without exec. The
implementation must isolate transport children with a tested spawn/descriptor
cleanup contract; a child must never unlock its parent's shared open-file lock.
Kill/reap children before release, preserve fencing on every late return, and test
parent-crash/child-survival behavior. Do not assume an expired lease stops a child.

## Failure And Recovery Matrix

| Boundary | Required outcome |
| --- | --- |
| Busy lock, incomplete capacity or changed code before claim | No fetch, no new provider attempt, queued job unchanged; safe blocked diagnostic. |
| Claim succeeds, no response arrives | Persist only an observed safe failure; no fabricated response/hash. Existing finite retry rules apply only to their actual transient codes. |
| Worker dies after claim or download | Expiry requires reconciliation, not blind re-claim or automatic re-download. No invented response if it was never durably captured. |
| Size/storage failure after claim | Stop the child; keep exact phase and missing state. Resource-specific safe codes need a reviewed version/schema contract if current enums cannot express them; do not disguise the failure as permission/network success. |
| Bytes publish, database transaction rolls back | Retain published bytes; DB evidence stays rolled back. Never created-only deletion or one-registry GC. Next preflight still counts those bytes. |
| DB commit succeeds, worker crashes before reporting | Reconstruct the exact attempt batch and originals; no second ingestion or favorable symbol/date match. No automatic checkpoint transition. |
| Process/OS lock disappears | Re-observe files, capacity, DB and lease history. Lock release is not proof the previous capture failed or left no data. |
| Files/directories lack durable publication after power loss | Keep missing-byte diagnostics. Advisory ownership is not cross-store atomicity, directory fsync or encrypted restore acceptance. |

## Implementation Acceptance Tests

Require real separate-process tests, not threads alone: two independent jobs
compete for the same resource; only one can reach a fake provider. A blocked
capacity scan must invoke neither provider nor claim. Include root replacement,
symlink/hard-link lock substitution, lock-file deletion hazards, different-resource
ordering, missing schema, changed policy/root/nonce, expired lease and stale child
returns. Record that legacy writers remain outside the contract until integrated.

Inject crashes before claim, during fetch, after publication, during SQL commit
and after commit. Test persistent BUSY without forced unlocking, OS crash release,
fork inheritance, no descriptor leaks, transport/memory/size limits, disk full,
empty/error snapshots, exactly one capture, safe credentials/error handling and
unchanged false research/trading authorities. Use temporary databases/archives and
fake providers first; real capture acceptance remains separately authorized.

## Delivery Status And Next Action

This document and one synthetic concurrent-preflight test are the delivery.
No runtime guard/reservation implementation, worker CLI, schema/default/version
change, source capture, user data migration, commit or push. Next implementation
slice should prove the ownership/descriptor boundary and integrate the separately
delivered fetch-side read guard under these tests. New persistence/codes require migration
review, not sidecar databases or unregistered tables. Scheduling and deployment
remain separate gates; GitHub review must package the local repairs first.

PIT stays UNSUITABLE, production NOT_READY, R1-R6 partial, WP-LAUNCH-001 ready/not
accepted. Execution and notification defaults stay disabled; no live trading,
broker submission, automatic trading or asset allocation is introduced.

## Verification Of This Design Slice

One new synthetic concurrent-preflight test; 112 expanded focused checks pass.
Full working-tree suite: **3276 passed / 6 skipped**, 157.09 seconds. Ruff,
mypy (306 files), governance (157 checks), scoped dependency/credential review
and git diff --check pass. Six opt-in network skips are not provider evidence.
Both retained sample database SHA-256 values remain unchanged. No provider call,
real archive inventory, user-DB migration, commit or push. No runtime guard is
claimed by these tests, and mixed-worktree checks are not release-candidate QA.
