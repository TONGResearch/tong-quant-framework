# Improved Turtle Price Observations

Date: November 8, Asia/Kuala_Lumpur. Existing ready WP-LAUNCH-001 / read-only
single-equity research increment. No trading or strategy admission.

## What Changed

The full TrendResearchModule correctly withholds an assessment when sentiment or
industry heat is unavailable, but previously withheld its observable price/volume
geometry too. New price_observations() exposes the existing calculations without
creating external confirmation evidence, an official ResearchReport, score or
Signal. Private _PriceGeometry is a shared calculation result, not a second
research/strategy domain model. Full evaluate() and the new view reuse the same
Donchian, volume and arithmetic ATR formulas; configuration and thresholds stay
unchanged.

The existing overseas CLI accepts optional --trend-observations in read-only
mode; --capture is rejected before database/network work. Default JSON is
unchanged without the flag. With it, the existing Chinese Markdown view renders
price/volume observations while keeping missing sentiment/industry explicit.
China-A callers can use the same pure calculation with checked daily bars; the
CLI still supports its declared US/HK/MY scope, not arbitrary-market ingestion.

## Contract And Boundaries

- Component version: trend-price-observations-v1, centrally managed.
- Exact UTC cutoff, market/symbol, selected observation/availability, parameters,
  usable/required counts and full original input hash remain explicit.
- Prior channel high and average volume exclude the current bar. Strictly equal
  close is not a breakout. Raw breakout and configured research-threshold
  observations remain separate; neither is an admitted trading confirmation.
- Both external confirmations are None and four_confirmations_complete is false,
  even when both price/volume observations pass. No favorable score can fill a
  missing confirmation. No regime switch or broker/order path.
- Missing warm-up returns None, not fake zero or False forecasts. Nonpositive
  prior average volume withholds ratio/volume threshold/ATR, preserving the
  existing full engine's insufficient-volume behavior.
- Full original-series validation rejects future, adjusted, conflicting,
  mixed-instrument and intraday-shaped input. Latest suspension blocks current
  calculations rather than reviving a prior active close. Duplicates do not
  inflate warm-up; original observations remain bound to the hash.
- Sources, sessions, adjustments and freshness remain unqualified/unassessed.
  Twenty observations are not proof of twenty complete verified trading days.
  ATR is the existing arithmetic true-range mean, not newly introduced Wilder
  smoothing. No new ATR stop/order/sizing interpretation is introduced.

Full Trend model version remains unchanged because its output semantics and
formulas remain identical. Before extraction, three synthetic complete-assessment
golden hashes were recorded and remain exact after refactoring:

| Case | SHA256 |
| --- | --- |
| Four satisfied | 60b13e1c44a98ecbfa4f25413a8ae6f585690651620b221790857566e4c8a218 |
| No breakout | 9ae03ff260657b054ff62180320f335cdc7bb3b27f45ff63825ea0e60071d4a1 |
| Zero prior volume | 9a6ad45ada2bfb5d9ae8f27da33f20bb91b8354623112009da42a29ccd50ef8b |

## Retained NVDA Check

Read-only reuse of the earlier real capture, not a new quote or a new provider:
data/processed/usability-nvda-20261108-44zdbrvz/market.sqlite3, cutoff
2026-11-08T09:18:31.925654+00:00, latest native daily date November 6.

- Native daily value: about USD 186.64.
- Prior 20-observation channel high: about USD 233.92, not a proposed buy price.
- Strict breakout: false; configured breakout-threshold observation: false.
- Current native volume: 179,722,400; prior average: 112,920,530.
- Volume ratio: about 1.591583; configured volume-threshold observation: true.
- Sentiment/industry heat: not assessed; all-four completeness remains false.
- ATR: about 8.020001, not a current position stop or risk guarantee.
- Source trust remains LOW/retrieval-time; no source/PIT/strategy promotion.

Generated ignored local files NVDA-trend-observations.json and
NVDA-trend-note.zh-CN.md preserve the old JSON/note. New observation hash:
acd7ec938bfc09fca5365e61fbf8f2033712aff0e4ae181928629567212648e7.
New Markdown hash: 40317625479d686ffac005c8799aa921195ce2d3b8a468d20cea15d5357d4569.
Original note hash and database hash remain unchanged. Git is not their backup.

Volume above a historical average can accompany selling or a rebound after a
decline. It is not institutional buying, imminent upside or a second independent
vote. A failed breakout observation does not invalidate all long-term/value
research approaches, and missing external data is not proof of a bad company.

## Verification And Next Steps

Thirty-one new cases cover formulas, equality, configuration, warm-up, zero
volume, suspension, future/adjusted/conflicting/intraday/mixed input, duplicates,
UTC labels, content hashes, three full-engine golden receipts, three-market
offline JSON/Markdown, latest-failure preservation, capture rejection and view
context/authority checks. Full pytest: 3741 passed / 6 skipped, 278.93 seconds;
Ruff, mypy (314 files), governance (171 checks), scoped import/credential review
and git diff --check pass. All four retained sample DB hashes are unchanged.
Network skips are not actual provider checks. These mixed-tree results do not
approve an isolated release candidate, source quality or a profitable strategy.
No schema, migration, dependency, execution/notification default or trading
changes. PIT UNSUITABLE, production NOT_READY and launch ready/not accepted remain.

Continue source-qualified sentiment/industry evidence, financial definitions and
actual research/validation. Do not turn this view into an entry-price generator,
an automatic order, an opening-minute prediction or a guaranteed profitable rule.
