# Work Package: WP-LAUNCH-001

Status: `ready`

## Owner-Approved Usability Priority: November 17

The first acceptance case is a repeatable MSFT research loop, not a prose-only
stock opinion or a new trading work package. This reorders delivery inside this
ready package; it does not mark it accepted or activate a scheduler/worker.
Retain the four-market and financial/nonfinancial scope after this first case.
Reuse the existing MSFT thesis proposal, technical bindings and official research
and validation contracts. Do not create an alternative official report or score.

1. Explicit fresh-input and failure checks: retain actual capture/availability,
   selected source and cutoff; do not present old data as a successful update.
2. Daily/weekly/monthly context: distinguish primary methods, supporting features,
   correlated evidence and ended periods. Yearly views cannot finalize an open year.
3. Compact change digest: compare two explicitly selected, verified original
   snapshots and their recomputed diagnostics. Bind company, market, source,
   parameters, exact UTC cutoffs and original receipts. Mark source/parameter/
   freshness/period changes separately from observed price or business changes.
4. Holding thesis review: qualified evidence plus explicit approved definitions,
   thresholds and windows; declarations alone remain NOT_EVALUATED.
5. Historical/OOS verification and concise research output through existing
   Validation. No best exit date, success probability or holding/add/exit authority
   is implied by a diagnostic, a simulated example or passing engineering tests.

The delivered bounded implementation is step 3's read-only daily foundation,
not the whole loop. Its tests cover fixed-input determinism, wrong-subject/
market/cutoff/parameter/source handling, DST/late revisions, prior/current
missing/stale/failed states and no favorable fallback. Missing evidence is not
no change. Comparing different source versions is not business improvement;
unverified bar coverage is not verified market sessions. Avoid arbitrary-JSON
comparison that can be satisfied merely by rehashing caller claims.

Every delivery should identify the runnable increment, remaining blockers and
next step. Ask Tong only for material operator decisions/actions, specifying what,
why and what stays blocked without it. No secrets or private position/risk details
in Git. Risk measurement needs an explicit definition before any policy. Owner-defined
271 terms and seven-plus-one stay deferred. Execution/notifications remain
disabled, PIT UNSUITABLE and production NOT_READY. The priority addendum is not
whole-loop acceptance; actual partial implementation is recorded below.

Research direction: define strategy and horizon before applying fundamental
criteria; short-term research may differ from long-term value research, but
data/tradability/validation/portfolio-risk gates remain hard. Separate market,
industry and instrument trends and large/small horizons; regime is contextual,
not a global trading switch. Market/flow evidence supports hypotheses, not
certainty about an institution's identity or intentions. No runtime policy is
relaxed by this statement, and a losing trade cannot silently change its horizon.

## Current implementation slice

November 24 independent release review identified unsanitized UTC conversion
overflow in the equity change CLI. Both price and native change APIs now turn
either cutoff's conversion overflow into a generic ValueError before source
reads. Twenty-four added API/CLI cases cover both range edges and all existing
period/native modes. This is an input-boundary repair, not source qualification,
new research outcomes, execution or work-package acceptance. Full publication
still requires exact-candidate quality checks and independent follow-up review.

November 23 H3 evidence-only follow-up binds fourteen original references to
XML-side affixes/neighbor cells and selected lexical headings. Native sign
attribute absence and split-cell PPE parentheses cannot determine numeric or
economic sign or authorize a value rewrite. No selected numeric text, new amounts,
parser/default/trading or qualification change. Two processes match and five old
pins stay exact; see ../msft-h3-definition-review-2026-11-19.md for final checks.
Independent read-only review did not complete due to the tool's usage-limit
error; it remains pending, not accepted or replaced by main-runner checks.
All seven accounting relations remain UNKNOWN; ready, not accepted.

November 23 optional compact source view reduces repeated detail after full
original recomputation on the same snapshot. Distinct source/full-inventory/view
hashes, explicit omissions and every blocker/unknown/authority are retained;
49 added cases, one fixed old-default vector and two synthetic byte-size examples.
See ../sec-window-inventory-2026-11-18.md. This is a bounded source diagnostic
view, not a new official report, source authentication or holding method. No
schema/default/trade/commit/push change; ready, not accepted.

November 23 optional v4 adds bounded per-selection parser-record/returned-occurrence
multiset hashes using the existing original factories and one DB snapshot. Typed
source/capture binding is rechecked; only hashes/status/counts are published.
Sixty-two added cases and one frozen old-default vector cover the scoped addition;
see ../sec-window-inventory-2026-11-18.md. Full lexical/formal SOURCE_CHANGE,
source/accounting/method/holding gates remain open, all authorities false and H3
unchanged. No schema/default/trade, commit/push change; ready, not accepted.

November 23 record-projection boundary design plus sixteen existing-reader
characterizations separates bounded parser records from full XML bytes. The
512-character decoded preview and independent 128-character stripped numeric
limit stay unchanged. Future representation scope is parser-occurrence-only;
original normalized strings/multiplicity and body hashes remain distinct. See
the SEC comparison proposal/boundary record. This is not parsed/representation
runtime, financial/source/method admission or a parser repair. No runtime/CLI/
version/schema/default/trading/commit/push change; ready, not accepted.

November 23 third slice opts into check/gap-state projection through the existing
source-reference API/CLI, requiring complete capture identity. Same outer snapshot
and original inventories; v3 preserves default single/v1/v2 outputs on one fixed
vector. Source failures/missing/stale material and version drift remain unassessed;
tag-scoped counts and original report-period blockers stay explicit. Forty-eight
added synthetic cases; see ../sec-window-inventory-2026-11-18.md for verification.
Parsed/representation and financial/source/method gates remain open. No schema/
default/trading/commit/push change; ready, not accepted.

November 23 second slice optionally adds full selected-capture ID/time/raw hash
to the existing two-cutoff source-reference API/CLI, from the original factory
documents on one outer DB snapshot. Default single-cutoff/v1 outputs match a
frozen synthetic vector; explicit v2 remains partial observation with all false
authorities, missing/failure/stale states intact. Forty-two added synthetic cases;
see ../sec-window-inventory-2026-11-18.md for checks and limitations. Parsed-record,
representation/gap and financial/method gates remain open. No schema/default/
trading, commit/push changes; ready, not accepted.

November 23 test-only follow-up adds complete parent/reference-material hash
assertions and asymmetric missing/available coverage through original synthetic
factories. Twenty cases include an independent-review-requested first-body capture
between cutoffs. No runtime, CLI, version, schema/default or authority change;
see ../sec-window-inventory-2026-11-18.md for final verification and remaining scope.
Full financial/source/method admission stays separate; ready, not accepted.

November 22 optional two-cutoff SEC source-reference observation is runnable in
the existing window API/CLI with --previous-as-of. One outer read snapshot binds
both original inventories. Receipt, capture ID/time reference, parent binding and
body bytes are separate; unknown/failure/stale is not unchanged. Full planned
SOURCE_CHANGE, raw_data_hash capture identity, parsed/representation/gap axes and
financial admission remain unimplemented. No values, default-output, schema,
source/method/trading, commit/push changes; ready, not accepted. See the November 22
section of ../sec-window-inventory-2026-11-18.md for verification/limits.

November 22 second follow-up: replay outcome v5 validates integer day horizon/lag
and catches duration/target/earliest datetime overflow. Invalid windows raise;
no rounding, fallback, economic horizon cap or session policy is introduced.
Thirty-two synthetic cases include defensive entry checks, valid integer windows,
datetime upper boundaries and legacy-v4 row preservation/current reconstruction.
See the replay endpoint record. No generic constructor/JSON/source admission,
schema/default/trading, commit/push changes; ready, not accepted.

November 22 follow-up: replay outcome v4 rejects unsupported/bool/overflowing
threshold inputs; real nonfinite floats retain the existing named blocker and
diagnostic-only result. Finite comparison and price/business separation stay.
Seventy-three new synthetic cases include nonzero float thresholds and legacy-v3
preservation/reconstruction; old rows are never rewritten. See the replay endpoint
record addendum. Scope is this evaluator, not constructors/windows/JSON or source/
strategy admission. No schema/default/trading, commit/push change; ready, not accepted.

November 22 H3 metadata review binds the exact lease-note continuedAt link to
the previously selected wrapper and ten fact references. Current wrapper context
must not override comparative fact contexts. Existing CIK/date/USD shape checks
and unique selected IDs do not qualify source/statement/accounting semantics.
Two runs match, five old file pins stay exact; this is direct pinned-byte review,
not new registry reconstruction. See ../msft-h3-definition-review-2026-11-19.md.
No new amounts, parser, test/config/default/authority, commit or push changes.
Next complete statement/classification and cash/noncash review; all seven overlap
relations remain UNKNOWN, ready, not accepted.

November 22 replay outcome v3 repairs automatic price-to-business-thesis labels.
Numerical return/success and endpoint rules are preserved; business thesis stays
NOT_OBSERVABLE, invalidation detection null. Existing historical price validation
and thesis aggregation now receive distinct semantics; no new thesis evaluator.
Twenty-three added synthetic cases include legacy-v2 row preservation/current
reconstruction and forged-label rejection. See the November 22 addendum in
../replay-endpoint-qualification-2026-11-17.md. No schema/default/strategy/trading,
commit or push change. Source-bound business outcomes remain open; ready, not accepted.

November 21 owner exit-research requirement is now in the existing MSFT thesis
proposal, with thirteen synthetic existing-behavior holding-review regressions.
Continuing/reducing/exiting/adding require distinct evidence; cost recovery, unknown
inputs and declared horizons cannot be holding approval or an exit instruction.
Business/strategy/event/funding reasons and cost-versus-portfolio drawdown scope
are separated. No evaluator, thresholds, production/default/schema/authority,
commit or push change. Next explicit falsifiable thesis conditions and qualified
outcome/OOS review; H3 work remains parallel. Ready, not accepted.

November 20 second H3 slice records fixed-source table/ancestor references for
four OCF/PPE occurrences and ten lease candidates without new amounts. The latter
share one issuer nonNumeric textblock; zero segment/scenario containers do not
admit contexts. No global scope/dimensional relaxation or new parser. Two audits
match; five old files remain exact, and a new ignored metadata/tool packet records
pins. See the second November 20 section in
../msft-h3-definition-review-2026-11-19.md. Next exact wrapper/continuation and
statement/context review; all seven accounting relations remain UNKNOWN.
Ready, not accepted; no runtime/test/default/authority, commit or push changes.

