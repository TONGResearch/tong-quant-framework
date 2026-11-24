# SEC Comparison Boundary Evidence

Subsequent November 23 optional runtime now implements only the bounded
parser-record hash projections described below. See
sec-window-inventory-2026-11-18.md for the v4 implementation/check record. The
design/test delivery below did not itself add that runtime; parser limits,
full-XML nonclaims, exclusions and all source/financial/method gates remain.

## Parser Record Versus Body Boundaries: November 23

Design and existing-reader test follow-up only; no runtime/CLI/version/default/
schema or parser limit changes. Source-reference v1/v2/v3 already exist, but the
remaining parsed-record and parser-occurrence representation projections are
not implemented. See the new design section in
proposals/sec-filing-change-comparison-v1.md before extending them.

Sixteen added synthetic characterizations (28 tests in this boundary module):
raw_text previews at lengths 511/512/513/1024; complete stripped numeric input at
127/128/129; different unsupported suffixes beyond the preview with identical
complete matching records; long whitespace-prefix previews with different valid
parsed values; child-markup/character-reference/attribute-spacing differences
with identical records; exact normalized-string preservation despite subset
numeric agreement; reordered repeated-value multiplicity and retained conflict.
All tests use original readers and synthetic temporary stores, not real retained
source files or a new projection implementation. Exact body hashes distinguish
the paired changed bytes. No source trust or economic admission follows.

The 512-character preview is not the numeric parser input and cannot authenticate
full original text or markup. Equal normalized Decimal quantities need not have
identical returned value strings; repeated observations remain separate. The
order case tests value-level counts, not a general projected-record multiset
algorithm. Existing unsupported rows stay unsupported with null values and
original reasons preserved; no nested/dimensional/H3 numerical support is added.

Future representation claims are limited to PARSER_OCCURRENCE_PROJECTION_ONLY.
Body-byte equality remains separate from source truth, accounting definitions
and strategy evidence. A future complete lexical hash needs separate reviewed
extraction/length/scope/version guarantees. The current design forbids reconstructing
amounts from previews, silently normalizing source strings or changing 512/128
limits/old receipts.

Final boundary module: **28 passed**, including sixteen added cases. Final related
SEC/H3 suites: **439 passed**, 81.68 seconds. Full working-tree pytest:
**5119 passed / 6 skipped**, 497.79 seconds. Ruff, mypy (324 source files),
governance (189 checks), whitespace and scoped eight-file known-pattern/privacy
checks pass. All 487 Python/config inputs retain the before/after final-suite
fingerprint:
a738acddd38a35b2c896f2d6631c6916ad5c6838faeec405003680d9a0e385ed.
Independent read-only static review/follow-up finds no actionable issue in these
tests and design. The follow-up confirms the exact 127/128/129 threshold cases;
the order case remains value-level multiplicity, not a full multiset comparator.
Reviewers did not run tests or independently regenerate hashes, inspect real
raw/DB/credentials, use network, edit or push. No source/accounting qualification
or unrelated-change certification follows.

Only this existing test module and seven existing guidance/design/status files
change this turn, inside the same 36 pending paths. Index empty and HEAD 4774193
unchanged; checks include prior pending work, not isolated candidate/release
verification. No runtime/CLI/version/schema/dependency/default, real-source
refresh, scheduler/trading, commit/push or owner action. Next implement/review
only the bounded source-bound record projections under these stated limits;
complete lexical extraction and financial/method/holding admission stay separate.
WP-LAUNCH-001 ready, not accepted; PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled.

Work package: WP-LAUNCH-001. This delivery is an implementation-ready comparison
proposal plus existing-reader regression evidence, not a runtime comparator or
accepted accounting definition. No production code/default/schema/version changes.
See proposals/sec-filing-change-comparison-v1.md and the existing dimensional plan.

## Concrete Gap

SECPeriodSelection selects native tag and exact dates, not namespace or complete
statement/dimension definitions. Existing receipts correctly remain unqualified.
Numeric agreement can coexist with unresolved contexts or multiple namespaces;
same ending date/value can coexist with different duration windows or an instant.
A future change consumer must not read OBSERVED_SUBSET_UNQUALIFIED as approved
growth, complete consolidation, historical availability or an exit/add condition.

