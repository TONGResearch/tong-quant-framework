# Tong Quant Multi-Provider Architecture

Status: provider-neutral evidence foundation implemented; provider rollout ongoing

Framework version: 0.8.0

This document defines the next-generation data-provider architecture for Tong
Quant. It does not implement new providers, trading, paper trading, broker
integration, order generation, or asset allocation.

## Decision

Tushare integration is complete from an engineering perspective. Current
Tushare limitations are external account-tier constraints rather than framework
defects. Tushare remains an optional China-market calibration provider and must
not block future data-platform progress.

Tong Quant should evolve from an AKShare/Tushare-centered data platform into a
provider-independent research data platform.

## Evidence-First Provider Policy

No provider is trusted by default.

Tong Quant consumes evidence, not providers. Every provider and every dataset
must be evaluated independently for:

- Trust
- Coverage
- Availability precision
- Historical continuity
- Cross-provider consistency

A provider brand, paid account, official API, open-source package, or prior
successful ingestion does not automatically upgrade data trust. Trust upgrades
must be earned by dataset-specific evidence and preserved as auditable metadata.

## Provider Priorities

| Priority | Provider | Primary role | Markets | Planned status |
|---:|---|---|---|---|
| 1 | Massive / Polygon | US equity market data and reference data | US | Future primary US provider |
| 2 | Yahoo Finance | Research-grade global market data | Global | Evidence adapter implemented; live continuity unverified |
| 3 | Finnhub | News, filings, fundamentals, events | Global | Future AI/research input provider |
| 4 | CNInfo | Authoritative China disclosure timestamps and filings | China A | Direct metadata/artifact adapter implemented; representative parity and continuity unverified |
| 5 | Tushare | Optional calibration provider | China A | Frozen optional provider |
| Existing | AKShare | China A open-source source and diagnostics | China A | Existing primary open source source |

## Non-Goals

- No Execution Engine work.
- No Paper Trading work.
- No Broker integration.
- No Orders, Trades, Fills, or Live Trading.
- No Portfolio Optimization or Asset Allocation.
- No trading-signal generation.
- No weakening of PIT safety to make a provider look usable.

## Core Principles

1. Provider independence has higher priority than provider-specific convenience.
2. No provider is trusted by default.
3. Every provider adapter must expose source limitations explicitly.
4. `DataTrustLevel` and `AvailabilityPrecision` remain first-class metadata.
5. Provider agreement can improve confidence but never proves PIT safety alone.
6. Missing data, permission failures, and API changes must be visible artifacts.
7. Calibration must fail closed when required evidence is unavailable.
8. Research, Validation, Historical Replay, and future Portfolio layers consume
   normalized data contracts, never provider-native payloads.

## Target Provider Stack

```text
Provider Adapter
  -> Raw Response Capture
  -> Capability Detection
  -> Normalization
  -> Data Quality Checks
  -> PIT Availability Annotation
  -> ProviderCalibration
  -> SQLite / Future Storage
  -> Research / Validation / Replay
```

Provider-specific SDKs and HTTP clients stay behind adapter boundaries. No
strategy, research module, validation module, portfolio module, or notification
module should call a provider SDK directly.

The implemented `ProviderEvidenceAdapter` contract now carries capability,
market, evidence timestamps, raw hash, trust, availability precision, and
limitations through one ingestion service. Provider-native payloads are stored
as auditable evidence and are not promoted into existing canonical research
models without a dataset-specific normalizer and readiness review.

CNInfo now has two explicit evidence identities: `cninfo_via_akshare` and
`cninfo_direct`. Direct metadata and raw artifact capture are implemented, but
trust remains conservative until representative parity, coverage, correction
continuity, and contract history are reviewed. Yahoo uses the unofficial chart
interface and is intentionally `LOW` trust with `RETRIEVAL_TIME` availability.

## Shared Provider Contracts

Future providers should conform to the existing provider direction rather than
introducing separate data paths.

Required contracts:

- Capability report
- Dataset availability report
- Provider limitation records
- Raw response hash
- Normalized dataset records
- Trust-level assignment
- Availability-precision assignment
- Calibration snapshot support where comparable datasets exist

Provider adapters should answer four questions before their data is consumed:

1. Is this endpoint accessible with current credentials?
2. What historical range and field coverage is available?
3. What point-in-time availability can be defended?
4. What provider limitations must follow the data downstream?

## Provider Roles

### Massive / Polygon

Primary future use:

