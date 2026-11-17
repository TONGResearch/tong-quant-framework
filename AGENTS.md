# Tong Quant Framework Agent Guidance

## Developer Context

- Owner: Tong Li
- Background: Computer Science student at Universiti Putra Malaysia
- Primary environment: PyCharm Professional on macOS Apple Silicon
- Python: 3.12
- Repository owner: TONGResearch
- Current data source: AKShare
- Source of truth: this local PyCharm project and its Git history

## Product Philosophy

The required workflow is:

> Discovery -> Hard Screening -> Research Queue -> Research ->
> Investment Scoring -> Validation -> Execution

Tong Quant is not a pure quantitative, technical-analysis, or AI system. It
combines opportunity discovery, traditional investment research, quantitative
validation, risk management, and controlled execution.

## Non-Negotiable Boundaries

- All upstream engines output the universal `Signal` model.
- Screening, research, strategies, market-regime analysis, events, and AI must
  never create or submit orders.
- Only `tong_quant.execution` may define order models or create orders.
- Risk checks have final veto authority before an order can be submitted.
- Keep data, screening, research, strategy, validation, portfolio, risk, and
  execution layers decoupled.
- Put market-specific behavior behind `MarketRules`, calendars, fee models, and
  provider or broker adapters.
- Never embed A-share assumptions in shared strategy logic.
- The typed SSE main-board pilot requires hash-verified local source documents
  and separately reviewed runtime calendar, status/phase/action and account-lot
  evidence. Never manufacture HIGH trust or a normal-listing flag to make a
  demo pass. Its calculation outputs cannot authorize Paper or live execution.
- SSE pilot calculations and runtime inventory share a conservative six-digit
  ASCII symbol boundary (600/601/603/605). Exchange tags alone cannot admit STAR,
  B-share, BSE, SZSE or fund instruments. A matching prefix is not a dated listing
  record or trading approval; preserve wrong-scope observations with explicit gaps.
- The SSE runtime inventory reads an existing database only, through one
  MarketDataService snapshot. Missing calendar dates are unknown, not closed.
  An empty corporate-action query is not proof of action-free status. Keep
  raw-data inventory separate from independently reviewed calculation inputs.
- Use point-in-time timestamps and reject future data.
- The SSE calendar-notice adapter emits only hash-pinned, explicitly reviewed
  dates with MEDIUM/RETRIEVAL_TIME evidence. Never infer a full calendar,
  weekends or settlement from a partial notice. Preserve conflicting and
  expired observations; a notice capture cannot complete runtime provenance.
- A complete reviewed annual notice plus verified effective weekday rules may
  derive a separate ordinary SSE schedule, never actual emergency opening,
  security status or settlement. Keep raw missing dates visible; expired,
  incomplete, conflicting or tampered evidence must remain unknown. Use an
  explicit rule capture, not an automatically selected latest file.
- Treat availability precision and data trust as separate concepts.
- Research, Validation, and future HistoricalReplay consumers must inspect
  both `AvailabilityPrecision` and `DataTrustLevel`.
- Do not treat PIT data as replay-ready until a `PITReadinessAssessment`
  supports that conclusion.
- Read `PITReadinessClassification` together with its numeric score,
  component scores, assumptions, and warnings. `CAUTION` and `UNSUITABLE`
  datasets must never be silently promoted by a consumer.
- HistoricalReplaySource reconstructs validation samples only. It must not
  backtest orders, allocate capital, connect to brokers, or make trade
  decisions.
- `ReplayConfidence` measures historical reconstruction quality separately
  from research correctness. Weak replay confidence must not be interpreted as
  proof that the research thesis was wrong.
- Every ReplayQuery must declare all underlying `readiness_datasets`, require
  at least `MEDIUM` trust, and preserve incomplete samples. Validation request
  creation must fail closed if the manifest or any sample is not explicitly
  validation-eligible.
- Lifecycle-preservation warnings for ST, suspension, delisting, or relisting
  are not missing data. Never remove or penalize a sample merely because the
  security later became untradable.
- Missing data must not silently become a favorable result.
- Hard-screen failures cannot be offset by favorable scores.
- Research Score prioritizes research only; it is not an investment decision.
- Screening owns Discovery, Hard Screening, Watchlist, and Research Queue only.
- `research.models.ResearchReport` is the single official research report
  contract.
- Investment Score must consume a completed ResearchReport and must be read
  together with `InvestmentAssessmentStatus`.
- A high Investment Score with low confidence remains a low-confidence
  opportunity; it is not an order or automatic approval.
- Priority, urgency, and confidence are separate Research Queue concepts.
- Every Research Report requires a thesis, counter thesis, and explicit
  falsifiable invalidation conditions.
- New report builds (including condition-free reports) and direct condition
  reviews must share one logical decision cutoff across module evaluations and
  separately supplied PolicyAssessment. Compare actual UTC instants, not local
  wall-clock labels/DST folds. Re-evaluate from visible inputs at the requested
  cutoff; never just retimestamp a cached result to pass. Input publication/
  availability may precede the cutoff and still needs independent freshness,
  source/content and PIT review. Do not rewrite historical report identities.
- Revalidate ResearchContext before starting a persisted run. Candidate identity,
  metric binding, queue/metadata cutoffs and fundamental version consistency
  must hold. Latest financial diagnostics use report period and visible version,
  never caller tuple order. Exposing unit/trust labels is not source approval or
  permission to turn unreviewed native observations into canonical facts.
- Research input visibility, revision identity/order and availability maxima must
  compare actual UTC instants, including repeated DST folds. Equal local labels
  can represent distinct versions; different timezone labels can represent one
  version. Shared daily selection must reject future or reversed chronology,
  keep intraday ambiguity visible and honor latest suspension without fallback.
  Retain original source timestamps/records, version changed research semantics
  and never claim that this scoped repair certifies all storage/domain consumers.
- Technical, Trend and Pattern research must share the checked daily-bar
  selector. Duplicate rows/revisions cannot inflate warm-up; conflicting
  versions, intraday-shaped series, adjusted inputs and future contexts fail
  closed. Observed dates are not verified exchange sessions or PIT approval.
- Current Technical/Trend/Pattern assessments must opt into
  `require_latest_active=True`. Validate the complete original series before
  blocking on the latest UTC-selected suspension; never score the preceding
  active close as current. Direct technical diagnostics must receive original
  context and bind the blocking observation, timestamps and missing reason.
  Historical selection remains available and records must not be deleted.
  A later active observation permits an unqualified calculation only; it cannot
  prove lifecycle resumption, source truth, trading status or execution permission.
- Research confidence must consider evidence quality, data completeness,
  module agreement, and point-in-time integrity; do not use simple averaging.
- Policy Research covers regulatory, industrial, fiscal, monetary, and
  geopolitical evidence and remains one variable among several.
- No single factor may determine an investment decision.
- Shared evidence-driven scores require exactly one numeric observation for
  every declared name. Missing/duplicate/boolean/text input cannot produce a
  partial score. Undeclared annotations stay visible but cannot raise score or
  confidence. Recheck context at the shared entry; structural admission and
  caller quality labels do not establish independent source qualification.
- Every decision must be deterministic where practical, explainable, versioned,
  and backtestable.
- Backtest, paper, and live modes should share decision logic.
- AI may assist discovery and research but never authorize a trade.
- Do not add live trading or credentials without explicit user approval.
- Paper Trading development is allowed only under `WP-LAUNCH-001` and
  `WP-PAPER-001`. It must remain deterministic, persistent, reconcilable, and
  incapable of reaching a live broker.
- Broker work is limited to read-only capability checks and provider-native
  simulation environments until `WP-BROKER-001` is ready. Sandbox access must
  not weaken `ExecutionDisabledGuard` or enable live orders.
- The 84-day provider-evidence horizon runs in parallel with controlled-launch
  engineering. It governs historical-evidence claims, not whether Paper
  Trading code may be developed.
- Live trading remains frozen while `execution.mode = "disabled"` and
  `allow_live_orders = false`. A future promotion requires a separate reviewed
  approval; Paper results cannot promote live execution automatically.
- Build the MVP before complex strategies or advanced AI.

## Development Style

SEC submissions/concept/filing-page/body producer clocks must be aware and have
zero actual offset before retained envelope/evidence construction. See
docs/sec-capture-clocks-2026-11-17.md. Keep accepted UTC bytes/IDs and non-UTC
request/read cutoffs unchanged; legacy bad captures stay blocked, not rewritten
or replaced with older good evidence. This is after download, not pre-fetch
audit. Other provider clock/ID findings are explicitly static follow-up risks,
not blanket fixes: publication clocks, observation IDs and request-derived
availability need separate contracts. Do not globally normalize historical IDs.

Yahoo global-equity snapshot capture-clock prevention is documented in
docs/yahoo-capture-clock-2026-11-17.md. Require an aware zero-offset producer
clock before artifact/evidence construction; do not normalize unsupported clocks
into new IDs or rewrite old records. Accepted UTC bytes/normalization stay exact;
non-UTC request/read cutoffs remain supported. Legacy mismatched captures stay
blocked without old-good fallback. A rejected new capture leaves no ingestion
row and does not freshen older evidence; future workers still need durable
pre-fetch attempts. This does not certify other producers or source/PIT quality,
enable unattended updates or define a new strategy. Default clock is already UTC.

Replay outcome v2 is documented in
docs/replay-endpoint-qualification-2026-11-17.md. Explicit suspended or nonboolean
endpoint flags, future visibility and reversed availability block numerical
outcomes in actual UTC. Preserve original endpoint bindings and incomplete
samples, never replace them with nearby/old active bars, zero returns or negative
research labels. False flags are not independently verified status or trading
clearance. New identities pin the outcome version; old replay rows stay unchanged
and require reconstruction before current validation. Existing outcome_missing
can mean a missing usable outcome, not missing raw records; inspect its precise
blockers. No source/PIT, strategy or execution admission follows from this repair.

