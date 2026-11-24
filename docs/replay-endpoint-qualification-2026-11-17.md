# Replay Endpoint Suspension And UTC Qualification

Work package: WP-LAUNCH-001. Status: ready, not accepted.
Scope: research price-outcome qualification, not a strategy, backtest or execution.

## Integer Duration Entry: November 22, Second Follow-Up

An offline direct call accepted a declared 31.5-day horizon and produced a price
success label. OutcomeDefinition annotations declare integer day windows, but
constructor comparisons and timedelta coercion did not enforce that contract.
This synthetic reproduction is not evidence of an actual owner or source error.

New replay outcomes use replay-outcome-v5-integer-duration-inputs. At evaluation,
the horizon must be an exact built-in int greater than zero, and availability lag
an exact built-in int at least zero. Bool, fractional/whole floats, missing/textual
values, unsupported number objects and negative/zero-invalid inputs are rejected.
Duration construction or target/earliest datetime overflow becomes explicit
ValueError, not a returned outcome or a fallback/rounded window. No arbitrary
economic horizon cap, holiday/session substitution or holding-duration rule is set.
Valid integer UTC calendar-day endpoints, lag/maturity checks, threshold policy
and price/business-thesis separation remain unchanged.

Version binding gives v5 new query/manifest/sample identities. Stored v1-v4 rows
are retained unchanged and require reconstruction for current request admission;
no complete historical evaluator or automatic migration is implemented. This is
an evaluator-entry repair, not generic constructor, timezone, JSON or source
qualification. Rejection is neither a failed business thesis nor holding approval.

Added 32 synthetic cases: 22 defensive duration-field/type checks, one zero-horizon
check, six valid integer horizon/lag combinations, two datetime-range boundaries
and one extra legacy-v4 persistence/reconstruction case. Defensive tests explicitly
bypass/tamper construction; they do not claim every bad input passes the normal
constructor. Red-phase execution reproduced missing rejection. Related suites:
420 passed, 9.04 seconds. Full working-tree pytest: **4964 passed / 6 skipped**,
495.92 seconds. Ruff, mypy (324 source files), governance (189 checks), whitespace
and scoped known-pattern privacy/manifest/disabled-default checks pass. All 487
Python/config inputs retain the same before/after full-suite fingerprint:
e39aaf5151205dd0d6b69635f30404fc01e267395453f9d05b8df552b8ce4435.
Thirty-six pending paths remain, index empty and HEAD unchanged. Checks include
earlier pending work, not isolated candidate/release or source/method qualification.
Known-pattern screening is not full secret certification.

Authorized read-only AI static review found no confirmed in-scope issue. It
checked short-circuit types/signs, overflow handling, version isolation and test
scope; it did not execute tests or inspect real data. Defensive cases bypass
construction and legacy-tag tests are not complete old evaluators. Generic model,
JSON, timezone and source/strategy behavior remains outside scope. No reviewer
edits, network, real DB/raw/credential access, commits or pushes occurred.
No new schema/default/dependency/strategy,
execution/notification, real-data write/capture, commit/push or owner action;
ready, not accepted, PIT UNSUITABLE and production NOT_READY. H3 work stays parallel.

## Replay Threshold Types: November 22, Follow-Up

A separate replay-entry reproduction accepts success_threshold=True as numeric
one and produces a usable price value/success label with no blocker. The registry
repair does not cover this separate evaluator. This is synthetic evidence of an
input-contract defect, not proof of an actual owner result or source error.

New replay results use replay-outcome-v4-strict-threshold-inputs. Before endpoint
evaluation, thresholds must be exact built-in int/float values whose finite check
does not overflow. Bool, missing/textual values, unsupported Decimal objects and
overflowing integers raise ValueError without a returned outcome. No coercion,
zero fill or fallback threshold is introduced. Real float NaN/infinities retain
the existing invalid_success_threshold blocker and diagnostic bindings, with no
numeric value, success or invalidation label. Supported finite operands retain
all six comparisons and price-only NOT_OBSERVABLE business-thesis semantics.

This intentionally differs from the registry's all-invalid-operand exception
boundary: replay keeps its existing nonfinite-real diagnostic behavior. General
definition constructors, duration/window types and canonical serialization of
nonfinite declaration metadata are not hardened by this slice. No price/PIT,
source, thesis, strategy, holding, cash/portfolio or execution approval follows.

Central version binding separates v4 query/manifest/sample identities and current
request admission from stored v1/v2/v3 records. Old rows remain unchanged and
require explicit reconstruction; no old evaluator or automatic migration is added.
Legacy-tag tests exercise identity/persistence boundaries, not full old semantics.

