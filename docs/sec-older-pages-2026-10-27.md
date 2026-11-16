# SEC Older Pages And Bounded Reference Expansion

WP-LAUNCH-001 remains ready, not accepted. No schema or trading change.

## Implementation

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes recent submissions and references to older JSON pages. This slice
captures only explicitly named, verified-parent references; it adds no crawler,
arbitrary URL, new provider schedule or independent-source claim.

Dataset `sec_issuer_filings_page_snapshot` binds CIK/filename and exact parent
evidence ID/hash/availability plus declared count/date interval. The request
factory reconstructs a usable local parent and requires a unique reference before
network access. Provider-neutral persistence reuses bounded SEC transport and
the existing form-aware normalizer. The page has no independent body CIK claim:
issuer association is its pinned URL/parent reference, not equity admission.
Capture cannot precede parent availability. Availability stays actual retrieval,
LOW/RETRIEVAL_TIME; filed/acceptance dates never become exact public availability.

The archive reader rechecks exact page bytes, record/registry/completed batch,
current parent identity and descriptor. It preserves latest failure/tie/corrupt/
future-completion states without favorable fallback. Parent changes require
explicit new capture/review, not silently rebinding old pages. Count disagreement
or dates outside the declared interval quarantine a page; native rows remain in
the retained evidence record. Cross-page duplicate accessions remain ambiguous.
Read bounds are 16 referenced pages and 50000 merged rows; additional/unusable
pages generate explicit coverage gaps, not full-history claims.

`read_sec_concept_inputs(..., include_older_pages=True)` explicitly opts into
this broader reference view under the same SQLite snapshot/cutoff. The CLI adds
`--include-older-pages`. Default recent-only output/hashes remain unchanged.
Page gaps block references in their declared intervals, while outside-period
usable recent references remain visible. Invalid merged rows keep partial status.
The archive's `older_pages` are original parent descriptors; `pages` records the
current capture/use state. A captured-but-quarantined page is never a usable page.

## Real Observations And Repair

Two older pages were explicitly captured for CIK 0000789019:

| Page | Declared rows | Observed filing-date range | Result |
| --- | ---: | --- | --- |
| 001 | 2007 | 2008-08-13 to 2020-08-26 | Inside parent's 2008-08-13 to 2020-08-31 interval; v2 usable for unqualified metadata references |
| 002 | 1521 | 1994-02-14 to 2008-08-12 | Exceeds parent's upper date 2008-08-11; quarantined |

The first v1 implementation incorrectly required observed extrema to equal the
declared interval endpoints. V2 requires exact count and interval containment,
not artificial equality of extrema. Both v1 page captures and original archive
hashes remain reconstructible. Page 001 was explicitly recaptured under v2;
no source record, hash, availability or original warning was overwritten.

Page 002 also contains 137 rows outside the current metadata-field support
contract. Neither its one-day date mismatch nor these rows were silently fixed.
The mismatch is not established as a provider defect: date-label semantics need
review. It remains an explicit older-period gap, not a network retry problem.

At `2026-10-27T12:35:00+00:00` the merged view has 3010 usable/in-scope catalog
rows (1003 recent + 2007 page 001). Current three-concept references are:

| Native concept | Previous matches | Expanded matches | Expanded input hash |
| --- | ---: | ---: | --- |
| Revenue | 81 / 134 | 134 / 134 | `b82a0a64b3d34d884630ac9ae1882b8779056f6a5f01388e0071607ce09c88f2` |
| Net income | 86 / 345 | 345 / 345 | `08baf6651e044fcb1792ec3ece5944a79e8eba6fad85cfa38a246700b3df4bd9` |
| Operating cash flow | 81 / 170 | 170 / 170 | `3660de73ec6099c7ced627c12799dcca36b052bd8631ce771cb0b10e80aa5057` |

The targeted 401 missing references are closed for these observations, whose
filing dates begin in 2009. This is not full historical coverage, independent
numeric verification, accounting qualification or 100% PIT readiness. Page 002
remains a gap; do not make unrelated pre-2009 cleanup a prerequisite for all
approved software work, and do not delete that gap or weaken historical gates.

Repeated expanded reads match; both original SEC catalog hashes, all three
recent-only concept hashes and both v1 archive hashes still reproduce at their
original cutoffs. The local SEC database now has eight records/artifacts/batches,
zero canonical fundamental facts/reports/signals. Read checks preserve its hash:
`35f47cd8a37bccea729aa84530d34bbf588e5c91b5d4d1e4e7a6d8ef20fd4507`.
No contact identity is found in new envelopes/database. New ignored evidence
still requires encrypted co-retention; no Git portability claim is made.

## Remaining Acceptance

The six release acceptance groups remain open, as reviewed in the current
[delivery plan](decision-delivery-plan-2026-10-27.zh-CN.md). This slice closes a
specific US sample reference gap within R2, not R2 or the four-market release.
Next prioritize filing-body/accounting/issuer review, HK/MY disclosure inputs,
financial-subsector definitions and actual technical-plus-financial validation.
No new report/score/PIT eligibility, Paper/Broker/Portfolio/Notification/live
behavior. PIT UNSUITABLE, production NOT_READY, execution/notifications disabled.
Verification: 2468 passed / 6 skipped in 137.08 seconds, 33 added cases. Ruff,
mypy (279 files), governance (127 checks), scoped forbidden-import review and
whitespace diff checks pass. Regression cases cover explicit parent/URI/clock
binding, count/range/field errors, v1 preservation, opt-in default hash stability,
corruption/ties/future completion, changed parents, overlapping duplicate
accessions, partial-status preservation and strict boolean opt-in. Six default-
disabled provider/notification live tests remain skipped; real captures are
separate from financial/source/strategy qualification.
