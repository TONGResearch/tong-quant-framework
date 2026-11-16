# Draft Source-Defined Bank Input Coverage

## What Changed

WP-LAUNCH-001: explicit source-defined bank input questions now consume the
existing immutable ReviewedDocumentResearchInput. A bounded versioned plan pins
the instrument/market/document, exact manual evidence/envelope hash and original
PDF hash. No names, amounts or Yahoo proximity select a mapping automatically.
The plan is **DRAFT_NOT_ADMITTED**, not a scoring methodology or canonical alias.

Each monetary question declares the exact original label, statement, Group/Bank
scope, flow dates, current/comparative column, currency/unit, physical/printed
page labels and restatement annotation. The checker reports a match only as
MATCHED_UNQUALIFIED_ANNOTATIONS. These are manual source annotations, not machine
PDF verification, accounting truth, issuer qualification or a complete bank model.
Expected numeric values, weights and scoring thresholds are not supported.

Different states stay separate:

- MISSING_REVIEWED_ROW means the current selected review lacks that row, not that
  the issuer never disclosed it. Never borrow it from an older review edition.
- ANNOTATION_MISMATCH retains the observed row and differing fields, not an alias.
- UNRESOLVED_VALUE cannot become zero or a favorable missing result.
- RATIO_CONTRACT_REQUIRED identifies a still-unsupported source measurement
  contract, not an absent disclosure or generic monetary metric.
- EXTERNAL_EVIDENCE_REQUIRED names another unassessed dependency, not acceptance.
- Bad/missing sources, changed review/PDF pins or wrong contexts block all checks.

Plan availability must be no later than the requested cutoff and no earlier
than its exact pinned review recording. These chronology checks prevent obvious
backdating, but a local plan timestamp is not authenticated historical publication.
Actual UTC instants govern comparisons. Negative amounts do not fail a company;
no average, coverage percentage, confidence or investment score is generated.

## Existing Paths, No New Engine

The existing global technical CLI accepts `--bank-document-plan` only with explicit
HK/MY reviewed filing and bank context. Missing/oversized/symlink/malformed plan
files reject; future plans reject. Default output without the option is unchanged.
The combined hash binds the optional coverage output alongside source receipts.
Technical and native financial statuses remain independent from coverage.

The existing FinancialResearchModule accepts an explicit optional
`bank_document_input_plan` and retains coverage JSON/plan/assessment hashes in its
existing report features. Synthetic Technical + Financial report storage and
reconstruction preserve these features. Financial remains null-scored, confidence
zero; reports stay INCOMPLETE and InvestmentScore remains absent. No actual queue
or report is fabricated for retained exploratory data.

Financial model: `financial-v0.5.16-bank-document-inputs`.
Coverage model: `bank-source-document-inputs-v1-draft`.
Source packet versions, old reports and framework/schema remain unchanged.
No database migration, real data write, canonical population or new provider.

## Real Maybank Example

Plan: `config/bank-document-input-plans/maybank-2025.toml`.
This targets the exact previously retained 15-row income-statement review,
not every Malaysian bank, every financial subsector or the latest issuer filing.
Its draft questions span Survival / Cycle / Valuation / Growth without assigning
weights, healthy/unhealthy thresholds, buy/sell criteria or holding periods.

At cutoff `2026-10-29T11:50:26+00:00`, the explicit 17 questions produce:

| State | Count | Meaning |
|---|---|---|
| MATCHED_UNQUALIFIED_ANNOTATIONS | 7 | Current group interest, Islamic, insurance, net/gross operating income and attributable profit annotations match this manual review |
| MISSING_REVIEWED_ROW | 1 | Prior-year parent-attributable profit has not been transcribed in the selected review |
| RATIO_CONTRACT_REQUIRED | 5 | Capital/CET1, liquidity, asset quality and bank ROE require separately defined source/period/denominator/regulatory contracts |
| EXTERNAL_EVIDENCE_REQUIRED | 4 | Attributable equity, dated valuation inputs, credit-cycle context and comparable-edition history need separate reviewed inputs |

The 2025 year-end annotation is 302 calendar days old at this cutoff. Review
capture age is a separate elapsed-time value. Freshness stays UNASSESSED and
latest_issuer_filing_verified false: neither a recent download nor a plan match
proves current interim coverage. The known summary/statement Bank revenue
discrepancy remains open; no Group/Bank or total/parent-profit substitution.

Two final same-cutoff CLI runs reproduce exactly. Both retained database byte
hashes remain unchanged. This is an offline reconstruction using previously
retained evidence, not a new provider request or independent numeric calibration.

- Input hash: `25dcedea5a2974b7370245791adaf82a6970de9d1f3e41a6c227bd9df7ee0a35`.
- Plan hash: `c19e0f7162d667f547741fed1b81165609f395bb75d23ccc78c767c5442184cf`.
- Assessment hash: `e692e29f5ec21dc4638f3c09aeedeae6cdef6d0b58f4ba33ac7f513dee778129`.
- Combined hash: `880901ccd195d7c579bc4376feb90c7d3c535d1a3a6cdf55951422361f88c241`.
- Document database: `81a136c9344ba4c8c44625e809e02c9ae2a70137b3a602ceabe75a26cb8b28bb`.
- Price/native database: `0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087`.

Full verification: **2762 passed / 6 skipped** in 129.44 seconds, 24 new cases.
Ruff passes, mypy passes on 292 source files, all 136 governance checks and
`git diff --check` pass. Scoped runtime imports have no trading/portfolio/
notification dependency. Six opt-in network tests stay skipped; real retained
reproduction does not count as a live network test or source independence proof.

Synthetic tests cover all exact annotation fields, missing/unresolved rows,
unsupported contracts, source/review/PDF pin conflicts, wrong sector, changed
current parent, future/backdated plans, equivalent UTC instants, rejected numeric
expectations/weights, CLI file/option failures, deterministic hashes and report
feature persistence/reconstruction with all financial scores still absent.

## Remaining Work

First fill the explicit prior-year review gap with a new preserved review edition
and a newly pinned plan; do not merge old captures or backdate plan availability.
Then review a distinct HK/MY ratio contract, source-defined equity/valuation
dependencies and applicable financial-sector methodology. The China-only CNY/YTD
and percent contracts must not be silently widened to make these observations fit.
Review actual issuer/sector identity and source accuracy independently.

Follow with real Discovery/Hard Screening/Research Queue inputs and preregistered
technical-plus-fundamental validation. A complete input checklist alone does not
validate the improved Turtle, indicator confluence, dynamic stops or investment
edge. Regime remains a research variable, never an automatic approval/rejection.

No Paper, Broker, Order, Execution, Portfolio, Notification, live trading or asset
allocation code changes. No new credentials, network capture, commit or push.
R1-R6 partial, WP-LAUNCH-001 ready/not accepted, PIT UNSUITABLE, production
NOT_READY, execution/notifications disabled. Prior ignored raw/database evidence
still needs encrypted co-retention; Git is not the data backup.
