# Yahoo Daily-Bar Calibration

## Purpose

`WP-DATA-003` compares Yahoo research-grade daily bars with an independent
provider through one provider-neutral contract. It measures agreement; it does
not certify either provider and cannot promote PIT readiness.

## Contract

Every comparable snapshot records:

- market and canonical subject;
- timezone-aware calibration `as_of`;
- explicit `unadjusted` price basis;
- exchange-local session date;
- open, high, low, close, and volume;
- corporate-action types aligned to their effective session;
- input hash, trust level, availability precision, and limitations.

Adjusted, unknown-basis, and unadjusted series are never compared as
equivalent. OHLC values must be finite, positive, and internally consistent;
volume cannot be negative; duplicate sessions and future sessions are rejected.

## Attempt States

`provider_calibration_attempts` preserves all outcomes:

- `completed`: comparable unadjusted snapshots produced a persisted report;
- `unavailable`: a provider could not supply evidence, so no report exists;
- `incompatible`: both inputs exist but their price basis is not comparable.

Unavailable evidence is not converted to zero coverage, agreement, or an empty
successful snapshot. Completed reports, conflicts, confidence, and their
attempt record are committed in one SQLite transaction.

## Sources

Yahoo uses the existing unofficial chart evidence adapter. It remains
`LOW/RETRIEVAL_TIME` regardless of its consistency score. The adapter now emits
exchange-local session dates, explicit unadjusted basis, and dividend, split,
or capital-gain event types when the chart response contains them.

Massive is an optional US secondary. The implementation follows the official
[Custom Bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars),
[Dividends](https://massive.com/docs/rest/stocks/corporate-actions/dividends),
and [Splits](https://massive.com/docs/rest/stocks/corporate-actions/splits)
contracts. Aggregate requests force `adjusted=false`. The API key is read only
from `MASSIVE_API_KEY` and sent only in an Authorization header. Redirects and
pagination remain inside approved HTTPS paths on `api.massive.com`.

Massive also starts at `LOW/RETRIEVAL_TIME`. A successful comparison cannot
promote either provider. Permissions, continuity, corrections, symbol changes,
and delisted coverage still require longitudinal evidence.

## Deterministic Offline Run

Fixture runs require an explicit `--as-of`, so identical inputs produce the
same attempt hash and report path:

```bash
python scripts/run_yahoo_calibration.py \
  --market us --symbol MSFT \
  --start-date 2026-06-18 --end-date 2026-06-19 \
  --as-of 2026-06-20T12:00:00+00:00 \
  --yahoo-fixture tests/fixtures/yahoo_daily_bars.json \
  --secondary-fixture tests/fixtures/independent_daily_bars.json \
  --require-secondary
```

Fixtures verify contract behavior only. Their trust is capped at `LOW` and
their availability precision at `RETRIEVAL_TIME`.

## Optional Live Run

```bash
export MASSIVE_API_KEY="<your key>"
python scripts/run_yahoo_calibration.py \
  --market us --symbol MSFT \
  --start-date 2026-06-01 --end-date 2026-06-30 \
  --require-secondary
```

Without a key, the run persists an `unavailable` Massive attempt. With
`--require-secondary`, the command exits nonzero after writing the audit
record. No credential value, raw provider exception, order, trade, or execution
object is persisted or rendered.

## Interpretation

A high consistency score means the compared records agree within the canonical
representation. It does not prove historical completeness, publication-time
availability, correction continuity, delisted-symbol coverage, or suitability
for Historical Replay. Yahoo remains excluded from strict PIT promotion until
reviewed real evidence supports a separate governance decision.
