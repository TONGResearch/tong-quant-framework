# Price Input Alignment: October 26

## Scope And Architecture

WP-LAUNCH-001 now connects the existing retained Yahoo China-A price observation
to `scripts/inspect_candidate_inputs.py`. The combined read-only snapshot exposes
financial inputs, existing market-value diagnostics, technical calculations and
the separate `yahoo_price_alignment` diagnostic at one explicit UTC cutoff.
No second ResearchReport, artificial queue, scoring grant or canonical fallback
is created. Existing global/BSE diagnostics remain usable: unsupported Yahoo
quote scopes are explicit and never guessed.

`research.technical.quote_alignment` calls the source-bound quote reader rather
than accepting an arbitrary caller-supplied price dictionary. It validates the
supplied bar subject/equity/currency/adjustment/visibility and uses shared daily
version selection. Latest failures, broken source bindings, tied captures and
latest suspensions cannot select older favorable prices. Every original bar's
full dataclass content, retained quote inspection and explicit matching policy
are bound into deterministic identity. Input order and equivalent UTC instants
do not change the result. Existing raw observations and schema are unchanged.

The separate centralized version is `yahoo-price-bar-alignment-v1`.
No provider SDK/network call is added to this diagnostic or research modules.
The CLI keeps its diagnostic-only exit code 2 even when a price is available.

## What The Comparison Means

- Quote age, capture age and daily-bar age are distinct elapsed UTC measurements.
  Missing limits remain UNASSESSED; missing inputs remain UNAVAILABLE. An
  illustrative 24-hour limit is not an admitted trading/session freshness rule.
- Date comparison uses Asia/Shanghai. Different market dates have no price
  residual, implied return or claimed provider conflict.
- Same-date snapshots and daily closes still have different price bases. An
  exact descriptive residual or equal number does not prove independent source
  consistency, exchange-close semantics or a presently executable price.
- Residual arithmetic is exact within a bounded decimal working range; extreme
  scales retain an explicit unsupported-numeric-range result, not a rounded
  residual. This does not qualify units, market capitalization or valuation.
- Financial freshness and cross-provider consistency are NOT_ASSESSED here.
  All valuation/scoring/validation/replay/execution/readiness grants are false.

## Actual Retained 002624 Example

This is an October 26 re-inspection of existing evidence, **not a new live quote**.
Two reads use cutoff `2026-10-25T15:10:07.279497+00:00`, start 2024-01-01,
nonfinancial profile, the existing `002624-2026h1.toml` trailing review and
explicit illustrative 86400-second quote/capture/bar limits.

- Yahoo price: 10.0 CNY; claimed timestamp `2026-10-23T07:04:33+00:00`.
- Latest supplied daily bar: October 19 07:00 UTC, close 9.94; 674 observed rows.
- Result: DIFFERENT_MARKET_DATE. No price residual or provider-conflict conclusion.
- Quote and bar: STALE under the illustrative limits. Capture:
  WITHIN_CONFIGURED_LIMIT. A fresh capture does not make an old quote fresh.
- Existing technical state: CONFLICTED; trend structure BEARISH. These are
  descriptive old-input diagnostics, not current buy/sell instructions.
- Financial missing metric in the requested set: ROIC. Dated share counts and
  market value remain absent/unqualified; retained Eastmoney capture unavailable.
- Financial policy remains NOT_ADMITTED; no report or score is invented.
- Both complete outputs agree. Alignment hash:
  `26025703110d4417e7e16117ba0b6f58fc3883ea102cbcf78e8a730dc10824fe`.
- Combined input review hash:
  `5d45299b88b6a8f779b2effe07adffbe63a7ac84115bf56b8e6451d05deb2e34`.

No new provider data is collected, no database migration/write is performed and
no source/trust classification is promoted. Research input alignment is now
observable; qualified coverage, screened reports and validated strategy outcomes
are still separate incomplete work.

## Tests And Remaining Work

New regressions cover missing/failed/tied/tampered quotes, old suspension
fallback, future/DST-fold bars, same-instant timezones, currency/identity/adjustment
errors, Shanghai date boundaries, exact age boundaries, unsupported scopes,
bounded exact arithmetic, full-bar hash changes and deterministic read-only CLI
integration. Offline fixtures verify software behavior, not real source truth.

Verification: full pytest **1924 passed / 6 skipped** in 61.50 seconds; 30 new
cases since the 1894-test checkpoint. Focused quote/alignment/market-value suite:
173 passed. Ruff passes; mypy checks 255 source files; governance has 111 passing
checks; `git diff --check` passes. Six opt-in real provider/notification checks
remain disabled and are not claimed as passed network validation.

Next: refresh permitted source-bound daily inputs, obtain independently reviewed
dated share-class-aware share counts and corporate-action context, then qualify
financial/technical data and evaluate explicit hypotheses out of sample with
realistic market constraints. Freshness policy must be calibrated separately.
No Paper/Broker/Execution/Portfolio/Notification development or live authority is
introduced. PIT remains UNSUITABLE; production NOT_READY; execution disabled.
