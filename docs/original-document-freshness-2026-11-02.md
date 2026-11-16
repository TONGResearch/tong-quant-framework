# Original Document Freshness Diagnostics

## Delivered Scope

WP-LAUNCH-001 adds one reusable, unscored time diagnostic for the existing
immutable HK/MY monetary and ratio review receipts. Financial research retains
it in the existing official ResearchReport path, including supplemental ratio
documents. The existing read-only CLI exposes it only with `--review-freshness`.
No separate report, provider, database table, migration or trading logic.

Version: `original-document-freshness-v1`. Financial evaluations advance to
`financial-v0.5.21-document-freshness`; framework/schema remain 0.8.0 / 0.8.2,
migration head 0010. Historical reports are not rewritten or requalified.

## Three Different Ages

| Observation | Calculation | What it cannot establish |
| --- | --- | --- |
| Annotated report age | Market-local decision date minus the original review's report-period end | Actual publication, latest interim disclosure or independent period verification |
| Original source capture age | Actual UTC cutoff minus the original PDF's source_available_at | Publication time, content accuracy or that a newly captured annual PDF contains new information |
| Manual review recording age | Actual UTC cutoff minus the review's actual recorded_at | That the source or financial period became newer |

HK uses Asia/Hong_Kong, MY Asia/Kuala_Lumpur for the date calculation; elapsed
times use UTC instants. Equivalent timezone labels produce identical hashes.
Comparative rows do not acquire the current report period as their own period;
this is an entire-document age annotation, not per-row freshness certification.
Rolling-average LCR and all original accounting notes remain unchanged.

`DocumentFreshnessPolicy` reuses research.financial.maximum_report_age_days and
adds research.financial.maximum_source_age_seconds. Both default to zero, meaning
UNASSESSED rather than unlimited freshness or an approved policy. Negative,
boolean, floating, text and null limits reject. The shared factory passes the
same values into Financial; CLI uses the same settings and records policy/hash.
Adding a default config key changes configuration identity. Old configuration-
pinned validation results cannot be silently reused for a new configuration.

When independently declared limits are positive, equality is within the specified
limit; an age strictly greater is STALE. The result remains UNASSESSED if a limit
is unset, unless an assessed age is already STALE. Only when both limits are
set and neither exceeded is it WITHIN_CONFIGURED_LIMITS. This is a diagnostic
result, not source/sector-policy admission, data trust or a trading signal.

Unusable current receipts yield BLOCKED_INPUT and null ages, never zero or an
older favorable receipt. Input integrity and source chronology are revalidated;
future/reversed timestamps reject. Latest issuer filing, exact publication,
source qualification, scoring/replay/validation/execution flags always stay false.
A manual re-review preserves the old source capture and report period.

## Integration

Exact retained reader -> immutable monetary/ratio receipt -> time diagnostic ->
existing Financial JSON/features -> existing single ResearchReport/SQLite
reconstruction. Primary and supplemental evidence remain distinct and canonically
ordered. Each result pins its input model/hash, source status, URL, decision
cutoff, timezone, declared limits and policy hash, with an assessment hash.
Missing and failed inputs survive persistence. Financial remains score None,
confidence zero; reports INCOMPLETE and InvestmentScore absent. Technical
calculations cannot upgrade these observations or bypass age/source limitations.

Native Yahoo, canonical China financial snapshots and prices retain their own
existing contracts/age checks. This slice does not certify their freshness or
complete four-market coverage. No account or network access is needed for the
retained-document calculation.

Use the previous [multi-file read-only example](readonly-ratio-source-selection-2026-10-31.md)
with `--review-freshness` to include the panel. Configure explicit limits through
`--config`, not hidden constants. Without the new flag the previous CLI structure
and hashes stay unchanged. The panel is included in combined_evidence_hash;
the original receipt freshness fields are not rewritten. CLI still creates no
official report or queue and exits 2 for unqualified output.

## Real Retained Check

Fixed cutoff: `2026-11-02T09:40:04+00:00` (17:40:04 Malaysia time). The source
sample is Maybank 2025; no live refresh or latest-filing search is claimed.

| Retained review | Annotated report age, days | Source capture age, seconds | Review recording age, seconds | Default state |
| --- | --- | --- | --- | --- |
| 31-row monetary Financial Statements | 306 | 466275.336974 | 259549.948947 | UNASSESSED |
| Six-row ratio Financial Statements | 306 | 466275.336974 | 259548.486818 | UNASSESSED |
| Three-row ratio Integrated Annual Report | 306 | 229067.33995 | 228754.003064 | UNASSESSED |

Default policy hash `e38a612473a11d3fce82f86687939e00685e3f11a9672b26ef694c523adfdc71`.
Their respective assessment hashes:

- `1119220267aa434db0c14e7226f45a873362f3728d1ca7818fb434ada3b220b8`
- `27b6ba5fb67fd03d743e9b750812f7030fa6e156d86fb3ed02093654a82a7fd7`
- `324003711309700618052950d183adec0b99f3931e696970f63d204028e3e75e`

A separate illustrative, NOT_ADMITTED policy of 400 report days / 86400 source
seconds labels all three STALE due to source age. Its hash is
`0612040aa290edcf0de38c1f90000c850d51ef8a59f2ce5bc3faa9f58eae07ac`.
This example is not installed in defaults, a suggested investment threshold,
proof of stale issuer information or permission to use a 400-day-old report.

Repeated same-cutoff calculations reproduce without writes/network. Document DB
remains `ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13`;
11 evidence/artifact/completed-batch rows, zero canonical facts/reports/signals.
Existing price/native DB is not written. No new raw artifact or schema change.
Encrypted database-plus-artifact co-retention remains outstanding.

The real CLI panel at the same cutoff repeats with combined hash
`a000376914fafa052a8e95724480577014759e61b1fc777627441a1797488c1b`.
Adding an illustrative `--max-observation-age-seconds 86400` triggers the
existing stale_observation price gate and withholds MACD; combined hash
`90d05f9c70c4e4d65d0198756ef897f95022adee5ee0a2e6c403c1eaad93870e`.
No new price gate or approved one-day policy is introduced. All original
fundamental receipts stay unqualified and no official report/readiness promotion
is created by this CLI. Both retained database hashes remain unchanged.

## Verification And Remaining Acceptance

36 new cases plus expanded official report integration cover age limits, zero /
exact boundary / stale behavior, separate clocks, timezone/date projection, missing,
failed/tampered sources, re-review without rejuvenation, settings/factory binding,
opt-in CLI and unchanged databases. Focused set: 206 pass. Full suite:
**3023 passed / 6 skipped**, 199.04 seconds. Ruff, mypy (298 files), governance
(145 checks), scoped import/output credential and diff checks pass. Six skipped
cases are opt-in real-network tests, not evidence of provider availability.
Existing dirty files are preserved; this is not a whole-checkout secret or
release-readiness certification. No Git commit or push was performed.

Next: explicit source/sector/freshness specifications for review, actual latest
disclosure evidence and real candidate screening/research/independent validation.
Age diagnostics do not supply absent publication history, provider corroboration,
sector accounting qualification, strategy edge or complete four-market coverage.
Financial scoring remains unadmitted; do not invent weights to turn tests green.

PIT UNSUITABLE, production NOT_READY, R1-R6 partial, launch ready/not accepted;
execution/notifications disabled, allow_live_orders false. No Paper, broker,
live-order, portfolio, notification or allocation change; no commit or push.
