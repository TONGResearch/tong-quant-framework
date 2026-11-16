# SSE Main-Board Rule Calculation Pilot

Review date: 2026-10-16, Asia/Kuala_Lumpur. Package: `WP-LAUNCH-001`.
Profile: `sse-main-board-2026-v1`. Calculation contract:
`sse-main-board-calculation-v1.2-symbol-scope` (accepts stored XSHG and legacy SSE
identifiers without rewriting instrument content, but additionally rejects
symbols outside the conservative 600/601/603/605 six-digit ASCII boundary).
Scope hardening reviewed on October 22; see the
[repair report](sse-pilot-symbol-scope-2026-10-22.md). A matching prefix does not
replace dated listing/status evidence or establish trading eligibility.

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

## Runtime input inventory (October 16 continuation)

`application.sse_runtime_inputs.SSERuntimeInputReader` reconstructs existing
inputs through MarketDataService in one consistent SQLite snapshot. It returns
the actual instrument and status, open **and closed** calendar sessions,
missing calendar dates, previous explicit open session and visible unadjusted
close, and every visible corporate-action observation/revision in the window.
It preserves ST/suspended/delisted records and original trust/precision.

```bash
.venv/bin/python scripts/inspect_sse_runtime_inputs.py \
  --database data/tong_quant.sqlite3 --symbol 600000 \
  --trade-date 2026-10-16 --as-of 2026-10-16T10:00:00+08:00 \
  --calendar-start 2026-10-02
```

Dates are explicit examples, not a request to reconstruct evidence that was
unavailable then. The CLI opens only an existing database with SQLite
`mode=ro`/query-only access. It never initializes or migrates a source, never
switches its journal mode, and never connects to a provider/broker. SQLite may
still need its normal WAL shared-memory sidecars; this is not immutable-file
snapshot access. `--database` must point to a separately populated operational
database, not a provider-monitor archive.

Exit 2 means missing database, unresolved input requirements, or an inspection
error. Errors report only their class, not possibly sensitive database values.
JSON output is screened for credential-like fields/assignments. No report or
database is written. The content hash covers the query/window, reconstructed
input objects, gap codes and reader version (originally `sse-runtime-input-v1.1`); it is not
a hash of the entire database. A changed visible input changes that hash.

The default local `data/tong_quant.sqlite3` was absent at the October 16 check;
the real command returned `database_missing` and left it absent. This describes
the local operational path only, not a loss of archived monitor evidence.

This inventory intentionally cannot create SSECalculationContext. Stored
TradingSession/Bar models do not carry reviewed exchange-scoped
trust/precision/raw-hash bindings. LISTED and an old listing date do not prove
normal phase or exclude relisting. An empty corporate-action query does not
prove action-free coverage. No account lots are imported or synthesized.
Those remain explicit gaps even with otherwise populated rows. Filling them
requires actual provenance, not setting favorable flags in a demo.

No schema change or migration is required. Synthetic integration tests cover
closed/missing dates, future revisions, adjusted-price exclusion, trust
preservation, exceptional statuses, corporate-action history, deterministic
hashes, concurrent writes, read-only writes/initialization rejection, and CLI
failure without file creation. They are not real-data evidence.

Continuation verification: 434 tests passed, 6 optional network tests skipped;
Ruff, mypy (206 source/script files), governance and git diff checks passed.
Execution and Notification remain disabled; PIT remains UNSUITABLE. The
work package remains partial, not complete.

The [subsequent real operational sample](operational-data-sample-2026-10-16.md)
populated that initially absent database and fixed observed ingestion defects.
The remaining input requirements still fail closed. Source normalization
now preserves retrieval-time visibility; it does not authenticate old rows.

## Remaining gates (unchanged)

The [real pilot coverage manifest](sse-pilot-coverage-2026-10-16.md) adds
`--pilot-coverage` to the same CLI for scoped research-input inventory. Optional
`--output` creates a new protected JSON report only; the source database remains
read-only. This supersedes the earlier no-report-write description only for
that explicit mode. It cannot create calculation context or grant readiness.

The [later notice-evidence slice](sse-calendar-notice-evidence-2026-10-16.md)
adds raw official notice capture and typed evidence reads. Runtime version is
v1.2 for that slice and includes scoped notice assertions, conflicts and review expiry in
the input hash. It does not fill absent dates or remove the calendar-provenance
requirement; the source remains MEDIUM/retrieval-time evidence.

The [subsequent price-evidence slice](daily-price-evidence-2026-10-16.md)
advances the runtime reader to v1.3. It includes raw-snapshot references and
exact previous-close bindings in the same read snapshot. A LOW-trust match is
not reviewed market-rule price authority and cannot create calculation context.

The [ordinary-calendar slice](sse-calendar-plan-2026-10-16.md) advances the
reader to v1.4. To include a separate plan, add an explicit verified
`--rule-capture PATH` to the diagnostic. Defaults use the reviewed annual
profile and separate rule/provider artifact roots; `--rule-profile`,
`--calendar-profile`, `--rule-artifact-root` and `--artifact-root` override them.
The source loader verifies the pinned reference bytes; no latest-capture
discovery, network fetch or calendar write occurs. Missing raw dates stay
missing. An ordinary schedule cannot prove emergency opening or settlement;
the diagnostic still exits 2 for unresolved gaps. Never use an October capture
as if it had been available during an earlier historical decision.

The [suspension repair](suspension-evidence-repair-2026-10-16.md) advances the
runtime inventory to v1.5. Lifecycle events and source evidence join the same
read snapshot; legacy suspension snapshots and inferred resumptions are
retained but explicitly flagged. A partial positive event does not establish
current ST/suspension/phase status, and no event is not a normal-status proof.
The dated `suspension-events YYYYMMDD` ingestion command returns partial/exit 2
even after successful capture. It does not supply trusted evaluator context.

1. Produce independently reviewed, PIT-visible runtime calendar, security,
   listing-phase, corporate-action, close, and account-lot inputs. Synthetic
   fixtures are not evidence that real data is ready.
2. Add intraday session/auction restrictions, price cages, fees, corporate
   actions, and other pilot requirements needed by a realistic fill model.
3. Bind exact Portfolio/Validation/Risk/policy, dataset-readiness, and rule
   calculation hashes at the future simulation boundary.
4. Complete `WP-LAUNCH-001` before making the deterministic paper-ledger
   package ready. Live execution stays disabled; PIT stays UNSUITABLE.