Opt-in --technical-binding is documented in
docs/technical-display-binding-2026-11-17.md. Bound notes require the exact original
GlobalPriceInputs and explicit TechnicalParameters on both build and render;
rehashing copied labels/output is not recomputation. Preserve full original Bar
hash/count and UTC cutoff, including missing/failed/suspended states. Never equate
the diagnostic input hash with the differently defined full Bar hash. Omitted
flags preserve old bytes; legacy unbound direct rendering is not source-bound or
silently migrated. New binding grants no source/PIT/session/score/holding/trading
authority, does not replace optional timeframe checks and cannot define 271 rules.
Use the explicit binding flag for newly produced overseas daily diagnostic notes;
do not describe an old unbound note as having passed that check. Retained old
files remain unchanged and need a new explicitly bound rendering for this claim.

Tong's November 16 271 decision is recorded in
docs/proposals/technical-routing-and-271-v1.zh-CN.md. Missing original definitions
must remain pending, never synthesized from similar terms or existing indicators.
This is not approval of a new strategy/router, thresholds or trading capability.
Seven-plus-one is separate. Features may support a predeclared primary method,
but correlated signals cannot replace Turtle's four confirmations or count as
independent confidence votes. Keep continuation versus mean reversion distinct,
and Turtle pyramiding versus 271 no-intermediate-sizing management isolated.

November 16 independent-review repairs require credential privacy preflight
before any provider artifact publication, preserving non-deleting rollback.
Known-pattern/JSON screening is not opaque-binary secret certification. Lifecycle
availability, research period-date admission and nested replay research visibility
must use actual UTC cutoffs; equivalent timezone labels cannot change admission.
See docs/independent-review-hardening-2026-11-16.md for scope and open debt.
The existing engineering heartbeat now runs every three hours (00/03/06/09/12/
15/18/21 Malaysia time), superseding the earlier 02/03/04 schedule notes without
changing the task prompt, conversation or GitHub sync schedule.

The MSFT dimensional-context proposal is design/audit only, not permission to
accept excluded facts. Exact expanded names, full dimension sets, source bytes,
periods and reviewed wrapper scope must precede any future versioned support.
Do not collapse namespace URI to prefix/local name, equate empty dimensions
with consolidation, substitute MicrosoftCloud for Azure or count shared contexts/
nested ancestors as independent facts. Existing tag/period and free-text scope
contracts must not be silently reinterpreted. Proposal tests are not implemented
coverage; no numeric acceptance, schema registry or taxonomy truth is implied.

SEC body exclusion structure is an opt-in observation, not acceptance. See the
November 16 source/proposal addenda. explain_exclusions must be an exact bool;
the CLI flag is read-only and rejects capture before I/O. Preserve the default
numeric/source contracts and every original fact/reason/value. Segment/scenario,
entity/period counts and unique references do not certify dimensions, content,
consolidation or valid/malformed accounting. Cache shared context structure but
retain each fact's independent ancestor/target barrier. Counts overlap and use
only the explicitly selected tags, not full-filing coverage. Malformed/oversized
documents stay unavailable; retained parent/raw/future/latest-failure gates cannot
be bypassed. Do not wire this audit to scores, business thesis or official reports
as source admission. New hashes identify diagnostics, never source authentication.

Long-horizon observations are documented in
docs/long-horizon-observations-2026-11-15.zh-CN.md. Optional --long-horizon is
read-only and adds ended calendar month/year SMA/MACD/KDJ using existing formulas,
not verified session candles, new scores, horizon estimates or holding decisions.
Keep legacy calendar v1/default JSON/Markdown unchanged; optional years and the
extended note have prospective versions. Exclude open periods, block known whole
period gaps/suspensions (including missing months within years) without stitching,
and preserve all missing/sample states. First-year missing leading months also
block yearly indicators; within-month coverage remains unknown. Never count daily
rows as monthly/yearly warmup, or correlated timeframes as independent votes.
Receipt context and full source Bar hashes/counts must match the base snapshot.
The helper supports four markets; the existing overseas CLI still supports US/HK/MY.
Optional --multi-timeframe adds ended weekly observations with explicit 13/26/52
SMA periods and the same MACD/KDJ, plus source-date alignment. weekly_sma_periods
None preserves v1 month/year receipts exactly; enabled v2/new v4 note only.
Same UTC cutoff is not same source/period close or independent voting. Preserve
the conservative next-Monday boundary until exchange/session evidence is qualified;
do not call Friday-completed observations verified weekly candles. Missing latest
periods retain null source/age, never older-good fallback. Validate alignment dates,
actual UTC age arithmetic, schema/version and false comparison/close authority.
No cross-timeframe score, monthly/yearly Turtle/Granville/setup policy, holding
decision, source qualification or trading approval is implied by this extension.
Optional annual calendar coverage is documented in the existing calendar coverage
record. --calendar-coverage plus a long/multi-timeframe mode reads the same price
database snapshot from the first year start; no automatic calendar-source join,
copying or weekday inference. New v2 coverage/v5 note bind source Bar hash/count,
cutoff and parent calendar receipt; v1/default output remains unchanged. Unknown
TradingSession trust/precision remain UNKNOWN. Distinguish absent declarations,
missing declared-open observations and adverse/conflicting dates; 100 percent is
conditional agreement only. Empty scoped calendars never prove no trading days
or provider-wide absence. No calendar/source/PIT/score/holding authority is granted.

Optional Nasdaq source co-review is documented in the existing Nasdaq source
record. All explicit source DB/root/year/positive-age flags and --as-of are
required; capture/non-US scope is rejected before database/raw writes. Reuse
retained readers and the same-store price snapshot where selected. Separate
stores share a cutoff only, never atomicity. Keep the entire source receipt,
native early-close times, future/stale/failed observations and price hash in the
new application receipt/v6 note. Recheck UTC age arithmetic and false authorities.
Never convert this holiday table to TradingSession, fill unknown dates, upgrade
LOW/retrieval_time or identify instrument venue from caller selection. It cannot
repair the earlier coverage receipt or authorize holding/add/exit rules. Caller
source-age examples are not production TTLs.

Nasdaq note v7 adds comparison-context labels, not a new source/review contract.
Never render a raw conflict=False as an evaluated favorable result for future,
unavailable, out-of-span or early-close/intraday-unknown observations. Validate
exact booleans and mutual observation/span/conflict consistency. Distinguish a
candidate date conflict from an unverified absence; neither qualifies coverage.
Keep JSON/source hashes and legacy v6 stored notes unchanged; only new optional
Nasdaq renderings use NASDAQ_PRICE_NOTE_CONTEXT_VERSION. No-source defaults stay
exact. Missing observations must never acquire favorable meaning through display.

research.thesis_bindings adds typed declarations for existing thesis conditions,
not a new report or evaluator. Complete declarations remain DECLARED_ONLY and
NOT_EVALUATED; caller trust/hash labels do not qualify sources. Exact identity,
definition, periods, revisions and UTC visibility are diagnosed without values,
threshold comparison, latest-good fallback or inferred fiscal continuity. The
helper now has opt-in DefaultResearchReportBuilder(thesis_binding_plan=plan)
integration through existing assessment features and SQLite reconstruction.
Bind queue/instrument/exact UTC cutoff and every unchanged condition definition;
reject future references before publishing. Every such report is INCOMPLETE and
cannot obtain InvestmentScore. No plan preserves legacy bytes/version; enabled
reports use RESEARCH_THESIS_REPORT_VERSION. No new Request/Report fields, CLI,
schema or authenticated source qualification exist. Preserve old model
serialization and hashes. See the November 15 implementation addenda in
docs/proposals/msft-holding-thesis-validation-v1.zh-CN.md before integrating it.

MSFT holding-thesis design is docs/proposals/msft-holding-thesis-validation-v1.zh-CN.md.
It is draft, not a registered strategy or approved thresholds/windows. Existing
ThesisInvalidationCondition stores descriptions and research.conditions explicitly
leaves thesis windows NOT_EVALUATED. ThesisValidationModule aggregates supplied
outcome labels; it does not derive source-qualified business outcomes. Never
claim those interfaces constitute an implemented hold/exit/add evaluator. Reuse
the sole ResearchReport, distinguish decision/outcome evidence and require exact
typed period/definition/version/source bindings before future rule evaluation.
Unknown labels, unqualified values, positive price returns and owner manual buys
cannot establish thesis success, holding horizons or permission to add/sell.

Explicit --sec-artifact-root composes separately retained US price/SEC stores;
see docs/sec-source-root-composition-2026-11-10.zh-CN.md. Require complete US
read-only SEC options, reject conflicting roots for one database, use the chosen
SEC root for body/issuer/period readers and never copy/rebind/fallback. Omitted
options preserve legacy output. Shared cutoff is not atomic cross-store reading
or provider/accounting admission; selected roots are not authenticated config.
Build optional holding_review before computing any SEC/HK/MY filing combined
hash. New holding combinations use EQUITY_HOLDING_DISPLAY_VERSION; preserve old
files and independent holding receipts. Full JSON carries SEC/root details that
the existing Markdown does not render. Native annual missing status cannot be
silently repaired by SEC values or converted into a score or trading decision.

Owner holding review is opt-in --holding-context in the existing global diagnostic;
see docs/holding-review-2026-11-09.zh-CN.md. It is a local owner annotation, never
an authenticated broker ledger, Portfolio input, official report or decision.
Validate bounded decimal amounts, identity/currency and actual UTC observation/
declared recording/cutoff chronology. Age limits are explicit; stale, suspended,
missing or pre-observation prices cannot yield a position comparison. The owner
loss threshold only requests review, never guarantees loss bounds or sells.
Preserve NOT_ESTIMATED horizons and NOT_EVALUATED thesis windows; old setup
references cannot become position stops. Keep private annotations ignored and
all source/PIT/scoring/validation/management/execution authority false. Do not
equate this foundation with completed fundamental or exit/add strategy validation.

For a compact Chinese cross-device handoff of Tong's philosophy, seven technical
research groups, gaps and recovery steps, read docs/PROJECT_HANDOFF.zh-CN.md.
It records local-versus-published distinctions, not release or trading approval.

The readable equity note now uses equity-diagnostic-note-v2-utc-context. Compare
every price/fundamental/review/optional-trend cutoff as an aware actual UTC instant,
never native datetime fold equality or string labels. Reject malformed/missing
cutoffs; retain original receipts and v1 files. New Markdown hashes may change,
not JSON, technical formulas or source/PIT/scoring authority. See the existing
single-equity usability record for the synthetic defect and real offline check.