Added 73 synthetic cases: six unsupported threshold kinds across six operators
(36), nonfinite-real blocking across six operators (18), valid nonzero floating
threshold comparisons below/at/above the threshold (18), and an additional legacy
v3 preservation/reconstruction case. Red-phase execution reproduced missing
rejection before the fix. Related suites: 388 passed, 8.65 seconds. Full
working-tree pytest: **4932 passed / 6 skipped**, 497.34 seconds. Ruff, mypy
(324 source files), governance (189 checks), whitespace and scoped known-pattern
privacy/manifest/disabled-default checks pass. All 487 Python/config inputs retain
the same before/after full-suite fingerprint:
a9fe429affa7682347ef1a8b3b8b5a861ae4d47670d1d929f59dd97303dd9fc5.
Thirty-six pending paths remain, index empty and HEAD unchanged. Checks include
earlier pending work, not isolated release validation or real source/method admission.
Known-pattern scanning is not full secret certification.

Authorized read-only AI static review found no confirmed in-scope issue. It
checked the guard, version binding, test counts and limits, not execution or real
data. Legacy-tag tests are not complete old evaluators; subclass/finite-extreme
inputs have no dedicated new cases. The constructor/duration/JSON/source gaps
remain explicit. No reviewer edits, tests, network, raw/database/credential access,
commits or pushes occurred.
No new API/schema/dependency/default, numeric strategy threshold or real-data
write/capture, commit/push; ready, not accepted, execution/notifications disabled,
PIT UNSUITABLE and production NOT_READY. H3 accounting/source review stays parallel.

## Price Versus Business Thesis: November 22

An offline regression reproduces a separate semantic defect: a usable price-only
return target automatically yielded SUPPORTED/INVALIDATED and the negation of
price success as invalidation_triggered. Thus price evaluation could populate the
business-thesis summary without evaluating a registered invalidation condition.
No actual owner loss, bad provider record or deployed validation result is proved
by this synthetic counterexample.

New results use replay-outcome-v3-price-thesis-separation. Numerical price change,
success comparison, endpoint blockers and original bindings remain unchanged.
Every price-only outcome now has thesis_status NOT_OBSERVABLE and
invalidation_triggered null, whether its price target succeeds, fails or is
unobservable. Explicit NOT_EVALUATED_PRICE_ONLY metadata/context explains the
scope; NOT_OBSERVABLE does not mean a usable price result is missing or failed.
Historical price-target validation can still resolve that sample, while the
existing ThesisValidationModule correctly has no resolved business-thesis sample
and no detection-rate claim. No new business/exit evaluator is implemented.

The existing centralized version binding gives v3 distinct query/manifest/sample
identities. Stored v1/v2 rows are retained unchanged and require reconstruction
before current request admission; no compatibility fallback rewrites their labels.
Legacy-tag tests emulate old identities, not a complete old evaluator. The bound
outcome verifier recomputes v3 and rejects forged favorable or adverse thesis
labels even when price endpoints and the price value are unchanged.

Added 23 synthetic regression cases: 18 operator/positive-flat-negative price
combinations, two replay-to-price/thesis module comparisons, two forged-label
checks and one additional legacy-v2 persistence/reconstruction case. Red-phase
execution failed on the old automatic SUPPORTED label before the scoped fix.
Related replay/validation tests: 189 passed. Full working-tree pytest: 4733 passed,
6 skipped, 490.83 seconds. Ruff, mypy (324 source files), governance (189 checks),
whitespace and scoped known-pattern privacy/disabled-default checks pass. All
487 Python/config inputs retain the same before/after full-suite fingerprint:
3781fb88423a9e915b5fc3030ca0c76fd24296004c17cd8055ec9f9928d3e335.
An authorized read-only AI static review found no confirmed in-scope issue. It
verified price/thesis consumer separation and current-version recomputation by
inspection, not real source admission. Module-separation tests call the modules
directly after building a replay request, not the full engine; legacy tests use
old version tags, not a full old evaluator. Existing full-engine tests also pass
but are not a new real-data qualification. Checks include earlier pending work,
not isolated candidate/release verification. Thirty-three pending paths remain;
the index is empty and HEAD unchanged. No commit, push or GitHub sync retry.
No new source capture, schema, strategy, thresholds, cash/portfolio policy,
execution/notification capability or live approval; PIT remains UNSUITABLE and
production NOT_READY. External supplied thesis labels, actual source-qualified
business outcomes and method/OOS validity remain separate unresolved work.

## Confirmed Counterexamples

