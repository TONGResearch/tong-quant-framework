# Same-Filing SEC Window Inventory

The November 23 XML-affix follow-up in msft-h3-definition-review-2026-11-19.md
gives a fixed-source example of presentation tokens outside returned numeric
fact records. It does not change this API or permit full-presentation, financial
sign or holding claims from parser-record equality.

## Optional Compact Source View: November 23

The existing two-cutoff API adds exact-boolean compact=False; CLI --compact
requires --previous-as-of before storage construction. All v1/v2/v3/v4 options
remain explicit. The public path first recomputes and hashes the complete original
observation using the same factories/snapshot, then emits a compact projection.
There is no caller-receipt or cached-summary input, new research report, source
admission, capture, strategy or trading capability. Omitting --compact keeps the
existing single-cutoff and v1-v4 complete output exact on one frozen fixture.

The view uses sec-source-observation-compact-view-v1 and explicit output_scope
COMPACT_SOURCE_OBSERVATION_VIEW. source_observation_model_version/hash identify
the full recomputed result, each full_inventory_hash identifies the full original
inventory, and summary_hash hashes the compact content itself. These hashes have
different meanings. The compact view cannot reconstruct omitted data to rederive
the full hashes; a received hash is not source authentication. Recompute through
the original retained store for verification, never admit arbitrary summary JSON.

All root statuses/axes, authority flags, versions, limitations, pending axes and
optional materials/counts remain. Each source summary preserves original source/
body/binding references, capture age/freshness, inspected/count state, all pair/
selection/check/raw blockers and review gaps. Per-occurrence references and exact
unresolved positions are omitted, with unresolved counts retained as None when
uninspected. Detailed parent bindings and other omitted inventory fields are
listed explicitly. Original full output remains available; this is not a complete
evidence packet or an input qualification upgrade. A retained failed capture can
remain source_bound=True while inspected=False/count=None; preserve all of them.

Forty-nine added cases cover all four source modes, missing/latest failed/stale/
namespace/unresolved/first/many/observed-empty states, exact option and CLI gates,
full/view hash distinctions, unchanged full material, tampered returned views,
original two-read recomputation and an interleaved writer. Two synthetic v4 size
examples measure 16974 -> 13599 bytes (19.88 percent reduction) and 55224 -> 13609
bytes (75.36 percent reduction with 80 extra synthetic repeated occurrences).
These are canonical JSON byte measurements, not actual token/billing measurements
or independent financial evidence. Output size benefit depends on source shape.

Frozen pre-edit single-cutoff/v1/v2/v3/v4 outputs match at 4723/12259/13017/15568/
16974 bytes; v4 SHA256 is
0d5ca59c553a8042b7d8a9b3fcb98695c938b5a973913319a6841484c77ed60b.
Earlier mode hashes are recorded below and remain unchanged on this same fixture.
No real source/DB was inspected/refreshed. Full lexical/formal SOURCE_CHANGE,
source/PIT/accounting/freshness/method/holding gates and all H3 exclusions remain.
Final compact module: **49 passed**. Final related SEC/H3 suites: **550 passed**,
105.50 seconds. Full working-tree pytest: **5230 passed / 6 skipped**, 538.83
seconds. Ruff, mypy (324 source files), governance (189 checks), whitespace and
scoped eleven-file known-pattern/privacy checks pass. All 489 Python/config
inputs retain the before/after final-suite fingerprint:
6cd18b0d16d5c8a65b000cd6f87ba10815b79e8720b302461ed4032d28dc0e38.
Authorized read-only static review finds no actionable scoped issue. The reviewer
did not execute tests/byte comparisons or inspect real raw/DB/credentials/network;
size/compatibility results are main-runner checks, not independent source or
financial validation. The receiving-view/full-evidence distinction remains open
to the original retained-source verification, not solved by summary_hash.

Eleven code/test/doc files change this turn, including one new test module;
38 pending paths remain local, empty index and unchanged HEAD 4774193. These are
working-tree checks including earlier pending changes, not isolated candidate/
release verification. No schema/dependency/default, real capture/refresh,
scheduler/trade, commit/push or owner action. Source/accounting/freshness/method/
business-outcome qualification and controlled update/recovery remain next gates;
the compact view cannot close them. WP-LAUNCH-001 ready, not accepted; PIT
UNSUITABLE, production NOT_READY, execution/notifications disabled.

