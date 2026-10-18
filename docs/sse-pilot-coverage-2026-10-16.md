# Real SSE Pilot Input Coverage: 2026-10-16

## Result and scope

WP-LAUNCH-001 now has a repeatable, read-only coverage manifest using the real
operational database, not fixtures or provider-monitor history. The observed
scope is one explicitly selected security, `600000`; inspection is not an
investment recommendation or historical market-wide selection result.

- Cutoff: `2026-10-16T15:08:32+00:00` (23:08:32 Asia/Shanghai).
- Price window: Oct 1-15, excluding decision-day bars conservatively;
  calendar/status queries include Oct 16. Universe: `china_a_all`.
- Verified rule capture: `ce1330b8fa64a905487dcd0ba83391d98791c616cf09cc177565dd8f03b052c2`.
- Model: `sse-pilot-coverage-v1`.
- Manifest: `9c7cf0e731a52167d5f342da3a4d95b9ceef12ce2cd77caab974cf3589a75b8d`.
- Runtime input hash: `064dfc71dd3cc6576d6d3b9f20f89960e55f05dbbc9f8db46d3fad5f84167deb`.
- Research configuration hash: `2be381b8655337ac83bd45a53b72cd34d5e1310588de835530a192a76910d9a2`.

The command intentionally exits **2**, with `not_assessed_no_promotion` and
`strict_validation_authorized=false`. There are **21 unresolved requirement
codes**, not 21 development phases or a duration estimate. PIT stays
UNSUITABLE; execution/notifications stay disabled. No acceptance gate changes.

## Real observations

| Input | Observed at cutoff | Interpretation and gap |
| --- | --- | --- |
| Unadjusted daily bars | 6 latest visible dates, Oct 8-15; 18 total stored versions | Descriptive prices, not 18 independent days or validated returns. The current trend configuration requires 21 non-suspended bars, leaving a count deficit of 15 in this window. A wider capture can supply research history, not retroactive PIT knowledge. |
| Exact price bindings | 6/6 observed dates match stored economic-row/source/availability evidence | Structural identity only; evidence remains LOW/RETRIEVAL_TIME. Independent source, current raw-artifact authentication and continuity are not established. |
| Availability | Selected rows became available Oct 16 at `05:09:58.556223+00:00` | Oct 8-15 observation dates cannot replace actual later retrieval time in a historical decision. |
| Calendar | 7 raw open dates, Oct 8-16; 9 absent dates in Oct 1-16 | Missing dates stay unknown. The separately bound ordinary schedule does not prove exceptional opening or settlement history. |
| Status/lifecycle | No status or lifecycle events for this subject | No ST-free, suspension-free, ordinary-listing or relisting clearance. Thirteen suspension-start observations elsewhere do not clear this subject. |
| Corporate actions | Zero events in this narrow window | Not proof of an action-free interval. The database retains 66 observations across other action dates/versions; a scoped zero is not an empty global table. |
| Financial data | Zero visible facts/publication events | Revenue, profit, cash flow, debt, ROE and ROIC inputs are absent. Publication metadata does not authenticate numeric revisions; facts alone do not generate normalized Financial Research evidence. |
| Historical universe | Zero members in the declared universe | No survivorship-safe selection or historical membership claim. Never fabricate membership from the current company list. |
| Screening/research | No scoped rows/report | No demonstrated Discovery/Hard Screening pass or completed real research artifact. Generic screening rows would not themselves establish such approval. |
| Trend confirmations | No report-bound sentiment or industry-heat evidence | Neither may be inferred from price breakout/volume or replaced with favorable flags. |
| Market regime | No report-linked regime | Required metric names come from configuration; raw metric coverage is explicitly not inspected, not reported as zero provider coverage. A regime state cannot authorize trading. |
| Policy/account | Validation configuration pin absent; account reader not integrated | Separate reviewed requirements; no account connection or approval of a configured pin occurs. |

Authoritative session coverage is **unknown**, not 100%. Six bindings out of
six dates measure binding completeness only. Raw Bar/TradingSession models
lack trust/precision and show UNKNOWN; separately bound evidence retains LOW/
RETRIEVAL_TIME. No provider trust is inferred or upgraded by name.

## Implementation and repeatability

`SSEPilotCoverageReader` composes existing MarketDataService, runtime inventory,
replay read-side and research review inside one SQLite read snapshot. It never
creates, migrates or writes the source database and has no network transport.
Its manifest hashes query, contents, research-configuration subset, schema
fingerprint, runtime input hash and diagnostic version. It does not attest all
database bytes or the exact inputs consumed by an original research run.

The existing CLI adds `--pilot-coverage`, `--universe`, `--config` and repeatable
`--config-override`. Optional `--output` is coverage-only, new-file-only, mode
0600, credential-screened before publication, and refuses file/symlink
replacement. Missing databases stay absent. No inventory can grant validation
or simulation readiness merely because its counts look complete.

```bash
.venv/bin/python scripts/inspect_sse_runtime_inputs.py \
  --pilot-coverage --symbol 600000 --trade-date 2026-10-16 \
  --as-of 2026-10-16T15:08:32+00:00 --calendar-start 2026-10-01 \
  --rule-capture data/processed/market-rule-references/sse-rule-capture-ce1330b8fa64a905487dcd0ba83391d98791c616cf09cc177565dd8f03b052c2.json
```

Final JSON is retained at
`data/processed/sse-pilot-coverage/sse-pilot-9c7cf0e731a52167d5f342da3a4d95b9ceef12ce2cd77caab974cf3589a75b8d.json`.
It is ignored local data, not a Git backup. Other earlier draft exports remain
separate and are not this final manifest. Device recovery needs verified
database/artifact/report backups, not only a clone of the code.

## Verification

- Full suite: **752 passed, 6 skipped**, eight additional regression cases.
- Ruff/mypy pass; **217** source/script files type-checked.
- Governance: **72** pass; tracked/new-file whitespace checks pass.
- Tests cover determinism, config/content changes, adverse status, future
  exclusion, snapshot consistency with a concurrent writer, read-only access,
  missing databases, protected export and credential-like metadata rejection.
- Static checks enforce transport-free and no execution/paper/broker/portfolio/
  notification dependency. No frozen modules were changed.
- Source audit passed at `2026-10-16T15:13:35.130625+00:00`, unchanged content hash
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
- Framework `0.8.0`, schema `0.8.2`, 64 tables and migration head
  `0010_portfolio_evidence_lineage` remain unchanged. No migration, network
  capture, ingestion, commit or push occurs in this slice.

## Next bounded data work

1. Expand unadjusted history through existing neutral ingestion with source
   artifacts and actual retrieval visibility. Supply the configured lookback
   for explicitly exploratory research, not a backdated historical validation.
2. Populate current financial observations and disclosure evidence, preserving
   numeric-revision limitations and reconciling accounting units/periods before
   mapping research evidence. Do not fabricate earlier publication knowledge.
3. Capture reviewed status/phase, universe and action coverage, retaining
   unknowns. Missing secondary access is not agreement; the frozen Tushare
   account tier is not a prerequisite for software development.
4. Assemble one real research/validation chain only when its declared inputs
   are eligible. All four improved-Turtle confirmations remain mandatory;
   more indicators or a numerical lookback count cannot replace missing
   evidence. Paper and live retain their independent package gates.
