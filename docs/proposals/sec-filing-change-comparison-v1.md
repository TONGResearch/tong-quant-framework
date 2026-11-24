# SEC Filing Change Comparison V1 Proposal

## November 23 Bounded Record Projection Implementation

Subsequent opt-in v4 now implements the per-selection parsed/returned-occurrence
multiset hashes under the boundary design below, through the existing source-
reference API/CLI. Original typed inputs and captures share the same read snapshot;
only statuses/hashes/counts are exposed. Default single/v1/v2/v3 output remains
unchanged on a fixed vector. Source failures, exact strings/duplicates/nulls/reasons
and original raw blockers remain intact. See ../sec-window-inventory-2026-11-18.md
for actual tests and scope. This does not implement full lexical extraction,
the formal SOURCE_CHANGE/SECComparisonPlan contract, financial admission or an
official report/holding method. The older design records what was pending then;
its no-new-parser/no-full-XML/source/accounting restrictions still apply.

## November 23 Record Projection Boundary Design

This follow-up defines the still-unimplemented parsed-record and representation
axes, supported by sixteen new existing-reader characterizations. It does not
add a runtime comparator, flag, new parser, version, source qualification or
financial condition. Source-reference v1/v2/v3 remain as previously implemented.
See ../sec-comparison-boundaries-2026-11-18.md for actual verification and limits.

### Parser Records Are Not Original XML

The existing inline reader stores raw_text as the first 512 characters of decoded
itertext. It stores neither full original lexical text nor the child-markup tree.
The numeric reader separately uses complete stripped itertext with a 128-character
bound. Those are different contracts: a long whitespace prefix can produce the
same preview for different successfully parsed amounts; an unsupported suffix
beyond 512 can change body bytes while leaving every returned occurrence field
identical. Character references, child markup and attribute spacing can also
change XML bytes without changing complete parser-occurrence records.

A future representation axis must therefore be explicitly scoped as
PARSER_OCCURRENCE_PROJECTION_ONLY, never full XML/lexical representation equality.
Its permitted unchanged statement is only that all projected parser fields agree.
The separate body-byte axis remains necessary to observe complete retained-body
identity. That still does not establish source authentication, accounting meaning
or business improvement. A length-512 preview does not identify whether the full
text ended there or was truncated; shorter previews still omit lexical markup.
No text-completeness or semantic-unchanged flag may be inferred from record equality.

### Future Parsed And Representation Material

Keep the existing normalized value string exactly, with native signs/scales and
the existing admission/exclusion results unchanged. Do not reparse raw_text,
normalize trailing zeros, manufacture missing contexts, deduplicate through a
Decimal/set conversion, or read an excluded value to complete a record. Existing
subset numeric agreement can coexist with distinct normalized strings. Preserve
null fields/reasons for unsupported occurrences; absence is not zero/validity.

For each unique exact selection reconstructed by the original factory, compare
every matching occurrence as a multiset. Preserve repeated-occurrence multiplicity
and distinct expanded names, entity, unit, period, status and reason. Repeated
window references must not create additional independent facts. Parsed projection
excludes query/capture clocks and location; parser-occurrence representation adds
the complete existing returned occurrence dictionary, including element index,
native attributes and bounded decoded raw_text. It remains only a parser record.
The new order test characterizes value-level multiplicity, not an implemented
general multiset comparator or acceptance of all projected fields.

Any future runtime slice must use original source-bound factories on one snapshot,
complete selected-capture identity, the existing freshness/failure gates and exact
source/review versions. Missing source/material or version-incompatible sides
stay unassessed with independently observable hashes retained. Hash material may
be computed internally without exposing new financial amounts; there is no
approval here for raw-value publication, financial arithmetic or scoring.

Full lexical/fact-text hashing would need a separately reviewed, prospectively
versioned extraction contract from exact verified bytes, with explicit completeness,
bounds and scope guarantees. Do not modify the existing 512/128 limits, historical
receipts, nested/dimensional exclusions or H3 gates to satisfy these projections.
The sixteen tests prove existing bounded-reader behavior only. Actual parsed/
representation implementation, source/accounting/method admission and holding
conditions remain pending; provider/PIT observation continues independently.

## November 23 Opt-In Check And Gap Follow-Up