## Optional Parser Record Projections: November 23

The existing source-reference API adds exact-boolean with_record_projections,
default False, requiring with_check_gap_state=True and its complete-capture
dependency. CLI --with-record-projections requires the existing gap/capture flags
and --previous-as-of; dependency errors reject before constructing storage.
Explicit opt-in uses sec-source-reference-observation-v4-parser-records. All
single-cutoff/v1/v2/v3 defaults remain unchanged on a frozen synthetic vector.
Success remains diagnostic exit 2, not source or trading admission.

The private original reader now retains its typed SECPeriodResearchInput alongside
the unchanged public inventory and selected capture. Both cutoffs use the same
outer read-only DB snapshot and original factories. Record material revalidates
the typed context and exact research/input hashes, subject, source/review versions
and original selected capture ID/time/raw hash. Mixed internal bindings raise;
unavailable/stale/failed/malformed identity keeps that side unassessed. No caller
receipt, raw-text reparsing or second source lookup can supply the record material.

Two separately hashed axes are added internally:

| Axis | Material and limits |
| --- | --- |
| parsed_subset_records | Per unique exact selection, a multiset of original tag/taxonomy/namespace/entity/period/unit/value-string/status/reason fields; absent fields remain null |
| parser_occurrence_representation | Per unique selection, a multiset of complete existing returned occurrence dictionaries, including original element index, native attributes and bounded decoded raw_text |

Structured canonical sorting preserves duplicate multiplicity, exact normalized
strings and every original matching occurrence, including unsupported rows with
null values and original reasons retained. Repeated pair/window references do not create extra
facts. Original namespace/period/raw-context blockers remain in both inventories
and gap state, not filtered away to improve agreement. Compatible interpretation
uses the existing version gate. Public output contains only axis statuses/hashes,
per-selection counts and explicit scope, not the new record/value/text material.
An inspected exact window with zero matches has an observed empty multiset and
MISSING_EXACT_PERIOD blocker, not a missing-source null or issuer-wide zero.

representation_scope is explicitly PARSER_OCCURRENCE_PROJECTION_ONLY; raw_text
remains a 512-character decoded preview with omitted lexical XML/child markup.
Unchanged parser records can coexist with different body bytes. Value-string
differences can be precision/lexical differences, not economic magnitude changes.
Full lexical representation remains explicitly unimplemented, as does the formal
SOURCE_CHANGE mode/SECComparisonPlan; full_source_change_mode_implemented=False.
No raw financial amount publication, new parser/tag acceptance, dimensional/nested
support, financial arithmetic, score/report/thesis/holding or trading rule follows.
H3 exclusions and all seven UNKNOWN accounting relations stay unchanged.

Sixty-two added cases: 35 in tests/test_sec_record_projections.py and 27 additional
v4 cases in existing mode suites (220 inventory tests total). They cover exact
original-factory material hashes, content versus index/context/prefix changes,
normalized-string/duplicate/order preservation, bounded-preview/markup equality,
unsupported reasons, source failure/tamper/ambiguity/future/stale/wrong-root and
parent invalidation, malformed capture, mixed bindings, asymmetric availability,
observed empty windows, unique selections, writer snapshots and strict CLI/options.
Private binding/projection fault tests are not real-source acceptance evidence.

One fixed synthetic fixture matches frozen pre-edit defaults exactly:
single-cutoff/v1/v2/v3 JSON sizes 4723/12259/13017/15568 bytes, SHA256 respectively
b9c9c1070ccd7544b72322ad3e78d37b456cf5a64f2b5ff1373efc5da9597f89;
15de65d87e9547cceef8aeab62ef027429586bcce36451cae885b13a44c79702;
e57627cf0e0882f673a33313fa74cf20a69e9b3c375990e87de2d9d9eaed6709;
73efec4d7cfc1457422b581b4f9d998f4f265921699b075d8749a49c2857b408.
This is fixed-vector compatibility, not universal old-code/source qualification.
No real retained source/database was inspected or refreshed. Existing DB snapshot
does not lock external artifacts; source/PIT/accounting/freshness/method/OOS and
business-outcome qualification remain separate. All authorities remain false,
LOW/retrieval_time, ready not accepted and production NOT_READY.

