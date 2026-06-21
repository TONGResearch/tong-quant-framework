# Historical Coverage Matrix

Scores below are source-policy baselines, not claims that a local database has
already ingested every period. Runtime assessments must be calculated from the
records actually present.

## Phase III Real Observation

The 2026-06-20 calibration run retrieved real AKShare data. Tushare was not
available because `TUSHARE_TOKEN` was not configured, so cross-provider
coverage and consistency remain `N/A` rather than zero.

| Dataset | AKShare records | Query scope | Runtime class |
|---|---:|---|---|
| Security lifecycle | 1,693 | Observation date 2026-06-19 | UNSUITABLE |
| ST status | 1,464 | Current and partial dated evidence | UNSUITABLE |
| Suspension status | 25 | Trade date 2026-06-19 | UNSUITABLE |
| Delisting records | 204 | Provider-available terminal records | UNSUITABLE |
| Financial publication dates | 5,189 | Period end 2025-12-31 | UNSUITABLE |
| Fundamental revisions | 23 | Symbol 600000 from 2024-01-01 | UNSUITABLE |
| Corporate actions | 25 | Symbol 600000 | UNSUITABLE |
| Market-wide universe | 5,528 | Retrieval-time snapshot | UNSUITABLE |
| CSI300 membership | 0 | June 2026 query window; upstream endpoint error | UNSUITABLE |
| CSI500 membership | 0 | June 2026 query window; upstream endpoint error | UNSUITABLE |
| CSI1000 membership | 0 | June 2026 query window; upstream endpoint error | UNSUITABLE |

These counts prove successful retrieval only. They do not prove continuity,
complete history, or point-in-time safety. See `provider-calibration-phase-iii.md`
and the generated dashboard for the full limitations and usage guidance.

The index counts above reflect the latest 2026-06-21 run. Older successful
responses are not silently substituted when the current endpoint fails.

| Area | Current evidence | Baseline trust | Expected class | Main limitation |
|---|---|---:|---|---|
| Suspension/resumption events | Daily Eastmoney event records | MEDIUM | CAUTION | Historical availability is retrieval-time unless separately proven. |
| Shenzhen ST entry/exit | Dated SZSE short-name changes | MEDIUM | CAUTION | No equivalent complete Shanghai/Beijing timeline. |
| National ST history | Current snapshots plus partial dated evidence | LOW | UNSUITABLE | Cannot reconstruct all historical intervals. |
| Delisting history | SSE/SZSE terminal listing records | MEDIUM | CAUTION | Warning period and announcement availability may be incomplete. |
| Relisting history | Event type reserved; no complete provider | UNKNOWN | UNSUITABLE | Must not infer relisting from ordinary trading resumption. |
| CSI300 membership | Dated current snapshots | LOW-MEDIUM | CAUTION forward / UNSUITABLE backward | Complete entry/exit history unavailable. |
| CSI500 membership | Dated current snapshots | LOW-MEDIUM | CAUTION forward / UNSUITABLE backward | Complete entry/exit history unavailable. |
| CSI1000 membership | Dated current snapshots | LOW-MEDIUM | CAUTION forward / UNSUITABLE backward | Complete entry/exit history unavailable. |
| Market-wide A-share universe | Retrieval-time snapshots | LOW | CAUTION forward / UNSUITABLE backward | Snapshot collection start defines earliest defensible history. |
| Actual financial disclosure date | Eastmoney reporting schedule | MEDIUM | CAUTION | Date-only; visible conservatively at end of day. |
| Financial announcement timestamp | CNInfo disclosure evidence | HIGH | USABLE when coverage passes | Title parsing and source completeness require monitoring. |
| Historical financial revisions | Ordered CNInfo announcements | MEDIUM-HIGH | CAUTION | Prior revised numeric values may still be unavailable. |
| Financial facts without publication evidence | THS statement payload | LOW | UNSUITABLE historically | Retrieval time remains the only safe availability. |
| Provider consistency | AKShare/Tushare comparison framework | UNKNOWN until measured | UNSUITABLE until measured | Adapter availability is not evidence of same-period agreement. |

## Score Interpretation

The coverage evaluator reports a 0-100 confidence score. A source label alone
does not determine classification. Sparse records, missing periods, low temporal
precision, contradictions, or one-provider dependence reduce the runtime score.