November 20 H3 issuer evidence retains a new public deck in an ignored manual
packet, with visual slide/period/unit/sign binding and two-column arithmetic.
Four values agree numerically with the exactly reconstructed old SEC subset;
receipt and five old files remain unchanged. No provider ingestion, independent
source qualification, approved FCF formula or seven-relation overlap resolution.
Entry HTML was rejected by existing preflight and not retained, not bypassed.
See the November 20 section in ../msft-h3-definition-review-2026-11-19.md.
Next exact statement/scope and cash-versus-lease review. No runtime/test/default/
schema/authority, commit or push change; ready, not accepted.

November 19 second H3 slice extends the existing review with a proposed signed-
contribution definition, issuer-versus-research metric identities, seven UNKNOWN
overlap relations and a pending predeclared outcome/validation path. Documents
only: no arithmetic, composite binding, extra numeric parsing or new test is
implemented. Official live references are method context, not retained/fresh
filing admission. Next retain/reconcile one issuer definition and exact-period
components before deciding composite support. See the follow-up in
../msft-h3-definition-review-2026-11-19.md. Ready, not accepted; no authority,
default/config/schema/runtime, commit or push change.

November 19 H3 source-definition review binds four existing OCF/PPE facts to old
source labels/contexts and locates ten lease-related metadata candidates without
extra numeric parsing. The 60-reference/32-name lexical inventory is not financial
coverage or accounting admission. Signed flows, aggregate overlap, noncash items,
measure definition and outcome-method questions are explicit. See
../msft-h3-definition-review-2026-11-19.md. Existing-reader regressions are not a
new formula, definition approval or H3 validation. No runtime/default/schema/
trading changes, commit/push or sync retry; ready, not accepted.

November 18 partial SEC window inventory adds a standalone read-only CLI and typed
API over existing period factories. Exact same-tag windows/namespace/CIK/cutoff and
selection bindings are inspected with retained blockers; no amount, arithmetic or
new financial admission. Old MSFT gives two raw unqualified/five economically
unadmitted pairs, preserving the old receipt and five files. See
../sec-window-inventory-2026-11-18.md. SOURCE_CHANGE, the full plan, definitions and
method validation remain open. Defaults/schema/dependencies/trading unchanged;
ready, not accepted; no commit/push or GitHub sync retry.

November 18 SEC comparison contract separates source changes from financial
window comparisons and explicitly records namespace/scope/definition/availability
gaps in the existing exact-period reader. Twelve added characterizations cover
existing behavior; they do not implement or accept the proposed comparator.
See ../proposals/sec-filing-change-comparison-v1.md and
../sec-comparison-boundaries-2026-11-18.md. Next opt-in comparability inventory
must remain non-dimensional, source-reconstructed and unqualified, with accounting
and method admission independent. No runtime/schema/default/trading change,
commit or push. Ready, not accepted.

November 18 optional native annual change context reconstructs original US/HK/MY
receipts in the same read-only snapshot as price inputs. Same/different retained
records, latest period/value/label changes and historical changes are descriptive;
they cannot establish growth or issuer restatements. Latest failures and partial
metric gaps remain explicit; no capture or older-good fallback. No flag preserves
v1/v2, opt-in uses v3. Frozen prior outputs and old-cutoff three-market rehearsal
preserve 54 pinned files, not source qualification. See
../native-fundamental-changes-2026-11-18.md. Qualified fundamental assessment stays
NOT_ASSESSED. Filing-backed accounting comparison, reviewed update/recovery and
method/OOS validation remain open. Ready, not accepted; no commit/push or trading.

November 17 optional weekly/monthly change context reuses existing long-horizon
calculations on the same read-only original snapshots. Calendar-end advancement
is distinct from new prices; cross-period indicators are NOT_ALIGNED, gaps and
missing warmup remain unassessed. False/missing opt-in preserves daily v1 bytes;
v2 carries compact hashes, dates, statuses and no decision authority. Retained
three-market compatibility/repeatability preserves 54 pinned files, not current
market/source qualification. See ../equity-period-changes-2026-11-17.md. Next:
bound fundamental changes, reviewed update/recovery and method/OOS verification.
No runtime defaults, schema, trading, commit or push. Ready, not accepted.

November 17 daily change digest and JSON CLI compare two retained US/HK/MY price
snapshots within one read-only transaction, binding recomputed original-source
diagnostics. Null counts, missing warmup, revisions/source/parameter changes and
latest failures stay explicit; no capture or favorable fallback. 65 focused
offline tests and old-cutoff three-market rehearsal pass. Fundamentals and
multi-timeframe changes are NOT_ASSESSED; holding method NOT_VALIDATED. Next:
ended-period context and financial changes, reviewed update/recovery and actual
method/OOS evidence. See ../equity-change-digest-2026-11-17.md. This is runnable
daily comparison, not a completed recurring loop or Paper/holding/trading authority.
Ready, not accepted; no commit or push.

November 17 Yahoo native fundamental clock guard rejects unsupported capture
offsets for US/HK/MY before retention, after download. UTC contracts and existing
native accounting boundaries stay unchanged; old mismatched records remain
blocked without favorable fallback. Seventy-two regressions, six frozen-HEAD
vectors and old-cutoff real retained MSFT/Tencent/Maybank compatibility checks
pass. No new capture, canonical fact or holding/strategy admission. See
../yahoo-fundamental-clock-2026-11-17.md. Pre-fetch attempt/recovery and independent
source/publication/revision qualification remain open. Ready, not accepted.

November 17 SEC clock prevention covers submissions, concepts, filing pages and
bodies. Unsupported producer offsets fail before retention, after download;
accepted UTC identities, non-UTC read cutoffs and historical records stay exact.
Sixty regressions and eight frozen-HEAD compatibility vectors pass. Real retained
MSFT's ten period checks retain exact old hashes; two archive gaps remain gaps.
Other provider clock risks are inventoried, not fixed by this slice. See
../sec-capture-clocks-2026-11-17.md. No source/PIT/strategy or trading promotion;
durable fetch attempts, independent qualification and exact-candidate release
review remain open. Ready, not accepted.

November 17 Yahoo snapshot clock prevention rejects unsupported producer offsets
before retention, preserving accepted UTC bytes/IDs and all legacy records.
Non-UTC query cutoffs remain allowed; blocked old captures cannot fall back to an
older good row. Failed new fetches do not count as fresh captures or durable
attempt audit. Synthetic tests and frozen-HEAD adapter comparisons cover US/HK/MY;
scoped static review found no actionable issue. See
../yahoo-capture-clock-2026-11-17.md. No source/PIT or strategy promotion, real
DB/schema/default changes or trading behavior. Ready, not accepted.

November 17 replay outcome v2 blocks flagged suspended/unknown price endpoints
and actual-UTC visibility/chronology failures. Raw bindings and incomplete samples
remain visible; no neighboring or old-active fallback, zero return or negative
research label is invented. Centralized versioning yields new identities without
rewriting legacy rows; old versions require reconstruction for current Validation.
No schema or real DB writes, source/PIT upgrade or trading change. See
../replay-endpoint-qualification-2026-11-17.md. Ready, not accepted; session/action/
source evidence and combined-method validation remain open.

November 17 opt-in daily technical binding recomputes the complete diagnostic
against explicit original prices/parameters at build and render. It binds full
Bar identity/count, original price receipt, UTC cutoff and output without changing
default JSON/Markdown, formulas, old identities or schema. Synthetic mismatch and
rehashed-content cases are rejected; US/HK/MY CLI scope stays read-only. Legacy
unbound direct calls, exact-candidate release review and default cutover remain
open. Retained MSFT/NVDA rehearsals preserve six old files and scoped static AI
review found no actionable issue. See ../technical-display-binding-2026-11-17.md. This is ready,
not accepted, and grants no source, strategy, holding, Paper or live authority.

November 16 independent review found four sync blockers despite passing checks.
Working repairs move credential preflight before artifact publication and use
UTC for lifecycle visibility, research period dates and nested replay research.
Re-review also repaired a UTF-8 BOM JSON bypass, preserving source bytes/hashes.
Forty-four regressions and 527 focused passing tests (127 research integration
tests) do not replace full isolated-tree checks or independent re-review; both
are required before publication. No schema,
dependency, production, source/PIT, strategy or trading promotion. Open nonblocking
source-binding, suspended-price and producer-clock debt is recorded in
docs/independent-review-hardening-2026-11-16.md. Ready, not accepted.

November 16 dimensional-context design audits expanded source names and wrappers
without new numeric parsing. Original exclusions span 35 distinct contexts, six
axes and 17 pairs; two Azure-named references cannot substitute for consolidated
or MicrosoftCloud inputs. The registered proposal specifies exact complete
context/source bindings and future tests, not runtime acceptance or new passing
coverage. Ready, not accepted; all financial/PIT/trading gates remain unchanged.

November 16 P1 financial-context slice adds opt-in excluded-occurrence structural
observations to existing SEC parser/read/CLI. Original defaults, facts, values,
source/period hashes and retained-source gates remain unchanged. Real MSFT has
45 excluded occurrences, 37 segment observations and 34 ancestor blocks with
26 overlapping; no accounting validity or source admission follows. No global
display/report/thesis evaluator or trading integration. Ready, not accepted.

November 16 v7 presentation repair removes raw false-as-success from Nasdaq date
comparison tables. Future/unavailable/out-of-span/intraday-unknown cases are
unassessed; contradictory fields are rejected. Source/review JSON and hashes,
stored old notes and no-source defaults are preserved. Real strict-price sample
now distinguishes eight unavailable and four future dates. No calendar/source/
method admission or trading changes. Ready, not accepted.

November 16 real calendar refresh rehearsal captures the fixed source into a
new private DB/root; old evidence remains unchanged. Changed body bytes retain
the same 12 parsed declarations, not independent corroboration. Real MSFT reads
prove old-cutoff exclusion, current source visibility and independent stale-price
blocking. Three new CLI regressions cover refresh history/latest failure and
immutability. No new runtime feature, automatic refresh, canonical dates, source
admission or trading authority. Ready, not accepted; see the Nasdaq source record.