Explicit optional v3 now projects existing check/gap state, requiring complete
capture identity on both original reads. See the third November 23 section in
../sec-window-inventory-2026-11-18.md. Exact selections/status/agreement/tag-scoped
counts and raw blockers remain distinct from values and absolute positions.
Missing material is unassessed; source/review version drift blocks interpretation
with hashes retained. Default single/v1/v2 output remains unchanged on a fixed
fixture. Parsed records and representation/location remain unimplemented; do not
claim complete SOURCE_CHANGE, accounting admission or verified financial changes.

## November 23 Opt-In Capture Identity Follow-Up

The existing SOURCE_REFERENCE_OBSERVATION API/CLI optionally adds complete
selected capture identity (ID, time and raw_data_hash), using the original
factory-selected capture on the shared snapshot. See the second November 23
section in ../sec-window-inventory-2026-11-18.md. Explicit v2 only; default v1 and
single-cutoff output remain unchanged on a fixed-vector check. Missing/failed/
stale/mismatched material remains unassessed and all authorities stay false.
This fills only the selected-capture material omission: parsed subset records,
representation/location and gap-state projections are still unimplemented. Do
not call this complete seven-axis SOURCE_CHANGE or verified financial change.

## November 22 Bounded Source-Reference Implementation

The existing inventory module/CLI now offers optional two-cutoff
SOURCE_REFERENCE_OBSERVATION through read_sec_source_reference_changes and
--previous-as-of. It is an explicitly narrower mode, not completed SOURCE_CHANGE
or the seven planned equality axes. Period-receipt identity, selected ID/time
reference, complete parent binding and body-byte identity are observed separately
on one outer read-only DB snapshot, preserving both original inventories/gaps.
The capture reference omits raw_data_hash; full capture identity, parsed/representation
multisets and check/gap projections remain unimplemented. Never relabel these
four observations as four fully implemented planned axes or business changes.

Source comparisons become NOT_EVALUATED when required source/freshness evidence
is unusable, not unchanged; receipt changes can be query-time changes. The default
single-cutoff path stays byte-compatible on a fixed synthetic vector. No original
parser/window meaning, new amounts, financial comparability/admission, threshold,
source trust or trade authority is changed. See ../sec-window-inventory-2026-11-18.md
for actual tests/limits. Full SOURCE_CHANGE, definition and method/OOS gates remain open.

Date: November 18, 2026, Asia/Kuala_Lumpur. Scope: ready WP-LAUNCH-001, MSFT first.
Original status: design and existing-reader characterization only. The November 18
implementation addendum below records a partial read-only window inventory, not
the complete comparator. No new admission rule, schema, financial definition,
dimension parsing or trade method is approved. Engineering review is not accounting admission.

## Objective And Two Different Axes

The existing native-change digest detects provider-record differences. The next
filing-backed layer must not mistake those differences for business growth.
Reuse SECPeriodSelection/read_sec_period_research_input and the sole official
ResearchReport/Validation contracts; do not create a parallel financial score.

1. Source-change observation: same exact CIK/accession, selected native contexts
   and financial dates at two strictly increasing actual UTC decision cutoffs.
   Detect capture/content/context differences, not verified issuer restatements.
2. Financial-window comparison: two explicitly declared financial windows at one
   decision cutoff, possibly both comparative columns in one filing. These are
   not two historical information vintages. Accounting comparability and arithmetic
   remain unadmitted until independently reviewed inputs and methodology exist.

Initial runtime scope should be same filing and existing non-dimensional supported
subset only. Cross-accession, amendment-chain, dimension and taxonomy mapping are
separate extensions, not inferred from similar local names, amounts or form labels.
No original historical publication/availability may be manufactured from the
current filing's comparative column. Replay outcome evidence is a separate axis.

## Proposed Plan Contract

The names below are API design, not importable code or executable configuration.
A future opt-in SECComparisonPlan should declare:

- Mode: SOURCE_CHANGE or FINANCIAL_WINDOW_OBSERVATION. No automatic mode inference.
- Exact requested US symbol, CIK and accession; caller linkage is still unverified
  until the existing issuer/share-class admission path supports it.
- Explicit store and artifact root, reused consistently by parent/body/period
  readers. Never search another root or accession to repair a failure.
- One to eight unique pairs, with at most sixteen distinct existing period
  selections. Preserve exact native tag and start/end or instant; canonicalize
  request order, not source context, raw text or occurrence identity.
- Two aware UTC-normalized decision cutoffs for SOURCE_CHANGE; one cutoff plus
  two explicit financial windows for FINANCIAL_WINDOW_OBSERVATION. Never overload
  the financial-period fields with decision/retrieval times.
