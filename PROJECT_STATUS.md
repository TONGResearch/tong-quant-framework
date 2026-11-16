# Tong Quant Project Status

This is the canonical short handoff for developers and AI agents. Read it with
`AGENTS.md` and `config/project-governance.toml` before changing code.

## Current Baseline

- Framework version: `0.8.0`
- Database schema version: `0.8.3`
- Migration head: `0011_refresh_ledger`
- Current phase: Parallel evidence and controlled launch
- PIT readiness: `UNSUITABLE`
- Production readiness: `NOT_READY`
- Execution default: `disabled`
- Notification default: `disabled`
- Portfolio/Risk model versions: `portfolio-proposal-v0.7.1` / `risk-assessment-v0.7.1`

## What Exists

### Independent Review Hardening: November 16

Two authorized read-only AI reviewers found four blockers in the entire pending
sync range despite passing tests: artifact publication before credential
rejection, lifecycle DST visibility, local-date fundamental admission and replay
nested-research DST visibility. Working repairs add pre-publication privacy
screening and UTC comparisons, preserving shared bytes and old evidence/report
identities. Re-review found and repaired a UTF-8 BOM JSON-screening bypass while
preserving original bytes/hashes. Forty-four regressions added; five focused
files pass 527 tests and research integration passes 127. Publication requires
full isolated repaired-tree checks and independent re-review; consult the reviewed
sync commit receipt/CI rather than reusing the old candidate's passing results.
No schema/dependency/trading change; PIT UNSUITABLE and production NOT_READY.

Follow-up debt remains for direct technical renderer source binding, suspended
replay endpoint interpretation and non-UTC producer-clock rejection. See
docs/independent-review-hardening-2026-11-16.md. Existing engineering automation
now runs every three hours at 00/03/06/09/12/15/18/21 Malaysia time; app readback
confirmed the same prompt/thread. GitHub sync schedule is unchanged.

### MSFT Dimensional Context Review Design: November 16

Read-only retained-byte review now inventories exact expanded concept/axis/member
names, native period text and nonNumeric ancestor names for the original five-tag
exclusions. Source verification runs before bounded XML observation, at the old
November 9 cutoff, without namespace URI fetching, amounts or parser relaxation.
New private inventory repeats exactly and four existing DB/WAL/audit/period
files retain their hashes. This is a one-off design audit, not a new adapter.

The 45 excluded occurrences refer to 35 distinct contexts; 37 have one explicit
member, 8 none. Six axes/17 axis-member pairs are observed. Two AzureMember name
candidates have ProductOrServiceAxis, not the MicrosoftCloudMember secondary
categorization. Both remain excluded; no Azure amount/growth input is admitted.
Ancestor memberships total 36 across 34 blocked occurrences, not independent
facts. URI/label/period observations are not schema, business or accounting truth.

The new proposal identifies the tag/period-only selection and free-text scope
gap, and specifies exact source/context/namespace/full-dimension bindings before
any optional, versioned numerical support. Empty dimensions cannot default to
consolidation, namespaces cannot be collapsed and textblock barriers cannot be
removed globally. The proposal is registered for governance but not implemented;
its future acceptance cases are not new passing tests. Full baseline pytest:
**4121 passed / 6 skipped**, 384.34 seconds. Ruff, mypy (318 files), governance
(176 checks), whitespace and scoped default/privacy checks pass. Mixed-workspace
checks are not isolated release or source/method approval. No runtime/schema/
dependency/default/scoring/holding/trading changes, commit or push. PIT remains
UNSUITABLE.

See docs/proposals/msft-dimensional-context-review-v1.zh-CN.md and the private
data/processed/msft-dimension-audit-20261116/dimension-inventory.json. Next:
independent source/definition/context review, then separately versioned scoped
implementation and genuine combined technical/fundamental validation.

### SEC Exclusion Structure Diagnostics: November 16

Existing review_inline_body/read_sec_body_inputs now offer an explicit boolean
explain_exclusions=False option. Enabled output adds a separately versioned,
body-hash/cutoff/CIK/tag-bound structural audit of excluded occurrences only.
It records context reference identity, entity/period/container counts and the
existing ancestor/target scope barriers, without accepting excluded values or
classifying contexts as valid/malformed. Shared context structure is cached,
while each occurrence retains its own original reason and scope flags.

The existing SEC body CLI exposes --explain-exclusions in read-only mode; capture
is rejected before storage/network setup. Default parser/body/period outputs,
numeric review/source versions and canonical hashes remain unchanged. Enabled
outer receipts record the diagnostic version; no new domain model/schema or
official-report/global-equity integration. No scoring or thesis evaluation.

Real retained MSFT at the original November 9 cutoff reproduces the exact old
ten period checks and source input hash. Of 61 selected five-tag occurrences,
45 remain excluded. All 11 context-barrier occurrences contain a segment; 34
scope-barrier occurrences have blocked ancestors, including 26 also containing
a segment. Thus 37 segment occurrences overlap 34 scope occurrences; do not
add them as independent counts. No scenario or global targeted-document flag
was observed in this scoped inventory. Unique references/counts do not prove
valid XBRL, consolidated accounting scope, value truth or completeness.

Thirty new regressions cover structural observations, overlapping causes,
per-fact scope isolation, invalid flags before DB access, malformed/oversized
input, original-value preservation, retained-source gates and offline CLI.
Full pytest: **4121 passed / 6 skipped**, 412.68 seconds. Ruff, mypy (318 files),
governance (175 checks), scoped import/disabled-default/privacy and tracked/new-
file whitespace checks pass. These mixed-workspace checks are not independent
source/method or release admission. No network, DB/raw rewrite, commit/push,
execution/default/Portfolio/Notification changes.
New private data/processed/msft-sec-exclusions-20261116 retains the deterministic
audit. LOW/retrieval_time, UNSUITABLE PIT and NOT_READY production persist.
Next is source/definition/namespace/dimension and operative context qualification
for H1-H4, then approved numeric thesis conditions and genuine Validation.

### Nasdaq Comparison Display Repair: November 16

Real retained strict-price-age output exposed a display ambiguity: raw false
closed-date conflict flags appeared even when no usable prices existed or the
date was still prospective. The flags were not source/session admission, but
the table could be read as a completed favorable comparison. New presentation
version v7 distinguishes future, unavailable, out-of-span and early-close
unassessed states, candidate date conflicts and observed absence without claiming
completeness. Contradictory or nonboolean comparison fields are rejected even
after rehashing. No new domain model or change to the source/comparison receipts.

Fifteen new cases plus existing focused checks pass (63 cases). Full pytest:
**4091 passed / 6 skipped**, 402.93 seconds. Ruff, mypy (318 files), governance
(175 checks), scoped dependency/default/privacy and whitespace checks pass.
Mixed-workspace checks do not certify an isolated release or source/method.
Source and review JSON/version/hashes, default no-Nasdaq output, technical
arithmetic, schema, dependencies and disabled defaults stay unchanged. The v6
note version remains a legacy constant;
newly rendered Nasdaq notes use v7. Stored old notes are never rewritten.

Real offline rendering repeats and leaves 11 old files unchanged. Strict-price
sample now shows eight past dates as unassessed/no usable prices and four future
dates as unassessed plans. The other sample shows eight unverified observed
absences, not calendar completeness. Default v4/v5 notes still match exactly.
New private *-v7.zh-CN.md files are in msft-calendar-refresh-20261116; no network.
No scoring/holding/PIT authority, commit or push. Source/session qualification
and combined-method validation remain open; UNSUITABLE/NOT_READY persist.

### Real Calendar Refresh Rehearsal: November 16

The existing explicit capture CLI fetched Nasdaq's fixed public source into a
new private diagnostic DB/root. Availability is November 16 Malaysia time
(2026-11-15T16:39:02.668051+00:00), never backdated to holiday dates. Retained
body reconstruction succeeds with 12 explicit declarations; original bytes
changed, but the full parsed declaration list equals the old capture. This is
same-provider repeat evidence, not independent consistency or source approval.

Three real offline MSFT compositions repeat exactly: old cutoff cannot see the
new source; the new cutoff sees the source within an illustrative one-day age
limit; imposing the same illustrative price-age limit still blocks old prices
even with a fresh calendar. Default price freshness remains UNASSESSED, not
approved. Eight pinned existing DB/WAL/report/capture files remain byte-identical.
No canonical calendar projection, original record overwrite or trading activity.

Three new end-to-end regressions cover refreshed source versions with unchanged
old-cutoff output, separate price/source age, latest source failure without old
success fallback, deterministic output and unchanged read-side databases. Full
pytest: **4076 passed / 6 skipped**, 404.21 seconds. Ruff, mypy (318 files),
governance (175 checks), tracked/new-file whitespace and scoped disabled-default/
privacy checks pass. These mixed-workspace checks are not isolated release or
independent source/method qualification. Runtime source and versions, schema,
defaults and dependency graph are unchanged. No commit/push.

See the November 16 addendum in docs/nasdaq-calendar-source-2026-11-07.md and
private data/processed/msft-calendar-refresh-20261116. LOW/retrieval_time,
UNSUITABLE PIT, NOT_READY production and disabled execution/notifications persist.
This is a manually completed refresh rehearsal, not an automatic updater or
guaranteed current-source operating policy. Session-aware freshness, operative
venue/session coverage and combined technical/fundamental validation remain open.

### Explicit Nasdaq Source Co-Review: November 15

The overseas diagnostic now accepts an explicit Nasdaq evidence DB, artifact
root, year and positive source-age limit, with a required fixed cutoff. This
read-only composition reuses retained-body verification and source-age checks;
it neither downloads nor populates canonical TradingSession dates. Same-store
reads reuse the price snapshot; separate stores share only a cutoff. Native
early-close times, future dates and stale/failed observations remain visible.

An optional price-hash-bound receipt/v6 Chinese section retains the full nested
source receipt, LOW/retrieval_time and false authorities. Scope, cutoff, source
age arithmetic and future-date contradictions are rejected. Venue pairing,
actual sessions and completeness remain unverified. Legacy indicators, coverage
percentages and default JSON/notes are unchanged. No holding/add/exit decision.

Real retained MSFT at the old November 15 cutoff repeats exactly with unchanged
price/calendar DB and WAL bytes. The November 6 source is 752066.505542 seconds
old; an illustrative 86400-second limit yields STALE, zero current comparisons
and all 12 original declarations retained. This is not a production TTL or proof
of false declarations. The price DB still has zero canonical calendar rows.

Forty-five new synthetic/CLI cases cover composition and rendering. Full pytest:
**4073 passed / 6 skipped**, 422.94 seconds. Ruff, mypy (318 files), governance
(175 checks), scoped import/default/privacy and whitespace checks pass. These
mixed-workspace checks are not independent source or isolated release approval.
No schema, dependencies, defaults, Execution/Paper/Broker/Portfolio/Notification,
commit or push changes.
PIT UNSUITABLE, production NOT_READY and launch ready/not accepted persist.
Next: current-source capture policy and operative venue/ordinary/abnormal-session
qualification, alongside combined technical/fundamental method validation.

### Annual Calendar Coverage And Gap Review: November 15

Existing declaration coverage now supports opt-in years with source Bar hash/
count and the same parent calendar receipt. --calendar-coverage may accompany
long/multi-timeframe modes directly; it reads declarations from the first year
start through the local cutoff in the same price database snapshot. Default v1
coverage and previous long/weekly indicators are unchanged. No source import,
weekday assumption, new schema or calendar qualification occurs.

New v2 coverage/v5 Chinese note distinguishes absent calendar declarations,
missing prices on declared opens, suspension and closed-date contradictions.
It checks source/cutoff/parent identities, unknown legacy trust/precision and
false authorities. Ended-year percentages are conditional, never source grades;
unended years withhold percentages. No InvestmentScore or holding decision is added.

Real retained MSFT has zero declarations in the selected price DB interval.
Annual unknown counts are 365/366/365 for ended 2023/24/25 and 319 through the
old November 15 cutoff for unended 2026; percentages stay null. This does not
mean no trading days, no observations or provider-wide absence. Two new private
JSON runs repeat exactly, old DB/v2 JSON/v4 note hashes are unchanged. No network.

Thirty new synthetic/CLI regressions pass. Full pytest: **4028 passed / 6 skipped**,
397.50 seconds. Ruff, mypy (317 files), governance (175 checks), scoped import/
disabled-default/privacy checks and tracked/new-file whitespace checks pass.
No Execution/Paper/Broker/Portfolio/Notification, schema, dependencies, defaults,
commit or push change. These mixed-workspace checks are not an isolated release
or independent source/method approval. PIT UNSUITABLE, production NOT_READY,
execution/notification disabled and launch ready/not accepted remain unchanged.
Next is retained-source/venue/calendar evidence integration and independent
qualification, alongside financial-definition review and genuine strategy validation.

### Weekly Observations And Timeframe Alignment: November 15

Optional --multi-timeframe adds ended weekly SMA/MACD/KDJ plus a dated source
alignment matrix to existing month/year diagnostics. Explicit weekly parameters
enable a new v2 receipt/v4 Chinese note; None keeps the previous v1 month/year
receipt and v3 note exact. Monthly/yearly values, daily analysis and old artifacts
are unchanged. No second report, Signal, voting score or holding decision exists.

Every period records its own last ended range, source observation/availability
and exact UTC distance from the latest daily observation. One cutoff does not
make sources simultaneous; calendar_end_is_exchange_close/comparison_eligible
remain false and freshness UNASSESSED. Rendering checks schema/version, matching
daily context, unique frequencies, period labels, actual UTC age and future dates.
Open or missing latest weeks cannot be filled with earlier favorable observations.

Retained MSFT yields 201 ended calendar weeks/46 months/3 years at the same old
cutoff: daily source November 13, weekly source November 6, monthly October 30,
yearly December 31, 2025. Weekly closure conservatively waits for next Monday,
not a claimed verified Friday close. Two new private JSON runs repeat exactly;
old DB/v1 JSON/v3 note hashes stay unchanged. No network or new ingestion.

Thirty-six new cases and focused compatibility tests pass. Full pytest:
**3998 passed / 6 skipped**, 362.41 seconds. Ruff, mypy (317 files), governance
(175 checks), scoped dependency/default/privacy checks and tracked/new-file
whitespace checks pass. No schema, dependencies, Execution/Paper/Broker/Portfolio/
Notification, defaults, commit or push changes. Mixed-tree checks do not certify
an isolated release, source or strategy. PIT UNSUITABLE, production NOT_READY,
execution/notification disabled and launch ready/not accepted remain unchanged.
See the existing long-horizon document. Next remains calendar/action/source and
financial-definition qualification, then genuine combined-method validation.

### Monthly And Yearly Technical Observations: November 15

Optional --long-horizon now adds ended calendar month/year observations and
unscored SMA/MACD/KDJ to the existing overseas JSON/Chinese diagnostic. The
four-market arithmetic helper reuses checked original daily versions and the
existing formulas; KDJ only gains a read-only OHLC protocol, not invented daily
Bars or timestamps. Legacy calendar v1 and default JSON/Markdown remain unchanged;
optional yearly receipts and extended views use central prospective versions.

Open periods never enter indicators. Whole gaps/suspensions block without
stitching or older-good fallback; known missing months also block yearly
calculations. A leading partial year with missing earlier months stays explicit.
Per-indicator samples count ended months/years, not supplied daily rows. Unknown
within-period coverage, first-month truncation, adjustment/action basis and source
qualification remain unknown. New defaults are research observation parameters,
not admitted trading thresholds. No extra independent votes/confidence, score,
holding horizon or cross-timeframe investment decision is generated.

Real retained MSFT at the prior November 15 UTC cutoff gives 46 ended months and
three ended years. Monthly MACD/KDJ are calculable but unqualified; yearly
MACD/KDJ are INSUFFICIENT_HISTORY. November and the current year are excluded.
New private JSON/note files do not replace old files. Database hash is unchanged,
and default real JSON plus 4996-byte Markdown exactly match the retained
pre-change script/viewer. The linked document records bounds, receipt and usage.

Fifty-two new synthetic/CLI cases pass. Full pytest: **3962 passed / 6 skipped**,
339.72 seconds; Ruff, mypy (317 files), governance (175 checks), tracked/new-file
whitespace and scoped dependency/default checks pass. These mixed-workspace and
network-skipped checks are not independent source, strategy or release admission.
No schema, dependencies, source capture, trading/Portfolio/Notification, default,
commit or push changes. PIT UNSUITABLE, production NOT_READY, disabled
execution/notification and launch ready/not accepted remain unchanged.

See docs/long-horizon-observations-2026-11-15.zh-CN.md. Next: qualify long-history
calendar/action/price inputs and financial definitions, then validate the combined
method. Monthly/yearly Turtle, Granville/setup rules, cross-timeframe synthesis,
official holding decisions and new A-share CLI are not implemented by this slice.
Any GitHub candidate must be rebuilt and independently reviewed for this source.

### Thesis Declarations In Official Reports: November 15, Second Slice

DefaultResearchReportBuilder now accepts an explicit ThesisReportBindingPlan
without changing Request/Report fields or interface signatures. The plan binds
the real queue, instrument, actual UTC cutoff and every unchanged condition.
Condition definitions cannot be replaced by same-id rules; missing, unknown and
duplicate definitions fail closed. Declarations persist in existing assessment
features through transactional SQLiteResearchRepository and reconstruct through
the existing HistoricalReplay repository. No schema or new table is needed.

Every enabled report remains INCOMPLETE, so InvestmentAssessment is INCOMPLETE
with no InvestmentScore, even with complete HIGH-labeled declarations and high
module scores. Module scores/confidence are not boosted. Source/hash labels are
still unverified declarations, not admitted evidence. The standalone diagnostic
can retain excluded future metadata; official reports reject future availability,
publication or period references before publishing a report or research Signal.
Failed engine runs may retain the existing generic failure audit record, not a
new decision report. Policy annotations stay consistent with stored assessments.

Enabled reports use research-report-v0.5.3-thesis-declarations and a separately
versioned declaration hash. Default no-plan output preserves the old version;
a fixed synthetic 6740-byte report exactly matches the retained pre-integration
builder and now has a pinned golden hash regression. No old records are rewritten.

Twenty-two new integration cases pass (64 focused with the prior contract suite).
Final whole-project pytest: **3910 passed / 6 skipped**, 568.00 seconds. Ruff,
mypy (316 files), governance (174 checks), tracked/new-source whitespace and
scoped import/default checks pass. These are final completed checks; an earlier
run interrupted for review hardening is not counted as a full pass. No real MSFT report,
fact or source capture, CLI, dependency, schema, default, trading/Portfolio/
Notification, commit or push change. These are mixed-workspace synthetic tests,
not independent source, strategy, data or release admission. PIT UNSUITABLE,
production NOT_READY and both disabled defaults remain unchanged; launch stays
ready, not accepted. The earlier isolated GitHub candidate is stale for this slice.

Next: inspect original financial definitions and unsupported contexts, then build
reviewable source qualification/metric-period mappings before economic evaluation
and genuine outcome generation. No holding horizon, threshold grid or add/exit
rule is approved. CLI/real-data binding and actual investment validation remain open.

### Typed Thesis Evidence Binding Foundation: November 15

research.thesis_bindings introduces explicit immutable period, metric-definition
and evidence-reference contracts around the existing ThesisInvalidationCondition.
The callable diagnostic binds issuer/instrument label, native namespace/tag,
definition/scope/sector/unit/currency, periods, document/input hashes, batches,
revisions and actual UTC publication/availability. Missing, future, mismatched
and ambiguous references stay visible; no favorable revision selection occurs.
Canonical output is deterministic and centrally versioned. Trust and availability
precision remain separate declarations, not authenticated source qualification.

Complete bindings are DECLARED_ONLY, never thesis pass/fail. Evaluation remains
NOT_EVALUATED; source bytes NOT_PERFORMED/qualification NOT_ADMITTED, continuity
NOT_VERIFIED, freshness UNASSESSED and horizon NOT_ESTIMATED. All authorities
remain false. No fact values, threshold comparison, outcome labels, secondary
report model, score or holding instruction is added. Old condition/request/report
serialization and stored identities are unchanged.

This is the P2 contract foundation only: not yet integrated into requests,
assessment features, CLI, persistence or real MSFT evidence. Next is explicit
versioned opt-in integration under the sole official ResearchReport, followed by
source/accounting qualification and genuine outcome generation/validation.
The existing MSFT proposal has an implementation addendum; the rest remains draft,
with no approved economic thresholds or holding-window grid.

Forty-two new synthetic contract regressions pass. Final whole-project pytest:
**3888 passed / 6 skipped**, 311.91 seconds. Ruff, mypy (316 files), governance
(174 checks), tracked and
new-source whitespace checks pass. Scoped import review confirms no new trading,
Portfolio or Notification dependency. No schema/default/dependency/source capture,
commit or push changes. Mixed-workspace/synthetic checks are not independent
release, source or strategy admission. PIT UNSUITABLE, production NOT_READY and
both disabled defaults remain unchanged; launch is ready, not accepted.
Previous GitHub sync candidate checks do not cover this new slice; recreate and
independently review the exact candidate before any commit/push.

### MSFT Holding-Thesis And Validation Design: November 14

[Scoped design](docs/proposals/msft-holding-thesis-validation-v1.zh-CN.md) audits
the actual ResearchReport/ThesisInvalidationCondition, condition features and
ThesisValidationModule. Free-text window declarations and supplied-outcome label
statistics are not an implemented source-qualified invalidation evaluator.
The draft maps five business/cash/valuation/risk theses and counter-theses,
required explicit source/period/definition/version bindings, decision/outcome
separation, family-aware technical conditions and hold/add/exit research limits.
No numeric thresholds or horizon grid is registered or approved; proposed
acceptance cases are design only, not newly implemented tests or strategy results.

Read-only audit of the retained MSFT body with the same five native tags finds
61 occurrences/45 unsupported: 11 combined dimensional-or-malformed context
reasons, 34 nested-or-targeted scope reasons. Neither reason proves issuer error
or permits relaxing the parser. Original database hash remains unchanged; the
audit uses the November 9 retained cutoff, not a new latest-data assertion.
Next bounded implementation is typed condition/source/window binding under the
sole official ResearchReport, with unqualified inputs still NOT_EVALUATED;
genuine outcome generation and validation remain distinct subsequent work.

Documentation/governance only, no runtime/schema/default/source capture changes.
Full pytest: **3846 passed / 6 skipped**, 290.74 seconds; Ruff, mypy (315 files),
governance (174 checks), tracked/new-document whitespace and scoped content review
pass. Mixed-tree regression is not independent release/data/method acceptance.
No new executable cases, reports, scores, labels, orders, commit or push. PIT
UNSUITABLE, production NOT_READY and both disabled defaults remain unchanged.

### Explicit SEC Root And Complete Holding Composition: November 10

