# Lifecycle Usability Review: 2026-10-16

## Deployment-oriented scope

This WP-LAUNCH-001 continuation prevents old status/resumption defects from
silently becoming stronger historical coverage or runtime clearance. It adds
no broker adapter, order path, paper ledger or live execution. Framework/schema
remain `0.8.0`/`0.8.2`, PIT `UNSUITABLE`, production `NOT_READY`, execution and
notifications disabled. Controlled-launch engineering continues in parallel
with historical evidence accumulation; neither is automatically promoted.

## Shared contract

`data.lifecycle_review.review_lifecycle_record` reviews original
SecurityLifecycleEvent or InstrumentStatus records at an explicit aware as-of
time and effective-date cutoff. Output includes a deterministic original-record
hash, disposition, reason codes and policy version `lifecycle-review-v1`.

- **QUARANTINED**: logically ineligible at this boundary, not deleted. Known
  delisted-quote status misrouting, unsupported AKShare resumption, old
  suspension normalization, future availability/effective date, expired status
  interval, missing source or malformed raw hash remain explicit reasons.
- **OBSERVATION_ONLY**: weak, partial, retrieval-time or imprecise evidence is
  retained; it cannot clear a stock's status or prove historical continuity.
- **REVIEWABLE**: basic structural checks passed. This is not independent
  source verification, artifact authentication, complete lifecycle coverage,
  PIT-readiness approval or authorization to trade.

No provider inherits trust by name. Even a VERIFIED label or a forged new
normalization tag cannot clear an AKShare forecast-derived resumption. ST,
suspension and delisting facts are not quarantined merely because they are
adverse. Existing inclusive security-status end-date semantics are preserved;
this change does not migrate interval contracts.

The original-record hash identifies the supplied record including metadata.
It is not the raw-source hash and does not prove original bytes exist or match.
Source-byte verification and independent provider/issuer review remain separate.

## Consumers and coverage repair

```text
raw MarketDataService preservation reads
  -> shared lifecycle record review
     -> runtime v1.6 (originals + review results + gap codes)
     -> HistoricalCoverageEvaluator.security_timeline
```

Runtime v1.6 includes status and per-event reviews in its content hash, while
retaining the original records and source evidence. Quarantine adds a clear
gap rather than fabricating a normal status or deleting an inconvenient sample.

Lifecycle coverage now excludes logically quarantined, out-of-period or
wrong-instrument records from event types, temporal precision and source
diversity. It preserves exclusion counts and reason codes as warnings. If
any input is excluded, the score is capped below the CAUTION threshold (49)
and classification remains UNSUITABLE; empty history scores zero. Invalid
periods, empty expected-event sets, invalid provider counts and negative
contradiction counts reject evaluation rather than creating a favorable
denominator. All score components remain percentages in [0,100], including
`in_scope_nonquarantined_pct`, even for large quarantined sets.

Lifecycle trust is the weakest retained record, not an average that can hide
a LOW observation among HIGH records. Coverage model version is now
`historical-coverage-v0.8-lifecycle-review`; previous persisted assessments are
not rewritten or recertified. Universe/publication scoring behavior is not
refactored in this slice, though the shared model version advances.

This is a coverage heuristic, not a measurement of every day/event in the
market. Admitted records and a high component score do not prove full
continuity or satisfy the separate replay/readiness governance gates.

## Local securities software boundary

The user authorized optional read-only inspection of local MooMoo and Guojin
software as supplementary evidence. App inventory showed `moomoo` and
`全能行`. The MooMoo UI request timed out and returned no page contents.
No current quote, login state, account tier, export feature, read-only API or
trading entitlement was verified. Guojin pages were not inspected. No order,
account operation, permission expansion or broker connection was attempted.

When UI reading is available, limit inspection to market/security information
and export capabilities. Do not copy account identifiers, balances, passwords,
tokens or screenshots of sensitive account panels into Git or public reports.
Do not unlock trading, buy data subscriptions, accept new terms or enable API
permissions without the necessary user action/approval.

A screen observation should record instrument/exchange, displayed field,
market timestamp, capture timestamp, timezone, delayed/realtime label if
visible, adjustment basis and provenance limitations. Unknown fields remain
unknown. Manual observations are supplementary retrieval-time evidence, not a
historical feed, provider-independent calibration baseline or assumed high
trust. GUI interaction must never become the unattended execution transport.
Any future supported data API needs separately reviewed capabilities, scope,
credentials, usage terms and audit boundaries; this slice implements none.

## Real read and database impact

The existing local reported-start observation for diagnostic identifier
`600293` was read at fixed as-of `2026-10-16T06:00:00Z`. It yields one
OBSERVATION_ONLY review, no status clearance, and the reasons
`partial_suspension_observation`, `retrieval_time_not_original_publication`,
and `trust_insufficient_for_historical_clearance`. The CLI correctly exits 2.

- Original-record hash:
  `07083742e2e921410ea76a3c0927828237ed05733cc71052d748bcee4dae8fb2`.
- Runtime input hash:
  `ac3362db76d806415701c24865b871693867f6932640f6b0e48b55cbb9acf43b`.
- No database writes, migrations or new source captures in this continuation.
  The existing 13 lifecycle observations and all original labels remain.
- Read-only database audit passed at `2026-10-16T06:10:50.033878Z`; its unchanged
  content audit hash is
  `fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.

## Verification and remaining work

Regression tests cover legacy/falsely relabeled resumptions, raw-hash/source
defects, future visibility, forecast preservation, weak/unknown trust,
deterministic record hashes, inclusive interval ends, adverse-status
preservation, empty history, invalid denominators, mixed trust, wrong-security
and out-of-period input, and large quarantine sets. Existing integration
tests verify review results alongside preserved events/statuses. That slice
finished with 646 passed / 6 skipped; Ruff, mypy (214 source/script files),
67 governance checks, database integrity and diff/whitespace checks passed.

The [subsequent replay boundary repair](replay-status-review-2026-10-16.md)
extends status review into replay and ValidationRequest creation. Lifecycle
events and old calibration reports still need further adoption/provenance work.

Adoption is not universal: raw service/repository reads still preserve
originals; historical calibration reports and replay inputs need explicit
eligibility/provenance review at their boundaries. This helper cannot recover
lost source truth. Remaining deployment prerequisites include authoritative
ST/listing-phase/resumption and exceptional-calendar/action coverage,
account/settlement evidence, reviewed policy hashes, realistic intraday/cost
constraints and exact simulation-input binding. Only after WP-LAUNCH-001
acceptance should the deterministic paper-ledger package become ready.

Code remains in the local PyCharm source-of-truth project; this and the prior
five continuation slices are uncommitted/unpushed. Git does not back up ignored
business databases, cache or raw artifacts. No user credential is required to
complete this software-hardening slice.