Twelve new synthetic characterizations cover these distinctions through the
existing retained period reader. The source pipeline and matching observations
are retained; no new qualification gate or dimension support is silently added.
They prove existing behavior, not the unimplemented proposal's future behavior.

## Retained MSFT Rehearsal

Reconstruct the existing exact-quarter receipt at its original
2026-11-09T15:13:28.573833+00:00 cutoff, not today's disclosure state. Request
order reversal must reconstruct the same full canonical receipt and hash. Pin
the existing database, committed WAL, original artifacts and receipt before/after.
No network, new capture or data initialization is needed. Read-only SQLite may
create empty coordination sidecars; no zero-filesystem-metadata claim is made.
The full canonical receipt matches the existing file, including its hash
055be22569c2c37f32c262168b48ccf82234340df525f495d382c6868629bcec.
Source body SHA256 remains
02b4114045c34fdd95c32b1efbf9acde4afffc094d887031b19b0be5bb5fc825.
All ten checks remain supported-subset/unqualified; six retain unresolved tag
contexts. The five requested tags span 61 source occurrences in this file,
including 45 unsupported occurrences. These are not whole-filing/company
denominators, and tag-level unresolved context does not prove a competing fact
belongs to a particular requested window. All five pinned existing files retain
exact hashes. Source-bound remains true, accounting admission/execution false.
The fixed synthetic cutoff-only vector demonstrates different receipt hashes
with identical selected capture, body, parent and matching facts. Period-isolation
tests assert actual successful occurrence hits, contextRef and exact original
dates, not only request-derived basis/day labels. The reviewed proposal now
separates receipt, capture, parent, body, parsed, representation and gap-state
equality. Updated focused/full quality and review results follow below.

Final focused suite: **223 passed**, 61.11 seconds, including twelve new existing-
reader characterizations. The earlier full run was deliberately stopped to
strengthen review findings; it is not a qualifying pass. The new full run below
covers the final stable test source.

Independent read-only AI review found request-derived period assertions too weak
and source-change equality fields underspecified. Tests now verify real fact
hits, exact contexts/dates and nonempty disjoint occurrences; the proposal fixes
the seven equality axes and a cutoff-only fixed vector. Static re-review found
both issues closed with no further actionable issue. The reviewer did not run
tests, inspect the real retained data or independently generate the golden hashes.
This is scoped engineering review, not financial/comparator acceptance.

Final stable working-tree pytest: **4636 passed / 6 skipped**, 442.07 seconds.
Ruff, mypy (322 files), governance (187 checks), whitespace and scoped known-pattern
privacy/disabled-default checks pass. All 483 tracked/new Python/config inputs
retain the same before/after fingerprint:
bdfdb2ffdceaff224f36ed8c971c6a09290ea817c2acc7f993dde1784732a991.
Twenty-two pending code/doc/config paths include nineteen pre-existing dirty
paths. Earlier work is preserved, not independently certified by this design/test
slice. The index remains empty; no private holdings, raw source content, DB,
logs/cache or IDE outputs were added to Git. These mixed working-tree checks are
not isolated candidate-tree checks/review required before a future reviewed sync.
No production code/default/model-version/schema change, commit or push this turn.

The known ten selections cover two exact 07-01/09-30 windows (2025 and 2026) for
operating cash flow, net income, operating income, property/plant/equipment
payments and contract revenue. These are native contexts, not independently
admitted accounting definitions or financial-window equivalence. Do not create
FCF by subtracting two plausible tag names or treat net income as automatically
parent-attributable profit. Missing/unresolved context is not zero or no risk.

No owner holdings/risk preferences or raw filing content enter tracked documents.
No action is required from Tong for this design/test slice. Future source and
accounting qualification is a separate review, not solved by caller declarations
or by waiting out the provider/PIT observation horizon. No commit or push.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled. The
continuous loop and WP-LAUNCH-001 remain ready, not accepted.