[Source-root follow-up](docs/sec-source-root-composition-2026-11-10.zh-CN.md)
adds explicit US read-only --sec-artifact-root for separate retained SEC stores.
No guessing/copy/rebinding/fallback; one database rejects contradictory roots.
Body, issuer and period readers use the selected SEC root, and default legacy
output stays unchanged. Optional owner review now precedes the full SEC/HK/MY
combined hash: the previous extension appended it afterward, leaving it outside
that hash. New combinations use equity-evidence-holding-display-v1 without
rewriting old files or independent holding receipts. No real trading error is
inferred; root selection is not authenticated source configuration or admission.

Real retained MSFT now combines 757 old daily observations, selected latest
10-Q/ticker/ten exact-period checks and owner annotation at one actual UTC cutoff.
Two repeated full JSONs match, complete combined hash verifies and both original
DB hashes remain unchanged. Six unresolved period checks remain visible; native
annual fundamentals still missing is not silently repaired by SEC values.
Holding comparison remains BLOCKED on pre-observation prices, horizon NOT_ESTIMATED,
all authorities closed. No network capture; private combined JSON is ignored,
mode 600, not Git/encrypted backup. Old historical MSFT SEC JSON matches the
pre-existing isolated candidate script exactly without database changes.

Seventeen added regressions. Full pytest: **3846 passed / 6 skipped**, 296.11
seconds; Ruff, mypy (315 files), governance (173 checks), tracked/new-file
whitespace and scoped import/privacy checks pass. These mixed-tree checks are
not an isolated release or independent source/strategy review. No schema,
dependency, defaults, Execution/Paper/Broker/Portfolio/Notification, commit or
push changes. PIT UNSUITABLE, production NOT_READY, launch ready/not accepted.
Next: MSFT source/accounting/period review and falsifiable thesis plus genuine
exit/add/horizon validation, not more co-display in place of decision research.

### Owner Holding Review And Latest MSFT Evidence: November 9

[Holding follow-up](docs/holding-review-2026-11-09.zh-CN.md) adds opt-in
--holding-context to the existing US/HK/MY read-only diagnostic. Bounded Decimal
owner annotations bind identity/currency, observation/declared-recording UTC,
explicit age policy and original source/technical hashes. Missing, stale,
suspended or pre-observation prices withhold comparisons; owner loss thresholds
only request review. Horizon/thesis stay NOT_ESTIMATED/NOT_EVALUATED, no inferred
exit/add/sizing authority. Private real MSFT annotations stay ignored/local.
Retained 757-bar MSFT reproduces trend BULLISH/momentum CONFLICTED; November 6
price predates tonight's observation, so comparison correctly BLOCKED. Old
candidate and current default JSON/Markdown match exactly; old price DB hash
ad5d3dc53048302721c945ff8e89b75ca592b0f78bb9581ef62c48e82210cad0 is unchanged.

Existing SEC adapters also captured a new independent diagnostic database:
1005 catalog rows and latest selected 2026-10-28 10-Q (0001193125-26-436133).
Five native tags/current and prior exact periods produce ten unqualified checks;
61 fact occurrences include 45 unsupported, and six checks retain unresolved
tag contexts. MSFT ticker declaration is unverified, not identity approval.
Two registered artifacts verify 2/2; period JSON repeats exactly, old-cutoff
read is SOURCE_UNAVAILABLE and reads leave the new DB unchanged. Two batches/
evidence/artifacts, zero canonical bars/facts. Actual retrieval availability is
November 9, not the filing date or manual trade time. New and old raw roots are
separate; full combined financial/holding research remains open, not silently
copied or rebound. New raw data is ignored, not Git or encrypted recovery.

Fifty-four added cases (46 unit/eight CLI). Final full pytest: **3829 passed /
6 skipped**, 379.05 seconds. Ruff and mypy (315 files) pass. Governance/diff checks
and scoped import/credential review are recorded in the follow-up document.
These mixed-tree/synthetic/network-skipped checks do not qualify an isolated
release, source truth or a profitable strategy. No schema/dependency/default,
Execution/Paper/Broker/Portfolio/Notification, commit or push change. PIT stays
UNSUITABLE, production NOT_READY, launch ready/not accepted. Owner priority is
real MSFT source/accounting review, falsifiable thesis and exit/add validation
within the November 30 read-only goal; other markets remain in overall scope.

### Cross-Device Owner Handoff: November 9

[Chinese handoff](docs/PROJECT_HANDOFF.zh-CN.md) records the owner philosophy,
seven technical research groups and separate deferred seven-plus-one, actual
calculation/qualification gaps, four-market scope, versions and recovery commands.
README/agent/continuity entries link it; the stale continuity-wide development
freeze now matches controlled-launch governance without admitting planned packages.
This is documentation only, not a changed method, source, schema or readiness.
The November 9 SSH query initially failed with publickey authentication; loading
the existing identity through the local Keychain restored a successful read-only
query. Remote branch was 6be0a842d997b7707b0d347b3206e6e003aac7fb at that check.
This handoff does not claim upload or cross-device data recovery.
Local new code remains unpublished; old HEAD still needs the retained rollback
repair and exact isolated-candidate checks/independent review before any push.
Candidate preparation found five whitespace issues in previously untracked files;
four TOML EOF blank lines and one test trailing space were fixed without changing
parsed configuration contents or test semantics. Keep the source snapshot tests,
candidate-wide whitespace check and independent review distinct; no push approval
or completed package is inferred from this documentation delivery.

### Readable Equity Note UTC Context: November 9

The existing [single-equity view](docs/single-equity-usability-2026-11-08.zh-CN.md)
now requires one actual UTC cutoff across price, fundamentals, financial review
and optional Turtle observations. Synthetic same-zone DST-fold contexts formerly
mixed distinct instants; equivalent aware labels were sometimes falsely rejected.
Aware parsing/UTC comparisons reject missing, naive or malformed cutoffs. No real
persisted report leakage is inferred; the CLI already supplies one UTC cutoff.
New EQUITY_NOTE_VERSION v2-utc-context changes regenerated Markdown identity, not
original JSON, formulas, receipts or old files. Retained NVDA full JSON matches
exactly; CLI-style note content matches except the version label, and its DB/two
v1 note hashes remain unchanged. No network or new data capture. Thirty-four new
cases; focused renderer 57 passed. Full pytest: **3775 passed / 6 skipped**, 281.65
seconds; Ruff, mypy (314 files), governance (171 checks), scoped boundary/security
review and git diff --check pass. Mixed-tree checks are not isolated release or
source/strategy validation. No schema, dependency, defaults, trading, commit or
push changes. PIT UNSUITABLE, production NOT_READY; launch stays ready/not accepted.
Next: qualified source/session/financial evidence and real research/validation,
not automatic conversion of this diagnostic into buy/sell or sizing authority.

### Improved Turtle Price Observations: November 8

[Price observations](docs/turtle-price-observations-2026-11-08.md) expose the
existing Donchian/volume/arithmetic ATR calculations separately from unavailable
sentiment/industry inputs. Shared private arithmetic preserves three pre-change
full Trend assessment hashes exactly; no threshold or full assessment semantics
change. New central component version and optional read-only --trend-observations
bind raw original inputs/parameters/cutoff, retain invalid/latest-failure/
suspension/warm-up states and withhold all-four completeness/authority. Existing
JSON/Markdown remain unchanged without the flag. Reused NVDA November 6 sample:
about 186.64 versus prior 20-observation high 233.92, no strict breakout; volume
ratio about 1.591583 meets the configured research threshold, but both external
confirmations stay missing. No buy price, score or trade approval follows.
Ignored new JSON/note preserve the previous note and DB hash. Thirty-one new
cases pass. Full pytest: **3741 passed / 6 skipped**, 278.93 seconds; Ruff, mypy
(314 files), governance (171 checks), scoped import/credential review and git diff
--check pass. All four retained sample DB hashes are unchanged. Network-skipped
and synthetic tests do not certify source truth or strategy returns; mixed-tree
checks are not isolated release approval. No schema, dependency, defaults, trading,
commit or push. PIT UNSUITABLE, production NOT_READY and launch ready/not accepted
persist. Observation usefulness is not source/session/strategy/release admission.

### Single-Equity Usability Check: November 8

[Usability delivery](docs/single-equity-usability-2026-11-08.zh-CN.md) adds an
opt-in Chinese Markdown rendering to the existing US/HK/MY diagnostic CLI.
Original JSON stays default; rendering is read-only and rejects capture mode.
No parallel official report or new scoring/trade decision. Existing states,
missing financials and LOW/unassessed limitations stay explicit; inactive setup
references do not become current stops. Optional evidence extensions still need
the full JSON. Real NVDA Yahoo capture produced 752 daily/28 native financial
observations; at 2026-11-08T09:18:31.925654+00:00 the latest November 6 daily value
was about 186.64 USD, trend/momentum both BEARISH, old bullish setup INVALIDATED.
Native annual fields remain unqualified, not latest quarterly/verified accounting.
Data/JSON/Chinese note are ignored local evidence in the linked runbook, not Git
backup. Viewing/formatting leaves the new DB unchanged. Separate NVIDIA web
research is not adapter ingestion or numeric/sector admission. Twenty new unit
and seven CLI integration cases pass. Full pytest: **3710 passed / 6 skipped**,
223.30 seconds; Ruff, mypy (314 files), governance (170 checks) and git diff --check
pass. Raw new evidence remains ignored local data, not Git backup. Network skips
are not provider or strategy qualification. No schema,
dependency, defaults, strategy/trading/commit/push changes. PIT UNSUITABLE and
production NOT_READY persist; useful research assistance is not autonomous
validated advice, all-symbol coverage, launch acceptance or publishable baseline.

### Research Confidence UTC Integrity: November 8

[Research confidence repair](docs/research-confidence-utc-2026-11-08.md) closes
wall-clock comparisons in direct confidence helpers, shared assessment availability
maxima and ResearchAssessment's future-data guard. The synthetic old direct helper
gave 100 PIT integrity/confidence to an actually future DST-fold observation;
context/condition gates were already UTC-aware, so no real run leakage is claimed.
Current helpers use aware cutoffs/actual UTC; base maxima retain the original
latest timestamp and no tuple-order dependency. Calculation weights/thresholds,
technical formulas and four-confirmation rules are unchanged. New confidence
methods bind research-confidence-v2-utc centrally; explicit old stored methods
are preserved, not silently promoted. New metadata hashes may change; no old
report/data rewrite or schema change. Thirty-four new cases include official
Policy report persistence/reconstruction for current and legacy method labels.
Full pytest: **3683 passed / 6 skipped**, 209.43 seconds. Ruff, mypy (313 files),
governance (169 checks), scoped import/credential review and git diff --check pass.
Retained historical MSFT co-display hash/confluence and all three sample DB hashes
are unchanged. Synthetic/network-skipped tests are not provider or strategy
qualification, and mixed-tree checks are not isolated release approval. No source
capture, trading/commit/push or default changes; PIT UNSUITABLE, production NOT_READY
and launch ready/not accepted persist. This is not data/strategy/release admission.

### Nasdaq Producer-Clock Write Guard: November 8

The existing [source-age record](docs/nasdaq-calendar-freshness-2026-11-08.md)
now documents preventative rejection of nonzero-offset capture clocks before any
batch/fingerprint/evidence/raw retention. This stops writing new records known to
be unreconstructible; it does not normalize clocks, repair old identities or admit
unsupported sources. Normal zero-offset capture output and v1 hashes remain
unchanged; arbitrary aware read cutoffs and existing age checks still work.
Six new cases cover Malaysia/NY DST rejection without writes and equivalent UTC
labels; 72 Nasdaq cases pass. The synthetic legacy-record test continues to prove
old unsupported evidence is blocked, not silently migrated. Full pytest:
**3649 passed / 6 skipped**, 263.17 seconds. Ruff, mypy (313 files), governance
(168 checks), scoped import/credential review and git diff --check pass. Retained
v1 receipt and all three sample DB hashes are unchanged; no network capture.
Skipped external tests are not source/strategy validation. No schema,
provider interface, normalization version, dependency or default changes.
No trading/commit/push; PIT UNSUITABLE, production NOT_READY and launch
ready/not accepted persist. Mixed-workspace tests are not release/source/strategy
approval. Next: ordinary/exception-session and price-session qualification,
technical/fundamental method admission and actual validation; legacy clock repair
remains separate debt, not a reason to wait for the evidence horizon.

### Nasdaq Source-Age Guard: November 8

[Source-age receipt](docs/nasdaq-calendar-freshness-2026-11-08.md) adds an optional
positive integer capture-age limit to the existing offline reader/CLI. Exact UTC
microseconds since the verified original capture determine within-limit versus
stale; completion/review/event dates cannot rejuvenate it. Stale current rows are
withheld but observed rows, source status and hashes survive. Missing/latest bad/
unsupported inputs stay blocked without favorable fallback. Default v1 output
and its retained real-data hash remain exact/UNASSESSED; no default TTL or refresh
is introduced. LOW/retrieval-time and all false authorities remain unchanged.
Nineteen new synthetic cases (66 Nasdaq cases total) pass, including repeated DST
hour and offline CLI checks. Existing non-UTC producer-clock identity reconstruction
is a separately documented blocked compatibility limitation; default captures use
UTC. The real 12-row capture becomes zero current / 12 observed rows when stale
under an illustrative one-hour limit. All three sample DB hashes are unchanged.
Full pytest: **3643 passed / 6 skipped**, 274.62 seconds. Ruff, mypy (313 files),
governance (168 checks), scoped runtime import/credential review and git diff
--check pass. Network skips are not real provider verification. No schema,
dependency/default/trading/commit/push changes. PIT UNSUITABLE, production NOT_READY
and WP-LAUNCH ready/not accepted persist. Mixed-tree checks cannot qualify an
isolated release, source truth, strategy or the old unsafe GitHub candidate.

### US Session-Rule Audit And Design: November 7

[Regular-session/calendar contract](docs/proposals/us-regular-session-calendar-v1.md)
is a design/source-audit delivery, not implemented runtime behavior. Primary web
review found an October 30 Nasdaq notice announcing a December 6 expanded-hours
transition, while rule text also distinguishes commencement conditions. This is
not proof of current operation. Proposal separates civil observation date from
exchange trade date, regular/extended scope, source availability, policy effective
period and operative status. Legacy Yahoo/native bars and market-only calendars
do not prove these relationships; new holiday captures must not silently qualify
them. Exact source bodies and independent policy/bar-semantics review remain
required. Web research is not retained/PIT provider evidence. Regular-only work
may continue without admitting overnight data or waiting on the evidence horizon.
No source/runtime/schema/default/trading/commit/push changes; existing hashes and
captured data remain unchanged. Design acceptance cases are specified, not new
passed tests. Unchanged-runtime regression: **3624 passed / 6 skipped**, 240.62
seconds; Ruff, mypy (313 files), governance (167 checks), scoped documentation
review and git diff --check pass. All three retained sample DB hashes are unchanged.
Network skips do not validate the new web references or future operations. PIT
UNSUITABLE, production NOT_READY and launch ready/not accepted remain unchanged.

### Nasdaq Explicit Calendar Source: November 7

[Nasdaq source retention](docs/nasdaq-calendar-source-2026-11-07.md) now uses existing
provider-neutral ingestion/artifact/batch/evidence contracts for bounded fixed-URL
original HTML capture and strict year/table/date/status parsing. Raw body hash
and versioned envelope hash stay separate; exact-cutoff offline reads recheck
originals, registry and completed batches. Latest failures/ties/tampering cannot
fall back. Native early-close times remain explicit; unlisted dates are unknown.
LOW/retrieval-time is not official-domain trust admission, full calendar coverage,
original publication history, actual opening or scoring authority. No canonical
TradingSession mapping. New manual diagnostic CLI refuses existing files and
competing file creation; no automatic capture/migration/monitor activation.
Real November 7 capture: 54,628 bytes, 10 full-day closures/two early closes for
2026, with actual capture availability. Offline receipt repeats; October 27 reads
remain missing, and existing price/SEC DB hashes stay unchanged. New diagnostic
DB/raw bytes are ignored local evidence, not Git synchronization. 47 new synthetic
cases; full pytest: **3624 passed / 6 skipped**, 237.31 seconds. Ruff, mypy (313
files), governance (166 checks), scoped import/credential review and git diff --check
pass. Six opt-in network skips are not source evidence. No schema/default/trading/commit/push.
Next: source-bound ordinary-session/abnormal-event and historical coverage review,
then provenance-preserving period-coverage integration; do not flatten early
closes or backfill old decisions. PIT UNSUITABLE, production NOT_READY, disabled
defaults and launch ready/not accepted persist. Mixed-tree checks cannot qualify
the old unsafe GitHub candidate, independent source truth or actual strategies.

### Calendar Declaration Coverage: November 6

[Calendar/date comparison](docs/calendar-declaration-coverage-2026-11-06.md)
now checks existing TradingSession declarations against original visible daily
observations per local week/month. Missing calendar dates, missing declared-open
observations, closed-date conflicts and suspension observations remain distinct.
Unknown weekends are not inferred closed; unended/partial/conflicting periods
withhold coverage percentages. Conditional 100 percent is not verified sessions
or source quality: legacy calendar trust/precision stay UNKNOWN, all authorities
false. Original calendar v1/old default CLI outputs are unchanged; optional
--calendar-coverage reads calendar and prices within the same database snapshot.
SQLite now rejects non-bool calendar writes before any batch write and malformed
non-0/1 integer read states instead of truthy/truncating conversion. No migration,
old-row rewrite or new calendar provider. 45 new synthetic cases cover pure
comparisons, read-only/concurrent CLI integration and SQLite flag corruption.
Full pytest: **3577 passed / 6 skipped**, 251.68 seconds. Ruff, mypy (310 files),
governance (165 checks), scoped import/credential review and git diff --check
pass. Opt-in network skips are not source evidence. Retained MSFT has zero visible calendar
declarations in the requested window; source gaps persist and both real DB hashes
stay unchanged. Next: source-bound exchange calendar/price-action qualification,
period-trend policy and real research/validation, not automatic admission from
date agreement. No trading/commit/push. PIT UNSUITABLE, production NOT_READY,
disabled defaults and launch ready/not accepted persist. Mixed-tree checks do
not qualify an isolated candidate, source truth or the old unsafe GitHub commit.

### Calendar Week/Month Observations: November 6

[Calendar diagnostics](docs/calendar-period-diagnostics-2026-11-06.md) now aggregate
visible original daily versions into market-local weeks/months with Decimal OHLCV.
Missing intervals and suspension observations remain visible; current unended
periods withhold numbers and latest suspension blocks rather than selecting an
older active close. Calendar completeness, freshness and source adjustment truth
are explicitly unverified. Optional --calendar-periods is read-only, changes no
old CLI output without the flag and does not enter scores. Existing Technical
5/21-interval returns and configured observation-range position now expose proxy
basis metadata, prospectively v0.5.5; formulas/historical reports are unchanged.
Pure calculations support four equity markets; the existing global CLI still
supports US/HK/Malaysia only. Retained October 27 MSFT repeats 706 observations,
147 ended weeks/33 ended months with unverified coverage, one missing week and
one unended month. Previous SEC v1 hash and both DB byte hashes are unchanged.
30 new synthetic cases plus proxy-label assertions cover boundaries and CLI
compatibility. Full pytest: **3532 passed / 6 skipped**, 447.88 seconds. Ruff,
mypy (309 files), governance (164 checks), scoped credential/import review and
git diff --check pass. Six opt-in network skips are not source validation.
No schema, real-data write, source/score/strategy admission, trading, commit or
push. Remaining: qualified calendars/source/action basis, period-trend policy,
PIT size/universe and participation inputs, real research/validation and reviewed
deployment. PIT UNSUITABLE, production NOT_READY, disabled defaults and ready
(not accepted) launch status persist. Current mixed-tree tests cannot qualify
the old unsafe GitHub candidate or serve as independent data/strategy validation.

### SEC Period Inputs In Official Research: November 6

[Immutable SEC research input binding](docs/us-sec-research-binding-2026-11-06.md)
connects copied exact-period receipts to existing ResearchContext/Financial
assessment features and the single official ResearchReport persistence path.
It validates requested US equity/symbol/sector/cutoff, rejects parallel canonical
receipts or sector disagreement, rechecks chronology/false authorities/rows before
writes and preserves unavailable/conflicting states. Read cutoffs participate in
availability even with older facts. Financial is now v0.5.22-sec-period-inputs;
source/period versions, framework/schema/defaults and historical reports remain
unchanged. 25 new synthetic persistence cases across five sectors show Technical
and Financial reports reconstruct intact, remain INCOMPLETE and yield no
InvestmentScore. Real MSFT input binding repeats without DB writes or an invented
real queue/report; source receipt hash unchanged. **3502 passed / 6 skipped**,
216.00 seconds, including 67 new unit/integration cases. Ruff, mypy (308 files),
governance (163 checks), scoped security/import review and git diff --check pass.
Six opt-in network skips are not provider evidence; mixed-worktree checks are
not release-candidate or source/strategy qualification. No source/
sector scoring admission, schema/trading/commit/push. Next: qualified issuer/
share-class/accounting/sector definitions, real screened research and actual
strategy validation, plus technical/deployment gaps. PIT UNSUITABLE, production
NOT_READY and disabled defaults persist; launch remains ready, not accepted.

### US SEC Exact-Period Inputs: November 6

[Explicit period selections](docs/us-sec-period-inputs-2026-11-06.md) now bind
native SEC tags to exact duration or instant contexts via the retained body
reader. All matching occurrences and unresolved tag contexts remain visible;
no FY/form/12M/365-day annual inference, quarter fallback, aggregation, financial
alias or score is introduced. Optional --sec-period uses a derived v3 display
only; previous paths remain unchanged. Real retained MSFT reproduces six native
contexts across two July-June windows, with 67 unsupported source facts and four
checks retaining unresolved tag contexts. Both DB hashes are unchanged and
previous SEC v1 output hash is exact; not current data or financial admission.
**3435 passed / 6 skipped**, 208.66 seconds, including 42 new cases. Ruff, mypy
(308 files), governance (162 checks), scoped import/security review and
git diff --check pass. Checks cover the mixed worktree, not a publishable
candidate or independent source/strategy validation. No capture/schema/trading/
commit/push. Next: reviewed
source/period/sector binding into existing Financial Research, real screened
research and separately admitted validation. PIT UNSUITABLE, production NOT_READY,
disabled defaults and outstanding technical/deployment gates persist.

### US Issuer Declaration Review: November 6

