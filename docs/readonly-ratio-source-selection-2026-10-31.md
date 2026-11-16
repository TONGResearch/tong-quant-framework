# Read-Only Ratio Source Selection

## Delivered Slice

WP-LAUNCH-001 exposes explicitly selected original ratio documents beside retained
price/technical, native-financial and reviewed monetary inputs in the existing
`scripts/inspect_global_technical.py` entry. This is an exploratory read-only
co-display, not the creation of an official ResearchReport, source admission,
validated buy/sell judgment or production release.

New repeatable option `--review-ratio-document-url` selects a primary ratio URL
first and up to three supplemental URLs. All URLs must be distinct and within
existing HKEX/Maybank scope; the current reviewed-filing database/URL pair plus
`--fundamentals --sector-profile ...` is required. Explicit sector remains caller
context, not a classification or scoring-policy approval. Capture/US review and
arbitrary URLs stay disallowed. Bad pairing, count, duplicate or URL scope fails
before database access. Price/native capture remains a separate explicit action.

The first ratio URL's role stays fixed. Supplemental URLs sort canonically, so
permuting supplements preserves byte-identical output and combined evidence hash.
`reviewed_ratio_evidence` retains the primary and every supplemental receipt,
including original rows, per-document hashes, dates, source identities, warnings,
unknown definitions and missing/failed states. Different document row keys may
coincide without being merged. Numeric presence cannot fill another source's
gap, and a rolling-average LCR cannot be treated as an instant year-end ratio.

The additive panel is versioned `global-review-ratio-display-v1` through central
GLOBAL_RATIO_DISPLAY_VERSION. Existing combined display V1, source/Financial
versions, framework 0.8.0, schema 0.8.2 and migration head 0010 are unchanged.
Without the new option, prior output structure/version/hash remain unchanged.
No new dependency, domain model, provider, table or migration.

## Snapshot And Safety Boundary

All monetary and ratio reads for the selected review database now share one
SQLite read snapshot. This prevents a writer committing between document reads
from mixing two database states in one panel. Nested exact readers reuse that
connection and continue artifact, parent, batch, identity and availability checks.
If prices and review data use the same file, the existing outer snapshot is also
reused; otherwise the output explicitly says separate database snapshots sharing
one cutoff, not an atomic cross-database snapshot. Artifact bytes remain external
and must still pass retained hash checks; SQLite isolation is not authentication.

The existing immutable ratio reader validates LOW/retrieval-time evidence and
false authorities before display. No numeric aliases, aggregation, consistency
vote, bank-plan credit, policy admission or scoring is added. The combined hash
includes the complete new panel and original limitations. Credential validation
still runs before output; credential-like URL parameters reject without echoing
the supplied value. Exit 2 means exploratory/unqualified, not validation success.

## Retained Example

This reads already stored snapshots only, with a fixed historical capture cutoff:

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/global-technical-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --market malaysia --symbol 1155.KL \
  --as-of 2026-10-30T18:07:38+00:00 \
  --fundamentals --sector-profile bank \
  --review-database data/processed/global-primary-documents-20261028.sqlite3 \
  --review-document-url https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-financial-statements.pdf \
  --review-ratio-document-url https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-financial-statements.pdf \
  --review-ratio-document-url https://www.maybank.com/iwov-resources/documents/pdf/annual-report/2025/maybank-ar2025-integrated-annual-report.pdf
```

Without an explicit maximum observation age, freshness stays UNASSESSED, not
current. Supply a reviewed positive `--max-observation-age-seconds` when testing
an age requirement; stale prices must block their own calculations rather than
borrow financial freshness. The example does not demonstrate latest-market data,
complete issuer coverage, original-year PIT availability or trading readiness.

Real retained Maybank output includes the separate six-row Financial Statements
and three-row Integrated Annual Report ratio receipts. Repeated fixed-cutoff
output is identical. No network/ingestion/write, official queue/report or signal
is created. Existing document DB hash stays
`ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13`, price/native DB
`0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.
No canonical fundamental or provider-trust promotion is performed.

At this cutoff the original prices/native financial observations are present
but unqualified, and price freshness is UNASSESSED. The primary/supplemental
ratio input hashes remain respectively
`9b9be7e6e0caaca85088ca9e00d0015a51d558e17668e79ce0f03cfc531d6fa9` and
`a1d4f13b0b5ce5d2a2f3f7f894f541c21778dd268d920de9c1480de49e332f75`.
Combined output hash:
`cd74859b30add9a936bf97953e388989b4d32687aefc215c1302b58efd50e9f1`.
Technical calculations are displayed, not interpreted as admitted conditions;
research_report_created and readiness_promoted remain false.

## Checks And Remaining Work

15 added cases cover HK/MY, shared/separate files, maximum document count,
deterministic supplemental order, unchanged legacy output, per-source failure,
future recording, invalid count/duplicate/URL/pairing and credential-safe errors.
Two competing-writer cases prove the current snapshot retains the old secondary
receipt while a fresh read sees its newly committed source failure. These writes
occur only in synthetic temporary test databases, not user evidence.

Focused module: 38 cases pass. Full suite **2987 passed / 6 skipped** in 143.62
seconds. Ruff, mypy (297 files), governance (144 checks), scoped import/credential,
unchanged retained DB hashes and diff checks pass. The six skipped tests are
opt-in real-network cases; no new provider availability is claimed. Checks do
not certify every pre-existing dirty file as secret-free or release-ready.

Next is admitted financial-sector/source/freshness methodology and real screened
technical/fundamental research plus independent validation, not more provider-name
trust or relaxed data gates. Read-only display is not completed four-market
deployment; R1-R6 remain partial. Existing five bank-policy/three external gaps,
current filings, cross-provider corroboration, known source discrepancies and
encrypted database/artifact co-retention remain open.

PIT UNSUITABLE, production NOT_READY, launch ready/not accepted; execution and
notification disabled, allow_live_orders false. No Paper, broker, live-order,
portfolio, allocation or notification change; no commit or push.