Optional --trend-observations exposes existing Donchian/volume/ATR geometry; see
docs/turtle-price-observations-2026-11-08.md. Full Trend evaluate and the view share
private arithmetic; preserve complete-assessment golden hashes/default output.
Keep strict breakout separate from threshold observation, None external evidence,
false four-confirmation completeness and no score/trade authority. Volume above
average is not verified buying pressure. The view is read-only, original-series
checked and suspension-blocking; never use a channel/ATR as a suggested order.

The existing overseas diagnostic CLI now has opt-in --format markdown; see
docs/single-equity-usability-2026-11-08.zh-CN.md. It renders existing unscored
technical/native financial observations, not a second ResearchReport or an
advice/scoring engine. Keep default JSON and exit-2 semantics, read-only rendering
and explicit capture separation. Preserve LOW/unassessed/source/sector gaps;
inactive setup references cannot appear as current position stops. Optional SEC,
manual review and calendar extensions still require the full JSON. New local
NVDA evidence proves this limited workflow runs, not data/strategy admission,
all-market completeness, backup, automatic refresh or a verified buying signal.

Research confidence and shared assessment maxima now compare actual UTC instants;
see docs/research-confidence-utc-2026-11-08.md. Require aware helper cutoffs, do
not count a later DST fold as visible, and retain the selected input timestamp.
New confidence methods bind RESEARCH_CONFIDENCE_VERSION; preserve explicit stored
legacy methods and never upgrade old reports/hashes. The method label is not
source, PIT, strategy or execution approval. This scoped repair does not certify
all timestamp consumers or replace genuine research/validation evidence.

Nasdaq source-age checks are opt-in read-side diagnostics; see
docs/nasdaq-calendar-freshness-2026-11-08.md. Omitted limits preserve v1 hashes
and UNASSESSED, not freshness approval. Compare exact UTC elapsed time since the
verified original capture, never completion/review/event time. Preserve stale
rows as observed_declarations but withhold current declarations; unsupported,
missing and latest bad inputs cannot be fresh or fall back. Caller TTL is not
trust/session/PIT admission. No auto-refresh or default TTL is approved. Existing
non-UTC producer-clock identities remain blocked pending separate compatibility
design; normal captures use UTC. New Nasdaq captures now explicitly reject
nonzero UTC-offset producer clocks before evidence/artifact/batch persistence;
equivalent zero-offset labels remain valid. This is preventative input rejection,
not clock normalization, legacy repair or admission of unsupported records.
Keep source normalization and old records intact.

The US regular-session/calendar proposal is design only; see
docs/proposals/us-regular-session-calendar-v1.md. A November 7 primary-source
audit found an announced December 6 expanded-hours transition; do not treat
announcement, consolidated rule text and confirmed operation as interchangeable.
Keep civil observation date separate from an independently supported exchange
trade date/session scope. Current Yahoo/native and calendar receipts do not
prove that mapping. No runtime rule, source capture, schema or overnight support
is admitted by the proposal; preserve old hashes and disabled defaults. Qualified
regular-only research may continue without admitting mixed/overnight bars.

Nasdaq holiday evidence uses the existing provider-neutral retention path; see
docs/nasdaq-calendar-source-2026-11-07.md. Fixed public URL only, bounded HTTPS,
no redirects/credentials, explicit year and one strict schedule table. Keep raw
body/envelope hashes separate and retain unsupported/latest failure/tie/tamper
states without older favorable fallback. Early closes retain local time; unlisted
dates stay unknown. Current retrieval never proves old publication or actual
sessions. Keep LOW/retrieval-time and false authorities, no canonical calendar
insertion or lossy TradingSession mapping. The manual CLI captures only to a new
exclusively reserved diagnostic file and reads existing files offline. It is not
refresh-worker/resource or automated monitor admission; no auto-append/migration.

Calendar declaration coverage uses existing TradingSession observations, never
an implicit exchange schedule; see docs/calendar-declaration-coverage-2026-11-06.md.
Unknown dates (including weekends) stay unknown; unended periods, conflicting
closed-date observations and partial calendars withhold percentages. Suspension
observations are present data, not silently missing. A conditional 100 percent
or DATES_MATCH_UNVERIFIED is not verified session coverage, trust or PIT/scoring
admission. Calendar trust/precision remain UNKNOWN because the legacy contract
lacks qualified metadata. Keep actual-UTC revision checks and source separation.
The opt-in global coverage read shares the price SQL snapshot, never writes or
captures. SQLite calendar flags must be bool before writing and integer 0/1 on
read; malformed legacy values fail closed, never coerce or silently rewrite them.

Calendar week/month observations are separate unscored diagnostics; see
`docs/calendar-period-diagnostics-2026-11-06.md`. Keep Technical's 5/21-interval
returns and configured observation-range scores explicitly labeled as proxies,
not calendar/session-complete research. Do not replace their arithmetic silently.
Aggregate original visible daily versions in market-local time, retain missing
and suspended periods, withhold unended numeric candles and honor latest
suspension without fallback. Unknown coverage/turnover stays unknown; calendar
ended is not verified exchange completeness or source/PIT/scoring admission.
The opt-in global display stays read-only; no auto-capture or old-record upgrade.

On November 5 Tong prioritized a US read-only increment for November 30, without
removing the four-market scope or approving scoring/trading. Track
`docs/us-readonly-delivery-2026-11-05.zh-CN.md`. Optional SEC co-display in the
existing global technical CLI requires an explicit database/CIK/accession,
US read-only mode and one cutoff. Shared DB means one read snapshot; separate
DBs do not. Caller pairing and same-origin numeric agreement cannot verify
issuer identity, accounting, freshness, independent consistency or scores.
Keep missing/failed/conflicting inputs visible and legacy no-SEC output unchanged.

Optional --sec-identity now reads exact retained SEC issuer declarations via
read_sec_issuer_claims; see docs/us-issuer-declarations-2026-11-06.md. Match is
TICKER_DECLARED_UNVERIFIED only, not share-class/listing/historical identity.
Preserve whole-list errors and duplicates, no case/punctuation/name joins or
positional exchange-array inference. Keep one SQL snapshot, actual capture
availability and latest failure/no-fallback semantics; recheck original bytes.
Previous SEC/no-SEC outputs and normalization versions remain unchanged without
the opt-in. No declaration receipt may authorize financial scoring or trading.

SEC exact-period inputs use immutable SECPeriodSelection and optional --sec-period;
see docs/us-sec-period-inputs-2026-11-06.md. Require explicit native tag/start/end
or instant date, preserve all matching occurrences and unresolved contexts, and
block conflicts, unsupported matches and targets after cutoff/report-end labels.
Do not infer annual/quarter/YTD/TTM from FY/form/12M or 365-day rules, aggregate
duplicates, normalize accounting aliases or apply ordinary-company health to
financial firms. Calendar-day counts and OBSERVED_SUBSET_UNQUALIFIED are not
fiscal/scope/source completeness or scoring approval. Old paths are unchanged
without the opt-in; no new official research report, schema or trade authority.

SECPeriodResearchInput now copies the period receipt into the existing official
ResearchContext/Financial path; see docs/us-sec-research-binding-2026-11-06.md.
Require US Equity, caller symbol/sector and exact UTC cutoff, no parallel
FinancialInputSnapshot, and consistent sectors with other financial receipts.
Keep the 2 MiB bound, false authorities, source/parent/capture/row checks and
pre-write revalidation. Copied hashes are not fresh source checks or verified
CIK/share-class identity. Store full receipts in the existing report features;
missing/failure/conflict states remain unscored and their read cutoff contributes
to assessment availability. Do not manufacture a real queue from captured data,
merge Yahoo/SEC fields, infer fiscal policy or requalify old stored reports.

The first research-decision release is tracked in
`docs/decision-delivery-plan-2026-10-27.zh-CN.md`. R1-R6 are acceptance groups,
not new approved work packages. On October 27 Tong confirmed read-only delivery
covering China A, US, Hong Kong and Malaysia, including financial and nonfinancial
equities, based on the previously requested technical methods. Do not narrow this
to the earlier China-A nonfinancial pilot proposal. The coverage matrix is
`docs/four-market-readonly-release-2026-10-27.zh-CN.md`. Scope confirmation is not
data/strategy admission or approval of draft rubrics, weights or thresholds.
The former 8-15-round narrow-pilot estimate is superseded, not a four-market ETA.
Preserve A-share-only pattern boundaries; financial firms need bank, securities,
insurance and other applicable sector definitions, not an ordinary-company
template. Missing coverage must remain visible, not be silently excluded or
reported as a validated decision. Keep source/strategy/deployment evidence
separate from prompt counts and correct stale roadmap claims against governance.

Global equity snapshot diagnostics use `global_equity_price_snapshot`, separate
from legacy Yahoo global_daily_bars. Retained decoded envelopes, evidence and
registry/completed-batch reconstruction bind transient bars; they do not certify
native OHLC adjustment history, issuer identity, calendars or price truth.
NONE on these transient bars means no Tong transformation, not unadjusted-source
approval. Use only the exploratory diagnostic path, never canonical/PIT/scored
research/replay admission. Preserve latest failure/tie/current-exchange-date
blocks without favorable fallback. Public transport success and deterministic
hashes cannot upgrade LOW/retrieval-time or count as an independent provider.

Native annual financial observations use `global_native_fundamental_snapshot`,
never canonical FundamentalFact aliases. Preserve provider names, reporting versus
quote currencies, fiscal labels and unknown release/revision/period-start/scope.
No fmt scaling, YTD/TTM/parent-profit/debt inference, FX or PE/PB/ROE/ROIC follows.
Duplicate/unknown/latest bad periods block without favorable fallback. Caller
sector labels are context, not FinancialInputSnapshot profile extensions or
scoring admission. Global readers share retained-snapshot consistency checks and
one cutoff when combined; byte agreement cannot promote source/PIT/official research.

`read_native_financial_research_input` copies those reader receipts into the
immutable NativeFinancialResearchInput contract for the existing ResearchContext.
Official Financial features may retain receipt/review JSON, not score them.
Do not fabricate a queue for exploratory captures, accept another instrument/
cutoff/non-equity, or supply a parallel FinancialInputSnapshot. Revalidate before
run writes. Missing/failed/rejected states survive report persistence; report
reconstruction is not PIT replay eligibility. All Financial outputs remain
insufficient/unscored until a separately admitted source-bound sector policy.