[Source-bound declaration review](docs/us-issuer-declarations-2026-11-06.md)
compares requested US symbols to exact retained SEC ticker statements, preserving
mismatch, missing, null, empty, duplicate, unsupported and failed-source states.
One SQL snapshot and repeat original-byte checks bind catalog and claims;
exchange arrays stay separate, no ticker/name alias or share-class inference.
Optional --sec-identity uses a new derived/display version; previous SEC v1 and
no-SEC outputs remain unchanged. A match is TICKER_DECLARED_UNVERIFIED, never
verified identity or score/validation authority. 187 focused tests pass, with
40 new cases; full suite **3393 passed / 6 skipped**, 205.30 seconds. Ruff, mypy
(307 files), governance (161 checks), scoped security/dependency review and
git diff --check pass. Existing MSFT capture declares MSFT/Nasdaq, still
TICKER_DECLARED_UNVERIFIED; repeat receipt/display hashes agree, both database
hashes are unchanged and the previous SEC v1 combined hash remains exact.
No fresh capture, independent source calibration, financial/identity admission
or release-candidate verification follows. No schema, source-normalizer,
real-data write, capture, trading, commit or push. Next:
US fiscal/accounting/sector contracts and independently qualified identity inputs,
then the official screened research/validation chain. Existing PIT UNSUITABLE,
production NOT_READY and disabled defaults persist; launch remains unaccepted.

### US First Read-Only Increment: November 5

Tong prioritized US delivery for November 30, not live trading or abandonment of
the four-market scope. [Delivery tracking](docs/us-readonly-delivery-2026-11-05.zh-CN.md)
splits remaining work into evidence, sector/accounting contracts, technical
completion, official research/validation and deployment. Deadline is a target,
not approval or evidence. The existing global technical CLI now optionally reads
an explicit retained SEC CIK/accession at the same cutoff; no auto ticker join,
Yahoo/SEC numeric mapping, scoring or report creation. Same DB reads share one
snapshot; separate DB reads are labeled honestly. Latest missing/failure/conflict
states stay visible. **3353 passed / 6 skipped**, 208.20 seconds, including 24
new display cases. Ruff, mypy (307 files), governance (160 checks), scoped
dependency/security review and git diff --check pass. Independent read-only
review found no actionable findings. Retained historical MSFT reproduces 706
bars and nine same-origin SEC numeric matches at one cutoff; both database
hashes stay unchanged. Not fresh market data, independent numeric verification,
an exact pre-increment CLI golden test, or repaired-candidate release validation.
No source/sector scoring or R1-R6 acceptance follows. Next: source-bound US
identity/accounting/sector policy and official research/validation, with technical
and deployment gaps retained. PIT UNSUITABLE, production NOT_READY and disabled
defaults persist. No database/schema/trading change or commit/push.

### Prepared Local Ownership Primitive: November 5

WP-LAUNCH-001 [adds one prepared-coordinator lock](docs/prepared-resource-ownership-2026-11-05.md).
Existing private empty files are pinned and exclusively tried with POSIX flock;
no creation/deletion/re-pinning, no implicit provisioning or thread-only fallback.
Held tokens are process/session-bound; fork children close copied descriptors
without unlocking the parent. Uncertain release quarantines further use in that
process. This is not whole-resource coordination, capacity or capture approval;
existing writers and CLIs remain unwired. 22 new cases / 107 focused checks pass,
including real-process/fork scenarios. Full suite **3329 passed / 6 skipped**,
186.07 seconds. Ruff, mypy (307 files), governance (159 checks), scoped credential/
dependency review and git diff --check pass. Retained sample DB hashes unchanged;
six opt-in network skips are not provider evidence. Additive operational pin
version prepared-local-resource-lock-v1 only. No real archive/user-DB operation,
schema/default change, collection, trading, commit or push. Next: complete resource
mapping/group ownership and supervisor shutdown/size/retention integration.
PIT UNSUITABLE, production NOT_READY, R1-R6 partial; ready/not accepted.

### Committed Fetch Lease Guard: November 5

WP-LAUNCH-001 [implements the fetch-side read guard](docs/refresh-fetch-lease-guard-2026-11-05.md).
It rejects stale/wrong/terminal/non-FETCHING ownership and exact-expiry/backward
clocks, revalidates schema metadata and current static plan, and uses one new
read-only committed snapshot. Caller-store managed read/write contexts are
rejected through a context-local boolean, not a writable connection. The existing
RETAINING guard remains transaction-compatible. A pass is transient observation,
not a token, resource lock or capture approval; existing callers are not wired.

31 new synthetic/real-child-process cases; 104 focused checks pass. Full suite
**3307 passed / 6 skipped**, 161.37 seconds. Ruff, mypy (306 files), governance
(158 checks), scoped credential/dependency review and git diff --check pass.
Six opt-in network skips are not provider evidence; retained sample DB hashes
remain unchanged. No schema/record-version/default change, provider call, real archive
scan, user-DB migration, commit or push. Next: resource ownership/fork/descriptor
tests and bounded one-shot integration. GitHub repaired-candidate review remains
blocked separately. PIT UNSUITABLE, production NOT_READY, R1-R6 partial and
disabled defaults persist; WP-LAUNCH-001 ready/not accepted.

### One-Shot Admission And Recovery Design: November 5

WP-LAUNCH-001 [specifies one-shot admission/recovery](docs/proposals/one-shot-refresh-admission-v1.md).
A concurrent synthetic preflight example shows independent 900-byte projections
can both pass a 950-byte retained limit while joint proposed usage would be 1000.
No bytes are reserved or written by that example. The design pins cooperating
resource ownership, fresh under-lock capacity checks, CAS-before-fetch, bounded
capture-once handoff, exact receipts and phase-aware recovery. Fork-inherited
locks, external writers and DB/cache/staging budgets remain implementation gates.
At the initial design delivery no runtime lock/reservation, fetch-side guard,
worker, scheduler or activation existed. The fetch-side guard is now recorded
separately above; this design did not implement those controls. One new test /
112 focused checks; full suite **3276
passed / 6 skipped**, 157.09 seconds. Ruff, mypy (306 files), governance (157
checks), scoped dependency/credential review and git diff --check pass. Both
retained sample DB hashes remain unchanged. Six opt-in network skips are not
provider evidence. No provider call, real archive scan, user-DB migration, commit
or push; no schema/default/model version or production-source/trading change.
PIT UNSUITABLE, production NOT_READY, R1-R6
partial, WP-LAUNCH-001 ready/not accepted.

### GitHub Sync Blocker: Last Verified November 4

The last sync review extracted exact candidate 8794b57 (tree a90eeea4) and
reproduced the historical shared-original rollback deletion: one synthetic probe
failed against the candidate, passed against the current local repair. That local
comparison and working-tree suite are NOT candidate release validation. No push
occurred; remote was 6be0a84 on codex/wp-launch-001-hardening at that observation.
SSH read-only query succeeded, not proof of push permission. This November 5
design run does not re-query the remote or promote yesterday's SHA to current.
The older candidate must not be published alone; prepare a bounded repaired
candidate and complete exact-tree checks/independent review. Recent local work
remains unsynchronized. This run makes no commit, push or index/history change.

### Read-Only Artifact Capacity Preflight: November 4

WP-LAUNCH-001 [adds capacity diagnostics](docs/artifact-capacity-preflight-2026-11-04.md):
explicit byte budgets, bounded no-follow single-volume metadata inventory and
conservative free-space checks. Counts unregistered/temp/hard-linked names;
unsafe, changed, unreadable or incomplete scans cannot claim favorable totals.
WITHIN_DECLARED_LIMITS is not a reservation or enforced quota. Existing writers
are not wired to this preflight; no capture/cleanup/schedule is activated.

40 new synthetic cases / 111 expanded focused checks pass. Full suite **3275
passed / 6 skipped**, 170.62 seconds. Ruff, mypy (306 files), governance (156
checks), scoped credential/dependency review and git diff --check pass. Six
opt-in network skips are not source availability evidence. Both retained sample
DB hashes remain unchanged. Additive readonly-artifact-capacity-v1 only.
Only temporary synthetic archives are scanned; no real archive capture, sample
DB change, default budget/schema/migration change,
commit, push or trading-layer change. Next: serialized one-shot admission and
reservation/recovery contract before integration. PIT UNSUITABLE, production
NOT_READY, R1-R6 partial and disabled defaults persist; launch ready/not accepted.

### Read-Only Exact Refresh Inspection: November 4

WP-LAUNCH-001 [adds exact job/batch/original inspection](docs/refresh-reconciliation-2026-11-04.md).
One SQL snapshot checks ledger/plan/scope, migration checksums/fingerprint, exact
batch/fingerprint/evidence/observations and explicit original references. Shared
secure bounded byte checks reject missing/corrupt/unsafe originals. Earlier first
registry ownership is allowed only with its explicit valid owner; missing links
never guess by symbol/date/hash. Failed snapshot bytes remain failed.

No repair/reset/checkpoint, collection, schema/default change or trading admission.
Current-snapshot cutoff is not historical DB reconstruction; unsigned SQL/file
hashes do not authenticate source truth. 37 new synthetic tests; full suite
**3235 passed / 6 skipped**, 174.35 seconds. Ruff, mypy (304 files), governance
(155 checks), scoped credential/dependency review and git diff --check pass.
Six opt-in network skips are not provider availability proof. Both retained
sample DB hashes remain unchanged. Additive readonly-refresh-reconciliation-v1;
framework/schema/migration/defaults unchanged. No user sample DB change, commit
or push. Next: bounded capacity,
one-shot capture integration and cross-store recovery acceptance. PIT UNSUITABLE,
production NOT_READY, R1-R6 partial and disabled defaults persist; ready/not accepted.

### Shared Artifact Rollback Retention: November 4

WP-LAUNCH-001 [fixes shared-original rollback deletion](docs/artifact-rollback-retention-2026-11-04.md).
A synthetic reproduction confirmed creator rollback could remove bytes another
writer had adopted. FileSystemArtifactStore.discard now retains all published
content; created is publication history, never an exclusive deletion lease.
Failed transactions still publish no database evidence; retained unregistered
bytes are not successful data or research admission. No registry-only or TTL GC.

13 new cases / 364 expanded focused checks pass, including a real child process,
interleaved ingestion into same/separate databases, daily price/lifecycle and
manual filing rollback cases. Full suite **3198 passed / 6 skipped**, 162.19 seconds.
Ruff, mypy (302 files), governance (154 checks), scoped dependency/credential
review and git diff --check pass. Six opt-in network skips are not provider
availability evidence. Both retained sample database hashes remain unchanged.
Additive content-addressed-retention-v2-concurrent-rollback policy version only;
framework/schema/migration/evidence/model/default versions otherwise unchanged.
No actual source capture, user data change, commit, push or trading-layer change.
Next: exact job/batch/original reconciliation and capacity limits before bounded
one-shot capture; orphan inventory, global-reference-safe GC, directory durability
and encrypted restore remain separate unmet controls. Registered-only audit does
not inventory or qualify unregistered files. PIT UNSUITABLE, production NOT_READY,
R1-R6 partial and disabled defaults persist; launch stays ready/not accepted.

### Durable Refresh Ledger And Reviewed GitHub Sync: November 3

WP-LAUNCH-001 [implements SQLite refresh persistence](docs/refresh-ledger-persistence-2026-11-03.md):
immutable registration, persisted claims, generation/nonce/version CAS, finite
observed-fetch retry, expiry -> reconciliation, and optional typed refresh_lease
batch/evidence association inside the existing ingestion transaction. No worker,
collector schedule, full reconciliation verifier, checkpoint or data admission.
Legacy unleased ingestion retains its pre-fetch audit gap.

New 0011_refresh_ledger / schema 0.8.3; old 0010 definition pinned, old checksums
and baseline SCHEMA unchanged. Retained user databases remain unmodified; migrate
only in reviewed restored copies. Attempts v2 adds retention-specific safe codes;
ledger sqlite-data-refresh-ledger-v1. Framework/plan/Financial/defaults unchanged.
36 new persistence cases; 129 focused checks pass. Full suite **3185 passed /
6 skipped**, 162.98 seconds. Ruff, mypy (302 files), governance (153 checks),
scoped source/credential/boundary review and git diff --check pass. Six skips
remain opt-in real network tests, not provider availability proof. Both retained
sample database hashes remain unchanged. PIT UNSUITABLE,
production NOT_READY, R1-R6 partial and disabled defaults persist.
Next: original-byte concurrency, exact reconciliation/restore verification,
then bounded one-shot capture and separately reviewed activation.

User-approved [reviewed GitHub sync](docs/github-reviewed-sync-2026-11-03.md) is
ACTIVE daily 05:00 Malaysia time, bound to this chat; development 02/03/04 unchanged.
Only complete reviewed candidates passing isolated-tree checks may commit/push;
mixed unreviewed files, secrets, artifacts, divergence or auth failure block it.
SSH read-only probe passed; remote 6be0a84 is ancestor of local 8794b57 by one
commit. Later work stays mixed/uncommitted. No commit or push this slice.

### Refresh Attempt / Recovery Contract: November 3

WP-LAUNCH-001 [adds pure attempt transitions](docs/refresh-attempt-contract-2026-11-03.md)
with immutable policy/lease identities, UTC chronology, finite fetch retry,
phase-aware failure and mandatory reconciliation after expiry or retention.
Stored-data and stored-failure declarations are not verified receipts or checkpoints.
No SQLite claim, pre-fetch persistence, concurrency CAS, worker or scheduler is
implemented; the existing ingestion gap remains until explicit atomic integration.
The [ledger migration proposal](docs/proposals/data-refresh-ledger-v1.zh-CN.md)
specifies two tables, atomic batch association, fingerprint/backup requirements
and crash recovery. Proposed 0011 / 0.8.3 are not registered or applied.

57 new cases; 139 focused checks pass. Full suite **3149 passed / 6 skipped**,
142.24 seconds. Ruff, mypy (301 files), governance (151 checks), scoped
dependency/credential review and git diff --check pass. The skipped real network
tests do not establish provider availability. Both retained sample database
hashes remain unchanged. Additive data-refresh-attempt-v1 only;
framework/schema/plan/Financial/defaults unchanged.
Next: reviewed ledger migration/repository in isolated test databases, concurrent
CAS and same-transaction evidence binding, then controlled one-shot collection.
PIT UNSUITABLE, production NOT_READY, R1-R6 partial and disabled defaults persist.
No user-data/network/trading-layer change, commit or push.

### AI-Assisted / Independent Operation And A-Share Refresh Requests: November 3

The [confirmed product boundary](docs/ai-assisted-and-independent-operation.zh-CN.md)
supports AI-assisted research interaction and future AI-independent data/rule
operation through the same research/validation/risk gates. AI language is not
evidence, strategy approval, a current buy/sell decision or execution authorization.
Automatic facts/re-evaluation must not become automatic strategy/governance changes.

The [A-share static refresh bridge](docs/akshare-offline-refresh-bridge-2026-11-03.md)
converts bounded equity scopes into existing DailyBarRequest, not the post-capture
evidence request. Explicit route/currency declarations and NONE are checked;
unknown routes/datasets stay visible, real listing/status/source trust stay unknown.
All five example requests now validate statically; no fetch/DB/scheduler is enabled.
Plan version offline-data-refresh-plan-v2-akshare-request; framework/schema/defaults
and other models unchanged. 23 new cases, 69 focused cases pass; full suite
**3092 passed / 6 skipped**, 155.04 seconds. Ruff, mypy (300 files), governance
(149 checks), scoped dependency/credential review and diff checks pass. The six
skips are opt-in real network tests, not verified provider availability. Retained
price/native and original-document database hashes remain unchanged.
Next: dedicated durable attempt/job migration and recoverable one-shot worker.
PIT UNSUITABLE, production NOT_READY, R1-R6 partial, disabled defaults persist.
No trading-layer change, actual collection, commit or push.

### Offline Refresh Planner: November 3

WP-LAUNCH-001 [implements the first offline refresh stage](docs/offline-data-refresh-plan-2026-11-03.md).
Strict bounded explicit scopes -> existing static Yahoo request validation ->
deterministic JSON plan with config/scope/version/UTC/Git context. Four-market
example retains all five scopes: four Yahoo requests validate statically; A-share
AKShare remains an explicit unsupported refresh bridge, not an ingestion defect.
No collection, provider permission test, inventory/due/freshness calculation,
database access, installed schedule or research admission. All authority flags
stay false; calendar, trust, availability and precision remain unobserved.

46 new cases; full suite **3069 passed / 6 skipped**, 145.80 seconds. Ruff, mypy
(300 files), governance (147 checks), unchanged retained DB hashes and diff checks pass.
Framework/schema/
Financial/defaults unchanged; additive offline-data-refresh-plan-v1 only.
Next: explicit source bridges and durable job/attempt design before a bounded
one-shot worker and separately reviewed activation. PIT UNSUITABLE, production
NOT_READY, R1-R6 partial, ready/not accepted, disabled defaults persist.
No trading-layer change, user-data write, commit or push.

### Automated Refresh Design: November 3

WP-LAUNCH-001 [defines a bounded automated-data refresh proposal](docs/proposals/automated-data-refresh-v1.zh-CN.md)
following Tong's automatic-update question. Existing health monitoring is not a
daily research-universe refresh. Proposed stages: offline explicit-watchlist plan,
persistent recoverable one-shot worker, separately reviewed scheduler activation,
then independently admitted research refresh. No service or new feature activated.

A temporary synthetic stopped-fetch exercise confirms provider-neutral ingestion
has no persisted attempt/batch if fetch raises before returning; evidence rows
also remain zero. This is a scheduler audit/recovery gap, not corrupt committed
data. Completed ingestion can also retain a failed-source snapshot; it cannot
be interpreted as successful data refresh. Proposed job/attempt ownership and
transaction/checkpoint/recovery requirements precede unattended deployment.

Design/governance documents only: no runtime/schema/version/default or user-data
change, no network, commit, push or installed schedule. Existing follow-up task
unchanged. Regression: **3023 passed / 6 skipped**, 153.54 seconds; no new tests
or runtime behavior claimed. Ruff, mypy (298 files), governance (146 checks),
scoped whitespace, unchanged retained DB hashes and diff checks pass.
Six skips remain opt-in network cases. Next is scoped offline refresh
planning and attempt/recovery implementation within current launch boundaries;
activation still requires scope/host/access review. Source/sector qualification,
latest filings, R1-R6 acceptance and encrypted cross-device retention remain open.
PIT UNSUITABLE, production NOT_READY, disabled defaults and launch ready/not accepted persist.

### Original Document Freshness: November 2

WP-LAUNCH-001 [separates report/source/review ages](docs/original-document-freshness-2026-11-02.md)
in existing immutable HK/MY receipt diagnostics, Financial report features and
opt-in CLI --review-freshness. Re-review cannot rejuvenate old source/period;
UTC elapsed times and market-local report dates remain distinct. Missing/failed
receipts have null ages and no fallback. Both configured age limits default zero,
UNASSESSED; within a declared limit never approves source/latest-filing/scoring.

36 new cases and expanded report persistence coverage; 206 focused cases pass.
Full suite **3023 passed / 6 skipped**, 199.04 seconds. Ruff, mypy (298 files),
governance (145 checks), scoped import/output credential and diff checks pass.
Six skips remain opt-in network tests. Real retained Maybank three receipts reproduce
at November 2 cutoff without writes or network; report annotations are 306 days
old, not publication ages or proof of latest disclosure. Document DB unchanged,
no new artifacts/tables/migrations. Financial version financial-v0.5.21-document-freshness;
framework/schema unchanged. New default source-age key changes configuration identity.
An explicit one-day retained-price age example also withholds stale technical
calculations; this rechecks the existing price gate, not an admitted age policy.

Next: reviewed source/sector/freshness specifications, latest disclosure evidence
and real screening/research/validation; no implicit financial policy admission.
PIT UNSUITABLE, production NOT_READY, R1-R6 partial, launch ready/not accepted,
disabled defaults persist. No trading-layer change, commit or push.

### Read-Only Ratio Source Selection: October 31

WP-LAUNCH-001 [exposes explicit multi-document ratios in the existing read-only CLI](docs/readonly-ratio-source-selection-2026-10-31.md).
Primary plus up to three unique supplemental URLs remain distinct beside technical,
native-financial and monetary inputs. All review documents share one SQLite
snapshot; separate price/review files still share only a cutoff, not atomicity.
Competing-writer tests preserve the current snapshot and expose new failure on the
next read. Missing/latest-bad/unknown-period inputs cannot be replaced or scored.
No official ResearchReport or buy/sell output is created by this co-display.

New additive panel version global-review-ratio-display-v1; old no-ratio output/
hashes and source/Financial/framework/schema versions unchanged. 15 new cases,
38 focused checks; full suite **2987 passed / 6 skipped**, 143.62 seconds. Ruff,
mypy (297 files), governance (144 checks), scoped import/credential and diff
checks pass. Six skips remain opt-in network cases. Real retained
Maybank six-/three-row ratios reproduce at one cutoff without network or writes;
both local evidence databases remain byte-unchanged. No new raw evidence/schema.

Next: admitted source/sector/freshness methodology and real screened technical +
fundamental research/validation. PIT UNSUITABLE, production NOT_READY, R1-R6
partial, launch ready/not accepted and disabled defaults persist. No trading-
layer change, commit or push; encrypted co-retention remains outstanding.

### Multi-Document Ratios In Research: October 31

WP-LAUNCH-001 [adds optional supplemental ratio receipts](docs/multi-document-ratio-research-2026-10-31.md)
to existing ResearchContext/Financial/official ResearchReport persistence. One
primary and up to three unique documents retain full independent receipts;
same-equity/cutoff/sector/hash/authority validation precedes run writes. Canonical
ordering preserves determinism; missing/failed sources stay visible. Primary
questions/equations never search supplements or merge similarly named metrics.
All bound cutoffs govern availability; outputs remain INCOMPLETE/unscored.

36 HK/MY focused cases pass, including SQLite reconstruction, primary/supplement
failure isolation and no InvestmentScore. Real retained six-/three-row Maybank
receipts reread together without network, writes or fabricated queue/report.
Document DB remains at 11 evidence/artifact/batch rows; no new artifacts/schema.
Financial version financial-v0.5.20-multi-document-ratios; framework 0.8.0 / schema
0.8.2 unchanged. Verification: **2972 passed / 6 skipped**, 124.15 seconds. Ruff,
mypy (297 files), governance (143 checks), scoped import/credential, retained DB
hashes and diff checks pass. Six skipped cases are opt-in network checks.

Next: explicit source selection in read-only delivery, current/qualified source
and sector methodology, real screened technical/fundamental research/validation.
PIT UNSUITABLE, production NOT_READY, R1-R6 partial, launch ready/not accepted,
disabled defaults persist. No trading-layer change, commit or push.

### Separate Bank Liquidity Source: October 31

WP-LAUNCH-001 [retains the separate Integrated Annual Report](docs/bank-liquidity-source-evidence-2026-10-31.md)
and three original liquidity percentages via existing adapters/readers. Full-page
visual review finds LCR/NSFR/LDR. LCR has a rolling 12-month average note,
conservatively unknown basis, not a year-end instant equation. All remain single-
review LOW/RETRIEVAL_TIME, definition-required, freshness unknown and unscored.
No implied regulatory scope, formula, cross-document merge or policy admission.

