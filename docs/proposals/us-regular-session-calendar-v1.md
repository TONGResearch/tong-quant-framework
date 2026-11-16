# US Regular-Session Calendar Contract V1

Date: 2026-11-07, Asia/Kuala_Lumpur. WP-LAUNCH-001 design/source-audit delivery.
Status: specified for review; no new runtime model, parser, schedule builder,
source capture, session admission or database migration is implemented here.
The existing partial Nasdaq holiday provider remains unchanged.

## Source Audit And Newly Identified Risk

Primary pages checked November 7:

1. [Nasdaq schedule](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule?display=b2b)
   distinguishes the regular equity interval, weekday wording and system hours.
   A general information page is a candidate reference, not effective-dated
   historical rule evidence. Testing-facility weekend availability is not equity
   market opening. Broker hours are separate.
2. [Nasdaq Equity 1](https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/Nasdaq%20Equity%201)
   distinguishes business days, regular and night sessions and conditions before
   night-session commencement. Current consolidated text does not establish when
   every paragraph became operational. Its definitions require separate source
   version/effective/operative checks before use in a historical calculation.
3. [Nasdaq ETA2026-64](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2026-64),
   dated October 30, describes a December 6, 2026 expanded-hours effective date.
   It also flags directory/halts-file operational changes. This is an announced
   future transition, not proof that it is running on November 7. Implementation
   notices, conditions and any intervening changes still need checking.

This audit used web retrieval, not a registered Tong provider capture. No raw
body/source receipt, exact first-publication time, independently approved policy
or PIT trust grade is claimed for these three pages. Store no invented source
hash or historical availability. The already retained holiday page remains a
different, partial, LOW/retrieval-time evidence record.

Engineering inference: a single local civil date is insufficient to qualify
overnight-inclusive daily bars. Source observations may span two civil dates
while belonging to one exchange trade date. Older static hours guides and the
current consolidated rulebook can disagree in scope or operative period without
one being a current executable schedule. Do not resolve that by picking the
most convenient source or assuming all US venues share a calendar.

## Actual Code Boundaries

- Yahoo snapshot normalization derives an unqualified observation date from its
  timestamp in the declared market timezone. It does not retain a proved
  exchange trade-date/session-scope mapping.
- The shared daily selector rejects multiple observations on a UTC date. That
  invariant protects today's daily-shaped diagnostic input; it is not a general
  overnight-session validator. Do not weaken it to accept intraday/mixed series.
- Calendar aggregation uses civil weeks/months, explicitly unverified coverage.
  The new declaration comparison uses market-only TradingSession records with
  UNKNOWN trust/precision; it cannot certify venue/session semantics.
- The partial Nasdaq provider preserves early closes and unknown unlisted days.
  It must not be copied into a full canonical calendar to close these gaps.

No current bug is repaired or legacy receipt reclassified by this document.
All existing diagnostics remain unqualified. Regular-session research can
continue in parallel; this risk does not block approved software development or
require waiting for the provider-evidence horizon. It does block claims that an
unverified daily series is already valid across every session regime.

## Minimal Future Data Contract

Reuse provider-neutral request, evidence, artifact, batch and snapshot-verifier
contracts. Do not create a second Bar or TradingSession domain hierarchy.
Propose source-bound annotations/derived receipts before changing canonical data:

| Required Item | Meaning |
| --- | --- |
| market / exchange / asset scope | Explicit US equity venue, never a ticker-prefix inference |
| session_scope | REGULAR_ONLY, EXTENDED, MIXED or UNKNOWN, supported by source evidence |
| trade_date / trade_date_basis | Exchange-assigned date and its mapping rule, not timestamp.date() by default |
| interval_start / interval_end | Explicit aware bounds with New York timezone and actual UTC instants |
| source references and body/envelope hashes | Exact registered captures, policy version and original bytes |
| source publication / available_at | Separate original publication precision and actual local visibility |
| effective_from / effective_to | Reviewed applicability of the particular rule, not capture dates |
| operative_status | Announced, conditional, operationally confirmed or unknown; no automatic promotion |
| reviewed_at / expires_at | Separate bounded review validity; re-review does not rejuvenate source age |
| trust / availability_precision | Independently evaluated, never derived from official-domain success |
| exception / freshness / coverage flags | Preserve missing or conflicting holiday, halt and rule evidence |

Fields above are proposed annotations, not implemented schema columns or a new
approved policy. Do not add nullable columns with misleading defaults simply to
make old rows appear session-qualified. Existing evidence remains reconstructible
under its original version/hash; new source or policy changes require new receipts.

## Proposed Ordinary Schedule Builder