Native financial review is exploratory: compare only the two latest unique,
usable, matching annual labels/currency/raw units, never an older favorable row.
Withhold percentage on a nonpositive baseline. Matching labels and native changes
are not verified accounting comparability or business growth. Sector-specific
Survival/Cycle/Valuation/Growth questions remain UNASSESSED/NOT_ADMITTED, not
approved rubrics. Negative nonfinancial observations request business context;
do not apply ordinary-company cash-flow failure flags to banks/other financials.
Receipt checksums are not authentication; no source/score/replay/validation/live
authority can emerge from this review, recomputed hashes or positive technicals.

SEC issuer metadata uses `sec_issuer_filings_snapshot` and explicit ten-digit CIK,
not inferred stock identity. Use environment-only declared access identity, never
persist contact headers or follow redirects. Acceptance, official filing date,
form-specific report date and actual capture availability are distinct; none
establish exact first publication. Preserve prospective event dates without
calling known future plans a data leak. V1 normalization remains reconstructible;
v2 form-aware semantics never rewrite v1 receipts. Older pages are references,
not complete history; `/A` is not numeric revision/restatement proof. Keep
LOW/RETRIEVAL_TIME and all score/replay authority false. No ticker join or
financial fact/report may be invented from this diagnostic; raw co-retention and
independent source/sector qualification remain required.

`sec_company_concept_snapshot` binds CIK/taxonomy/native tag, never canonical
aliases. Keep all units, exact start/end, accessions and values; FY/frame labels
are not annual duration or comparability. Exact integer source values only in
this slice; fractional rows remain visible/unusable, never rounded. Duplicate
contexts cannot be ranked or averaged. Join catalog references at one SQLite
snapshot/cutoff by unique usable accession/form/filed, retaining comparative,
missing/conflicting/failed states. A metadata match is not independent numeric
corroboration, restatement mapping, equity identity or scoring/replay admission.
Do not backdate availability, fabricate old references, or drop missing rows.

SEC older pages use explicit retained-parent references and a separate dataset.
Pin parent evidence/hash/availability/count/interval; never guess page filenames,
follow arbitrary links, rebind changed parents or use pages before capture.
V2 uses interval containment plus count agreement; v1 extrema semantics remain
reconstructible. Out-of-range/malformed/failed/tied/corrupt pages remain visible
and unusable, with interval gaps blocking favorable reference fallback. Expanded
concept references require an explicit boolean/CLI opt-in; default recent-only
hashes must remain exact. Metadata references, including 649/649 in the US sample,
are not independent numeric truth, full-history/PIT coverage or scoring admission.

`sec_primary_filing_body_snapshot` requires a verified parent catalog and explicit
CIK/accession/periodic filename; never guess a URL or rebind a changed parent.
Retain original bytes inside the envelope, with distinct body/envelope hashes.
The bounded UTF-8 single-document Inline XBRL review is only a subset, not full
XBRL/schema or accounting validation. Namespace URIs, context/entity, exact period,
USD unit, scale/sign/precision and all supported occurrences matter. Keep excluded
facts and their reasons visible; never guess nil/dash zero or convert currencies.
Same-accession numeric agreement is same-origin, not independent calibration or
source/scoring/replay/validation admission. Reject DTD/entities, external loading,
unknown formats, future/tied/failed/tampered/changed-parent inputs without favorable
fallback. Before base64 retention reject credential assignments/reflected contact
and unsupported encodings. Do not turn exploratory body observations into facts.

Global primary PDF snapshots use explicit HKEX SEHK/Maybank annual-report URLs
only. Maybank-specific transport is not a Bursa/market-wide integration. Retain
original bytes and separate envelope/body hashes; magic/official host is not
PDF/accounting/source qualification. Caller issuer/subject/period and landing
references stay unverified, LOW/RETRIEVAL_TIME. Read an explicit document URL at
one snapshot/cutoff; latest failed/tied/tampered/future-completion captures cannot
fall back favorably. No production text/table extraction or scoring/replay/live
authority. Future overseas reviews need distinct counter/reporting currencies,
group versus bank, exact unit/column/period and version semantics; never relax
the China-only CNY/calendar-YTD contract or auto-join similarly named subsidiaries.

Overseas monetary reviews are single manual transcriptions, not canonical facts
or another independent provider. Pin exact current source evidence/envelope/PDF/
availability; preserve native label, Group/Bank scope, current/comparative periods,
currency/unit and separate physical/printed page labels. Unknown/conflicting cells
stay null, never zero. Decimal scaling does not certify PDF text, accounting or
summary precision. Claimed reviewed_at cannot backdate actual recording time;
--as-of is preview-only. Recheck source pins on every read after possible source/
write races; latest invalid input cannot fall back favorably. No canonical aliases,
financial scoring, independent review, issuer identity or replay/trading authority.

The optional technical/reviewed-filing co-display is exploratory only. Pair an
explicit HK/MY document URL and database at the same cutoff; preserve independent
price/native/manual missing and failed states. Same-file snapshots may be shared;
separate files do not provide an atomic cross-database snapshot. Combined hashes
bind inputs/calculations, not truth. Never infer accounting/native-field mapping,
provider consistency, FX, valuation or scores from co-display or currency-label
agreement. Default no-review CLI output must remain unchanged. Provider inventory
must distinguish code, retained evidence and current untested account permission;
no new token is necessary for an offline retained-input step.

Explicit HK/MY native/manual candidates are questions, not approved mappings.
Retain all requested profit/revenue alternatives, exact end-label matches and
scope/period/unit/precision/revision blockers; never choose by nearest amount,
infer an alias or tolerance, or compute a consistency vote from candidate pairs.
Use exact retained readers and the common cutoff; missing/latest-bad inputs stay
blocked. Equal numbers cannot admit financial scoring, source trust or validation.

Explicit manual income sums are signed transcription checks, not source or
accounting validation. Require identical statement/scope/flow-period/column/
currency/original-unit/restatement labels; retain unresolved cells and exact nonzero
residuals. Never infer an expense sign, zero, coefficient, tolerance or Yahoo alias.
New review captures preserve old editions and cannot auto-merge missing keys.
Within-document summary/statement differences stay unresolved, not silently fixed.

ReviewedDocumentResearchInput carries exact retained HK/MY manual receipts into
the existing ResearchContext/Financial assessment, never canonical aliases or a
new report model. Revalidate identity, cutoff, strict rows and false authority
before evaluation/run writes; preserve missing/failed states and unscored output.
Native/manual requested sectors must agree when combined, without approving the
classification. Read new inputs for a new cutoff: copied receipts are not live
source rechecks, independent truth or permission to retimestamp an old result.

Bank document input plans are draft source-specific questions, not admitted
financial policy. Pin the exact review/envelope/PDF and require identical native
annotations; never infer numeric targets, aliases, weights or health thresholds.
Separate missing review rows, unsupported ratio contracts and external dependencies.
Plans cannot precede their pinned review or follow the cutoff; local timestamps
are not authenticated publication. Keep period/capture age distinct and freshness
unassessed. Changed source editions require explicit new pins, never auto-rebinding.

Same-filing manual annual changes require explicit current/comparative rows,
matching native labels/scope/currency/original units and full aligned annual
windows. Preserve unsupported windows and missing/conflicting inputs. Nonpositive
prior amounts withhold percentages. Changes are descriptive, not verified growth,
original historical vintages, reconciled revisions or scores. New manual editions
retain old-cutoff receipts and require new plan pins/availability, never backdating.

Original HK/MY percentages use GlobalRatioRow/GlobalRatioReview and an independent
dataset, never monetary V1 or China CNY/YTD models. Preserve printed percent units,
negative/above-100 values, annual/instant/unknown periods and unknown definitions,
denominators/regulatory scope. Net impaired loans cannot alias gross NPL; financial
Group is not verified regulatory consolidation. Use exact retained ratio readers,
actual recording, latest-failure/tie/no-fallback and current-parent pins. Raw ratio
receipts do not enter monetary research wrappers, bank plan credit or scores.
ReviewedRatioResearchInput is the separate immutable official-context slot: keep
exact hash/cutoff/row/false-authority validation before evaluation/run writes,
equity/canonical-receipt boundaries and consistent requested sectors. Copied JSON
is not a live source recheck; reread for new cutoffs. Explicit original-row questions
retain missing/unresolved/definition-required states without formula, thresholds,
regulatory approval, source/sector admission or scores. All ratio receipts persist
as unqualified Financial features; no separate report model or favorable fallback.
Assessment availability must include the exact read cutoff of every bound native,
monetary and ratio receipt, including missing/failed states; older raw facts cannot
backdate these features. Regenerate/revalidate older reports before historical
reuse, never silently rewrite stored report timestamps.

Bank capital/equity source editions preserve all old income rows and use explicit
new evidence/plan pins. Attributable-equity heading subtotals exclude separate NCI;
regulatory CET1/Total Capital/RWA cannot alias financial equity/assets. Keep Note
59 consolidation exclusions and Note 12 net-loan/investment-account/allowance basis
as unqualified original annotations. Nonempty notes do not verify definitions or
close ratio-policy gaps. A liquidity-management narrative is not a numeric LCR;
missing reviewed rows do not prove issuer-wide nondisclosure. Preserve old-cutoff
hashes; do not repeat an interrupted ingestion whose completed records already exist.

Cross-receipt percentage arithmetic requires explicit bounded identities and plan
pins to both review IDs/envelopes/PDF, with plan availability after recordings and
before cutoff. Revalidate both copied inputs, same actual UTC cutoff/original
source, instant/balance basis, scope/date/column role/restatement and original
currency/units. Keep missing/unresolved/nonpositive/precision/context failures and
stale source pins blocked. Use exact Fraction quotient/residual and declared
half-even precision, never tolerance or favorable alternatives. Arithmetic and
rounding agreement cannot verify definitions, regulatory Group equivalence, source,
sector policy, bank-plan credit, Financial score or trading. Annual ROE averaging
is unsupported; persist diagnostics in the existing Financial/report path only.

