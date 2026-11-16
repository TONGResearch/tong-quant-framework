# Technical Implementation Audit: October 20, 2026

## Scope And Authority

This review inspects the actual PyCharm working tree, preserving pre-existing
dirty financial/recovery work. Earlier conversational stock commentary did not
run Tong Quant. Tong's new request authorizes WP-RESEARCH-002 for deterministic
technical calculations before the provider horizon finishes. It does not waive
WP-RESEARCH-001 source admission, historical validation, size/style or live gates.
Framework/schema stay 0.8.0/0.8.2; existing ResearchAssessment features JSON stores
the new diagnostics without a migration.

## Coverage

| Method | Before this review | Current result / remaining boundary |
|---|---|---|
| Modified Turtle | Donchian, volume, two supplied confirmations, ATR/pyramid geometry | Strict prior-channel breakout and conjunctive four confirmations. Failure gives CAUTION/no score; success uses the weakest component. Supplied sentiment/industry scores still need source-qualified calculation. |
| MACD + KDJ | Design only | Configurable numeric calculations and current cross observations; not a validated entry strategy. |
| Indicator resonance | No family computation | Two descriptive families: trend structure and momentum. Correlated indicators count once; contradictions remain visible. No confluence investment score. |
| Body crossing three MAs | Design only | Explicit bullish/bearish candle-body crossing, configurable SMA cluster; wick-only crossing is rejected. Default 5/10/20 is a declared convention. |
| Startup capture | Design only | Causal WATCH/ARMED/CONFIRMED/INVALIDATED/EXPIRED observations; later confirmation never changes an earlier prefix. Missing warm-up remains insufficient. |
| Dynamic stop | Rolling ATR references | Added long/short setup invalidation references that only tighten while confirmed. Not position-aware or executable; intrabar touches/fills are not inferred. |
| Granville | Basic MA alignment | Eight named predicates, with continuation and extreme-deviation mean reversion kept separate. No universal chart-platform equivalence claim. |
| Large/small cap | Design only | Still blocked on qualified PIT market caps, shares and eligible universe; no ranking from current snapshots. |
| A-share patterns | Upper shadow computed; remaining patterns supplied | Fixed explicit integer breadth admission and strict >3000. VWAP, first/second-board, opening support, low-volume pullback and timing windows are not automatically calculated from intraday data. |
| Seven-plus-one | No verified specification/code found | DEFERRED_BY_OWNER after Tong explicitly postponed it this turn. It does not block the other requested methods; never guess a similarly named internet method. |
| Fundamentals | Source-bound diagnostics | Remains unscored without admitted sector/source policy. Technical agreement cannot override this gap. |
| Weekly/monthly trend | Five/21-observation returns | Still proxies, not completed exchange-week/month bars. |
| T+1 | Scoped SSE market-rule pilot | Not an all-China execution implementation or proof of SZSE/STAR/BSE account permissions. |

## Versioned Formulas

- MACD uses existing pandas recursive EWM (`adjust=False`), first-close seed,
  alpha=2/(period+1), DIF=fast-slow, DEA=EMA(DIF), histogram=DIF-DEA, not doubled.
  Output requires slow+signal observations; seed/window dependence is retained.
- KDJ uses full N-observation RSV, K=D=50 seed, alpha=1/K and 1/D recursion,
  zero-range RSV=50, unclipped J=3K-2D, and N+1 warm-up for cross comparison.
- SMA uses full trailing close windows. Body crossing compares the current
  candle with current-inclusive MAs. Granville predicates explicitly freeze MA
  period, slope lookback, relative support tolerance and extreme deviation.
- Startup arms on body crossing and confirms only on a later close beyond the
  original candle high/low. A close beyond the prior invalidation reference
  invalidates first. Unconfirmed setups expire after configured observed bars.
  Arithmetic true-range ATR (not Wilder smoothing) tightens references; these
  are not fills, orders or verified exchange-session counts.
- Existing Technical score excludes the new diagnostics, which carry
  `technical_scoring_admitted=false`. No automatic financial synthesis, scoring
  admission, parameter profitability or buy/sell effectiveness is claimed.

