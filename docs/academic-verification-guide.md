# Academic Verification Guide

Scope: read-only research presentation and public synthetic reproduction.
This guide distinguishes software verification, source qualification and economic
validation. None substitutes for either of the others. No brokerage account,
holding annotation, AI response or paid data feed is required for the public checks.

## What Is General And What Is Demonstrated

| Layer | Current scope | What is not established |
| --- | --- | --- |
| Presentation exporter | Parameterized subject and US/HK/MY market, not MSFT-only | Arbitrary global ticker, listing or venue eligibility |
| Real local demonstration | Retained MSFT and NVDA observations, at different fixed cutoffs | Current prices, same-date comparison, complete exchange sessions |
| Public reproduction | Six synthetic flat/rising cases across US/HK/MY identity routes | Real HK/MY coverage, provider truth, market-rule calibration |
| A-shares and Japan | Not admitted by this particular exporter | A displayed overseas case does not certify other framework adapters |
| Investment conclusions | Not evaluated by the presentation | Profitability, validated hold/add/sell decisions or autonomous trading |

A generated page contains one frozen observation bundle. Its frequency controls
do not fetch or switch stocks. A different accepted subject requires a separate
export from an appropriate retained source. A syntactically accepted symbol is
not a dated listing record. No claim of "all stocks supported" is made.

## Supervisor Quick Check

The reviewed academic revision is
9407bdeca6cdf11a206e6a6d426c0755d7e7e336, with tree
5884ca61aecb6d4da267029217ea0788c1d791d9. The default branch need not contain it.
Use a new checkout so inspection cannot discard an existing developer's changes:

```sh
git clone --branch codex/wp-launch-001-hardening https://github.com/TONGResearch/tong-quant-framework.git tong-quant-academic-review
cd tong-quant-academic-review
git switch --detach 9407bdeca6cdf11a206e6a6d426c0755d7e7e336
git rev-parse HEAD HEAD^{tree}
```

The last command must print the commit and tree above before reproducing that
release's claims. Cloning requires repository access and a network connection;
checking out this revision does not provide private historical source artifacts.
Later revisions may add documentation or code and need their own scoped checks;
the recorded full-suite result must not silently follow a moving branch.

Use the reviewed branch containing this guide, not an older default branch.
Install Python 3.12 and the project's dependencies following the README. Initial
dependency installation can require internet access; the checks below do not.

```sh
python scripts/verify_academic_reproduction.py --output verification.json
python -m pytest -p no:cacheprovider tests/test_academic_verification.py tests/test_academic_showcase.py
python scripts/check_project_governance.py
```

The verification command reports CHECKS_PASSED only when every declared check
passes; it exits 1 on a failed check. Existing output files cannot be overwritten.
It records Python/pandas/framework versions. A report hash identifies its own
content, not trusted provenance. Same-environment repetition is tested; numerical
reference checks use an explicit absolute tolerance of 1e-9. Cross-version or
cross-platform byte equality is not promised.

The fixture subjects TQDEMO, 0000.HK and TQDEMO.KL do not assert real listings.
Each has 96 synthetic civil-day observations, deliberately not an exchange calendar.
The fixed research cutoff is 2026-11-15T09:00:00Z. No original provider envelopes,
real raw-data hash, publication history or trading-session qualification is faked.

## Independent Numerical References

The implementation under test is academic_showcase -> existing checked selectors
and technical/calendar functions. The separate reference in academic_verification
uses standard-library Decimal arithmetic at precision 50, not production indicator
functions or pandas. It checks the configured default conventions, not every
parameter or indicator implementation on arbitrary data.

- Flat fixture: open/close 20, high 21, low 19. SMA5/10/20 = 20; MACD DIF/DEA/
  histogram = 0; K/D/J = 50.
- Rising fixture: close c[t] = 20+t, t=0..95; high=c+1, low=c-1. Last SMA5=113,
  SMA10=110.5, SMA20=105.5, obtained from arithmetic means of the last observations.
- EMA uses the first close as its initial value and recursively applies
  EMA[t]=EMA[t-1]+2/(n+1)*(c[t]-EMA[t-1]). DIF=EMA12-EMA26; DEA is the same
  first-value recurrence with span 9 over DIF. Histogram=DIF-DEA, not twice that.
- KDJ uses a 9-observation range, initial K=D=50 and smoothing divisors 3/3.
  For a rising sample of n observations, RSV=90 throughout its u=n-8 updates.
  With q=2/3: K=90-40*q^u; D=90-40*q^u*(1+u/3); J=3*K-2*D.
  Check n=10,11,12 as well as 96; short samples expose initialization/smoothing
  errors hidden by endpoint convergence. A fault returning RSV directly instead
  of smoothing must fail, even though the 96-row endpoint would appear correct.