Final record module: **35 passed**; related SEC/H3 suites: **501 passed**, 98.55
seconds. Full working-tree pytest: **5181 passed / 6 skipped**, 552.61 seconds.
Ruff, mypy (324 source files), governance (189 checks), whitespace and scoped
thirteen-file known-pattern/privacy checks pass. All 488 Python/config inputs
retain the final-suite before/after fingerprint:
e1ea55e0421a79ef1c11a0b4549166a58ab1024e946c949eec412d31cd84c56e.
Authorized read-only independent review finds no actionable scoped issue; follow-up
also checks the added observed-empty-window test. Reviewers did not run tests or
compatibility checks, inspect real raw/DB/credentials, use network, edit or push.
These engineering results do not establish source, accounting or method admission.

Thirteen code/test/doc paths change this turn, including one new test module;
37 pending paths remain local, index empty and HEAD 4774193 unchanged. Checks
include earlier pending work and are not isolated candidate/release validation.
No schema/dependency/default, real source refresh, scheduler/trade, commit/push or
owner action change. Next independently reviewed source/statement/definition,
freshness/revision and method/business-outcome evidence, plus controlled update/
recovery before any holding-condition integration. Formal SOURCE_CHANGE and full
lexical extraction remain separate. WP-LAUNCH-001 ready, not accepted; PIT
UNSUITABLE, production NOT_READY, execution/notifications disabled.

## Optional Check And Gap State: November 23, Third Slice

The existing two-cutoff reader adds exact-boolean with_check_gap_state, default
False. It requires with_selected_capture_identity=True. The corresponding CLI
--with-check-gap-state requires --with-selected-capture-identity and explicit
--previous-as-of; dependency errors reject before storage construction. Opt-in
uses sec-source-reference-observation-v3-check-gap-state while remaining explicitly
SOURCE_REFERENCE_OBSERVATION. Single-cutoff/v1/v2 outputs remain unchanged when
the new flag is omitted; no legacy receipt is rewritten.

Each check_gap_state_material side projects only its original reconstructed
inventory: source/review versions, original selected-tag occurrence/unsupported
counts, canonical pairs, expected namespace, exact selections, basis/duration,
matching counts, check status, supported-subset numeric agreement, unresolved-tag
presence/count, raw-context status and original blocking reasons. Source counts
retain their prior meaning and are not full-filing coverage. Unresolved counts
are tag-scoped and repeated per declared side, not verified window-conflict counts
or independent votes. Absolute element positions, occurrence references, numeric
values/text, capture clocks and receipt IDs are excluded from this state axis;
the original inventories remain intact and retain those available references.

Both side materials require usable complete selected-capture identity. Missing,
failed/stale, tampered, ambiguous, future-incomplete, wrong-root, parent-invalid
or malformed projected identity remains null rather than a favorable empty state.
One observable side retains its material/hash while comparison stays NOT_EVALUATED.
Different source/review versions preserve both materials and hashes but mark
interpretation VERSION_CHANGED and comparison NOT_EVALUATED. SAME_VERSIONS is
only a mechanical compatibility label, not source or financial qualification.
The comparison reuses both original inventories and the same outer DB snapshot;
it performs no additional source lookup or caller-receipt admission.

Tests distinguish state from content: value and location changes can leave the
check/gap projection unchanged; namespace mismatch, duplicate occurrences and an
unresolved context alter it. A changed parent report date preserves the existing
AFTER_FILING_REPORT_END blocker even with identical body bytes. Initial test
expectation of unchanged state for that fixture was corrected after inspecting
the original check; no original period-admission rule was relaxed. Fault-injected
interpretation versions/malformed capture projections are boundary tests, not
real-source acceptance. Pair order, source failures, asymmetric availability,
active-writer snapshots, exact switches and CLI dependencies are also covered.