- Expected expanded concept name (namespace URI and local name) for each side;
  exact unit, entity and period basis; occurrence/source pins and reviewed
  definition references. References are declarations, never source approval.
- A separately reviewed, bounded source-age/freshness policy if age is evaluated.
  Native capture-age examples are not approved SEC publication/freshness policies.
- Explicit financial-window relation, definition version and statement/sector
  scope declaration. Free-text consolidated/Azure/FCF labels cannot certify scope.

Inventory-only plans may declare absent definition/review references explicitly;
the output must record those gaps and remain NOT_ADMITTED. Do not invent a review
identifier or block safe source-inventory development while admission is pending.

The current SECPeriodSelection does not carry namespace, definition or complete
dimensions. Do not modify its default meaning or filter out other occurrences to
satisfy an expected namespace. A wrapper may expose the ambiguity; it cannot
admit dimensional facts or treat absent dimensions as verified consolidation.

## Read And Decision Procedure

1. Validate mode, typed bounds, exact identity and UTC chronology before reading.
   SOURCE_CHANGE requires previous < current in actual UTC, including DST folds;
   the other mode must not demand different financial windows be decision cutoffs.
2. Reconstruct through existing retained factories, never accept caller receipt
   JSON/checksums as source proof. Recheck exact context and source/body/parent
   hashes and versions at the requested cutoff.
3. For one store, all relevant reads share an outer read snapshot. Separate price
   and filing stores share a cutoff only, never claimed cross-store atomicity.
   A future cross-store composition needs its own explicit consistency contract.
4. Preserve latest missing/failed/tampered/ambiguous/future/expired source states.
   No old-good, nearby-period, alternate filing, Yahoo or different-tag fallback.
5. Inspect all returned supported occurrences and unresolved/unsupported scope
   inventories. A supported subset's numeric agreement is not an independent vote
   or completeness test. Preserve conflicting and repeated occurrences separately.
6. Require exact namespace/unit/entity/basis/period agreement with each declared
   side. Multiple namespaces, mismatches, unresolved context or unsupported matching
   occurrences block an economic comparison; never pick a favorable occurrence.
7. Distinguish instant balances from duration flows. Same end date or day count,
   10-K/10-Q, FY/Q1, 12M, 52/53 weeks and calendar-quarter labels do not establish
   fiscal equivalence. Do not annualize, subtract cumulative periods or create TTM.
8. Inspect definition, consolidation/sector scope, period/column role, revision,
   publication, source quality and method admission independently. Missing authority
   remains NOT_ASSESSED/NOT_ADMITTED; a caller boolean cannot supply it.

Initial implementation should emit a versioned read-only comparability inventory,
not arithmetic or financial condition labels. Even when raw subsets align, all
accounting/financial-score/Validation/replay/holding/execution authorities stay
false. Source-bound means verified retained content, not independent source truth.
No new FinancialInputSnapshot profile or Report completion follows from this plan.

## Proposed Output And Future Arithmetic

Keep two separately named sections: source_record_changes and window_comparability.
Bind mode, cutoffs, exact windows, requested/verified identity separately, source
versions/hashes, selected captures, all occurrence references and blocker codes.
Unknown inventories/counts are null, not zero. Empty observed sets need an explicit
source state. Missing metrics are not issuer-wide nondisclosure or zero amounts.

Source-record status may describe identical/different retained records, keeping
capture changes separate from content. It cannot label issuer restatement proven.
The following equality axes must be versioned separately, not collapsed into one
changed flag or inferred from a whole-receipt hash:

| Axis | Exact comparison material | Excluded from that axis |
| --- | --- | --- |
| Receipt identity | Existing complete canonical receipt/input hash | Nothing; binds the requested cutoff but is not a content-change test |
| Selected capture | Selected evidence ID, selected capture available_at and raw_data_hash | Requested as_of and nonselected capture-history rows |
| Parent binding | Complete canonical source_parent_binding and exact CIK/accession | Requested symbol/definition annotations; never relabel a parent change as business growth |
| Body bytes | source_body_sha256, only when both sides are source-bound and usable | Envelope/capture time, receipt hash and query cutoff |
| Parsed subset records | Multiset of tag, taxonomy, namespace, entity_cik, exact start/end, unit, normalized value string, status and reason from every matching occurrence | Query/capture times, element_index, raw_text and lexical native_attributes |
| Parser-occurrence representation/location | Complete existing returned occurrence multiset including element_index, bounded decoded raw_text and native_attributes | Query/capture times; original XML markup/lexical completeness is not represented or implied |
| Check/gap state | Exact selection, check status, numeric-agreement state, unresolved-presence/count and source supported/unsupported counts | Absolute unresolved element positions, retained separately as source references |