Document DB now has 11 evidence/artifact/completed-batch rows, no canonical facts,
reports/signals or FK errors. Old 31-row money/six-row ratio reads and old-cutoff
hashes remain exact; price DB unchanged. New ignored bytes need encrypted
co-retention. No runtime/schema/version or trading change, commit or push. Next:
independent source/averaging/perimeter review, latest-period evidence and explicit
multi-document financial research/validation. PIT UNSUITABLE, production NOT_READY,
disabled defaults, R1-R6 partial and launch ready/not accepted remain unchanged.
Verification: **2936 passed / 6 skipped**, 120.89 seconds; four new cases. Ruff,
mypy (297 files), governance (142 checks), scoped plan credential/import and diff
checks pass. Six skipped tests are opt-in network checks, not source qualification.

### Explicit Ratio Arithmetic: October 31

WP-LAUNCH-001 [adds source-pinned cross-receipt percentage equations](docs/manual-ratio-arithmetic-2026-10-31.md)
to existing unscored Financial report features. Explicit plans pin both review
IDs/envelopes/PDF and availability; context/source/period/unit/precision mismatch,
missing/unresolved cells, nonpositive denominators and stale pins remain visible.
Only instant ratios over same-unit/currency balances are supported, no annual ROE
averaging, aliases, tolerances or favorable alternatives. Exact rational and rounded
residuals are distinct; half-even rounding is proposed, not issuer-verified.

Real Maybank's three explicit equations repeat at one cutoff/snapshot and reproduce
the printed decimal places; their unrounded residuals are nonzero. Neither database
changes. Synthetic HK/MY Technical + Financial reports retain all diagnostic states
through SQLite, stay INCOMPLETE/unscored and cannot create InvestmentScore. Five
bank ratio-policy gaps and three external dependencies remain unresolved.

Financial version financial-v0.5.19-ratio-arithmetic, arithmetic version
global-original-ratio-arithmetic-v1; source/framework/schema unchanged. Next:
independent definition/source/regulatory review, numeric liquidity/latest filings,
admitted sector methodology and real research/validation. No network capture,
trading-layer change, commit or push. PIT UNSUITABLE, production NOT_READY,
disabled defaults, R1-R6 partial and launch ready/not accepted persist.
Verification: **2932 passed / 6 skipped** in 128.78 seconds; 40 new cases plus
expanded HK/MY report coverage. Ruff, mypy (297 source files), governance (141
checks), scoped import/credential and diff checks pass. Six opt-in real-network
tests remain skipped. Retained real databases stay byte-unchanged.

### Bank Capital And Attributable Equity Evidence: October 31

WP-LAUNCH-001 [completes the interrupted source editions](docs/bank-capital-equity-evidence-2026-10-31.md).
Existing 22 income rows are preserved in a new 31-row monetary review with
attributable equity/NCI, regulatory capital/RWA and net impaired/net loans.
Six-row ratio edition adds original Note 12 detail and Note 59 scope annotations.
All remain single-review LOW/RETRIEVAL_TIME; financial equity, regulatory capital,
net/gross impaired loans and annual ROE cannot be conflated or scored.

New explicitly pinned 19-question draft plan: 11 unqualified annotation matches,
five ratio contracts and three external dependencies. Numeric LCR remains missing
from this review; selected liquidity narrative is not a ratio value or proof of
issuer-wide nondisclosure. Old editions and cutoff hashes remain exact; stale plan
blocks at the new cutoff without rebinding. Resumed checks do not repeat ingestion.
Real document DB has nine evidence/artifact/completed-batch rows, zero canonical
facts/reports/signals and no FK errors. Same-cutoff reads repeat without DB writes.

No runtime/schema/model-version changes, network capture, trading change, commit or
push. Next: explicit cross-receipt arithmetic questions without policy admission,
separate dated liquidity/current filing sources and independently reviewed sector
policy, then real research/validation. Known Bank revenue discrepancy and encrypted
co-retention remain open. PIT UNSUITABLE, production NOT_READY, disabled defaults,
R1-R6 partial and launch ready/not accepted persist.
Verification: **2892 passed / 6 skipped** in 144.75 seconds; 14 source-edition
cases. Ruff, mypy (296 source files), governance (140 checks), source-plan
credential and diff checks pass. Six opt-in real-network tests remain skipped.
No new provider probe or independent numerical/source qualification is claimed.

### Original Ratios In Official Research: October 30

WP-LAUNCH-001 [binds original ratio receipts](docs/original-ratio-research-binding-2026-10-30.md)
to the existing ResearchContext/Financial/report persistence, distinct from monetary
V1 and canonical financial inputs. Immutable copied receipts revalidate identity,
UTC cutoff, strict rows, hash, trust/precision and false authorities before direct
evaluation or run writes; sector disagreement, non-equities, tampering and parallel
canonical receipts reject. Missing/current-source failures remain visible.

Explicit optional original-row questions preserve unresolved/missing/definition-
required states; configured questions without a ratio receipt reject. All require
independent definition/denominator/regulatory/period review, never bank policy or
metric equivalence. Existing draft plan still has five ratio/four external gaps.
Synthetic HK/MY Technical + Financial reports reconstruct all receipts, stay
INCOMPLETE/unscored and cannot create InvestmentScore. Real Maybank questions
repeat at a fixed cutoff without data writes or inventing a real queue/report.
An independently reproduced availability defect is repaired: old raw facts cannot
make an assessment containing later native/manual/ratio receipts appear available
before those receipts' read cutoff. Regression checks cover all three slots,
including missing/failed states; old stored reports are not silently rewritten.

Financial version financial-v0.5.18-original-ratio-receipts; source/framework/schema
unchanged. Next: original bank definitions/liquidity/equity evidence, independently
admitted source/sector/freshness policy and real research/validation. Encrypted
co-retention and known summary/statement discrepancy remain unresolved. No trading-
layer/network change, commit or push; PIT UNSUITABLE, production NOT_READY,
disabled defaults, R1-R6 partial and launch ready/not accepted remain unchanged.
Verification: **2878 passed / 6 skipped** in 165.76 seconds; 34 new cases and
expanded HK/MY report/availability regressions. Ruff, mypy (296 source files),
governance (139 checks), scoped import/credential and diff checks pass. Six opt-in
real-network tests remain skipped; real retained databases remain byte-unchanged.

### Original Bank Percentage Evidence: October 29

WP-LAUNCH-001 [adds an independent HK/MY percentage contract](docs/global-bank-ratio-evidence-2026-10-29.md)
and source-pinned retained ingestion/read path through existing SQLite/artifacts.
Five real Maybank Group 2025 summary ratios are preserved with original units,
annual/instant periods, page/column and explicit unknown definitions/denominators/
regulatory scope. Values above 100% and negative values are permitted, missing
cells stay null; no monetary scaling, canonical aliases or metric/policy admission.
Actual recording, current parent/ownership/hash checks and latest-failure/tie/
future rejection stay fail-closed. Existing CLI adds opt-in `--kind ratio`.

New ratio version global-document-ratio-review-v1; monetary V1 and Financial
versions unchanged. Document database now has seven evidence/artifact/batch rows,
zero canonical facts/reports/signals, no FK errors; old 22-row monetary receipt
hash is unchanged. New fixed-cutoff ratio reads repeat without database writes.
Raw ratio evidence is not yet bound to official ResearchContext or draft bank
checklist: five ratio questions/four external dependencies remain unresolved.
Next: explicitly source-bound ratio research questions and immutable report
evidence, then sector/source/freshness admission and real research/validation.
No schema/trading-layer/network change, commit or push. Ignored new evidence needs
encrypted co-retention. PIT UNSUITABLE, production NOT_READY, execution/notifications
disabled, R1-R6 partial and launch ready/not accepted remain unchanged.
Verification: **2844 passed / 6 skipped** in 181.47 seconds; 57 new cases. Ruff,
mypy (294 source files), governance (138 checks), scoped import/credential and
diff checks pass. Six opt-in real-network tests remain skipped; retained-file
reproduction does not establish independent calibration or current availability.

### Same-Filing Annual Comparatives: October 29

WP-LAUNCH-001 [adds seven Maybank comparative rows](docs/manual-income-comparatives-2026-10-29.md)
in a new 22-row review edition, preserving the previous 15 rows and old-cutoff
receipt. New plan pins are explicit; the old plan blocks at the new cutoff rather
than rebinding. Current draft coverage is eight unqualified matches, five ratio
contracts and four external dependencies. No source/sector policy admission.

Existing CLI/Financial report features now retain explicit same-filing annual
changes: exact labels/scope/units/roles/windows only, no older favorable fallback.
Seven real pairs reproduce; one negative prior base withholds percentage. These
are filing comparatives, not original historical vintages or verified business
growth. Configured manual diagnostics without a receipt now reject explicitly.
Financial model financial-v0.5.17-manual-income-changes; all scores still absent.

Real document database has six evidence/artifact/batch rows and zero canonical
facts/reports/signals; new ignored evidence needs encrypted co-retention. Source/
schema unchanged; read-only reproduction preserves database hashes. Next: reviewed
overseas bank ratio/equity contracts, source admission and real research/validation.
PIT UNSUITABLE, production NOT_READY, defaults disabled; R1-R6 partial and launch
ready/not accepted. No trading-layer change, network capture, commit or push.
Verification: **2787 passed / 6 skipped** in 124.34 seconds, 25 new cases.
Ruff, mypy (292 source files), governance (137 checks), scoped import-boundary
and diff checks pass. Six opt-in network tests remain skipped; retained-file
reproduction is not independent source calibration or a live provider probe.

### Source-Defined Bank Input Coverage: October 29

WP-LAUNCH-001 [adds explicit draft bank input questions](docs/bank-source-input-coverage-2026-10-29.md)
to the existing global CLI and Financial report feature path. Plans bind exact
review/envelope/PDF pins, context, chronology and monetary annotations, without
numeric expectations, weights or aliases. Missing review rows, annotation/value
issues, unsupported ratios and external dependencies remain distinct; bad/current-
changed sources cannot rebind or fall back. No input-coverage score or admission.

Real Maybank draft coverage: seven matched unqualified annotations, one absent
prior-year review row, five unsupported ratio contracts, four external evidence
dependencies. Period age is 302 days, separately from review capture age; freshness
and latest issuer filing remain unverified. Two fixed-cutoff outputs repeat with
unchanged databases. Synthetic report reconstruction keeps coverage JSON but
Financial unscored / report incomplete / no InvestmentScore. No real queue invented.

Financial model financial-v0.5.16-bank-document-inputs; source/schema unchanged.
Next: preserve a new review edition for the prior-year column, then source-defined
ratio/equity/valuation contracts and independently reviewed sector methodology.
PIT UNSUITABLE, production NOT_READY, defaults disabled; R1-R6 partial. No trading-
layer change, new data write, provider request, commit or push. Existing raw data
still needs encrypted co-retention. WP-LAUNCH ready, not accepted.
Verification: **2762 passed / 6 skipped** in 129.44 seconds, 24 new cases.
Ruff, mypy (292 source files), governance (136 checks), scoped forbidden-import
and diff checks pass. Six opt-in network tests remain skipped; repeated retained
reads are not live availability, source/sector approval or strategy validation.

### Reviewed Primary Documents In Official Research: October 29

WP-LAUNCH-001 [binds manual HK/MY source receipts](docs/reviewed-document-research-binding-2026-10-29.md)
to the existing immutable ResearchContext and Financial assessment/report storage.
No parallel research outcome model or schema. Copy/hash/context/chronology/strict
row reconstruction checks run before evaluation and run writes. Missing/failed
states persist; native and manual receipts can coexist without aliases, but
conflicting requested sectors, non-equities and parallel canonical receipts reject.

Synthetic HK/MY Technical + Financial reports retain the exact manual receipt
through SQLite reconstruction while remaining INCOMPLETE/unscored. Real factory
reads repeat four Tencent / 15 Maybank rows plus 28 native rows separately, with
unchanged databases; no real queue or report is invented from exploratory captures.
Financial model is financial-v0.5.15-reviewed-document-binding; old packets/records
remain unchanged. Known revenue discrepancy and new-evidence encrypted backup
requirements remain open; factory receipts do not requery a live database on use.

Next: separately reviewed bank metric/sector policy and real screened research /
preregistered validation, not guessed Yahoo aliases or arbitrary weights. R1-R6
partial, WP-LAUNCH ready/not accepted, PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled. No trading-layer changes, commit or push.
Verification: **2738 passed / 6 skipped** in 111.90 seconds, 33 added cases.
Ruff, mypy (291 source files), governance (135 checks), scoped forbidden-import
and diff checks pass. Opt-in real network tests stay skipped; retained local
reader reproduction is not a live provider probe or strategy validation.

### Bank Income Transcription And Arithmetic: October 28

WP-LAUNCH-001 [adds explicit signed income sums](docs/bank-income-arithmetic-2026-10-28.md)
to the existing global technical CLI and appends 15 real Maybank statement rows
through the existing unqualified manual-evidence contract. Four declared same-
column sums agree exactly as transcribed. Scope/period/currency/unit/column and
restatement labels must match; missing/unresolved rows stay null, small residuals
cannot round away and expense signs are never inferred. No schema/canonical fact.

Visual review of the retained statement and Note 35 clarifies gross/net, Islamic,
insurance and Group/Bank distinctions, not Yahoo aliases. An unresolved Bank
revenue summary/statement discrepancy is recorded explicitly, never corrected.
The current document database has five records/artifacts/batches; prior reviews
and the old cutoff receipt remain exact. New data needs encrypted co-retention.
Two same-cutoff outputs repeat; read-only passes do not change either database.

PIT UNSUITABLE, production NOT_READY, defaults disabled and R1-R6 partial.
No Paper/Broker/Portfolio/Notification/live change, commit or push. Next: admitted
source-defined bank metric/sector policy and real screened research/validation,
without forcing primary statements to fit Yahoo names or unapproved scores.
Verification: **2705 passed / 6 skipped** in 103.96 seconds, 29 added cases.
Ruff, mypy (290 source files), governance (134 checks), scoped forbidden-import
and diff checks pass. Real reproduction uses retained bytes, not a fresh network
probe or independent numeric calibration. Ignored evidence is not a Git backup.

### Explicit Native/Manual Financial Candidates: October 28

WP-LAUNCH-001 [adds optional explicit candidate-pair review](docs/global-native-manual-candidates-2026-10-28.md)
to the existing global technical CLI. Exact retained receipts bind the same UTC
cutoff, input hashes and all requested alternatives. Unknown scope/units/flow
start, precision, revisions, publication and source identity remain blockers;
missing/latest-bad/ambiguous inputs cannot select an older or closer number.
Default output without candidate arguments stays unchanged. No schema/data write.

Eight real retained HK/MY candidate questions reproduce exactly with both
database hashes unchanged. Tencent total/parent profit differ; Maybank's displayed
Yahoo income differs from both manual revenue labels. These are unresolved native
definitions, not proven provider defects. Equal profit amounts or rounded summary
proximity cannot admit a mapping, numeric consistency, score or investment decision.
Next: exact banking statement/definition review and versioned sector policy, then
actual screened research and registered technical-plus-fundamental validation.

PIT UNSUITABLE, production NOT_READY, execution/notifications disabled, R1-R6
partial, WP-LAUNCH-001 ready/not accepted. No Paper/Broker/Order/Portfolio/live
changes, commit or push. New ignored evidence still needs encrypted co-retention.
Verification: **2676 passed / 6 skipped** in 113.04 seconds, 44 added cases.
Ruff, mypy (290 source files), governance (133 checks), scoped forbidden-import
and diff checks pass. Six opt-in real network tests remain skipped; this slice
made no provider requests and cannot claim live availability or calibration.

### Technical And Reviewed-Filing Display: October 28

WP-LAUNCH-001 [extends the existing global technical CLI](docs/global-review-display-2026-10-28.md)
with paired explicit HK/MY review-database/document options, not another engine.
One cutoff preserves independent price/native/manual statuses; same-file reads
reuse one snapshot, separate databases explicitly do not claim cross-database
atomicity. Nested receipts/parameters and the payload bind a combined display hash.
Default no-review output remains unchanged; capture/US manual-review combinations
are rejected. Missing/bad inputs cannot borrow older values or auto-fill fields.

Two real offline co-displays repeat exactly: 0700.HK has 692 price observations /
four manual rows with different currency labels; 1155.KL has 690 / four with
same-but-unverified labels. Neither label agreement nor co-display admits field/
accounting correspondence, provider numeric consistency, valuation, scoring,
research-report creation or validation. Both databases preserve their hashes.
No provider refresh or data/schema/dependency/trading-layer write was introduced.
PIT UNSUITABLE, production NOT_READY and disabled defaults remain; R1-R6 partial.
No commit/push. Next is explicit field/accounting correspondence, then real
screened research/strategy validation, not automatic aliases or synthetic reports.

The [current provider inventory](docs/provider-integration-status-2026-10-28.zh-CN.md)
separates adapters, real evidence, frozen Tushare/account constraints, optional
Massive and unimplemented Finnhub. API integration is necessary; this offline
slice does not require new credentials or subscriptions. No live permission
or provider availability probe is claimed. Full verification: **2632 passed /
6 skipped** in 110.11 seconds, 13 added cases. Ruff, mypy (289 source files),
governance (132 checks) and diff checks pass. Synthetic co-display tests cover
same/separate databases, currency labels, deterministic hashes, missing/future/
failed inputs, unfilled native data and rejected CLI combinations. The six opt-in
network tests remain skipped; no new provider capture was performed this slice.

### Source-Pinned Overseas Monetary Review: October 28

WP-LAUNCH-001 [adds an independent overseas manual-review contract](docs/global-document-manual-review-2026-10-28.md),
not a new ResearchReport or a relaxation of China-only CNY/calendar-YTD rules.
Source evidence/envelope/PDF/availability pins, native labels, Group/Bank scope,
column/current-comparative periods, currency/unit and separate physical/printed
page labels survive exact evidence persistence and reconstruction. Decimal scale
conversion is unqualified; missing/unreadable/conflicting cells remain null.

Claimed review time cannot backdate evidence: write uses actual UTC recording
time and rejects CLI --as-of. Preview is hypothetical/unpersisted. Reads recheck
current source and review ownership/completion at one snapshot/cutoff; newest
failed/tied/tampered/changed-parent inputs cannot fall back favorably. There is
no spanning source/write transaction claim; a source race invalidates use.

Two real single-transcription plans store four Tencent and four Maybank native
observations, with total/parent profit, Group/Bank and rounded-summary semantics
kept separate. Eight observations are not qualified facts or a second review.
The local global-document database now has four records/artifacts/batches and
zero canonical facts/reports/signals; original source read hashes are preserved.
No schema, dependency, score/replay admission or trading-layer change. New data
needs encrypted co-retention; no commit/push. PIT UNSUITABLE, production NOT_READY,
execution/notifications disabled and R1-R6 partial persist. Next: explicit native
accounting correspondence and combined read-only technical/financial evidence,
without premature field aliases, source admission or scoring. Full verification:
**2619 passed / 6 skipped** in 116.38 seconds, 44 added cases. Ruff, mypy (289
source files), governance (130 checks), scoped forbidden-import review and diff
checks pass. The six default-disabled network tests remain skipped; this slice
used retained local PDFs and made no new provider network captures.

### HK/MY Primary PDF Evidence: October 28

WP-LAUNCH-001 [adds explicit HKEX/Maybank original PDF retention](docs/hk-my-primary-documents-2026-10-28.md)
through the existing provider-neutral contract, SQLite evidence/artifact/batch
tables and retained-snapshot verifier. Exact URL/market scope, no redirects or
credentials, bounded bytes/retries and original/envelope hashes are enforced.
Explicit fixed-document reads keep latest failure/tie/tamper and future batch
completion from falling back favorably. No schema/domain/dependency change.

Two real PDFs captured: Tencent 3,999,857 bytes from HKEX, Maybank 3,415,287 bytes
from its official annual-report host. Ignored database has two records/artifacts/
batches and zero canonical facts/reports/signals. Same-cutoff reads repeat with
unchanged SQLite bytes; manual offline page inspection identifies currency/
counter, Group/Bank, unit and comparative/restatement hazards, not qualified facts.
The Malaysia provider is Maybank-specific, not a Bursa or market-wide adapter.
Caller issuer/subject/period labels and landing references remain unverified.
Publication, freshness, revisions, sector accounting and independent consistency
remain open. LOW/RETRIEVAL_TIME and all extraction/scoring/replay authority false.

No commit/push, Paper/Broker/Portfolio/Notification/live change. New ignored raw
evidence needs encrypted co-retention. R1-R6 remain partial, PIT UNSUITABLE,
production NOT_READY and disabled defaults persist. Next: source-bound overseas
page/column/unit/period review contract and sector policy, not a shortcut through
the existing China-only CNY/calendar-YTD mapping. Full verification: **2575 passed /
6 skipped** in 297.07 seconds, 45 added cases. Ruff, mypy (286 source files),
governance (129 checks), scoped forbidden-import review and diff checks pass.
The six default-disabled network tests remain skipped; two manual real captures
are not independent provider, numeric or strategy validation.

### SEC Filing Body And Numeric Subset: October 27

WP-LAUNCH-001 [adds retained primary bytes and a bounded Inline XBRL review](docs/sec-body-numeric-review-2026-10-27.md).
Verified catalog -> explicit parent-pinned periodic document -> existing neutral
ingestion/evidence/artifact/batch storage -> same-snapshot body/concept read.
Original bytes and envelope have separate hashes. No schema/domain change.
The subset checks namespaces, entity/context, exact periods, USD units, Decimal
scale/sign/precision and supported duplicate occurrences. DTD/entities, unknown
formats, nil, dimensional/ambiguous contexts and unsupported encodings remain
rejected or visibly unsupported, never guessed. Latest failures/ties/tampering,
future completion and changed parents cannot fall back to older favorable bodies.

Real annual body is 8,585,622 bytes. The initial 8 MiB bound rejected a normal
HTTP 200 response; explicit bounded recapture after the capacity correction
preserves that failure. Future oversize/empty diagnostics are explicit, while
existing JSON error/receipt semantics remain unchanged. Eighteen of 85 selected
fact occurrences are supported; 67 remain visible/unsupported. Nine API records
(three tags across three periods) agree with their supported body occurrences.
This is same-origin subset correspondence, not complete accounting review,
independent calibration, issuer/equity identity, historical availability or PIT
validation. All financial score/replay/validation/live authority remains false.

SEC database now has ten records/artifacts/batches, zero canonical facts/reports/
signals. Repeat reads preserve database bytes and fixed-cutoff hashes. Contact
is not retained. New ignored database/raw evidence still needs encrypted
co-retention; no commit/push, Paper/Broker/Portfolio/Notification/live change.
R1-R6 remain partial with zero fully accepted groups, PIT UNSUITABLE, production
NOT_READY and disabled defaults. Verification: **2530 passed / 6 skipped** in
91.64 seconds, 62 added cases; Ruff, mypy (283 files), governance and diff checks
are recorded in the linked slice report. Next is accounting/issuer review plus
HK/MY primary disclosures and financial-sector definitions, not unrelated archives.