Offline synthetic direct calls to evaluate_outcome returned a successful 20 percent
close change with a flagged suspended decision endpoint, outcome endpoint or both.
Flat carried prices could also generate a numerical outcome label. Retaining a
last close is useful for diagnosis but does not satisfy the new endpoint policy.
No actual owner result or provider record was demonstrated to be wrong by this
synthetic reproduction.

A second direct-call counterexample used New York's repeated November 1 01:30:
bar availability at fold 1 was one hour after a fold-0 decision cutoff, but native
datetime comparison treated them as equal and produced the same numeric outcome.
This was a direct evaluator defect; the existing bound-reader/request checks have
additional defenses and this audit does not claim every repository leaked it.

## Prior V2 Outcome Contract

On November 17, REPLAY_OUTCOME_VERSION advanced to
replay-outcome-v2-suspension-utc-endpoints. The price-only target metric and exact
UTC calendar-day window remain; no nearest-day/session or last-good fallback is
added. Changes are:

- An explicitly suspended decision/outcome bar contributes a named blocker.
  A nonboolean is_suspended is unknown/invalid, never coerced into False.
- Visibility compares observation, availability and cutoff as actual UTC instants.
  Availability before the observation adds a separate chronology blocker, even
  when repeated wall-clock labels passed the existing Bar constructor.
- Any blocker withholds numeric value, success and invalidation labels. The
  outcome is NOT_OBSERVABLE, not a negative assessment of the business research.
- Original endpoint contents and hashes remain in outcome_context, along with
  precise reasons and the explicit endpoint policy. Missing endpoints remain
  absent; suspended positive or unchanged closes are not replaced with zero.
- False suspension flags are necessary for this scoped calculation, not proof
  of actual trading, source correctness, full lifecycle/session coverage or fill
  availability. Existing source, calendar, action and execution limitations remain.

HistoricalReplayBuilder already preserves incomplete diagnostic samples and
binds outcome blockers to sample/manifest ineligibility. This slice reuses those
paths without dropping symbols or moving future outcome facts into decision
research. The direct bound-outcome verifier recomputes the same policy, rejecting
validly rehashed suspended bindings that still claim a favorable value.

Existing outcome_missing flags denote missing usable outcomes, not necessarily
missing raw endpoint records. This slice does not redesign missing-data scoring;
the raw bindings/reasons must be read with that flag. An adverse lifecycle status
alone remains distinct from a flagged unusable price endpoint and is not newly
filtered from the universe. No real PIT or source trust score is upgraded.

## Versions And Storage

The centralized outcome version participates in query hashes, dataset versions,
sample/manifest identities and ValidationRequestFactory checks. New v2 results
have distinct identities; stored v1 JSON, hashes and rows are not rewritten or
recertified. Old version-tagged results require explicit reconstruction before
current validation. There is no v1 evaluator fallback in the new code.

Synthetic compatibility tests emulate old version tags and persistence, not a
full old-code interpreter. They verify unchanged stored manifest/sample rows,
separate new identities and current-request rejection of the legacy version.
The research report contract, framework/schema/migration versions, replay/confidence
algorithms and database schema remain unchanged. No real database is migrated or
written by this delivery; all publication/revision exercises use temporary fixtures.

## Verification

New tests cover flagged/unknown suspension endpoints, positive and flat prices,
both endpoint positions, actual-UTC fold boundaries and chronology, equivalent
instants, incomplete sample persistence, deterministic retries, no nearby/old-good
fallback, omitted required-outcome fields, future suspension revisions, rehashed
bindings and synthetic legacy-version immutability/reconstruction.
The 155 replay tests pass, including 33 new cases. An owner-authorized read-only
AI reviewer found no actionable issue in the scoped evaluator/version/tests;
that was static review without tests, network, real databases or source approval.
Final stable-tree pytest: 4257 passed, 6 skipped (406.62 seconds). Ruff, mypy
(319 files), governance (179 checks), whitespace and scoped known-pattern privacy/
import/disabled-default checks pass. All 475 tracked/new Python/config inputs have
unchanged content fingerprints before/after that run. This does not certify
opaque secrets or unrelated/private data. Working-tree tests and scoped review
do not qualify an isolated release candidate or real data.

## Residual Work And Boundaries

Independent price/status/session/corporate-action evidence, lifecycle conflicts,
exchange-session-aware targets, total-return/cost policy, reconstruction-quality
versus missing-usable-outcome scoring and genuine technical/fundamental validation
remain open. No new Paper, Broker, Order, Portfolio, Notification or execution
logic exists. Execution and notifications remain disabled; PIT stays UNSUITABLE
and production NOT_READY. 271 definitions stay deferred. No commit/push occurs
in this slice, and engineering success cannot promote live trading.
