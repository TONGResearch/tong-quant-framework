# Academic Research Workbench

Date: November 24, 2026. Scope: existing WP-LAUNCH-001 read-only presentation.
This adds an actual screenshot-ready interface over existing computations, not a
strategy, portfolio allocation, broker connection or second ResearchReport.

For current multi-subject scope, independent numerical references, public offline
reproduction and reviewer limitations, read academic-verification-guide.md. The
exporter accepts US/HK/MY identities with suitable retained inputs, but each page
is one fixed case; the original MSFT screenshot never established all-market
coverage. A separate historical NVDA example does not create a same-date ranking.
Adjustment basis remains unverified; not transforming values inside Tong is not
proof that the provider history is unadjusted.

## Academic Focus

A suitable narrow technical research direction is an evidence-aware, reproducible
equity-research workbench with explicit temporal boundaries. The demonstrated
engineering questions are source-content binding, prevention of future-data use,
multi-timeframe alignment, explicit missingness and separation of engineering
verification from economic validation. This is a proposed focus, not an approved
FYP title, proof of novelty, completed empirical study or profitable strategy.

## Four Views

1. Research workbench: historical candlesticks, volume, shared SMA/MACD/KDJ formulas,
   family-aware daily diagnostics and day/week/month/year selection. Frame gaps,
   stale/failed inputs, latest suspension and insufficient history are not filled.
2. Evidence lineage: selected source identity, capture availability, explicit
   research cutoff, raw/input/diagnostic hashes and period/source date alignment.
3. Verification and safety: actual project-governance checks and an optional local
   pytest JUnit record. No win-rate, return or drawdown result is invented.
4. System architecture: existing modules/contracts and the disabled execution
   boundary, with incomplete qualification and future Paper Trading work explicit.

The interface is English for academic discussion. Its controls change presentation
only. No input for holdings, account identifiers, costs, passwords or API keys
exists. JSON export contains the constructed observation bundle and bounded
project context, never raw provider envelopes, account data or local source paths.

## Reproduction

The original local MSFT case has 971 retained daily rows at the fixed cutoff
2026-11-15T09:13:45.007947+00:00. It is not a live quote. Its source remains LOW /
retrieval_time, provider-native/unverified price basis; complete sessions,
corporate actions, publication history and independent source qualification are
not established. The capture and research cutoff are not the market close.

Use the README export command. For a local engineering record, run a chosen test
scope separately, then pass its JUnit file to the exporter:

```bash
.venv/bin/pytest -p no:cacheprovider tests/test_academic_showcase.py \
  --junitxml=data/processed/academic-showcase/local-tests.xml
.venv/bin/python scripts/export_academic_showcase.py \
  --database data/processed/msft-review-20261115-zgzl_o5o/snapshot.sqlite3 \
  --artifact-root data/processed/msft-review-20261115-zgzl_o5o/raw \
  --market us --symbol MSFT \
  --as-of 2026-11-15T09:13:45.007947+00:00 \
  --max-observation-age-seconds 604800 \
  --junit-report data/processed/academic-showcase/local-tests.xml \
  --output data/processed/academic-showcase/index-with-tests.html
```

No tests run merely by opening the page or exporting a snapshot. Test records are
bounded, duplicate/conflicting cases, contradictory suite counters, unsupported
outcome structures and XML entity declarations are rejected;
record hashes support traceability, not independent verification or source trust.
The reader requests at most 2,000,001 bytes before enforcing the two-megabyte
limit, so an oversized record is not loaded in full merely to reject it.
A parser-level DTD callback additionally rejects declarations before entity
expansion regardless of the XML encoding; raw ASCII-byte preflight alone is not
sufficient for UTF-16. Valid encoded records retain their original-byte hash,
not a transcoded-content identity. No external DTD is resolved by this reader.
Daily bars and calendar periods reuse the original checked selectors/formulas.
Native missing values stay null, open periods never become ended observations,
and correlated indicators are not converted into independent votes.

The exporter requires an existing read-only store and explicit cutoff/age limit.
It does not initialize/migrate/capture or change original database/artifact bytes.
SQLite coordination metadata is not claimed to remain untouched. Output must be
outside the original artifact root and cannot replace an existing file or source
database. Template data is script-boundary escaped; safety flags remain false.

## Publication And Assets

Encoding follow-up: the old reader admitted a synthetic UTF-16 document containing
a DTD/internal entity despite its ASCII preflight. A DTD-rejecting TreeBuilder
callback closes that boundary without changing valid record summaries or hashes.
Fifteen rejection cases span plain/internal/external DTDs and UTF-8/BOM/UTF-16
variants; five valid encoded cases preserve original-byte identity. All 61 focused
tests pass in 8.07 seconds, plus Ruff, mypy (326 files), 189 governance checks and
whitespace checks. Independent static follow-up closes the parser/read-bound
repairs; no tests, data, network or Git operations were performed by that reviewer.
No new full-suite, isolated publication check or regenerated screenshot is claimed.

Subsequent bounded-read hardening adds two instrumented regressions (41 focused
cases pass), with Ruff, mypy (326 files), 189 governance checks and whitespace
checks passing. Existing valid records retain their counts/hashes. The full-suite
run and screenshots described next precede that narrow repair; no new full-suite,
independent-review or publication result is claimed for the follow-up.

Local verification on November 24: 39 focused tests; full suite 5293 passed,
6 skipped in 553.00 seconds; Ruff; mypy (326 source files); 189 governance checks;
and whitespace checks. Independent static review and scoped follow-up closed
the artifact-root normalization and JUnit-counter findings. That reviewer did
not run tests or inspect actual market-data/source bytes.

The full local JUnit file is 7,105,648 bytes, exceeding the exporter's two-megabyte
input bound. The final screenshot therefore uses a 631,033-byte anonymous JUnit
derivative: all 5,299 case identities are hashed and every pass/failure/error/skip
outcome is preserved, after checking the original suite counters. Its properties
retain the original record fingerprint; no test is dropped or reclassified.
Original SHA-256: d7efe504a2a9f0949fcf502101a5bc1e3c89a6474e347ca4b12aeda52cba9913.
Displayed derivative SHA-256: 9e26b25d739563116ecaacb556da9e32fdb31be6f83386f9fa6aff5c0a18ceec.
Both are local engineering records, not independent validation.

Headless Chrome checks cover all four views, day/month/year controls, chart-window
and SMA controls, provenance dialog, JSON download and 320/390/520/768/1600-pixel
widths. No script errors or page-level horizontal overflow were observed. The
real retained-data export left the three inspected DB/WAL/artifact byte pins
unchanged. These are local checks, not an isolated publishable candidate, installed
wheel verification, whole-work-package acceptance or independent strategy study.

The HTML, CSS, chart display logic and a small vendored Lucide 1.8.0 icon subset
are self-contained. Full ISC attribution is retained in academic_showcase_icons.json.
No Node/frontend dependency is added to the framework; package data includes the
two presentation resources. Browser automation is an external verification tool,
not an application/runtime requirement.

Generated exports, JUnit records and screenshots do not belong in Git. The original
DB and raw evidence remain local and ignored. Review market-data redistribution
rights before sharing embedded data; screenshots do not establish data licensing,
independent data quality, investment suitability or trading authority. No email is
sent and no supervisor approval is inferred from producing this demonstration.