### Targeted SEC Older-Page References: October 27

WP-LAUNCH-001 [adds explicit parent-pinned older-page capture and opt-in expansion](docs/sec-older-pages-2026-10-27.md).
Counts/interval/parent identity and exact retained ownership/completed-batch checks
gate use. Latest failed/tied/corrupt/changed-parent pages cannot fall back to an
older positive record; missing intervals remain visible. Default recent-only
concept outputs and original metadata/page-v1 hashes are unchanged.

Real page 001 has 2007 rows inside its parent's declared date interval; v2 fixes
v1's unjustified extrema-equality requirement via explicit recapture, preserving
v1 records/hashes. Page 002 has a one-day out-of-range label and 137 unsupported
metadata rows; it remains quarantined, not silently repaired or called a proven
provider defect. Combined usable reference view: 3010 metadata rows, not facts.
The three concepts now match 134/134, 345/345 and 170/170 references: the targeted
401 missing references are closed, not financial/PIT/strategy validation.

SEC database now has eight records/artifacts/batches, zero canonical facts/
reports/signals; no schema change. Repeat reads preserve bytes/hashes. Runtime
contact is absent from new source/database; ignored evidence needs encrypted
co-retention. Six four-market release acceptance groups remain open; this is a
bounded R2 improvement, not overall percentage or a new fixed prompt countdown.
No Paper/Broker/Portfolio/Notification/live change, commit or push. PIT UNSUITABLE,
production NOT_READY and disabled defaults persist. Verification: **2468 passed /
6 skipped**, 137.08 seconds, 33 added cases. Ruff, mypy (279 files), governance
(127 checks), scoped forbidden-import review and `git diff --check` pass. Default-
disabled live provider/notification tests stay skipped; real SEC captures and
metadata references are not independent numeric/strategy validation.
Next: filing-body/accounting/issuer review, HK/MY primary disclosure inputs and
financial-subsector definitions, then real research and strategy validation.

### SEC XBRL Values And Filing References: October 27

WP-LAUNCH-001 [adds retained source-native XBRL concepts and reference checks](docs/sec-concept-evidence-2026-10-27.md).
Composite CIK/taxonomy/tag identity, original units/start/end/accessions/fiscal
labels and distinct values prevent accidental metric, period or revision mixing.
Shared bounded SEC transport preserves existing catalog receipts. Same-snapshot/
UTC read-side checks verify bytes/registry/completed batch and link unique usable
accession/form/filed labels, not independent numeric or accounting correctness.
Failures/duplicates/older comparative/missing references stay visible without
favorable fallback, annualization, currency conversion or canonical aliases.

Real revenue/net-income/operating-cash-flow captures retain 134/345/170 rows, all
native integer USD amounts. 248 references match current catalog metadata; 401
are missing and all predate its earliest 2020-09-02 filing. This is a recent-window
coverage gap, not a validation score. Repeated fixed-cutoff reads and original
catalog v1/v2 hashes reproduce. Contact is absent from new envelopes/database.
Exact integer normalization only: fractional/boolean/text rows stay unusable.

SEC database now has five records/artifacts/batches and zero canonical facts/
reports/signals; no schema change. New ignored evidence needs encrypted
co-retention. LOW/retrieval-time, all scoring/replay authority false, PIT UNSUITABLE,
production NOT_READY and disabled defaults persist. No Paper/Broker/Portfolio/
Notification/live change, commit or push. Verification: **2435 passed / 6 skipped**,
86.35 seconds, 47 added cases. Ruff, mypy (276 files), governance (126 checks),
scoped forbidden-import review and `git diff --check` pass. Default-disabled
provider/notification live tests remain skipped; real SEC captures are separate
from independent source/accounting/strategy qualification.
Next: older catalog capture, filing-body/context and issuer/accounting
verification, then sector admission and actual technical-plus-financial validation.

### SEC Issuer Filing Evidence: October 27

WP-LAUNCH-001 [adds a bounded SEC issuer-disclosure metadata path](docs/sec-filing-evidence-2026-10-27.md)
through existing provider-neutral ingestion/retained-snapshot verification. Raw
accessions, filing/report dates, acceptance strings, amendment labels, malformed
rows and uncaptured older-page references remain explicit. Actual retrieval is
availability; acceptance is not first public dissemination or published_at.
CIK routing is not an admitted issuer/ticker/equity association.

Real CIK 0000789019 captures contain 1003 recent metadata rows, not financial facts.
The first response exposed false future-data quarantine of a prospective DEF 14A
meeting date. Form-aware v2 fixes that distinction; original v1 bytes/record/hash
remain reproducible, not overwritten. Both versions repeat unchanged; two older
pages remain NOT_CAPTURED. No contact identity is found in new envelopes/database.
Runtime identity is environment-only, with bounded reads/retries, no redirects
and sanitized errors. No permanent environment setting was written.

New local evidence: two records/artifacts/batches in an ignored SEC database;
zero canonical facts/reports/signals. New data needs encrypted co-retention.
LOW/retrieval-time, continuity unknown and no source/sector/scoring/replay
promotion persist. No schema/Paper/Broker/Portfolio/Notification/live change,
commit or push. PIT UNSUITABLE, production NOT_READY and disabled defaults remain.
Verification: **2388 passed / 6 skipped**, 124.52 seconds, 61 added cases. Ruff,
mypy (273 files), governance (125 checks) and `git diff --check` pass. Default-
disabled live provider/notification tests remain skipped; two explicit real SEC
captures are separate from independent source/strategy qualification.
Next: exact issuer/filing-body/
XBRL semantic matching and independent accounting/source review, then sector
admission and actual technical-plus-financial validation; no fabricated queue.

### Native Financial Evidence In Official Research: October 27

WP-LAUNCH-001 [connects retained native financial inputs to official research](docs/native-financial-research-binding-2026-10-27.md).
An immutable receipt/context contract reuses the existing source reconstruction;
the existing Financial assessment/report features retain original receipt and
review JSON, hashes, availability, failed/missing states and sector questions.
Existing SQLite report reconstruction preserves them without new tables or a
second report model. Exact identity/UTC/equity and revalidation checks precede
run writes. Public hashes/caller labels never authorize scoring or source trust.

Synthetic persisted-queue tests exercise the report boundary; no actual candidate
or official report is invented for the real captures. MSFT/0700.HK/1155.KL read-only
bindings repeat with original receipts and unchanged database bytes. Financial
remains unscored/zero-confidence, report/InvestmentAssessment INCOMPLETE and no
InvestmentScore. No source capture, schema, Paper/Broker/Portfolio/Notification/
live change, commit or push. PIT UNSUITABLE, production NOT_READY and execution/
notifications disabled. Verification: **2327 passed / 6 skipped**, 82.35 seconds,
52 added regression cases. Ruff, mypy (270 files), governance (124 checks), scoped
forbidden-import review and `git diff --check` pass. Default-disabled live provider/
notification network tests remain skipped; retained reads are not independent
source or strategy validation.
Next: authoritative issuer/accounting/release evidence and sector admission,
real screened candidates, then actual technical-plus-financial validation.

### Native Financial Changes And Sector Research Questions: October 27

WP-LAUNCH-001 [adds exploratory native amount changes and sector questions](docs/global-native-sector-review-2026-10-27.md).
The existing combined CLI now binds the reader receipt/model/subject/market/cutoff
and compares only unique usable adjacent native annual labels with same currency
and raw units. Bad/latest/previous/tied/unknown/future/irregular periods cannot
select favorable old data; nonpositive prior values withhold percentages. Native
amount arithmetic is not verified growth, accounting comparability or a return.

Nonfinancial/bank/securities/insurance/unknown profiles expose distinct
Survival/Cycle/Valuation/Growth research questions, not admitted rubrics. Negative
nonfinancial cash-flow/profit observations request business review only; financial
profiles do not inherit generic cash-flow deterioration flags. All sector policies
stay NOT_ADMITTED and financial condition EVIDENCE_INSUFFICIENT. No official
ResearchReport, Financial score or trading decision is generated or authorized.

Read-only re-evaluation of retained MSFT/0700.HK/1155.KL snapshots is deterministic
with unchanged SQLite bytes and original input receipts. No schema/provider/data
capture, Paper/Broker/Portfolio/Notification/execution, commit or push change.
PIT UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
Verification: **2275 passed / 6 skipped**, 83.28 seconds, 36 added regressions.
Ruff, mypy (269 files), governance (123 checks), new-path forbidden-import check
and `git diff --check` pass. Real retained-snapshot reads are not source or strategy
qualification; default-disabled live provider/notification tests remain skipped.
Next: independently reviewed issuer/sector/period
definitions and release/interim/revision evidence into the official research chain;
neither native arithmetic nor added questions admit scoring or complete validation.

### Native Global Financial Observations With Technical Context: October 27

WP-LAUNCH-001 [adds retained native annual financial observations](docs/global-native-financial-inputs-2026-10-27.md)
through existing Provider/neutral evidence/artifact contracts. Seven selected
native field names, fiscal year-end/12M labels, currencies and invalid/missing/
duplicate rows remain explicit; publication/revision/scope stay unknown. No
canonical financial definitions are inferred or old favorable values selected.
Shared snapshot verification/routing preserves prior real price hashes/versions.

Real MSFT/0700.HK/1155.KL captures each retain 28 observations with seven parseable
latest selected fields. At one fixed cutoff, combined technical/native-financial
outputs repeat exactly. HKD quotes/CNY statements remain separate with no FX or
valuation. Caller bank/nonfinancial/securities/insurance profiles cannot admit a
policy. Annual snapshots are not full/latest-interim financial research or PIT.

No schema, canonical fact/report/score, Paper/Broker/Portfolio/Notification/
execution change, commit or push. Three new ignored financial envelopes/SQLite
writes need encrypted co-retention; no source/strategy gate is promoted. PIT
UNSUITABLE, production NOT_READY, execution/notifications disabled. Verification:
**2239 passed / 6 skipped**, 110.47 seconds, 49 added regression cases. Ruff,
mypy (268 files), governance (122 checks), no forbidden imports in the new path
and `git diff --check` pass. Default-disabled live provider/notification tests
remain skipped; real Yahoo exercises are separate, not independent qualification.
Review reproduced local-time acceptance of naive stored completion timestamps;
shared artifact/batch verification now requires explicit timezone offsets before
UTC comparison. The failing regression now passes and all three real combined
outputs/previous price hashes remain intact. No other stored-time consumer is
certified by this scoped repair.
Next: authoritative issuer/sector accounting and interim/
release/revision definitions into the existing official research chain, not
another score or fabricated candidate.

### Global Price Evidence To Technical Diagnostics: October 27

WP-LAUNCH-001 [adds retained overseas price reconstruction](docs/global-price-technical-bridge-2026-10-27.md)
using the existing Provider/neutral ingestion/artifact contracts. One explicit
global_equity_price_snapshot observation/envelope captures success or failure;
the read side verifies bytes, identity, registry, complete batch and cutoff before
passing ephemeral native-price bars to existing technical diagnostics. Latest
failure/tie/current exchange-date/stale/invalid rows cannot select old favorable
prices. Capture is opt-in; fixed-cutoff CLI reads do not initialize or write the
database. The Yahoo HTTP client now bounds response bytes before JSON parsing.

Real Yahoo exercises reconstruct MSFT 706, 0700.HK 692 and 1155.KL 690 daily
observations, with exact repeated output/hash and unchanged exploratory SQLite
bytes. Initial MSFT October 26 capture is preserved but blocked: New York was
still on that date at capture. An explicit October 23 end-date produced the
706-row sample, not an implicit fallback. Four evidence/artifact/batch records
exist; canonical daily bars, ResearchReports and Signals remain zero in this
separate database. These are transport/calculation samples, not selected stocks.

Provider-native adjustment history remains unverified even without adjusted-close
fields. LOW/retrieval-time transient bars cannot enter strict PIT canonical data,
official scored research or replay. Financial/sector/industry/sentiment remain
unassessed, no provider consistency or strategy gate is promoted. New ignored
bytes require encrypted co-retention. No schema, Paper/Broker/Portfolio/
Notification/execution path changes, commit or push. PIT UNSUITABLE, production
NOT_READY and execution disabled persist. Verification: **2190 passed / 6 skipped**,
139.32 seconds, 55 added regressions. Ruff, mypy (263 files), governance (121
checks), no forbidden imports in the new path and `git diff --check` pass.
Synthetic tests and the separate real Yahoo exercise do not qualify source truth,
historical adjustment continuity, global financial research or strategy readiness.
Next: source-qualified identity/adjustment inputs and global sector financial
mapping into the existing official chain, not orders or a second report model.

### Four-Market Read-Only Release Scope Confirmed: October 27

Tong confirmed the first deployable release must cover China A, US, Hong Kong
and Malaysia, including financial and nonfinancial equities, using the previously
requested technical methods. Read-only delivery is accepted; the earlier narrow
China-A nonfinancial proposal is superseded, not silently retained as the release.
See the [scope and implementation gap matrix](docs/four-market-readonly-release-2026-10-27.zh-CN.md)
and revised [R1-R6 delivery plan](docs/decision-delivery-plan-2026-10-27.zh-CN.md).
Detailed sector/source scoring definitions, weights, thresholds and strategy
validation remain unapproved. The nonfinancial rubric is a China-A sector draft,
not a universal financial model. The previous narrow-pilot 8-15-round estimate
does not apply; do not invent a new completion percentage from test counts.

All four market identifiers and shared Technical/Trend calculations exist;
Yahoo global evidence is DEGRADED/LOW/retrieval-time, not admitted canonical
inputs. Banks have partial input diagnostics; securities/insurance and overseas
financial definitions remain gaps. Size/style, real weekly/monthly aggregation,
A-share intraday inputs, qualified real reports and validation remain required.
Scope includes these gaps rather than declaring them removed. Seven-plus-one
remains owner-deferred. No live/Paper/Broker/Portfolio/Notification code, schema,
score admission, commit or push changes. PIT UNSUITABLE, production NOT_READY,
disabled execution and existing package acceptance gates are preserved.

This slice adds synthetic four-market technical/four-confirmation and A-share
pattern-boundary regression coverage, not provider/sector/strategy qualification.
Verification: **2135 passed / 6 skipped**, 70.38 seconds, 28 added synthetic
regressions. Ruff, mypy (260 files), governance (120 checks) and
`git diff --check` pass. Real provider/network skips remain unverified; software
checks do not admit any source, financial rubric, strategy or deployment gate.
Next: four-market real input mapping and bounded official-chain design, alongside
sector-specific data definitions; no repeated request to approve the market scope.

### Earlier Narrow First-Release Proposal (Superseded Scope): October 27

WP-LAUNCH-001 [defines six finite proposed acceptance groups](docs/decision-delivery-plan-2026-10-27.zh-CN.md)
for a first research-decision release, separately from Paper and live trading.
The linked [nonfinancial long-term rubric draft](docs/proposals/nonfinancial-long-term-rubric-v1.zh-CN.md)
proposes scope, four Value dimensions, source/admission boundaries, candidate
internal weights and explicit unresolved thresholds/validation requirements.
At that earlier proposal point all remained DRAFT; the later four-market scope
confirmation above supersedes its narrow scope and effort estimate. No runtime
policy/weight, data
qualification or scoring permission is changed. R1-R6 are acceptance groups under
the existing package, not new ready/completed governance work packages.

Historical estimate (not applicable to the confirmed release): 8-15 focused
implementation/acceptance rounds for that limited
research-decision scope, conditional on scope approval, usable data and acceptable
validation. Not an engineering-derived completion forecast, fixed date or live
trading estimate. Six groups still require acceptance; R1 has a draft, not approval.
Data access/evidence gaps or rejected strategies can block or extend the estimate.
The existing evidence horizon and replay/Paper/live gates are preserved.

Current execution storyboard now distinguishes parallel approved development
from evidence promotion, completed technical/condition software from planned
Style research, and implemented Portfolio lineage from older string-status notes.
No code, database, Paper/Broker/Portfolio/Notification implementation, commit or
push change. PIT UNSUITABLE, production NOT_READY and execution disabled persist.
The earlier next step required scope/rubric review; scope is now confirmed above.
Detailed rubric review, concrete source/definition acceptance and the official
real-candidate chain remain required, not further generic engine expansion.
Verification: **2107 passed / 6 skipped**, 251.37 seconds; no new runtime tests
or code in this design-only slice. Ruff, mypy (260 files), governance (119 checks),
the focused governance suite (7 passed) and `git diff --check` pass. Test success
does not accept any proposed stage, source, strategy or live readiness.

### Nonfinancial Research Input Checklist: October 27

WP-LAUNCH-001 [adds a nonfinancial input/period checklist](docs/nonfinancial-input-checklist-2026-10-27.md).
Eleven selected China-A group metrics now have explicit definition/period checks,
separate requested/missing/rejected/unsupported/ambiguous statuses and report-age
diagnostics. ROIC and interest-bearing-debt definitions remain explicitly
unimplemented, not substituted or hidden as ordinary missing data. Existing
financial age configuration wires both bank/nonfinancial policies; zero means
UNASSESSED. The combined CLI accepts an explicit target quarter; official
Financial assessments persist the full source/policy-bound checklist using the
existing features JSON, not a new report, score, schema or persistence path.

Real fixed-cutoff reads of 002624 agree: 17 source-bound observations support
11 selected June 30 inputs, all OBSERVED_UNQUALIFIED with 118-day period age.
An explicit September 30 target yields 11 PERIOD_MISMATCH checks, not old-data
fallback or proof of a missing issuer disclosure. Default freshness is unassessed,
ROIC/debt definitions remain open, technical confluence is CONFLICTED and source/
financial policy are not admitted. SQLite bytes are unchanged; no real report/
score or favorable financial conclusion is manufactured.

No provider/network capture, schema, Paper/Broker/Portfolio/Notification change,
commit or push. PIT UNSUITABLE, production NOT_READY and disabled execution persist.
Next: independently reviewed sector/source scoring rubric, dated share/action
continuity and actual combined hypothesis validation. Verification: **2107 passed /
6 skipped**, 189.16 seconds, 26 added cases against the 2081-test checkpoint.
Focused changed-policy/research/CLI tests: 225 passed. Ruff, mypy (260 files),
governance (117 checks) and `git diff --check` pass; encrypted co-retention remains open.

### Financial Snapshot UTC Integrity: October 27

WP-LAUNCH-001 [repairs a reproduced financial input timing gap](docs/financial-snapshot-utc-2026-10-27.md).
The snapshot could admit a one-hour future folded-clock input, alias different
decision cutoffs and disagree on equivalent timezone labels. Bank/nonfinancial
latest selection could favor an older higher-revision value over a later rejected
row. FundamentalFact chronology, snapshot visibility/context/hash revalidation and
bank/nonfinancial version selection now use actual UTC instants. Equal-instant
duplicates remain ambiguous. Snapshot date bounds use a pinned conservative UTC
date, not exchange-session or local-report-calendar approval; China bank age
diagnostics still use their separately defined Shanghai date.

Changed snapshot/financial/bank/nonfinancial runtime versions preserve old source
packets, SQLite facts/schema and historical reports. One persisted-run regression
rejects a mismatched snapshot cutoff before any run/report/signal write. Repeated
real reads reconstruct all 17 stored 002624 observations with unchanged database
bytes; ROIC remains missing. Source-bound means stored consistency, not verified
accuracy, admitted financial scoring or independent source continuity.

No provider/network capture, schema, Paper/Broker/Portfolio/Notification change,
commit or push. PIT UNSUITABLE, production NOT_READY and disabled execution persist.
Next: independent source/sector policy and dated action continuity, then actual
technical-plus-fundamental hypothesis validation. Verification: **2081 passed /
6 skipped**, 76.34 seconds, 31 added cases against the 2050-test checkpoint.
Focused financial/research/integration suite: 440 passed. Ruff, mypy (259 files),
governance (116 checks) and `git diff --check` pass. Remaining shared temporal consumers,
revision provenance, source coverage and encrypted co-retention need separate review.

### Manual Share-Action Document Review: October 26

WP-LAUNCH-001 [adds explicit per-document observations](docs/share-action-review-2026-10-26.md).
Read-only plans distinguish issuer capital from holder/plan transfers, disposal
and plan termination, and completed claims from proposals/pending/unknown stages.
One shared retained-CNInfo binder checks bytes/registry/completed batches and
actual review visibility for both action and share-count reviews. The existing
share-count receipt remains unchanged; inventory v2 adds explicit document
reviews, unmatched review identities and pre-base/within/after/unknown date labels.
Only exact captured PDF versions inherit manual review, never metadata-only or
changed bytes. No issuer delta (even zero), current shares or market value is inferred.

Actual 002624 checks annotate one of 21 unique announcements with four manual
observations: two pre-base transfers, one disposal with unreported exact date,
and plan termination with unreported exact date. Independent second review is
pending. Fixed-cutoff repeated combined reads agree and SQLite bytes are unchanged;
an earlier cutoff rejects the later review. LOW/retrieval-time, PIT UNSUITABLE,
production NOT_READY and disabled execution persist. No schema/capture, canonical
publication, Paper/Broker/Portfolio/Notification change, commit or push.
Next: review dated issuer/share-class actions and prior notices/corrections;
admit a source-bound sector financial policy before actual combined hypothesis
validation. Newly retained data/plans still require encrypted co-retention.
Verification: **2050 passed / 6 skipped**, 91.50 seconds, 46 added regressions
against the 2004-test checkpoint. Ruff, mypy (259 files), governance (115 checks)
and `git diff --check` pass; focused share/review tests: 103 passed.
Offline checks and one manual document review do
not establish issuer/source truth, full continuity or investment performance.

### Share Continuity Disclosure Inventory: October 26

WP-LAUNCH-001 [adds an explicit share-continuity document inventory](docs/share-continuity-inventory-2026-10-26.md).
Actual neutral CNInfo capture adds 21 metadata records for the post-H1 window and
two targeted PDFs. The read-only combined CLI accepts an explicit through-date
with the base share plan, checks record/batch identities and actual UTC capture/
completion visibility, and retains rejected/duplicate versions. Title tags prepare
document review only; publication dates/keywords never establish effective share
deltas, complete coverage or absence of changes. Unmatched documents stay unreviewed.

Real fixed-cutoff reads agree: 25 metadata versions, 21 unique announcements and
8 title-triaged unique documents, zero scoped binding rejections. An earlier
cutoff sees only two old H1 versions, not the newly retrieved old publications.
The employee-plan PDF received a limited manual preview, not current share-count
or issuer-cancellation approval. At that v1 checkpoint all runtime documents were
NOT_REVIEWED; the v2 follow-up above adds explicit manual annotations only.
Current shares/market value stay null. Technical conflict, missing ROIC, source/sector
admission and actual strategy validation remain unresolved.