There are 48 additional synthetic cases, 193 inventory cases total. Independent
literal assertions cover total/unsupported/matching/unresolved counts, a numeric
conflict transition and the unavailable-previous/usable-current v3 case. On one fixed
synthetic fixture, frozen pre-edit versus current single-cutoff/v1/v2 canonical
JSON match exactly: 4723/12259/13017 bytes. SHA256 values respectively:
b9c9c1070ccd7544b72322ad3e78d37b456cf5a64f2b5ff1373efc5da9597f89;
15de65d87e9547cceef8aeab62ef027429586bcce36451cae885b13a44c79702;
e57627cf0e0882f673a33313fa74cf20a69e9b3c375990e87de2d9d9eaed6709.
This is fixed-vector compatibility, not universal or real-source qualification.
No real retained source/database was read or refreshed by this slice. Parsed
financial records and representation/location axes remain unimplemented; the
complete SOURCE_CHANGE comparator and accounting/fiscal/definition/method/OOS
admission stay open. H3 exclusions and seven UNKNOWN relations are unchanged;
all score/Validation/replay/holding/execution authorities remain false. A reduced
gap inventory is not financial improvement, safe holding or permission to trade.
Final related SEC/H3 suites: **423 passed**, 82.11 seconds. Full working-tree
pytest: **5103 passed / 6 skipped**, 499.93 seconds. Ruff, mypy (324 source files),
governance (189 checks), whitespace and scoped eleven-file known-pattern/privacy
checks pass. All 487 Python/config inputs retain the before/after final-suite
fingerprint:
626f3648344529ab2001f7fb5e0dcbe06fb26b2f2b9b24446134d4176e8c8500.
Read-only independent review and follow-up find no actionable scoped issue;
requested exact-count/conflict/asymmetric-v3 regression gaps are covered. Reviewers
did not execute tests/compatibility checks, inspect real raw/DB/credentials, edit
or use the network. Main verified final document counts as 48/193 after review.
This is not independent real-source, accounting or method admission.

Eleven existing code/test/doc paths change this turn, within the same 36 pending
paths. Index remains empty and HEAD remains 4774193; these checks include prior
pending work and are not isolated candidate/release verification. No schema/
dependency/default, real source refresh, scheduler/trade, commit/push or owner
action change. WP-LAUNCH-001 remains ready, not accepted; PIT UNSUITABLE,
production NOT_READY, execution/notifications disabled. Next review the remaining
parsed-record/representation scope and financial definitions independently before
using source differences as business or holding conditions.

## Optional Full Selected Capture Identity: November 23, Second Slice

The existing two-cutoff API adds exact-boolean with_selected_capture_identity,
default False. The CLI opts in with --with-selected-capture-identity and requires
--previous-as-of; otherwise it rejects before constructing storage. No flag keeps
the original single-cutoff or source-reference-v1 output. Opt-in uses version
sec-source-reference-observation-v2-capture-identity, still explicitly
SOURCE_REFERENCE_OBSERVATION, not full SOURCE_CHANGE or financial comparison.

The private reader returns the original inventory plus its original selected
capture from the same reconstructed period document; the public single-cutoff
frame discards the extra return value. Both opt-in reads share one outer DB
snapshot, without a second source lookup or accepting caller receipt JSON.
The new selected_capture_identity axis compares the complete explicit dictionary
of evidence_id, available_at and raw_data_hash. Both nullable identity materials
remain visible separately; raw_data_hash is the retained envelope identity, not
the body-byte hash or the parent envelope hash. The old ID/time reference axis
remains separate and unchanged.

Identity material requires the existing source-bound/inspected/within-limit gates,
an exactly matching selected ID/time and a lowercase 64-hex raw hash. Missing,
stale, failed, ambiguous, future-incomplete, tampered, wrong-root or parent-invalid
content cannot become unchanged identity. One observable side keeps its material
and hash while the comparison remains NOT_EVALUATED. Missing/mismatched projected
capture material stays null without a fallback. No source authentication follows
from record identity or a hash comparison; all admission/holding/trading flags
stay false and LOW/retrieval_time remains. External artifacts are not locked by
the DB snapshot; source freshness is not qualified publication freshness.

Added 42 synthetic automated cases (145 inventory tests total): full original-
factory material binding, recapture versus body change, asymmetric availability,
staleness, strict option/CLI, active-writer snapshot consistency and projected
material rejection. Existing failure and complete-parent suites now run with
both v1 and v2. A separately named private-projection fault test changes only
raw_data_hash to ensure it participates in identity comparison. This is not a
claim that a real accepted source can keep its evidence ID/time while substituting
its raw bytes; original retained-source verification remains upstream.