Missing fields in occurrence projections remain null; never synthesize a context.
Preserve duplicate multiplicity and all original occurrence references. Canonical
field projections use structured JSON and existing source bounds. Values retain
the parser's normalized string: lexical numeric differences are descriptive,
not a claim of changed economic magnitude. Prefix/context-ID/position changes may
alter representation without altering expanded-name/period/value projections.
Unresolved presence/count remains an unknown-scope blocker, not a new fact amount.
Different review/model/normalization versions block parsed-record interpretation
and receive INTERPRETATION_VERSION_CHANGED; byte comparison may remain possible.
Both unavailable and uninspectable comparisons are NOT_EVALUATED, not false/zero.

When only as_of advances and the selected source is identical, the two full
receipt/input hashes can differ while selected capture, parent, bytes, parsed
subset, representation and check/gap state stay identical. Capture freshness is
re-evaluated separately; becoming stale is not source content change. Reconstruct
at each cutoff instead of dropping timestamps from arbitrary supplied receipts.
The existing-reader cutoff-only fixed vector is a characterization baseline,
not proof that these proposed comparisons have been implemented.

Window status may describe matching raw subset context, but economic comparison
must remain NOT_ADMITTED while definition/source/method gates are incomplete.
Do not expose an ambiguous bare comparable=true that downstream code can misread.

Future independently admitted arithmetic needs a separately versioned policy:
exact Decimal bounds, nonpositive denominator behavior, fiscal continuity and
signed/zero inputs, plus reproducible method tests. It is not implemented by this
proposal. No growth, FCF, valuation, profitability threshold, probability, holding
duration, add/exit instruction or technical/financial vote aggregation is approved.

## Existing Evidence And Acceptance

The paired November 18 evidence record reports exact retained MSFT reconstruction
at the original November 9 cutoff. Ten selected quarter contexts are supported
subsets; six retain unresolved tag contexts. Four without that flag are only
review candidates, not automatically complete or admitted. Excluded Azure and
MicrosoftCloud contexts remain excluded under the November 16 dimensional plan.

Implemented characterizations in tests/test_sec_comparison_boundaries.py exercise
the existing reader, not the proposed comparator: matching/conflicting amounts
with one/two namespaces, different duration starts at one end, instant versus
duration, excluded contexts despite supported agreement, retrieval visibility and
latest failure and the fixed cutoff-only identity/content distinction. No passing
count may be described as comparator acceptance.

Future implementation acceptance additionally needs fixed old-output vectors;
strict mode/bounds/context/source validation; independent-writer snapshot tests
at component boundaries; source failure/tamper/stale/future/DST/one-microsecond
cases; reordered/repeated/conflicting observations; representation versus value
changes; explicit caller-only versus verified mappings; no dimension/scope
promotion; no arbitrary rehashed JSON; false authorities and privacy checks.
These future cases have not been implemented or passed merely by being listed.

Next bounded runtime slice: opt-in comparability inventory on the existing
non-dimensional SEC period path after this contract's scoped engineering review.
Keep actual accounting admission and method/OOS validation separate. Provider/PIT
observation continues in parallel and does not block safe software development.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled.

## November 18 Partial Implementation

application.sec_window_inventory.SECWindowPair/read_sec_window_inventory and
scripts/inspect_sec_windows.py implement one-cutoff, same-filing, same-tag window
inventory only. Existing source factories and exact context checks are reused;
the standalone CLI accepts one pair and the API up to eight. An explicit expected
namespace and positive capture-age limit are requests, not independently reviewed
taxonomy/freshness policy. No amounts or arithmetic are output; economic status
is always NOT_ADMITTED and all authorities stay false. Existing default paths
are not modified. See ../sec-window-inventory-2026-11-18.md for tested scope.

This does not implement the SOURCE_CHANGE mode/seven equality axes, reviewed
definition-reference contract, dimension support or financial admission. The
initial inventory uses explicit missing review gaps, not caller self-approval.
Do not reinterpret the earlier twelve characterization tests as full comparator
acceptance or the new runtime as completion of all proposed cases.