November 15 explicit Nasdaq co-review composes the retained source reader with
the overseas CLI under explicit DB/root/year/age/cutoff selection. New price-bound
receipt/v6 note preserves native times and stale/failed observations; no fallback,
calendar conversion or coverage repair. Real MSFT yields STALE under an illustrative
one-day limit, retaining 12 old observations with DB/WAL bytes unchanged. Venue/
session/source and method qualification remain open. Ready, not accepted.

November 15 annual date-coverage follow-up extends the existing declaration
comparison to years and exposes it in long/multi-timeframe notes. Same-snapshot
price/calendar hashes and cutoff are bound; all source/session/scoring authorities
stay closed, with legacy trust/precision UNKNOWN. Real retained MSFT finds no
calendar rows in its selected price database, not provider-wide unavailability
or no trading days. No weekday filling, source import or indicator change.
Ready, not accepted; retained-source/venue calendar qualification remains open.

November 15 timeframe follow-up adds optional weekly SMA/MACD/KDJ and explicit
daily-versus-ended-period source dates. Keep v1 month/year output and existing
default views exact; v2/new v4 are opt-in. Known weekly gaps/latest failures and
unended weeks are not bypassed. Exchange closure, freshness, source admission
and cross-timeframe investment methods remain unverified, not completed by a
same-cutoff display. No voting/score/holding decision. Ready, not accepted.

November 15 long-horizon slice adds optional ended month/year observations and
shared SMA/MACD/KDJ arithmetic, with a context-checked Chinese view. No period
gaps or suspensions are stitched; open periods and insufficient yearly warmup
stay explicit. Real retained MSFT yields 46 ended months/3 ended years without
DB writes or changes to legacy default JSON. No session/source qualification,
cross-timeframe scoring or holding decisions. See the long-horizon observation
document. Ready, not accepted; the four-market helper is not a new A-share CLI.

November 15 second slice connects typed thesis declarations via an explicitly
configured DefaultResearchReportBuilder to the sole ResearchReport's assessment
features, existing transactional SQLite writes and historical reconstruction.
Plans bind actual queue/instrument/UTC cutoff and unchanged complete conditions;
future references cannot be published. Enabled reports remain INCOMPLETE with
no InvestmentScore; default report bytes/version are unchanged. No CLI, schema,
real-source admission, evaluator or outcome labels. Ready, not accepted.

November 15 implements a callable typed thesis evidence/window declaration
contract with deterministic diagnostics and no source admission or evaluation.
It reuses existing condition definitions, preserves all legacy report contracts
and keeps future/mismatched/missing/ambiguous references visible and excluded.
Not yet connected to requests, CLI, official report persistence or real MSFT
observations. See the implementation addendum in the linked MSFT proposal.
This is the P2 contract foundation only, not launch acceptance or thesis validation.

November 14 [MSFT thesis/validation design](../proposals/msft-holding-thesis-validation-v1.zh-CN.md)
audits the actual condition/report/validation contracts and retained source gaps.
It defines falsifiable business/cash/valuation/risk questions, future explicit
period/source bindings, separate decision/outcome evidence, add/exit research
boundaries and pre-registered horizon validation. No evaluator, numeric threshold,
source admission or result label is implemented/approved. Ready, not accepted.

November 10 [explicit SEC raw root](../sec-source-root-composition-2026-11-10.zh-CN.md)
removes the real price/filing directory composition blocker through explicit US
read-only selection, not copying, registry rebinding or source admission. Optional
holding context now precedes the complete combined hash in SEC and HK/MY branches;
new combination version preserves old records. Real retained MSFT prices, ten
period checks and owner annotation repeat together with old-price BLOCKED and all
authorities closed. Schema/defaults unchanged; launch remains ready/not accepted.

November 9 owner holding follow-up: optional --holding-context reads a bounded
local manual annotation into existing diagnostics. Exact UTC, original daily
inputs, source/technical hashes, price/context age and latest suspension guards
block pre-position/stale comparisons without guessing returns, stops or horizons.
Owner loss thresholds request review only; cash/fill/fees/action continuity and
financial/strategy validation remain unqualified. All authority stays false;
default output unchanged, no schema or account connection. See
../holding-review-2026-11-09.zh-CN.md and PROJECT_STATUS. Ready, not accepted.

November 9: the existing single-equity view now enforces actual-UTC cutoff equality
across price, fundamental, review and optional trend receipts. Synthetic DST-fold
mixing is rejected; equivalent aware labels are accepted. New Markdown component
version preserves old files, original JSON and numerical formulas. No source/PIT
or trading admission; real offline NVDA reconstruction is unchanged. See the
single-equity usability record and PROJECT_STATUS for checks. Ready, not accepted.

November 8 [Nasdaq source age](../nasdaq-calendar-freshness-2026-11-08.md): optional
offline exact UTC age checks preserve original observations but withhold stale
current declarations. Missing/latest bad inputs remain blocked without fallback;
limits bind receipt hashes. Old default v1 output stays exact and UNASSESSED.
No automatic refresh, chosen default TTL, source qualification, schema or trading
change. Non-UTC producer-clock reconstruction limitation is explicitly retained
as blocked debt. Full verification is recorded in PROJECT_STATUS.md. This slice
does not accept launch or admit dependent packages/strategies.

The [US regular-session/calendar contract](../proposals/us-regular-session-calendar-v1.md)
is a design/source-audit slice only. Primary web review identified a prospective
December 6 hours transition, not proof of current operation. It specifies separate
source/policy availability, effective/operative status, session scope and exchange
trade-date mapping before ordinary-calendar/price coverage admission. Acceptance
cases cover DST, Sunday/holiday/month boundaries, source ambiguity and legacy
receipt preservation; they are not newly implemented tests. No source capture,
runtime, schema/default/trading/commit/push changes. Regression suite: 3624 passed /
6 skipped, 240.62 seconds; Ruff/mypy (313 files), governance (167 checks), scoped
documentation review and git diff --check pass. Sample DB hashes are unchanged;
no future acceptance case or source is qualified by this run. Next: exact retained
source/operative evidence and scoped regular-only implementation, not a blind
weekday default or automatic overnight switch. Ready, not accepted.

The [Nasdaq explicit source](../nasdaq-calendar-source-2026-11-07.md) retains bounded
fixed-URL original HTML through existing neutral ingestion/artifact/batch/evidence
contracts and reconstructs at one actual cutoff without networking. Strict year/
table/date/status checks preserve drift/duplicates/latest failure/tie/tamper;
early-close times stay explicit and unlisted dates unknown. Manual capture reserves
a new diagnostic DB, never auto-append/migrate existing files. Real November 7
capture supplies 10 closure/two early-close declarations, not full calendar or
actual sessions. LOW/retrieval-time and false authorities persist; no old-cutoff
visibility or source/PIT upgrade. Existing price/SEC DBs are unchanged; new raw/DB
evidence is ignored by Git. 47 new cases; full pytest 3624 passed / 6 skipped,
237.31 seconds. Ruff/mypy (313 files), governance (166 checks), scoped import/
credential review and git diff --check pass. Network skips are not source evidence.
No schema/default/strategy/trading/commit/push; ready, not accepted. Next: regular/
abnormal-session and historical-source coverage, provenance-preserving period
integration and actual research/validation, not a lossy TradingSession copy or
automatic collector/monitor admission. Mixed-tree tests are not release validation.

The [calendar declaration comparison](../calendar-declaration-coverage-2026-11-06.md)
reuses original calendar/daily checks and legacy TradingSession observations to
separate unknown dates, missing open-day observations, closed-date conflicts and
suspensions. Actual-UTC revisions and source separation remain strict. Conditional
percentages never certify sessions/source/PIT; UNKNOWN calendar trust/precision
and false authorities persist. Opt-in CLI uses the price database snapshot and
leaves old output unchanged when absent. SQLite calendar writes reject non-bools
before any writes and reads reject malformed non-0/1 integer states; no schema or
historical-data rewrite. Real MSFT's queried window has zero calendar declarations;
no source evidence is invented. 45 new synthetic cases; full suite 3577 passed /
6 skipped, 251.68 seconds. Ruff/mypy (310 files), governance (165 checks), scoped
import/credential review and git diff --check pass. Skips are not source evidence.
Next: qualified exchange/source/price-action inputs, period-trend policy and actual
validation. No defaults/trading/commit/push; ready, not accepted. Mixed-tree tests
are not source or isolated-release qualification.

The [calendar period diagnostic](../calendar-period-diagnostics-2026-11-06.md)
aggregates original daily versions into market-local weekly/monthly OHLCV with
exact Decimal sums, explicit missing/unended/suspension states and false scoring/
PIT/validation/trading authority. Expected session coverage stays unknown. The
optional global CLI flag is read-only and leaves legacy output unchanged when
absent. Technical's existing observation-return/range score now declares its
proxy basis, prospectively v0.5.5; no arithmetic or historical record replacement.
Four-market pure math and US/HK/Malaysia CLI boundaries stay separate. Real
retained MSFT reproduces 706 rows/147 ended weeks/33 ended months, retains missing
and unended periods and leaves both database hashes/previous SEC v1 output intact.
30 new synthetic cases plus proxy-label assertions cover integration. Full suite
3532 passed / 6 skipped, 447.88 seconds; Ruff/mypy (309 files), governance (164
checks), scoped security/import review and diff check pass. Not complete
U3, independent price/session/source/strategy qualification or isolated candidate
review. No schema/default/trading/commit/push. Next: calendar/source/action
coverage and admitted period-trend/actual validation alongside existing financial
and deployment gates. WP-LAUNCH-001 remains ready, not accepted.

The [SEC period research binding](../us-sec-research-binding-2026-11-06.md) adds
an immutable copied receipt to existing context/Financial/report features, with
US equity/sector/cutoff/parallel-input and pre-write integrity validation. Failed
states retain their read cutoff; Financial remains unscored and report incomplete.
25 synthetic combined Technical/Financial persistence cases pass across five
sectors/source states. Real retained MSFT builds the same input binding without
creating a real queue or report. Full suite 3502 passed / 6 skipped, 216.00
seconds; 67 new cases. Ruff/mypy (308 files), governance (163 checks), scoped
security/import review and diff check pass. Mixed-worktree tests are not
release-candidate/source/strategy qualification. No source/sector admission,
schema/default/trading/commit/push; ready, not accepted. Next: qualified identity/
accounting/sector definitions and real screened research/strategy validation,
alongside technical/deployment work. Financial version changes prospectively only.