Totals: 4094 evidence records, 21 artifacts, 23 batches, 3374 versioned daily rows
and 17 facts; zero real reports/signals. 21/21 registered bytes verify; encrypted
retention remains open. No schema/strategy/Paper/Broker/Portfolio/Notification
change, commit or push. PIT UNSUITABLE, production NOT_READY and execution disabled
persist. Next: independently reviewed implementation/share-class/effective-date
evidence, including prior notices and corrections, before any share carry-forward.
Verification: **2004 passed / 6 skipped**, 65.85 seconds, 20 new regressions
against the 1984-test checkpoint. Focused share/continuity suite: 57 passed.
Ruff, mypy (257 files), governance (114 checks) and `git diff --check` pass.
Scoped real capture/read reproducibility is separate from offline regressions;
neither demonstrates full source continuity, investment performance or admission.

### Dated Issuer Share-Count Review: October 26

WP-LAUNCH-001 [adds an opt-in read-only share-count review](docs/share-count-review-2026-10-26.md).
The combined diagnostic binds a separate issuer/whole-share/period-end review to
retained CNInfo PDF bytes, registry identity, completed batch and actual UTC
review visibility. CNY book share capital, EPS averages, current shares and index
free float cannot be substituted. Incomplete/conflicting components remain visible;
LOW/retrieval-time (UNKNOWN stays UNKNOWN) and all admission flags remain closed.
This is not a new provider, canonical Financial fact or SQLite population path.

Actual 002624 PDF page 36 was visually checked; the June 30 total/restricted/
unrestricted counts reconcile but are 118 days old at the fixed review cutoff.
The CNY book-capital note on page 104 is excluded, not guessed into shares. Two
joint reads agree with UNQUALIFIED_CONTINUITY and null market value; real SQLite
bytes are unchanged. Financial admission/ROIC/current shares/actions and strategy
validation remain open; no real report or InvestmentScore is invented. The Git-
managed plan needs co-retention and independent second review before promotion.

No schema/data capture, Paper/Broker/Portfolio/Notification change, commit or push.
PIT UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
Next: independently reviewed dated share-class/action continuity and sector
financial policy, then real financial-plus-technical hypothesis validation.
Verification: **1984 passed / 6 skipped**, 82.26 seconds, 37 added share-review
cases against the prior 1947-test checkpoint. Ruff, mypy (256 files), governance
(113 checks) and `git diff --check` pass. Offline fixtures and retained-PDF
reconstruction do not prove independent annotations, original historical
publication, source accuracy or real investment performance.

### Daily Refresh And Current Suspension Guard: October 26

WP-LAUNCH-001 [refreshes real daily inputs and fixes pre-suspension scoring](docs/daily-refresh-suspension-guard-2026-10-26.md).
002624 now has 678 visible daily observations through October 23, four more dates
than the prior October 19 endpoint. Actual availability remains October 26 local
retrieval time. All 678 stored rows/evidence reconstruct from retained frame bytes;
19/19 registered files verify. Earlier cutoffs still see 674 observations ending
October 19. Totals: 4071 evidence records, 19 artifacts, 21 batches, 3374 versioned
daily rows and 17 facts; no real report/signal is invented.

A reproduced synthetic latest suspension still produced a supportive score
79.7621 from an older active close. Technical, Trend and Pattern current research
now require the latest selected observation to be active; suspended latest input
returns insufficient data/no score. Direct diagnostics preserve original context
and hash-bound blocking evidence. Historical selector defaults and old rows stay
intact. Explicit later active observations can restore unqualified calculations,
not prove lifecycle resumption or source/trading qualification. Module/calculation
versions distinguish the repaired behavior; official report persistence retains
the block and InvestmentAssessment stays INCOMPLETE without InvestmentScore.

Two fixed-cutoff real combined reads agree: October 23 Yahoo/close both show
10.0, but price bases/independent consistency stay unqualified. Technical families
are still CONFLICTED; the confirmed setup is bearish, not a long entry. Requested
ROIC, dated shares/market value, sector admission and real strategy validation
remain open. Illustrative elapsed-time age limits do not establish session-aware
freshness. No schema/trading/Paper/Broker/Portfolio/Notification change, commit or
push. PIT UNSUITABLE, production NOT_READY and disabled execution persist.
Next: independently qualified dated shares/actions and sector financial inputs,
then real financial-plus-technical hypothesis validation. New ignored bytes/database
need approved encrypted retention; file hashes alone do not establish backup.
Verification: **1947 passed / 6 skipped**, 60.19 seconds, 23 added cases against
the 1924-test checkpoint. Focused calculation/research/SQLite suite: 348 passed.
Ruff, mypy (255 files), governance (112 checks) and `git diff --check` pass.
The real refresh, 678-record reconstruction, 19/19 artifact checks and earlier-
cutoff checks are separate from offline tests and do not prove source truth,
historical PIT coverage, investment outcomes or trading eligibility.

### Common-Cutoff Price Input Alignment: October 26

WP-LAUNCH-001 [joins retained Yahoo prices to the combined input diagnostic](docs/price-input-alignment-2026-10-26.md).
Price/capture/bar ages are explicit, date comparison uses Shanghai, and differing
market dates cannot become price conflicts/returns. Same-date snapshot-versus-
close residuals remain unqualified; full original bars, quote reconstruction and
policy bind identity. Failed/tied/broken/latest suspended inputs cannot revive
older favorable prices. Other-market/BSE quote scopes stay explicitly unsupported.
No arbitrary price dictionary, canonical fallback or second ResearchReport is used.

Two real 002624 reads at the retained October 25 15:10:07.279497 UTC cutoff agree:
Yahoo's October 23 price and the October 19 daily bar have DIFFERENT_MARKET_DATE;
both are STALE under illustrative 24-hour limits despite a recent capture. The
existing technical diagnostic remains CONFLICTED, requested ROIC is missing and
market value unavailable/unqualified. This is not a current market or buy/sell
assessment. No new data capture, database/schema write or source promotion.

Next: refresh source-bound daily inputs and qualify dated share-class-aware
shares/actions/market value, then admitted financial-plus-technical hypothesis
validation. Official financial/scoring and launch gates remain open; PIT
UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
No Paper/Broker/Portfolio/Notification work, commit or push this slice.
Verification: **1924 passed / 6 skipped**, 61.50 seconds, 30 added cases against
the prior 1894-test checkpoint. Focused quote/alignment/market-value suite: 173
passed. Ruff, mypy (255 files), governance (111 checks) and `git diff --check`
pass. Offline tests and retained-input reproducibility are not live provider or
strategy-performance verification.

### Real Yahoo China Price Evidence: October 25

WP-LAUNCH-001 [retains a working price-only Yahoo observation](docs/yahoo-china-quote-evidence-2026-10-25.md).
A scoped ProviderEvidenceAdapter validates SSE/SZSE ticker/exchange/currency/type/
clock metadata and saves SDK-decoded snapshots via neutral atomic ingestion.
Stored-consistency reconstruction checks content/artifact/batch provenance at
cutoff; latest failure/rejection/tie cannot resurrect old prices. Unavailable and
invalid inputs remain explicit. BSE/funds/unrelated markets are not guessed.
This is a separate price-observation dataset, not an automatic market-value or
canonical-bar fallback. All Financial/valuation/investment gates stay closed.

One actual 002624 observation is retained, quoted by Yahoo as October 23 07:04:33
UTC, with LOW/retrieval-time and UNASSESSED freshness. Shares/market values remain
missing; the Eastmoney public recheck still returns HTTP_502. Two fixed-cutoff
reads agree and earlier cutoffs hide the new observation. Files verify 18/18;
evidence/artifact/batch totals are 3393/18/20, with 2696 bars and 17 facts unchanged
and no research report/signal invented. New bytes are decoded JSON, not original
HTTP wire capture or independent source verification; encrypted retention is open.

No schema, Tushare transport, trading, commit/push or readiness change. PIT
UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
Next: dated share-class-aware shares/market-value qualification and common-cutoff
price/fundamental/technical validation. A working price source does not finish
those gates. Existing Yahoo transport whole-call/response bounds remain separate
hardening debt; post-decode size limits do not certify the transport.
Verification: **1894 passed / 6 skipped**, 63.63 seconds, 66 added cases against
the prior 1828-test checkpoint. Ruff, mypy (254 files), governance (110 checks)
and `git diff --check` pass. Real capture/byte checks are separate from offline
regressions; source and strategy qualification remain open. DB/new evidence files
are ignored by Git and not a substitute for encrypted retention.

### Provider Ingestion UTC Integrity: October 25

WP-LAUNCH-001 [repairs the upstream provider-neutral UTC boundary](docs/provider-ingestion-utc-integrity-2026-10-25.md).
Strict ingestion previously admitted a synthetic folded-clock observation one
actual hour after cutoff. Provider record/artifact/observation chronology,
child-to-batch retrieval binding and completion checks now compare actual UTC
instants. Returned contracts are revalidated before file/database publication or
canonical callbacks. Equivalent timezone instants remain valid; relaxed PIT
cannot disable chronology or trust ceilings. The separate centralized timing
marker changes no existing source/packet identities or schema.

Read-only scoped real chronology check: 3392 evidence records, 17 artifact
registrations, 8 artifact observations and 19 batches show no checked UTC-order
violations. Registered raw files still verify 17/17. No new provider capture or
real database population; the retained quote failure/source/strategy gaps remain.
PIT UNSUITABLE, production NOT_READY and execution/notifications disabled persist.
Next: permitted dated quote qualification and real technical-plus-fundamental
validation, with separate temporal audits outside this boundary. No commit/push.
Verification: **1828 passed / 6 skipped**, 60.33 seconds, 32 added cases from
the prior 1796-test checkpoint. Focused ingestion/evidence/trust suite: 89 passed.
Ruff, mypy (251 files), governance (109 checks) and `git diff --check` pass.
These are offline engineering checks, not live provider or investment validation.

### Research Input UTC Integrity: October 24

WP-LAUNCH-001 [repairs a reproduced DST-fold input leak](docs/research-input-utc-integrity-2026-10-24.md).
A synthetic bar one actual hour after cutoff was accepted when its local wall
clock looked equal. ResearchContext now checks queue/evidence/fact/metadata and
regime visibility in UTC; shared daily selection and financial latest-version/
availability ordering use actual UTC instants too. Distinct folded revisions no
longer alias, a later suspension cannot resurrect an old price, and same-instant
timezone representations remain valid. SQLite rejection precedes persisted runs
or publication, retaining the pending queue. New report/module versions record
the change without rewriting historical reports, source packets or schema.

No new provider capture or real database population; the retained HTTP_502 and
source/sector/strategy gaps remain unresolved. PIT UNSUITABLE, production
NOT_READY and execution/notifications disabled persist. This is a scoped research
repair, not a repository-wide UTC certification or WP-LAUNCH-001 acceptance.
Next: permitted dated quote-source qualification and independent technical-plus-
fundamental validation; audit other temporal boundaries separately. No commit/push.
Verification: **1796 passed / 6 skipped**, 64.00 seconds, 35 added cases against
the prior 1761-test checkpoint. Focused suite: 402 passed. Ruff, mypy (251 files),
governance (108 checks) and `git diff --check` pass. Repeated fixed-cutoff real
reads agree; technical state remains CONFLICTED and quote remains unavailable.

### Market-Value Research Binding: October 24

WP-LAUNCH-001 [binds market-value diagnostics to official Financial research](docs/market-value-research-binding-2026-10-24.md).
An input-hash defect is fixed: changed consumed OHLCV/source/availability now
changes matching identity even when close/date match booleans are unchanged.
Explicit separate quote/capture/bar age policies default to UNASSESSED, not PASS;
latest suspension cannot match an old active close. Exact-context/mutation and
equity-scope checks apply before a persisted research run. Existing report features
retain reasons, limits, trust, ages and evidence/hash links in SQLite without a
schema migration. Financial reports/InvestmentAssessments remain incomplete,
unscored and unable to issue InvestmentScore; no real queue/report is invented.

Real fixed-cutoff reads agree and detect stale October 19 bars under an illustrative
24-hour policy. The retained quote request remains HTTP_502/UNAVAILABLE; a fresh
failure capture is not a usable quote. Registered bytes verify 17/17. No new
capture/database population, source qualification, commit/push or trading change.
PIT UNSUITABLE, production NOT_READY and disabled execution/notifications persist.
Next: obtain a functioning permitted dated quote source and independently review
units/clock/share-class/action context before sector valuation and actual
technical-plus-fundamental strategy validation.
Verification: **1761 passed / 6 skipped**, 63.28 seconds, 32 added cases against
the prior 1729-test checkpoint. Ruff, mypy (251 files), governance (107 checks)
and `git diff --check` pass. Offline fixtures verify engineering behavior, not
live quote access, source authenticity or investment performance.

### Market-Value Capture And Matching: October 23

WP-LAUNCH-001 [adds market-value evidence contracts](docs/market-value-inputs-2026-10-23.md).
A fixed scoped Eastmoney public adapter preserves the delivered body, response
status and actual retrieval time through existing neutral atomic ingestion.
Total/float market values and share counts remain separate; native mapping,
share-class scope and quote clock are unqualified. Raw reconstruction, completed
batch checks, immutable read receipts and latest-failure/no-fallback behavior feed
the combined read-only CLI. Date/price matching and exact arithmetic residuals
cannot create valuation multiples, financial scores or trading authority.

Real access probing returned HTTP 302; the completed audited capture returned
HTTP 502 and is explicitly UNAVAILABLE, not zero market value or framework/PIT
readiness. Its failure envelope verifies 17/17 registered bytes with older facts
unchanged; two fixed-cutoff combined reads agree and old cutoffs cannot see it.
The pre-request versus post-capture cutoff race was fixed without changing
strict ingestion checks. A labelled-JSON credential-filter gap was also fixed
before encoding the capture envelope; opaque-secret detection is not guaranteed.

No new table, schema, canonical fact/bar, trading-module, commit/push or readiness
change. Raw capture bytes remain ignored and outside earlier encrypted retention.
Official Financial/scoring consumption and source/sector valuation remain open.
PIT UNSUITABLE, production NOT_READY and execution/notifications disabled remain.
Next: obtain a functioning permitted quote source and independently review units,
quote timing/share-class/FX/action context before admitting matched valuation.
Verification: **1729 passed / 6 skipped**, 58.25 seconds, 52 new cases. Ruff,
mypy (251 files), governance (106 checks) and `git diff --check` pass. Real HTTP
capture/byte audit is separate from offline regression coverage; no numeric
market-value or source-quality claim follows passing software checks.

### Annual Inputs And Reviewed Trailing Arithmetic: October 23

WP-LAUNCH-001 [adds source-bound annual/trailing inputs](docs/trailing-financial-inputs-2026-10-23.md).
Two real 002624 annual income facts join the existing H1/current comparative
observations. A reusable trailing diagnostic computes only reported annual
amounts or explicitly reviewed FY + current YTD - prior YTD arithmetic, never
interim annualization. Exact receipt hashes bind all three inputs; missing,
changed, rejected, ambiguous, future or different-edition inputs cannot select
an older favorable result. Reviews must follow inputs and be visible at cutoff.

Existing Financial reports and the read-only combined CLI expose these diagnostics;
factory defaults grant no edition review. Explicit review injection/CLI plans
remain diagnostic only. All reports/InvestmentAssessments stay incomplete and
unscored; source trust and original historical availability are not qualified.
The original valuation-basis output remains partial-year alongside the separate
derived trailing amount. Dated market value and sector valuation still remain.

Real duplicate ingestion leaves 17 financial observations and preserves first
provenance. Fixed-cutoff reads agree, older cutoffs hide the new annual inputs,
and registered bytes verify 16/16. New ignored PDF/review bytes are outside earlier
encrypted retention; config review files need to accompany source code. No schema
change, trading-module change, commit/push or readiness promotion. PIT UNSUITABLE,
production NOT_READY and execution/notifications disabled remain unchanged.
Next: dated equity market-value/source-unit contract and matched valuation
diagnostics, then admitted sector conditions and actual strategy validation.
Verification: **1677 passed / 6 skipped**, 59.90 seconds, 47 new cases. Ruff,
mypy (246 files), governance (105 checks) and `git diff --check` pass. Focused
trailing/filing/research suite: 503 passed. Real annual capture/byte checks were
performed separately; the full suite keeps network tests disabled by default.

### Valuation Basis And Parent Equity: October 23

WP-LAUNCH-001 [adds valuation denominator diagnostics](docs/valuation-basis-inputs-2026-10-23.md).
Signed current group parent equity uses a new v7 source review without changing
v1-v6 packets, schema or framework version. Financial ResearchReport features
and the combined read-only CLI distinguish missing/not-requested, incompatible,
partial-year, nonpositive and observed-but-unqualified bases. They never create
PE/PB/PS, market value, annualization, TTM, valuation scores or execution authority.

One manually reviewed 002624 H1 parent-equity fact of CNY 6,511,874,265.88 joins
existing retained evidence. Duplicate ingestion preserves first provenance;
the previous-day cutoff cannot see it. Two actual fixed-cutoff reads agree;
13/13 registered artifacts verify. LOW/retrieval-time remains explicit, not
independent verification. Interim losses do not prove full-year/TTM losses.
New ignored review bytes are outside earlier encrypted retention. No commit/push.

PIT UNSUITABLE, production NOT_READY, disabled execution/notifications and
incomplete Financial research remain unchanged. Next: independently qualified
dated equity market-value and full-year/TTM input contracts, then sector-aware
valuation/financial admission and real technical-plus-fundamental validation.
Do not treat a populated denominator or code-test success as buying permission.
Verification: **1630 passed / 6 skipped**, 55.05 seconds, 42 new cases. Ruff,
mypy (245 files), governance (104 checks) and `git diff --check` pass. Six live
network checks remain opt-in; no live provider claim follows the offline suite.

### Research Evaluation-Cutoff Binding: October 23

WP-LAUNCH-001 [repairs mixed module evaluation cutoffs](docs/research-assessment-cutoff-2026-10-23.md).
A synthetic prior-day financial result previously combined with current modules
into VALIDATION_REQUIRED. Shared exact-UTC checks now bind all new report builds,
direct conditions and separate policy wrappers to the request's logical decision
instant. Equivalent timezone instants preserve condition hashes; DST folds cannot
hide future assessments or child data. This does not require inputs to originate
on the decision day or independently prove their freshness or original provenance.

Three SQLite styles preserve failed-run audit/pending retry but publish no report,
assessment, evidence or signal for cached-cutoff failures. New report/condition
versions are centralized; stored historical records and schema are unchanged.
Full suite: **1588 passed / 6 skipped**, 50.08 seconds, 28 new cases; focused
research/integration tests pass 231 cases. Ruff, mypy (244 files), governance
(103 checks) and `git diff --check` pass. No data population, trading-module,
commit/push or readiness promotion; PIT UNSUITABLE and disabled defaults remain.
Next: dated valuation and source/sector decision-condition work, plus original
consumed-input and freshness evidence. Never retimestamp a cached result to pass.

### Nonfinancial Cash And Balance Diagnostics: October 22

WP-LAUNCH-001 [adds source-bound cash/balance inputs](docs/nonfinancial-cash-balance-2026-10-22.md).
Five current nonfinancial group amounts now cover total/current liabilities,
monetary funds and YTD operating cash inflow/outflow. Four reusable same-filing
diagnostics flow into existing Financial ResearchReport features and the combined
read-only CLI. Exact cash residuals remain visible; component conflicts/rejections
withhold dependent cash ratios even when another component is missing. No older
favorable fallback, generic debt/cash alias or blank-to-zero inference is allowed.

The real 002624 sample retains 14 financial observations beside 674 prior daily
rows ending October 19. Repeated writes keep five new facts and first provenance;
two fixed-cutoff reads match without writes. Registered bytes verify 12/12.
New review bytes are outside earlier encrypted backups and ignored by Git.
V6 review/input receipts and a new diagnostic/financial version preserve v1-v5
source packets. No migration or trading module change; no commit/push.

Ratios remain LOW/retrieval-time, not debt clearance, unrestricted liquidity or
validated cash quality. ROIC/valuation/source-sector scoring and actual screening/
strategy validation remain incomplete; technical confluence stays CONFLICTED.
PIT UNSUITABLE, production NOT_READY and disabled defaults remain unchanged.
Completion verification is recorded in the linked report.
Full suite: **1560 passed / 6 skipped**, 64.00 seconds, 54 new cases. Ruff,
mypy (243 files), governance (102 checks) and `git diff --check` pass. Final
unit coverage also rejects combined missing/rejected cash components without
hiding their conflict; the pinned real-data reconstruction remains unchanged.
Next: explicit borrowing/restricted-cash context and dated valuation inputs,
then source/sector decision-condition admission and actual strategy validation.

### Nonfinancial ROE Input: October 22

WP-LAUNCH-001 [fills the disclosed-but-unsupported ROE gap](docs/nonfinancial-roe-inputs-2026-10-22.md).
Explicit current calendar-YTD weighted ROE now uses a separate signed-percent,
null-currency nonfinancial contract, not generic roe/roic, bank period-end data,
an annualized value or an ending-equity calculation. V5 packets/input receipts
extend the current reader; five pre-change v1-v4 packet hashes remain unchanged.

One real 002624 fact joins eight existing financial observations and 674 prior
daily observations in the same-cutoff read. Duplicate ingestion retains one
fact and original provenance; the October 20 cutoff cannot see the new review.
Two fixed-cutoff combined reads match without database writes. ROIC remains
missing, financial scoring NOT_ADMITTED, screening NOT_ASSESSED and technical
confluence CONFLICTED. This is input progress, not a completed research report
or validated buy/sell judgment. Bytes verify 11/11; the new ignored review packet
is outside earlier encrypted backups. No schema, trading module, commit/push or
readiness promotion; source/basis review remains manual LOW/retrieval-time.

Full suite: **1506 passed / 6 skipped**, 53.14 seconds, 45 new cases. Ruff,
mypy (242 files), governance (101 checks), `git diff --check` pass; focused
filing/research tests pass 386 cases. Next: debt/cash drivers, dated valuation
and named ROIC/sector inputs, then actual screened technical/fundamental
validation. A disclosed ROE cannot override incomplete evidence or conflicts.

### SSE Pilot Scope Hardening: October 22

WP-LAUNCH-001 [closes a board-scope defect](docs/sse-pilot-symbol-scope-2026-10-22.md):
synthetic STAR 688363 tagged as SSE could previously receive main-board
calculations. A shared conservative six-digit ASCII 600/601/603/605 boundary now
guards all four calculation paths. Runtime inventory retains mismatched records
with explicit scope gaps; a matching prefix does not replace dated listing,
status/phase/calendar, account or source evidence. Calculation/runtime versions
advance to v1.2-symbol-scope/v1.7-symbol-scope; historical results are not rewritten.

