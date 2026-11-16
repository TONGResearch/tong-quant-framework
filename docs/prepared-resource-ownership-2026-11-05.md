# Prepared Local Resource Ownership

WP-LAUNCH-001 implements the first ownership primitive in
`data.resource_ownership`, version `prepared-local-resource-lock-v1`. It owns one
explicitly prepared coordinator inode. It is NOT a whole resource set, physical
disk reservation, enforced quota, capture worker or deployment approval.

## Preparation And Acquisition

An operator/reviewed provisioner must first supply an existing zero-length regular
file, mode 0600, owned by the current effective user, with exactly one hard link,
inside an existing current-user-owned mode-0700 directory. No automatic mkdir,
file creation, chmod, truncation, unlink, stale-file replacement or PID-file data.
These strict local assumptions are not an encryption/ownership authentication
certificate or approval of a network/distributed filesystem.
POSIX mode bits alone do not audit extended ACLs, mount policy or hostile same-user
access; approved provisioning/host security remains an independent prerequisite.

inspect_prepared_lock reads metadata through no-follow descriptors and returns
an immutable PreparedResourceLock pin: file device/inode, parent device/inode,
owner and version. Its fingerprint excludes path strings. Preparation is an
explicit review step, not a function to silently rerun after failed acquisition.
Retain the reviewed pins across attempts; re-pinning a substituted lock file could
split coordination. Secure creation and durable configuration/provisioning are
not implemented by this slice.

hold_resource_lock revalidates the pins and private-file constraints, opens the
existing inode read-only and tries POSIX flock LOCK_EX | LOCK_NB. Contention is
BUSY; an opening/permission failure is UNAVAILABLE, never guessed contention.
Other fixed codes cover unsafe inputs, changed identity, unsupported platform,
inactive ownership and uncertain release. Internal error messages do not include
paths, file bodies, exception text or credentials.

Only the OS-lock operation is nonblocking. Local registry bookkeeping is serialized;
filesystem metadata/open calls on unhealthy mounts can still stall. A future
supervisor must supply deadlines and supported-host/filesystem acceptance. There
is no fallback to a thread-only lock on unsupported hosts.

## Held Session

HeldResourceLock.validate checks the active session/current process, original
descriptor, current no-follow namespace and pinned file/parent identity. It
returns None, not capture authorization. Replaced/unlinked/unsafe files invalidate
the token for the rest of that context, even if an operator restores metadata.
The original OS lock remains held until context exit; validation failure must
not silently release ownership early. No raw descriptor is exposed by the public
API and held ownership cannot be pickled into a child worker.

Context exit closes only owned descriptors: it never uses LOCK_UN or deletes the
coordinator. Kernel close/process exit releases ordinary ownership. If close is
uncertain, the process is quarantined against further pin/acquire/validate calls;
there is no production reset API. Retire/exit that process and independently
reconcile before restarting. A new worker can remain BUSY while the old process
is alive; never force availability by removing its lock file. Synthetic fault
tests restore their own monkeypatched state, not a production recovery shortcut.

## Fork And Exec

The module registers POSIX fork callbacks once on import. They coordinate only
this module's active descriptors. A fork child closes copied ownership descriptors
without LOCK_UN, invalidates copied tokens and resets its local registry mutex.
It cannot use the parent's token, and exiting the child's copied context must not
unlock the parent's still-open description. Descriptors are close-on-exec too,
but close-on-exec alone is not a safeguard for fork without exec.

These hooks do not close other libraries' SQLite/cache descriptors, kill a child,
make arbitrary signal-handler/fork use safe, or prove all supervisor crash paths.
Real tests separately exercise child invalidation/descriptor closure, preservation
of the parent's lock, ordinary release and holder-crash release. The combined
parent-crash/long-lived-child case and broader supervisor shutdown/timeout handling
remain required before collector acceptance.

## Integration Boundaries

Cooperating callers must use the same reviewed coordinator inode. A different
file, a different coordinator directory, uncoordinated legacy writer or a hostile
same-user actor is outside the mutual exclusion guarantee. Pin checks detect
changes but cannot make an arbitrary cross-directory filesystem transaction
atomic against namespace tampering.

The mapping from actual artifact/DB/cache/staging resources to coordinator files,
stable ordering/deduplication and acquisition of the entire resource set remain
unimplemented. No existing ingestion/store/CLI is wired to this primitive.
Do not mistake a held token for verified capacity, a live refresh lease, provider
permission, a complete calendar/session, trust, PIT readiness or strategy evidence.
Still perform fresh under-ownership capacity/DB checks, pre-fetch lease fencing,
capture-once limits, later handoff checks and exact receipt reconstruction.

No database table, migration, record-model version or default changes. The new
version identifies this operational pin/ownership contract, not a source dataset.
All tests use temporary prepared coordinators, not user archives or databases.
Execution/notification defaults stay disabled; PIT UNSUITABLE, production
NOT_READY, R1-R6 partial, WP-LAUNCH-001 ready/not accepted. No provider calls,
collector schedule, trading functionality, commit or push is activated.

## Verification

22 new cases / 107 expanded focused checks pass. Full working-tree suite:
**3329 passed / 6 skipped**, 186.07 seconds. Ruff, mypy (307 files), governance
(159 checks), git diff --check and scoped credential/dependency review pass.
Six opt-in network skips are not provider availability evidence. Both retained
sample DB hashes match the preceding slice. No user coordinator is provisioned,
no real archive or provider is used and no code is committed/pushed. These checks
are not independent release-candidate validation or full supervisor acceptance.
