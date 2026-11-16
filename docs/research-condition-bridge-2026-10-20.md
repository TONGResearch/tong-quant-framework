# Research Condition Bridge And Provider Diagnosis: October 20

## Meaning Of Conflict

CONFLICTED means the selected technical predicates disagree at the pinned
cutoff. It is not a global recommendation against the company, a prediction of
a price decline, or a sell instruction. Under a confirmation-based candidate
specification it fails to establish a currently confirmed entry. Missing input
and contrary observations must stay separate. An investor without a position
does not acquire an exit instruction from this diagnostic.

## Concrete Implementation

ResearchRequest now accepts an explicit optional condition_style:

- long_term_confirmation: actual hard-screen results, scored Financial and
  Value research with configurable confidence, bullish trend-structure and
  momentum families. This is an initial research hypothesis, not Tong's final
  universal buy rule or an optimized strategy.
- improved_turtle: qualified financial review as context, actual hard screening,
  strict prior Donchian breakout and all four breakout/volume/sentiment/industry confirmations.
  One weak or missing confirmation cannot be offset by another strong one.
  A supportive long-term Value score is not required for every trend hypothesis;
  contrary fundamentals remain visible, not automatically erased or approved.

Existing requests without a selected style retain their original behavior.
The condition policy's minimum confidence defaults to 60 and is injectable,
versioned and content-bound. Effective settings supply
`research.minimum_condition_confidence`; no claim is made that this is optimal.
Regime remains a separate research variable, never a hard approval switch.

The existing report builder attaches structured entry-condition diagnostics to
an assessment's features JSON and exposes the state in findings:

| State | Meaning |
|---|---|
| DATA_BLOCKED | Required research/financial/input qualification is missing |
| WAIT_CONFIRMATION | Inputs evaluated but this candidate specification is not satisfied |
| SCREEN_REJECTED | Actual hard-screen failure; cannot be compensated by technicals |
| VALIDATION_REQUIRED | Candidate specification met; independent validation still not performed |

DATA_BLOCKED/SCREEN_REJECTED keep the report incomplete and therefore block
InvestmentScore through its existing completed-report requirement. No new
trade action, order, execution permission or strategy acceptance is generated.
No second ResearchReport model or database migration is introduced. Stored
condition JSON binds subject, cutoff, actual queue/screens, thesis/counter
thesis, policy and full consumed assessment hashes; tuple order does not alter
identity. Recursive annotated inputs, future children and duplicates fail closed.

Long-candidate invalidation is shown separately. A bearish candidate reference
cannot be displayed as a long-position stop. Without actual position state,
these observations are never sell instructions. Fundamental invalidation
windows remain NOT_EVALUATED until a proper source-qualified window evaluator
exists; one raw value is not a two-quarter observation window.

Current Financial Research is deliberately unscored. No real five-stock report
has passed the financial/source admission boundary. Numeric values, test
fixtures or caller metadata cannot make the actual FinancialResearchModule
score them. This slice joins the research contracts; it does not claim the
technical-plus-fundamental strategy has been validated or become profitable.

## Actual BSE Failure Diagnosis

Installed AKShare: 1.18.64. Separate bounded workers called each endpoint without
fallback hiding the first error. Query: 20240101 through 20261019, unadjusted
equity request. Probes are access diagnostics only, not canonical population.

| Subject / time UTC on Oct 20 | Main endpoint stock_zh_a_hist | Fallback stock_zh_a_hist_tx |
|---|---|---|
| 920982 / 09:57:50-52 | ConnectionError, network_or_upstream | bj920982, KeyError, missing day |
| 000063 control / 10:01:07-09 | ConnectionError, network_or_upstream | sz000063, available, 674 rows |

Conclusions supported by these observations:

1. The earlier local bug routing 920-prefix symbols to Shanghai was real and
   fixed separately. The present probe verifies the correct bj920982 request.
2. The main source currently fails for both subjects. The precise remote/network
   cause is not established; it is not evidence that 920982 has no history.
