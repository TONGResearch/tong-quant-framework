# Native Dependency Baseline - 2026-10-18

Work package: WP-LAUNCH-001, partial deployment hardening.
Framework 0.8.0, schema 0.8.2, PIT UNSUITABLE, production NOT_READY.
Execution and notifications remain disabled. No Paper or live authorization.

## Delivered

- Native SHA-256 locks: 35 runtime packages, 48 dev packages including runtime,
  and four separate bootstrap/build tools. Existing tested versions were
  preserved rather than broadly upgraded.
- JSON resolver-report compiler using standard packaging APIs. It checks
  root identity/requirements, approved HTTPS source, chosen wheel metadata,
  artifact hashes, native target and the reviewed jsonpath source exception.
  It emits new files only, with cleanup of its own partial output on failure.
- Structured manifests bind lock content, build inputs and dependency specs.
  Re-rendering the exact lock from the manifest catches omitted/duplicated pins;
  installed versions are checked without importing any provider SDK.
- `deployment-preflight-v1.1` now separately checks lock integrity and actual
  installed runtime versions. Compatible-but-different versions are still drift.
  Unsupported host/architecture/Python/OS-floor cannot silently reuse this lock.

## Actual Verification

Created a fresh Python 3.12.10 venv on this Apple Silicon host, without system
site packages. Installed build and runtime packages with hash checking; installed
the separately hashed framework wheel without resolving unpinned dependencies.
Verified package origin beneath the new prefix and that user site packages,
the PyCharm venv and checkout `src` were absent from its operational import path.
The installed console and preflight were exercised from outside the checkout.
Then installed the hashed dev profile and ran the full suite in that environment.
Final local wheel SHA-256:
`1b3d3a25331e93a6a91ff709b33ce4e7d569be4812bba9d2dccf705f4622b513`.
It is a temporary uncommitted-source test artifact, not a signed release.
Regenerating both native locks/manifests from the retained pip reports produced
byte-identical outputs. This checks report conversion, not network or source-build
byte reproducibility.

Native profile: macOS arm64 / CPython 3.12, minimum macOS 14.0 due to the
selected NumPy artifact. This is same-host clean-environment evidence, not an
independent machine, Linux, Windows or broker deployment test.

Runtime and dev manifest/package checks passed. Runtime preflight has 15 host
checks; 13 pass, while dirty checkout and committed-source mismatch remain
blocked. No false overall pass was manufactured. The operational SQLite content
audit remains `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.

Full pytest: 884 passed / 6 skipped in both development and fresh environments;
Ruff, mypy (221 source/script files), governance and whitespace checks pass.
No schema migration or business-data rewrite. Sixteen continuation slices
remain local/uncommitted/unpushed; no remote CI run is claimed.

## Limits and Next Gates

One runtime dependency, jsonpath 0.82.2, is a hash-pinned source build using
controlled build tools. Other source builds require review. Package hashes
are integrity evidence, not upstream code-security review, release signing or
proof of deterministic source-wheel bytes. Development installation adjusts
its own packaging tool version; rebuild in the separately pinned build environment,
not an arbitrarily modified dev environment.

The initial all-platform pip-tools hash collection was stopped because it
downloaded unrelated platform artifacts. Its temporary caches were removed;
runtime/dev locks use only pip's selected native artifacts. Installed versions
in the original PyCharm venv were not changed, and operational data was not rewritten.

Next: review/commit the accumulated source, reproduce a clean release from that
commit, and verify encrypted database/source-artifact portability and recovery.
Continue real financial mapping/strategy evidence in parallel. Host reproducibility
does not resolve UNSUITABLE PIT data or authorize simulated/live trading.

See [dependency procedures](../requirements/README.md) and
[deployment operations](research-deployment-runbook.md).