Full suite: **1461 passed / 6 skipped**, 48.15 seconds, 69 new regression cases.
Ruff, mypy (242 files), governance (100 checks) and `git diff --check` pass.
No database/schema, new provider capture, trading-module, commit or push change.
PIT remains UNSUITABLE and production NOT_READY. WP-LAUNCH-001 stays ready, not
accepted. Next priority remains source-qualified technical/fundamental candidate
validation and remaining runtime gates; prefixes/tests are not trading approval.

### BSE Raw Price Observations: October 20

WP-DATA-004 [finds a reachable source for 920982](docs/bse-price-source-repair-2026-10-20.md).
Optional bounded Sina SDK probe returned 674 rows; old 832982 was tested separately
and never aliased. The native SDK merges/fills/rounds/deduplicates, so its output
was not admitted as a canonical fallback. A separate fixed-URL raw price adapter
uses the installed decoder without those postprocessing steps and archives
original bytes through neutral ingestion. 674 selected observations were retained
(2024-01-02 to 2026-10-19); 112 outside-range rows remain in the raw response.
The CLI's rejected count reflects range selection, not bad-price coverage.

Provider consistency, volume units, price basis, code history and session/status
coverage remain unverified. All observations are LOW/retrieval-time; no daily_bars
or trading authority is created. Registry bytes verify 10/10; new raw data is
outside earlier encrypted backups and ignored by Git. No schema, readiness,
trading-module, commit or push change. Final checks are in the linked report.
Offline raw reconstruction matches all 674 stored records. Full suite:
**1392 passed / 6 skipped**, 48.79 seconds, 24 new cases. Ruff/mypy (242 files),
governance (99 checks) and `git diff --check` pass; 75 focused provider/CLI and
7 final governance cases pass. No independent price calibration is claimed.

### Real Nonfinancial Inputs: October 20

WP-RESEARCH-004 [adds a real 002624 example](docs/nonfinancial-research-inputs-2026-10-20.md):
eight current/comparative facts from a retained official unaudited 2026H1 PDF,
read beside 674 existing daily observations at one pinned cutoff/snapshot.
Exact Decimal conversion supports explicitly annotated CNY, CNY-thousand and
CNY-million; separate nonfinancial calendar-YTD operating cash flow is neither
income, parent-only cash flow nor FCF. Same-filing comparisons normalize units.
Extended packets use v4; legacy v1/v2/v3 packet identities stay unchanged.
No database migration. The combined CLI is not a second ResearchReport and
does not invent screening, a queue, financial scores, validation or trading.

Real combined output is deterministic: eight source-bound LOW observations,
ROE/ROIC absent from the requested inputs, technical CONFLICTED, bearish setup
ARMED. The filing discloses ROE but no nonfinancial ratio contract is implemented;
this is an implementation gap, not provider absence. Debt/cash drivers, valuation,
sector/news/sentiment, admitted scoring and actual strategy validation remain.
Nine of nine registered artifacts verify; new files remain outside earlier
encrypted backups and are ignored by Git. No commit/push. PIT UNSUITABLE,
production NOT_READY and disabled defaults unchanged. Final verification is
recorded in the linked report; no independent-source or release acceptance.
Final verification: **1368 passed / 6 skipped**, 50.04 seconds, 33 new cases;
Ruff/mypy (241 files), governance (97 checks) and `git diff --check` pass.
Focused source/research tests pass 341 cases. Brokerage-specific financial
semantics for 600109 remain separate; do not reuse the nonfinancial profile.

### BSE Daily Fetch Repair: October 20

Follow-up maintenance of WP-RESEARCH-003 fixes the production adapter/ingestion
path, not only the access probe. Empty, malformed and wrong-type primary frames
now attempt the correctly routed fallback. Both unusable endpoints raise a
sanitized typed failure retaining endpoint, category, attempts and allowlisted
missing field. Only network-class exceptions retry, independently per endpoint;
the outer retry cannot multiply them. CLI worker/parent preserve these details
instead of masking them as an invalid-JSON ValueError. Failures do not enter
cache; a centralized fetch-version key bypasses old empty caches without
rewriting prior source evidence. A successful fallback is not source approval.

One bounded repeat at 10:53:17-19 UTC: 920982 main ConnectionError; bj920982
fallback KeyError/day, labeled bse_daily_payload_unavailable. This is an observed
payload limitation, not proof that BSE history never exists. No new price/fact
population or readiness promotion. Technical/fundamental candidate research
remains the priority; missing BSE data must not block other equities or be
replaced by guessed old-code history. Full verification results are recorded
in the linked [condition/diagnosis report](docs/research-condition-bridge-2026-10-20.md).
Final full suite: **1335 passed / 6 skipped**, 46.39 seconds. Ruff, mypy
(240 files), governance (95 checks) and `git diff --check` pass. Fourteen new
regressions cover fallback, non-network no-retry, bounded retry recovery,
safe worker/parent failure propagation, index identity and legacy-cache isolation.
No commit/push, source qualification, remote CI or investment validation claimed.

### Candidate Conditions And BSE Diagnosis: October 20

WP-RESEARCH-003 [joins research conditions](docs/research-condition-bridge-2026-10-20.md)
inside the single official ResearchReport. Explicit request styles separate a
long-term confirmation hypothesis from improved Turtle. Actual screen failures,
missing finance, technical conflicts and candidates requiring validation have
distinct states; blocked/rejected reports remain incomplete. Confidence policy
comes from effective settings, no new score/order or schema is created, and
bearish setup references are not long-position stops. Current Financial stays
unscored; real five-stock financial/technical validation is not completed.

AKShare 1.18.64 real per-endpoint probes: 920982 main source ConnectionError,
correct bj920982 fallback KeyError/day; 000063 control has the same main error
but fallback returns 674 rows. This isolates a main-source connection issue and
a separate BSE fallback limitation, not a Tushare account-tier diagnosis. Safe
bounded diagnostics preserve failures without exposing provider exception text
or promoting coverage. The linked report also distinguishes prior platform/data
hardening from actual strategy implementation. No new business data, real
financial reports, schema, trading module, commit/push or readiness promotion.
Final verification: **1321 passed / 6 skipped**, 48.92 seconds; Ruff and mypy
pass (240 source/script files), governance passes **95 checks**, and
`git diff --check` passes. Forty new regression cases cover candidate/report
states, financial gaps, independent Turtle confirmations, policy/hash binding,
future inputs, invalidation direction, persistence and safe bounded diagnostics.
Synthetic acceptance proves software behavior only, not real-source truth or
investment effectiveness. No independent-host, remote-CI or release acceptance.

### Technical Implementation Audit And Calculation Slice: October 20

The [actual-code audit](docs/technical-implementation-audit-2026-10-20.md)
found MACD/KDJ, triple-average/Granville events and startup/confluence were
design-only. Tong's explicit request authorizes WP-RESEARCH-002 for software
calculations without waiting for the provider horizon. Configurable diagnostic
features now flow through Technical Research and official report persistence;
new outputs remain unscored and family contradictions visible. Four-confirmation
Turtle admission and actual >3000 pattern breadth checks are repaired. No schema
or trading-module change. WP-RESEARCH-001 source/style/strategy validation gates
remain planned; seven-plus-one is postponed at Tong's request.

Existing business databases contain zero visible bars for the five requested
equities at the pinned cutoff. New captures use an independent ignored research
database: a bounded retry captured 674 unadjusted 000063 bars, retaining LOW/
retrieval-time limitations. No complete model-backed stock conclusion is claimed.
PIT stays UNSUITABLE, production NOT_READY and execution/notifications disabled.
No commit/push. Final verification results follow below.

Final captures: four equities (000063/002624/688363/600109), 674 observations
each, latest October 19. BSE 920982 remains unavailable after a real 920-prefix
fallback misrouting fix and retry. Real calculation output at October 20
09:45:41Z shows conflicted technical families on all four available series, not
buy signals or a completed financial synthesis. Tong clarified all five stocks
and explicitly deferred seven-plus-one; it is not a blocker for this slice.

Full suite: **1281 passed / 6 skipped**, 82.74 seconds; Ruff and mypy pass (238
source/script files). New data is outside earlier encrypted backups and needs
normal evidence retention; it is ignored by Git. A final owner-deferral label
change passes **240 focused tests**. Governance and `git diff --check` pass.
All four new registered raw-frame artifacts verify with explicit root
`data/processed/raw/provider-artifacts`; using generic `data/raw/provider-artifacts`
first reported four missing files, an incorrect-root observation, not lost bytes.
No remote-CI, independent price-source or release acceptance claimed.

### Declared Research Evidence Admission: October 20

The [shared scoring repair](docs/research-evidence-admission-2026-10-20.md)
excludes undeclared annotations from Policy/Industry/Value scores and confidence
while retaining all original evidence/ids. Empty/missing/duplicate/boolean/text
rubrics remain incomplete and unscored; invalid ranges fail closed. Component
versions and admission diagnostics are explicit. Integration tests preserve
annotations in SQLite and block InvestmentScore from incomplete reports.
Financial stays unscored; direct calculated technical/trend/pattern paths and
all trading modules are unchanged. No schema/business data/real reports/commit/
push/readiness changes. Source truth, caller quality, legacy report audit and
formal scoring policies remain independent gaps.

Latest full suite: **1207 passed / 6 skipped**, 41.66 seconds; 24 new cases.
Ruff/mypy pass (234 source/script files), governance passes 91 checks and
`git diff --check` passes. After documentation updates, targeted governance/
research/persistence checks pass 163 cases. No remote-CI/release acceptance.
Next: reviewed bank/source/freshness/valuation inputs and runtime market-rule/
policy gates, not live enablement or automatic data promotion.

### Bank Research Input And Freshness Diagnostics

The [bank input policy](docs/bank-research-input-policy-2026-10-19.md) now maps
nine China-A group-bank requirements to exact receipt-bound diagnostic checks.
Latest rejected/ambiguous/unsupported inputs do not fall back favorably; missing
and not-requested remain distinct. Report age is separate from capture age;
effective Settings default freshness to UNASSESSED. Financial research/CLI
expose hashes, gap and age states without scoring. A real read reconstructs six
LOW observations for four required metric names and five canonical gaps; the
current period is 202 days old, not automatically current because just reviewed.
Existing data/schema/PIT/live defaults remain unchanged; no real reports or
scores were generated. No commit or push. Next: independently reviewed missing
bank definitions/population, freshness/valuation and remaining runtime gates.

Latest primary-workspace verification: **1183 passed / 6 skipped**, 45.64 seconds;
Ruff and mypy pass (234 source/script files), governance passes 90 checks and
`git diff --check` passes. Twenty-three new regression cases cover gaps,
no-fallback selection, scope/period definitions, age boundaries, equivalent
timezone instants, settings wiring and read-only CLI exports. Real final export
hash was reproduced under the final code. No release/remote-CI acceptance.

### Financial Scoring Admission Repair: Adopted Locally

The [admission repair](docs/financial-scoring-admission-2026-10-19.md) is now
applied to the primary PyCharm working tree after approval recovered. All twelve
target-file baselines and the patch application check matched before adoption.
It removes financial evidence-only scoring without a separately
admitted source/sector policy, preserves diagnostics, and blocks incomplete
Financial/Value reports from producing InvestmentScore through the existing
builders. Twenty regression cases cover old bypasses, caller authorization
claims, empty inputs, report propagation and SQLite persistence. No business
data, schema, live defaults, commit or push changed. Original patch/manifest
files remain historical preparation evidence, not current adoption status.

Primary-workspace verification: **1160 passed / 6 skipped**, 50.72 seconds;
Ruff and mypy pass (233 source/script files), governance passes 89 checks and
`git diff --check` passes. The two business database main-file hashes are
unchanged across the checks; this is not full WAL/content/recovery verification.
No remote-CI, installed-release or independent-host acceptance is claimed.
Next: explicit bank research-input/gap policy and
outstanding runtime/policy gates, not numerical financial scoring or trading.

### Bank Financial Input Semantics: October 19

The [bank-unit slice](docs/bank-financial-inputs-2026-10-19.md) adds two real
group period-end ratios with explicit percent/null-currency/basis semantics.
It prevents monetary scaling and implicit fraction/annualization assumptions;
v1/v2 packets still reproduce their original hashes. Richer receipts are v3.
Exploratory totals are eight facts, 13,228 provider records and 11/11 verified
artifacts; financial scores remain unavailable and no real reports were created.
Operational counts/audit identity, schema, PIT and disabled defaults stay
unchanged. New data is outside the earlier encrypted snapshot. No commit/push.
Next: explicit bank research-input/sector policy and outstanding runtime/policy
gates, not a score inferred from two ratios or live trading.

Bank-unit-slice local verification: **1140 passed / 6 skipped**; Ruff and mypy pass
(233 source/script files), governance passes 88 checks and whitespace checks
pass. Twenty-three regression cases were added. No remote-CI, release or
independent-host acceptance is claimed.

### Same-Filing Financial Comparatives: October 19 MYT

The [comparative research slice](docs/financial-comparatives-2026-10-19.md)
adds three explicit comparative observations from the retained later filing,
not original 2025 numeric revisions. Exploratory totals are now 6 facts,
13,226 provider records and 10/10 verified artifacts. V1 source packets/hashes
are preserved; comparative packets and richer input receipts are versioned.
Two YTD year-on-year changes and one asset change since prior year-end are
source-bound descriptive diagnostics, never scores or investment returns.
Wrong filing/period/unit/scope, duplicate or rejected inputs cannot produce
a favorable fallback; nonpositive baselines yield no growth percentage.
Financial research remains unscored, four requested input gaps remain visible,
and no real ResearchReport/ValidationReport was generated. Operational data,
schema, PIT and disabled defaults are unchanged. New data is outside the
earlier encrypted snapshot. No commit or push was performed.

Comparative-slice local verification: **1117 passed / 6 skipped**; Ruff and mypy pass
(233 source/script files), governance passes 87 checks and whitespace checks
pass. Next: bank-appropriate observations/units and an
explicit sector research/scoring policy, not automatic trading.

### Financial Source Inputs: October 19 MYT

The [research input boundary](docs/financial-source-inputs-2026-10-19.md) now
reconstructs the three reviewed facts from retained PDFs/packets and checks
fact/evidence content, artifact metadata, batch ownership/parameters and visible
completion. Typed immutable diagnostics preserve rejected versus missing rows
and bind exact consumed facts/cutoffs in ResearchContext. Financial research
with fundamental inputs remains unscored; attaching high-score evidence cannot
approve it. Scope, bank applicability, source status and input hashes are
visible without promoting trust. Real reads bind three LOW observations and
retain four explicitly requested gaps, not a complete bank checklist.
That read-only slice left both databases unchanged with zero real reports;
PIT and all disabled defaults are unchanged. New diagnostics are local, not
part of the earlier encrypted backup. No commit or push was performed.

Source-input local verification: **1096 passed / 6 skipped**; Ruff and mypy pass
(232 source/script files), governance passes 86 checks and whitespace checks
pass. Next: comparable financial periods/relevant metrics
and explicit sector research/scoring policy, not live trading.

### Reviewed Issuer Facts: October 18

The [dedicated filing extraction](docs/reviewed-filing-facts-2026-10-18.md)
published three explicit group/CNY financial observations into the exploratory
fact table with their review packet, evidence and audit transaction. This is
manual issuer extraction, not promotion of AKShare mappings or the spot-review
report. LOW/retrieval-time facts are invisible before capture/review availability;
original source bytes/semantics stay bound. Retries are fact-idempotent and
conflicting versions fail closed. Existing instrument metadata is unchanged.
Scope/sector/source details require companion evidence, not raw fact rows alone.
Exploratory totals: 3 facts, 13,223 provider records, 8/8 verified artifacts;
zero ResearchReports/ValidationReports. Operational data and all trading defaults
are unchanged. Dataset readiness is not promoted and new data is not retained
in the earlier encrypted snapshot. No commit or push was performed.

Issuer-extraction local verification: **1043 passed / 6 skipped**; Ruff and mypy pass
(229 source/script files), governance passes 85 checks and whitespace checks
pass. Next: source-bound, sector-aware research reads and
additional reviewed financial periods/metrics, not automated trading.

### Source-Bound Financial Spot Review: October 18

The [financial source review](docs/financial-source-corroboration-2026-10-18.md)
captured three real issuer PDFs in the exploratory database and compared three
2026-Q1 values with retained native evidence. Group CNY-million revenue,
parent-attributable profit and total assets numerically match under an explicit
native-unit hypothesis. A versioned read-only review tool retains source/plan/
row hashes, conservative review availability and rejected/missing results.
All authorizations stay false: this is not an approved accounting mapping,
independent-provider validation or InvestmentScore input. Native records stay
LOW/retrieval-time; that earlier checkpoint had zero canonical facts or completed
research/validation reports. Operational data was unchanged; 7/7 exploratory
artifacts verified then. New captures postdate the retained encrypted snapshot and
are not claimed backed up there. No schema/trading changes, commit or push.

Spot-review local verification: **1003 passed / 6 skipped**; Ruff and mypy pass
(226 source/script files); governance passes 84 checks and whitespace checks
pass. Recovery-slice results below are historical checks,
not claims of installed-package, remote-CI or independent-host acceptance.

### Reviewed Recovery Baseline: October 18

Tong approved consolidating the eighteen local continuation slices in a local
Git commit without pushing. The [baseline review](docs/reviewed-baseline-2026-10-18.md)
records scope, installed-wheel/source identity, quality checks and unresolved
acceptance gates. The commit containing that report is the recovery checkpoint;
use Git for its exact identity. The slice-specific uncommitted/test-count notes
below are historical checkpoints, not the current checkout state. A local
commit is not remote/off-device retention. PIT stays UNSUITABLE and production
NOT_READY; execution and notifications stay disabled.

### Encrypted Same-Host Recovery: October 18

The [actual recovery drill](docs/encrypted-recovery-2026-10-18.md) retained both
operational and exploratory snapshots on the verified existing encrypted
sparse-bundle. Corrected isolated restores matched source content; 8/8
registered artifact files and five rule/capture files were copied/verified.
The initial metadata-timestamp mismatch was rejected and diagnosed, not hidden.
New local backup/restore hardening adds content hashes, skips current-schema
initialization, rejects lossy NUL text and closes read snapshots/connections.
This repair is not yet committed or pushed; historical baseline preflight
results do not attest this dirty working tree. The encrypted volume was safely
detached. Independent-device recovery, cloud upload completion and complete
ignored-file/code-history retention remain open. Next: review this bounded
repair and finish authoritative launch input/policy gates, not live trading.

Recovery-repair verification: 961 passed / 6 skipped; Ruff and mypy pass
(224 source/script files), governance passes 83 checks and whitespace checks
pass. These are final local checks, not new installed-package/remote-CI or
independent-device acceptance. No database schema or trading boundary changed.

- Provider-neutral evidence contracts and transactional ingestion
- Provider-neutral ingestion now enforces every trust-level ceiling for both
  records and raw artifacts before any persistence, and rejects capabilities
  declared under another provider identity. This repairs the former
  VERIFIED-only check, not source quality or historical completeness. Existing
  stored evidence is not reclassified; see risk `R-036` and debt `TD-037`.
  The October 16 repair adds 52 regression cases; full verification reports
  535 passed / 6 skipped, Ruff and mypy pass, and governance/diff checks pass.
- The [SSE notice evidence slice](docs/sse-calendar-notice-evidence-2026-10-16.md)
  captures 14 explicit dates and source bytes through neutral ingestion. Typed
  reads include them in the same runtime snapshot, preserving MEDIUM trust,
  retrieval-time visibility, conflicts and review expiry. It neither merges
  into the open-only calendar nor proves a complete exchange schedule.
  That slice used `sse-runtime-input-v1.2`; schema is unchanged.
  Notice-slice verification: 558 passed / 6 skipped, Ruff and mypy pass
  (208 source/script files), governance passes 63 checks, and diff checks pass.
- The [daily-price evidence slice](docs/daily-price-evidence-2026-10-16.md)
  now commits unadjusted AKShare bars, exact row/source/availability bindings,
  raw-frame artifacts and audit records in one neutral ingestion transaction.
  Cache reads retain original serialization and verify hashes; snapshot bytes
  must reproduce normalized prices exactly. The real sample adds six new
  bar/evidence observations without overwriting older versions. Its primary
  source matches the earlier fallback's six OHLC/native-volume observations,
  but this is not independent calibration. Trust remains LOW/retrieval-time;
  runtime v1.3 exposes exact matches and unresolved review requirements.
  Price-slice verification: 576 passed / 6 skipped; Ruff, mypy (210 source/script
  files), governance (64 checks), and diff checks pass. No schema change or
  readiness promotion; the three continuation slices remain uncommitted.
- The [ordinary SSE calendar slice](docs/sse-calendar-plan-2026-10-16.md)
  binds the reviewed annual notice, 46 explicit assertions and verified
  effective weekday references to a separate deterministic calendar plan.
  Runtime v1.4 keeps raw sessions unchanged, rechecks annual artifact bytes,
  and preserves unknown/conflicting/expired inputs. The October 1-16 window
  has 7 planned open and 9 planned closed days, not verified actual opening.
  Ordinary-calendar verification: 593 passed / 6 skipped; Ruff, mypy (212 source/script
  files), governance and diff checks pass. Schema/readiness are unchanged;
  all four continuation slices remain uncommitted and unpushed.
- The [suspension evidence repair](docs/suspension-evidence-repair-2026-10-16.md)
  disables the misrouted delisted-quote/current-suspension endpoint and removes
  unconfirmed resumption inference from normalization and AKShare calibration.
  Versioned dated captures now archive source frames and LOW/retrieval-time
  events in one neutral transaction, preserving company metadata. Runtime v1.5
  retains lifecycle evidence and flags legacy records without assuming normal
  ST/suspension/listing status. The real 13-row capture created 13 reported
  starts and zero confirmed resumptions; full status coverage remains open.
  Schema/readiness are unchanged; the five continuation slices are uncommitted
  and unpushed. Suspension-slice verification: 621 passed / 6 skipped; Ruff, mypy (213
  source/script files), governance (66 checks), database integrity and diff
  checks pass.
- The [shared lifecycle usability slice](docs/lifecycle-usability-review-2026-10-16.md)
  separates reviewable, observation-only and logically quarantined records.
  Runtime v1.6 and lifecycle coverage use the same review policy; invalid,
  legacy or wrong-scope rows cannot improve coverage, and weak trust cannot
  be averaged upward. All originals remain preserved. Local MooMoo UI reading
  timed out; no displayed data, permissions or broker capabilities were
  verified. Framework/schema/readiness and disabled execution are unchanged.
  All six continuation slices remain uncommitted/unpushed; final check results
  and remaining raw-reader/calibration boundaries are recorded in the report.
