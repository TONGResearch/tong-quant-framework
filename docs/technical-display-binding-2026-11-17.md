# Opt-In Daily Technical Display Binding

Work package: WP-LAUNCH-001. Status: ready, not accepted.
This is display-composition hardening, not a new strategy or data qualification.

## Defect And Scope

An offline synthetic audit reproduced six instances of one known composition
gap: direct render_equity_note accepted a different symbol, market, cutoff,
price series, source label or row count in diagnostics while retaining the
original price receipt/title. The normal overseas CLI already constructs its
two sections from the same snapshot; this audit did not demonstrate actual
mislabeling in that normal path or actual owner records.

TECHNICAL_CALCULATIONS_VERSION and GlobalPriceInputs use different input hashes.
Requiring those hashes to equal or merely renaming one would be incorrect.

## New Opt-In Path

application.technical_binding builds a separately versioned receipt only after
checking the full price receipt against an explicitly supplied GlobalPriceInputs
and recomputing the entire daily diagnostic with explicit TechnicalParameters.
It rejects different bar identities and non-equity scope, price/status mismatch,
future inputs and changed diagnostics. Empty, failed and latest-suspended inputs
remain missing/blocked observations; a consistent binding cannot make them usable.

The receipt includes instrument/market, actual UTC cutoff, original full asdict
Bar hash/count, exact price-receipt hash, parameters, calculation version, technical
input and complete output hashes, observed status and explicit false authorities.
All supplied rows, including duplicates or suspension observations, remain in
the source hash; arithmetic still uses the existing checked daily selector.
Equivalent cutoff timezone labels are allowed without rewriting source records;
different DST-fold instants are rejected. Original Bar serialization stays exact.

Rendering a document containing technical_binding requires the original snapshot
and parameters through keyword arguments. The renderer recomputes and compares
again, so a caller cannot bypass the check by rehashing a changed output/receipt.
This is not an authenticated source: replacing all original inputs consistently
can still describe untrusted data. Receipt consistency cannot establish original
provider truth, identity, sessions, adjustment basis, freshness or PIT qualification.

The CLI exposes --technical-binding in explicit read-only mode:

```text
.venv/bin/python scripts/inspect_global_technical.py \
  --database <existing-price-database> --artifact-root <existing-price-root> \
  --market us --symbol MSFT --as-of <aware-cutoff> \
  --technical-binding --format markdown
```

Use the same flag without --format markdown to retain the binding in JSON.
Capture is rejected before database/artifact setup. Missing data remains an
exploratory exit-2 result, not a successful validation. No network or capture
operation is introduced by the flag. The existing CLI supports US/HK/MY, not A.

## Compatibility Decision

- The flag is opt-in. Omission keeps old JSON, hashes, arithmetic and Markdown
  unchanged; existing files and official report identities are not rewritten.
- New bound notes have EQUITY_BOUND_NOTE_VERSION and receipts have
  TECHNICAL_DISPLAY_BINDING_VERSION. Legacy version constants remain available.
- A new receipt without original read-side inputs fails closed. Passing those
  inputs without an explicit receipt also fails, rather than implying a check.
- Old direct unbound rendering remains a known limitation. This slice protects
  the new explicitly selected path; it does not claim the old API is fully fixed.
  Default cutover needs separate reviewed compatibility/migration work.
- This receipt is composed before any optional filing combined hash, so new
  optional combined outputs bind it without changing old no-flag combinations.
- Optional calendar/long-horizon/holding checks retain their existing contracts;
  daily binding neither replaces them nor adds their sources to its proof.

## Verification And Remaining Work

New regressions cover the six mismatches, rehashed receipt contradictions,
rehashing both a diagnostic and its receipt, incomplete original-input pairs,
DST/equivalent cutoffs, source metadata, changed parameters, empty/suspended/
duplicate inputs, future availability, false-authority boundaries and immutable
deterministic results. CLI tests cover all three overseas markets, default output
preservation, unchanged diagnostic DB content and early capture rejection.
There are 59 new unit/CLI cases. Final stable-tree pytest passes 4224 tests with
6 skipped (694.93 seconds); related display/holding/timeframe tests pass 289.
Ruff, mypy (319 files), governance (178 checks), whitespace and scoped known-pattern
privacy/import/disabled-default checks pass. All 475 tracked/new Python/config
inputs have the same content fingerprint before/after the final run. These are
working-tree checks, not an isolated release candidate or universal secret scan.
An earlier run loaded a new test's incomplete fixture before its correction;
the final complete rerun above includes the corrected future-data regression.
Tests are not source/method admission.

A real offline rehearsal at the original MSFT November 15 and NVDA November 8
cutoffs binds 971 and 752 retained rows respectively, with repeated identical
JSON/notes and unchanged no-flag output. Six pinned DB/WAL/old JSON files retain
their hashes. Existing trend and multi-timeframe views compose without alteration.
These are old retained observations, not new quotes or a freshness/trust upgrade.
A separate owner-authorized read-only AI review reported no actionable finding
in this scoped implementation. It did not review source truth or certify a release.

Exact-candidate release review, default-interface migration,
qualified calendars/actions and combined financial/technical strategy validation
remain open. No schema, dependency, financial score, holding decision, Portfolio,
Notification, Paper, Broker or execution behavior changes. PIT stays UNSUITABLE;
production stays NOT_READY; execution/notifications remain disabled. No automatic
commit or push belongs to this slice. The owner-deferred 271 rules stay pending.
