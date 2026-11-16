# Work Package: WP-DATA-004

Status: `completed`

Tong explicitly requested a reliable-data investigation and repair of 920982
on October 20. This slice adds optional bounded Sina SDK access diagnostics
and a separate raw Sina BSE price-observation adapter. It does not admit Sina
as a canonical price fallback, create orders or promote data readiness.

Delivered: retain original wire bytes, use the installed fixed decoder on parsed
data only, reject symbol/schema/OHLC/duplicate-date/size errors, avoid the SDK's
share merge/fill/rounding/deduplication, and persist LOW/retrieval-time evidence
through neutral ingestion. Actual 920982 capture: 674 selected observations,
112 outside the requested range. No guessed alias or canonical daily-bar write.

See docs/bse-price-source-repair-2026-10-20.md for source identities, limitations,
reconstruction and quality checks. Second-source, units, price-basis, code-history
and session coverage checks remain required. No schema or trading-module change,
no commit/push, and execution/notifications remain disabled.

Verification: 1392 passed / 6 skipped, Ruff/mypy/governance/diff checks pass;
offline reconstruction matches 674 records and artifact audit verifies 10/10.
