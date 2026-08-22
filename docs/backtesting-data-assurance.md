# Backtesting And Data Assurance

## Scope

Tong Quant separates two different forms of testing:

- **Historical backtesting** evaluates past Research outputs with point-in-time
  data. It does not simulate orders or claim that a stop price was fillable.
- **Gray rollout testing** is a future operational sequence: shadow mode,
  isolated Paper Trading, and then tightly controlled semi-automatic capital.
  None of those execution-side stages is currently implemented.

The framework cannot guarantee that an external source is always correct.
Instead, it fails closed unless the evidence needed for a specific historical
validation is sufficiently attributable, complete, timely, continuous, and
internally consistent.

## Historical Validation Storyboard

```text
Versioned research hypothesis
        |
Pre-registered outcome and horizon
        |
ReplayQuery(decision_as_of, outcome_as_of, required inputs and datasets)
        |
PIT reconstruction with unadjusted visible-at-the-time evidence
        |
Replay data-quality gate
        |
Historical -> Walk-Forward -> Final OOS -> Robustness and ablation
        |
ValidationReport with research quality and replay quality kept separate
```

The decision context can contain only evidence with
`available_at <= decision_as_of`. Outcome observations are reconstructed only
at `outcome_as_of` and never enter the earlier research context. Delisted, ST,
suspended, missing, low-trust, and provider-limited records remain visible.

## Replay Data-Quality Gate

`ReplayQuery` must declare both:

- `required_inputs`: the decision and outcome artifacts needed by the sample;
- `readiness_datasets`: every underlying dataset whose PIT readiness must be
  authenticated for that run.

The query cannot lower its trust requirement below `MEDIUM` and cannot hide
incomplete samples. `ReplayConfidence` records a boolean
`validation_eligible` and explicit `blocking_reasons`. Validation request
creation fails closed when any of these conditions exists:

- a declared dataset has no PIT readiness assessment visible at replay
  generation time;
- a declared dataset is `CAUTION` or `UNSUITABLE` rather than `USABLE`;
- a dataset has missing critical fields;
- row or dataset trust is below the query's minimum;
- a required sample input is missing;
- any sample would otherwise be silently omitted from Validation.

ST, suspension, delisting, and other lifecycle preservation flags are warnings,
not missing data. Keeping those securities is required to prevent survivorship
bias. Each manifest freezes a hash of every consumed readiness assessment.

## Evidence Hierarchy

Provider reputation never grants trust automatically. Dataset evidence is
evaluated independently.

1. **Authoritative primary evidence**
   - China disclosures: direct CNInfo or official exchange artifacts with
     original bytes, timestamps, hashes, and correction history.
   - Exchange calendars, lifecycle notices, and corporate actions should come
     from the responsible exchange or disclosure venue where accessible.
2. **Structured provider evidence**
   - Tushare, Massive, or a future licensed source may normalize and enrich
     evidence, but permissions, coverage, adjustments, and revisions are still
     measured per dataset.
3. **Aggregation and research evidence**
   - AKShare transports public-source data and must retain the original source
     identity. Its live snapshot cannot be relabeled as historical truth.
   - Yahoo remains `LOW/RETRIEVAL_TIME` research evidence and needs an
     independent comparison before historical use.
4. **News and AI-derived evidence**
   - Store publisher, publication time, retrieval time, canonical URL, raw
     hash, corrections, and model version. AI summaries never replace the
     source artifact and never upgrade source trust.

Official references supporting the source classification include:

- CNInfo describes itself as the Shenzhen Stock Exchange statutory disclosure
  platform: <https://www.cninfo.com.cn/new/index?lang=zh>
- AKShare states that it collects public-source data for research and documents
  concrete data risks: <https://akshare.akfamily.xyz/introduction.html> and
  <https://akshare.akfamily.xyz/data_tips.html>
- Tushare documents endpoint-specific permission and point requirements:
  <https://tushare.pro/document/1?doc_id=108>
- Massive documents unadjusted stock files and its adjustment behavior:
  <https://massive.com/docs/flat-files/stocks/overview>

These descriptions are provenance evidence, not proof of historical accuracy.

## Dataset Acceptance Evidence

A dataset can be proposed as `USABLE` only after review of:

- raw response or artifact hash and provider provenance;
- coverage and missing-field measurements;
- exact/date-only/estimated/retrieval-time availability precision;
- revision and correction preservation;
- historical continuity, including scheduled missing periods;
- lifecycle and universe coverage, including delisted securities;
- independent-provider consistency and a persistent conflict registry;
- deterministic normalization and schema-contract monitoring.

Contract health, provider login, payment tier, or one successful comparison
cannot promote trust. Promotions remain human-reviewed and versioned.

## Current Readiness

Historical Replay and Validation machinery are implemented, but the current
project-wide PIT classification is `UNSUITABLE`. The new gate therefore blocks
credible backtest requests from current production evidence. Synthetic test
fixtures prove software behavior only and cannot support a performance claim.

The active engineering task remains `WP-EVIDENCE-001`: retain and review at
least 84 days of representative provider evidence, account for missing periods,
and reassess each critical replay dataset without automatic promotion.

## Future Gray Rollout

After data, research, validation, portfolio/risk, and Paper Trading gates are
separately approved, operational rollout should proceed in this order:

```text
Shadow decisions with no orders
  -> isolated Paper Trading
  -> broker sandbox and reconciliation
  -> semi-automatic minimum capital with manual approval
  -> bounded automation only after a separate audit
```

Every stage requires pre-defined success and stop criteria, an immutable
decision journal, stale-data rejection, kill switches, and market-specific
fill analysis. Current Execution remains disabled.
