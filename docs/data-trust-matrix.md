# AKShare Data Trust Matrix

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

No currently integrated AKShare dataset qualifies as fully PIT-safe without a
documented assumption or limitation.

## Matrix

| Dataset | AKShare endpoint | Classification | Trust | Historical-validation rule |
|---|---|---|---|---|
| A-share unadjusted daily bars | `stock_zh_a_hist`, Tencent fallback | Partially reliable | MEDIUM | Allowed only unadjusted; close+1 minute availability is an internal assumption and later corrections are not reconstructed. |
| A-share adjusted daily bars | Same endpoints with qfq/hfq | Unsuitable for historical validation | LOW | Rejected in strict PIT mode until dated adjustment factors can be reconstructed as known at each decision time. |
| China index daily bars | `index_zh_a_hist`, Tencent fallback | Partially reliable | MEDIUM | Price history is usable with the same assumed close availability and correction warning. |
| Trading calendar | `tool_trade_date_hist_sina` | Partially reliable | MEDIUM | Useful as an operational calendar; emergency closures and historical source corrections are not versioned. |
| Company information | `stock_individual_info_em`, CNInfo fallback | Retrieval-time snapshot only | LOW | Never use as historical company state before `retrieved_at`. |
| Current A-share universe | `stock_zh_a_spot_em`, code-name fallback | Retrieval-time snapshot only | LOW | Must not reconstruct a historical listed or tradable universe. |
| Financial statements | THS income, balance-sheet, cash-flow endpoints | Retrieval-time snapshot only | LOW | Facts are visible only from ingestion time; historical publication and revision timing are unavailable. Unsuitable for pre-ingestion validation. |
| Current ST status | `stock_zh_a_st_em` | Retrieval-time snapshot only | LOW | Preserves observed current ST membership only; cannot infer earlier ST intervals. |
| Current suspension status | `stock_zh_a_stop_em` | Retrieval-time snapshot only | LOW | Preserves observed current suspension only; cannot reconstruct full suspension history. |
| Delisted securities | Shanghai and Shenzhen delisting endpoints | Partially reliable | MEDIUM | Effective delisting dates may be useful, but announcement availability and complete exchange coverage require verification. |
| CSI index membership | `index_stock_cons_csindex` | Retrieval-time snapshot only | MEDIUM | Effective dates are retained when supplied, but missing exits and retrieval-time availability prevent survivorship-safe historical membership. |
| Corporate actions | `stock_fhps_detail_em` | Partially reliable | MEDIUM content / LOW timing | Effective dates are useful for audit; announcement availability and revision history are not reliable enough for PIT price adjustment. |

## Mandatory Consumer Behavior

Research, Validation, and Historical Replay must retain `DataTrustLevel`,
`AvailabilityPrecision`, provider limitations, and missing-data warnings.
Records classified as retrieval-time snapshots may be used only from their
stored `available_at`. Incomplete records remain visible and must never be
silently promoted to PIT-safe data.

## Upgrade Evidence

A dataset may move to a stronger class only after tests demonstrate historical
coverage, publication-time provenance, revision handling, delisted-security
retention, stable identifiers, and reproducible raw payload hashes. Provider
documentation alone is not sufficient evidence.
