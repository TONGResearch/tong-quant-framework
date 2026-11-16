# Market-Value Evidence And Matching

Date: 2026-10-23. WP-LAUNCH-001 remains ready, not accepted.
Framework 0.8.0, schema 0.8.2, migration head 0010_portfolio_evidence_lineage.
PIT UNSUITABLE, production NOT_READY; execution/notifications disabled.

## Scope And Actual Outcome

Implement current market-value response capture, source-bound read contracts and
matching diagnostics. No valuation multiple, score or buy/sell decision is added.

The installed AKShare `stock_individual_info_em` maps price, total/float shares
and total/float market value but discards the original quote timestamp. Reviewed
primary implementation: [AKShare source](https://github.com/akfamily/akshare/blob/main/akshare/stock/stock_info_em.py)
and [official docs](https://akshare.akfamily.xyz/data/stock/stock.html).
Those mappings are useful engineering evidence, not independent validation of
Eastmoney's units, share-class scope or quote clock.

A fixed public HTTPS quote path is captured directly to retain the delivered
body and native clock field rather than guessing time from a transformed frame.
Direct Eastmoney and AKShare Eastmoney are the **same upstream**, not independent
calibration. Capability stays DEGRADED / LOW / RETRIEVAL_TIME, no historical
continuity. Supported symbol routing is conservatively SZSE/SSE equity prefixes;
BSE/funds/global instruments are not guessed into this endpoint.

## Architecture

1. `data.providers.eastmoney_market_values`: existing ProviderEvidenceAdapter,
   fixed URL/fields, no credentials, no arbitrary redirect, socket timeouts and
   bounded 64 KiB delivered body. No hidden retry. Transfer decoding is performed
   by the HTTP client; this is the delivered body, not raw TLS packets/headers.
2. Capture envelope: status, safe exception code, actual retrieval time, exact
   base64 body, normalization version and hashes. Labelled secrets in text and
   parsed JSON are rejected **before** encoding; opaque-secret detection is not
   guaranteed. HTTP headers/redirect target/credentials are not archived.
3. Provider-neutral atomic ingestion persists artifact/evidence/fingerprint/batch/
   limitations. Each attempt produces a capture record, including failed access.
   A capture-record count is never numeric coverage. No canonical bar/fact writes.
4. `data.market_value_inputs`: source-neutral typed inspection/snapshot with exact
   record hashes, subject/market/UTC cutoff and mutation checks. A SOURCE_BOUND
   failure means the failure capture is reproducible, not a verified price.
5. `data.market_value_reader`: one MarketDataService read snapshot; verify bytes,
   artifact ownership/metadata, exact evidence reconstruction, source clock and
   completed original evidence/artifact batches. Rejected data stays visible.
   Other providers need independent verifiers before using this contract.
6. `research.financial.market_value`: latest available capture only; a new failed,
   rejected or tied capture cannot select an older favorable observation. Total
   and float values/shares remain separate; exact price-times-share residuals are
   preserved without rounding away conflicts. Checked unadjusted daily bars supply
   date/price comparisons, not independent source or trading qualification.
7. Existing combined inspection CLI emits these diagnostics beside financial,
   trailing and technical inputs, at one cutoff. It does not create a queue,
   ResearchReport, InvestmentScore or a parallel report domain model. Official
   Financial consumption/sector admission remain future reviewed work.

## Semantics And Safety

- `f116` and `f117` are separate provider-total/float market-value observations;
  `f84`/`f85` are share-count mappings, not CNY share-capital amounts. Never replace
  total value with float value or infer missing shares from filing share capital.
- Native `f86` is retained as a **claimed**, unverified quote clock. Unknown,
  malformed or future claims block complete observations. It is not used as the
  record's original publication/availability time. Current snapshots become
  visible only at actual capture, never earlier historical quote dates.
- Unit/currency mappings, cross-listing, share-class/FX aggregation, treasury
  shares, buybacks, issue/split changes and correct company equity value need
  independent review. A provider-total figure is not automatically an admissible
  numerator for group parent earnings/book equity.
- Missing/boolean/nonfinite/negative/fractional share values, wrong symbol, float
  exceeding total, duplicate JSON keys and invalid response/schema remain visible
  as incomplete/inconsistent/invalid captures. HTTP errors are unavailable, not
  empty universe coverage or zero market value.
- Exact arithmetic agreement does not prove units or share-class scope. A same-day
  same-price match is not a verified close, security status, action clearance,
  source independence, freshness or historical continuity. Freshness remains
  UNASSESSED. PE/PB/PS and all authorization flags remain null/false.
- Prefetch response first, pin its actual time, then ingest. A request timestamp
  taken before a network call cannot admit the later response in strict PIT.
  Strict ingestion was not changed or disabled to make this capture work.

## Real Access And Audit

One initial bounded public probe returned HTTP 302 instead of JSON. The subsequent
completed capture returned HTTP 502. This does not establish whether the source,
gateway or network path is responsible; no numeric quote is claimed.

- Completed batch: `6598e036-f398-4cb8-b232-c92674ed2344`.
- Capture availability: 2026-10-23T15:36:22.848322Z.
- Capture-envelope SHA-256:
  `0412305271ce62ebbec5e7c41a107442f3b72f2439c066ed5dc52ad3bd2d9017`.
- Evidence: `700e13561623da3d3af866ccccb69b703a46e1222955e986a819dbd8e087eb0d`.
- Reconstructed source binding passes; status UNAVAILABLE / HTTP_502, all values
  absent. Earlier 14:47:26Z cutoff cannot see this attempt.
- Two combined read-only calls at 15:38:11Z agree, review hash
  `bfc9f097abc1901a66524ec9b0335d8acb2c9e116bfc41f6cb4ab59b28544e5a`.
  Earlier financial/trailing observations remain intact; technical confluence
  stays CONFLICTED. No new canonical data or investment conclusion is produced.
- Registered bytes: 17/17 verified; audit hash
  `a5812a28885b03ed1ccd072465684a82cc44d757cb5bd809ff8c7dc55f0c5425`.
  This verifies stored bytes, not source truth or encrypted recovery. The new
  ignored envelope is outside earlier encrypted backup snapshots.

The first CLI attempt was blocked before persistence by the pre-request/post-
capture cutoff race. Prefetch/pinned ingestion fixes it without weakening PIT.
Tests also exposed and repaired scanning JSON strings only as text before base64;
structured credential-key checks now run before encoding. Tests use synthetic
noncredentials only. No Tushare, trading, broker, Portfolio or Notification change.

## Verification

- Full Pytest: **1729 passed / 6 skipped**, 58.25 seconds; 52 new cases.
  New focused suite: 52 passed. Six live provider/notification tests remain opt-in.
- Ruff passes; mypy passes across 251 files; governance passes 106 checks;
  `git diff --check` passes. No database/schema or disabled-default change.
- Tests cover routes, response limits, structured credential filtering, failed
  HTTP/invalid JSON/duplicate fields, identity/count/value/clock checks, exact
  residuals, missing/stale/adjusted/future bars, record mutation, byte/metadata/
  batch tampering, cutoff prefetched ingestion, idempotency, latest failures/ties,
  no old-data fallback and deterministic combined CLI without database writes.
- Software tests use synthetic quotes, not evidence of real endpoint coverage,
  independent units/clock/share-class validation or strategy performance.
- Real status remains UNAVAILABLE / HTTP_502. Failed capture bytes are verified
  17/17, while the associated numerical values and valuation multiples are absent.

## Operations And Next Work

Capture explicitly into an existing research database (exit 2 means missing/
unavailable/invalid observation; no default automated capture or network test):

```bash
.venv/bin/python scripts/capture_market_value.py --symbol 002624 \
  --database data/processed/technical-request-20261020.sqlite3 \
  --artifact-root data/processed/raw/provider-artifacts
```

The existing `inspect_candidate_inputs.py` needs no new flag to read retained
market-value captures. It still requires an explicit `--as-of`; it never performs
network requests. No schema/table migration: existing evidence, artifact, batch
and warning tables are reused. Capture/input/diagnostic versions are centralized.
No commit/push or readiness promotion.

Next: functioning permitted numeric source, independent units/clock/class/FX/
action evidence, explicit freshness and sector valuation admission; then official
Financial/ResearchContext decision consumption and real strategy validation.
Do not paper over source unavailability with guessed shares, old quotes or a
"verified" provider-name label. Historical size research still needs a historical
eligible universe and dated market-cap coverage, not this current snapshot.