References: [pandas EWM](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html),
[TA-Lib function taxonomy](https://ta-lib.org/functions/). They define methods,
not evidence of investment returns. Tests include independent recursive
references and eight explicit event fixtures, not proprietary-vendor parity.

## Provenance And Actual Data

The shared selector checks visible timestamps, one subject/source, unadjusted
finite OHLCV, conflicting versions and multiple timestamps on one UTC date.
Duplicate rows/revisions cannot inflate warm-up. Latest suspended revisions
cannot resurrect an older price. Diagnostics bind selected rows, parameters,
version and cutoff in a hash. Empty-input hashes must be read with their outer
subject; these are input hashes, not issuer report identities.

Hash identity is not source authentication. Unadjusted action jumps, missing
sessions, staleness, incomplete-session timestamps and unknown historical
corrections remain independent limitations. Calculations do not raise trust,
PIT readiness or strategy confidence. Mean-reversion events cannot become
additional trend-continuation votes.

At the pinned diagnostic cutoff 2026-10-20T15:00:00+08:00 both existing business
databases returned zero visible bars for 000063, 002624, 920982, 688363 and 600109.
This means database/query absence, not provider-wide unavailability. The new
read-only `scripts/inspect_technical_inputs.py` creates no queue/report/score
or database and intentionally exits 2 for partial diagnostics.

Real captures use the existing bounded AKShare neutral-evidence ingestion into
the separate ignored `data/processed/technical-request-20261020.sqlite3`, never
the existing business databases. First 000063 attempt failed; a bounded retry
accepted 674 rows with zero rejects. Original frame/query evidence and
LOW/retrieval-time warnings remain retained; this does not qualify an original
historical publication/revision series. Other capture outcomes and diagnostic
coverage must be read from the actual run, not inferred from this first success.

Final capture outcome: 000063, 002624, 688363 and 600109 each have 674 retained
daily observations (2024-01-01 query start, last observed 2026-10-19). BSE 920982
failed with DataProviderError on both attempts. A real adapter defect routed
920-prefix fallback requests to Shanghai; it is repaired with a separately
versioned routing parameter and eight regression cases. Retrying the correct
BSE route still failed, so source availability is unresolved, not certified by
the code fix. No old/new ticker alias or historical membership is fabricated.
Issuer identity is corroborated by this [BSE disclosure](https://www.bse.cn/disclosure/2026/2026-05-18/89258161a83b47ccaa11f6fc3c559156.pdf).

At calculation cutoff 2026-10-20T09:45:41.580662Z the actual local code produced:

| Symbol | Last raw close | MACD DIF / DEA | K / D | Calculated technical context |
|---|---|---|---|---|
| 000063 | 27.27 | -1.630736 / -1.308052 | 10.303314 / 8.841552 | BEARISH trend structure, conflicted momentum |
| 002624 | 9.94 | -0.198929 / -0.260393 | 59.748139 / 60.775684 | BEARISH trend structure, conflicted momentum |
| 920982 | unavailable | unavailable | unavailable | INSUFFICIENT_DATA |
| 688363 | 34.00 | -0.464389 / -0.449997 | 30.716428 / 28.681568 | BEARISH trend structure, conflicted momentum |
| 600109 | 8.07 | -0.099712 / -0.106578 | 46.696966 / 49.180248 | BEARISH trend structure, conflicted momentum |

Prices above are October 19 observations, not October 20 real-time quotes.
Positive MACD histogram is not positive DIF or proof of reversal; K>D is not
automatically a new crossover. Extreme-downside Granville events observed in
000063/002624/688363 do not prove a bottom. The four available series show no
current triple-body-cross event. Setup-state labels refer only to their own
body-cross candidate and direction, never full-Turtle approval. No source-bound
financial integration, independent replay or validated buy/sell result was
generated by this diagnostic run. These numbers are not trade instructions.

## Remaining Work

1. Analyze all five equities as Tong clarified; seven-plus-one is postponed.
2. Qualified calendar/actions/price and intraday evidence; preserve capture gaps.
3. Source-bound sentiment/industry and sector financial policies, then an
   explicit horizon-aware synthesis rather than manually favorable scores.
4. Component/ablation/combined-method validation, nearby-parameter stability,
   OOS, costs, T+1, limits, suspension, liquidity and failed-exit tests.

Execution, Paper, Broker, Portfolio and Notification modules are unchanged.
Execution and notifications stay disabled, allow_live_orders stays false, PIT
stays UNSUITABLE and production NOT_READY. No commit/push is included.

Final-code full suite: 1281 passed / 6 skipped; Ruff and mypy (238 source/script
files) pass. Final governance and whitespace checks are recorded in canonical
status. Tests use synthetic fixtures; they do not prove real-source accuracy,
profitability or vendor indicator parity. A subsequent owner-deferral label-only
change is verified with the focused technical/research/governance suite.
That focused run passes 240 tests. All four newly registered raw-frame files
verify against the registry under the actual pipeline root
`data/processed/raw/provider-artifacts` (report hash
`8e36127fb34a6313fb584ea0023e2b8895c9ddf9ff8c599f421c8c5e2e7b3454`).
An earlier audit with the generic `data/raw/provider-artifacts` root reported
four missing files; correcting the explicit root resolved that observation,
not a repair/replacement of bytes. This audit is not source corroboration or
encrypted recovery. New captures are not covered by earlier encrypted backups.
