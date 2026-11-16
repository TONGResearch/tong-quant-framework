# Read-Only Artifact Capacity Preflight

WP-LAUNCH-001 adds `data.artifact_capacity` and
`scripts/inspect_artifact_capacity.py`, version `readonly-artifact-capacity-v1`.
This is a bounded current-filesystem diagnostic for a single declared future
artifact. It is not an enforced storage quota, reservation, worker or activation.

## Contract

`ArtifactCapacityPolicy` is immutable and requires explicit positive integer
limits for maximum artifact bytes, maximum retained logical bytes, minimum free
bytes and staging headroom. There are no production storage-budget defaults.
Diagnostic limits default to 10,000 entries and depth 16, with hard ceilings
100,000 entries/depth 32. The artifact limit cannot exceed the retained limit.
Policies and planned sizes are revalidated before filesystem access.

The root must already exist. POSIX no-follow descriptor traversal rejects root
and ancestor symlinks and traversal components. Scanning follows directory
descriptors, never symlinks; special files and different-volume entries prevent
a complete result. No file contents are opened. Every regular filename counts,
including unregistered originals, temporary/hidden files and hard links. Hard
links are counted conservatively per name; no registry, extension or orphan
guess can exclude retained bytes. This is not an orphan or global-reference audit.

Entry/depth limits, unreadable metadata, observed entry/root changes or missing
volume-space metrics prevent a complete usage total. Partial observed counts
remain visible, but total/projected bytes and inventory identity remain null;
partial values must not be treated as current usage or free-space clearance.
Before/after available-space observations use `f_bavail * f_frsize`; take the
smaller result. Unsupported platforms produce an explicit non-success.

For a complete scan, `WITHIN_DECLARED_LIMITS` requires all three inequalities:

1. planned artifact bytes <= maximum artifact bytes;
2. observed logical file bytes + planned artifact bytes <= retained budget;
3. observed available space >= planned bytes + staging headroom + free reserve.

Equality is within the declared limit. Otherwise the result is BLOCKED, with
fixed reason codes. Unreadable roots/entries are UNKNOWN, not a favorable zero.
All results retain false `space_reserved`, `quota_enforced`, collection,
research-refresh and execution authorities. Report and policy hashes are content
identities, not authentication. Capacity timestamps describe the actual inspection,
not source availability or historical PIT reconstruction.
The root device/inode/metadata is hashed into a separate reference and inventory
identity, including for empty roots; filenames and absolute paths are not rendered.
These local metadata identities are not portable backup or ownership certificates.

## Operational Boundary

The CLI requires `--artifact-root`, `--maximum-artifact-bytes`,
`--maximum-retained-bytes`, `--minimum-free-bytes`, `--staging-headroom-bytes`,
and `--planned-artifact-bytes`. Optional `--maximum-scan-entries` and
`--maximum-depth` only bound diagnostic work. Output is stdout JSON: no paths,
filenames, raw exception strings, file contents, credentials or database data.
Exit 0 means WITHIN_DECLARED_LIMITS only; 1 means BLOCKED/UNKNOWN, 2 invalid input.
No collect/delete/retry/repair/schedule flags, directory creation or cleanup.

Logical sizes are not physical blocks, directory overhead, compression or quotas.
Free space concerns this artifact volume, not a separate database/WAL/backup
volume. A declared planned size does not bound a future transport, decoded payload
or multi-artifact batch. Other processes, snapshots and user quotas can consume
space between calls. Directory/stat checks detect some mutations, not an atomic
cross-directory snapshot or a hostile concurrent adversary. Count/depth bounds
do not impose wall-clock deadlines on unresponsive filesystems. Read-only
inspection does not prove write permission, encryption, source truth or PIT quality.

**Existing FileSystemArtifactStore and ingestion writers are unchanged and are
not constrained by this preflight.** Before one-shot integration, separately
review an explicit admission call, actual capture-size checks, staging and
database-space budgets, cross-process writer coordination/reservation and expiry
recovery. Passing a preflight must never authorize unattended collection by itself.
Do not solve full storage by deleting published originals, TTL cleanup or assuming
one database covers all references. Retention/deletion requires independent review.

## Scope And Follow-Up

Only synthetic temporary archives are scanned in this slice. No user archive,
sample database, source capture, provider permission, default budget, schema or
migration is changed. Source/trust/financial policies and trading boundaries stay
unchanged. PIT UNSUITABLE, production NOT_READY, R1-R6 partial; WP-LAUNCH-001 stays
ready/not accepted. Next: review/write the serialized bounded one-shot admission
and recovery contract before activating any collector. Encryption, restore and
independent data/strategy qualification remain separate gates.

## Verification

40 new synthetic tests; 111 expanded focused checks pass. Final working-tree
suite: **3275 passed / 6 skipped**, 170.62 seconds. Ruff and mypy (306 files)
pass, governance has 156 passing checks, git diff --check and scoped dependency/
credential review pass. Skipped opt-in network tests are not provider evidence.
Tests cover policy/size validation, exact thresholds, all regular names, hard
links, unsafe entries, root/path identity, different volumes, bounded partial
scans, mutation detection, descriptor closure, safe CLI errors and false authority.
Both retained sample database hashes remain unchanged. No original source capture,
real archive inventory, user database migration, commit or push. These tests are
not an independently reviewed release candidate or deployment acceptance.
