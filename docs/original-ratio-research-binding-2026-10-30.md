# Original Ratio Evidence In Official Research

## Delivered Slice

WP-LAUNCH-001, October 30 Malaysia time (October 29 UTC): original percentage
receipts can now enter the existing official ResearchContext and Financial
assessment/report storage. This is not another ResearchReport/ResearchOutcome
model, a bank financial policy, a canonical fundamental input or an investment
conclusion. Monetary V1 receipts and original percentage V1 receipts remain separate.

`read_global_ratio_review_inputs` -> `ReviewedRatioResearchInput` -> optional
`ResearchContext.reviewed_ratio_inputs` -> existing Financial features alongside
Technical -> existing report JSON / SQLite reconstruction. No schema migration,
new table, provider request or real research queue is created.

The frozen input stores canonical copied JSON. Checks enforce identity, explicit
UTC cutoff, strict version/rows/chronology, unique selected capture, checksum,
LOW trust, RETRIEVAL_TIME, UNASSESSED freshness and all false authority flags,
including denominator/regulatory-scope verification. Original percentage rows
cannot masquerade as monetary rows or vice versa. Context validation runs before
direct evaluation and before ResearchEngine starts a persisted run. Mutated inputs
reject without creating a research run. Current integration remains equities only;
parallel canonical financial receipts reject. Requested ratio/native/monetary
sector contexts must agree, without certifying the sector classification.

Receipts may reference distinct filings. Co-presence in a report never asserts
matching edition/period/regulatory scope or metric correspondence. No automatic
join, ratio/money alias, computation, sector approval, trust upgrade or bank-plan
credit is introduced. Read-time source integrity belongs to the exact retained
reader; copied inputs are not a live source recheck or authenticated authorship.
Every new run needs a fresh read for its own cutoff, not retimestamping old JSON.

## Assessment Availability Repair

A failing regression reproduced an assessment-chronology defect: with older raw
facts present, Financial.available_at could remain at those facts' earlier time
despite including later native/manual evidence. Previously defaulting to context
time when no facts were supplied hid this issue. The existing final availability
calculation now includes each bound native, monetary and ratio receipt's exact
read cutoff, including missing/failed receipt states. This conservative bound
does not claim actual issuer publication. Eight HK/MY observed/missing/failed/
tampered integration cases exercise each receipt slot independently with older
facts; report availability cannot precede the bound read. No historical data or
previously stored report is silently rewritten.

## Explicit Research Questions

FinancialResearchModule accepts optional `manual_ratio_row_keys`, a bounded unique
tuple of original row keys. Configuring questions without a ratio input object
rejects. The full receipt is retained even without selected questions. Explicit
questions preserve the complete selected original observation and separate:

- DEFINITION_REVIEW_REQUIRED: transcribed, but not independently qualified.
- UNRESOLVED_VALUE: cell was missing/unreadable/conflicting, never zero-filled.
- MISSING_REVIEWED_ROW: requested key not transcribed, not an issuer-wide absence.
- BLOCKED_INPUT: missing/rejected/current-parent-invalid source, no older fallback.

Every question still requires definition, denominator, regulatory scope, period
basis and independent source review. Nonempty caller notes do not close these
questions. No numeric threshold, weight, health score, latest-filing assumption or
canonical metric is inferred. Question hash binds exact input/context/request keys;
it does not authenticate correctness. Existing draft bank source plan is unchanged:
five ratio-policy questions and four external dependencies remain unresolved.

Financial features preserve full ratio receipt/input hash/status/row count,
requested sector, trust/precision and optional question JSON/hash. Financial
remains unscored with confidence zero; combined reports INCOMPLETE and no
InvestmentScore. Model version `financial-v0.5.18-original-ratio-receipts`;
question version `global-original-ratio-questions-v1`. Framework 0.8.0, schema
0.8.2, source receipt versions and existing default global CLI output are unchanged.

## Real Retained Reproduction

At `2026-10-29T18:02:07+00:00`, two reads/questions for retained Maybank evidence
repeat exactly. Five selected original keys return DEFINITION_REVIEW_REQUIRED;
explicit `unreviewed_liquidity_coverage` returns MISSING_REVIEWED_ROW. This does
not say the issuer has never disclosed liquidity coverage. Original ratios are
single-review financial-summary annotations, not admitted regulatory bank metrics.

- Ratio input hash: `b07f58a1c5c3fa18781b7e450eb701f92429373b4ef2e17ba5e75567d62224b9`.
- Question hash: `570d07a1352d67d5fb5af66e9a22072d7075940efbd2a066a43dec59565408ea`.
- Document DB SHA: `69d54a7bc32b99b560bc75edbbaec9219e24ba2046c7e4fe127c106e338684e7`, unchanged.
- Old 22-row monetary receipt at `2026-10-29T12:11:01+00:00` retains exact hash
  `4aa54309f31a06aa37bc0de31868fdd26f1b5feec8efda2a2767219c2344ea2c`.

Real database still has seven provider evidence rows, zero canonical facts,
ResearchReports or signals. No synthetic admission is written into real data.
Synthetic HK/MY integration fixtures demonstrate official Technical + Financial
report persistence/reconstruction with native, monetary and ratio receipts in
observed, missing, failed and tampered states. They prove software contracts,
not real screening quality, verified data, validation effectiveness or readiness.

## Remaining Work And Boundaries

Next: review original bank numerator/denominator/regulatory definitions and
separately sourced liquidity/attributable-equity evidence, then explicit admitted
sector/source/freshness policy and real screened research with preregistered
validation. No formula, banking threshold or scoring rubric is admitted by this
engineering slice. Real examples across four markets/sectors, strategy validation,
latest filings and the known Maybank summary/statement discrepancy remain open.
New ignored raw evidence still requires approved encrypted co-retention.

No Portfolio, Notification, Paper, Broker, Order, Execution, live trading or
allocation implementation. No commit/push. PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled, R1-R6 partial and launch ready/not accepted
remain unchanged.

## Verification

Final suite after the availability repair: **2878 passed / 6 skipped** in 165.76
seconds. There are 34 new cases plus expanded eight-case HK/MY official report
integration coverage. Ruff passes, mypy passes on 296 source files, all 139
governance checks and `git diff --check` pass. Scoped runtime import checks find
no execution, broker, order, trade, fill, paper, portfolio or notification imports.
Real receipt credential-structure checks pass; databases/artifacts/test caches
remain ignored and both real database byte hashes are unchanged.

New tests cover canonical copied JSON, rehashed/mutated receipts, false authority
flags, exact UTC/identity/version/row binding, unknown denominators/regulatory
scope, explicit bounded questions, missing/unresolved/failed sources, monetary
wrapper separation, sector and fund rejection, direct/pre-run revalidation,
report persistence/reconstruction, absent InvestmentScore and conservative
availability with older raw facts. The red availability regression was observed
before the repair; all eight affected integration cases pass afterward. No
previously stored report is silently repaired. Six opt-in network tests remain
skipped; no live provider capability or independent source calibration is claimed.