Separate integrated-report liquidity receipts must not overwrite Financial
Statements reviews or share parent pins merely because issuer/year match. A
rolling-average LCR note is not an instant year-end ratio: retain unknown basis
when the existing enum cannot express it, with the original note and restatement
label. Do not infer start dates, average balances or denominator components.
Same-origin KPI repetition is not independent calibration. Numeric availability
does not close source-specific bank-policy questions or permit scoring/replay.
Keep explicit document selection. ResearchContext may add an immutable tuple of
at most three supplemental ratio receipts to a required primary receipt. Require
unique document URLs, same equity/cutoff/requested sector and full receipt/false-
authority validation before evaluation/run writes. Sort supplemental documents by
URL when retaining full receipts in existing Financial/report features; preserve
missing/failed states and all availability cutoffs. Primary row questions and
same-PDF arithmetic plans never search supplements or overwrite missing values.
Co-presence is not metric aggregation, period/perimeter equivalence, independent
calibration, sector admission or scoring/replay authority. No second report model.

The existing global technical CLI may explicitly select one primary ratio URL and
up to three distinct supplemental URLs with reviewed-filing/fundamentals/sector
context. Co-display remains exploratory and creates no official report/queue.
Keep the primary role fixed and sort supplements canonically; unselected legacy
output/hash/version must remain unchanged. All selected monetary/ratio documents
in one review database share one read snapshot. Separate price/review files still
share only a cutoff, not cross-database atomicity. Never turn receipt count,
matching values, unassessed freshness or a healthy sibling into source approval,
fallback, numeric consistency, aggregation or a validated decision.

Original-document freshness uses report-period age in the market calendar,
original PDF source-capture age and actual manual-review recording age as separate
quantities. Re-review cannot rejuvenate source capture or report period. Shared
financial settings supply report/source limits; zero means UNASSESSED, equality
is within a declared limit, and absent/failed receipts retain null ages. Do not
equate WITHIN_CONFIGURED_LIMITS with latest issuer filings, publication knowledge,
source truth, admitted policy or scoring. CLI output is opt-in; persist official
Financial diagnostics without changing original receipt freshness labels or old
report identities. Native/canonical/price age contracts are not certified by this
HK/MY manual-receipt slice. Default config changes need a new configuration identity.

The automated refresh proposal in docs/proposals/automated-data-refresh-v1.zh-CN.md
has offline request planning and separate persistent audit/ingestion contracts,
but no running capture worker. The planner is data.refresh_plan / plan_data_refresh.py;
see docs/offline-data-refresh-plan-2026-11-03.md and the v2 AKShare follow-up in
docs/akshare-offline-refresh-bridge-2026-11-03.md. The AKShare static bridge converts
only declared China-A equities into existing DailyBarRequest; it never fetches.
Do not confuse this request with the post-capture evidence adapter's request.
Preserve actual legacy endpoint provenance, unknown BSE availability and unsupported
index/fund/fundamental scope. A route/NONE request is not listing or adjustment proof.
Static request validation is not
provider capability, successful capture, freshness, a due calculation or calendar
approval. Preserve unsupported scopes, NOT_TESTED permissions, UNKNOWN observations
and false authority flags. Capture workers and scheduler activation remain unbuilt.
The plan timestamp/hash is never actual availability, a job ID or checkpoint;
Git commit/dirty flag is not a content-pinned reviewed working tree. Strict bounded
explicit scopes and safe CLI errors must remain offline and database-free.
There is no installed scheduling or unattended collection. Health monitors
do not refresh a research universe. Provider-neutral ingestion persists a batch
after fetch/validation, not a durable pre-fetch job attempt; a committed failure
snapshot is not successful refresh. Future scheduling needs explicit scope,
separate durable attempt/lease/checkpoint recovery, safe error codes and real
acceptance tests before activation. Never repurpose write_canonical or strict
provider parameters as a generic scheduler hook. No raw response means unknown
response/hash, not a fabricated digest. Data refresh cannot admit trust, PIT,
financial policy, execution or new trading capabilities.

The data.refresh_attempts value contract is now backed by SQLiteRefreshRepository;
see docs/refresh-ledger-persistence-2026-11-03.md. Claims precede capture; persistent
updates re-read current generation/nonce/version inside store transactions.
Optional refresh_lease binds the exact batch inside the existing ingestion write
transaction. Unleased calls retain their old pre-fetch audit gap. Missing/old
databases are never initialized by the repository. Schema is 0.8.3 / 0011;
retained user databases stay unchanged pending isolated restore/migration review.
Only observed transient fetch failures get finite retries. Expiry, retention
failure and retained batches require reconciliation; no complete verifier,
checkpoint, worker or source/strategy admission exists. Decoded payload hashes
are not wire bytes. Clock provenance and cross-store recovery still need operational
acceptance. No sidecar schemas, old
checksum mutation, write_canonical scheduler hooks or silent user-DB upgrades.

November 4 shared-byte hardening is documented in
docs/artifact-rollback-retention-2026-11-04.md. FileSystemArtifactStore.discard
retains published bytes on rollback; created is not exclusive ownership. Never
restore created-only deletion, delete based on one database's registry, or
equate unregistered retained bytes with success. DB rollback and failed statuses
still apply. Registered-artifact audits do not inventory orphan files. No
automatic GC/TTL is approved; future deletion needs global reference coverage,
active-writer isolation and retention/authorization review. Bounded disk capacity,
exact job/batch/original reconciliation, encryption and recovery must precede
unattended collection; this protection does not activate capture or trading.

Read-only exact refresh inspection is data.refresh_reconciliation and
scripts/inspect_refresh_reconciliation.py; see docs/refresh-reconciliation-2026-11-04.md.
Use the exact attempt ingestion_batch_id, never inferred symbol/date/hash matches.
All SQL checks share a read snapshot, including repository metadata validation;
selected original files remain non-atomic with SQL. first_batch_id is registry
history, not exclusive ownership or this capture's only reference. Failed snapshot
bytes remain failed. LINKED_BYTES_MATCH grants no checkpoint, source/PIT/research
admission or trading readiness. No repair, retry reset, GC or capture is enabled.
Do not weaken LOW/retrieval-time limits, leak stored payloads/paths/errors, or
interpret the inspection cutoff as historical database reconstruction.

Read-only artifact capacity preflight is data.artifact_capacity and
scripts/inspect_artifact_capacity.py; see docs/artifact-capacity-preflight-2026-11-04.md.
Require explicit byte budgets; count all regular names including unregistered,
temporary and hard-linked files. Missing, unstable, cross-volume, unsafe or
bounded-out scans cannot produce a total or favorable clearance. Preserve partial
observations without treating them as current usage. WITHIN_DECLARED_LIMITS is
not a reservation, enforced quota, source/PIT/deployment approval or capture
authority. Existing ingestion/store writers are NOT wired to this preflight.
Review serialized one-shot admission, actual size bounds, concurrent reservations,
staging/DB space and recovery before integration. Never auto-delete to free space.

The one-shot design is docs/proposals/one-shot-refresh-admission-v1.md (November 5).
The concurrent preflight counterexample is not a failing capacity implementation:
independent observations cannot reserve joint headroom. Resource ownership must
cover complete under-lock capacity checks, claim, bounded capture, retention and
receipt inspection; existing writers remain outside that proposed contract.
Do not equate lease expiry with OS-lock release or child termination, use
close-on-exec as a fork safeguard, or unlink a BUSY lock. Full fetch admission,
multi-resource/staging budgets and full supervisor crash acceptance remain pending.
Design completion is not worker activation, schema change or milestone acceptance.

The fetch-side read guard is now SQLiteRefreshRepository.validate_fetch_lease;
see docs/refresh-fetch-lease-guard-2026-11-05.md. It opens a fresh read-only snapshot,
checks current metadata/runtime-plan/committed FETCHING identity and UTC lease
bounds, and rejects the caller store's managed read or write context. The new
has_active_connection property is context-local, not a global writer detector
or a tracker of manually borrowed connections/BEGIN statements.
Successful checks return None, not capture approval or a continuing ownership
token. Existing entry points are NOT wired to this guard. Keep retention's
transaction-compatible phase guard unchanged. Resource ownership, actual transport
bounds, child termination and subsequent handoff fencing remain necessary.

The first local ownership primitive is data.resource_ownership; see
docs/prepared-resource-ownership-2026-11-05.md. It uses an already prepared,
private zero-length coordinator inode and immutable reviewed pins. Never silently
recreate, re-pin, chmod or unlink a missing/BUSY/substituted lock. A held token is
one cooperative inode, not all DB/artifact/cache resources, capacity or capture
permission. No existing entry point is integrated. Namespace failure latches the
token invalid; uncertain close quarantines the process until retirement/restart.
Fork callbacks close only this module's copied descriptors without LOCK_UN;
they do not terminate children or make the entire supervisor crash-safe. Resource
mapping/order/group acquisition and broader shutdown tests remain required.

The November 4 GitHub review blocked old candidate 8794b57 after an exact-source
rollback-deletion reproduction. The working repair's pass does not qualify the
candidate or mean it was pushed. Consult PROJECT_STATUS for the dated remote
observation; recheck live ancestry/auth before any sync. Preserve mixed changes
and require exact repaired-candidate checks plus independent review.

Tong authorized periodic reviewed GitHub sync on November 3. The app heartbeat
tong-quant-github runs daily 05:00 Malaysia time; engineering 02/03/04 unchanged.
Read docs/github-reviewed-sync-2026-11-03.md. Only complete reviewed candidates
that pass exact isolated-tree checks may commit and non-force push to the verified
TONGResearch/tong-quant-framework corresponding branch. Never git add ., overwrite
unrelated changes, force/rebase/diverge automatically or publish local data/secrets.
Unreviewed mixed work remains blocked, and Git is not encrypted data/artifact backup.

Tong's confirmed operating model is documented in
docs/ai-assisted-and-independent-operation.zh-CN.md. AI interaction and eventual
AI-independent updates/rule runs must share the same evidence/research/validation/
risk gates. Do not treat AI text as an official completed report, evidence or
execution authorization. Automatic facts refresh is not automatic strategy,
parameter, trust or governance mutation. Conditional entry/scale/exit monitoring
requires separately admitted methods and actual current positions/data; none is
enabled by a plan, a conversation or an open brokerage account.

Before implementation, read `PROJECT_STATUS.md`,
`config/project-governance.toml`, and the selected work-package document. Run
`python scripts/check_project_governance.py`. Work on one `ready` package at a
time; do not infer project state from chat history or historical milestone docs.
When state changes, update governance, status, package, risk, and debt records
in the same commit.

