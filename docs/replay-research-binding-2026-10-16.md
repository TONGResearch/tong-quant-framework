# Replay Research Content Binding: 2026-10-16

## Scope and result

WP-LAUNCH-001 now binds reconstructed research content, not only report ids,
to historical replay identity. Replay/ReplayConfidence advance to `v0.6.3.4`;
`replay-research-binding-v1` is centrally versioned and pinned in query and
manifest dataset versions. Older results require explicit reconstruction.

No strategy, Paper Trading, broker, execution, Portfolio or Notification
behavior is added. Framework/schema remain `0.8.0`/`0.8.2`. Execution and
notifications remain disabled, PIT UNSUITABLE and production NOT_READY.

## Contract

- Decision context stores a canonical ResearchReport snapshot and content hash,
  including thesis/counter thesis, invalidation conditions, confidence/method,
  module scores/features/versions, findings/risks/limitations, evidence content,
  source references, input hashes, metadata, policy research and market regime.
- The visible fundamental and screening rows are separately retained and
  hashed, including values, revisions, source/time/trust fields and original
  stored JSON. Ingestion bookkeeping and SQL version-rank columns are excluded.
  Equal row counts cannot hide changed economic content.
- These are reconstructed decision-visible input inventories, NOT proof that
  the original research run actually consumed precisely those rows. Complete
  original request/context lineage remains a separate unresolved requirement.
- Changes to report/evidence or visible input content change sample and
  manifest identity, even when report id and generation time are unchanged.
  Earlier immutable replay rows retain their own research snapshot. Future
  input revisions remain excluded by decision-time reads.
- Missing/duplicate evidence references, conflicting evidence ids, duplicate
  module assessments, late assessment/evidence times, wrong instrument and
  future regime/report clocks block research reconstruction eligibility.
- Rejected report content is not placed into usable decision inputs or a
  ValidationSample. A rejected-content hash and reason codes remain diagnostic;
  originals remain in their source tables. Incomplete samples are persisted.
- Policy reconstruction retains embedded evidence and hydrates referenced
  run evidence. Conflicting embedded/run versions remain visible to the review,
  rather than one silently winning. Malformed policy payloads raise an explicit
  error instead of silently becoming "no policy assessment".
- ValidationRequest creation rechecks snapshots, derived factor scores,
  expected-success labels, regime state, evidence references, visible-input
  hashes/counts, sample/query cutoffs, complete sample content hashes and the
  manifest sample map. Clearing flags, editing only scores, or changing both
  report and local snapshot cannot bypass the unchanged replay content hash.
  A substituted instrument or unbound journal/portfolio-position side channel
  cannot enter the generated validation sample.
- Market regime is still a research variable, never a Bull/Bear approval switch.

## Source persistence correction

The previous TD-040 narrative was too broad: the current ResearchReport writer
already uses INSERT with a primary key and rejects a duplicate report id.
The actual mutable child path was research_evidence INSERT OR REPLACE, and
module assessments could be appended repeatedly under one report.

Evidence writes now use insert-if-absent plus material-column comparison.
Exact retries are idempotent; changed content under the same run/evidence id
raises an error and requires a new identity. Research publication's existing
transaction protects the full run. No old evidence is rewritten or deleted.
Duplicate module assessments are rejected at replay review; no guessed winner
is selected. Upstream global uniqueness/schema redesign is not part of this slice.

Report-mutation tests use deliberate SQL edits only in isolated fixture
databases, representing legacy/manual corruption, not an allowed report API.
New replay rows cannot recover source content lost before their publication.

## Verification

- Full suite: **744 passed, 6 skipped**, 45 additional regression cases.
- Ruff passes; mypy passes for **216** source/script files.
- Governance: **71 checks pass** after registering this report.
- Tracked and new-file whitespace checks pass. No local database/cache/artifact
  paths or credential-pattern findings in changed/new files.
- No frozen execution/paper/broker/portfolio/notification module changes.
- Read-only operational audit passed at `2026-10-16T15:04:44.646899+00:00`.
  Content audit hash remains
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
  Schema fingerprint remains
  `69ceb0931c99cf63ec353399877c4cffcd588c9b77cf8f719ec90f45c66fa517`.

Schema has 64 noninternal tables; no migration is required. The operational
sample still has zero research/validation reports, fundamental facts,
status-history rows and universe memberships. Tests do not populate real
strategy evidence. No network capture, commit or push is performed.

## Remaining gates and concrete continuation

TD-040's report/evidence-content identity defect is repaired for new replays;
full transitive provenance is not complete. Input hashes are declarations,
not authenticated provider bytes or proof of original model calculations.
Entirely self-consistent forged results are not prevented by local hashes;
independent source, version/configuration, coverage and governance review
remain mandatory. Some structurally malformed records still abort explicitly
rather than producing typed quarantine diagnostics.

Next bounded delivery is a real pilot input-coverage manifest, not another
unbounded architecture expansion. Inventory the existing SSE scope, date
windows, statuses/phases, calendar, price/actions, publications and policy
versions with precise blockers; never fill them from fixtures. Use that
manifest to prepare one actual research/validation chain when eligible inputs
exist. Freeze one reviewed strategy specification rather than implementing all
technical families at once. Paper ledger/cost/reconciliation development then
follows the existing package acceptance gates. Evidence accumulation continues
in parallel; no elapsed observation period automatically enables live trading.
