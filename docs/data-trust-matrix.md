# Data Trust Matrix

This document records the current point-in-time quality of every dataset exposed
by `AkShareAdapter`. Classification is conservative: retrieval success does not
prove historical availability, completeness, or publication timing.

## Classification Rules

- **PIT-safe**: historical values and their historical availability can be
  reconstructed without using later information.
- **Partially reliable**: useful historical content exists, but availability,
  corrections, or coverage has unresolved limitations.
- **Retrieval-time snapshot only**: the record is valid only as knowledge
  obtained when Tong Quant fetched it.
- **Unsuitable for historical validation**: it must not be used to reconstruct
  decisions before its retrieval without a stronger source.

No currently integrated AKShare dataset qualifies as universally PIT-safe.
Individual records backed by exact CNInfo announcement timestamps may be usable
when runtime coverage passes, but that does not upgrade the entire dataset.

## Matrix

| Dataset | AKShare endpoint | Classification | Trust | Historical-validation rule |
|---|---|---|---|---|
| A-share unadjusted daily bars | `stock_zh_a_hist`, Tencent fallback | Retrieval-time snapshot only | LOW | New ingestion uses actual retrieval visibility, never assumed historical close+minute. Only unadjusted; historical corrections and optional turnover remain unverified. |
| A-share adjusted daily bars | Same endpoints with qfq/hfq | Unsuitable for historical validation | LOW | Rejected in strict PIT mode until dated adjustment factors can be reconstructed as known at each decision time. |
| China index daily bars | `index_zh_a_hist`, Tencent fallback | Retrieval-time snapshot only | LOW | Actual retrieval-time visibility; not authenticated historical publication or correction history. |
| Trading calendar | `tool_trade_date_hist_sina` | Retrieval-time snapshot only | LOW | Actual retrieval-time visibility. Open dates do not prove absent dates were closed or establish historical emergency closures/revisions. |
| Company information | `stock_individual_info_em`, CNInfo fallback | Retrieval-time snapshot only | LOW | Never use as historical company state before `retrieved_at`. |
| Current A-share universe | `stock_zh_a_spot_em`, code-name fallback | Retrieval-time snapshot only | LOW | Must not reconstruct a historical listed or tradable universe. |
| Financial statement numeric values | THS income, balance-sheet, cash-flow endpoints | Retrieval-time snapshot only | LOW | Values are visible only from retrieval time, even if disclosure metadata matches. A publication date/revision label does not authenticate the numeric version. |
| Actual disclosure schedule | `stock_yysj_em` | Partially reliable | MEDIUM | Date-only evidence is available for supported periods and becomes visible conservatively at end of day. |
| Financial disclosure announcements | `stock_zh_a_disclosure_report_cninfo` | PIT-usable per covered record | HIGH | Exact announcement timestamps are retained; title parsing, report coverage, and numeric revision values still require warnings. |
| Current ST status | `stock_zh_a_st_em` | Retrieval-time snapshot only | LOW | Preserves observed current ST membership only; cannot infer earlier ST intervals. |
| Current suspension status | `stock_zh_a_stop_em` | Retrieval-time snapshot only | LOW | Preserves observed current suspension only; cannot reconstruct full suspension history. |
| Suspension/resumption events | `stock_tfp_em` | Partially reliable | MEDIUM | Effective dates are retained, but historical knowledge is limited to retrieval time unless stronger provenance exists. |
| Shenzhen ST name changes | `stock_info_sz_change_name` | Partially reliable | MEDIUM | Supports dated ST entry/exit evidence for Shenzhen only; Shanghai and Beijing remain incomplete. |
| Delisted securities | Shanghai and Shenzhen delisting endpoints | Partially reliable | MEDIUM | Effective delisting dates may be useful, but announcement availability and complete exchange coverage require verification. |
| CSI300/500/1000 membership | `index_stock_cons_csindex` | Retrieval-time snapshot only | LOW-MEDIUM | Stored as dated current snapshots. Missing entries/exits prevent backward survivorship-safe reconstruction. |
| Corporate actions | `stock_fhps_detail_em` | Partially reliable | MEDIUM content / LOW timing | Effective dates are useful for audit; announcement availability and revision history are not reliable enough for PIT price adjustment. |

