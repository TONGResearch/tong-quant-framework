# SSE Ordinary Calendar Plan: 2026-10-16

## Scope and outcome

This bounded WP-LAUNCH-001 slice reconstructs an **ordinary planned schedule**
for the reviewed SSE 2026 scope. It is not actual exchange-opening history,
emergency-closure coverage, stock suspension status or settlement evidence.
It creates no canonical TradingSession rows, calculation authority, paper
ledger, broker connection or execution path. Framework/schema remain
`0.8.0`/`0.8.2`; PIT remains `UNSUITABLE`, execution/notifications disabled.

The real October 1-16 read reconstructs 16 planned days: 7 open, 9 closed,
0 unknown. The original calendar still has 9 missing dates in that window.
The reader reports unresolved gaps and exits 2; complete ordinary-plan
coverage is not a readiness pass. Annual capture returns partial/exit 2 too:
its 46 accepted assertions do not establish complete actual market history.

## Reviewed evidence

- [SSE annual holiday announcement, published 2025-12-22](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml).
  Profile: `config/markets/sse-calendar-notice-2026-year.toml`. Its manually
  reviewed mapping contains seven closed intervals, six extra closed dates
  and seven reopening dates: 39 closed + 7 open = 46 explicit assertions.
- [SSE 2026 trading rules](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml).
  The locally verified rules attachment, clause 2.4.1, supplies the ordinary
  weekday rule. The separately pinned deferral attachment was checked for
  applicability. The [official rules-release explanation](https://big5.sse.com.cn/site/cht/www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml)
  confirms July 6 effectiveness. This slice does not extend these rules
  backward to January or assume they apply in another year/exchange.
- Explicit existing rule capture:
  `data/processed/market-rule-references/sse-rule-capture-ce1330b8fa64a905487dcd0ba83391d98791c616cf09cc177565dd8f03b052c2.json`.
  The loader verifies all three pinned files; it never guesses a latest
  capture. Rule raw bytes live separately from provider raw artifacts.

The annual HTML capture is 28,079 bytes. Hashes:

| Item | SHA-256 |
| --- | --- |
| Annual source bytes | `c531e4ed2328b40ef4ce0abf961a044aeff802e60eb2e2f24ec2e9d8b2e48674` |
| Annual profile | `8db10d91ea601683d39692604ec247dd5a61b39a6ac4dc2f9b0f170498acad93` |
| Provider artifact identity | `6d7299f7e0ce9f9b99273ce64a9a37a5293ae69d8a884c1be193bbe201913d97` |
| Rule reference bundle | `9edd24123b9e35fa9f1d055e56ba5631936a13c390e256af4d8453f8bfbac3c0` |

The annual batch is `8f84459b-6ca9-4a14-b3dc-e07cadfa8e7f`. Actual capture
visibility is `2026-10-16T05:25:12.581775Z` (13:25:12 Malaysia), not the 2025
publication date. These observations cannot be injected into earlier research.
The annual review expires November 15 05:19:10 UTC; the rule review expires
earlier, November 14 16:01:12 UTC. These are review deadlines, not claims that
the legal rules themselves expire on those dates. Neither refreshes silently.

## Architecture and failure behavior

```text
SSE reviewed notice profile -> existing adapter -> neutral ingestion
                               -> SQLite evidence + captured source bytes

explicit verified rule capture + annual profile + same-snapshot notice records
  -> SSECalendarPlanBuilder -> separate SSECalendarPlan
  -> SSERuntimeInputSnapshot v1.4 (raw sessions and gaps retained)
```

`data.calendar_evidence` owns the transport-free profile; the provider module
retains its old import path as a compatibility alias. The application builder
uses existing data contracts without importing provider transports or trading
modules. CLI plan reconstruction is opt-in via `--rule-capture` and has no
fetch, initialize, migrate or calendar-write behavior.

All 46 annual claims are required, including dates outside the selected
window. Validation checks provider/dataset/market/exchange/subject, source URL,
raw hash, artifact identity, trust, precision, review/capture visibility and
exact date/boolean mapping. A bounded read verifies current annual artifact
bytes and rejects missing/modified content, invalid hashes and path escape.

Missing, invalid, expired or tampered annual sources make all requested days
unknown. Future-visible evidence is rejected. Unreviewed rule periods remain
unknown. Any conflicting visible notice makes its date unknown rather than
silently selecting a favorable opening or assuming a supersession. Plan
availability includes retained later notices and rule availability. All
source records and assumptions are hash-bound, with deterministic ordering.

Only a usable reviewed annual mapping plus effective weekday references can
derive ordinary days absent from the explicit announcement. A partial holiday
notice alone cannot justify this inference. Canonical raw sessions remain
separate, including any conflict with the plan. The plan does not choose the
previous session, establish settled holdings, or set action-free/normal flags.

Trust is capped at MEDIUM with RETRIEVAL_TIME precision, not inherited HIGH
trust from rules. The ordinary schedule always warns that exceptional closure,
settlement and security status coverage is unverified. Manual source mapping
can be wrong even when bytes match; hashes prove identity, not semantic truth.

## Reproduction and observed state

```sh
.venv/bin/python scripts/inspect_sse_runtime_inputs.py \
  --symbol 600000 --trade-date 2026-10-16 --calendar-start 2026-10-01 \
  --as-of 2026-10-16T05:25:46+00:00 \
  --rule-capture data/processed/market-rule-references/sse-rule-capture-ce1330b8fa64a905487dcd0ba83391d98791c616cf09cc177565dd8f03b052c2.json
```

This fixed-as-of read includes 60 notice records (46 annual + 14 retained
September claims), with no conflicts in this sample. Its plan hash is
`56013adfcc0c55ce2ec9b2203f638fcd36d697d1ece2827a09f52fee19c3f5a6`;
inventory hash is
`60f8d4f1336d287c4bde9ca7f865170c72f41f93a1962d86ac31f322cd59d059`.
Neither is a whole-database snapshot or independent source-quality approval.

Unresolved diagnostics cover actual calendar authority/provenance, raw
calendar gaps, security status, LOW price trust and artifact review,
listing phase, corporate-action coverage and account lots.

Database impact versus the preceding price slice: +46 evidence records,
+1 artifact, +1 artifact observation, +1 ingestion batch, +1 raw fingerprint,
+3 availability warnings. Provider limitations remain 13. Totals: 66 evidence
records, 3 artifacts, 13 batches; 18 bars, 8,797 raw calendar rows and 66 action
observations unchanged. No new tables or migration. The read-only audit passed
integrity, foreign keys, checksums and schema fingerprint checks at
`2026-10-16T05:28:28.510111Z` (audit hash
`76a3b1a502858e9bb74f3eac78e17222c1212c265b041eebf1b10f19987d8e44`).

Raw files and the local business database are ignored development data, not
included in Git synchronization. Future device recovery needs verified raw
artifact backup/restore, not just a source-code push. Source recapture gets a
new visibility timestamp; it must not impersonate this capture.

## Verification and next step

Seventeen new regression cases cover complete ordinary schedules, determinism,
missing annual assertions, altered identity/hash/trust/boolean/exchange,
future visibility, expiry, unsupported dates, artifact absence/tampering,
notice conflicts, runtime separation, partial-profile rejection and bounded
artifact reads. Existing layering checks also cover the transport-free builder
and profile. Full suite: **593 passed, 6 skipped**; Ruff, mypy (212
source/script files), governance (65 checks) and diff/whitespace checks pass.

This remains an uncommitted continuation slice, alongside the earlier trust,
notice and price changes. No commit or push was made in this continuation.
Next: establish dated security/listing-phase and exceptional-calendar/action
coverage evidence, then reviewed account/settlement and remaining cost/session
inputs within WP-LAUNCH-001. Do not mistake this progress for package completion
or start a broker, paper ledger or live submission path.
