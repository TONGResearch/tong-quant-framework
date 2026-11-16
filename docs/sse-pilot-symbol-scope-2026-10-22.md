# SSE Pilot Symbol-Scope Repair

Package: `WP-LAUNCH-001`, still `ready`. Review completed October 22, 2026.
This report completes the software repair begun during the October 21 check.

## Reproduced Defect

The main-board evaluator checked exchange, market, category, currency and bound
runtime evidence, but not the symbol itself. A synthetic fixture could substitute
STAR symbol `688363`, retain an SSE exchange tag and otherwise consistent HIGH
evidence, and recompute its security-content hash. Before repair, requesting 250
shares produced 200 and a previous close of 10.05 produced a 9.05--11.06 ordinary
main-board band. These were synthetic calculation results, not orders or a live
incident. Hash consistency alone did not establish board scope.

## Repair and Ownership

- `markets.sse_references.is_sse_main_board_pilot_symbol` defines a conservative
  six-digit ASCII 600/601/603/605 boundary for this pilot only.
- `SSEMainBoardEvaluator` applies it before all buy-quantity, sellable-quantity,
  sell-quantity and price-band calculations. Out-of-scope instruments fail closed
  even with consistent synthetic SSE/HIGH metadata.
- `SSERuntimeInputReader` uses the same boundary and retains mismatched instruments
  with `instrument_scope_unverified`. No database records are hidden or deleted.
- A matching prefix is necessary but insufficient: existing exchange, asset,
  currency, calendar, security-status, listing-phase and evidence checks remain.
  No symbol test is a dated security master or proof of listing/tradability.

Calculation version is centralized as
`sse-main-board-calculation-v1.2-symbol-scope`; runtime inventory version is
`sse-runtime-input-v1.7-symbol-scope`. Changed derived results receive different
version-bound identities. Old records/hashes are not rewritten or automatically
qualified; consumers must explicitly re-evaluate them when needed.

## Tests and Scope

Sixty-nine new cases: four bounded-prefix fixtures preserving evidence checks,
15 rejected symbol forms across four calculation paths, and five SQLite-backed
inventory fixtures preserving the original records and exposing gaps. Rejections
cover STAR, B-shares, BSE old/new codes, SZSE, funds, out-of-bound prefixes, invalid
lengths, non-ASCII numerals and letters. All use local synthetic evidence, not
new provider data or claims about current security listing status.

Completion checks:

- Full pytest: **1461 passed, 6 skipped**, 48.15 seconds. This includes all 69
  new cases; skipped tests are not claimed as verified live-provider coverage.
- Ruff: all checks passed.
- Mypy: no issues in 242 source/script files.
- Governance: 100 checks passed, including the new required repair report.
- `git diff --check`: passed.

These are local working-tree results, not remote CI, independent data review,
deployment acceptance or verification of every earlier uncommitted change.

## Remaining Gates

Authoritative dated instrument/board history, original source availability,
calendar/status/phase/actions, account permissions and settlement evidence remain
separate requirements. This bounded guard deliberately does not claim exhaustive
exchange code allocation or infer a normal listing from a code prefix. Rejecting
an unknown code is safer than silently extending this pilot to a different board.

Real candidate work still needs independently reviewed financial inputs/sector
scoring, screened research reports and falsifiable technical-plus-fundamental
validation. Passing software tests is neither a validated strategy nor an
investment recommendation. No database/schema migration, new data population,
Execution/Paper/Broker/Portfolio/Notification logic, commit or push is introduced.
PIT remains `UNSUITABLE`, production `NOT_READY`; disabled defaults remain intact.