3. The fallback can cover the control but its BSE response lacks the expected
   daily field. This agrees with a known limitation discussed in the primary
   [AKShare issue 6205](https://github.com/akfamily/akshare/issues/6205), including
   a 2026 comment. That issue is corroboration, not an exchange data guarantee.
4. These are public AKShare routes, not Tushare endpoint calls. No Tushare
   account upgrade or token re-entry is indicated by this test.
5. Do not silently rename 920982 to an older code, fabricate absent bars or
   relabel returned adjusted prices as proved unadjusted history.

The new probe method and CLI preserve endpoint, subject, range, safe exception
type and allowlisted missing-field names. Raw exception strings/URLs/stdout/
stderr are not rendered. SDK preliminary calls may ignore a native timeout;
therefore each endpoint has a finite subprocess lifetime and timeout state.
Worker identity/range mismatches and malformed output become diagnostic failures,
not empty history or provider agreement. No credentials, database writes or
trust/readiness upgrades are part of this diagnostic.
Probe timestamps identify diagnostic call starts, not historical data
publication or `available_at`; they are not fed into canonical data ingestion.

## Follow-Up: Real Ingestion Failure Handling

Tong prioritizes runnable technical-plus-fundamental research, with reliability
serving that objective. This follow-up is a targeted data-blocker repair, not a
new infrastructure milestone or a substitute for completing financial research.

One bounded repeat on October 20 at 10:53:17-19 UTC returned main ConnectionError
and correctly routed bj920982 fallback KeyError/day. No repeated network loop,
new data population, guessed historical code alias or trust promotion occurred.
The installed Sina daily implementation was inspected but not enabled as a new
fallback: it combines price/share-count series with forward filling and is not
an independently reviewed replacement for the current evidence contract.

Real implementation defects repaired in the existing adapter and ingestion CLI:

- Empty primary data previously bypassed fallback. Empty, wrong-type or
  missing-column responses now try the next endpoint and are never cached.
- A failed fallback previously hid the first error and the CLI could replace
  it with ValueError when no worker JSON was produced. A typed sanitized
  failure now crosses worker/parent boundaries with both endpoint outcomes.
- Network-class exceptions have bounded per-endpoint retries. Empty/schema/
  missing-field responses are not retried; outer generic retries cannot repeat
  the entire failed pair. The command's subprocess still bounds SDK helpers
  that ignore native timeouts. Direct adapter callers must supply equivalent
  outer supervision; this change does not impose a global SDK time limit.
- BSE plus missing day is labeled observed bse_daily_payload_unavailable,
  not a blanket permanent unsupported-market policy. Valid BSE frames still
  pass; a later recovered main source or fallback is not artificially blocked.
- A central AKSHARE_DAILY_FETCH_VERSION changes cache identity so legacy empty
  cached responses cannot bypass this repair. Old files/records remain intact.

No raw exception text/URLs or cause chains enter the typed failure. Index
routing and native fallback turnover limitations remain intact. The existing
four equity captures are not re-ingested or relabeled as independently trusted.
No database schema, execution, Paper, broker, portfolio or notification change.
No commit/push. A verified BSE daily source/export is still required before
calculating this stock's actual technical research; other equities can proceed.

Follow-up final verification: **1335 passed / 6 skipped**, 46.39 seconds; Ruff,
mypy (240 source/script files), governance (95 checks) and `git diff --check`
pass. Fourteen additional regressions cover malformed/empty fallback, both
failure causes, no credential text/cause chain, retry boundaries/recovery,
cache-write prevention, legacy-cache isolation, index identity and CLI failure
propagation. These tests do not establish source accuracy or strategy returns.

## What Previous Continuations Actually Delivered

The current code, canonical status and Git history support these categories,
not a claim that every past chat turn completed an investing milestone:

| Category | Concrete work | What it did not establish |
|---|---|---|
| Framework V0.1-V0.8 | Data, Screening/Queue, Research contracts, Validation/Replay, Portfolio/Risk research artifacts, Notification outbox | A profitable stock-selection or trading system |
| Data reliability | Conservative retrieval availability, revisions, lifecycle/universe models, provider diagnostics/calibration, source-byte binding | Complete historical PIT coverage; readiness remains UNSUITABLE |
| Engineering hardening | Migrations/fingerprints, backup/restore, version/ownership/dependency checks, secret-safe persistence | Investment effectiveness or real broker readiness |
| Controlled-launch preparation | Validation/portfolio lineage and scoped SSE market-rule calculations | Complete Paper ledger or all-board executable A-share rules |
| Recent financial work | Reviewed 600000 example facts, comparative/bank units, freshness and anti-false-scoring controls | Completed financial analysis for the user's five equities |
| October 20 technical slice | Actual MACD/KDJ, triple/Granville, startup/invalidation and family diagnostics | Validated combined financial/technical entry and exit rules |

Examples in recent Git history: 8794b57 consolidates the Oct 18 research/data
hardening baseline; 12c221d adds the scoped SSE rule pilot; 90ea3e4 adds runtime
input diagnostics; e33cadc preserves observed AKShare availability; 6be0a84
repairs corporate-action evidence. New financial/technical work after that
baseline remains dirty/uncommitted in the inspected checkout.

Earlier pure technical implementation was left planned behind the evidence
package. Tong subsequently authorized research calculations separately. That
planning dependency must not be confused with a claim that completed technical
strategies were merely waiting to run. Future progress should report both
engineering completeness and an actual end-to-end investing example, separately.

## Remaining Path

1. Obtain a verifiable BSE daily source/export with explicit code history and
   evidence, rather than repeatedly relying on a failing fallback.
2. Admit source-bound sector financial inputs, valuation and actual sentiment/
   industry calculations for the chosen scope; preserve missing data honestly.
3. Define and evaluate falsifiable fundamental invalidation windows and
   horizon-specific technical exits without assumed fills.
4. Validate components and combined hypotheses with OOS/ablation/stability,
   corporate actions, calendar/status, costs, T+1 and failed exits.
5. Consider controlled simulation only under its separately approved gates.

Execution/notifications stay disabled, live orders false, PIT UNSUITABLE and
production NOT_READY. No Execution, Paper, Broker, Portfolio or Notification
module change; no commit/push. No new real financial reports or trading claims.

## Verification

Full suite: **1321 passed / 6 skipped**, 48.92 seconds, including 40 new cases.
Ruff and mypy pass (240 source/script files); governance passes 95 checks and
`git diff --check` passes. Persistence tests exercise the official report and
existing SQLite schema with/without explicit condition selection; real Financial
gaps still prevent InvestmentScore. Endpoint tests cover safe failure details,
empty/schema/type distinctions, worker timeouts and identity failures.
No real-source accuracy, profitability or completed strategy validation is claimed.