## Mandatory Consumer Behavior

Research, Validation, and Historical Replay must retain `DataTrustLevel`,
`AvailabilityPrecision`, provider limitations, and missing-data warnings.
Records classified as retrieval-time snapshots may be used only from their
stored `available_at`. Incomplete records remain visible and must never be
silently promoted to PIT-safe data.

October 16 correction: the earlier close+minute/calendar-midnight assumptions
and publication-linked numeric visibility are removed for new ingestion.
Legacy backdated rows are not rewritten or made reliable by this code change;
they need explicit raw-evidence audit/reconstruction before historical use.
The [real operational sample](operational-data-sample-2026-10-16.md) records
observed coverage, retained corrections and the open corporate-action mapping
gap. A successful provider response is not a normalization/readiness pass.

## Provider Evidence Adapters

| Provider evidence | Current trust | Availability precision | Permitted use | Explicit limitation |
|---|---|---|---|---|
| CNInfo disclosures via AKShare transport | MEDIUM | EXACT per parsed announcement timestamp | Filing-timing evidence from the record's `available_at` | Direct CNInfo parity, coverage, correction continuity, and raw filing capture are unverified. |
| Direct CNInfo disclosures and artifacts | MEDIUM | EXACT per official announcement timestamp | Direct filing metadata and content-hash evidence from `available_at`; artifact bytes are research evidence only | Public web contract, representative parity, historical coverage, URL-change behavior, and correction continuity remain unverified. |
| Yahoo Finance unadjusted daily bars | LOW | RETRIEVAL_TIME | Global exploratory research and provider comparison from ingestion time | Unofficial API, no authoritative historical availability, and unverified delisting/symbol/correction continuity. |
| Massive unadjusted US daily bars and action dates | LOW | RETRIEVAL_TIME | Optional independent calibration after authorized retrieval | No provider is trusted by default; permissions, corrections, identifier history, and continuity are unverified. |

These adapter defaults are deliberately weaker than any dataset-specific trust
that may be earned later. A scheduled provider contract check tests endpoint and
field health only; it cannot upgrade trust, coverage, continuity, consistency,
or PIT readiness.

Runtime readiness is classified as `USABLE`, `CAUTION`, or `UNSUITABLE` and is
calculated from coverage, trust, availability precision, revision support,
continuity, and provider consistency. The detailed source-policy baseline is in
`historical-coverage-matrix.md`; provider comparison rules are in
`provider-calibration.md`.

Tushare is implemented as the first secondary calibration provider. A dataset
remains `UNKNOWN` until an actual same-period comparison has been run; adapter
availability alone is not evidence of agreement. High-severity conflicts cap
readiness below `USABLE`.

The offline Yahoo calibration fixtures prove only deterministic contract
behavior. Even perfect fixture agreement is capped at `LOW/RETRIEVAL_TIME` and
does not change this matrix or PIT readiness.

## Upgrade Evidence

A dataset may move to a stronger class only after tests demonstrate historical
coverage, publication-time provenance, revision handling, delisted-security
retention, stable identifiers, and reproducible raw payload hashes. Provider
documentation alone is not sufficient evidence.

## Historical Validation Consumption Gate

A source classification does not by itself authorize historical validation.
Each `ReplayQuery` must declare the datasets it depends on. Validation request
creation requires an as-of-visible `USABLE` PIT readiness assessment for every
declared dataset, trust of at least `MEDIUM`, no critical missing fields, and no
incomplete or silently omitted replay sample. The manifest stores hashes of the
exact readiness assessments consumed.

This gate cannot prove that external data is correct. It prevents known weak,
missing, stale, or undeclared evidence from being treated as a credible
backtest. See `backtesting-data-assurance.md`.
