# Same-Filing Financial Comparatives: October 19 MYT

## Delivered Scope

This WP-LAUNCH-001 slice extends the three reviewed issuer observations into
six source-bound observations and three **descriptive** period comparisons.
It does not qualify financial scores, historic validation, Paper or live use.
Trust remains LOW / RETRIEVAL_TIME and global PIT remains UNSUITABLE.

The retained [2026-Q1 issuer report](https://static.cninfo.com.cn/finalpage/2026-04-30/1225261168.PDF)
was visually rechecked on PDF pages 15, 17 and 18. Its group columns contain
2025-Q1 income comparatives and December 2025 balance comparatives. These are
historical amounts **as presented in a later filing**, not independently
recovered original 2025 numeric revisions or publication times. Annotation
correctness and accounting comparability have no independent second review.

| Metric | Current CNY million | Comparative CNY million | Comparison | Change % |
|---|---:|---:|---|---:|
| revenue | 46,573 | 45,922 | 2026-Q1 versus 2025-Q1 YTD | 1.4176 |
| profit_attributable_to_parent | 17,861 | 17,598 | 2026-Q1 versus 2025-Q1 YTD | 1.4945 |
| total_assets | 10,305,646 | 10,081,746 | March 2026 versus December 2025 | 2.2208 |

The asset change is `since_prior_year_end`, not a year-on-year rate, stock-price
return or investment return. The December balance column is labeled audited
in this otherwise unaudited quarterly report; this is a retained source label,
not verification of a separate audit opinion or permission to raise trust.
No favorable/adverse investment conclusion follows from these changes.

## Contracts And Compatibility

`FilingExtractionReview` now optionally declares `filing_period_end`,
`comparability=as_presented_same_filing` and
`issuer_revision_status=unverified`. The source column distinguishes
`group_current_period`, `group_prior_year_period` and `group_prior_year_end`.
Comparative flows require matching calendar-year YTD periods; comparative
stocks require the previous December 31. Unsupported columns, missing edition
annotations, unproved revision claims and wrong period/statement combinations
fail closed. Availability is still capture/review bounded, not the prior
period end; recorded batch completion is also required at the read cutoff.

- Existing v1 source packets omit all new optional fields and preserve their
  exact byte representation, hashes, evidence identities and limitations.
  The fixture golden hash and real current-packet hash were rechecked.
- New comparative packets use `reviewed-comparative-filing-facts-v2` and
  retain the later filing edition, column and original-revision warning.
- Input receipts use `financial-source-inputs-v2-comparatives` because their
  provenance shape has changed. Earlier v1 receipt exports remain archived;
  they do not acquire a v2 identity. Reconstruct a new receipt explicitly.
- `same-filing-financial-comparison-v1` binds the input snapshot, exact values,
  dates, source references, method, statuses and outcome in deterministic
  comparison hashes. Financial assessment version becomes
  `financial-v0.5.3-comparative-diagnostics`. Prior stored assessments are not
  rewritten or automatically qualified.
- Framework 0.8.0, schema 0.8.2, migration 0010 and 64 tables remain unchanged.
  No dependencies, Portfolio, Notification, strategy, Paper, broker or
  execution code changed. Persistence uses the existing neutral transaction.

## Descriptive Research Boundary

```text
retained current-column v1 facts + explicit same-filing comparative v2 facts
 -> existing source-bound reader / immutable receipt v2
 -> financial_comparisons
 -> diagnostic FinancialResearchModule features or explicit CLI export
 -X-> InvestmentScore, validation approval, orders or execution
```

The calculator requires the same issuer, filing identity/hash, group scope,
currency/unit, sector, filing edition and compatible exact periods. It does
not compare arbitrary latest rows across filings, silently choose among
duplicates, or fall back to an older favorable current observation when the
latest is rejected. Missing, unsupported and incompatible inputs remain
explicit. Source binding proves stored consistency, not document authenticity.

Signed amount change is `current - prior`. A percentage is emitted only when
the prior value is positive: `(current - prior) / prior * 100`, rounded to four
decimal places with Decimal ROUND_HALF_EVEN. Zero/negative baselines retain
the signed amount change but have no growth percentage. Numeric bounds and
unsupported calendars fail closed. There is no annualization, standalone-
quarter inference, TTM calculation, growth score or portfolio-return claim.

`inspect_financial_inputs.py --comparisons` explicitly includes the descriptive
diagnostics. It remains read-only and returns exit 2; optional exports are
credential-screened new-only mode-0600 files. FinancialResearchModule exposes
the changes/statuses/hashes without granting a score or confidence. Bank
scoring remains unqualified; the caller's missing-metric list is not an
approved bank checklist.

## Actual Local Observation

Three new observations were added only to the exploratory database through
two dedicated review plans in `config/filing-extractions/`:

| Scope | Batch | Review-packet SHA-256 |
|---|---|---|
| 2025-Q1 comparative in 2026-Q1 filing | c74e8ccf-6716-4ed2-b800-75f6d4ad4ec2 | 932fb6678c0cd41ef50e7c35295f7b01f199a4d466aee9492fc7e5b5bbd5c1d4 |
| 2025 year-end comparative in 2026-Q1 filing | bb5f7dd6-31ec-415d-a7d1-0efab60dd5ed | e2f60a02fc5814ed91db23a25df1932ec7afc2f22cf0d448d99c626169323817 |

Review availability is `2026-10-18T16:38:57+00:00`. A new diagnostic at
`2026-10-18T16:48:04.820679+00:00` reconstructed all six observations, with input
hash `2626f1f50b11e91aaa051aaefe7053d7d25b0937473935126dfb158c0a016758`.
It is retained locally at
`data/processed/financial-reviews/comparative-inputs-20261019.json`.
Four requested gaps (cash_flow, debt, roe, roic) remain visible; unsupported
comparisons have absent values, not zero changes. All authorization flags
remain false. Original current-fact raw hash remains
`bc7ddc18728f4714db39bcb58387f09451d8d54fb3aceca904745b256561388a`.

Exploratory counts: 3 -> 6 facts, 13,223 -> 13,226 provider records and 8 -> 10
registered artifacts. All ten files verify. Both database integrity audits
passed; the operational audit identity remains
`fce73cf7f000c105b6aa96b12d108f4aba3d34805fdfd02f608e116b564133a0`.
The exploratory audit identity is now
`f319b39a424634395ba3d218e4940eaca87618d952ee9bb15187b43b79297626`.
These audit identities are not row-content hashes. Real ResearchReport and
ValidationReport counts remain zero. No operational source data was written.

## Verification And Next Work

Full local verification: **1117 passed / 6 skipped**, including 21 new
regression cases; Ruff and mypy pass (233 source/script files). Final governance
and whitespace checks are recorded in PROJECT_STATUS. Tests cover v1 golden
identity, comparative edition/period/revision rejection, source-bound six-fact
population and retries, older cutoffs, exact signed changes, nonpositive bases,
missing/mismatched/duplicate/rejected inputs, numeric/calendar bounds, CLI
partial exports and unscored FinancialResearchModule integration.

Next expand bank-appropriate financial/ratio observations with explicit source
units and period definitions, and define reviewed sector research/scoring
policies. Do not manufacture generic ROIC/FCF/debt scores or interpret the
three changes as an investment thesis. Historical original revisions,
independent calibration, sector applicability, real research-validation
lineage and authoritative launch runtime inputs remain incomplete.

The existing encrypted recovery snapshot does not include this new data or
code. Ignored data is not uploaded by Git; independent-device retention remains
open. No new commit, push, remote-CI or installed-release acceptance is claimed.
Production remains NOT_READY, execution/notifications disabled; this is not
completion of WP-LAUNCH-001 or permission for any live trading.
