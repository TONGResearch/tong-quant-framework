# Native Research Dependency Baseline

This is a research installation baseline, not production or trading approval.
Supported runtime: **CPython 3.12, macOS arm64, macOS 14.0 or newer**. The OS
floor comes from the selected NumPy wheel. Linux, Intel macOS and Windows need
separate native resolution/validation; do not reuse this lock on those hosts.

## Artifacts

| File | Purpose |
| --- | --- |
| `runtime-macos-arm64-py312.lock` | 35 runtime dependencies with exact versions and native artifact SHA-256 values. |
| `dev-macos-arm64-py312.lock` | 48 dependencies in total, including runtime and the development/test tools. |
| `build.in` / `build-py312.lock` | Four explicitly pinned bootstrap/build tools; kept separate from runtime. |
| `*.manifest.json` | Target, minimum OS, dependency-specification hash, build-input hashes and exact selected package inventories. |

Runtime/dev locks are compiled from pip's JSON resolver report, not by writing
a dependency resolver or guessing transitive packages. The initial resolution
was constrained to versions already installed in the tested PyCharm environment.
The compiler checks the framework identity, selected root requirements, root
pins, download host, artifact identity/hashes and unexpected source builds.
Package URLs and package descriptions are not persisted in the manifest.

The manifests and locks are intended to be reviewed in Git. Their hashes detect
drift and bind content; they are not signatures or proof that upstream packages
are benign. Native wheels are not a complete OS/system-library lock.

## Installation Into a New Environment

Create a new environment with a reviewed Python 3.12 interpreter; do not use
`--system-site-packages` or replace the active environment. From the reviewed
project root, using that new environment's Python:

```bash
python -m pip --isolated install --only-binary=:all: --require-hashes -r requirements/build-py312.lock
python -m pip --isolated install --no-build-isolation --require-hashes -r requirements/runtime-macos-arm64-py312.lock
```

For test/development use, install `dev-macos-arm64-py312.lock` instead of the
runtime lock, after bootstrapping the build tools. Use only the approved PyPI
index or an independently reviewed mirror. Do not put credentials in command
arguments or requirement files. `--isolated` ignores user pip configuration;
the runtime source exception must not fetch uncontrolled build dependencies.

Then install the reviewed framework wheel with its separately recorded hash,
and run `pip check`, installed `status` and `preflight` outside the checkout.
The project wheel is deliberately not a package pin in the dependency lock;
its code/commit/wheel identity remains a separate release artifact.

**Source-build exception:** PyPI provides `jsonpath==0.82.2` as a source archive.
Its archive hash is pinned and it was built with controlled setuptools/wheel
using `--no-build-isolation`. Other source builds are rejected by the compiler
until reviewed. This is not a claim that the locally built wheel is bit-for-bit
reproducible or that source build execution is sandboxed.

## Regeneration and Review

1. Use a native supported interpreter and reviewed bootstrap/build tools.
2. Generate a pip report with `pip install --dry-run --ignore-installed
   --no-build-isolation --report REPORT.json --constraint REVIEWED-PINS.txt
   FRAMEWORK.whl` (append `[dev]` for the dev profile). Select public index and
   bounded network timeouts explicitly. Resolver reports may contain local
   paths and upstream package descriptions; retain them outside Git.
3. Compile into a **new staging directory**:

   ```bash
   python scripts/compile_native_dependency_lock.py \
     --project-root /absolute/project-root \
     --report /absolute/REPORT.json --profile runtime \
     --output-dir /absolute/new-staging-directory
   ```

4. Review changes, root constraints, native artifact hashes, source exceptions,
   OS floor and both manifests. Replace the checked-in artifacts only after
   review, then repeat clean installation and the full quality suite. The
   compiler never overwrites an existing lock/manifest pair.

Use the existing structured manifests to prepare reviewed version constraints;
do not blindly upgrade every package or use a developer `pip freeze` containing
private URLs/editable paths. Re-resolve each OS/Python/architecture separately.
The current Linux CI still uses its own dependency installation and does not
claim this macOS lock is validated on Linux. No new paid runner job was enabled.

Official references: [pip installation reports](https://pip.pypa.io/en/stable/reference/installation-report/),
[pip hash checking](https://pip.pypa.io/en/stable/topics/secure-installs/), and
[pip-tools hash generation](https://pip-tools.pypa.io/en/stable/#using-hashes)
(used for the four-package build lock only).
