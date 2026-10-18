# Replay Status Review: 2026-10-16

## Problem and result

WP-LAUNCH-001 continues the shared lifecycle-usability work at the historical
replay/ValidationRequest boundary. Previously replay retained status labels
and declared trust but did not apply the shared review. A mislabeled legacy
status with HIGH trust and favorable dataset-readiness labels could therefore
look complete. Record provenance changes also were absent from decision hashes.

Replay now preserves the original status record, review disposition/reasons,
and original-record hash in decision context. QUARANTINED and OBSERVATION_ONLY
status cannot enter formal validation. Incomplete diagnostic samples remain
visible with research and outcome objects; a bad data record is not evidence
that a research thesis was wrong.

Real ST, suspended and delisted status with structurally reviewable provenance
is not excluded simply for being adverse. Such samples retain their status
preservation warning without a missing-data penalty. This remains historical
research validation, never approval to trade an untradable security.

## Contract changes

- Replay and ReplayConfidence versions advance to `v0.6.3.2`. Query identities
  now include replay/confidence/lifecycle-review policy versions, separating
  the new interpretation from old IDs. Dataset versions pin the review policy.
- Decision context adds `status_record` and `status_review`. Full record
  content and review results enter sample hashes, including source, raw hash,
  capture/effective dates, precision, trust, dataset, instrument and batch.
- `instrument_status_review_blocked` is an explicit blocking flag for sample
  completeness and manifest/sample confidence eligibility. It is separate
  from physical missing-input counts; invalid data need not be physically absent.
- A present unusable status still blocks when a caller omits status from
  required_inputs. This prevents hiding a known bad record, without pretending
  the transitive dataset dependency registry has been implemented.
- ValidationRequestFactory independently checks current model/review versions,
  required status presence, disposition, reasons, record hash, decision time,
  symbol/market/category identity and status/tradability/trust summary binding.
  Removing flags alone cannot clear an invalid status. Old results require
  explicit reconstruction, not silent recertification.

Hashes here bind supplied metadata, not external issuer truth. Reviewable data
still needs independent source, artifact, continuity and readiness evidence.
The factory is not a cryptographic signer or defense against a caller forging
an entirely new internally consistent result and readiness declarations.

## Snapshot and transaction changes

All replay reconstruction reads now share one SQLite read snapshot, including
subjects, readiness, status, fundamentals, screening, reports and outcomes.
The read snapshot closes before optional persistence. Manifest and sample
writes then share one transaction; a sample-write failure rolls back the whole
result rather than leaving a stranded manifest. A timezone-aware generation
clock is required and cannot precede outcome_as_of.

No schema/migration change is needed: added metadata fits existing JSON
contracts. Existing stored records and reports are not rewritten. Two older
storage debts remain: the low-level replay writers still use replacement
semantics, and manifest IDs are query/version based rather than fully
content-addressed across later input snapshots. Versioned identities prevent
this new policy colliding with old policy IDs, not every future overwrite.
See TD-038; strict immutability needs a separate bounded repair.

## Verification

Regression cases cover invalid legacy/changed-source status, bad raw hashes,
unknown/retrieval-time precision, weak trust, favorable dataset labels,
omitted required inputs, adverse-status preservation, removed review/flags,
changed record/source/time/version/reasons/instrument, old manifest versions,
future status versions, timezone errors, concurrent writes and atomic rollback.
Synthetic baseline status hashes were corrected to valid hex for meaningful
positive-control tests; this is not a change to real data quality assumptions.

Final verification: **670 passed, 6 skipped**; Ruff passes; mypy passes for
214 source/script files; all 69 governance checks pass; tracked/new-file
whitespace checks pass. No ignored local artifacts or frozen
execution/paper/broker/portfolio/notification module changes are included.
The operational database remains a research sample, with zero ResearchReport,
ValidationReport, PortfolioProposal and replay report/sample rows. The read-only
audit passed at `2026-10-16T07:45:08.123354Z` (15:45 Malaysia), unchanged content
audit hash `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
No real profitable strategy or trading readiness is demonstrated by unit tests.

## Boundaries and next work

Framework/schema stay `0.8.0`/`0.8.2`; execution/notifications remain disabled,
PIT UNSUITABLE and production NOT_READY. No broker, order, live, Paper Trading,
Portfolio or Notification logic is added. No new provider/network capture occurs.
All seven continuation slices remain uncommitted/unpushed in the PyCharm
source-of-truth directory. Ignored databases/cache/artifacts are not Git backups.

Remaining high-priority issues include replay content immutability (TD-038),
exact outcome-session coverage and price/corporate-action provenance (TD-039),
complete lifecycle/phase/calendar/action evidence, reviewed policy and account
inputs, and exact future simulation binding. The shared reviewer does not yet
audit every historical calibration report or all preserved lifecycle events
inside replay. See the [deployment gap plan](deployment-gap-plan-2026-10-16.md).
