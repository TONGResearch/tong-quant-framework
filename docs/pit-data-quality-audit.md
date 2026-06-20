# PIT Data Remediation Audit

## Scope

This audit covers A-share lifecycle history, universe membership, fundamental
publication timing, provider consistency, and replay readiness. It adds no
Paper Trading, Execution, Broker, Asset Allocation, or live-trading behavior.

The inspected local provider runtime is AKShare 1.18.64. Capability statements
below are based on the adapter endpoints and installed provider implementation,
not on assumptions about data that might exist elsewhere.

## Findings And Remediation

### Security Lifecycle

- Daily suspension and expected/actual resumption evidence can be collected from
  `stock_tfp_em`.
- Shenzhen dated short-name changes can identify ST entry and exit events.
- Exchange delisting records produce explicit delisted events in addition to the
  existing status history.
- True relisting history is not reliably available and remains unsupported.
- Shanghai and Beijing historical ST entry/exit coverage require another source.

Lifecycle events are append-only and preserve effective date, retrieval-safe
availability, source, raw hash, precision, and trust. Timeline quality scoring
measures event-type coverage, temporal precision, source diversity, and
contradictions. Missing events remain visible as warnings.

### Historical Universe

- CSI300 (`000300`), CSI500 (`000905`), and CSI1000 (`000852`) are explicitly
  reserved and validated by the adapter.
- The CSI endpoint supplies current constituents, not a complete historical
  entry/exit ledger.
- Every retrieval is therefore stored as a dated snapshot.
- Current A-share universe ingestion now also persists a `market:china_a`
  membership snapshot.

Repeated snapshots improve forward coverage only. They do not reconstruct dates
before collection began. Membership confidence scores snapshot coverage,
temporal precision, provider diversity, and verified entry/exit history.

### Fundamental Publication Accuracy

- `stock_yysj_em` supplies actual disclosure dates from 2008-era reporting
  periods onward, but only at date precision.
- CNInfo disclosure search supplies announcement timestamps and report titles.
- Report periods are parsed conservatively from annual, half-year, first-quarter,
  and third-quarter titles.
- Multiple announcements for one period are retained as ordered revisions.
- Unknown titles are excluded from normalized publication evidence rather than
  guessed.

Financial facts may use the latest publication evidence visible at ingestion.
Current revised values are never copied backward into earlier publication
events when the previous reported value is unavailable.

### Multi-Provider Calibration

`ProviderCalibrationEngine` compares normalized snapshots using stable record
keys, key overlap, and requested field matches. Reports retain provider counts,
provider-only records, field scores, limitations, deterministic hashes, and a
derived trust level. Tushare is now implemented as the first secondary adapter,
but no dataset is upgraded until a real same-period comparison succeeds.

### PIT Readiness

Readiness now produces:

- `usable`: score at least 80, required coverage and trust pass, no critical gap.
- `caution`: score from 50 to below 80; visible to replay with explicit warning.
- `unsuitable`: score below 50 or evidence too weak for historical use.

The score combines coverage, trust, availability precision, revision support,
timeline continuity, and provider consistency. Missing secondary-provider
evidence is explicit and receives a neutral-but-limited component rather than a
silent pass.

## Current Maturity

Publication timing is materially improved when CNInfo evidence exists. Lifecycle
and universe data are now auditable and forward-accumulating, but national ST
history, true relisting history, and complete historical CSI entries/exits remain
the largest gaps. Research and Validation must continue reading classification,
score components, assumptions, and provider limitations together.