The [US exact SEC period inputs](../us-sec-period-inputs-2026-11-06.md) add strict
native tag/duration/instant selections and an opt-in v3 diagnostic. Exact contexts
never become annual/quarter/YTD/TTM classification, accounting aliases or scores.
Duplicates, conflicting/unsupported matches, unresolved contexts and source
failures remain visible. Six real retained MSFT contexts repeat without DB writes
or altering previous v1 hashes; source remains partial/unqualified. Full suite
3435 passed / 6 skipped (42 new cases), 208.66 seconds; Ruff, mypy (308 files),
governance (162 checks), scoped import/security review and diff check pass.
Mixed-worktree checks are not release-candidate/source/strategy qualification.
No schema/default/source normalization/trading/commit/push. Ready, not
accepted. Next: source/sector binding to existing Financial Research and real
screened research/validation, alongside outstanding technical/deployment work.

The [US issuer declaration review](../us-issuer-declarations-2026-11-06.md)
adds exact retained ticker comparison with whole-list ambiguity/unsupported
handling and separate exchanges, not a ticker/CIK qualification. One snapshot
and original-byte rechecks preserve latest failures and cutoff identity.
Optional --sec-identity has separate derived/display versions; old paths and
source normalizers stay unchanged. 187 focused checks pass (40 new); full suite
3393 passed / 6 skipped, 205.30 seconds. Ruff/mypy (307 files), governance (161
checks), scoped security/dependency review and diff check pass. Retained MSFT
declarations repeat without DB writes or changing the previous SEC v1 hash.
Not independent identity/source or repaired-candidate verification. No source/
score/schema/trading grant or commit/push; ready, not accepted.
Next: source-bound US accounting/sector contracts, qualified identity and real
screened research/validation, with existing technical/deployment gaps retained.

The [US read-only delivery increment](../us-readonly-delivery-2026-11-05.zh-CN.md)
prioritizes November 30 as a target within the existing four-market scope.
The existing technical CLI now optionally reads explicit retained SEC body/
catalog/concept evidence at one cutoff, preserving independent missing/failure/
conflict states. Caller CIK/ticker pairing is unverified, no native field mapping,
source/scoring/validation or trading authority follows. Same DB uses one snapshot;
separate DBs share only cutoff. No schema/default/capture change. 24 new cases;
full suite 3353 passed / 6 skipped (208.20 seconds), Ruff, mypy (307 files),
governance (160 checks), scoped security/dependency review and diff check pass.
Independent read-only review found no actionable findings. Retained historical
MSFT repeats 706 bars/nine SEC same-origin matches; both DB hashes unchanged.
Not current data, exact pre-increment golden verification or candidate release
validation; no commit/push. Ready, not accepted. Next: US identity/accounting/
source policy and real research/validation plus technical/deployment gaps,
not indefinite co-display.

The [prepared local ownership primitive](../prepared-resource-ownership-2026-11-05.md)
pins existing private empty files and tries exclusive OS flock. Cross-process
BUSY, holder-crash release, child descriptor invalidation and parent-lock retention
are tested. No auto-create/unlink/re-pin; uncertain close quarantines process use.
It does not map or atomically acquire all resource coordinators, reserve bytes or
authorize a collector. Existing writers are not integrated. Next: group ownership
and broader supervisor shutdown/transport/retention tests. No schema/default,
real-data, trading, commit or push; ready, not accepted.
22 new cases / 107 focused checks; full suite 3329 passed / 6 skipped, 186.07
seconds. Ruff/mypy (307 files), governance (159 checks), scoped credential/
dependency review and git diff --check pass; retained sample DB hashes unchanged.

The [committed fetch lease guard](../refresh-fetch-lease-guard-2026-11-05.md) now
checks FETCHING ownership in a new read-only snapshot, rejects caller-store
managed contexts, and revalidates metadata/current runtime plan. Real child
processes prove retained/retried/expired ownership is no longer accepted by the
parent's cached claim. It is not a resource lock or continuing capture approval;
no existing collection entry point is integrated. Next: cooperative resource
ownership/fork tests before capture-once integration. No schema/default/user-data/
trading change, commit or push. Ready, not accepted.
31 new cases / 104 focused checks; full suite 3307 passed / 6 skipped, 161.37
seconds. Ruff/mypy (306 files), governance (158 checks), scoped credential/
dependency review and git diff --check pass; retained sample DB hashes unchanged.

The [one-shot admission/recovery contract](../proposals/one-shot-refresh-admission-v1.md)
is specified, not implemented. A concurrent synthetic preflight test preserves
false reservation/collection authority despite individually passing observations.
The design requires cooperative resources, current under-lock checks, pre-fetch
CAS, capture-once, fenced retention and exact failure-aware recovery. Fork/child
termination, resource-specific safe codes and staging/DB bounds remain gates.
Next: scoped ownership/fetch-side guard implementation and real-process tests,
then bounded integration. Old GitHub candidate 8794b57 remains blocked pending
packaged repair and exact-tree review; no commit/push. Ready, not accepted.
One new synthetic case / 112 focused checks; full suite 3276 passed / 6 skipped,
157.09 seconds. Ruff/mypy (306 files), governance (157 checks), scoped dependency/
credential review and git diff --check pass. Both retained sample DB hashes unchanged.

The [capacity preflight](../artifact-capacity-preflight-2026-11-04.md) adds an
explicit immutable byte policy, bounded no-follow metadata inventory and
conservative space diagnostics. All regular names count; unsafe/incomplete scans
cannot produce favorable totals. This is not an enforced quota or reservation,
and existing writers are unchanged. No real archive scan, collection, defaults,
schema or trading change. Next: reviewed serialized single-shot admission/size/
reservation/recovery contract, then bounded integration. Ready, not accepted.
40 new synthetic cases / 111 focused checks; full suite 3275 passed / 6 skipped,
Ruff/mypy (306 files), governance (156 checks), scoped dependency/credential review
and git diff --check pass. Retained sample DB hashes unchanged; no commit/push.

The [read-only exact refresh inspector](../refresh-reconciliation-2026-11-04.md)
now verifies exact attempt/batch/fingerprint/evidence/original references using
one SQL snapshot plus bounded secure byte checks. Shared parameter/status helpers
avoid retention/reconciliation drift. First registry ownership may be earlier;
failed captures remain failed, missing links never use guessed substitutes.
No repair/reset/checkpoint, capture, scheduler or source/trading admission. Next:
bounded capacity and one-shot integration; cross-store recovery remains unaccepted.
37 new synthetic cases; final suite 3235 passed / 6 skipped, Ruff/mypy (304 files),
governance (155 checks) and git diff --check pass. Both retained sample DB hashes
are unchanged. No commit/push; launch stays ready, not accepted.

The [shared-original rollback protection](../artifact-rollback-retention-2026-11-04.md)
reproduces and prevents creator rollback deleting another writer's adopted bytes.
Published originals remain retained; failed database writes still roll back.
Interleaved ingestion and separate-process tests cover same/shared registries.
No automatic GC or data/source/PIT admission. Next: exact reconciliation and
capacity gates before one-shot capture; encrypted recovery/global references
remain independent. No user-data, schema or trading change. Ready, not accepted.

The [durable refresh ledger](../refresh-ledger-persistence-2026-11-03.md) adds
registered immutable tasks, pre-capture persistent claims, transactional CAS,
bounded retry, expiry -> reconciliation and same-transaction typed batch links.
Migration 0011 / schema 0.8.3 is tested in temporary databases only; retained
user data stays unchanged. No worker, full verifier or successful checkpoint.
Next: original-file concurrency and exact reconciliation/restore acceptance,
then one-shot capture. [Reviewed sync](../github-reviewed-sync-2026-11-03.md)
does not waive candidate validation or publish the mixed worktree. Ready, not accepted.

The [pure refresh attempt contract](../refresh-attempt-contract-2026-11-03.md)
adds immutable lease/phase/failure rules, finite observed-fetch retry, UTC/DST
checks and reconciliation-required outcomes. It is not a durable queue, persisted
claim, crash recovery service or data checkpoint. The [ledger migration proposal](../proposals/data-refresh-ledger-v1.zh-CN.md)
defines dedicated job/attempt ownership, transactional evidence correlation and
isolated fingerprint/backup validation before deployment. No schema/PIT/default/
trading promotion. Next: review and implement the ledger in test databases,
prove concurrent CAS and atomic batch links, then one-shot capture. Ready, not accepted.

The [dual operating model](../ai-assisted-and-independent-operation.zh-CN.md)
keeps AI-assisted interaction and eventual independent operation behind identical
evidence/research/validation/risk gates. The [A-share request bridge](../akshare-offline-refresh-bridge-2026-11-03.md)
adds static DailyBarRequest conversion only, preserving unsupported datasets,
unknown provider availability and actual future endpoint attribution. Five sample
requests validate, but no capture/worker/attempt/DB/schedule or research admission
exists. Next: dedicated durable job/attempt migration and audited one-shot recovery.
No framework/schema/default/PIT/trading promotion. Ready, not accepted.

The [offline refresh planner](../offline-data-refresh-plan-2026-11-03.md) is the
first implementation stage: strict explicit watchlist, existing static Yahoo
contracts, deterministic scope/config/UTC/version/Git plan and visible unsupported
bridges. It never collects, writes databases, schedules or admits sources/research.
AKShare legacy capture is not broken by an unbuilt refresh bridge. Unknown
permissions/calendar/quality and false authorities persist. Next: bounded source
bridges and dedicated durable job/attempt design, then audited one-shot recovery.
No schema/PIT or trading promotion. Ready, not accepted.

The [automated refresh design](../proposals/automated-data-refresh-v1.zh-CN.md)
distinguishes provider health from watchlist updates and specifies offline plans,
durable attempts/leases/checkpoints, bounded recovery and separate activation.
Synthetic stopped-fetch audit confirms no pre-fetch attempt exists today; no
production failure or user-data change is claimed. Design only, no runtime,
schema, scheduler, source/financial/PIT or trading promotion. Next: bounded
planner and crash-auditable one-shot data worker, with deployment separately
reviewed. Source/sector methodology and real validation stay required. Ready, not accepted.

