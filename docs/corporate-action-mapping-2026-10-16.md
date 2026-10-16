# Corporate-Action Mapping: 2026-10-16

Package: `WP-LAUNCH-001`, still partial. Normalization contract:
`akshare-corporate-action-v1`. Framework `0.8.0`, schema `0.8.2`, migration
`0010_portfolio_evidence_lineage` and execution/notification defaults unchanged.

## Evidence and scope

The [official AKShare schema](https://akshare.akfamily.xyz/data/stock/stock.html)
lists composite cash/share-distribution fields and a distribution description,
but does not itself define reliable units for all numeric ratios. The actual
26-row payload includes explicit per-basis descriptions, implemented labels,
and separate ex-dates/registration dates. The new parser requires corroboration
between those descriptions and the corresponding numeric components.

An [issuer proposal on CNInfo](https://static.cninfo.com.cn/finalpage/2026-03-31/1225062338.PDF)
independently states CNY 4.20 per ten shares equals gross CNY 0.42 per share.
It also explicitly requires later approval and an implementation notice.
It verifies this example's unit convention, NOT an implementation date or all
historical rows. The implementation PDF fetch was unavailable during review;
provider-labelled implementation is therefore not independent verification.

No provider or dataset is upgraded. New events remain LOW trust and
RETRIEVAL_TIME availability. There is no adjustment-factor construction,
price adjustment, holdings mutation, ledger, broker or trading instruction.

## Canonical interpretation

- Gross cash is CNY per **old share**, excluding account-specific tax effects.
  A matching gross marker and corroborating numeric cash component are required.
- SPLIT ratio is **total new shares per old share**. For ten old shares plus
  five bonus/converted shares it is 1.5, not 5 or 0.5. This is a data convention,
  not an operation applied to holdings. Bonus and conversion components must
  agree with the total and textual description when present.
- Zero and missing remain distinct; no zero-valued event is manufactured.
  Only corroborated positive components are emitted. Missing components do not
  establish a zero balance, no distribution or complete action coverage.
- The bounded description grammar accepts explicit bases 1/10/100/1000,
  cash/bonus/conversion terms and supported gross-tax annotations. Unknown
  syntax, duplicate terms, contradictory net/gross amounts, rights issues and
  unsupported numeric/unit values are rejected rather than inferred.
- Only an explicit provider label `实施分配` and a non-future explicit ex-date
  can produce events. Board/shareholder proposals and unknown labels remain
  row-level rejections. Registration dates never substitute for ex-dates.
- Duplicate/conflicting same-date/type rows within one payload are all
  rejected; their distinct scheme identity cannot be proved by this schema.
  Multiple legitimate same-date schemes need a future explicit identity.

The instrument must be a PIT-visible China A-share CNY equity. A future
instrument snapshot cannot enter normalization. Every event keeps the raw
payload hash, batch, source, dataset, trust and availability precision.

## Contracts and persistence

The new `data.normalization.corporate_actions` batch API returns actions,
accepted source-row count, received count and explicit row-index/reason issues.
Row indices are zero-based payload ordinals. The legacy list API delegates to
this parser; ingestion uses the batch API so rejected rows are not hidden.
Old alias-only payloads without explicit basis/status are no longer guessed.
They are not automatically relabeled with the new units.

IngestionResult counts **source rows**, not derived events. One accepted row
can create a cash and share event without a negative rejected-row count.
Normalized-event and actually inserted-event counts are separate audit
warnings. Row issues, summary, batch, fingerprint and domain writes commit
together; injected warning failure rolls the entire write back.

The CLI returns `partial`/exit 2 for zero or partial acceptance. Empty provider
responses are auditable but cannot prove no-action coverage. Raw SDK output
and credentials are not rendered. Existing timeout isolation remains active.

Corporate-action writes are idempotent at the existing PIT key. Same-key
amount/unit-relevant metadata conflicts now raise and roll back instead of
being silently ignored. Corrections require a new available_at version;
distinct raw observations remain visible. No schema/table/migration change
was necessary. No old row was rewritten. Legacy rows with ambiguous cash or
ratio units require separate audit before canonical use.

## Real verification

Two fresh observations each mapped 26 source rows to 33 events: 26 dividends
and seven share distributions. The second capture was saved to cache;
replaying that exact cached snapshot normalized 33 events but inserted
**zero** new event rows.

The business database now holds 66 observations for 33 distinct date/type
keys, not 66 independent actions. First capture:
`2026-10-16T02:06:38.639211+00:00`; second:
`2026-10-16T02:07:39.421405+00:00`. All observations retain LOW/RETRIEVAL_TIME.
An actual read immediately before the first capture returned zero events.
Read-side history is not a deduplicated adjustment series; never compound all
versions as if they were separate splits or dividends.

After the cached replay, the read-only audit passed: 66 action observations,
12 bar versions, 8,797 calendar rows, five instrument versions, ten batches,
six raw fingerprints and 15 warnings. Integrity is OK, no FK violations,
checksums valid, and physical schema fingerprint remains
`69ceb0931c99cf63ec353399877c4cffcd588c9b77cf8f719ec90f45c66fa517`.
Data/cache files and SQLite sidecars remain local and ignored by Git.

Verification: 483 tests passed, 6 optional network tests skipped; Ruff, mypy
(207 source/script files), governance and diff checks passed. Tests cover
unit corroboration, net/gross distinction, dates/statuses, zero/missing values,
unsupported/duplicate/conflicting rows, PIT reads, idempotence, corrections,
atomic rollback and partial CLI semantics. Tests do not establish data trust.

## Next bounded work

1. Bind exchange-calendar and security-status evidence to real source hashes,
   trust and availability through existing provider-neutral contracts.
2. Establish listing-phase evidence and corporate-action **coverage**, not
   merely positive historical events. Preserve ST/suspension/delisting records.
3. Add approved account-lot provenance and remaining intraday/cost/policy
   checks before the simulation boundary. Do not infer settled holdings.

PIT remains UNSUITABLE; live execution stays disabled. The seven runtime
evidence requirements are not closed by this mapping fix. This does not
complete WP-LAUNCH-001 or make WP-PAPER-001 ready.
