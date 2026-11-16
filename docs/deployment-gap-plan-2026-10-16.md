# Deployment Gap Plan: 2026-10-16

October 27 follow-up: this document retains the broad five-group trading roadmap.
For a proposed first read-only research-decision release and an explicitly
conditional effort estimate, see the
[six-group decision delivery plan](decision-delivery-plan-2026-10-27.zh-CN.md).
These are different scopes, not competing counts of prompts until live trading.
Consult PROJECT_STATUS.md for current source/data/checkpoint observations.

## Honest baseline

Tong Quant is a research/validation framework under controlled-launch
hardening, not a deployable autonomous trading system. Existing tests demonstrate
software invariants, not profitable strategies or realistic fills. The current
local operational sample has no persisted real ResearchReport, ValidationReport
or PortfolioProposal and no replay reports. Test fixtures do not fill this gap.

Execution and notifications are disabled, PIT UNSUITABLE, production NOT_READY.
Broker accounts being opened or software being installed does not establish
API entitlement, safe connectivity, permissions or reconciliation behavior.
No firm completion date or defensible "90% done" estimate exists yet.

October 18 operational slice: the installed research command and
[offline deployment runbook](research-deployment-runbook.md) now support
explicit-root startup, source/version/configuration checks and a read-only
database audit. Local wheel installation outside checkout is verified; source
changes are still uncommitted, so release preflight remains blocked. This
advances installation diagnostics only, not the Paper/broker/live gates below.

## Five Remaining Deliverable Groups

These are work groups, not five prompts or a promise about duration. Group 1
is in progress; strategy evidence can be developed in parallel where allowed.
Paper and broker packages keep their existing governance dependencies.

| Group | Remaining work | Evidence needed before advancing |
| --- | --- | --- |
| 1. Trustworthy launch inputs | Close status/phase/calendar/action/price/account provenance gaps; pin reviewed validation policy; repair replay identity and outcome alignment | Exact source/version/time binding, preserved unknowns, deterministic reconstructions, explicit coverage and no silent report replacement |
| 2. One validated strategy chain | Freeze one market/instrument scope and strategy specification; run Discovery, Screening, Research, InvestmentScore, Validation and Portfolio/Risk with actual eligible inputs | Reproducible real reports, predefined OOS/robustness criteria, no future leakage, transaction-cost/capacity assumptions, independent review; not just a high score |
| 3. Deterministic Paper Trading | Build persistent cash/position/event ledger, fill and cost simulation, duplicate protection, crash recovery and reconciliation | WP-LAUNCH-001 accepted and WP-PAPER-001 made ready; deterministic replay, market-rule failures, daily balances and restart tests; no live submission path |
| 4. Read-only/sandbox integration and deployment | Verify account/environment/API capabilities; test reconnect, environment separation, diagnostics, monitoring, backup/restore and operator controls | WP-PAPER-001 accepted and WP-BROKER-001 made ready; provider-native sandbox evidence, independent reconciliation, no trading-password persistence or live unlock |
| 5. Separately approved live rollout | Independently assess strategy/data/risk/operations and define explicit live scope, capital limits, manual approval, kill switch and rollback | New explicit human approval and reviewed live-readiness evidence; no automatic promotion from elapsed time, paper results or account availability |

Group 3 is the first meaningful trading-workflow milestone, but simulated
operation is not real-money readiness. Group 5 is a future separately approved
phase, not authorized work under this document. Portfolio remains proposal-only
until any later approved boundary exists; no asset allocation is authorized.

## Shortest Responsible Path

Continue the existing SSE ordinary-equity pilot first, one tightly specified
strategy and one account/environment at a time. This is an engineering scope
choice, not a stock-selection or capital-allocation recommendation. Keep the
shared core reusable, but do not wait for every global market and asset class
to be complete before delivering the first governed simulation workflow.

Retain the approved modified-Turtle requirements: breakout, volume, market
sentiment and industry heat all need explicit inputs and confirmation. ATR,
pyramid and trailing-stop research must not assume an executable price. A-share
settlement/sellability, quantity, price-band, suspension, cost and session rules
must be verified for their date/scope; they cannot be generic constants. Other
markets need their own separately verified rules rather than A-share defaults.

The provider evidence horizon runs alongside software development. It is not
a reason to stop approved engineering, but it cannot be fabricated or waived
to make historical validation or real-money readiness look complete. Narrowing
scope can reduce the evidence required; relabeling weak data cannot.

## Next Concrete Queue

1. Exact UTC calendar endpoint coverage and price-content binding now reject
   missing/misaligned windows; immutable replay publication is repaired. Finish
   source authentication and explicitly scoped session/action-aware metrics
   before treating raw price changes as historical strategy returns.
2. Full reconstructed research/evidence/policy and visible-input content now
   enter replay hashes. Finish exact original-run input/source lineage (TD-040)
   without claiming the reconstructed row inventory proves original consumption.
3. The real-data [SSE coverage manifest](sse-pilot-coverage-2026-10-16.md) now
   pins dates/scopes/blockers. Next expand exploratory history/current financial
   capture, then complete reviewed inputs and pin policy hashes. Retrospective
   capture does not establish earlier availability.
   [Actual exploratory captures](exploratory-data-expansion-2026-10-16.md) now
   provide 187 price dates, 13,000 native financial observations and 30 limited
   disclosure metadata rows in a separate database. Next is canonical units/
   metric review and coverage proof; original operational readiness is unchanged.
4. Freeze one strategy specification and construct its real evidence chain;
   design paper ledger contracts in the approved package sequence.
5. Review/commit the accumulated local changes, then push only with permission;
   separately back up ignored source artifacts/business data for device recovery.

MooMoo/Guojin may supplement market-data inspection, but their screens have not
been verified as providers. No live order, login credential, API permission
expansion or subscription purchase is required for the current code repairs.