Frozen pre-edit module and current defaults match exactly on one synthetic
fixture at the declared cutoffs: single-cutoff JSON is 4723 bytes, SHA256
b9c9c1070ccd7544b72322ad3e78d37b456cf5a64f2b5ff1373efc5da9597f89;
default two-cutoff JSON is 12259 bytes, SHA256
15de65d87e9547cceef8aeab62ef027429586bcce36451cae885b13a44c79702.
This is one fixed-vector compatibility check, not universal old-code/source
qualification. No real retained source/database capture or refresh is performed.
Parsed records, representation/location and check/gap projections, accounting/
fiscal/definition and method/OOS review remain open; H3 exclusions and all seven
UNKNOWN relations stay unchanged.

Final related SEC/H3 suites: **375 passed**, 78.98 seconds. Full working-tree
pytest: **5055 passed / 6 skipped**, 508.65 seconds. Ruff, mypy (324 source files),
governance (189 checks), whitespace and scoped eleven-file known-pattern/privacy
checks pass. All 487 Python/config inputs retain the same final-suite fingerprint:
ef9c1fe528195d44a35caee0e17aa5e9278136b011d0d30ce7cefb28f428e396.
Read-only independent review and follow-up find no actionable scoped defect;
requested failure/parent and hash-only projection test gaps are covered. Reviewers
did not execute tests or inspect real raw/DB/credentials/network. Passing these
checks does not complete financial/source/method verification.

Eleven code/test/doc files change this turn within the existing 36 pending paths;
index remains empty and HEAD remains 4774193. These are working-tree checks,
including prior pending changes, not isolated candidate/release certification.
No schema/dependency/default, real source refresh, scheduler/trade, commit/push or
owner-action change. WP-LAUNCH-001 stays ready, not accepted; PIT UNSUITABLE,
production NOT_READY, execution/notifications disabled. Next complete the remaining
source-record projections and independently reviewed financial definitions before
using a change observation as a financial or holding condition.

## Reference Material Regression Coverage: November 23

This test-only follow-up adds 20 synthetic automated cases without changing the
runtime reader, CLI, version, schema, dependencies or defaults. Seven direct-axis
cases check canonical dictionary ordering, list order, string material and both
directions of missing material. Hash expectations use standard-library canonical
JSON independently of the runtime helper, including hashing string material as
a JSON string rather than confusing it with an already-computed source hash.

Twelve original-factory integration cases bind all four axes to exact complete
materials: unchanged input, body recapture, changed body bytes, parent recapture,
each of primary document/form/filed/report-date metadata changes, parent refresh
without a body recapture, absent body, later failure and one-microsecond staleness.
Parent recapture changes reference IDs/hash/time while unchanged filing metadata
and body bytes remain distinguishable. A parent-only update does not authorize an
old body through the new binding. Material hashes retain the observable side when
the other side is unassessed; unavailable comparison is never OBSERVED_SAME.

Read-only independent review identified one missing direction in the first 19
cases: first usable body capture between the cutoffs. The twentieth case now
asserts unavailable previous inventory, usable current inventory and, for all
three source axes, NOT_EVALUATED with null previous hash and exact current material
hash. Both original period-receipt hashes remain observable. This fills the named
prior automation gaps on selected synthetic fixtures, not every possible parent
update or source failure. Tests compare fixture artifact/evidence footprints;
they do not claim zero SQLite coordination-sidecar or filesystem metadata writes.

No real retained source/database was read or refreshed by this slice. No values,
financial-change comparator, source/accounting/method admission or holding/exit
rule is implemented. Full selected capture identity, parsed-record and location/
gap projections remain open, as do H3 exclusions and seven UNKNOWN relations.
Verification: all 20 added cases are included in 103 inventory tests; related
SEC/H3 suites pass **333 tests**, 77.11 seconds. Final full working-tree pytest:
**5013 passed / 6 skipped**, 490.90 seconds. Ruff passes, mypy passes on 324
source files, and governance passes all 189 checks. The preceding 19-case test
revision also passed the full suite (5012 passed / 6 skipped); it is not counted
as verification of the final added case. All 487 Python/config inputs retain the
same fingerprint before/after the final full suite:
e3f5a6cb9efd10dbd6c9e29e87cb4046630af5aebd4e0a1101c7a4fd781fd06b.