1. Accept an explicit venue/year/window/cutoff, original holiday receipt, separate
   regular-weekday/hours source receipts and a reviewed effective policy. Reject
   mismatched venue/year, source failure, ambiguity, expired review, future
   availability, unsupported operative status and missing pins without fallback.
2. Keep holiday/early-close declarations, regular weekday rules and exceptional
   opening/halt evidence distinct. A complete reviewed annual schedule can
   support PLANNED_REGULAR_SESSION only, not verified actual opening. Row counts
   alone cannot prove that the annual exception set is complete.
3. Derive an ordinary date only inside the reviewed interval and scope. Otherwise
   preserve UNKNOWN. In particular, weekend closure is a reviewed-rule deduction,
   never a default for an absent calendar record. Unknown emergency coverage stays
   an independent warning even when an ordinary planned day can be calculated.
4. Preserve early-close times and New York timezone. Convert actual intervals to
   UTC using timezone rules, not a fixed offset. Do not infer extended-session,
   settlement, security-level suspension or instrument listing permissions.
5. Bind the derived receipt to every exact source/policy version, the cutoff,
   actual availability maximum and all unresolved flags. Keep source quality,
   planned-date coverage, session verification and strategy validity separate.
6. A transition announcement must not change old dates, retroactively activate a
   rule or automatically admit a new session. Confirm applicable operations and
   provider bar semantics independently before selecting a policy version.

There is no automatic December 6 feature switch proposed. Unknown operability
remains unknown. Preserve a separately qualified regular-only path when possible;
do not unnecessarily block it merely because extended sessions are unsupported.

## Price-To-Calendar Bridge

Require independently reviewed instrument/venue identity and the provider's bar
interval, regular/extended inclusion, timestamp and trade-date semantics. Yahoo's
native metadata fields, response interval=1d and positive OHLC are not that proof.

Only a source-qualified REGULAR_ONLY series may be compared with the matching
planned regular-session calendar, and even then planned-date agreement cannot
prove actual-session completeness, OHLC truth, adjustment basis or strategy value.
MIXED/EXTENDED/UNKNOWN data stays visible but cannot silently use regular-session
coverage as an admission test. Keep original observation timestamps and map via
an explicitly supported trade-date rule, not a rewritten Bar timestamp.

Future coverage output must retain every source/hash/version, trust/precision,
session scope, declared versus inferred date basis, early-close interval and
missing/conflicting/suspended observation. Do not flatten the receipt into the
legacy market-only TradingSession solely to reuse a favorable coverage percentage.
No new ResearchReport, InvestmentScore or order follows from this bridge.

## Required Future Tests

- Reject new captures/reviews/rules at old cutoffs; source expiry remains a gap.
- Distinguish announcement date, effective date and confirmed operating status.
- Preserve pre-transition receipts and reject a prospective policy for an older
  period; do not silently replace approved rules or reinterpret old hashes.
- Explicitly synthetic Sunday-evening/next-trade-day, holiday-adjacent and month/
  year-boundary examples must not collapse civil date into trade date.
- Test actual UTC around DST folds/gaps; distinguish pre/post-market, regular,
  night, options, testing facilities and different US exchanges.
- Partial holiday lists, duplicate/unsupported source rows, early-close conflicts,
  stale/missing halt feeds and latest source failure cannot yield admitted coverage.
- Existing no-opt-in CLI outputs, source receipt hashes, schema and disabled
  execution/notifications must remain unchanged.
- Determinism and conditional planned-date agreement must not produce a trust,
  validation, PIT, scoring, Paper or live authorization upgrade.

These are design acceptance cases, not newly implemented or passed tests.

## Implementation Order And Non-Goals

First retain and reconstruct exact source bodies/operative notices under a
separate explicit source contract; then implement reviewed regular-only schedule
receipts and a provenance-preserving exploratory bridge. Qualify original price
session/adjustment basis and actual research/strategy validation independently.
Review the December transition before relying on the model after that boundary.

No overnight trading implementation, live broker access, Paper ledger, execution,
allocation, orders, alerts, scheduled downloads or historical data writes. Keep
framework 0.8.0/schema 0.8.3, PIT UNSUITABLE, production NOT_READY and disabled
defaults. WP-LAUNCH-001 stays ready, not accepted. A November 30 read-only delivery
target does not waive a December operational review or any existing data gate.

## Verification Of This Design Slice

Full regression of the unchanged runtime: 3624 passed / 6 skipped, 240.62 seconds.
Ruff, mypy (313 files), governance (167 checks), scoped documentation review and
git diff --check pass. Existing price, SEC and Nasdaq diagnostic database byte
hashes match the prior baseline. No source/strategy admission, runtime fix,
commit or push. Skipped opt-in network cases cannot validate these web references
or the future operating transition. These are mixed-worktree quality checks,
not an isolated release-candidate review or implementation of the future tests.
