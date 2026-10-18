# Replay Outcome and Persistence Integrity: 2026-10-16

## Delivery

This WP-LAUNCH-001 slice repairs two concrete obstacles to reproducible
research validation: moving observation windows and replacement replay writes.
It does not implement a strategy, trading simulation, broker or live execution.

## Exact observation contract

`replay-outcome-v1` defines `close_return_pct` as an unadjusted price-only
observation, excluding distributions, corporate-action adjustments and costs.
It must not be interpreted as total investment return, a fill or a P&L result.

- Start is the UTC date of decision_as_of. Target observation time is
  decision_as_of in UTC plus observation_horizon_days calendar days.
- Both exact endpoint dates are required. There is no previous/next session
  substitution, first/last available-bar fallback or zero-return shortcut.
  A weekend or missing bar remains an incomplete diagnostic sample; this
  contract does not claim to resolve exchange sessions or exceptional closures.
- Start bars are read using decision_as_of, never the later outcome cutoff.
  Revisions published after the decision cannot replace the starting price.
- Target bars are read using outcome_as_of and must describe the exact target
  date, with observation timestamp no later than the target clock.
- The query must reach target observation time plus availability_lag_days.
  Waiting longer does not extend the price window. Outcome availability is
  conservatively recorded at the query cutoff, not backdated to the target.
- Unsupported metrics/benchmarks, adjusted prices, nonpositive/nonfinite
  prices, missing sources and wrong instruments cannot produce a usable value.
  Duplicate symbols/outcome identifiers are rejected before reconstruction.
- Context retains the definition, expected dates/times, price basis, blocking
  reasons and exact economic-row/source/availability contents and hashes.
  A hash establishes content identity, not independent provider verification.
- `outcome_review_blocked` independently blocks sample and manifest eligibility,
  including when callers omit outcome from required_inputs. Invalid samples
  remain visible and are persisted for diagnosis.
- ValidationRequestFactory reconstructs and recomputes the bound outcome;
  clearing flags or changing confidence labels cannot authorize a bad window.

Replay and confidence advance to `v0.6.3.3`; dataset versions pin the outcome
contract. Earlier replays require explicit reconstruction. The synthetic test
fixture's Jan 15 to Feb 15 interval was corrected from 30 to 31 calendar days;
no real data or readiness conclusion was upgraded by that correction.

## Immutable publication

Manifest identity now hashes the versioned query, ordered sample content
hashes, dataset/readiness versions and hashes, limitations, confidence and
generation time. Sample persistence identities are namespaced by manifest
identity and sample content hash; nested ValidationSample ids match them.

An exact retry with the same generation time and inputs is idempotent. A later
generation has its own manifest/sample ownership, while unchanged sample
content retains the same replay_hash. Changed inputs at the same generation
time also produce a distinct manifest. Generation time is audit metadata, not
part of the economic sample hash or evidence that more history exists.

SQLite writers use insert-if-absent plus full material-column comparison,
excluding ingestion time. Conflicting reuse raises an error; it cannot replace
or move old samples. Sample writes require an existing manifest whose input
map binds that sample id to its replay hash. Repository-level publication owns
one transaction, including for direct callers; failures roll back the entire
new publication. Reconstruction retains its separate single read snapshot.

Schema remains `0.8.2`, migration head `0010_portfolio_evidence_lineage`, 64
noninternal tables. Existing JSON and primary-key contracts suffice. No schema
rewrite, migration, legacy deletion or silent historical recertification occurs.
Legacy replacements already performed cannot be recovered by this repair.

## Verification

- Full suite: **699 passed, 6 skipped**, including 29 additional regression cases.
- Ruff: pass. Mypy: pass for **215** source/script files.
- Governance: **70 checks pass** after registering this report.
- Tracked and new-file whitespace checks: pass.
- No changes to execution, paper, broker, portfolio or notification modules;
  execution and notifications remain disabled. No network/provider capture.
- Read-only operational database audit passed at
  `2026-10-16T14:53:33.637039+00:00`; content audit hash remains
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.

The local sample still has zero fundamental facts, status-history records,
universe memberships, ResearchReports, ValidationReports, PortfolioProposals,
replay manifests and replay samples. Thirteen suspension-start observations
are not complete status timelines. Unit-test fixtures are not operational data.

## Residual risks and next work

TD-038's new-publication overwrite/ownership defect is repaired. TD-039 is only
partly resolved: exact UTC calendar endpoints and content/availability binding
now exist, but exchange-session-aware outcomes, authenticated raw artifacts,
independent price review, complete corporate actions and total-return/cost
semantics remain open. Price-source trust is not inferred from source names or
from a favorable dataset-level label. Readiness dependency declarations remain
caller-owned and need independent review.

Sample hashes still reference research reports by id rather than binding all
research/evidence content. Correction after inspection: report-header writes
already reject duplicate ids; child evidence was replaceable and module
assessments appendable. The subsequent research-binding slice repairs content
identity and child evidence persistence, while exact original-input/source
lineage remains open as TD-040. Immutability
of these new replay rows is not a claim that every upstream artifact is immutable.

Next: bind full research inputs, inventory a narrowly scoped real SSE pilot
bundle with explicit gaps, review policy/configuration hashes, and establish
one real reproducible research/validation chain. Paper ledger development
keeps its approved package gates; the evidence horizon runs in parallel.
PIT remains UNSUITABLE and production NOT_READY. No commit or push is performed.
