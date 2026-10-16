# Operational Research Sample: 2026-10-16

Historical initial sample below. A later same-day
[corporate-action repair](corporate-action-mapping-2026-10-16.md) resolves the
26-row mapping defect for supported descriptions. Follow PROJECT_STATUS and
the current work package for next work, not this initial gap list.

Work package: `WP-LAUNCH-001`, partial implementation. Framework `0.8.0`,
schema `0.8.2`, migration `0010_portfolio_evidence_lineage` unchanged.
This records a real public-data ingestion exercise, not a strategy result,
provider trust upgrade, or Paper/live trading approval.

## Corrections before population

- AKShare daily bars and their placeholder instrument are now visible from
  the dataset's actual retrieval time, not an assumed historical close+minute.
  The observation timestamp still describes the historical market close.
  A one-minute post-close filter excludes unfinished same-day observations;
  it does not prove historical publication time or final-bar accuracy.
- Calendar dates likewise retain retrieval-time visibility. The open-date
  response cannot establish unreturned dates as confirmed closures.
- A matched disclosure event cannot backdate current financial values or
  raise their trust. Numeric facts retain LOW/RETRIEVAL_TIME; nominal linked
  publication date/revision labels are not authenticated numeric revisions.
- Tencent fallback turnover is unknown (`None`), not fabricated zero.
  The validator distinguishes missing optional turnover from invalid present
  values, including infinities. Price, volume, and OHLC constraints still apply.
- `akshare-market-data-v2` participates in daily-bar/calendar cache parameters
  and raw fingerprints. Old cache entries are not relabeled as corrected data.
- Price/action ingestion reuses an already visible instrument in the same
  transaction rather than superseding company metadata with a placeholder.
- XSHG (stored MIC) and SSE (legacy label) identify the same exchange in this
  pilot. Persisted strings are not rewritten, and other exchanges remain
  outside scope. Input and calculation contracts advance to `v1.1`.

These changes apply to new ingestion. No legacy database, old fact, or source
archive was rewritten. Old backdated AKShare data and fabricated-zero turnover
must not be accepted for historical validation simply because new code exists.
Audit/reconstruction from retained raw evidence is required; already lost
historical corrections cannot be recovered by code alone. PIT stays UNSUITABLE.

## Real observations

The configured business database did not exist before this exercise. A new
ignored `data/tong_quant.sqlite3` was populated through DataIngestionPipeline,
not from monitor history or synthetic fixtures. Public calls required no
Tushare token, paid endpoint, or broker connection.

| Input | Actual observation | Interpretation |
|---|---|---|
| 600000, unadjusted, 2026-10-01 through 2026-10-15 | 6 daily bars through Tencent fallback; 12 stored rows across two observed versions | First sample exposed fabricated turnover zero; a fresh version preserves missing turnover as null. Old rows remain auditable and are not eligible turnover evidence. Six dates are not market-wide coverage. |
| Calendar | 8,797 returned open-date records | Retrieval-time knowledge only; no proof of exchange-specific closure completeness or corrections. |
| Company information | Current name, industry and listing date through `akshare:stock_profile_cninfo` | Transport provenance is explicit. It is not direct CNInfo verification, a historical company snapshot, or proof of ordinary trading status. |
| Corporate actions | 26 raw rows, zero accepted normalized events | Implementation/semantic mapping gap, not proof of no actions and not an account-permission failure. Replay and adjustment remain blocked. |
| Security status/account lots | No records populated | No ordinary-listing, ST-free, settled-holdings or sellability conclusion. |

The real corporate-action field names match the
[official AKShare endpoint documentation](https://akshare.akfamily.xyz/data/stock/stock.html):
cash-distribution and share-distribution fields use composite column names.
The legacy normalizer recognizes different aliases. The documentation does
not specify reliable units for these ratio columns. Do not fix this by blindly
renaming columns, assuming per-share amounts, or treating registration dates
as ex-dates. Next work must authenticate field semantics/units, distinguish
proposals from implemented events, preserve zero versus missing values and
test real-schema fixtures before population. Raw payload fingerprints, cached
responses and zero-acceptance warnings are retained for that review.

After seven audited ingestion attempts (including a cache replay), the
read-only database audit passed: 12 bar versions, 8,797 calendar rows, five
instrument versions, seven batches, five raw fingerprints, nine availability
warnings, zero normalized actions/statuses/fundamentals, no FK violations,
valid migration checksums and matching physical schema fingerprint
`69ceb0931c99cf63ec353399877c4cffcd588c9b77cf8f719ec90f45c66fa517`.
These are local sample counts, not provider coverage or historical readiness.

## Repeatable entry points

Global options precede the subcommand. Each CLI invocation uses an isolated,
captured worker with a finite total timeout (default 60s, maximum 300s), even
when an AKShare endpoint has no native timeout. A timed-out worker is killed
and reaped by subprocess.run; exceptions/raw SDK output are not rendered.
Transactions protect each completed domain/audit write, but a killed request
can still leave an initialized database or earlier completed batches. Inspect
those before retrying. No rollback across separate CLI invocations is claimed.

```bash
.venv/bin/python scripts/ingest_data.py --timeout-seconds 40 daily-bars 600000 20261001 20261015
.venv/bin/python scripts/ingest_data.py --timeout-seconds 35 calendar
.venv/bin/python scripts/ingest_data.py --timeout-seconds 35 --refresh company 600000
.venv/bin/python scripts/ingest_data.py --timeout-seconds 35 corporate-actions 600000
.venv/bin/python scripts/manage_database.py audit --database data/tong_quant.sqlite3
```

`--database` selects an explicit research database. This ingestion command
initializes/migrates its selected target; do not use it on an archive or an
unreviewed existing database. Use the read-only audit and approved backup
procedure first. `--refresh` bypasses cache without deleting prior snapshots.
Invalid dates, identifiers, adjusted-price requests and timeout limits fail
before initialization. Exit 2 with `partial` means no normalized rows were
accepted; it must not be treated as successful evidence population.

The runtime inventory still reports seven unresolved requirements: missing
calendar dates, calendar provenance, security status, price provenance,
listing phase, corporate-action coverage and account-lot integration. It
continues to exit 2; merely populating rows cannot construct trusted context.

Reconstruction at the already elapsed cutoff `2026-10-16T01:30:30+08:00`
(`calendar_start=2026-10-01`, subject `600000`) produced input hash
`462bb4bc25131c827172841de4d1adcb1aeaad0cae308aff07deb7666baa2c24`.
All selected sample observations predate that cutoff. This identifies the
input inventory, not a claim of source correctness or readiness.

Verification: 451 tests passed, 6 optional network tests skipped; Ruff, mypy
(206 source/script files), governance and git diff checks passed. The real
public calls above were explicit operational exercises, not default CI tests.

The business database and raw caches are deliberately not pushed to GitHub.
SQLite WAL/shared-memory/rollback-journal files are also ignored; those can
contain database content even when the main database filename is excluded.
A new device needs explicit re-ingestion or verified backup/restore to an
approved encrypted destination; a Git clone is not a market-data backup.

## Next bounded work

1. Fix and test corporate-action field/unit/event semantics before re-ingestion.
2. Capture reviewed exchange-calendar and status/phase evidence; no inference
   from weekdays, security names or absence from a special-status list.
3. Bind raw hashes, trust and availability to actual price/calendar inputs via
   the existing provider-neutral evidence/artifact contracts.
4. Complete account-lot, intraday/cost, policy and simulation-boundary gates in
   WP-LAUNCH-001 before promoting WP-PAPER-001. No live behavior is added.
