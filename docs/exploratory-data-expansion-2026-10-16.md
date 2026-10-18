# Exploratory Research Data Expansion: 2026-10-16

## Delivery and boundary

WP-LAUNCH-001 continues with real public inputs, not another strategy engine.
New captures use a separate research database,
`data/processed/exploratory-pilot-20261016.sqlite3`, preserving the existing
operational baseline. This is an explicit-symbol `600000` engineering sample,
not a recommendation or survivorship-safe market-wide selection.

| Capture | Actual result | Meaning |
| --- | --- | --- |
| Unadjusted prices, Jan 1-Oct 15 | 187 rows/dates, Jan 5-Oct 15; 187 exact price-evidence bindings | The current trend module's 21-bar numerical minimum is satisfied. Source continuity, volume units, actions and historical publication/corrections remain unverified; this is not strategy validation or complete weekly/monthly/52-week history. |
| Income statement | 2,550 native rows | Captured from AKShare's THS income endpoint; not 2,550 qualified FundamentalFacts. |
| Balance sheet | 5,950 native rows | Native metrics/units retained without canonical assumptions. |
| Cash-flow statement | 4,500 native rows | Native missing, zero and negative values stay distinct. |
| Statement periods | Provider labels range from Mar 2014 to Jun 2026 | Old report periods are not proof these particular numeric revisions were historically visible. |
| CNInfo direct metadata | 30 records, zero downloaded filing artifacts | One page only; explicit pagination-truncated and metadata-only limitations. No complete disclosure history, independent comparison or numeric-revision authentication. |

Total native statement observations: **13,000**. Canonical fundamental facts,
ResearchReports and ValidationReports remain **zero** in the new sample.
Units, currency, field definitions, consolidation/period basis and sector
applicability need review before mapping provider-native rows into research.

Prices became visible at `2026-10-16T15:19:50.276318+00:00`. Income/balance/cash
captures retain `15:20:16.460365`, `15:25:02.063878` and `15:25:44.493012` UTC
respectively. No value is backdated to its report period or a matched announcement.
Price and financial evidence remain LOW/RETRIEVAL_TIME. Direct disclosure
metadata retains the existing provider's MEDIUM/EXACT declarations; its
source timestamp granularity is not independently proved, and midnight/day-
boundary values must not be treated as verified intraday publication times.

No Tushare upgrade, broker connection or account credential was needed.

## Implementation

- `AkShareFinancialSnapshotAdapter` implements the existing provider evidence
  contract and writes through ProviderNeutralIngestionService. It introduces
  no parallel domain storage or database tables.
- `financial_statement_snapshot` records retain each native row, statement,
  row number, raw artifact binding, capture/model version and explicit null
  canonical metric/accounting unit. They do NOT populate FundamentalFact,
  investment scores, research reports or strategy decisions.
- The full original serialized DataFrame and parameters are SHA-256 verified,
  bounded to 16 MiB and credential-screened. Artifact bytes must reproduce
  delivered native rows. Metadata, frame and audit writes share the existing
  transaction; cache replay is idempotent at evidence/artifact identity.
- New `financial-snapshot SYMBOL income|balance|cash_flow` uses the existing
  isolated, timeout-bounded ingestion CLI. Exit 2/partial remains mandatory,
  even after every native row is captured: canonical semantic review is pending.
- Financial endpoint selection is now lazy: an available income endpoint does
  not fail merely because another unused statement endpoint is missing.
- Pilot inventory v1.1 separately reports native snapshots and direct CNInfo
  metadata. Neither satisfies missing canonical financial/publication inputs
  nor enables validation. Transport-free boundaries are retained.

The pre-existing generic `ingest_financial_statement` normalization is not
used for these captures. Its assumptions need audit before native data can
use that path, including zero-value fallbacks, units, native metric identity
and revision linkage. The new native snapshot path deliberately avoids guessing.

## Repeatable commands

Use an explicit new/reviewed database. These populate and may migrate their
selected target; do not point them at an unreviewed archive or live source.