The [original-document freshness slice](../original-document-freshness-2026-11-02.md)
separates annotated report age, original source age and actual review-record age
in existing Financial/report features and optional read-only output. Shared age
settings default UNASSESSED; re-review does not refresh old source or periods.
Missing/failure states remain visible and no age result qualifies source/scoring.
Next: reviewed source/sector/freshness specifications, current disclosure evidence
and real candidate research/validation. No schema/PIT or trading promotion.
Ready, not accepted.

The [read-only ratio selection slice](../readonly-ratio-source-selection-2026-10-31.md)
connects explicit primary/supplemental URLs to existing technical/native/monetary
co-display. Review documents share one read snapshot, with competing-writer
regressions; independent missing/failure states and legacy output remain intact.
No report creation, scoring, source/sector/PIT/schema or trading promotion.
Next: qualified source/sector/freshness methodology and real screened technical/
fundamental research/validation. Ready, not accepted.

The [multi-document ratio slice](../multi-document-ratio-research-2026-10-31.md)
adds primary plus bounded immutable supplements to existing context/Financial/
official report persistence. Receipts remain separate, same-cutoff and unscored;
missing/failure states and primary questions cannot be silently replaced. HK/MY
report reconstruction and pre-write rejection tests are included. No new schema,
source/sector policy, PIT or trading promotion. Next: explicit delivery-source
selection, qualified/current financial evidence and real research/validation.
Ready, not accepted.

The [separate liquidity-source slice](../bank-liquidity-source-evidence-2026-10-31.md)
retains a real Integrated Annual Report and three original percentage rows using
existing ingestion/read contracts. LCR rolling-average semantics stay explicit
and unsupported for instant arithmetic; exact documents/parents and old receipts
remain isolated. No runtime/schema/source-policy/score/PIT or trading promotion.
Next: independent definitions/current sources, explicit multi-document financial
research and admitted methodology/validation. Ready, not accepted.

The [explicit ratio arithmetic slice](../manual-ratio-arithmetic-2026-10-31.md)
adds source-pinned money/percentage equations and exact/rounded residuals in
existing Financial/report features. Three real declared displays reproduce;
unknown definitions, rounding and regulatory scope stay unqualified. HK/MY
synthetic reports preserve blocked sources and no InvestmentScore. No bank-policy,
source/PIT/schema or trading promotion. Next: independent candidate qualification,
dated liquidity/latest sources and admitted research/validation. Ready, not accepted.

The [bank capital/equity evidence slice](../bank-capital-equity-evidence-2026-10-31.md)
finishes interrupted 31-row money/six-row ratio editions and explicit 19-question
source plan. New scoped amounts/notes remain unqualified; 11 annotation matches
do not admit ratio/sector policy. Numeric LCR stays missing; old-cutoff receipts
remain exact and stale plan pins block. No schema/runtime/score/PIT or trading
promotion. Next: explicit context-bound arithmetic questions, dated liquidity /
current filing evidence and independently reviewed research policy. Ready, not accepted.

The [official original-ratio binding slice](../original-ratio-research-binding-2026-10-30.md)
adds distinct immutable ratio context, explicit source-row questions and existing
Financial/report persistence alongside Technical. HK/MY synthetic reports retain
missing/failed states without scores; real retained questions repeat without data
writes. Context/authority checks precede run writes. No ratio/sector/source policy,
schema, PIT or trading promotion. Next: original metric definitions and liquidity/
equity evidence, then admitted research/validation. Ready, not accepted.

The [original bank percentage slice](../global-bank-ratio-evidence-2026-10-29.md)
adds an independent ratio contract and exact retained reader, preserving five real
Maybank Group observations without widening monetary V1. Unknown definitions /
denominators / regulatory scope and current-parent failure gates remain explicit.
No official ratio report binding, bank-policy gap closure, source/score/PIT/schema
or trading promotion. Next is explicit immutable ratio research binding/questions;
WP-LAUNCH remains ready, not accepted. New ignored evidence needs co-retention.

The [manual annual comparative slice](../manual-income-comparatives-2026-10-29.md)
preserves a new 22-row review and plan, filling one selected prior-row gap while
retaining old reads. Seven explicit annual pairs produce descriptive changes;
one nonpositive base has no percentage. Existing reports remain incomplete /
unscored. No schema/PIT/source/scoring or trading promotion. Ready, not accepted.

The [draft bank source-input slice](../bank-source-input-coverage-2026-10-29.md)
adds exact source-pinned annotation questions with separate missing, unsupported
ratio and external evidence states. Real Maybank results reproduce without data
writes; synthetic report reconstruction stays incomplete/unscored. No policy,
source, scoring or PIT admission; no schema/trading changes. Ready, not accepted.

The [reviewed-document research binding](../reviewed-document-research-binding-2026-10-29.md)
connects exact manual receipts to existing ResearchContext, unscored Financial
features and report reconstruction. Synthetic Technical + Financial reports stay
INCOMPLETE; real factory reads repeat without inventing queues or writing reports.
No schema/sector/score/PIT or trading promotion. Ready, not accepted.

The [bank income arithmetic slice](../bank-income-arithmetic-2026-10-28.md) adds
explicit signed same-column checks and 15 real source-pinned Maybank statement
observations. Four declared sums agree as transcribed; a summary/statement Bank
revenue discrepancy remains unresolved. Prior editions/receipts survive; no
canonical/sector/scoring/PIT admission or schema/trading change. Ready, not accepted.

The [explicit native/manual candidate slice](../global-native-manual-candidates-2026-10-28.md)
adds bounded opt-in questions to the existing technical CLI and preserves unknown
scope/period/unit/precision/attribution/revision semantics. Eight real HK/MY
candidate questions repeat without SQLite changes; Maybank revenue definitions
remain unresolved rather than force-matched. No mapping/score/PIT admission,
schema or trading change. R1-R6 remain partial; ready, not accepted.

The [technical/review co-display slice](../global-review-display-2026-10-28.md)
uses the existing CLI and exact readers at one cutoff, preserving independent
missing/failed/unqualified states and explicit separate-database snapshot limits.
Real HK/MY outputs reproduce without database writes. No field/sector/source/
scoring/PIT or trading promotion. Provider inventory clarifies existing adapters,
real evidence, optional permissions and future-only providers. Ready, not accepted.

The [overseas monetary-review slice](../global-document-manual-review-2026-10-28.md)
adds a distinct source-pinned manual contract and eight real unqualified native
observations. Actual recording time, page/column/unit/period/scope pins and current
parent rechecks prevent backdating or favorable fallback. No China-model relaxation,
canonical population, financial score, independent validation or schema/trading
change. R1-R6 remain partial and the work package remains ready, not accepted.

The [HK/MY primary PDF slice](../hk-my-primary-documents-2026-10-28.md) retains two
real official-host documents through existing neutral storage and exact read-side
verification. Original bytes are not canonical financial facts; manual identity/
period/landing references remain unverified. A page-level manual review identifies
counter/currency, Group/Bank and unit/column hazards, without runtime extraction
or source/scoring/PIT promotion. No schema/trading change; R1-R6 remain partial,
status ready, not accepted. Next is a source-bound overseas review contract.

The [SEC primary-body slice](../sec-body-numeric-review-2026-10-27.md) retains
original periodic filing bytes and compares supported Inline XBRL occurrences
with same-accession API records, preserving unsupported facts. One real 8.6 MB
body yields nine supported numeric correspondences, not independent validation
or accounting/source admission. Initial byte-bound failure is preserved and
explicit recapture succeeds within bounded capacity. No score/canonical fact/
replay/trading authority or schema change. R1-R6 remain partially complete; this
does not accept WP-LAUNCH-001 or enable dependent packages.

The [targeted SEC older-page slice](../sec-older-pages-2026-10-27.md) closes 401
missing metadata references for the three-concept US sample through explicit
parent-pinned page 001. Page 002 remains quarantined for date-boundary/field gaps;
no provider defect or complete history is presumed. V1 source/archive hashes and
default recent-only concept receipts stay exact; v2 requires count agreement and
interval containment, not equal extrema. All six release acceptance groups remain
open. No schema/score/PIT/Paper/live promotion; status ready, not accepted.

The [SEC XBRL concept slice](../sec-concept-evidence-2026-10-27.md) retains 649 real
revenue/net-income/operating-cash-flow rows with native units/periods/accessions.
248 current-catalog references match; 401 missing references predate its recent
window and remain visible. Shared bounded transport, exact source ownership and
one-snapshot reference checks preserve old catalog hashes and never admit canonical
financial facts, scores or PIT replay. Older-page/body/accounting/issuer review and
encrypted raw co-retention remain open. No schema/Paper/live change; ready, not accepted.

The [SEC issuer filing slice](../sec-filing-evidence-2026-10-27.md) retains two
real 1003-row recent metadata snapshots through existing neutral contracts, not
canonical facts. A reproduced prospective DEF 14A report-date misclassification
is fixed by versioned form-aware semantics; original v1 hashes remain exact.
Acceptance/filing labels never become first publication or historical availability;
older pages remain uncaptured and issuer/ticker binding unverified. Environment
contact identity is not persisted. No source/trust/scoring/readiness promotion,
schema or Paper/live change; raw co-retention remains open. Ready, not accepted.

The [native Financial research binding](../native-financial-research-binding-2026-10-27.md)
connects retained receipts to the existing official context/Financial assessment/
report and SQLite reconstruction, retaining failed/missing states and original
source/review hashes. Financial remains unscored and incomplete, with no investment
score or PIT promotion. Synthetic queue fixtures test persistence only; real
three-market readers repeat without production reports or database changes.
No schema/source capture/Paper/live change; status ready, not accepted.

The [native sector-review slice](../global-native-sector-review-2026-10-27.md)
adds receipt-bound exploratory native amount changes and separate nonfinancial/
bank/securities/insurance/unknown research questions to the existing read-only
CLI. Native changes/positive technicals cannot qualify accounting, sector policy
or scoring; negative bank cash flow cannot become a generic failure. Real
retained three-market outputs repeat with unchanged SQLite bytes. No source,
schema, official-report/Paper/live change; status ready, not accepted.

The [native global financial input slice](../global-native-financial-inputs-2026-10-27.md)
adds seven selected annual provider-named observations and a fixed-cutoff combined
technical/native-financial diagnostic. Real three-market samples each retain
28 observations, not canonical facts or validated research. Reporting/quote
currency differences, unknown publication/revision/scope and latest bad/missing/
duplicate inputs stay explicit. Shared verification preserves price hashes.
No source/sector scoring or official-chain shortcut is admitted; no schema/Paper/
live change. Status remains ready, not accepted.