The October 18 reviewed research checkpoint is documented in
`docs/reviewed-baseline-2026-10-18.md`. Historical slice notes describe their
original dirty checkout; consult current Git state and the canonical status
before claiming changes remain uncommitted or that a local checkpoint is
available on another device. Never confuse a clean research-host preflight
with acceptance of WP-LAUNCH-001, Paper, PIT or live operation.

- Prefer Python standard library and typed, immutable domain models.
- Use `Protocol` or abstract interfaces at external boundaries.
- Add dependencies only when they solve a current requirement.
- Keep provider-specific payloads outside the domain layer.
- Access AKShare only through `tong_quant.data.providers`.
- In strict point-in-time mode, do not ingest provider-adjusted historical bars
  until dated corporate-action factors can reconstruct the adjustment visible
  at each decision time.
- Never overwrite point-in-time facts, security-status history, universe
  membership, or corporate actions silently. Use revisions, raw hashes, and
  ingestion batches to preserve auditability.
- Fundamental fact retries must compare material content, not raw hashes alone.
  Reject conflicting values, semantics or trust labels under one version;
  preserve first-capture audit metadata on identical retries. Keep each write
  call atomic even if an outer transaction catches its exception. Invalid
  legacy rows remain visible and require separate review, never silent repair.
- Financial numeric corroboration is read-only and partial. Bind manual PDF
  page/column/period/unit annotations to exact retained bytes and native rows;
  numerical agreement cannot approve native semantics, canonical population,
  research/validation, provider independence or PIT. Keep bank applicability
  explicit and do not backdate a review before capture/review availability.
- Dedicated manual issuer-filing extraction is separate from numeric spot
  review/native mapping approval. Publish only supported explicit group/CNY
  semantics with registered PDF bytes, review packet, facts and audit in one
  neutral transaction. Keep LOW/RETRIEVAL_TIME (UNKNOWN stays UNKNOWN), source
  claimed publication/revision limitations and metadata intact. Raw fact rows
  lack standalone scope columns; inspect companion evidence before research
  eligibility. Table presence is not approval to score, replay or validate.
- Extended v4 monetary reviews support explicit CNY/yuan, CNY-thousand and
  CNY-million amounts with Decimal conversion. Preserve v1/v2 packet identities
  and v3 bank-ratio semantics. Nonfinancial operating_cash_flow is distinct
  consolidated calendar-YTD net operating cash flow, not FCF, parent-only flow,
  standalone-quarter flow, income or a bank metric. Compare only source-bound
  same-filing normalized amounts. A combined input diagnostic is not a completed
  ResearchReport, passed screening or financial scoring policy; never invent
  a queue or source qualification to make the real example pass.
- Research financial snapshots must recheck source bytes, review/evidence/fact
  content, registry ownership and completed batch chronology in one read
  snapshot. Preserve rejected/unsupported observations separately from absent
  metrics. Bind the receipt to the exact consumed facts/instrument/cutoff;
  caller mutation must fail before a persisted run. SOURCE_BOUND describes
  stored consistency, not independent trust or financial scoring approval.
  All new financial assessments remain diagnostic/unscored until a separate
  admitted source-bound sector policy exists, including empty/evidence-only
  contexts. High numeric annotations, industry labels and caller authorization
  metadata cannot bypass this boundary. Retain legacy records read-only rather
  than automatically qualifying or rewriting them. Do not apply generic bank ROIC/FCF
  assumptions or reinterpret local review versions as issuer revision history.
- Financial snapshots must revalidate fact/instrument chronology and visibility
  in actual UTC, including hash/document and context binding calls. A repeated
  local clock label cannot admit a later input or alias two decision cutoffs;
  equivalent actual instants must bind. Snapshot period/filing date guards use
  a pinned UTC date, not caller timezone; this is a conservative date bound,
  not an exchange-session or issuer-local financial-calendar approval. China-A
  bank report-age diagnostics retain their separate Shanghai-date contract.
  Bank/nonfinancial latest selection orders availability in UTC before revision;
  rejected latest inputs cannot fall back and exact-instant ties stay ambiguous.
  Preserve original timestamps, source packets, facts and historical receipts.
  Scoped temporal checks do not admit sector scoring, source trust or PIT.
- China-A nonfinancial input checks must distinguish NOT_REQUESTED, missing,
  rejected/unsupported/ambiguous latest rows, semantic/target-period mismatch and
  observed-unqualified inputs. Explicit quarter targets must not select older
  favorable data; inferred latest visible periods are not proof of the latest
  issuer filing. Report-period age and observation-availability age are distinct.
  Zero report-age limit is UNASSESSED. Keep ROIC and interest-bearing-debt
  definitions unimplemented until reviewed; never substitute ROE or total
  liabilities. The selected checklist is neither complete research nor a sector
  classifier. Persist its exact hash/policy/diagnostic JSON through the existing
  Financial assessment; no second report, financial score or trading authority.
- Same-filing comparatives require an explicit filing edition, source column,
  flow/stock periods and unverified original-revision status. Preserve exact
  v1 source packets when extending the model; receipt-shape changes need new
  model versions. Descriptive comparisons must match issuer/filing/scope/units,
  use compatible periods, preserve missing/rejected/ambiguous inputs and never
  fall back to an older favorable current row. Nonpositive baselines do not
  yield growth percentages. Asset changes since year-end are not stock returns
  or automatically year-on-year growth. All such features remain unscored.
- Bank ratio reviews use a separate current-period-end percent contract, not
  CNY-million conversion. Preserve `1.23` as 1.23 percent with null currency,
  explicit `period_end_ratio` basis and group/bank scope. Never infer fractions,
  annualization, percentage-point changes or a generic ROE definition. Keep
  v1/v2 monetary packet identities byte-stable and version richer receipts.
  Ratio observations alone cannot approve a sector scoring policy or readiness.
- Nonfinancial ROE uses the separate v5 current calendar-YTD weighted contract
  `roe_weighted_ytd_unannualized` with percent/null-currency semantics, signed
  values and explicit January-start/end-quarter periods. Do not annualize,
  recompute from ending equity, alias generic roe/roic, infer a comparative or
  reuse bank period-end semantics. Preserve v1-v4 packets and retained missing
  metrics. Source-bound ROE remains LOW/retrieval-time and cannot admit scoring.
- V6 nonfinancial cash/balance reviews add current total/current liabilities,
  monetary funds and YTD operating cash inflow/outflow. Do not infer blank
  borrowing amounts, interest-bearing debt, unrestricted cash, cash equivalents
  or debt clearance from these inputs. Same-filing diagnostics preserve missing,
  rejected, ambiguous and conflicting observations; a cash-flow residual is exact,
  never rounded away. A failed component check withholds dependent cash ratios.
  Arithmetic agreement and favorable ratios cannot authorize financial scoring.
- V7 adds signed current nonfinancial group `equity_attributable_to_parent`.
  Never substitute total assets, minority-inclusive equity, share capital in CNY
  or an inferred share count. Valuation-basis diagnostics distinguish missing,
  not-requested, incompatible, interim and nonpositive denominators. Interim
  profits/revenue are not annual or TTM inputs, including when negative. No
  annualization, favorable old-row fallback or valuation multiple is permitted
  without independently qualified dated market-value/period inputs. Preserve
  v1-v6 source packets and LOW/retrieval-time evidence. Financial scoring stays
  unqualified; these diagnostics are not a second report or investment advice.
- Dated issuer share-count reviews are a separate read-only annotation contract,
  not group monetary FundamentalFacts or a new provider ingestion path. Require
  whole shares, issuer/period/column/page labels, retained PDF/registry/completed-
  batch binding and actual review visibility in UTC. Keep LOW/retrieval-time
  (UNKNOWN remains UNKNOWN), incomplete/conflicting components and explicit
  current-continuity gaps. Unrestricted shares are not index free float; CNY book
  share capital/EPS averages are not share counts. No later-price multiplication,
  current carry-forward or scoring/validation/readiness authority follows exact
  arithmetic or a manual page label. Review plans are not populated SQLite facts;
  source semantics still require independent review and dated action continuity.
- Share-continuity inventory requires an explicit base review and target date.
  Check actual retrieval and completed-batch visibility in UTC, not claimed
  publication alone. Preserve visible versions/rejected bindings; titles only
  organize document review, never quantify or confirm actions. Empty/unmatched
  inventories cannot prove no changes. Publication windows miss earlier notices
  with later effective dates. Keep current shares/market value unknown and all
  admission gates closed until independently reviewed interval/action evidence
  exists. Batch binding is not original-query/PDF verification or full coverage.
- Manual share-action reviews are external read-only annotations, not a canonical
  action ledger. Share one retained-CNInfo source binder with share-count reviews.
  Require exact PDF/registry/completed-batch binding and actual UTC review
  visibility; only matching captured metadata versions inherit a supplied review.
  Keep issuer capital, holder/plan transfers/disposals, plan termination and
  proposed/pending events separate. Missing effective dates remain unknown;
  retrospective pre-base events cannot become incremental post-base changes.
  Never infer issuer delta (including zero), current shares, coverage or totals
  from plan quantities/rounded percentages. Manual review is not independent
  verification or scoring/validation/PIT admission; preserve unmatched reviews.
- Trailing financial v1 supports only source-bound China-A nonfinancial group
  calendar-year income. A year-end input is a reported annual observation;
  interim trailing arithmetic requires exact reviewed receipts for previous FY,
  current YTD and same-current-filing prior YTD. Bind the full three inspections,
  not values or evidence IDs alone, and require review availability after inputs
  and no later than the actual UTC cutoff. Changed receipts need a new review.
  Keep negative/zero values, missing/rejected/ambiguous inputs and original
  editions visible. Manual as-reported review is not independent accounting/
  consolidation/revision verification, source promotion, financial scoring or
  qualified TTM. Default factories have no review grants; explicit module
  injection/CLI review plans cannot authorize valuation, validation or trading.
  Do not replace the original partial-year valuation-basis diagnostic with the
  separate derived trailing amount or use a late review at an earlier cutoff.