```bash
.venv/bin/python scripts/ingest_data.py \
  --database data/processed/exploratory-pilot-20261016.sqlite3 \
  --timeout-seconds 45 daily-bars 600000 20260101 20261015
.venv/bin/python scripts/ingest_data.py \
  --database data/processed/exploratory-pilot-20261016.sqlite3 \
  --timeout-seconds 35 financial-snapshot 600000 income
```

Balance and cash-flow captures use the same entry point. CNInfo capture used
the existing capture script in a bounded 45-second parent, with
`--metadata-only --max-pages 1 --max-artifacts 0`, Jan 1-Oct 15 scope, and the
same isolated database. Failed/limited access cannot become provider agreement.

An updated read-only inventory at `2026-10-16T15:27:09+00:00` is stored locally:
`data/processed/sse-pilot-coverage/sse-pilot-26cd2064981257c5016eb7c6d79e715da92bc48ac96e0653226808a3d4c85ff3.json`.
It shows zero numerical trend warm-up deficit, but remains inventory-only,
with validation unauthorized. Its gap-code count is not comparable to the
earlier operational manifest: the database, history window and available
calendar/reference inputs differ. Never subtract those counts as progress.

## Verification and portability

- Full suite: **762 passed, 6 skipped**, ten additional regression cases.
- Ruff and mypy pass; **218** source/script files type-checked.
- Governance: **73** checks pass; tracked/new-file whitespace checks pass.
- New tests cover native zero/blank/null/negative preservation, no facts/report
  creation, original availability, cache idempotence, artifact hashes,
  mismatched identity/schema/content, transaction rollback, credential filtering
  and CLI partial semantics. A minimal client proves unused endpoints are not
  eagerly required.
- All four new price/financial artifact files passed SHA-256 verification.
- Both databases passed read-only integrity/migration/fingerprint audits at
  `2026-10-16T15:27:10+00:00`. Original audit hash is unchanged:
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
  Exploratory sample hash:
  `9cf45f444cee2780ea519cdbbd92aa78d9d41ed8937e75fce389fb79be74aec0`.
- Framework/schema remain `0.8.0`/`0.8.2`, 64 tables, migration head unchanged.
  No execution, paper, broker, portfolio or notification module changes.
- No commit/push. Databases, raw artifacts and generated JSON remain ignored
  local data, requiring separate verified backup for a new device.

## Distance to the Final Goal

These are five acceptance groups, not five prompts or a duration estimate.

| Group | Current status | Remaining evidence/delivery |
| --- | --- | --- |
| 1. Trustworthy pilot inputs | In progress; price count and native capture improved | Canonical units/metrics, disclosure coverage/precision, status/phase/universe/actions, reviewed policy and account input provenance. |
| 2. One real validated strategy chain | Not yet demonstrated | Reviewed specification, all four modified-Turtle confirmations, actual research/scoring/validation/portfolio-risk artifacts and predefined OOS/robustness/cost checks. |
| 3. Deterministic Paper Trading | Planned, package acceptance pending | Persistent cash/position/event ledger, costs/fills, A-share sellability/session constraints, reconciliation and crash/retry recovery. |
| 4. Read-only/sandbox and deployment | Planned, package acceptance pending | Verified account/environment/API scope, reconnect, independent reconciliation, monitoring, backup/restore and operator controls. |
| 5. Separately approved live rollout | Frozen | Independent strategy/data/risk/operations acceptance and explicit approval with capital limits, manual control, kill switch and rollback. |

Software development and forward evidence collection can run in parallel.
No calendar waiting period alone enables trading. The shortest responsible
path remains one market/scope/strategy first, not every market or indicator.
Next bounded work: define and test a small explicit financial metric/unit map
with industry applicability and evidence references, expand disclosure source
coverage, and close status/universe/action gaps before treating new captures
as qualified inputs. PIT remains UNSUITABLE; execution/notifications stay disabled.