The [global price-to-technical bridge](../global-price-technical-bridge-2026-10-27.md)
adds explicit decoded snapshot capture and read-only reconstruction through the
existing neutral contracts. Actual US/HK/MY sample responses reproduce technical
diagnostics; an initial current-New-York-date sample is retained and blocked,
not silently replaced. Native adjustment history and source qualification remain
unknown; ephemeral bars do not enter canonical/PIT/scored research. No official
candidate/report/score is fabricated. Global financial inputs, independence,
continuity and actual validation remain open. No schema/Paper/live change;
status ready, not accepted. Ignored new evidence needs encrypted co-retention.

The [first decision-release plan](../decision-delivery-plan-2026-10-27.zh-CN.md)
and [four-market coverage matrix](../four-market-readonly-release-2026-10-27.zh-CN.md)
record Tong's confirmed read-only China A/US/Hong Kong/Malaysia financial and
nonfinancial equity scope. The earlier narrow-pilot scope/8-15-round estimate is
superseded. Six acceptance groups are not new governance packages, admitted
scores, approved weights or a live countdown. Financial sub-sector/overseas
definitions, Style and actual source/strategy validation remain gaps; no
China-specific pattern/rule assumption may silently migrate globally. Synthetic
cross-market regression tests verify shared calculations and boundaries only.
Existing evidence/replay/Paper/live gates are unchanged; status ready, not accepted.
Next: real four-market input mapping and bounded official candidate/report design
with separate detailed rubric/source acceptance, not renewed market-scope approval.

The [nonfinancial input checklist slice](../nonfinancial-input-checklist-2026-10-27.md)
adds explicit selected metric definitions, gap/target-period/version statuses and
separate report/availability ages to the combined diagnostic and existing official
Financial features. Shared financial age settings wire both bank/nonfinancial
policies; zero stays UNASSESSED. Real fixed-cutoff H1 data cannot satisfy an
explicit Q3 target. Source/sector scoring remains unadmitted; report persistence
tests keep research/InvestmentAssessment incomplete without InvestmentScore.
No schema/provider/Paper/live change or readiness promotion; status ready, not accepted.

The [financial snapshot UTC slice](../financial-snapshot-utc-2026-10-27.md)
repairs future folded-clock admission, snapshot cutoff identity and bank/
nonfinancial latest-version selection using actual UTC. Revalidation protects
direct diagnostics and persisted research before writes. Source packets/data/
schema are unchanged; runtime versions record changed semantics. Real 17-row
source binding stays LOW/retrieval-time with ROIC missing, not independent truth
or sector/strategy qualification. Status remains ready, not accepted; no Paper,
broker, Portfolio, Notification or live change, and PIT remains UNSUITABLE.

The [manual share-action review slice](../share-action-review-2026-10-26.md)
records explicit per-document scope/stage/date/quantity semantics in read-only
plans and joins exact retained PDF versions to continuity inventory v2. Shared
CNInfo source binding preserves existing share-count receipt identity. The actual
employee-plan annotation records holder transfers/disposal/termination, not
issuer cancellation or zero issuer delta. Prior-base dates and missing dates stay
explicit. Independent source/body/action/coverage review, financial admission and
strategy validation remain open; no schema, Paper or live changes. Status stays
ready, not accepted, and PIT stays UNSUITABLE.

The [share-continuity inventory slice](../share-continuity-inventory-2026-10-26.md)
captures a post-H1 CNInfo metadata window and two targeted PDFs through existing
neutral ingestion. Actual UTC capture/completion gates prevent newly retrieved
old publications entering earlier inventory. Title tags and version/batch checks
prepare document review, not implemented share changes or complete action coverage.
Current shares/market value and all admission gates remain unqualified; prior
effective-date notices, corrections, source semantics, financial/strategy validation
and raw co-retention stay open. The package remains ready, not accepted.

The [dated share-count review slice](../share-count-review-2026-10-26.md) binds an
opt-in manual issuer/whole-share review to retained PDF/registry/completed-batch
identity at an actual UTC cutoff. The real June 30 002624 counts reconcile, but
are not qualified current shares; CNY book capital and index free float stay
separate. No source promotion, canonical data publication or price multiplication
occurs. Independent page semantics/share-class/action continuity, sector admission
and strategy validation remain open. This package stays ready, not accepted.

The [daily refresh/suspension slice](../daily-refresh-suspension-guard-2026-10-26.md)
adds four real observed 002624 dates and exact frame/678-row reconstruction at
actual capture availability. Earlier cutoffs remain unchanged. A synthetic
pre-suspension current-score fallback is repaired across Technical/Trend/Pattern
and direct diagnostics without deleting historical rows or inferring resumption.
Incomplete report/InvestmentAssessment persistence cannot issue an investment
score. Raw byte checks, same-date price equality and module tests are not source,
financial, strategy or trading qualification. Dated shares/actions, admission,
retention and remaining launch gates stay open; status ready, not accepted.

The [common-cutoff alignment slice](../price-input-alignment-2026-10-26.md) joins
retained Yahoo prices into the combined financial/technical input diagnostic.
UTC ages, Shanghai date alignment and full-row/quote/policy identity avoid
fresh-capture/old-quote confusion and cross-date false conflicts. Real retained
002624 inputs are mismatched and stale under illustrative limits, not qualified
current investment evidence. No new database data, report, score or authority is
created. Dated shares/actions, source/sector policy and actual strategy validation
remain open; WP-LAUNCH-001 stays ready, not accepted.

The [Yahoo China price-evidence slice](../yahoo-china-quote-evidence-2026-10-25.md)
retains one real price-only observation through neutral atomic ingestion and
source/batch reconstruction. Exact scope/clock checks and failure/tie handling
prevent guessed identities, backdating and old favorable fallback. It is not a
canonical daily close, market value, admitted Financial input or source promotion.
Decoded-not-wire and transport limitations stay explicit; 18/18 file checks are
not backup or truth verification. Share-class/unit/action/clock qualification,
source-aware financial/technical validation and other launch gates remain open.
The package stays ready, not accepted; no Paper/live authority is created.

The [provider-ingestion UTC repair](../provider-ingestion-utc-integrity-2026-10-25.md)
closes the equivalent folded-clock leak at the upstream neutral evidence boundary.
Child contracts, actual retrieval binding and completion are rechecked before
file/database publication; relaxed PIT cannot disable chronology or trust ceilings.
Existing source identities, schema and real data remain unchanged. A scoped
read-only chronology inventory finds no violations and 17/17 byte checks pass,
without source/trust/strategy qualification or resolution of the quote outage.
This remains a partial hardening slice; the package stays ready, not accepted.

The [research-input UTC repair](../research-input-utc-integrity-2026-10-24.md)
closes a reproduced future DST-fold bar/context leak and incorrect revision
selection. UTC keys prevent repeated-clock version collisions; latest suspension
and valid same-instant representations are tested, including rejection before
SQLite run/report publication. Report/module versions change without schema or
old-row rewriting. This is scoped research integrity, not global PIT certification,
source qualification, strategy validation or package acceptance. HTTP_502 and
remaining data/runtime gates stay open; this package stays ready, not accepted.

The [market-value research binding](../market-value-research-binding-2026-10-24.md)
repairs omitted consumed-bar identity, introduces explicit separate freshness
limits and passes diagnostics through the official Financial report/SQLite
features. Context cutoff/mutation/equity checks, latest suspension and incomplete
InvestmentAssessment boundaries are tested. Retained real quotes remain HTTP_502;
illustrative age checks flag stale bars without promoting source/valuation trust.
No real queue, schema migration, score or trading authority is invented. Obtain
permitted numeric/source-qualified inputs and complete remaining sector/strategy/
runtime validation. The package stays ready, not accepted.

The [market-value slice](../market-value-inputs-2026-10-23.md) adds response-body
capture, neutral persistence, source reconstruction and matching diagnostics.
Prefetch fixes ingestion cutoff chronology without relaxing strict PIT; failed
HTTP responses remain audited UNAVAILABLE captures, not numeric coverage. Native
units, quote-clock semantics, share-class/FX/action context, independent source
calibration and official sector valuation admission remain open. No PE/PB/PS,
score or trading authority is introduced. The package stays ready, not accepted.

The [annual/trailing slice](../trailing-financial-inputs-2026-10-23.md) populates
two real annual facts and adds exact receipt/review-bound calendar-YTD arithmetic
to existing Financial report/CLI diagnostics. Factory defaults grant no review;
late/changed/missing/ambiguous inputs cannot authorize old or synthesized results.
No interim annualization, trust/scoring upgrade or market value is introduced.
Independent accounting/edition review, dated market value, source/sector policy
and actual strategy validation remain open. This package stays ready, not accepted.

The [valuation-basis slice](../valuation-basis-inputs-2026-10-23.md) supplies a
signed parent-equity observation and unscored denominator diagnostics to the
existing Financial module/combined reader. Interim profits/revenue cannot be
annualized or silently treated as TTM, and total assets/minority equity cannot
replace parent book. Missing market-value inputs remain explicit; all multiples
stay uncomputed. Old packets, schema and disabled defaults remain intact. Dated
market-value/annual-or-TTM evidence, independent review, sector scoring and real
strategy validation remain open. This package stays ready, not accepted.

The [evaluation-cutoff repair](../research-assessment-cutoff-2026-10-23.md) rejects
cached module results evaluated at a different decision instant, including in
condition-free reports and separate policy wrappers. Shared UTC checks handle
DST folds and future child evidence. SQLite regressions retain failed-run audit
and a pending queue item but no report/signal publication. This binds logical
evaluation clocks, not original consumed input truth or freshness; do not simply
retimestamp a cached result. Data/strategy/runtime gates remain open and this
package stays ready, not accepted.

The [cash/balance input slice](../nonfinancial-cash-balance-2026-10-22.md) adds
five real 002624 source observations and reusable same-filing ratios/exact cash
reconciliation to existing financial/report diagnostics. Missing/ambiguous/
rejected inputs do not select older favorable data; component inconsistencies
withhold the cash ratio. Liabilities are not inferred interest-bearing debt and
monetary funds are not unrestricted cash. Financial scoring, historical/source
qualification, valuation and remaining runtime/launch gates remain open. This
package stays ready, not accepted; no Paper/live authority is created.

