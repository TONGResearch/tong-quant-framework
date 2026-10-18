# Research Deployment Runbook

Scope: offline research-host installation and diagnostics only. This is not
authorization to run Paper Trading, brokers, live execution or allocation.
Framework 0.8.0; schema 0.8.2; PIT UNSUITABLE; production NOT_READY.

## What Is Implemented

The installed `tong-quant` console command and `python -m tong_quant` support:

```bash
tong-quant status --project-root /absolute/path/to/TongQuant_v1
tong-quant preflight --project-root /absolute/path/to/TongQuant_v1
```

`status` accepts an explicit `--config` and repeated `--config-override` paths.
`preflight` requires an explicit project root, applies the same configuration
selection and optionally audits `--database /absolute/path/to/existing.sqlite3`.
Relative paths are resolved against that root, not the caller's working directory.
Configuration, governance documents and databases remain external to the wheel;
the command does not create or migrate them.

Preflight checks Python 3.12, installed framework version, installed dependency
consistency, Git identity and a clean checkout, effective safe configuration,
governance consistency, and the existing SQLite integrity/migration/fingerprint
audit. It compares Python source hashes across the installed package, checkout
and explicit Git commit. Commit bytes are read through a Git archive in memory,
never extracted onto the filesystem.

Subprocesses have 30-second deadlines and their output/errors are not rendered.
Configuration credential fields are rejected before reporting. The report
exposes hashes and fixed diagnostic codes, not settings, database rows,
credential values or Git filenames. It does not inspect provider credentials
or make provider/broker network calls. The underlying database audit may be
expensive on large databases; schedule it during maintenance rather than treat
preflight as a low-latency liveness probe.

| Exit | Meaning |
| --- | --- |
| 0 | All scoped offline host checks passed at observation time. Not production/PIT/Paper/live approval. |
| 2 | One or more checks failed or required evidence was unavailable; or CLI arguments were invalid. |

The report always declares production/PIT readiness unassessed and Paper/live
authorization false. It is an advisory point-in-time observation, not a durable
authorization token or a service that continuously protects later operations.

## Controlled Installation

1. Review accumulated changes and obtain approval before committing/pushing.
   On the target device, use the reviewed commit in a clean dedicated clone;
   confirm remote identity separately. Do not interpret the currently dirty
   development checkout as a release candidate.
2. Build a wheel into a new external release directory, not source control:

   ```bash
   python -m pip wheel --no-deps --wheel-dir /absolute/new/release-dir /absolute/project-root
   ```

   Record its SHA-256, commit, Python/platform and build dependency versions.
   The initial macOS arm64/Python 3.12 native dependency locks are now in
   [requirements](../requirements/README.md); use the pinned build tools with
   `--no-build-isolation` for a controlled build. Artifact signing, other host
   profiles and independent target-machine qualification remain open.
3. Create a separate Python 3.12 environment and install the reviewed wheel
   with its compatible dependencies. Retain the old environment for rollback;
   do not replace the active installation in place. Provider tokens belong in
   the environment only, never TOML, SQLite, shell arguments or Git.
4. Restore approved data to an isolated path and run the documented database
   audit. A Git clone does not contain ignored databases, raw source artifacts,
   provider monitor history or local evidence bundles. Do not copy a running
   SQLite file with filesystem copy commands; use `SQLiteBackupService` and
   the [database engineering workflow](database-migrations.md) on an approved
   encrypted destination. Retain/verify referenced source artifacts separately.
   Run the [registered-artifact audit](artifact-portability-2026-10-18.md) on
   both source and destination using each database's explicit artifact root.
   Its passing result is not a complete recovery or production readiness gate.
5. Run installed `status` and `preflight` from outside the source directory.
   Keep execution/notifications disabled, strict PIT enabled, and prices
   unadjusted. Fix failed checks without weakening them or fabricating data.
6. Retain the operator-reviewed wheel/hash/configuration and database audit
   identities. A passing host check cannot replace the strategy/data/risk/
   recovery evidence in [the deployment gap plan](deployment-gap-plan-2026-10-16.md).

## Recovery and Rollback

Stop the research process before changing its selected release. Keep execution
and notifications disabled throughout. Switch back to the retained reviewed
environment and matching configuration only after checking schema compatibility.
For data recovery, perform a verified restore drill into a new path, compare
audits and migration fingerprints, and get operator review before selecting it.
Never overwrite the active source database or discard newer source evidence.
The preflight itself performs no backup, restore, migration or rollback.

## Local Verification - 2026-10-18

- Built a pure-Python research wheel and installed it into a separate temporary
  target. Both package origin and installed metadata were checked, not merely
  import success through an editable checkout.
- The installed console command ran successfully from outside the project.
- The wheel contains package code/metadata only, with no local SQLite, bytecode,
  virtual environment, raw data or provider artifacts.
- Local offline preflight remains blocked by the dirty checkout and its code
  not matching the current committed baseline. Runtime/checkout byte matching,
  configuration safety, dependency health and operational database audit pass.
  The database content audit hash remains
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
- CI now builds a wheel, installs it into an isolated target, checks installed
  origin/version and runs the console command outside checkout. These new CI
  steps have not run remotely because changes have not been pushed.
- Local smoke artifact: 210 wheel members; SHA-256
  `4c74bf77ce81df84c02b840ef863800649d62801be47deb8244769a75d2d7ff6`.
  This is an unreviewed temporary development build, not a signed release.
- Full pytest: 862 passed, 6 skipped, including 22 new preflight/CLI/identity
  regression cases. Ruff, mypy (219 source/script files), governance and
  whitespace checks pass. No schema change; all changes remain uncommitted
  and unpushed. The business database content audit is unchanged.

Local installation reused the project's already installed runtime dependencies;
this first smoke slice was not a clean-machine dependency-resolution test. The
subsequent [dependency baseline](dependency-baseline-2026-10-18.md) records a
fresh venv installation without borrowed site packages. No cloud/system service,
broker, simulated ledger or live trading process was deployed.

## Next Release Gates

Review and commit the accumulated changes; reproduce the wheel from that clean
commit; qualify dependency profiles on each target host; verify encrypted backup and
restore plus artifact portability. Continue the trusted-input/real-strategy
chain and governed Paper work in parallel. A finalized runtime installation
cannot make an unvalidated strategy or UNSUITABLE historical data deployable
for real money.
