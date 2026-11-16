# Provider Ingestion UTC Integrity: October 25

WP-LAUNCH-001 remains `ready`, not accepted. This slice hardens the existing
provider-neutral evidence boundary. It introduces no provider transport, source
trust promotion, canonical data population, trading functionality or migration.

## Reproduced Defect

The research-side UTC repair did not cover provider ingestion. A synthetic
America/New_York cutoff of November 1, 2026 01:30 fold=0 is 05:30 UTC. Evidence
available at 01:30 fold=1 is 06:30 UTC, one actual hour later. Strict neutral
batch validation accepted that future evidence under the original comparison.

The old provider contract constructors also compared local wall-clock labels.
They could accept reversed actual chronology, bind a child to the wrong batch
retrieval instant, or reject an equivalent UTC representation of the same folded
instant. A later actual completion with an earlier wall-clock label could fail,
while an earlier actual completion with the same label could pass. The boundary
did not revalidate an already constructed batch/children returned by an adapter.

These defects were reproduced with synthetic records, not observed investment
outcomes or evidence that the current real dataset contains such corruption.

## Implemented Boundary

1. ProviderEvidenceRecord checks available/retrieved, published/available and
   observed/retrieved ordering using actual UTC instants. Artifact and artifact
   observation publication/retrieval checks do the same.
2. ProviderEvidenceBatch rechecks each child's existing constructor invariants,
   then compares retrieval binding in UTC. Provider/dataset/market/raw-hash and
   captured-artifact reference checks remain intact. Equivalent actual instants
   are accepted; distinct folded instants cannot masquerade as one capture.
3. ProviderNeutralIngestionService rechecks the request before fetching, then
   rechecks the returned batch and child contracts before publishing files,
   database rows or the canonical-write callback. Existing strict PIT event,
   availability and publication limits use UTC.
4. Completion must be timezone-aware and no earlier than retrieval in UTC,
   before raw-artifact publication. IngestionBatch constructor chronology uses
   the same actual-instant comparison.
5. Relaxed PIT retains its existing explicit behavior, but cannot disable contract
   chronology, batch binding, trust ceilings or file/database safety checks.

This repair does not redefine claimed historical publication availability as
first retrieval. Existing strict-mode behavior still distinguishes retrieval
chronology from event/publication/availability cutoffs. A historical metadata
claim remains unqualified without independent provenance; valid UTC ordering
does not authenticate it or make later numeric revisions historically visible.

## Identity And Compatibility

The runtime marker is centralized as PROVIDER_INGESTION_TIMING_VERSION =
`provider-ingestion-utc-v1`, exposed by the ingestion service. It is not a
retroactive persisted acceptance stamp on older batches. Provider evidence and
artifact identity helpers, serialization, source packet versions and the existing
PROVIDER_EVIDENCE_VERSION remain unchanged; no historical ids/hashes are rewritten.

Framework 0.8.0, database schema 0.8.2 and migration head
0010_portfolio_evidence_lineage remain unchanged. Public Provider interfaces and
Tushare transport implementation stay unchanged. Invalid legacy records must be
retained and separately reviewed, not silently requalified, modified or deleted.

## Read-Only Real Check

The existing `data/processed/technical-request-20261020.sqlite3` was inspected in
one read snapshot. Checks parsed explicit timezone-aware timestamps and compared
actual UTC order, with artifact registry `first_retrieved_at` treated as first
capture, not an invented `retrieved_at` column.

| Inventory | Rows | Invalid checked UTC chronology |
| --- | ---: | ---: |
| Provider evidence records | 3392 | 0 |
| Registered provider artifacts | 17 | 0 |
| Artifact observations | 8 | 0 |
| Ingestion batches | 19 | 0 |

No incomplete batches were found in this scoped inventory. This checks record
chronology only, not all batch/content relationships, original timestamp truth,
canonical tables, other databases, historical coverage or research eligibility.
The first ad-hoc audit attempts used a string instead of the required Path and
then an incorrect registry column; both failed read-only without database
changes. The final schema-aware check above completed successfully.

The separate registered-byte audit still verifies 17/17 files, report hash:

```text
a5812a28885b03ed1ccd072465684a82cc44d757cb5bd809ff8c7dc55f0c5425
```

No new network request or provider capture was made. The retained 002624
HTTP_502 quote failure remains unresolved; passing a stored-byte audit does not
recover quotes or establish source authenticity, encryption or backup coverage.

## Verification

Thirty-two added cases cover five strict future-input paths with folded and UTC
cutoffs, five constructor chronology paths, three child/batch binding paths and
their positive timezone-equivalence controls, adapter-return mutation, completion
chronology, relaxed PIT safety and request rejection before fetch. File/database
publication and canonical callback suppression are asserted on rejected inputs.
The original 30-case reproduction had 24 failures and 6 passing controls.

An additional fixture initially used local datetime addition after a folded
instant, which reset fold and did not represent a future instant. It was corrected
to advance in UTC rather than weakening the production guard. The focused
ingestion/evidence/trust suite then passes 89 cases in 3.06 seconds. Final full
suite: **1828 passed, 6 skipped in 60.33 seconds**. Ruff passes; mypy passes for
251 source files; governance passes 109 checks; `git diff --check` passes. Six
opt-in real provider/notification network checks stay disabled. Offline fixture
success is not live access, source accuracy or investment-performance validation.

## Remaining Work

This is not a repository-wide temporal certification. Domain market-data models,
screening, regime metric/run construction, other adapters and storage consumers
still require separately scoped UTC/DST and report/session-date review. Preserve
legacy evidence and investigate conflicts rather than backdating/relabeling it.
Complete permitted dated quote sourcing, independent units/share-class/clock/
action review, sector valuation admission and real technical-plus-fundamental
strategy validation. Provider/PIT horizon evidence continues independently.

PIT remains UNSUITABLE, production NOT_READY, execution/notifications disabled.
No Paper, broker, live orders, Portfolio, allocation or notification development
is introduced. No commit or push; no operator action is required by this repair.
