# SEC Issuer Filing Evidence

Work package: WP-LAUNCH-001; ready, not accepted.

## Source Semantics

The SEC submissions endpoint supplies issuer metadata and bounded recent filing
columns, with references to older JSON pages. It is not itself the filing body
or numeric XBRL extraction. See the [official API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

EDGAR acceptance is not exact first public dissemination. The official filing
date is also a different label; report dates need form-specific interpretation.
The [SEC developer FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
explains timestamp distinctions, public availability lag and declared User-Agent
requirements. Do not convert acceptance/filing dates into historical published_at.

## Implementation

`data.providers.sec_submissions.SECSubmissionsAdapter` follows the existing
provider-neutral capability/evidence/artifact interfaces. Dataset identity is
`sec_issuer_filings_snapshot`; provider is `sec_edgar`. Requests require an
explicit ten-digit CIK, US routing and no parameters, never guessed ticker/CIK
mapping. US routing does not prove an issuer is a tradable US equity.

The endpoint is fixed to data.sec.gov. Runtime access identity comes only from
`TONG_QUANT_SEC_USER_AGENT`; this slice does not write that environment setting.
Requests are bounded to two sequential attempts, ten-second timeout and 2 MiB
response read, with pauses and no redirects. No contact/header values or remote
error bodies are retained. Credential-like decoded content, reflected contact
identity, ambiguous duplicate JSON keys, bad identity and invalid responses are
rejected. Capture failures retain sanitized status evidence. The local pacing
does not coordinate independent processes; operators must respect aggregate SEC
fair-access limits. No crawler, automatic schedule or contract-monitor enrollment
is added.

The retained decoded envelope is not original HTTP wire bytes. Explicit capture
feeds the existing atomic ingestion/artifact ownership checks; the read side
reconstructs the exact envelope, normalized record, registry and completed batch
at an actual UTC cutoff. Latest failed/tied/rejected/corrupt/uncompleted inputs
never fall back to older favorable metadata. Missing inputs remain visible.

`scripts/inspect_sec_filings.py` requires either explicit capture or fixed-cutoff
read-only mode. Diagnostic exit code 2 means unqualified output, not a crash or
validation success. For example, after capturing into an approved local database:

```text
.venv/bin/python scripts/inspect_sec_filings.py \
  --database data/processed/sec-filings-20261027.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts \
  --cik 0000789019 --as-of 2026-10-27T11:55:09.798965+00:00
```

No source is trusted by default: all new records stay LOW/RETRIEVAL_TIME,
capability DEGRADED, continuity unverified. published_at is unknown, available_at
is capture time, and raw acceptance strings plus normalized aware timestamps
remain separate. The legacy required artifact publication field is explicitly
capture time with RETRIEVAL_TIME precision, never issuer publication.

## Real Capture And Reproduced Defect

Two real snapshots for issuer CIK `0000789019` were retained on October 27:

| Version | Read cutoff UTC | Result | Input hash |
| --- | --- | --- | --- |
| v1 | 2026-10-27T11:52:04.038336+00:00 | 1002 observed, 1 quarantined | `78e53807eead170bcabe4b70b10fba70e93e865aa3d889720964bbc658ccfe9f` |
| v2 | 2026-10-27T11:55:09.798965+00:00 | 1003 observed, unqualified | `db0beeb1bfca8ea9e41add35d26a15dd239f4d7e64d7d32bfcd2dcb7f79c8436` |

The first real response exposed a parsing assumption: DEF 14A accession
`0001193125-26-427849`, filed October 21, labels reportDate December 8. A known
prospective meeting date is not future availability. V2 reserves period-end
labels for 10-K/10-Q/20-F/40-F families, preserves other form-specific dates and
flags prospective labels rather than treating them as financial periods. Official
future filing-date labels also remain separate from actual acceptance/capture.
Actual future acceptance timestamps and unsupported financial-period labels
remain quarantined. Nothing gains numeric financial eligibility.

V1 remains reconstructible using its original normalization, payload and input
hash; v2 is a separately captured version, not a silent rewrite. The second
capture has six 10-K and eighteen 10-Q rows, but row counts do not prove complete
filing history or audited financial facts. Two older pages advertise 2007 and
1521 rows; both remain NOT_CAPTURED. No historical coverage percentage is inferred.

Amended forms retain distinct accessions. `/A` is a label, not proof of financial
restatement, a numeric revision sequence or a replacement link. Duplicate
accessions and malformed rows stay visible. Raw report dates are not fiscal
period starts and do not support TTM or comparability by themselves.

The database has two evidence records, two artifacts and two completed batches;
canonical fundamental facts, reports and signals remain zero. Repeated read-only
reconstruction preserves both hashes and database bytes:
`a649e71d725cf22b433795f8e54cd3f67fbd06f1ae1004443dd3f3d369bf00d6`.
Contact identity byte checks are negative in both new envelopes and the database.
This verifies scoped persistence, not external transport logs or absolute truth.

## Boundaries And Remaining Work

No numeric accounting mapping, ResearchQueue fabrication, report, score, PIT
replay eligibility, provider independence or investment decision is introduced.
The existing Yahoo and CNInfo contracts and their source receipts are unchanged;
SEC evidence is not automatically joined to an equity or treated as independent
calibration. Issuer/ticker association, filing body/XBRL/accounting definitions,
amendment relationships, older-page continuity and cross-source checks still
need verification. HK/MY primary-disclosure coverage is not supplied by this US
slice. New ignored source bytes and the database need encrypted co-retention;
Git alone cannot move them to another machine.

No schema migration, Paper/Broker/Orders, Portfolio, Notification or live change.
PIT UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
Verification: 2388 passed / 6 skipped in 124.52 seconds, 61 added cases; Ruff,
mypy (273 files), governance (125 checks) and whitespace diff checks pass. Tests
cover request scope, explicit clocks/date roles, versioned reconstruction,
duplicates, missing/corrupt/latest-failure states, idempotency, HTTP bounds/retry/
redirects, access-identity redaction and read-only CLI. Six default-disabled live
provider/notification tests remain skipped; real SEC captures are separate.