Read-only follow-up review finds no actionable issue in the final 20 cases and
confirms the specific between-cutoff coverage gap is addressed. Reviewers did not
run tests, inspect real raw/DB/credentials, access the network, edit or push. This
is source-only test review, not independent real-source or accounting verification.
Only this test file and four existing guidance/status documents change this
turn; all 36 pending paths remain local, index empty and HEAD unchanged. Checks
include earlier pending work, not an isolated candidate or release. No owner
action, commit/push, scheduler or trade change; execution/notifications disabled,
WP-LAUNCH-001 ready, not accepted, PIT UNSUITABLE and production NOT_READY.

## Optional Source Reference Observation: November 22

New read_sec_source_reference_changes uses the existing single-cutoff inventory
twice inside one outer read-only database snapshot. It accepts the same explicit
CIK/accession, symbol, pairs and age limit plus strictly increasing actual-UTC
cutoffs. No receipt JSON is accepted from the caller. Both inventories retain
their original factory hashes, raw-context failures, counts and all admission gaps.

The existing CLI opts in only with --previous-as-of; all other required arguments
stay explicit. Omission keeps the old single-cutoff output/version and exit-2
contract. Example: append --previous-as-of with an earlier aware timestamp to
the existing command, while --as-of remains the current cutoff. This observes
one exact filing at two cutoffs, not another accession or historical vintage
manufactured from a comparative financial column.

The new version is sec-source-reference-observation-v1; mode is explicitly
SOURCE_REFERENCE_OBSERVATION, not the complete planned SOURCE_CHANGE comparator.
Four observations are separately named:

| Observation | Exact material and limits |
| --- | --- |
| period_receipt_identity | Full existing period-input hash; may differ only because the query cutoff changed, including unavailable-state receipts |
| selected_capture_reference | Selected evidence ID plus available_at only; excludes raw_data_hash, so it is not full capture identity |
| parent_binding | Complete original source_parent_binding; differences do not prove a different parent document or business event |
| body_bytes | Exact verified source_body_sha256; a difference does not prove a changed financial amount |

Each has OBSERVED_SAME, OBSERVED_DIFFERENT or NOT_EVALUATED plus canonical material
hashes. Capture-reference/parent/body comparison requires both original inventories
source-bound, inspected and within the explicitly configured capture-age limit;
missing/failed/tampered/future-incomplete/stale inputs do not become unchanged.
Their underlying inventories remain visible. Receipt identity can still be
observed as different without claiming usable source content. Raw window-level
namespace/definition blockers remain even when source bytes match. One DB snapshot
does not lock external artifact files or make capture age a qualified freshness policy.

Full selected-capture identity, parsed-record multisets, representation/location
and check/gap-state projections are explicitly unimplemented. No values, growth,
restatement confirmation, fiscal mapping, source qualification, second official
report or holding/add/exit instruction is produced. All source/PIT/accounting/
score/Validation/replay/holding/execution authorities remain false and LOW/retrieval_time.
H3 dimensional/wrapper exclusions and seven UNKNOWN overlap relations stay intact.

Added tests cover cutoff-only receipts, recapture versus changed/whitespace body,
missing/latest-failed/tampered/ambiguous/incomplete sources, wrong roots, stale
microsecond boundary, blocked window contexts, strict UTC cutoffs/DST, read-only
stores, competing-writer snapshot consistency and opt-in/default/sanitized CLI.
Pre-edit module versus current default API gives identical 4723 canonical JSON
bytes on one synthetic fixture, SHA256
567666324bf3966e9bc64f839a995f1dc3d541ae109d50702d9d977959c20786.
This is a fixed compatibility check, not universal old-code/source qualification.
New automated cases: 29 (83 inventory tests total). Related SEC/H3 suites:
313 passed, 78.95 seconds. Full working-tree pytest: **4993 passed / 6 skipped**,
501.24 seconds. Ruff, mypy (324 files), governance (189 checks), whitespace and
scoped full-file known-pattern privacy/default/manifest checks pass. All 487
Python/config inputs retain the same before/after full-suite fingerprint:
23a1d31c4b771ab3632424acc3891a417b9877a03aa32edc7074741173c10b74.
All 36 pending paths remain local, index empty and HEAD unchanged. These checks
include earlier pending work, not isolated release or source/method qualification;
pattern screening is not full secret certification.

