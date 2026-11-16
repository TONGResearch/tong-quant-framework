# SEC XBRL Concept Evidence And Filing References

WP-LAUNCH-001 remains ready, not accepted.

## Scope And Contracts

The [official SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
provides per-issuer, standard-taxonomy concept observations grouped by unit. This
slice captures that extracted JSON, not the filing body or custom-taxonomy facts.
`SECConceptAdapter` implements the existing neutral evidence/artifact interface
under `sec_company_concept_snapshot`, version `sec-company-concept-snapshot-v1`.
Subject identity binds explicit CIK + taxonomy + tag; another concept cannot
silently become the latest version of the requested metric.

The existing bounded SEC JSON transport is reused: fixed endpoint allowlist,
environment-only access identity, no redirects/error-body/contact persistence,
bounded timeout/read/retries and declared sequential pacing. No new dependency,
provider schedule or automatic monitor/calibration enrollment is added. Existing
submissions normalization and v1/v2 receipts remain unchanged.

Native accn/form/filed, exact start/end, units, fiscal labels/frame and values
remain separate observations. Different accessions are retained; no favorable
latest selection, inferred replacement/revision number, averaging, YTD/TTM,
growth, currency conversion or canonical accounting alias is introduced. Duplicate
contexts within an accession are ambiguous, never selected. Empty or malformed
inputs do not become zero. This bounded first slice normalizes exact integer
amounts only; fractional/boolean/text values remain visible but unusable, not
rounded. Instant/duration labels are structural, not approved metric definitions.

`read_sec_concept_inputs` verifies retained envelope bytes, record identity,
registry and completed batch, then reads the issuer filing catalog under one
SQLite snapshot and actual UTC cutoff. Latest capture failure/tie/corruption or
future completion cannot fall back to an older positive record. Every native
row remains visible even when its filing reference is missing or conflicting.
Link checks require a unique usable accession plus identical form/filed label.
Historical comparative periods inside a newer report are explicitly different
from its current report-end label; they are not automatically annual growth.

The combined input hash includes original observations, source/catalog receipt
hashes, reference results and cutoff. A matching reference is not independent
numeric corroboration, accounting admission or proof of the filing body. Acceptance
and filed dates never become public publication or historical availability; see
the [SEC timestamp explanation](https://www.sec.gov/about/webmaster-frequently-asked-questions).
All source records remain LOW/RETRIEVAL_TIME with unverified continuity and all
financial-scoring/replay/validation/execution authority false.

## Real Evidence

Three explicit real captures for CIK 0000789019, `us-gaap`, October 27:

| Native concept | Rows | Metadata reference matches | Missing references |
| --- | ---: | ---: | ---: |
| RevenueFromContractWithCustomerExcludingAssessedTax | 134 | 81 | 53 |
| NetIncomeLoss | 345 | 86 | 259 |
| NetCashProvidedByUsedInOperatingActivities | 170 | 81 | 89 |

All 649 rows have native integer USD amounts. The 248 matches are reference
checks, not audited values or a coverage/consistency/PIT score. All 401 missing
references have filed dates before the current catalog's earliest date,
2020-09-02: revenue spans 2018-08-03 through 2020-07-30; the other concepts span
2009-10-23 through 2020-07-30. This is a documented recent-window gap; older-page
capture is still needed, not fabricated missing history or automatic rejection.

At fixed common cutoff `2026-10-27T12:07:34+00:00`, repeated reads reproduce:

| Concept | Combined input hash |
| --- | --- |
| Revenue | `9ce636d5a2ec8f46c297f91beb855fe9ea03ac4d7317977bc14285338ada2613` |
| Net income | `6e90ab77943b6802720ac5fce51f24ae828756e7cc72cdcf8f435416bafd479c` |
| Operating cash flow | `e093e8702eb98e9fbc95d73391b42bbdd597b69926578e468a6a0f8f5b1bffdc` |

The previous SEC catalog v1/v2 hashes still reproduce at their original cutoffs.
The SEC database now holds five evidence records/artifacts/batches, zero canonical
facts/reports/signals. Read-only checks preserve database hash
`6463003a2409a7729abcb6580c97f25194fc76b179f2033475c6903bc4c8ddaa`.
No contact identity bytes are found in the three new envelopes or database.
Ignored raw/database files require encrypted co-retention, not just Git.

## Operations And Remaining Gaps

Use `scripts/inspect_sec_concept.py` with explicit CIK/taxonomy/tag and either
`--capture` or `--as-of`, existing approved database and artifact-root paths.
Read-only mode makes no network request or database write; diagnostic exit 2 is
not validation acceptance. No access identity is permanently configured here.

Next: capture the explicitly referenced older catalogs without rewriting current
receipts, then verify filing-body/XBRL contexts and issuer/ticker association.
Fractional-source decimal transport, custom-taxonomy coverage, restatement
relationships, independent accounting/cross-provider checks and admitted sector
policies remain open. This US sample does not provide HK/MY financial coverage.
No schema, official research/score, Paper/Broker/Orders/Portfolio/Notification/live
change. PIT UNSUITABLE, production NOT_READY and disabled defaults persist.
Verification: 2435 passed / 6 skipped in 86.35 seconds, 47 added cases. Ruff,
mypy (276 files), governance (126 checks), scoped forbidden-import review and
whitespace diff checks pass. Tests cover scope, units/periods/vintages, bad or
ambiguous values, exact reference conflicts, future/missing/failed catalog states,
latest failure/corruption/tie/completion, idempotency, deterministic reads and
read-only CLI. Six default-disabled live provider/notification tests remain
skipped; real captures are separate from independent source/strategy validation.
