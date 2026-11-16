# Nonfinancial ROE Input: October 22

Bounded input repair under `WP-LAUNCH-001`, which remains `ready` and incomplete.
No Paper, broker, execution, portfolio or notification implementation is added.

## Gap And Implementation

The real 002624 filing already disclosed weighted ROE, but the supported ratio
contract covered only bank period-end asset quality. This was an implementation
gap, not missing issuer disclosure. The existing reviewed-filing adapter now
accepts `roe_weighted_ytd_unannualized` / `nonfinancial_profitability` only with:

- Nonfinancial/group/current-period scope, separate percent review and null
  canonical currency; values remain signed percent, not fractions or CNY.
- Explicit January 1 start, calendar-quarter-end period and
  `ytd_unannualized_ratio` basis. No period-end-bank, standalone-quarter,
  generic ROE, ROIC, recomputed ending-equity or annualized substitution.
- Retained PDF/registered capture, exact review packet, evidence/fact identity
  and completed ingestion chronology through the existing neutral transaction.

Negative and zero percentages are valid observations, not missing values. No
arbitrary 0--100 quality-score bound applies to a reported profitability ratio.
Comparative ROE/growth and sector scoring remain unsupported, not inferred.
The reported basis is manually annotated, not an independently verified formula.

New packet version: `reviewed-nonfinancial-ytd-ratios-v5`; input receipt version:
`financial-source-inputs-v5-nonfinancial-ratios`. Five fixed pre-change packet
hashes verify that v1 monetary, both v2 comparative shapes, v3 bank ratios and
v4 cash flow remain byte-identical. New receipt identities distinguish current
reader semantics; stored reports are not rewritten or retrospectively qualified.

## Real Retained Example

Source: [Perfect World 2026 half-year report](https://static.cninfo.com.cn/finalpage/2026-08-20/1225482115.PDF).
One-based PDF page 7 (printed page 6) was rendered and visually inspected in this
round, with text extraction used as a secondary check. It reports current-period
weighted average ROE **-1.70%** under the half-year current column. The prior-period
value/change column is not ingested as a current observation or derived growth.
No code annualization or weighted-equity recomputation is performed. Audit/scope
labels inherit the retained unaudited group filing review; no second reviewer.

- PDF SHA256: `284af037c8a319c67a13ce6ecf0b17fceb29e0c96e902c06b4107b9e605c7691`.
- Source artifact: `39798ad9fe058ac4c36bab4edbe2672bb212986ea76360b5bb6f9ccb8e21dfbf`.
- Source capture remains October 20; review: `2026-10-22T11:13:15+00:00`.
- Plan: `config/filing-extractions/002624-2026h1-weighted-roe.toml`.
- First facts batch: `478810ae-b665-47d7-8d5b-0b97e2a0d267`.
- Review packet SHA256: `69318b0ffd0a9da688367baaea38b6eeac170b25feb8fa6f2552e14b40418c86`.
- Evidence: `0f5247aedb2ba8e6c840c0a6ee61c138ddded31f9e04ab54a5dae94578de7a15`.
- Review artifact: `efe4970599c4658eff2f01ba83b0dc9af513be92c5e89d3fad33ec40f3b4fbdb`.

One fact is stored with LOW/RETRIEVAL_TIME provenance. Repeating ingestion creates
a separate audit batch, not a duplicate fact; the first fact batch remains bound.
An October 20 read does not see this new observation. The older claimed August
publication is not used to backdate numeric availability or establish revisions.

## Combined Research-Input Check

```bash
.venv/bin/python scripts/inspect_candidate_inputs.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --symbol 002624 --sector-profile nonfinancial \
  --metrics revenue profit_attributable_to_parent operating_cash_flow total_assets \
    roe_weighted_ytd_unannualized roic \
  --as-of 2026-10-22T11:14:48+00:00
```

Exit 2 denotes partial diagnostics, not a failed provider request. Two identical
reads preserve database bytes and produce the same input-review hash:
`31df0085cdf69d63ef007906144d5d41baae200ee48099941397a10ace98724b`.
Financial-input hash:
`93f2820b7e1a874f469f23772783cd9aa07b3a5736fecf7a911be38a6c43b101`.

Nine financial observations reconstruct beside 674 prior daily observations,
ending October 19; these are not fresh October 22 prices. ROIC is still missing
from this explicit six-metric subset. Querying generic `roe` remains missing by
design, not aliased. Requested-metric coverage is not total financial completeness.
Technical structure remains BEARISH, momentum/aggregate CONFLICTED, bearish setup
ARMED. Those are diagnostics, not validated sell/buy instructions. Financial
scoring is NOT_ADMITTED, screening NOT_ASSESSED; no queue/report is invented.

The artifact registry verifies 11/11 files. Audit report hash:
`f1a99cb5b10b9e87d66e2f423bd4ec6e34f64ed390bbb6bb00dccf32a8a5dbc1`.
That verifies retained bytes, not independent content truth, trust, completeness
or recovery. New bytes remain ignored by Git and outside earlier encrypted
backups; the extraction plan alone cannot transport source evidence to a new host.

## Remaining Work And Boundaries

Debt/cash-flow drivers, named ROIC/valuation inputs and method for loss-making
issuers, source/sector admission, actual screening/research/validation and market
status/action continuity remain open. No data provider can guarantee absolute
accuracy; independent review/calibration remains necessary. Adding ROE cannot
override losses, technical conflicts or incomplete evidence.

No schema migration: one fact plus its neutral review/evidence/audit records use
existing tables. Framework/schema remain 0.8.0/0.8.2. PIT UNSUITABLE, production
NOT_READY; execution/notifications disabled. No commit/push or live authority.

## Verification

Full pytest: **1506 passed / 6 skipped**, 53.14 seconds, 45 added cases. Focused
filing/research tests pass 386 cases. Ruff passes; mypy reports no issues in 242
source/script files; governance passes 101 checks; `git diff --check` passes.
Skipped cases are not claimed as verified provider/live coverage. No remote CI
or independent investment validation was performed. New regression coverage
includes signed percentages, exact basis/period/scope, future visibility,
aliases/mixed-unit rejection, tamper preservation, previous packet hashes,
unscored research propagation and read-only deterministic combined diagnostics.