The [nonfinancial ROE input](../nonfinancial-roe-inputs-2026-10-22.md) supplies
a source-bound current YTD weighted percentage without annualization, money
scaling or generic aliases. One real 002624 observation joins existing technical/
financial diagnostics; v1-v4 source packet identities and old cutoffs remain
intact. ROIC/valuation, independent source/basis review and an admitted sector
scoring/validation policy remain missing. This scoped input repair does not
complete this package or bypass any runtime, Paper or live acceptance gate.

The [SSE symbol-scope repair](../sse-pilot-symbol-scope-2026-10-22.md) prevents
STAR/B-share/BSE/SZSE/fund and malformed symbols from receiving main-board
calculations merely through SSE metadata. All four calculation paths share the
check; runtime inventory retains the record and reports a scope gap. Existing
calendar/status/phase/evidence checks remain required. Calculation/runtime
versions change without rewriting old records or schema. This is not listing
authentication or acceptance of this package; financial/strategy validation and
remaining runtime gates stay open.

The [shared research score repair](../research-evidence-admission-2026-10-20.md)
closes unknown-number, duplicate-name and incomplete-rubric scoring in the
Policy/Industry/Value helper, retaining original annotations and requiring
complete declared numeric input. Incomplete report/InvestmentAssessment and
SQLite propagation are tested. This does not authenticate caller quality/source
truth, admit Financial scoring, change technical formulas or complete launch
gates. Next: reviewed source/sector inputs and remaining runtime gates.

The [bank research-input policy](../bank-research-input-policy-2026-10-19.md)
adds typed, hashed gaps/age diagnostics, effective Settings/factory wiring and
read-only CLI export. Four real current metric names remain unqualified and
five are missing from the canonical query. Unconfigured freshness is UNASSESSED;
old rejected/ambiguous inputs cannot be replaced by a favorable fallback.
Source data/schema/live defaults are unchanged; no investment score or report
is created. Next: independently reviewed missing bank definitions, freshness
and valuation inputs plus the outstanding runtime/policy gates, not trading.

The [financial admission repair](../financial-scoring-admission-2026-10-19.md)
now closes the evidence-only financial scoring fallback in the primary working tree.
No-source, unrelated-number and self-authorized annotations stay unscored;
existing report/InvestmentAssessment boundaries preserve incompleteness and
SQLite persistence retains evidence. Exact patch baselines were verified and
the normal approval succeeded; this is not package or deployment acceptance.
Next: bank input policy and
the remaining runtime/policy gates. No Paper/live acceptance is implied.

The [bank ratio input slice](../bank-financial-inputs-2026-10-19.md) adds two
source-bound LOW/retrieval-time group period-end observations, with explicit
percent/null-currency/basis semantics rather than monetary scaling. V1/v2
identities survive; monetary comparison and financial scores remain unavailable
for these ratios. Exploratory totals: eight facts and 11 verified artifacts.
Next: an explicit bank research-input/sector-policy contract and remaining
runtime/policy gates, not readiness promotion or execution. This package remains
in progress; no Paper/live gate is accepted by this slice.

The [same-filing comparative slice](../financial-comparatives-2026-10-19.md)
adds three retrieval-time comparative observations without rewriting v1
identities, plus exact source-bound descriptive changes. Filing-edition,
period, unit/scope and source mismatches remain blocked; nonpositive baselines
do not imply percentage growth. Financial research stays unscored and no
original historical revision or readiness is claimed. Next: explicitly sourced
bank-appropriate observations/units and sector research/scoring policy, while
continuing the outstanding runtime/policy gates below.

The [financial input reader](../financial-source-inputs-2026-10-19.md) now
reconstructs source-bound diagnostics with exact fact/evidence/artifact/batch
checks and immutable context binding. Rejected observations remain visible;
completed recorded batch chronology must precede the cutoff. Financial inputs
do not authorize their own scoring, including with positive numeric evidence.
Three real LOW observations bind; four requested gaps remain explicit, and
generic financial fields are not a qualified bank policy. Next: comparable
periods/relevant metrics and a reviewed sector-aware research/scoring policy.
This slice does not complete this package or any Paper/live acceptance gate.

The [dedicated issuer-filing extraction](../reviewed-filing-facts-2026-10-18.md)
now publishes three LOW/retrieval-time observations in the exploratory fact
table with atomic review-packet/evidence/audit lineage. It bypasses unproved
native mappings by using separate manually reviewed issuer annotations, not
by approving the earlier spot report. No score/replay/validation promotion
occurs. Next: typed source-bound/sector-aware research consumption and more
reviewed periods/metrics, alongside outstanding runtime/policy gates below.

The [financial source corroboration](../financial-source-corroboration-2026-10-18.md)
adds three retained issuer PDFs and a read-only partial numeric-review boundary.
Three bank/group/CNY-million values match explicit native-scale hypotheses;
unit/currency/scope/revision mapping is not approved. Review availability is
capture/review-bounded and no facts, scores or validations are populated. Next
is independently evidenced accounting mappings and sector applicability, not
Paper or live promotion. New captures are not in the earlier encrypted backup.

The [encrypted same-host recovery](../encrypted-recovery-2026-10-18.md) now
retains both real databases, eight registered files and five explicit rule
captures on the existing verified encrypted volume. A rejected first attempt
exposed current-schema metadata rewriting; restore now skips needless init and
compares logical content. This is not independent-host/cloud synchronization,
schema-transition full-content verification or acceptance of this package.

The October 18 [reviewed local baseline](../reviewed-baseline-2026-10-18.md)
consolidates the eighteen continuation slices. This is a recoverable code
checkpoint, not acceptance of this package, remote CI, encrypted recovery,
source trust or Paper/live readiness. The historical slice reports retain
their original per-slice verification and checkout-state observations.

- [Research bar integrity](../research-bar-integrity-2026-10-18.md) fixes duplicate
  warm-up, same-observation revision selection, direct-entry context checks and
  Technical N-interval returns/window requirements. Shared input checks reject
  ambiguous/adjusted/nonfinite daily series without deleting raw observations.
  This is not source/session authentication or a launch acceptance pass.

- [Native dependency baseline](../dependency-baseline-2026-10-18.md) adds
  hash-checked native runtime/dev/build locks, exact version drift checks and
  a resolver-report compiler. A fresh venv installation and quality suite now
  supplement the initial reused-dependency smoke test. Scope is macOS arm64 /
  CPython 3.12 / macOS 14+ only; jsonpath source build is explicit. No signing,
  independent target-host, Paper or live acceptance is claimed.
- [Offline deployment preparation](../research-deployment-runbook.md) adds an
  installed research console command, explicit-root configuration and read-only
  host preflight. Runtime/checkout/committed Python bytes must agree; clean Git,
  safe settings, governance and SQLite integrity remain required. Local wheel
  installation was exercised outside checkout; CI smoke checks are configured,
  not yet remotely run. No data, Paper, sandbox or live readiness is promoted.
- [Research input integrity](../research-input-integrity-2026-10-18.md) rejects
  mixed instruments/metrics, future queue/metadata/periods and ambiguous fact
  versions before a run starts. Latest financial diagnostics use period and
  visible revision, not tuple order, with explicit units/trust/precision. This
  does not authenticate accounting semantics or freeze all nested input data.
- [Fundamental fact integrity](../fundamental-fact-integrity-2026-10-18.md)
  rejects silent same-hash semantic conflicts and conflicting batch/concurrent
  writes. Savepoints preserve atomic calls inside caller transactions; new
  explicit versions preserve PIT history. This does not validate native metric
  semantics or authenticate source timing, and legacy facts remain unaudited.
- [Financial numeric hardening](../financial-numeric-hardening-2026-10-17.md)
  repairs legacy zero/nullable/alias handling and rejects inconsistent values
  atomically. It does not resolve unreviewed metric/unit/period semantics or
  convert native observations into eligible fundamentals. Complete the
  evidenced mapping checklist before canonical financial population.
- [Exploratory data expansion](../exploratory-data-expansion-2026-10-16.md)
  adds real 187-date price history and 13,000 native statement observations in
  a separate research database, plus 30 bounded direct CNInfo metadata rows.
  Neutral snapshot capture retains unknown units and retrieval-time values;
  no canonical financial/research/validation completion is claimed. Original
  operational data is unchanged. Next: reviewed metric/unit mapping and source,
  status, universe and action coverage, not direct paper/live enablement.
- The [real SSE coverage manifest](../sse-pilot-coverage-2026-10-16.md) now
  inventories scoped runtime and research inputs in one read-only snapshot.
  The real sample retains six price dates, a 15-bar configured-count deficit
  and 21 requirement codes without favorable inference or readiness promotion.
  Next: extend exploratory history/current financial capture through existing
  ingestion, not backdated historical eligibility. Source time and scoped-
  empty/global-table distinctions remain explicit.
- [Research-content binding](../replay-research-binding-2026-10-16.md) now pins
  full report/evidence/policy contents and visible input inventories in replay
  hashes; nested defects block eligibility without hiding diagnostic samples.
  Request creation rechecks content, derived fields, query cutoffs and manifest
  membership. Evidence writes are immutable/idempotent. Original consumed-input
  and raw-provider provenance remain open; next is a real pilot coverage manifest.
- The [exact outcome/immutable replay slice](../replay-outcome-integrity-2026-10-16.md)
  replaces first/last fallback with exact UTC calendar endpoints, horizon/lag
  checks and separate start/outcome visibility. Bound prices are independently
  recomputed at ValidationRequest creation. Immutable manifest-owned sample
  publication is atomic and idempotent; old results are not rewritten. Full
  original-run input binding, exchange-session/action-aware returns and
  authenticated source coverage remain open. No Paper/live work is enabled.
- The [replay status slice](../replay-status-review-2026-10-16.md) binds original
  status and shared review to replay hashes and blocks unreviewable status at
  both replay confidence and ValidationRequest creation. Valid adverse status
  is preserved without a missing-input penalty. One reconstruction snapshot
  and atomic report/sample writes prevent mixed reads and stranded manifests.
  Full source validity and outcome coverage remain open; the subsequent slice
  above repairs new replay publication identity/immutability.
