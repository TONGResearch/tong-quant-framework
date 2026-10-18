# Financial Numeric Hardening - 2026-10-17

Work package: WP-LAUNCH-001 (partial). No market-data promotion or trading
authorization. Framework 0.8.0, schema 0.8.2, PIT UNSUITABLE, execution disabled.

## Confirmed defects and bounded repair

The legacy financial normalizer selected `value or alternate-value`. Numeric
zero therefore disappeared when no alternate existed, or was replaced by an
inconsistent alternate. Nullable pandas values could raise an ambiguous truth
error; blank strings failed decimal conversion. Both aliases could disagree
without any explicit conflict rejection.

The normalizer now parses aliases independently, retains zero and negatives,
treats null/NaN/blank as missing (never as zero), and requires nonmissing
numeric aliases to agree. Malformed, boolean, infinite and conflicting values
fail with fixed error text that does not echo the payload. The ingestion
transaction retains its pre-call domain/audit state on a numeric conflict.
Native snapshot capture is unchanged: it preserves original observations,
including unreviewed/malformed values, without converting them into facts.

The legacy ingestion warning now explicitly identifies its unreviewed metric,
currency, unit and accounting-period semantics. This patch fixes numeric
selection, not the entire legacy normalization contract. Existing facts are
not rewritten, relabelled or silently repaired.
At this milestone the writer ignored duplicate storage identities and checked
raw-hash conflicts, not every material-field disagreement. Reprocessing the same
raw hash was therefore not proof of a corrected old fact. A separate audited
correction/material-field-conflict contract remained technical debt. The
[October 18 repair](fundamental-fact-integrity-2026-10-18.md) subsequently added
material-field checks and atomic conflict rejection; legacy audits remain open.

## Reviewed-mapping acceptance checklist

Before any real native observation may populate canonical fundamentals:

1. Pin the source dataset/statement, raw artifact hash, native metric name and
   reviewed canonical definition. Similar names are not semantic equivalence.
2. Require evidenced accounting unit, scale and currency per metric. Never
   apply a blanket CNY/absolute assumption to ratios or per-share quantities.
3. Establish consolidated versus parent-company scope, fiscal period, and
   cumulative versus single-period basis. Do not derive quarter deltas from
   incomparable versions or missing periods.
4. Review applicability by industry. A bank's revenue, debt and cash-flow
   interpretation must not inherit a generic industrial-company score.
5. Bind numeric revisions to actual source evidence. A matching announcement
   date cannot backdate the current numeric snapshot's `available_at`.
6. Retain missing, unsupported and conflicting fields as explicit gaps;
   document evidence and tests before admitting each individual mapping.

This is an acceptance checklist, not an implemented mapping registry. The
13,000 exploratory native observations remain unreviewed; canonical fact,
research and validation counts are not increased by this change. Independent
source corroboration, disclosure granularity and historical continuity remain
open. No provider receives upgraded trust.

## Verification and impact

- Added 19 numeric unit cases and one integration rollback regression.
- Full pytest: 782 passed, 6 skipped.
- Ruff, mypy (218 source/script files), governance and whitespace checks pass.
- No schema migration, database write, network capture or artifact publication.
- No Paper Trading, Broker, Execution, Portfolio or Notification changes.
- Changes remain local and uncommitted; no push performed.

Next bounded step: review a small explicit metric/unit/period mapping against
retained source artifacts and authoritative statements, then implement only
the evidenced subset. Original-time availability and independent validation
remain separate acceptance gates. No immediate user credential action is
needed for this numeric repair.