An offline rehearsal copies only five pinned old MSFT input files into a temporary
directory, verifying every copied input before opening the clone read-only. The
original database is never queried in this rehearsal; its five original file
hashes remain exact. At the original November 9 cutoff and one second later,
two OCF/PPE window pairs retain four requested-tag occurrences. Receipt identity
is different while capture reference, complete parent binding and body bytes are
the same. Two repetitions give observation hash
4fbdbd7f70d311e817ec488369ee8d075bd62087b645981477538a521d2225f5.
This is old-source cloned-reader compatibility, not a new capture, current
financial freshness, independent accounting qualification or H3 validation.

Authorized read-only AI static review found no actionable in-scope issue. It
did not run tests/rehearsals or inspect actual raw/database inputs, and identified
missing direct automated assertions for successful parent-binding equality/
difference and exact material hashes. Separate manual synthetic equality/difference
and canonical-hash vectors pass; these do not increase the automated case count
or close every end-to-end parent-update coverage gap. No reviewer edits, network,
real raw/database/credential access, commits or pushes occurred.
No schema/dependency/default, capture/scheduler/trading, commit or push change;
ready, not accepted; PIT UNSUITABLE, production NOT_READY, execution/notifications disabled.

Work package: WP-LAUNCH-001. Ready, not accepted. Implements only the first
read-only FINANCIAL_WINDOW_OBSERVATION inventory slice of the reviewed proposal,
not its SOURCE_CHANGE comparator, accounting admission or financial arithmetic.

## Runnable Entry

`application.sec_window_inventory.SECWindowPair` binds two exact same-tag
SECPeriodSelections to one explicitly expected US-GAAP namespace. The new
`read_sec_window_inventory` requires an existing read-only store/root, exact
CIK/accession, requested US symbol, aware cutoff and positive integer capture-age
limit. One to eight unique typed pairs share one factory read with at most sixteen
distinct selections. Caller symbol linkage remains unverified, not authenticated.

The standalone inspection CLI supports one explicit pair:

```sh
.venv/bin/python scripts/inspect_sec_windows.py \
  --database data/processed/msft-sec-20261109-xok7gp2w/snapshot.sqlite3 \
  --artifact-root data/processed/msft-sec-20261109-xok7gp2w/raw \
  --cik 0000789019 --accession 0001193125-26-436133 --symbol MSFT \
  --as-of 2026-11-09T15:13:28.573833+00:00 \
  --left NetCashProvidedByUsedInOperatingActivities=2025-07-01/2025-09-30 \
  --right NetCashProvidedByUsedInOperatingActivities=2026-07-01/2026-09-30 \
  --namespace http://fasb.org/us-gaap/2026 --max-capture-age-seconds 3600
```

This is an old retained-source example, not current financial analysis. The age
limit is illustrative, not an independently reviewed production policy. No network
or namespace download occurs; no capture flag is supported. Exit 2 always denotes
unqualified information, not readiness or trading success. The CLI sanitizes
errors and cannot initialize an absent DB/artifact root.

## Scope And Binding

The API enters one read snapshot, reconstructs through the existing
read_sec_period_research_input factory and validates exact symbol/US/cutoff,
CIK/accession and the complete selection set. Original source/body/parent and
period/research-binding hashes/versions remain visible. No caller-supplied JSON,
cached labels or rehashed assertions can replace the original factory read.

Each side exposes exact selection labels, requested basis/day counts, check
status, matching occurrence count and nonnumeric source references (contextRef,
unitRef, element index, namespace, entity, unit, exact periods). No amount values
are emitted. Source totals name their requested-tag scope and are not whole-file
or company denominators. Unresolved flags/indices are tag-level unknowns, not
proof of a competing fact in that particular selected window.

Latest source failure/ambiguity/tamper/future completion or configured capture-age
failure blocks raw context observation without old-good fallback. Uninspectable
counts remain null. A missing exact context in an inspected source has zero
matching occurrences and an explicit blocker, never a zero financial amount.
Age arithmetic compares whole seconds/microseconds exactly; offset labels and
DST folds use actual UTC. Capture age is not publication/period/filing freshness.

Both sides must be observed supported subsets, with no unresolved tag context,
all matching occurrences in the expected namespace, USD and the requested CIK.
Mixed/wrong namespaces, unsupported/conflicting matches and instant/duration
basis mismatches are retained as blockers, not filtered to a favorable occurrence.
Raw status OBSERVED_UNQUALIFIED is not economic comparability. Repeated/same-window
occurrences remain references, not extra evidence votes or independent samples.

