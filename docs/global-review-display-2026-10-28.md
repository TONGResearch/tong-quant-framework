# Technical And Reviewed-Filing Evidence Display

Date: October 28, 2026 (Malaysia). WP-LAUNCH-001, exploratory R2/R5 tooling only.
This is not an accepted business decision flow, new ResearchReport or scoring model.

## Implementation

Existing `scripts/inspect_global_technical.py` gains an explicit paired read-only
option: `--review-database` plus `--review-document-url`. Both must be supplied;
capture and US manual-document modes are rejected. Default output without these
options is unchanged. Existing US Yahoo technical/native-financial diagnostics,
SEC-specific tools and China A inputs remain separate; this is not acceptance
of the unified four-market release.

The current retained price reader, optional native Yahoo financial reader and
source-pinned HK/MY manual review reader share the same explicit UTC cutoff.
Same-file inputs reuse one SQLiteStore snapshot. Different databases hold
separate snapshots, explicitly labelled `separate_database_snapshots_shared_cutoff`;
this is not an atomic cross-database snapshot or synchronized live feed.
Exact nested receipts, technical parameters and the co-display payload are bound
by `combined_evidence_hash`; version `GLOBAL_REVIEW_DISPLAY_VERSION` is
`global-review-evidence-display-v1`. Hashes give reproducibility, not authentication.

The output preserves independent price, native-financial and manual-review
statuses. Missing/future/failed/rejected review records stay visible; a review
cannot fill absent Yahoo data. Failed/stale price input cannot borrow an older
quote currency. Each review row keeps its original label, Group/Bank scope,
current/comparative period, currency/unit, raw value and page/column annotation.

Quote versus reviewed reporting currency is shown as UNKNOWN,
SAME_LABEL_UNVERIFIED or DIFFERENT_CURRENCIES_NO_FX. Matching labels cannot authorize
FX, valuation or numeric comparison. Accounting field correspondence remains
NOT_REVIEWED and provider numeric consistency NOT_ASSESSED; total/attributable
profit and Group/Bank columns cannot be silently mapped by name or numerical
agreement. Data/sector admission, financial/investment scoring, valuation,
validation, official research-report creation and execution all remain false.
The existing four trend confirmations remain NOT_ASSESSED; no technique is
silently activated or declared validated by adding financial evidence.

No provider network request, credentials, schema migration, data writes, new
runtime dependency or trading-layer change is introduced. Only the existing CLI
and centralized display-version constant change; no parallel engine or domain
research model is created.

## Real Offline Reproduction

Primary database: ignored `data/processed/global-technical-20261027.sqlite3`.
Review database: ignored `data/processed/global-primary-documents-20261028.sqlite3`.
Shared raw root: ignored `data/processed/raw/provider-artifacts`.
Cutoff: `2026-10-28T05:14:00+00:00`.

| Context | Price observations | Manual monetary rows | Currency label result | Combined evidence hash |
| --- | --- | --- | --- | --- |
| 0700.HK | 692 | 4 | DIFFERENT_CURRENCIES_NO_FX | `edfa78c86bb859a73141a0af7679021a8bb65f5d78b83ebdbb918f63f69733c4` |
| 1155.KL | 690 | 4 | SAME_LABEL_UNVERIFIED | `916761897f43457a87e7e2ab705a2a827214c01048beac99c6d6215212d198fc` |

Both price/native-financial statuses remain observed_unqualified; manual records
remain MANUAL_TRANSCRIPTION_UNQUALIFIED. Sector-profile arguments are caller
context, not admitted bank/nonfinancial policies or verified business identity.
Repeated fixed-cutoff CLI output is byte-identical. No provider refresh was
performed, so these samples do not claim latest or realtime prices/financials.
Freshness labels remain visible; capture time is not first issuer publication.

Both database hashes stay unchanged after reads:

- Price/native: `0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
- Document/review: `899f4c282eac3d41acc8bc0863cfd712a6c89389a2972de1425bab1ed5ce3de6`.

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market hong_kong --symbol 0700.HK --as-of 2026-10-28T05:14:00+00:00 \
  --fundamentals --sector-profile nonfinancial \
  --review-database data/processed/global-primary-documents-20261028.sqlite3 \
  --review-document-url https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040901231.pdf
```

Exit 2 is an unqualified diagnostic, not an execution instruction. Real reproduction
is separate from synthetic tests and default-disabled provider network tests.

## Next Steps And Data Interfaces

Separately reviewed native-field/statement/accounting correspondence is still
required before comparison or official Financial admission. Then use real screened
candidates and actual strategy validation, never manufacture a queue or report.
Co-display does not close R1-R6, solve data quality or produce validated buy/sell
judgments. New ignored raw/database evidence still requires encrypted co-retention.

The [provider integration inventory](provider-integration-status-2026-10-28.zh-CN.md)
explains why data APIs are necessary even when research reads offline snapshots.
It distinguishes implemented adapters from retained real evidence, optional
credentials, account permissions and future-only integrations. No provider is
trusted by default; this slice does not require another token or paid subscription.

PIT UNSUITABLE; production NOT_READY; execution/notifications disabled. No commit,
push, Paper/Broker/Portfolio/Notification/live or allocation change. Quality results
are recorded in PROJECT_STATUS.md at handoff.

## Verification

Full suite: **2632 passed / 6 skipped**, 110.11 seconds; 13 added tests. Ruff,
mypy (289 source files), governance (132 checks) and `git diff --check` pass.
Synthetic integration cases exercise same/separate databases, unequal/equal
unverified currency labels, deterministic combined hashes, missing/future reviews,
latest price failure, failed current document, missing native financial inputs
and invalid paired/US/capture options. Existing global input/CLI tests also pass.
The six default-disabled network tests remain skipped; offline real receipt
reproduction is not a live permission probe or independent calibration result.