- US equity OHLCV bars
- US reference data
- Corporate actions
- Market status and calendars
- Potential future real-time or delayed market data

Expected trust posture:

- `DataTrustLevel.HIGH` for paid historical bars and reference data after
  calibration.
- `AvailabilityPrecision.DATE_ONLY` or better when provider timestamps support it.
- `UNKNOWN` until real capability and coverage reports are generated.

Design notes:

- Use provider pagination and cursor metadata as part of raw response hashing.
- Treat adjusted prices and corporate actions as separate datasets.
- Strict PIT mode must not use provider-adjusted bars unless the adjustment
  factors are independently timestamped and replayable.

### Yahoo Finance

Primary future use:

- Global research-grade price history
- Basic fundamentals where available
- Low-cost cross-checks for global equities
- Initial market coverage for US, Hong Kong, Malaysia, and other markets

Expected trust posture:

- Usually `DataTrustLevel.MEDIUM` or `LOW`, depending on dataset.
- Often `AvailabilityPrecision.RETRIEVAL_TIME` unless a stronger timestamp is
  demonstrated.

Design notes:

- Yahoo Finance should be treated as a research and fallback provider, not as an
  authoritative historical-replay source.
- Delistings, restatements, symbol changes, and corporate-action history require
  explicit limitations.
- Yahoo-derived evidence should not by itself upgrade PIT readiness to `USABLE`.

### Finnhub

Primary future use:

- News
- Filings
- Earnings calendar and events
- Basic fundamentals
- Company profile and alternative research inputs

Expected trust posture:

- `DataTrustLevel.MEDIUM` to `HIGH` for timestamped news and filings after
  verification.
- `AvailabilityPrecision.EXACT` may be possible for timestamped news/events.
- Fundamentals remain `UNKNOWN` until publication/revision behavior is tested.

Design notes:

- Finnhub should feed Research and AI Engine inputs through normalized event and
  filing contracts.
- AI Engine may summarize Finnhub-derived documents, but must not directly make
  trades.
- News and filings must preserve source timestamp, retrieval timestamp, URL, raw
  hash, and provider limitations.

### CNInfo

Primary future use:

- China A authoritative announcements
- Actual disclosure timestamps
- Filing URLs and raw document references
- Revision and correction announcement evidence

Expected trust posture:

- Potentially `DataTrustLevel.HIGH` or `VERIFIED` for China disclosure timing
  after reproducible ingestion is implemented.
- `AvailabilityPrecision.EXACT` if exact publication timestamps are captured and
  verified.

Design notes:

- CNInfo should become the authoritative source for China filing availability.
- CNInfo can reduce AKShare/Tushare publication-date uncertainty, but cannot
  repair price, universe, or corporate-action gaps by itself.
- Raw filing evidence should be referenced by immutable URL, timestamp, hash, and
  downloaded artifact metadata.

### Tushare

Current role:

- Optional China A calibration provider.
- Engineering-complete capability detection.
- External account-tier constraints currently prevent dataset availability.

Policy:

- Do not build future architecture around Tushare availability.
- Do not require a Tushare account upgrade for the roadmap to proceed.
- Keep fail-closed behavior when Tushare is explicitly required.
- Keep permission limitations visible in generated capability reports.

## Dataset Ownership Matrix

| Dataset family | Preferred future source | Secondary source | Current fallback | PIT caution |
|---|---|---|---|---|
| China daily bars | AKShare initially | Tushare optional | None | Adjusted bars require factor history |
| China disclosures | CNInfo | AKShare CNInfo-derived evidence | Tushare optional | Exact publication availability is critical |
| China universe/status | AKShare initially | Tushare optional | CNInfo events where relevant | Delisted/ST/suspended securities must remain visible |
| US daily bars | Massive / Polygon | Yahoo Finance | None | Corporate actions must be replayable |
| Global daily bars | Yahoo Finance | Massive/Finnhub where covered | None | Research-grade only until calibrated |
| Global news/events | Finnhub | Provider-specific feeds | None | Event timestamps must be preserved |
| Global fundamentals | Finnhub/Yahoo initially | Massive where available | None | Publication and revision behavior must be audited |
| Index constituents | Massive for US, provider-specific for China/global | Yahoo/Tushare where available | None | Historical membership requires effective dates |

## Calibration Strategy

ProviderCalibration should become N-provider capable without changing its core
semantics.

Current model:

```text
Primary Provider + Secondary Provider -> Consistency Report
```

Target model:

```text
Dataset Calibration Group
  provider_a snapshot
  provider_b snapshot
  provider_c snapshot
  ...
  -> pairwise comparisons
  -> consensus summary
  -> conflict registry
  -> dataset confidence assessment
```

Near-term implementation should preserve the existing two-provider path and add
multi-provider grouping only when a second non-Tushare provider exists.

Calibration outputs must continue to include:

- Coverage comparison
- Consistency score
- Conflict analysis
- Critical conflict count
- Dataset confidence
- Provider limitations
- Data trust reassessment
- PIT readiness impact

## PIT Safety Rules

Every provider must annotate:

- `published_at`
- `available_at`
- `retrieved_at`
- `effective_from`
- `effective_to`
- `source`
- `provider_dataset`
- `raw_data_hash`
- `DataTrustLevel`
- `AvailabilityPrecision`

If a provider cannot support one of these fields, the missing field must become a
limitation and reduce PIT readiness. It must not be silently inferred.

Strict PIT mode must reject:

- Data with `available_at > decision_as_of`
- Future-adjusted prices without dated adjustment-factor evidence
- Current universe snapshots used as historical universes
- Restated fundamentals presented as original filings
- Delisted, suspended, or status-changed instruments silently dropped from samples

## Capability Detection

Each provider should implement a capability detector before full ingestion.

Required detector outputs:

- Credential status
- Endpoint status
- Dataset capability status
- Required account tier or known pricing constraint
- Sanitized provider error
- Rows observed
- Historical coverage warning
- Rate-limit warning
- Provider API version if available

Capability detection is diagnostic evidence. It does not prove historical
coverage or PIT readiness.

## Storage Impact

The current schema already reserves many provider and calibration concepts.
Future work should prefer additive migrations.

Likely future additions:

- `provider_capability_reports`
- `provider_endpoint_capabilities`
- `provider_dataset_capabilities`
- `provider_raw_payloads`
- `provider_dataset_versions`
- `provider_coverage_snapshots`
- Optional `provider_calibration_groups` for N-provider comparisons

No schema rewrite is recommended before the next provider adapter is designed.

## Recommended Sequencing

### Phase MP-1: Provider Registry Design

- Define provider metadata objects.
- Classify providers by market, dataset family, trust policy, credential mode,
  and PIT capability.
- No network integration required.

### Phase MP-2: Massive / Polygon Design

- Design US equity market-data adapter contracts.
- Define bar, reference, corporate-action, and calendar datasets.
- Decide how adjusted and unadjusted prices are represented.

### Phase MP-3: Yahoo Finance Evidence Foundation (implemented)

- Define research-grade global provider boundaries.
- Explicitly limit Yahoo usage in Historical Replay until calibrated.
- Map supported markets: US, Hong Kong, Malaysia, and broad global equities.

### Phase MP-4: Finnhub Design

- Define news, filings, events, and fundamentals contracts.
- Connect to Research/AI inputs only through normalized artifacts.
- Preserve no-trading-decision boundary.

### Phase MP-5: CNInfo Evidence Foundation (implemented)

- Preserve direct and AKShare-transport provenance independently.
- Capture official timestamps, URLs, raw filing hashes, and relation evidence.
- Accumulate representative parity and continuity before any trust reassessment.

### Phase MP-6: Multi-Provider Calibration Upgrade

- Extend ProviderCalibration from pairwise to grouped comparisons.
- Keep the existing pairwise coordinator for backward compatibility.
- Add consensus and conflict aggregation only after at least three providers are
  producing comparable datasets.

## Readiness Gate Before Implementation

Before implementing any provider, require:

- Provider scope document
- Dataset mapping
- PIT availability assumptions
- Trust-level default policy
- Capability detector design
- Credential storage policy
- Rate-limit and retry policy
- Raw-response hashing policy
- Tests with fake clients
- No broker/order/execution dependencies

## Current Roadmap Recommendation

Do not wait for Tushare account upgrades. The next design milestone should be:

```text
MP-1 Provider Registry Design
-> MP-2 Massive / Polygon US Equity Provider Design
-> MP-3 Yahoo Finance Global Research Provider Design
-> MP-4 Finnhub News/Filings Provider Design
-> MP-5 CNInfo China Disclosure Provider Design
```

The provider-neutral ingestion contract, direct/transported CNInfo evidence,
Yahoo evidence adapter, content-addressed artifact store, and scheduled contract
monitor are now implemented. The next provider work should calibrate real
coverage and continuity; it must not assume that successful contract probes
grant higher trust or PIT readiness.