Economic status is always NOT_ADMITTED. Source/PIT/issuer-linkage/accounting,
Financial/InvestmentScore, Validation, replay, holding/execution and official-report
authorities are always false; LOW/retrieval_time remains unchanged. Source-record
changes and fundamental assessment are NOT_ASSESSED. Fiscal/column roles, scope,
publication/revision, definition and method review gaps are explicit even when raw
contexts align. No growth, FCF, valuation, thresholds, horizon or trade instructions.

## Verification

Initial focused scope was 271 passing tests with 48 new cases. Final scope adds
six regressions for CLI/API UTC conversion overflow, wrong artifact root and a
concurrent parent update between body and parent reads. Updated counts follow below.
Final focused result: **277 passed**, 67.48 seconds, including 54 new inventory
tests and the existing SEC body/period/boundary suites.
Coverage includes exact original
factory bindings and source references, order determinism, same window, full
sixteen-selector bound, namespace/unit/context/conflict/period blockers, latest
failed/ambiguous/tampered/future-completed sources, missing/null inventory states,
microsecond age and DST, strict pairs/limits, wrong source context, active snapshot
and concurrent writer, nonempty committed WAL preservation, and offline/sanitized
CLI behavior. UTC conversion under/overflow is normalized to a sanitized error
before database access; no traceback or local-path echo. Final full and independent
review results follow after completion.

Retained MSFT rehearsal uses only the original November 9 cutoff and ten existing
selections across five tags. Two raw pairs are observed unqualified (operating
cash flow and property/plant/equipment payments); three are blocked by unresolved
tag context (net income, operating income and revenue). All five economic statuses
remain NOT_ADMITTED. Across this five-tag request, 61 source occurrences include
45 unsupported; these are not company-wide completeness counts. The observed
capture age is 87.170899 seconds at that old cutoff, not current evidence freshness.
Reversed pair order repeats exactly; the old full period receipt/hash remains
055be22569c2c37f32c262168b48ccf82234340df525f495d382c6868629bcec.
Five pinned existing DB/WAL/artifact/receipt files retain exact hashes. No network,
new capture or real DB data writes. Read-only SQLite can create empty coordination
sidecars, so no zero-filesystem-metadata claim is made.
The final metadata-scoped inventory repeats at 15947 JSON bytes with hash
e16fc1271b4008062eddb48cef2499a3aa3f64739bf2856b57fef9774a930a11.

Read-only independent AI review found the CLI UTC-overflow error issue and two
coverage gaps (wrong root and an in-factory competing parent update). The error
is normalized and those tests were added. Re-review found no further concrete
defect and suggested direct API overflow coverage; those two tests were also
added. The reviewer did not run the suites, inspect real retained data or certify
all legacy outputs; scoped review is not financial/source/production admission.

Final stable working-tree pytest: **4690 passed / 6 skipped**, 487.25 seconds.
Ruff, mypy (324 files), governance (188 checks), whitespace and scoped known-pattern
privacy/disabled-default checks pass. All 486 tracked/new Python/config inputs
retain the same before/after fingerprint:
ff7b864ec3114c00e3726741d76f5eaab2154a8e00eaa699a23f87f07d2728dc.
Twenty-six pending code/doc/config paths include twenty-two pre-existing dirty
paths; prior work is preserved, not independently certified by this slice. The
index remains empty. No private holdings, DB, original source artifacts, logs,
cache or IDE outputs were added to Git. These working-tree results are not isolated
candidate-tree checks/review required for a later sync. No commit/push this turn.

## Remaining Work

This is not the complete SECComparisonPlan: source-change equality axes, versioned
definition/reference admission, publication/revision evidence, independently
reviewed freshness policy and arithmetic/OOS methods are not implemented. Dimension
and ancestor exclusions remain intact. Existing SEC period/technical/change CLI
defaults, source normalizers, old versions, framework/schema and dependencies are
unchanged. The new entry uses only SEC_WINDOW_INVENTORY_VERSION.

Next use the explicit blocker inventory for scoped filing-definition/context
review and actual method validation; do not add scores or relax dimensions to
make a sample pass. Refresh/recovery remains separate loop work. No new owner
action is required for this increment. The previously reported GitHub SSH failure
is a separate sync issue, not a software-development gate; no sync retry here.
PIT UNSUITABLE, production NOT_READY, execution/notifications disabled. No
commit/push, broker/Paper/trading or automatic allocation change.