- Market-value captures preserve the delivered public HTTP body in a bounded
  envelope with status/error and actual retrieval time. Never follow arbitrary
  redirects, fabricate a zero quote, re-date current shares backward or treat a
  failed capture record as numeric coverage. Capture first, then pin ingestion
  cutoff; do not weaken strict PIT validation to hide network elapsed time.
  Direct Eastmoney and AKShare Eastmoney share an upstream, not two providers.
  Reconstruct observations from bytes/evidence/artifact/completed batch before
  use. Latest failure/rejection/tie must not select an old favorable snapshot.
  Keep total versus float shares/values distinct; never use CNY share capital
  as share count. Native CNY/share units, claimed quote clock, cross-listing/FX,
  buybacks and share-class scope remain unqualified. Matching date/price or
  exact arithmetic is not freshness, independent truth, PE/PB/PS or scoring
  approval. V2 diagnostics bind every original supplied bar row and the explicit
  quote/capture/bar age policy; None limits are UNASSESSED, never unlimited/PASS.
  Latest suspension cannot resurrect an older close. Optional equity-only
  ResearchContext receipts must match subject and actual UTC cutoff and recheck
  mutation before a persisted run. Official Financial report features retain the
  full matching diagnostic with reasons/ages/limits/trust/evidence hashes, but
  remain incomplete/unscored. The combined CLI is diagnostic only, not a second
  report. Source/sector valuation and decision qualification remain separate work.
- China-A bank input diagnostics must preserve NOT_REQUESTED versus MISSING,
  rejected/unsupported/ambiguous latest observations and exact target-period
  semantics. Do not fall back to older favorable inputs. Report-period age and
  capture age are distinct; a zero/unconfigured maximum age is UNASSESSED, not
  unlimited freshness or PASS. Within-limit/source-bound inputs remain
  unqualified for scoring. This scoped policy cannot apply implicitly to global
  banks, substitute generic ROE aliases or establish complete bank research.
  Use the pinned Asia/Shanghai decision date for this policy's period age;
  equivalent timestamp instants must not diverge by caller timezone.
- New AKShare bars, calendars and numeric statement values must not be
  backdated before actual retrieval. A matching disclosure event cannot prove
  numeric revision provenance. Missing fallback turnover is unknown, not zero;
  price/action ingestion must not replace company snapshots with placeholders.
  Legacy backdated records require separate audit/reconstruction, not automatic
  acceptance after a code upgrade.
- Daily AKShare failures must preserve safe per-endpoint diagnostics through
  ingestion workers. Empty/schema/key failures are not network retry candidates
  or proof of zero historical coverage. An observed missing BSE payload must
  not permanently disable valid later responses. Change fetch-cache identity
  when repairing acceptance behavior, never rewrite legacy evidence silently.
- Sina BSE raw captures are LOW/retrieval-time observations only, not canonical
  daily bars or a new automatic fallback. Retain exact wire bytes and decoder
  identity; never evaluate provider JavaScript, forward-fill missing prices,
  round/deduplicate history or infer former codes. Admit after actual retrieval,
  not the pre-fetch cutoff. Out-of-range counts are not defective-price coverage.
  Require independent units, basis, identity and source calibration before any
  promotion; Sina SDK versus Sina raw is not two independent providers.
- New unadjusted AKShare daily bars must commit through neutral ingestion with
  source-bound frame artifacts and exact canonical-row evidence in one unit
  of work. Keep original cached serialization, verify fingerprints and exact
  price reconstruction; never silently round a mismatch away. Bind full rows
  and availability, not close alone. A binding remains LOW/retrieval-time until
  independently reviewed and cannot manufacture trusted calculation context.
- New corporate-action cash amounts are gross currency per old share; split
  ratios are total new shares per old share. Require explicit corroborated
  units, provider implementation label and ex-date; never substitute the
  registration date or treat a proposal as implemented. Preserve rejected rows
  and LOW/RETRIEVAL_TIME evidence. Repeated observations are not cumulative
  adjustments, and legacy action units are not silently migrated.
- AKShare provider limitations and missing publication timestamps must be
  persisted as warnings instead of hidden inside normalizers.
- AKShare endpoints without native timeout parameters must use a bounded Tong
  Quant wrapper. A slow endpoint must become an explicit partial-report error,
  never block the entire audit indefinitely.
- AKShare response quality metrics describe observed rows only and must not
  upgrade PIT trust, historical continuity, or cross-provider consistency.
- Persist normalized market data through `SQLiteStore`; do not write ad hoc
  strategy-specific data files.
- Screening, research, and validation must read historical data through
  `MarketDataService` with an explicit timezone-aware `as_of` timestamp.
- Treat company information and universe snapshots as current snapshots unless
  a dedicated historical security-master source proves otherwise.
- Current CSI constituent responses are dated snapshots, not historical
  entry/exit ledgers. Repeated ingestion improves forward coverage only.
- Never infer relisting from trading resumption, or infer a complete ST interval
  from a current name/status snapshot.
- Never use `stock_zh_a_stop_em` as suspension evidence: it is delisted-market
  quote data. The old current-suspension method deliberately fails closed.
  Dated `stock_tfp_em` rows are partial LOW/retrieval-time observations, not
  current-status clearance. Expected resumption and reported end dates must
  never emit confirmed resumption events. New suspension captures archive
  original frame evidence with canonical events in one neutral transaction;
  preserve and flag old records rather than silently certifying/deleting them.
- Use `data.lifecycle_review.review_lifecycle_record` for record usability in
  runtime/coverage consumers. QUARANTINED is logical exclusion, not deletion;
  OBSERVATION_ONLY preserves weak evidence. REVIEWABLE means structural review
  only, never independent source verification, full timeline coverage or
  trading approval. UI-visible broker data is a retrieval-time observation,
  not historical/PIT authority or permission to connect/submit orders.
- Replay must preserve original status provenance and shared review results.
  Unusable status blocks sample/manifest eligibility even when present and
  highly labeled; adverse but reviewable status is not a missing input.
  ValidationRequest creation must recheck version, record hash, instrument and
  decision-time binding. Build replay reads in one snapshot and persist each
  manifest/sample set atomically; old results require explicit reconstruction.
- Replay outcomes use the versioned exact UTC calendar-day contract, not
  nearest available bars or assumed exchange sessions. Bind exact price rows,
  enforce horizon/lag and separate decision/outcome visibility; missing or
  unsupported inputs remain blocked diagnostic samples. Unadjusted price
  changes are not total returns or executable prices. Persist replay results
  without replacement, with manifest-owned sample ids and atomic repository
  writes; preserve content hashes across distinct generation times.
- Bind the complete reconstructed ResearchReport/evidence and visible input
  row inventories into replay identity. Recheck content and derived validation
  fields before use; missing references, conflicting evidence, duplicate modules
  and future child data block eligibility without dropping diagnostic samples.
  Preserve policy evidence during reconstruction. Research evidence ids are
  immutable within a run; changed content requires a new identity. Reconstructed
  visible inputs are not proof of the original run's exact consumed context,
  and hashes are not independent source verification or trading approval.
- Use the scoped SSE pilot manifest to distinguish observed date counts,
  exact source bindings, configured warm-up deficits and trusted historical
  coverage. Versions are not extra dates; no session percentage is valid
  without a verified denominator. Scoped empty action/lifecycle queries do
  not prove absence. Inventory cannot promote PIT or authorize validation/
  simulation; optional credential-screened exports must be new files only.
- Capture real AKShare native statements through financial-snapshot and the
  neutral evidence/artifact transaction until accounting units, native metrics,
  periods and revisions are reviewed. Native snapshot rows are not qualified
  FundamentalFacts. Preserve zero/blank/null separately, retain retrieval-time
  availability and do not use disclosure dates to backdate numeric values.
  Keep exploratory and operational databases distinct; cross-scope gap counts
  cannot be subtracted as a readiness percentage. New captures do not satisfy
  the scheduled five-scope provider horizon automatically.
- Fundamental publication dates and reported numeric values are independent
  evidence. Never copy a current revised value backward into an earlier
  publication event when the earlier value is unavailable.
- Provider calibration compares normalized evidence but cannot alone grant
  `VERIFIED` trust. Preserve provider-only records and disagreement warnings.
- All new providers must implement `ProviderEvidenceAdapter` and enter through
  `ProviderNeutralIngestionService`; provider SDKs must not create parallel
  persistence paths.
- Neutral ingestion must revalidate returned batch/child chronology and compare
  strict event/availability/publication cutoffs and batch/completion instants in
  UTC before file/database publication or canonical callbacks. Repeated DST
  labels cannot alias retrieval binding; equivalent actual instants remain valid.
  Relaxed PIT never disables chronology, trust ceilings or batch integrity.
  Preserve existing identities/old rows; valid ordering is not source trust,
  original historical availability, or a repository-wide temporal certification.
- No provider is trusted by default. Capability health, trust, coverage,
  availability precision, continuity, and consistency are separate evidence.
- CNInfo evidence transported through AKShare must retain the provider identity
  `cninfo_via_akshare`; do not claim direct-source verification.
- Direct CNInfo evidence must retain `cninfo_direct` provenance, use only the
  approved official HTTPS query/static-document scope, respect bounded
  pagination/rate limits, and persist failed or missing artifact observations.
- Provider document bytes belong in `ProviderArtifactStore`; SQLite stores
  content hashes and safe relative storage keys, never ad hoc absolute paths or
  credentials. Direct-source success cannot promote trust without measured
  parity, coverage, and continuity review.
- Yahoo Finance evidence is research-grade, unofficial, `LOW` trust, and
  `RETRIEVAL_TIME` availability. Calibration agreement alone cannot change
  either classification.
- Scoped China-A Yahoo quote observations are a separate price-only dataset,
  not a market-value, canonical-bar or global-adapter capability shortcut. Require
  explicit .SZ/.SS route and matching native metadata, actual retrieval cutoffs
  and retained decoded-envelope/artifact/completed-batch reconstruction. Preserve
  latest failures/ties without fallback, LOW trust and UNASSESSED freshness.
  Decoded JSON is not original wire bytes; post-decode size limits do not bound
  the existing transport. Do not infer shares/market value, daily closes, source
  qualification, financial scoring or trading permission from this diagnostic.
- The combined read-only candidate diagnostic may consume retained Yahoo prices
  through `research.technical.quote_alignment` at the same explicit cutoff. Keep
  quote/capture/bar ages separate; None limits are UNASSESSED, not approval.
  Compare dates in Shanghai, never infer price conflicts/returns across different
  dates. Same-date snapshot/close arithmetic is descriptive, not cross-provider
  consistency or current executable pricing. Bind full supplied bars, quote
  inspection and policy; retain unsupported scopes/failures/ties/suspensions and
  bounded-arithmetic limitations. Do not promote shares, market value, financial
  freshness, official research/scoring, strategy validation or readiness.
