# SEC Primary Filing Body And Numeric Subset Review

## November 16 Optional Exclusion Structure Audit

review_inline_body and read_sec_body_inputs accept explain_exclusions=False.
Explicit True adds sec-inline-exclusion-structure-v1 diagnostics, never supported
facts or accepted values. Numeric/source normalization versions and default
outputs remain exact. The body read adds exclusion_review_version only when
requested; its ordinary completed-batch/parent/raw/cutoff checks remain required.

The parser audit hashes original bounded bytes, CIK, actual UTC cutoff, requested
tags and every excluded occurrence. It retains the original reason and index;
observes unique/missing/ambiguous context references; counts direct entity,
period, segment/scenario and other children; and records existing ancestor scope
and global targeted-document barriers. It reads no extra numeric values or
dimension members. Shared context counts are cached without merging per-fact
scope flags. Structural presence is not context/dimension/conformance validity.
Invalid/oversized documents stay DOCUMENT_UNAVAILABLE, not a successful empty
financial inventory; oversized bytes are not rehashed after the size guard.

The existing manual CLI adds --explain-exclusions only with read-only --as-of;
combination with --capture fails before database/artifact/network setup. This
diagnostic has not been wired to the global equity display, official reports,
thesis evaluation or financial scoring. It must not become a route around them.
The CLI retains its three default tags. The five-tag real case below uses the
callable reader with an explicit tags tuple; counts depend on that requested
scope, not an automatically discovered whole-filing denominator.

Real retained MSFT (CIK 0000789019, accession 0001193125-26-436133), at
2026-11-09T15:13:28.573833+00:00, reproduces the original ten period checks and
source_input_hash 4e514feda9bfa15fb8b2f19a09e9f540b6e411416b445a56abbbeeae8497039b.
Five selected native tags yield 61 occurrences, with the original 45 exclusions:

| Original Barrier | Occurrences | Segment Present | Ancestor Scope Blocked |
| --- | ---: | ---: | ---: |
| dimensional or malformed context | 11 | 11 | 0 |
| nested or targeted document scope | 34 | 26 | 34 |

Segment presence totals 37, ancestor blocks total 34 and their overlap is 26;
these are not independent additive failures. All 45 references were unique in
this inventory, with one entity and period container each; no scenario, other
top-level context child or global targeted-document flag was observed. These
counts do not validate entity/period contents, taxonomy/dimension semantics or
accounting definitions. They neither prove erroneous financials nor qualify
otherwise excluded facts. Selected-tag counts are not whole-filing coverage.

Body SHA256: 02b4114045c34fdd95c32b1efbf9acde4afffc094d887031b19b0be5bb5fc825.
Audit hash: 38d5bfc88b729f32f684bc7fe1185f3a07859a62d88bd96fe32daf34340ad10a.
New ignored mode-600 JSON files in data/processed/msft-sec-exclusions-20261116
retain the full audit and summary. Existing DB/WAL/period bytes are unchanged;
repeated results and original numerical comparisons agree. Hashes bind bytes,
not independent source truth. This is a fixed historical read, not a claim to
have checked every latest filing, original publication time or purchase decision.

Thirty new cases cover structure/overlap/scope isolation, unchanged defaults,
flags rejected before I/O, malformed/oversized inputs, old values/comparisons,
retained future/failure/raw gates and deterministic read-only CLI. Full pytest:
4121 passed / 6 skipped in 412.68 seconds; Ruff, mypy (318 files), governance
(175 checks), scoped imports/default/privacy and whitespace checks pass. These
mixed-workspace checks are not independent data/method or isolated release
admission. No automatic data acceptance, dimension
support, source trust/PIT/score/validation/execution upgrade, schema or dependency
change, commit or push. Next: exact source definitions and reviewed context/
dimension semantics before any separately approved numerical thesis evaluator.

Date: October 27, 2026. Scope: a bounded WP-LAUNCH-001 / R2 evidence slice.
This is a research diagnostic, not accounting certification, an investment
assessment, validation acceptance or a buy/sell conclusion.

## Architecture

Verified retained recent issuer catalog -> explicit CIK/accession request ->
parent-pinned periodic primary-document URL -> bounded SEC bytes transport ->
provider-neutral ingestion -> existing evidence/artifact/batch tables -> exact
retained reconstruction -> bounded Inline XBRL subset -> same-cutoff, same-
accession Company Concept comparison. No new domain model or database migration.