- The [shared lifecycle usability review](../lifecycle-usability-review-2026-10-16.md)
  gives runtime v1.6 and timeline coverage one structural review policy. It
  preserves original records and distinguishes observation-only from logical
  quarantine, excludes wrong-scope/invalid records from scoring, and uses the
  weakest retained trust instead of averaging lifecycle trust upward. This is
  not raw artifact authentication or complete downstream quarantine enforcement.
- The [suspension repair](../suspension-evidence-repair-2026-10-16.md) disables
  the delisted-quote endpoint misused as a current suspension list and removes
  forecast/end-date resumption inference, including AKShare calibration.
  A real dated capture now archives 13 LOW/retrieval-time reported starts and
  source frames atomically; no current status or confirmed resumption is
  created. Runtime v1.5 retains lifecycle observations with explicit legacy
  and coverage gaps. ST/phase/complete status and resumption proof remain open.
- The [ordinary SSE calendar slice](../sse-calendar-plan-2026-10-16.md)
  adds a separate rule-backed schedule, not canonical TradingSession writes.
  A verified annual source and all 46 explicit claims are required; original
  rule capture and bounded raw-byte checks preserve source integrity. Missing,
  future, conflicting or expired inputs remain unknown. Runtime v1.4 retains
  raw gaps and does not promote the derived plan into calculation authority.
- The [price-evidence slice](../daily-price-evidence-2026-10-16.md) now saves
  unadjusted AKShare equity/index rows and exact source/raw-snapshot evidence
  through one neutral ingestion transaction. Original cache serialization is
  retained and checked; artifacts must reconstruct normalized rows exactly.
  Runtime v1.3 exposes exact previous-close matches without promoting LOW
  trust or claiming current artifact verification. The real six-row primary
  capture preserves all earlier fallback observations. Price binding exists;
  independent source/runtime review is still incomplete.
- The [official SSE notice slice](../sse-calendar-notice-evidence-2026-10-16.md)
  captures 14 explicit dates and raw bytes through the existing neutral path.
  Typed MarketDataService reads expose these records in the same runtime
  snapshot. Missing days are not filled; conflicts and review expiry are
  preserved. The real sample has MEDIUM/retrieval-time evidence, not complete
  calendar provenance; reader version advances to v1.2 without schema changes.
- The prerequisite provider-neutral evidence gate now rejects every trust
  promotion above a declared capability, including LOW-to-HIGH, for both
  records and artifacts. Capability provider identity is checked before fetch;
  trust checks run before artifact publication or SQLite writes, even with
  relaxed PIT mode. Fifty trust-matrix cases plus identity/relaxed-PIT tests
  cover this repair. It does not supply missing runtime provenance or
  authenticate a provider's self-declared ceiling. Existing stored rows are
  unchanged and need an explicit provenance audit (`R-036`, `TD-037`).
- The [project-wide audit](../architecture-audit-2026-10-15.md) records the
  current fixes, residual risks, dependency map, and continuation plan.
- Portfolio and Risk factories read the same effective Settings; candidate
  sector/country/theme classifications are preserved. Model versions advance
  to `v0.7.1` so old results cannot silently acquire corrected semantics.
- Authoritative portfolio reconstruction and lineage checks use one read
  snapshot. Risk inputs reject unnormalized or duplicate position sets, and
  acceptable risk cannot carry unresolved breaches or required adjustments.
- Versioned market-rule evidence coverage is implemented with exact
  market/exchange/board/account scopes, PIT visibility, half-open effective
  intervals, trust checks, deterministic hashes, and ambiguity rejection.
  The [SSE main-board pilot](../sse-main-board-pilot.md) now adds reviewed,
  hash-verified official source capture and dated ordinary-equity calculations.
  A read-only runtime inventory now reads stored calendar/security/close/action
  inputs through MarketDataService in one snapshot and reports exact gaps.
  It preserves closed dates, low trust and exceptional statuses; it cannot
  manufacture trusted context, normal-listing status or action-free flags.
  Reviewed runtime provenance, account readers and full simulation integration
  are still absent. The default local business database was missing in the
  October 16 inspection; no database was initialized for this diagnostic.
- The [subsequent real sample](../operational-data-sample-2026-10-16.md) now
  populates that operational path through the existing pipeline. New market
  ingestion uses actual retrieval visibility, preserves company metadata and
  unknown turnover, and rejects silent success when normalization accepts no
  rows. Matched publication metadata cannot backdate numeric values. Source
  corrections do not authenticate legacy rows; reviewed context remains open.
- The [corporate-action repair](../corporate-action-mapping-2026-10-16.md)
  now maps the 26-row real payload to 33 research events using corroborated
  units, provider implementation labels and explicit ex-dates. Row rejections
  and event counts are transactional audit data. Same-key conflicts reject
  writes; cached replay inserts zero duplicates. Legacy units are not migrated
  and all new actions stay LOW/RETRIEVAL_TIME; this is not coverage completion.
- Portfolio candidates and proposals carry typed, persisted ResearchReport,
  InvestmentAssessment, InvestmentScore, and ValidationReport lineage.
- Repository writes verify authoritative identity, status, value, timestamp,
  configuration hash, and validation model version before saving the proposal
  and its children in one transaction. Reusing a proposal identifier is rejected
  rather than silently replacing persisted evidence.
- Conditional validation and low-confidence investment assessments cannot
  produce an unconditional proposal.
- A read-side PortfolioEvidenceGate rechecks authoritative lineage at the
  decision timestamp, with an explicit age/version/configuration policy and
  deterministic policy hash. Passing this structural check is not Paper or
  live-trading authorization.
- The policy can now be constructed from effective project settings. The
  checked Portfolio and Validation model versions come from their settings;
  age limits and the Risk model version are explicit configuration. The
  validation configuration hash is empty by default, so this construction
  fails closed until a reviewed run hash is pinned in an override. Changing
  the pinned hash changes the deterministic policy hash and requires review.
- Cash remains visible in exposure reports but no longer breaches sector,
  country, or theme concentration caps merely because it is a large buffer.
  Existing proposals and RiskAssessments are not rewritten; they need new
  proposal identities and fresh verification before future simulation use.
- A-share sellability and price-limit calls now fail closed when dated rule
  evidence is absent.
- US, Hong Kong, and Malaysia sellability and price-limit calls also fail
  closed. Their former same-day-sell and unrestricted-price defaults were not
  backed by account-specific settlement or effective-dated exchange evidence.
- All four markets' buy/sell quantity helpers now fail closed too. The former
  A-share buy helper could accept the generic Instrument default lot size of
  one, and the global helpers rounded with an unverified stored lot size.
  These context-free helpers remain disabled. The separate typed SSE pilot
  requires verified reference documents and dated runtime evidence; its
  calculation output cannot authorize a simulated quantity by itself.
- Remaining before this package can complete: review and pin an authoritative
  validation configuration hash, supply reviewed runtime pilot inputs and
  remaining intraday/cost restrictions, and bind the structural check and
  exact calculation hashes to the future simulation-intent boundary.
  No simulation or live trading is authorized by this partial slice.

## Objective

Remove the known authority, lineage, and market-rule gaps that would make even
Paper Trading misleading, while preserving the live-execution freeze.

## Next bounded implementation

1. Retain and extend the corrected real corporate-action sample without
   treating supported positive events as full coverage. Unsupported syntax,
   legacy units and issuer confirmation remain explicit gaps. Do not
   substitute monitor history or fixtures for operational inputs.
2. Add independently reviewed exchange-calendar and price-source provenance
   through the existing provider-neutral evidence/artifact contracts.
   Legacy TradingSession and Bar rows lack complete provenance bindings. The
   partial notice alone cannot compose ordinary days. A separate annual-notice
   and weekday-rule builder now reconstructs the ordinary schedule; actual
   exceptional closures and independent price review remain open.
   New unadjusted prices now carry exact raw-snapshot bindings; legacy rows
   cannot inherit them merely from equal closes.
3. Establish dated listing-phase and corporate-action coverage evidence.
   No matching event is not evidence of no event; LISTED is not normal phase.
   Partial suspension source capture now exists, but does not establish current
   status or complete ST/resumption/phase coverage. Audit retained legacy
   suspension snapshots, inferred resumptions and calibration outputs before
   considering them eligible evidence.
   Shared runtime/coverage review now exists; immutable originals and reports
   still need full provenance reconstruction, and unadapted raw readers must
   not treat a structural review result as historical validation approval.
4. Add read-only account-lot and confirmed-settlement provenance only within
   approved package boundaries, then bind verified inputs to calculation
   hashes. No broker connection or paper ledger belongs to this inventory.
5. Complete the existing intraday/cost, policy and simulation-boundary gates.

The repeatable diagnostic is `scripts/inspect_sse_runtime_inputs.py`; see the
pilot document for explicit arguments and exit-code semantics. Its input hash
identifies reconstructed content, not the entire database or a readiness pass.

## Dependencies

October 18 portability hardening adds a bounded read-only provider-artifact
registry/file audit. Both operational and exploratory registries verify 4/4
files against their different explicit roots. This does not complete encrypted
backup, independent-host recovery, full capture inventory or any acceptance
gate. See `docs/artifact-portability-2026-10-18.md`. Schema and PIT are unchanged.

- `WP-VALIDATION-001`: historical replay data-quality eligibility gate

## Scope

- Replace free-form validation status strings with versioned domain states.
- Preserve ValidationReport identities from PortfolioCandidate through
  PortfolioProposal and RiskAssessment.
- Verify identity, status, version, freshness, and configuration binding before
  creating any downstream simulation intent.
- Introduce effective-dated market-rule capability declarations.
- Fail closed when exchange calendar, settlement, board, suspension, ST, or
  price-limit evidence required by a market is unavailable.
- Keep `ExecutionDisabledGuard` authoritative for every live OrderFactory and
  Broker entry point.

## Acceptance Gates

- Conditional or unreliable validation cannot be interpreted as accepted.
- Artifact identifiers alone are insufficient; repositories must verify the
  referenced record and state.
- A-share placeholder T+1 and price-limit logic cannot authorize simulated or
  live execution.
- Tests cover stale, missing, mismatched, conditional, and rejected evidence.
- No live credential, live order, or broker submission path is introduced.

## Non-Goals

- No live trading.
- No broker order submission.
- No automatic strategy promotion.
- No reduction in PIT or provider trust requirements.
