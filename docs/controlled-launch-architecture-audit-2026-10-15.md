# Controlled-Launch Architecture Audit (2026-10-15)

## Scope and decision

Reviewed the current 0.8.0 research platform, provider evidence and PIT gates,
historical replay, validation, portfolio/risk, market rules, persistence, and
disabled execution boundary. This is an engineering audit, not a return
forecast. The software may advance toward deterministic Paper Trading while
the provider-evidence horizon accumulates in parallel. PIT readiness remains
`UNSUITABLE`; neither paper results nor elapsed time authorize live capital.

## What is structurally sound

- Discovery, hard screening, research, investment assessment/score, validation,
  portfolio proposal, and risk assessment are distinct research stages.
- Dataset trust, availability precision, PIT readiness, replay warnings, and
  provider provenance are explicit rather than inferred from provider names.
- Schema checksums/fingerprints, backups, restore drills, CI governance, and
  default-disabled execution provide useful fail-closed controls.
- Portfolio outputs are research artifacts, not orders. Market regime remains a
  decision variable, not a unilateral trade switch.

## Prioritized findings

| Priority | Finding | Current control | Next acceptance gate |
|---|---|---|---|
| P0 | Historical security status, universe, disclosure time, and corporate-action evidence are incomplete; historical accuracy cannot be inferred from a successful replay. | Replay retains missing/low-trust warnings and PIT readiness is `UNSUITABLE`. | Independently reviewed dataset coverage, revisions, and provider consistency for the exact pilot inputs. |
| P0 | A-share T+1 and price-limit approximations were date-insensitive and could produce false paper fills. | `ChinaAShareRules` now rejects these queries without dated evidence. | Effective-dated exchange/board rules, trading-calendar and lot fixtures, suspension/ST checks, and historical rule-change tests. |
| P0 | Caller-supplied portfolio validation identifiers and status were insufficient provenance. | Proposal lineage is typed, persisted, checked against authoritative research/score/validation rows on save, and cannot be silently replaced; conditional evidence stays conditional. | Define validation-age policy and independently bind risk/proposal evidence at the eventual simulation-intent boundary. |
| P0 | A deterministic paper ledger and realistic fill/reconciliation model do not exist. | `WP-PAPER-001` is planned; live execution remains disabled. | Idempotent intent/fill/cash/fee ledger, market-session and stale-data gates, restart recovery, daily reconciliation, and fault-injection tests. |
| P1 | Portfolio weights are score/confidence heuristics using assumed volatility, liquidity, and correlation. | Proposal-only semantics and explainable RiskAssessment. | Calibrate costs, covariance, capacity, currency, lot sizes, and risk budgets on validated samples; prohibit treating proposed percentages as actual position size. |
| P1 | Future live readiness still relies partly on caller-provided identifiers and tokens. | `ExecutionDisabledGuard` and default-disabled configuration. | Separate future approval design with authoritative, short-lived, artifact-bound review; no live mode in this package. |
| P1 | Closely related technical indicators can produce false multi-signal confidence. | `WP-RESEARCH-001` is a documented reservation. | Version formulas, group evidence by family, test ablations, and require out-of-sample results before any score contribution. |
| P1 | Market/provider and broker behavior differs across US, Malaysia, Hong Kong, and China A. | Market-specific modules and provider contracts. | Select one pilot market and verify its calendar, currency, fees, corporate actions, permissions, and paper-account capabilities before broker sandbox work. |

## Accelerated delivery path

1. Finish `WP-LAUNCH-001`: versioned rule capability declarations, validation
   freshness policy, exact artifact identity, and negative-case tests. Preserve
   the existing disabled live boundary.
2. Implement `WP-PAPER-001` as an isolated, deterministic local simulator for
   one explicitly chosen market. Do not assume the user's Moomoo Malaysia or
   Guojin account includes any particular API or simulation entitlement.
3. Run shadow and paper observations with timestamped inputs, fees, slippage,
   rejected fills, reconciliation, and incident review. Continue scheduled
   provider evidence and backup/restore independently.
4. Reassess the pilot datasets and strategy separately. Require an explicit
   future authorization for any broker-native sandbox, and another distinct
   approval for micro-live. No automatic promotion is permitted.

The 84-day/eight-scheduled-check provider horizon is an evidence maturity gate,
not a ban on controlled software development. It also cannot be replaced by
quick paper wins. A short path to a working simulator is plausible; a reliable
date for autonomous live trading is not established by the present evidence.

## Residual verification

The new portfolio lineage checks are applied on repository write. Historical
portfolio rows without lineage do not gain provenance retroactively; they
require explicit migration/reconstruction or must remain ineligible for future
simulation. This audit does not claim that paper or live order submission is
implemented.
