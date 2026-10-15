# SSE Main-Board Rule Calculation Pilot

Review date: 2026-10-16, Asia/Kuala_Lumpur. Package: `WP-LAUNCH-001`.
Profile: `sse-main-board-2026-v1`. Calculation contract:
`sse-main-board-calculation-v1`.

## Scope

This is an evidence-bound research calculation for ordinary SSE main-board
A-share cash holdings. It produces `SSERuleCalculation`, with the value,
query, reference hash, coverage hash, input hash, calculation hash, reasons,
and warnings. It creates no orders, fills, broker calls, or paper ledger.

Existing context-free `ChinaAShareRules` methods still reject calls. The new
API requires explicit `SSECalculationContext` and `SSEReferenceBundle`.
No generic Instrument lot-size default is used.

## Reviewed sources

The [SSE release notice](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml)
identifies 2026-07-06 as the effective date and points to the deferred clauses.
The pinned bytes were downloaded from the official site, parsed, and reviewed
with that attachment. The three independent document hashes are committed in
`config/markets/sse-main-board-2026.toml`.

| Source | Reviewed interpretation |
|---|---|
| [2026 rules](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/10816482/files/e3a3b98e36894edca77841837936e006.docx) | Sections 3.1.4-5 exclude ordinary shares from same-day turnover; 3.3.8-9 set quantity increments and per-submission cap; 3.3.11/13/17 define tick and price-band calculations. |
| [Deferred provisions](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/10816482/files/c4510656662e48dc9d8d0deb8cc864b3.docx) | Deferred block-trading provisions are excluded from this auction-only pilot. |
| [Odd-lot clarification](https://www.sse.com.cn/lawandrules/guide/stock/jyglywznylc/tz/c/c_20230209_5716007.shtml) | Whole lots and the full odd remainder can be sold separately or together; the odd remainder cannot be split. |

Interpretations are paraphrased; the official originals remain authoritative.
The daily price band is not an intraday price-cage or execution-validity check.

## Calculations

- Buy quantity rounds down to a 100-share increment. Inputs above 1,000,000,
  negative values, booleans, or non-integers are rejected. A result of zero is
  a no-op calculation, not a valid submission.
- Sellable quantity excludes same-day purchases and older lots without
  settlement confirmation. Known remaining quantities, matching account and
  security, proven purchase sessions, no restrictions, visible timestamps and
  sufficient trust/precision are required. The calendar is never synthesized
  from weekdays. This is a restriction calculation, not a settlement engine.
- Sell quantity cannot exceed the eligible holdings or split their odd
  remainder. Unconfirmed older balances and exceptional same-day odd balances
  require separate account review rather than guessing the odd-lot balance.
- The ordinary daily band uses 10%, a CNY 0.01 tick, half-up rounding,
  minimum one-tick movement, and a one-tick floor. The input must be the
  previous explicit open session's unadjusted close, with a complete calendar
  between sessions and explicit corporate-action-free status.

The profile rejects unsupported exchanges/boards/account types, non-equities,
ST/suspension/delisting, IPO/relisting/unknown phases, adjusted closes,
missing/stale/future inputs, ambiguous coverage, and expired source review.
Decision-date checks use Asia/Shanghai, not the UTC calendar date.

Calendar content is bound by `calendar_input_hash`. Security content, listing
phase, corporate-action flags, instrument snapshot and raw-status hash are
bound by `security_input_hash`. Changing a flag without changing its evidence
is rejected. These hashes bind content; they do not independently verify a
caller's trust declaration. Authoritative input readers remain necessary.

## Source capture and portability

The application-level capture utility uses the existing content-addressed
`FileSystemArtifactStore`. It is configuration-reference capture, not another
market-data provider or a parallel price/fundamentals ingestion path.

```bash
.venv/bin/python scripts/capture_market_rule_references.py
```

The default command fetches only approved official SSE HTTPS paths, refuses
redirects, applies time and size bounds, and verifies the reviewed byte hashes.
A changed source requires a new review; it cannot silently update the profile.
`--source-dir` imports already-downloaded pinned documents conservatively at
the current import time. It does not claim their earlier download time.

The command outputs a content-addressed capture manifest and reference hash.
Load them with `application.market_rule_references.load_sse_references` using
the same profile, artifact root, and capture path. Missing, tampered, escaped,
or mismatched bytes fail closed. Identical repeated capture at the same time
is idempotent; later captures keep separate manifests.

Raw documents live under ignored `data/raw/market-rule-references`; capture
manifests live under ignored `data/processed/market-rule-references`. They are
not pushed to GitHub. A new device must recapture the sources or restore the
verified artifact store and its manifest. Code and reviewed source pins alone
cannot substitute for missing document bytes.

Availability is `RETRIEVAL_TIME`, bounded by completed capture and review time.
The source review has a separate 30-day expiry; this is a project review
policy, not the legal expiration of the trading rules. Source-document trust
is explicitly HIGH for this reviewed byte set only. No provider or unrelated
dataset receives a trust upgrade. The profile does not establish historical
source availability at the publication date or before this capture.

The real local source import passed byte and manifest verification:
capture `68fd1de5...32b30d2`, reference `a078c368...4e4eb18`.
This proves reference recovery, not readiness of stock/account inputs.

A second end-to-end run fetched all three sources directly with the new
utility and reloaded the verified bytes successfully: capture
`ce1330b8...3b052c2`, reference `9edd2412...fbac3c0`. It kept its new completed
capture time rather than inheriting the first import's availability.

Local verification: 416 tests passed, 6 skipped; Ruff, mypy (204 source/script
files), governance and git diff checks passed. Network calls remain explicit;
the new automated integration tests use synthetic source bytes and HTTP fakes.

## Remaining gates

1. Produce independently reviewed, PIT-visible runtime calendar, security,
   listing-phase, corporate-action, close, and account-lot inputs. Synthetic
   fixtures are not evidence that real data is ready.
2. Add intraday session/auction restrictions, price cages, fees, corporate
   actions, and other pilot requirements needed by a realistic fill model.
3. Bind exact Portfolio/Validation/Risk/policy, dataset-readiness, and rule
   calculation hashes at the future simulation boundary.
4. Complete `WP-LAUNCH-001` before making the deterministic paper-ledger
   package ready. Live execution stays disabled; PIT stays UNSUITABLE.
