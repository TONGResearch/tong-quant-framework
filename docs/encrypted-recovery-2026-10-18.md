# Encrypted Recovery Observation: October 18

## Verified Destination

The owner asked Codex to locate the existing encrypted backup. It was found
at iCloud Drive's `TongQuantEvidenceBackup.sparsebundle`. `hdiutil isencrypted`
confirmed encryption and mounted-image metadata independently matched that
exact image to `/Volumes/TongQuantEvidenceBackup` with `image-encrypted=true`.
The system image mounter unlocked it; no password was requested in chat,
supplied as a command argument or captured by the recovery tooling.

The existing volume is approximately 64 MiB. The drill used a new directory:

`TongQuantRecoveryDrills/research-8794b57-20261018T151541Z`

Older evidence archives and source databases were not overwritten. Real
snapshots, copied evidence, reports and failure diagnostics remained on this
encrypted volume. Temporary isolated restore copies created by this drill
were removed only after verification/diagnosis to bound peak disk usage.
The encrypted volume was subsequently safely detached, not force-unmounted.
Its directory is therefore unavailable until the image is mounted again.

## Rejected First Attempt And Repair

The first exploratory restore passed existing integrity/count checks but
failed an additional SQLite dump-content comparison. Independent comparison
confirmed the retained snapshot matched the original and that the restored
copy differed only in `schema_metadata` rows. The cause was unconditional
`SQLiteStore.initialize()` during an already-current-schema restore, which
rewrote metadata timestamps. This was not lost business data or a source write.
`initial-failure-diagnostic.json` preserves the rejection, hashes and cause.
The failed temporary restore copy was removed; its verified snapshot was
retained and reused, not silently replaced.

`SQLiteBackupService` now skips initialization when no migration is required.
New backup manifests include independent logical source/snapshot hashes.
Same-schema restores compare logical source/restored hashes and require
`same_schema_content_verified=true`. Supported older schemas still run
forward migration on their isolated copy, but explicitly report this flag
false: whole-dump equality across a schema transition is not claimed.

The new contract is `sqlite-iterdump-content-v1`: standard SQLite dump statements
are streamed into SHA-256 inside a read-only transaction, without exporting SQL
or row values. It is SQLite-version/representation/row-order sensitive, not a
canonical cross-version forensic database fingerprint. Embedded NUL text is
rejected because SQLite quote()/iterdump() would truncate it. Integrity audits
now keep one read snapshot and explicitly close their connections; backup
connections are explicitly closed too. The existing audit hash remains an
integrity/schema/count identity, not a row-content hash.

## Actual Retained Results

| Scope | Snapshot | Isolated restore content | Registered evidence |
|---|---|---|---|
| Operational baseline | Retained | Matches source/snapshot | 4/4 copied and verified |
| Exploratory pilot | First-attempt verified snapshot retained | Corrected retry matches source/snapshot | 4/4 copied and verified |

The original exploratory backup service manifest was not retained before the
first driver aborted. Its report explicitly labels the retained snapshot's
observational re-verification rather than inventing that original manifest.
The retry's restore report is retained. Operational backup/restore reports
include the strengthened service fields. Three raw market-rule files and two
rule-capture JSON files were separately copied and hash-verified.

A separate read-only verification then rechecked manifest/report/file hashes,
snapshot database integrity, dump content, all eight registered artifacts and
the five explicitly inventoried rule/capture files. Original database integrity
audit identities remain unchanged, and original/snapshot/restored/source-after
dump comparisons matched under SQLite 3.49.1:

- Operational dump: `f7ac1a6050dbb4940e2a32bc81113da46785c2f77c81b3c49b7fd3794e961676`
- Exploratory dump: `072ebbade5cf9757f01b315b287b36b65c57ec374c3531af80576115fa646753`
- Retained manifest: `555d4867de632f296b585abe8c3175f161454be8f976a1ec1ef4c3db0eab1233`

The manifest records reviewed parent commit `8794b572f27262d73abdb031103b3bd57035efd8`,
`source_dirty=true`, the code identity actually used for the retry and the
hash of an archived implementation patch. This is not a falsely clean Git
release. The final NUL-text guard/test was added after that retained patch;
the patch is not claimed to contain all final working-tree changes. Original
databases were subsequently read through the final guard as well.

## Verification And Remaining Gates

Final local verification: **961 passed / 6 skipped**; Ruff and mypy pass
(224 source/script files), governance passes 83 checks and whitespace checks
pass. This final working tree has not been rebuilt/released or tested on an
independent machine; no remote CI claim is made.

Five new regression cases cover no current-schema initialization, same-count
content changes during backup and restore, closed read connections and rejected
lossy NUL text. Framework 0.8.0, schema 0.8.2 and migration 0010 are unchanged;
there is no DDL, broker, Paper, portfolio, notification or execution change.

This proves an encrypted **same-host** recovery exercise for the two explicit
datasets, not independent-device recovery, complete inventory of every ignored
file, code-history backup, iCloud upload completion or source authenticity.
Existing backups/manifests do not automatically gain the new content guarantee;
re-verify them when needed. Schema-transition domain-content comparison remains
open. PIT stays UNSUITABLE, production NOT_READY, and all live authorization
remains false. No GitHub push or readiness promotion was performed.
