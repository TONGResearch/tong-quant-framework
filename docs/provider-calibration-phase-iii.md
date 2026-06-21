# Provider Calibration Phase III

## Objective

Phase III measures whether the current data foundation is reliable enough for
point-in-time research and historical validation. It does not authorize Paper
Trading, broker integration, order generation, execution, or live trading.

The canonical generated artifacts are:

- `docs/generated/phase3/framework-data-readiness.md`
- `docs/generated/phase3/framework-data-readiness.json`
- `docs/generated/phase3/tushare-provider-capabilities.md`
- `docs/generated/phase3/tushare-provider-capabilities.json`
- `docs/generated/phase3/pit-readiness-gap-report.md`
- `docs/generated/phase3/pit-readiness-gap-report.json`
- `docs/generated/phase3/akshare-data-quality.md`
- `docs/generated/phase3/akshare-data-quality.json`

They are produced by `scripts/run_data_readiness.py`. Credentials are read from
environment variables only and are never rendered into either artifact.

## Readiness Inputs

Every dataset assessment considers five independent inputs:

1. Observed coverage
2. Source trust level
3. Availability precision
4. Cross-provider consistency
5. Historical continuity

The result is one of `USABLE`, `CAUTION`, or `UNSUITABLE`. Record count alone
cannot establish historical readiness. A large retrieval-time snapshot may
still be unsuitable for reconstructing an earlier decision date.

When the secondary provider is inaccessible, coverage and consistency are
reported as `N/A`. Permission failure, missing credentials, and unsupported
endpoints are provider-access limitations, not empty datasets.

## Tushare Capability Detection

The runner validates `TUSHARE_TOKEN` locally without retaining its value, then
probes each required endpoint once. Probe results distinguish:

- Available
- Permission denied
- Authentication failed
- Rate limited
- Provider error
- Not tested

A successful empty response proves only that the endpoint call is permitted.
It does not prove historical coverage. Endpoint access is mapped to every
calibration dataset before the dual-provider comparison starts.

The current endpoint set is `stock_basic`, `namechange`, `suspend_d`,
`disclosure_date`, `income`, `dividend`, and `index_weight`. Tushare documents
account-level permission requirements for several of these endpoints, including
500 points for `disclosure_date` and 2,000 points for `stock_basic`, `income`,
`dividend`, and `index_weight`. Runtime capability detection remains authoritative
because provider rules and account permissions can change.

## Real Calibration Run

The repository report generated on 2026-06-20 used real AKShare responses and
the following explicit sample scope:

- Lifecycle and suspension observation date: `2026-06-19`
- Financial publication period: `2025-12-31`
- Fundamental revision sample: `600000`, from `2024-01-01`
- Corporate-action sample: `600000`
- Index query window: `2026-06-01` through `2026-06-20`

`TUSHARE_TOKEN` was not configured for this run. Therefore no claim of real
AKShare/Tushare agreement is made, and every cross-provider metric remains
unmeasurable. The overall framework classification is `UNSUITABLE` until the
required provider evidence and historical continuity improve.

The best-case ceiling analysis assumes perfect dual-provider coverage and
consistency while preserving all other evidence. Under that deliberately
optimistic assumption:

- Financial publication dates may reach `USABLE`.
- Fundamental revision evidence may reach `USABLE`.
- Security lifecycle, ST, suspension, delisting, corporate actions, market-wide
  universe, and CSI membership remain capped at `CAUTION`.

The ceiling is not a measured calibration result. It demonstrates that adding a
second provider cannot repair retrieval-time availability, low source trust, or
missing historical continuity by itself.

## AKShare Independent Audit

Tushare availability does not block AKShare quality measurement. The independent
audit records normalized record counts, expected-size coverage where known,
required-field completeness, date validity, key uniqueness, evidence scope, and
a deterministic snapshot hash.

Evidence scope is explicit:

- `DATE_SCOPED`: the provider accepts an explicit date or reporting period.
- `PARTIAL_HISTORY`: historical evidence exists but known intervals or markets
  are incomplete.
- `CURRENT_SNAPSHOT`: only the retrieval-time state is defensible.
- `TERMINAL_RECORDS`: terminal events exist without a complete warning timeline.

The 2026-06-21 run successfully normalized eight dataset groups. CSI300, CSI500,
and CSI1000 constituent downloads failed at the upstream CSI workbook endpoint.
Tong Quant now uses a timeout-guarded downloader for this AKShare-compatible
endpoint, retries within a fixed bound, records the safe exception type, and
continues the report with an explicit error instead of hanging indefinitely.

Observed 100% field completeness, date validity, or key uniqueness describes
the returned sample only. It never upgrades source trust or PIT readiness.

## Dataset Usage Policy

| Dataset group | Current use | Prohibited interpretation |
|---|---|---|
| Security lifecycle | Data-quality diagnostics and forward collection | Complete national historical status timeline |
| ST and suspension | Preserve observed events and warnings | Absence of a record means normal tradability |
| Financial publication | Conservative date-based availability checks | Exact intraday availability when only a date exists |
| Fundamental revisions | Revision evidence for sampled disclosures | Complete prior numeric-value reconstruction |
| Corporate actions | Sampled event evidence and provider calibration | PIT-safe adjusted prices without dated factor history |
| Market-wide universe | Forward snapshot collection | Historical tradable universe before collection began |
| CSI membership | Forward snapshot collection and provider comparison | Complete historical entry and exit ledger |

## Reproduction

```bash
.venv/bin/python scripts/run_data_readiness.py \
  --database /private/tmp/tongquant-phase3-real.sqlite3 \
  --output-dir docs/generated/phase3 \
  --trade-date 20260619 \
  --period-end 20251231
```

Tushare calibration activates only when `TUSHARE_TOKEN` is available locally.
Paid endpoints are not required by the runner, but endpoint access still
depends on the account's actual permissions. Unavailable endpoints remain
visible as limitations rather than being downgraded to empty results.