- `sec_primary_filing_body_snapshot`: `SEC_BODY_VERSION` =
  `sec-primary-body-snapshot-v1`.
- Original document bytes are base64-retained inside one JSON artifact; body
  SHA-256 and envelope SHA-256 are separate. JSON wrapping does not mean the body
  has been normalized, rendered, repaired or re-fetched during reads.
- `SEC_INLINE_REVIEW_VERSION` = `sec-inline-subset-review-v1`.
- One SQLite read snapshot/cutoff covers the body, current verified parent,
  and concept evidence. Latest failures, tied captures, tampering, future batch
  completion and changed parents cannot fall back to older favorable bodies.
- No ticker inference or issuer/equity admission. Exact accession, form and filed
  labels bind comparison; report dates do not become public availability.
- Existing metadata/concept/page versions and default recent-only outputs are
  preserved. No source upgrade or historical backdating.

## Supported Subset And Rejections

Single UTF-8 XML-compatible Inline XBRL 2013 document; original bytes stay intact.
No scripts, schemas, redirects, external entities or linked documents execute or
load. A simple HTML doctype is accepted; internal/external DTDs, malformed XML,
unknown entities and excessive structure are rejected without HTML repair.
Limits: body 32 MiB, envelope 48 MiB, 250,000 elements, depth 128, 256 attributes/
namespace bindings per scope, 10,000 selected facts. This is not a full XBRL
processor or conformance validator.

QName resolution uses in-scope namespace URIs, not familiar prefixes alone.
Supported native US-GAAP concepts require explicit tags, matching entity CIK,
unambiguous IDs, exact duration/instant labels, and a simple ISO4217 USD unit.
Dimensioned/scenario contexts, unsupported units/continuations/targets/tuples,
nil values and ambiguous IDs remain visible without normalized values. Other
taxonomies/currencies, multi-document XBRL and other financial-sector semantics
remain unimplemented, not silently converted.

Only strict decimal text and a documented lexical subset of registered dot-
decimal transforms are handled. Scale/sign use bounded exact Decimal arithmetic;
decimals is retained as precision metadata, not another scale. No float, guessed
dash-to-zero, arbitrary punctuation removal, currency conversion or alias to a
canonical accounting measure. All matching supported occurrences are compared;
conflicting or unsupported matching occurrences prevent an agreement status.
Other excluded facts are counted and shown, not silently discarded. Agreement
is specifically `SUPPORTED_OCCURRENCES_AGREE_UNQUALIFIED`, never full validation.

Capture rechecks sensitive assignments and reflected runtime contact before
base64 encoding, including HTML-escaped contact and unsupported encoding/control
characters. Diagnostics retain sanitized error codes, not HTTP error bodies,
headers or credentials. Access identity remains transient environment-only.

## Real Capture And Implementation Correction

Issuer CIK: `0000789019`; accession: `0001193125-26-323660`;
catalog primary document: `msft-20260630.htm`; form: `10-K`;
filed label: `2026-07-29`; report end label: `2026-06-30`.

1. First capture at `2026-10-27T15:23:21.827461+00:00` retained a sanitized
   `invalid_decoded_response` failure. A bounded diagnostic confirmed HTTP 200,
   text/html, and more than 8 MiB: the initial body byte limit, not missing
   credentials or a proven provider defect, caused rejection. This failure was
   not deleted or rewritten.
2. Body capacity was raised to a bounded 32 MiB (within the existing artifact
   store limit), Accept headers made document-aware, and future oversize/empty
   bodies receive explicit `response_too_large` / `empty_response` codes. Existing
   JSON capture error semantics remain unchanged.
3. Explicit recapture retained **8,585,622 original bytes**. At fixed read cutoff
   `2026-10-27T15:25:57.208239+00:00`, 85 selected fact occurrences remain visible:
   **18 supported, 67 unsupported**. Nine native API records match all their
   supported body occurrences across these three exact periods:

| Native tag | 2023-07-01 to 2024-06-30 | 2024-07-01 to 2025-06-30 | 2025-07-01 to 2026-06-30 |
| --- | --- | --- | --- |
| RevenueFromContractWithCustomerExcludingAssessedTax | 245122000000 | 281724000000 | 331839000000 |
| NetIncomeLoss | 88136000000 | 101832000000 | 133749000000 |
| NetCashProvidedByUsedInOperatingActivities | 118548000000 | 136162000000 | 182935000000 |

Amounts above are native USD labels after explicit scale handling, not newly
qualified facts or verified growth. Supported duplicates are occurrences, not
independent votes. Excluded dimensional/unsupported facts are not proof of error;
this subset cannot establish statement scope, accounting comparability, truth,
first publication, revision lineage, or issuer-to-instrument identity.

## Reproduction Receipts

Database: ignored `data/processed/sec-filings-20261027.sqlite3`.
Artifact root: ignored `data/processed/raw/provider-artifacts`.

- Original body SHA-256:
  `89d8ae5862209ca1805996149f1d1f0d4a4a1971189e30f11a3bbb268fa3459a`.
- Body envelope SHA-256:
  `0d575fc9d1c953761b6feaf7a11d903b6044fa519d98b77e07ddd0f7e5e5fc0f`.
- Body evidence ID:
  `9715de585f6c9e595eda12af0e80fd0b7e327223e7f95a7456771a4871fe9cdc`.
- Fixed-cutoff input hash:
  `6fa0c38269fbd1ec127c72b061400fb7f3293f745237da021f1975c05add5e1f`.
- Database SHA-256 after captures:
  `24f0f88b9726a1f3510b9aae0dcd59e0093611a30350c57ff7a4a06721980803`.

Ten evidence records/artifacts/batches total: the previous eight plus failed and
successful body captures. Zero canonical facts, research reports or signals.
Integrity check passes; fixed-cutoff reads leave database bytes unchanged. Git
does not back up ignored evidence: newest database and raw artifacts still need
encrypted co-retention before a cross-device restore claim.

```sh
.venv/bin/python scripts/inspect_sec_body.py \
  --database data/processed/sec-filings-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --cik 0000789019 --accession 0001193125-26-323660 \
  --as-of 2026-10-27T15:25:57.208239+00:00
```

Read mode is offline and read-only. Capture is a separate explicit `--capture`
mode, requiring an already retained verified catalog and environment-only
declared SEC access identity. Exit 2 means diagnostic/unqualified, not a trading
approval; read the statuses rather than treating it as an implementation crash.

## Tests And Remaining Work

Focused tests cover exact bytes, scale/sign/precision, namespaces, duplicate IDs
and facts, dimensional/unsupported data, DTD/entity/depth rejection, nil handling,
comparison conflicts, future availability/completion, parent rebinding, latest
failure/tie/tamper, secrets, transport limits and explicit read-only CLI modes.
Real capture is separate from default-disabled live test coverage.

Full verification: **2530 passed / 6 skipped**, 91.64 seconds (62 new cases).
Ruff passes; mypy passes for 283 source files; governance passes 128 checks;
`git diff --check` passes. Scoped AST review finds no forbidden imports in the
four new runtime files (57 imports). Two legacy catalog and three legacy concept
fixed-cutoff hashes are preserved; current body hash is repeatable. Contact
checks cover the envelope, decoded body and database. The six skipped real-network tests remain opt-in and
are not claimed as coverage of the manual capture.

This advances only the US sample within R2. R1-R6 remain partly complete, none
fully accepted. Next: issuer/instrument and accounting-policy review, HK/MY
primary disclosures and financial-subsector definitions, then real research
and actual strategy validation. Do not expand unrelated old archives forever.
Financial scoring, canonical/replay/validation admission remain false;
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled.
No Paper, Broker, Order, Portfolio, Notification or live changes; no commit/push.

## Primary References

- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Inline XBRL 1.1 specifications](https://specifications.xbrl.org/work-product-index-inline-xbrl-inline-xbrl-1.1.html)
- [XBRL Transformation Registry 4, 2020](https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2020-02-12/inlineXBRL-transformationRegistry-REC-2020-02-12.html)

References describe source formats, not certification of this limited parser or
the issuer's numbers. Numeric equality from SEC-derived endpoints and the SEC
filing is same-origin correspondence, never independent provider calibration.
