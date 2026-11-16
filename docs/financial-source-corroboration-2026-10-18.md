# Financial Source Corroboration: October 18

## Scope And Result

This bounded WP-LAUNCH-001 input review is not an issuer recommendation or
authorization to trade. The native capture has 13,000 statement observations
but no canonical facts. Three observations for 600000 / 2026-03-31 numerically
match a retained issuer filing **under an explicit native-unit hypothesis**,
not an approved global accounting mapping.

The [issuer's unaudited first-quarter report](https://static.cninfo.com.cn/finalpage/2026-04-30/1225261168.PDF)
was captured through existing direct CNInfo neutral ingestion. PDF pages 15,
17 and 18 were rendered and visually reviewed as well as text-read. Tables
distinguish group from company columns and parent shareholders' profit from
total profit, and explicitly use CNY million.

| Descriptive review metric | Native field | Issuer CNY million | PDF page(s) |
|---|---|---:|---|
| revenue | operating_income_total | 46,573 | 17 |
| profit_attributable_to_parent | parent_holder_net_profit | 17,861 | 17, 18 |
| total_assets | assets_total | 10,305,646 | 15 |

Flows cover January 1-March 31; assets are a March 31 stock. Values use the
current-period group column. This bank sample does not establish applicability
of nonfinancial-company ROIC, free-cash-flow or other scores. Descriptive
metric labels do not register canonical mappings.

## Repeatable Boundary

`data.calibration.financial_review` binds immutable review annotations to a
native evidence id, exact original serialized frame/row, period, statement,
issuer PDF hash/bytes and artifact identity. Decimal arithmetic preserves zero,
negatives and precision. Missing/conflicting values and rejected inputs stay
visible; future inputs fail closed. Existing calibration machinery compares
exact normalized strings with trust capped at LOW, or UNKNOWN if native trust
is unknown. Numeric agreement is not dataset coverage, Research/Investment
confidence, independent-provider proof or PIT readiness.

`config/financial-reviews/600000-2026q1.toml` records manual page/column, value,
unit hypothesis, period, sector and review-time annotations. The tool does not
authenticate annotations by parsing the PDF. Native currency, consolidation,
unit and flow-start semantics remain hypotheses awaiting separate review.
Matching a few numbers cannot prove all history, revision chronology,
publication timing or independence of provider lineages.

`scripts/review_financial_observations.py` reads an existing SQLite snapshot
and content-addressed files without initializing or writing the database.
It exports new-only, credential-screened mode-0600 JSON, binds the plan hash/
model version and retains rejected rows. Exit 2 is intentional even on numeric
agreement: semantic/historical approval remains incomplete. Existing output is
not overwritten. Reports deny canonical population, historical replay,
investment scoring, validation and independent-provider authorization. No
ResearchReport is created and no readiness conclusion is promoted.

```text
native AKShare evidence + retained original frame
              + manually reviewed CNInfo filing annotations/bytes
    -> read-only numeric corroboration -> partial review report
    -X-> canonical facts, InvestmentScore, Validation or execution
```

Effective review availability is the latest of review time, native visibility/
retrieval and filing publication/retrieval, never the historic period end.
The direct CNInfo adapter's claimed publication precision is not independently
verified here and cannot become historical numeric availability.

## Actual Local Observation

This section records the earlier zero-fact checkpoint. The subsequent
[dedicated issuer extraction](reviewed-filing-facts-2026-10-18.md) populated
three LOW/retrieval-time facts through a separate manual contract; it did not
authorize or change this numeric spot review or native mappings.

- CNInfo batch: `32ca2a40-6b56-405e-9362-f7ac1a72d7eb`.
- Three disclosure records and three PDF artifacts were added to the separate
  exploratory database; prior metadata and native snapshots were preserved.
- Selected PDF SHA-256:
  `df6911eb74bd5448fbf7729936979c60391052746db7d0577e4d4803f38d77e1`.
- Selected PDF retrieved: `2026-10-18T15:28:25.871823+00:00`.
- Manual review time: `2026-10-18T15:34:32+00:00`.
- Report as-of: `2026-10-18T15:40:08.876323+00:00`.
- Review plan SHA-256:
  `e9c99724ec1ae1398f650eb97bf14fa7980164e3ad2cd8343d6d6f1cc7784777`.
- Local output: `data/processed/financial-reviews/600000-2026q1-20261018.json`;
  three `NUMERIC_MATCH_REVIEW_REQUIRED`, LOW / RETRIEVAL_TIME. Generated output
  and captured bytes remain ignored local data, not GitHub content.

Both database integrity audits passed. Operational audit identity remains
`fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
Exploratory inventory has 187 bars, 13,220 provider records and seven registered
artifacts; all seven files verified. Both databases still have zero fundamental
facts, research reports and validation reports. There is no schema or dependency
change; framework/schema remain 0.8.0/0.8.2.

These captures postdate the encrypted recovery snapshot described in
`encrypted-recovery-2026-10-18.md`. That earlier drill does not retain or verify
these additional files. Independent-device recovery and cloud synchronization
are not claimed.

## Verification And Next Work

Forty-two new regression cases cover exact decimals, deterministic hashing,
zero/negative/missing/conflicting values, time cutoffs, row/source/artifact
mismatches, malformed semantics, credential-like annotations, CLI snapshot
reads, rejected-row preservation and no-overwrite output. Full local suite:
**1003 passed / 6 skipped**; Ruff and mypy pass (226 source/script files).
Final governance/whitespace results are recorded in PROJECT_STATUS. There is
no remote-CI or clean installed-release claim for this working tree.

Next independently establish source-backed native unit/currency/scope and
period mappings before reviewed retrieval-time-only fact population. Expand
corroboration to relevant periods/metrics and sector-appropriate research,
leaving missing revisions and historical continuity explicit. Finish real
status/universe/action coverage, pinned validation policy and an actual
research-validation chain before paper acceptance. Evidence accumulation runs
in parallel; this tool is not a substitute. PIT stays UNSUITABLE, production
NOT_READY, execution/notifications disabled. No Paper, broker, order, portfolio,
notification or execution code changed. No new commit or push was performed.
