# BSE Price Source Repair: October 20

## What Is Established

No provider can guarantee absolute correctness. Tong's requirement is enforced
as retained source evidence, explicit data-quality limitations and refusal to
promote unverified observations into investing or execution authority. A SHA256
match proves retained byte identity, not that the provider's values are true.

The original 920982 acquisition route had two independent failures: Eastmoney
ConnectionError and Tencent missing-day payload. The previous 920-prefix
Shanghai routing bug was fixed earlier. This slice finds a reachable Sina path;
the earlier absence of a Sina path was an integration-coverage gap, not proof
that the stock's history was unavailable everywhere.

Real bounded probes on October 20 UTC:

| Requested symbol | Main source | Tencent | Sina SDK |
|---|---|---|---|
| 920982, 11:21:42-46 | ConnectionError | bj920982, KeyError/day | bj920982, 674 rows |
| 832982, 11:21:52-56 | ConnectionError | bj832982, KeyError/day | JSONDecodeError |

The old symbol is evidenced by the issuer's
[BSE filing under 832982](https://www.bse.cn/disclosure/2025/2025-06-26/eb3cd1e843434853b6fa2dd84ca1d20c.pdf).
New-code issuer documents and linked broker code-mapping disclosures corroborate
the code-history question, but no authoritative dated alias ledger was captured.
The BSE code-mapping page was unavailable during this check. No old-code series
was substituted, merged or relabeled; no migration date was guessed.

The [AKShare source documentation](https://akshare.akfamily.xyz/data/stock/stock.html)
describes the Sina daily interface and volume-in-shares/amount-in-yuan units.
Documentation is a provider claim, not independent unit verification.
Installed SDK: AKShare 1.18.64, mini-racer 0.14.1, already in native locks.
No dependency/environment upgrade was performed. The decoder's content hash is
retained per record because its SDK-internal import remains a maintenance risk.

## Why The SDK Result Is Not Used As Canonical Data

Installed stock_zh_a_daily merges prices with outstanding shares, forward-fills
the merged frame, rounds OHLC and drops repeated rows. These steps can affect
dates or prices and therefore are not silently accepted for Tong's strict data
path. Native SDK access is diagnostic only; optional --include-sina preserves
the original two-probe default and subprocess timeout protection.

The new SinaBsePriceObservationAdapter instead downloads the fixed official
Sina raw price URL once with finite timeout, no redirects and a 2 MiB limit.
It parses only a symbol-bound KLC_K2/KLC_KL data assignment plus optional comment;
provider JavaScript is never evaluated. Only the installed fixed SDK decoder
runs, with time/memory limits. There is no share-count merge, fill, extra rounding,
deduplication or corporate-action adjustment. Invalid selected rows reject the
capture instead of being repaired or discarded. Duplicate dates fail closed.

Separate LOW/RETRIEVAL_TIME evidence enters ProviderNeutralIngestionService and
ProviderArtifactStore. It does not enter daily_bars, source approval, research
scores or validation eligibility. The existing AKShare canonical source allowlist
is unchanged. Canonical-bar authority is explicitly false on every observation.

## Actual Capture And Reproduction

```bash
.venv/bin/python scripts/ingest_data.py \
  --database data/processed/technical-request-20261020.sqlite3 \
  --timeout-seconds 20 \
  sina-bse-snapshot 920982 20240101 20261019
```

Exit 2 intentionally means partial evidence, not completed price qualification.
Decoded raw count 786; selected 674, January 2 2024 through October 19 2026;
112 outside query bounds remain in the retained raw response. The common
ingestion result labels them rejected; this is range selection, not 112 bad
prices or a historical-coverage percentage. No verified session denominator.

- Batch: c47cd157-9adc-4c4d-b071-14eba58657df.
- Provider/dataset: sina_via_akshare_decoder / bse_daily_price_observations.
- Capture time: 2026-10-20T11:27:09.334413Z.
- Artifact: 3e440911b0c6c6c6f71ca483978fc72e6af83926d399f8072c0b7865869c6bab.
- Raw SHA256: f709ebd3cd9cf880db0c59aa59f37f8e209d8250b70dbc8a807f94ab9b7475db.
- Model: sina-native-price-observations-v1.

The command captures first and admits the immutable batch with its actual
retrieval cutoff. Initial development checks correctly rejected an older
pre-fetch cutoff; the fix rebinds the admission request, not data availability
or the PIT guard. Parser development also established the KLC_K2 assignment and
trailing comment format before successful persistence; failed attempts did not
publish observations. No raw exception text is rendered by the ingestion CLI.

The artifact audit verifies 10/10 registered files, report hash
4abbd40ee2dfc523c301f5f5dbe75530cc20b675b4ee4c050a927f93c016e6cf.
New data remains ignored by Git and outside earlier encrypted backups.
Offline reconstruction from the retained response reproduced all 674 stored
evidence records exactly, including evidence identities and full content;
this tests reconstruction, not source truth. An initial local inspection helper
passed a string where SQLiteStore requires Path; the corrected read-only helper
completed without changing source or stored data.

## Outstanding Accuracy Checks

1. Compare overlapping OHLCV and amount with an independently obtained source
   such as a Guojin historical export. Comparing the Sina SDK with Sina raw data
   is not independent provider calibration. Provider consistency remains unknown.
2. Verify volume/amount units and unadjusted-price basis against dated source
   definitions and corporate actions; reject adjusted/unadjusted comparisons.
3. Capture authoritative code mapping/effective dates without automatic alias
   guessing. Current retrieval-time history cannot prove original publication.
4. Review listing, suspension/ST history, exchange sessions and gaps. A positive
   observation count cannot certify historical continuity or full coverage.
5. Only after these reviews decide whether a canonical adapter is warranted;
   do not merely expand the old source allowlist to clear a gate.

Framework/schema versions unchanged. PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled, live orders false. No Paper, Broker, Portfolio,
Notification or execution change. No commit or push. No accuracy guarantee or
research buy/sell conclusion is claimed.

## Verification

Full suite: **1392 passed / 6 skipped**, 48.79 seconds; 24 added cases.
Ruff, mypy (242 source/script files), governance (99 checks), and
git diff --check pass. Post-documentation governance tests pass 7 cases.
Focused provider/CLI tests pass 75 cases. Coverage includes data-only decoder
parsing, symbol identity, size/CPU limits, invalid numeric/OHLC/duplicate/intraday
rejection, original byte retention, idempotent persistence, no canonical bars,
future-retrieval refusal and proper capture-time admission in the CLI.
Synthetic tests and raw reconstruction do not prove prices correct or independent.
