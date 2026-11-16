# Independent Review Hardening: November 16

Work package: WP-LAUNCH-001. Status: ready, not accepted. This is an engineering
repair, not source qualification, strategy validation or trading authorization.

## Findings And Repairs

Two owner-authorized read-only AI reviewers examined the full pending remote
6be0a842d997b7707b0d347b3206e6e003aac7fb to candidate tree
c4f831669dbf12791571ff4e1f3111457f0ca08f range, including unpublished history.
The review was risk-focused, not an exhaustive line-by-line audit of 397 paths.
It identified four sync blockers despite the old candidate's passing tests:

- Provider ingestion published artifacts before repository credential checks.
  The new preflight checks batch metadata, records, limitations, artifact and
  observation metadata before any artifact put or ingestion SQL write. JSON
  bodies are inspected before duplicate keys discard earlier values; UTF-8 BOMs
  are removed only from the inspection view, never retained bytes/hashes. Re-review
  caught the text/plain BOM bypass and added object/array/duplicate-key regressions
  plus a clean-byte-preservation control. Supported
  UTF-8 text is screened for known credential assignment forms. Malformed JSON,
  unsupported text encoding and recursion failure reject retention with a generic
  error that excludes source values and fragments. Repository checks remain active.
- Lifecycle record and instrument availability compared repeated DST wall times.
  Both now compare UTC instants. Quarantined events remain preserved but cannot
  improve historical security coverage.
- Research fundamental period admission used the caller's local date. The
  boundary now uses the UTC cutoff date consistently, not an inferred market
  calendar. Equivalent timezone representations cannot change admission.
- Replay's nested research verifier used native datetime comparisons. Report,
  regime, assessment and evidence visibility now compare UTC instants; a naive
  decision cutoff is rejected. Rejected reports retain identity/blocking reasons
  without becoming usable decision content.

Rollback still never deletes published shared bytes. Privacy rejection is not
an excuse to restore unsafe creator-only deletion. This preflight does not
delete or certify earlier orphan files and does not inspect private originals.

## Limits And Follow-Up

Known-field/pattern screening is not universal secret detection. Opaque binary
PDFs, compressed streams, arbitrary encodings or credentials hidden under unknown
names are not certified credential-free. Public-source transport restrictions,
separate credential handling, access controls and independent retention review
remain necessary. This repair does not qualify an arbitrary producer as trusted.

The review also identified nonblocking follow-up work: direct daily technical
rendering needs a separately versioned instrument/cutoff/source-bar receipt;
replay outcome endpoints need an explicit suspended-price interpretation rather
than silently treating carried closes as executable returns; affected retained
source producers should reject unsupported clock representations before writes.
The last is a documented identity-compatibility limitation, not permission to
rewrite old evidence IDs. These items are not fixed by this slice and remain
required before relevant consumers are promoted. No validated hold/add/sell or
holding-horizon conclusion follows from existing diagnostic output.

## Versions And Validation

Privacy preflight has its own version. Lifecycle review/coverage, replay research
binding and both prospective research report variants have new versions for
changed admission semantics. Stored historical identities are not rewritten.
No schema or dependency change is required. The 44 added regressions cover early
privacy rejection with artifacts, DST folds, timezone-equivalent cutoffs and UTC
period dates. The five focused test files pass 527 tests and research integration
passes 127. The test-only legacy-version projection preserves the old field-content
golden hash while asserting the prospective report version; production output and
stored report identities are not projected or rewritten. Full isolated candidate
checks and independent re-review are required before sync. Do not reuse the
old candidate's 4121-test pass as qualification of this repaired tree.

PIT stays UNSUITABLE; production stays NOT_READY. Execution and notifications
remain disabled. No broker, order, Paper, portfolio, live or allocation behavior
is added. Code sync does not back up private databases or original evidence.

## Automation Update

At Tong's request, the existing conversation-bound engineering heartbeat was
updated through the app tool to every three hours: 00:00, 03:00, 06:00, 09:00,
12:00, 15:00, 18:00 and 21:00 Malaysia time, daily including weekends. Readback
confirmed ACTIVE with identical task name, prompt and conversation binding.
No duplicate task was created; GitHub sync scheduling was not changed. Earlier
November 3 notes describe the former 02:00/03:00/04:00 engineering schedule.
Local-file runs still require an available computer/app and do not bypass
permissions, independent review, data gates or live-trading approval.