- Daily-bar calibration compares only explicitly unadjusted series. Persist
  `unavailable` or `incompatible` attempts; never turn missing secondary access
  into zero coverage or agreement.
- Massive is an optional US calibration provider. Read `MASSIVE_API_KEY` only
  from the environment, send it only in an Authorization header, require
  `adjusted=false`, and keep redirects/pagination inside approved official
  HTTPS paths.
- Provider contract monitoring may detect access and schema drift but must never
  upgrade `DataTrustLevel`, PIT readiness, or historical continuity.
- Provider health is repository operations data. It must not import or call the
  Notification Engine, external message channels, Portfolio, or trading code.
- Only implementation/contract defects fail the scheduled monitor. External
  unavailability and repeated degradation remain visible, acknowledged audit
  conditions and must preserve their historical gaps.
- Provider contract checks distinguish structural schema absence from value
  completeness. A missing required payload key is a defect; a present key with
  a null value or an empty normalized response is degraded and must remain
  visible in missing-field coverage.
- Provider monitor outputs use run IDs or content hashes. Keep CI artifacts for
  90 days and retain the contract-history database until an archive and restore
  have been verified.
- GitHub-hosted workflows pin an explicit supported runner image and use
  Node 24-compatible official Actions. Do not return to a moving `*-latest`
  runner label or an end-of-life Action runtime without a reviewed migration.
- Longitudinal provider baselines must keep successful observations, required
  field coverage, and scheduled-run continuity as separate metrics. Missing
  periods, failed probes, and empty responses remain visible; baseline history
  cannot promote provider trust or PIT readiness.
- Provider evidence bundles must be read-only, content-addressed,
  credential-free, and bounded by an explicit timezone-aware `as_of`.
  Continuity gates must be reviewed per provider, dataset, market, and subject;
  dataset-level aggregates cannot hide a missing scope. Never export local
  artifact paths or include incomplete/future-completed ingestion batches.
- Archived provider history must contain the contract-run, check, and baseline
  identities claimed by its evidence bundle. ZIP integrity alone does not prove
  recoverability; use the isolated `restore-drill` on each retained copy.
- `WP-EVIDENCE-001` horizon completion requires a verified bundle whose five
  scheduled CNInfo/Yahoo scopes each pass the fixed 84-day/eight-check audit
  with complete baseline measurements. Calendar age, a dataset aggregate, or a
  successful endpoint response cannot substitute for this evidence.
- Only new runs recorded as `scheduled` with a GitHub run reference can count
  toward the horizon's scheduled checks and observed days. Pre-migration runs
  remain `unknown`; verify claimed GitHub event and artifact identity before
  accepting a horizon pass. Never backfill run origin from timing alone.
- Tushare credentials must come only from `TUSHARE_TOKEN`. Never persist,
  render, log, or include the token in cache keys or request parameters.
- Validate Tushare credentials locally before live access and persist only
  capability status, never token values, lengths, prefixes, or fingerprints.
- A successful empty provider response proves endpoint access only; it does not
  prove dataset coverage or historical continuity.
- Provider permission errors are access limitations, not empty datasets.
- Missing secondary-provider access must render coverage and consistency as
  unknown or `N/A`; never convert it to zero or provider agreement.
- Generated readiness reports must record query dates, symbols, periods, and
  other scope parameters needed to interpret and reproduce each observation.
- Persist repeated provider conflicts as audit history. High-severity conflicts
  must prevent `USABLE` PIT readiness until resolved or explicitly superseded.
- Market regime classifiers consume only normalized `RegimeMetric` inputs.
- Every regime input, bar, and external breadth or volatility metric must have
  `available_at <= as_of`.
- Market Regime is a high-weight decision variable, not a hard trading switch.
- No regime state may automatically approve or reject an opportunity.
- Regime weights and thresholds belong in configuration, not strategy code.
- Trend ATR, trailing, and pyramid outputs are research scenarios only until
  they pass the future Validation Engine.
- MACD, KDJ, moving-average events, Granville events, and candlestick patterns
  are correlated technical evidence, not independent votes or direct trade
  actions. WP-RESEARCH-002 implements unscored family-aware diagnostics, not
  the admitted strategy/sizing layer. Read the October 20 technical audit for
  actual coverage; caller-supplied intraday scores are not implementations.
  MACD/KDJ share one momentum family and MA/triple/Granville continuation one
  trend family. Preserve contradictions and separate mean reversion.
  Seven-plus-one needs Tong's exact rules. Software calculations do not waive
  WP-RESEARCH-001 data/validation gates.
- Candidate conditions require an explicit ResearchRequest.condition_style.
  WP-RESEARCH-003 joins actual hard screens, qualified financial review and
  technical predicates in the official report, not a second report model.
  DATA_BLOCKED/SCREEN_REJECTED keep reports incomplete; WAIT_CONFIRMATION is
  not a sell instruction; VALIDATION_REQUIRED is not validated strategy approval.
  Long-value and trend hypotheses have distinct financial roles. Do not present
  bearish setup references as long stops or claim fundamental invalidation
  windows are evaluated when marked NOT_EVALUATED. Seven-plus-one is deferred.
- Size is cross-sectional Style Research. It requires PIT market capitalization
  and the historical eligible universe; never classify or rank size from a
  current-universe snapshot copied backward.
- A triple-average candle setup must use explicit versioned predicates and
  configurable periods. Follow-through observed on later bars must never enter
  the original decision context.
- Dynamic stops remain invalidation references until a future approved layer
  has real position state, market rules, and fill evidence. A stop price is not
  a guaranteed execution price.
- A-share Pattern Research must return insufficient data when required
  breadth or intraday evidence is unavailable.
- Validation must distinguish data `as_of` from the actual `requested_at` run
  timestamp.
- Validation outcomes and thresholds must be registered before results are
  evaluated.
- Research correctness and Decision Journal correctness must be measured
  independently.
- Every Validation Run must store Git, framework, configuration, research,
  validation, and database schema versions.
- Final OOS usage limits must be enforced by persistent state, not caller
  convention.
- Portfolio validation may measure research concentration but must not simulate
  portfolio returns or orders.
- Validation outputs only `REVIEW` Signals and must never create trade actions.
- Replay samples with missing data, low trust, ST/suspended/delisted status, or
  provider limitations must remain visible with warnings.
- Portfolio consumes InvestmentScore outputs only and must not bypass Research
  or Validation.
- PortfolioProposal and PositionProposal are research artifacts only. Do not
  use advice-oriented or execution-oriented names for them.
- RiskAssessment may constrain or reject a PortfolioProposal, but it must not
  create orders, broker requests, fills, trades, paper-trading actions, or
  auto-rebalancing instructions.
- Execution defaults to `disabled`. Future OrderFactory, Broker, or execution
  entry points must be protected by ExecutionDisabledGuard and
  ExecutionReadinessGate.
- Notification is a research notification boundary only. It may consume
  ResearchReport, ValidationReport, PortfolioProposal, and RiskAssessment. It
  must not consume Order, Trade, Broker, Fill, or Execution objects.
- Notification mode defaults to `disabled`. Generation writes to the SQLite
  outbox; delivery must occur later through the dispatcher.
- Notification dispatch claims must use finite leases. Expired claims must be
  recovered or dead-lettered; never leave `dispatching` records permanently
  orphaned.
- Channel credentials must come from environment variables and must never be
  persisted, logged, rendered, or placed in tests.
- Credential-like assignments must be rejected at domain, repository, and
  low-level persistence boundaries.
- Every notification must carry the mandatory research-only disclaimer.
- Database schema changes must use ordered checksum-verified migrations. Do not
  update schema metadata without completing the migration.
- Before changing `SCHEMA`, preserve the previous fingerprinted migration
  head's schema-definition hash in `SCHEMA_DEFINITION_HASHES`; otherwise newer
  code cannot authenticate and restore that historical backup safely.
- Never copy a live SQLite database with filesystem copy commands. Use
  `SQLiteBackupService`, run a read-only audit before and after copying, and
  publish only to a new destination after verification.
- Current-schema restores must not initialize or rewrite metadata. Require
  same-schema logical content verification in addition to integrity/counts;
  SQLite dump comparison is representation/version-sensitive and lossy NUL
  text must fail closed. Older schema migrations cannot claim the same content
  flag merely from row-count equality. Never upgrade historical backup reports.
- Restore drills must use a separate new path. Never overwrite or migrate an
  active source database during recovery testing, and keep backups on an
  approved encrypted volume with no credentials in command arguments.
- Audit registered provider artifact bytes with the database's explicit storage
  root before and after migration to another device. A registry/file hash match
  is not a full backup, source authentication or PIT approval; unregistered rule
  captures and metadata-only disclosures need separate recovery inventories.
- Multi-step final Research and Validation writes must use one transaction
  boundary.
- `docs/data-trust-matrix.md` is authoritative for AKShare PIT suitability. Do
  not promote a dataset without new provenance and coverage evidence.
- Store secrets in environment variables or untracked local configuration.
- Preserve PyCharm as the primary development workflow.
- Deployment preflight is offline host diagnostics only. Keep its explicit
  project root, committed/runtime/checkout source binding, clean-Git check,
  safe configuration and read-only database audit fail-closed. Never turn a
  passing host report into PIT, strategy, Paper or live authorization. Installed
  wheel smoke checks must run outside checkout and verify package origin.
- Native dependency locks are target-specific and hash checked. Keep runtime,
  dev and bootstrap/build scopes separate; preserve the reviewed source-build
  exception and fail closed on lock/spec/version/target drift. Generate from
  pip resolver reports using standard packaging APIs, not inferred transitive
  dependencies. A matching lock does not approve provider data or trading.
- V1.0 remains equity-focused. Reserve naming and interfaces for future funds,
  ETFs, REITs, money-market funds, bond funds, and allocation research, but do
  not implement fund research, portfolio allocation, or execution before an
  approved milestone.

## Verification

Before considering a change complete:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
python scripts/check_project_governance.py
```

Add tests for market behavior, timestamp integrity, configuration safety,
layering constraints, and changed decision rules.