- Production warm-up still applies: MACD requires 35 observations and KDJ 10.
  A yearly value is not manufactured from 96 daily rows.

Fault injection changes a computed DIF by +1 and requires CHECKS_FAILED. This
tests whether an independent reference can detect a wrong result, not whether
two copies of the same production function agree.

## Fail-Closed And Identity Checks

Each case additionally checks same-environment repeatability, subject/market
identity, absent yearly history and false execution authority. Stale, missing
and latest-suspended inputs must expose no old usable chart or indicator output.
Pytest separately rejects mixed-subject inputs and nonboolean fixture modes,
forbids network connection and retained-source reads in the public protocol, and
checks the CLI's no-overwrite behavior. The existing presentation suite covers
future visibility, duplicate versions, cutoffs, XML input, escaping and safety.
Passing these cases is scoped engineering evidence, not exhaustive correctness.

## Inspecting The Real Demonstrations

MSFT uses 971 daily rows with cutoff 2026-11-15T09:13:45.007947Z; NVDA uses 752
daily rows with cutoff 2026-11-08T09:18:31.925654Z. Both remain LOW/retrieval_time,
provider-native/unverified. They were captured at different times and cannot be
ranked as contemporaneous opportunities. Full-year history can be insufficient.

The source DB and raw artifacts are local and not on GitHub. A teacher can audit
the public code and synthetic references immediately, but cannot independently
authenticate the private retained observations merely by opening the HTML or
checking its displayed hashes. An authorized, separately licensed source bundle
or an independently obtained equivalent sample is required for that next step.
A fresh download is a new vintage, not a reproduction of the old capture.

Use the README exporter with an explicit subject, market, cutoff, age limit,
existing DB/artifact root and new output path. No original source is rewritten.
Generated HTML can contain historical market data; review redistribution rights
before publishing it. Account/holding data must never accompany a review bundle.

## Research Evaluation Still Required

The current evidence supports implementation-level questions about reproducible
computation, temporal rejection, identity isolation and explicit missingness.
It does not establish profitable prediction, novelty or an approved FYP topic.
An economic study would separately require qualified multi-instrument data,
predeclared strategy/parameters, chronological out-of-sample splits, baselines,
survivorship/revision controls, transaction costs and uncertainty/sensitivity
analysis. No return, win rate, Sharpe ratio or drawdown is invented here.

Live execution remains disabled. The proposed academic scope is a reproducible,
evidence-aware equity-research workbench, not a proven automated money-making system.

## Review Checkpoint

The following paragraph describes the pre-publication checkpoint; the completed
release record is in the next section. Its pending wording is not a current gate.

The two focused academic suites pass 73 cases; Ruff, mypy (328 files), whitespace
and all 189 governance checks pass locally. Independent static review of the
15-file academic scope and follow-up closed the adjustment-provenance and
convergence-only KDJ-reference findings, plus prior JUnit/path hardening. The
reviewer ran no tests, real-data/browser/network operations or Git mutations.
Exact isolated-candidate release checks remain a separate gate at this checkpoint.
Do not transfer an old full-suite record to later edits or claim independent
verification of private source bytes from this code review.

## Completed Release Record

The pinned commit above records the exact isolated 15-file candidate verification:
5327 pytest cases passed, six skipped, zero failures/errors, 649.23 seconds;
Ruff, mypy (328 files), all 189 governance checks, whitespace/privacy preflight
and independent complete-candidate static review passed. Packaging evidence is
an offline wheel build and imports/resource access from its unpacked contents,
not a fresh isolated dependency installation or an independent-host test.

The original local JUnit record fingerprint is
acb52c201f1436c9eff76d084de955792b8a01cee729b8fc2c51742156185f09.
The final presentation's anonymous derivative is
33f4ce721d84448793c823cedfdefc6e47134c50fe5fac492a3646d1a65971ce.
All 5333 case outcomes are preserved, with hashed case identities and the original
fingerprint retained in properties. The derivative fits the reader's existing
size bound; no test was dropped or reclassified to fit it. These local records
are not bundled in Git. Without the corresponding bytes, a reviewer can inspect
the public implementation and rerun checks but cannot authenticate these historic
execution records merely from the quoted fingerprints.

Do not mix these records with the earlier 5293-pass screenshot checkpoint. A new
test execution yields a new local record even when its outcomes agree. Nothing
in this publication accepts WP-LAUNCH-001, validates a trading strategy, admits
private source data or changes disabled execution/notification defaults.