- [Replay status review](docs/replay-status-review-2026-10-16.md) now applies
  shared usability review at replay and ValidationRequest boundaries. Version
  v0.6.3.2 binds source records/review metadata and rejects invalid/observation-
  only status without dropping adverse-status samples. Reconstruction shares
  one read snapshot; manifest/sample persistence is atomic. Framework/schema
  and real-readiness conclusions are unchanged; all seven slices are local,
  uncommitted and unpushed. Latest verification: 670 passed / 6 skipped; Ruff,
  mypy (214 source/script files), governance (69 checks), database integrity
  and diff/whitespace checks pass.
- The [deployment gap plan](docs/deployment-gap-plan-2026-10-16.md) defines five
  remaining delivery groups, starting with trustworthy launch inputs and one
  real validated strategy chain, then Paper, sandbox/deployment and separately
  approved live work. The local sample has no real research/validation/portfolio
  reports; software test count is not a trading-readiness percentage.
- The [outcome/persistence integrity slice](docs/replay-outcome-integrity-2026-10-16.md)
  advances replay/confidence to v0.6.3.3. Exact UTC calendar endpoints, horizon
  and availability lag replace moving first/last-price windows; start prices
  use decision-time visibility. Missing/unsupported outcomes remain blocked
  samples. The request factory recomputes bound outcomes. New manifest/sample
  writes are immutable, owner-bound, idempotent and atomic, with separate run
  identities but stable economic sample hashes. No schema or real-readiness
  promotion occurs. Latest verification: 699 passed / 6 skipped; Ruff, mypy
  (215 source/script files), governance (70 checks), read-only database audit
  and whitespace checks pass. Eight continuation slices are local/uncommitted/
  unpushed. Upstream full research-content hashing remains open (TD-040).
- AKShare data foundation and quality audit
- [Research-content binding](docs/replay-research-binding-2026-10-16.md) advances
  replay/confidence to v0.6.3.4 and binds full report/evidence/policy content
  plus visible fundamental/screening row inventories. Missing/conflicting or
  future nested evidence blocks eligibility, with diagnostic samples preserved.
  ValidationRequest rechecks content hashes, manifest mapping and derived
  research fields. Evidence writes now reject conflicting identity reuse.
  Correction: report header writes already reject duplicate ids; mutable child
  evidence and duplicate module assessments were the actual defects. Latest
  verification: 744 passed / 6 skipped; Ruff, mypy (216 source/script files),
  governance (71 checks), database audit and whitespace checks pass. No schema
  change or readiness promotion. Nine slices remain local/uncommitted/unpushed.
  Next: real SSE pilot coverage manifest with exact blockers, not fixture-based
  strategy approval. Original-run input lineage/source attestation stays open.
- Optional Tushare capability and calibration adapters
- The [real SSE coverage manifest](docs/sse-pilot-coverage-2026-10-16.md) now
  reads runtime and research inputs in one read-only snapshot. The actual
  Oct 1-15 price window/Oct 16 cutoff has six bound price dates with LOW/
  retrieval-time evidence, a 15-bar deficit against the configured minimum,
  absent scoped status/fundamentals/universe/research and 21 unresolved
  requirement codes, not 21 development phases. Protected optional JSON
  exports remain ignored local data, not a readiness promotion or Git backup.
  Latest verification: 752 passed / 6 skipped; Ruff, mypy (217 source/script
  files), governance (72 checks), database and whitespace checks pass. No
  schema/readiness change; ten slices remain local/uncommitted/unpushed.
  Next: extend explicitly exploratory history and current financial/disclosure
  capture through existing ingestion, without backdating or trust inflation.
- CNInfo disclosure evidence through explicit AKShare transport provenance
- [Real exploratory expansion](docs/exploratory-data-expansion-2026-10-16.md)
  collected 187 unadjusted dates, 13,000 native rows across three statements
  and 30 direct CNInfo metadata records in a separate research database. Four
  price/financial artifacts passed hash checks; the original business database
  is unchanged. The native financial evidence path uses neutral transactions,
  preserves unknown units/missing values and creates zero canonical facts or
  research/validation reports. Pilot inventory v1.1 exposes native/metadata
  counts separately. Current numerical trend warm-up deficit is zero in the
  exploratory sample, not a strategy or PIT pass. Latest checks: 762 passed /
  6 skipped; Ruff, mypy (218 source/script files), governance (73 checks), both
  database audits and whitespace checks pass. Eleven continuation slices stay
  local/uncommitted/unpushed. Next: reviewed financial metric/unit mapping and
  source/status/universe coverage. Five final acceptance groups remain open;
  no calendar completion date or defensible trading-readiness percentage exists.
- Yahoo US/Hong Kong/Malaysia research-grade daily-bar evidence
- [Financial numeric hardening](docs/financial-numeric-hardening-2026-10-17.md)
  fixes a confirmed legacy zero/alias-selection defect, handles missing values
  without inventing zero, and rejects conflicting/nonfinite numeric inputs.
  Twenty new regression cases include atomic rollback. Legacy ingestion now
  warns explicitly about unreviewed semantic/unit assumptions; real native
  observations remain on the noncanonical capture path. Latest verification:
  782 passed / 6 skipped; Ruff, mypy (218 source/script files), governance and
  whitespace checks pass. No schema, database, trust or readiness change;
  twelve continuation slices remain local/uncommitted/unpushed. Next: review
  evidenced metric/unit/period/industry mappings before canonical population.
- [Fundamental fact integrity](docs/fundamental-fact-integrity-2026-10-18.md)
  now rejects same-hash material disagreements and within-batch/concurrent
  conflicts instead of silently accepting ignored inserts. Writer reservation
  plus a savepoint keeps each call atomic even inside a caller transaction.
  Original values, versions and audit metadata remain unchanged on repeats;
  invalid legacy numerics are flagged, not repaired. Verification: 808 passed /
  6 skipped; Ruff, mypy (218 source/script files), governance and whitespace
  checks pass. No schema/data/readiness promotion or trading-module changes.
  Thirteen continuation slices remain local/uncommitted/unpushed; next is
  evidenced metric/unit/period mapping, not simulation or live enablement.
- [Research input integrity](docs/research-input-integrity-2026-10-18.md)
  binds bars/facts to the candidate and metric, rejects future queue/metadata/
  report periods and conflicting fact versions, and rechecks before a run
  starts. Financial diagnostics select by period and visible version instead
  of input order and expose original trust/unit/availability labels. The
  financial module is `financial-v0.5.1-input-integrity`; no automatic scoring
  or canonical unit mapping is added. Verification: 840 passed / 6 skipped;
  Ruff, mypy (218 source/script files), governance and whitespace checks pass.
  Framework/schema/readiness are unchanged. Fourteen slices remain local/
  uncommitted/unpushed. Native-to-canonical mapping/source review remains next.
- [Offline research deployment preparation](docs/research-deployment-runbook.md)
  adds the installed `tong-quant` command, explicit-root startup and offline
  preflight. Runtime/checkout/commit Python bytes, safe effective configuration,
  dependencies, governance and read-only database integrity are checked without
  authorizing trading. A wheel was installed into an isolated temporary target
  and exercised outside checkout with verified package origin/version. CI smoke
  checks are configured but have not run remotely. Verification: 862 passed /
  6 skipped; Ruff, mypy (219 source/script files), governance and whitespace
  checks pass. Current release preflight remains blocked by uncommitted source
  and dirty Git; database content audit is unchanged. Fifteen continuation
  slices remain local/uncommitted/unpushed. No schema, PIT, production or live
  promotion. Next: reviewed clean-release/dependency/restore evidence alongside
  source-evidenced financial mapping and the existing strategy/Paper gates.
- [Native dependency baseline](docs/dependency-baseline-2026-10-18.md) now pins
  35 runtime / 48 dev packages plus four build tools with artifact hashes and
  scoped manifests. New clean-venv installation, import isolation, installed
  console and version checks passed without borrowing the PyCharm environment.
  Preflight v1.1 checks actual locked versions; macOS arm64/Python 3.12 and
  macOS 14+ scope is explicit, not a universal lock. Verification: 884 passed /
  6 skipped in both environments; Ruff, mypy (221 source/script files),
  governance and whitespace checks pass. Source-build, signing and independent
  host limits remain explicit. Sixteen slices are local/uncommitted/unpushed;
  schema, data, PIT and live readiness remain unchanged. Next: reviewed clean
  release and encrypted restore/artifact portability, alongside strategy inputs.
- [Registered artifact portability](docs/artifact-portability-2026-10-18.md)
  adds a bounded read-only registry/file audit, safe explicit-root reads and
  deterministic reference/report hashes. Both local databases verify 4/4
  registered files; the corrected runbook distinguishes their different roots.
  This is not a full database-content hash, encrypted backup, independent-host
  restore or unregistered-capture inventory. Verification: 905 passed / 6
  skipped; Ruff, mypy (223 source/script files), governance (80 checks) and
  whitespace checks pass. Seventeen continuation slices remain local,
  uncommitted and unpushed. Schema, PIT, production and execution are unchanged.
  Next: consolidate/review the local changes and perform approved encrypted
  recovery, while advancing independently authorized strategy/data inputs.
- [Research bar integrity](docs/research-bar-integrity-2026-10-18.md) now gives
  Technical/Trend/Pattern one checked daily-observation selector. Duplicates
  and revisions cannot inflate warm-up; conflicting versions, intraday-shaped
  input, mixed sources, adjusted and nonfinite inputs fail closed. Direct
  calls recheck context visibility. Technical N-interval returns and window
  requirements are corrected; all three model versions are centralized.
  Verification: 956 passed / 6 skipped, Ruff and mypy (224 source/script files)
  pass; governance passes 81 checks and whitespace checks pass. No source/PIT/
  session authentication or strategy acceptance is claimed. Eighteen slices
  remain local/uncommitted/unpushed. Next: consolidate/review the accumulated
  changes, then establish an approved recoverable baseline and complete
  authoritative launch inputs before the planned Paper package can advance.
- Provider-neutral unadjusted daily-bar calibration with deterministic fixtures,
  optional Massive US evidence, trust ceilings, and auditable unavailable or
  incompatible outcomes
- Schema baseline, checksum migrations, and physical fingerprint checks
- Scheduled provider contract monitoring
- Provider health operations with explicit owner, acknowledgement, recovery,
  repeated-condition escalation, content-addressed reports, and 90-day CI
  artifact retention
- Immutable longitudinal provider baselines with separate success, field
  coverage, and schedule-continuity metrics
- Credential-free, content-addressed provider evidence bundles with explicit
  `as_of`, per-scope continuity, deterministic reconstruction, and tamper checks
- Content-addressed, no-overwrite durable evidence archiving with ZIP safety,
  credential screening, SQLite history integrity checks, copied-byte
  verification, and independent manifest revalidation
- Fail-closed per-scope evidence-horizon audits for the five scheduled
  CNInfo/Yahoo scopes, with exact 84-day/eight-check deficits and no automatic
  readiness promotion
- Provider monitor run-origin metadata: new GitHub-scheduled runs retain an
  auditable run/attempt reference, local or dispatched runs are manual, and
  pre-migration runs remain `unknown`. The current horizon gate counts only
  recorded scheduled runs toward its 84-day/eight-check requirement.
- Deterministic evidence-backed PIT readiness reassessment with immutable input
  hashes, explicit missing/stale evidence, cause classification, and no
  automatic promotion
- Direct CNInfo disclosure metadata and content-addressed filing artifacts with
  immutable capture observations and AKShare-transport parity support
- Read-only SQLite integrity audits, verified online backups, and isolated
  no-overwrite restore drills
- Discovery, Screening, Research, Validation, Historical Replay, Portfolio/Risk
  research artifacts, and disabled Notification infrastructure
- Fail-closed Historical Replay data-quality eligibility: explicit readiness
  datasets, minimum trust enforcement, incomplete-sample preservation, and
  readiness evidence hashes before ValidationRequest creation
- CI type-checking covers both the reusable `src` packages and operational
  `scripts` entry points
- Portfolio proposals now preserve a typed, persisted research/assessment/
  score/validation evidence chain; repository writes verify that chain against
  authoritative records. A-share sellability and price-limit helpers fail
  closed until effective-dated exchange evidence exists.
- The read-side PortfolioEvidenceGate re-verifies lineage at a decision time
  using explicit freshness, model-version, and configuration requirements;
  cash is exempt from sector/country/theme concentration breaches. This is
  structural research evidence only, not a Paper or live approval.
- Its policy now reads effective project configuration; a reviewed Validation
  configuration hash must be pinned explicitly because the default is empty
  and refuses construction. This provides a controlled policy path, but the
  future simulation boundary must still require it. Paper, PIT, and live
  readiness are unchanged.
- US, Hong Kong, and Malaysia market-rule helpers no longer assume same-day
  sellability or unrestricted prices without dated evidence; they now reject
  those calls until the relevant rule capabilities are supplied.
- Buy/sell quantity normalization for all four markets also rejects calls
  without dated lot and account rules; the generic Instrument lot-size default
  must not become an executable market assumption.
- The [project-wide audit](docs/architecture-audit-2026-10-15.md) repairs lost
  candidate exposure classifications, Portfolio/Risk configuration drift,
  mixed-version proposal reads, stale notification worker acknowledgements,
  and silent same-version bar/calendar replacement. Existing persisted results
  are not rewritten. New Portfolio/Risk model versions distinguish corrected
  research artifacts.
- Market-rule capability coverage now has versioned, PIT-visible declarations,
  exact exchange/board/account scopes, explicit missing/ambiguous states, and
  reproducible evidence hashes.
- The [SSE main-board pilot](docs/sse-main-board-pilot.md) now verifies three
  pinned official documents and calculates ordinary buy increments, confirmed
  settled-lot sellability, odd-lot sell quantities and daily price bands. Its
  typed inputs bind dates, source review, status/classification flags, calendar
  content and calculation hashes. Raw sources are local ignored artifacts
  and can be recaptured on a new device. A read-only runtime input inventory
  now reconstructs stored sessions (including closed dates), status,
  unadjusted previous close and corporate-action observations in one SQLite
  snapshot. It preserves trust and reports missing evidence; it does not
  construct trusted calculation context. On October 16 the default local
  `data/tong_quant.sqlite3` did not exist; the command reported
  `database_missing` without creating it. A subsequent
  [real ingestion exercise](docs/operational-data-sample-2026-10-16.md) created
  a local research sample: six distinct daily bars (12 observed versions),
  8,797 open-date rows and current company information. It also exposed
  backdated availability, fabricated fallback turnover and placeholder
  metadata replacement; new ingestion now fixes those behaviors and preserves
  old observations. Numeric facts no longer inherit earlier visibility/trust
  from matched publication events. The subsequent
  [corporate-action repair](docs/corporate-action-mapping-2026-10-16.md) now
  maps those 26 source rows to 33 research events. Two fresh observations are
  retained; replaying one cached snapshot inserts zero duplicates. Units,
  provider-labelled implementation and ex-dates are checked, with rejected
  rows preserved in audit warnings. All new actions remain LOW/RETRIEVAL_TIME.
  Zero or partial normalization remains partial, not absence of actions. Runtime
  evidence categories remain unresolved. Reviewed provenance, listing-phase,
  action-coverage and account-lot readers, intraday restrictions and the
  simulation boundary remain incomplete; this does not
  complete `WP-LAUNCH-001` or change PIT/live readiness.

## Controlled Launch Boundary

Paper Trading and broker-native simulation development may now proceed through
the approved work packages below while the 84-day evidence horizon continues in
parallel. Broker work is initially read-only or sandbox-only. Live broker order
submission, unattended trading, live Order/Trade/Fill behavior, Asset
Allocation, Auto Rebalancing, and live execution remain frozen.

The default remains `execution.mode = "disabled"` and
`allow_live_orders = false`. No Paper Trading result or elapsed calendar time
may change those values automatically.

## Next Ready Work

1. `WP-EVIDENCE-001`: representative longitudinal evidence horizon
2. `WP-LAUNCH-001`: execution lineage and market-rule hardening

These packages run in parallel. `WP-LAUNCH-001` must bind every downstream
simulation decision to authoritative Validation, Portfolio, and Risk artifacts;
replace placeholder market-rule assumptions; and preserve the existing
fail-closed live-execution guard. After it completes, `WP-PAPER-001` may become
ready. `WP-BROKER-001` remains planned until the deterministic paper ledger is
complete.

The first `WP-LAUNCH-001` lineage and market-rule hardening slice is described
in [the controlled-launch architecture audit](docs/controlled-launch-architecture-audit-2026-10-15.md).
It does not complete the package or change PIT/live readiness.

`WP-READINESS-001` completed with 12 reviewed datasets, zero promotion-review
eligible datasets, and unchanged `UNSUITABLE` effective readiness. The next
package must retain and freeze at least 12 weeks of operational evidence before
another reassessment. The October 8 scheduled run completed successfully and
contains 17 checks per required scope across 47.2 days, with 7/12 baseline
periods and 58.3% continuity. Its downloaded artifact, SQLite integrity,
content-addressed bundle, and deterministic horizon reconstruction were
independently verified on October 9. The original horizon audit was ineligible
with 36.8 days outstanding under its former all-run count. All five required
scopes still carry expected
provider/data-limitation degradation, with no new implementation defect in the
latest run. The five stable warnings are acknowledged in
[GitHub issue #1](https://github.com/TONGResearch/tong-quant-framework/issues/1)
without promoting provider trust or PIT readiness. Elapsed calendar time alone
is not evidence, and the package cannot promote trust or PIT readiness
automatically.

The October 8 interim scope review found that its original 17-check count did
not encode scheduled versus manual run origin. Migration `0009` preserves those
old runs as `unknown`; a new version of the horizon auditor therefore counts
zero proven scheduled checks in that immutable snapshot. Future scheduled runs
record GitHub run and attempt identifiers for independent review. The new
84-day span starts with the first provenance-qualified scheduled run; the old
36.8-day deficit is not its remaining time. The monitor
database's empty calibration and conflict ledgers are not evidence of
cross-provider agreement.

On October 10, the October 8 artifact was retained in two independently
verified durable copies: a private local content-addressed archive and a
separate AES-256 encrypted sparse-bundle in private iCloud Drive. The encrypted
copy was detached, remounted from its final destination, and reverified before
CloudDocs reported a caught-up state. This closes the current two-copy storage
gap, but it does not satisfy the outstanding 84-day evidence horizon or promote
PIT readiness.

An isolated restore drill from the private local October 8 archive also passed
on October 10: the restored provider-history database matched the source audit
hash, schema fingerprint, migration head, and table counts. An independent
restore drill from the mounted encrypted iCloud copy also passed on October 10:
the restored audit hash matched the source (`2b2173cf...329eeba8`), with 17
contract runs, 85 checks, 17 baseline manifests, and matching table counts.
The encrypted volume was detached after the drill. The drill is now a repeatable
`archive_provider_evidence.py restore-drill` command with fail-closed tests and
credential-free, path-free summary output. Archive verification also rejects
bundled contract-run, check, or baseline identities absent from its embedded
SQLite history. Both retained copies are recoverable, but this does not close
the 84-day evidence-horizon deficit or change PIT readiness.

On the current `0.8.2` code, restoring the retained `0.8.0` snapshot applies
the `0009` and `0010` migrations in the isolated copy, so its post-migration audit hash is
expected to differ from the untouched source. Table counts and historical
records remain intact.

The October 10 post-migration manual Actions smoke test
([run #18](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38065714984))
passed on commit `539b676`. Its downloaded artifact matched the GitHub SHA-256
digest and passed archive verification and an isolated restore drill. The
database is at `0.8.1`/`0009`, with 18 runs, 90 checks, and 18 baselines.
The new run is recorded as `manual` with its GitHub run reference; all five
scopes have zero provenance-qualified scheduled checks. This verifies deployment
and recovery, not the evidence horizon or PIT readiness.

The first provenance-qualified scheduled observation is
[run #19](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38227888290),
completed successfully on October 12 from commit `539b676`. The Actions event,
run JSON, and SQLite row independently agree on `scheduled` origin and GitHub
run `38227888290` attempt 1. Its artifact digest `0c817d5a...cd490` matched the
downloaded ZIP; archive verification and an isolated restore drill recovered
19 runs, 95 checks, and 19 baselines with matching source/restored audit hashes.
Each required scope now has 1/8 provenance-qualified scheduled checks and a
0/84-day qualified observation span. The retained local archive ID is
`367af4cd...80444`. On October 13, a second independently verified copy was
retained in the AES-256 encrypted private iCloud sparse-bundle. Its archive ID
is `e0b8e0e0...735a0`; verification and an isolated restore drill reproduced
audit hash `9180999a...88711`, migration head `0009`, and matching table counts.
CloudDocs reported the detached sparse-bundle caught up at 15:48 Malaysia time.
The time gate cannot become eligible before approximately January 4, 2027, and
eligibility would still require uninterrupted evidence, an independent
provenance review, and a separate PIT readiness reassessment. PIT readiness
remains `UNSUITABLE`.

The next [scheduled run #20](https://github.com/TONGResearch/tong-quant-framework/actions/runs/38698359370)
completed on October 15 from commit `e6e98d2`, attempt 1. The GitHub schedule
event, artifact digest `053d4704...347733c`, run JSON, and SQLite origin row
were independently matched. The artifact contains 20 contract runs, 100 checks,
and 20 baseline manifests; all five required scopes have 2/8 qualified
scheduled checks across 2.9/84 days. Its evidence bundle and temporary
content-addressed archive passed verification and an isolated restore drill;
the restored copy advanced from schema `0009` to `0010` with matching table
counts. The five pre-existing provider/data-limitation warnings remain, with
no newly observed implementation defect. The calibration-attempt and conflict
ledgers are still empty, so they do not demonstrate provider agreement. The
October 15 artifact still needs durable private-local and encrypted off-device
retention. PIT readiness remains `UNSUITABLE`.

Planned work must respect dependencies in `config/project-governance.toml`.

Future planned work after the evidence and readiness gates:

- `WP-RESEARCH-001`: family-aware technical confluence and size/style research

This reservation covers MACD, KDJ, parameterized triple-average candle events,
Granville events, startup-state tracking, and dynamic invalidation references.
It is not ready and does not relax the trading-development freeze.

## Provider Policy

No provider is trusted by default. Tong Quant evaluates dataset evidence for
trust, coverage, availability precision, historical continuity, and
cross-provider consistency. Provider health does not imply PIT readiness.

## Agent Startup

1. Read `AGENTS.md`.
2. Read this file.
3. Read `config/project-governance.toml`.
4. Run `python scripts/check_project_governance.py`.
5. Select one `ready` work package and read its document.
6. Inspect the relevant code and tests before editing.

## Required Completion Checks

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src scripts
git diff --check
.venv/bin/python scripts/check_project_governance.py
```

Update this status, governance configuration, relevant work package, risk
register, and technical-debt register when a milestone changes project state.
