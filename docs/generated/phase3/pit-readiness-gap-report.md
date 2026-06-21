# PIT Readiness Gap Report

Generated at: 2026-06-21T08:26:29.222166+00:00
Historical Replay reliable: **NO**
Future Paper Trading research reliable: **NO**

`best_case_after_dual_validation` assumes 100% cross-provider coverage and consistency while preserving current trust, availability precision, revision, and continuity evidence. It is not an observed result.

## Dataset Gaps

| Dataset | Current | Perfect-dual ceiling | Missing requirements |
|---|---|---|---|
| security_lifecycle | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>availability precision remains retrieval_time<br>historical continuity is 35.00, below the 80 target |
| st_status | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>availability precision remains retrieval_time<br>historical continuity is 50.00, below the 80 target |
| suspension_status | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>availability precision remains retrieval_time<br>historical continuity is 20.00, below the 80 target |
| delisting_records | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>availability precision remains retrieval_time<br>historical continuity is 55.00, below the 80 target |
| financial_publication_dates | unsuitable | usable | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>historical continuity is 70.00, below the 80 target |
| fundamental_revisions | unsuitable | usable | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>historical continuity is 55.00, below the 80 target |
| corporate_actions | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>availability precision remains retrieval_time<br>historical continuity is 55.00, below the 80 target |
| universe_coverage | unsuitable | caution | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>trust level remains low<br>availability precision remains retrieval_time<br>historical continuity is 25.00, below the 80 target |
| csi300_membership | unsuitable | unsuitable | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>trust level remains unknown<br>availability precision remains unknown<br>historical continuity is 0.00, below the 80 target<br>critical fields missing: primary_provider_data |
| csi500_membership | unsuitable | unsuitable | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>trust level remains unknown<br>availability precision remains unknown<br>historical continuity is 0.00, below the 80 target<br>critical fields missing: primary_provider_data |
| csi1000_membership | unsuitable | unsuitable | Tushare dataset capability is not_tested<br>cross-provider coverage is unmeasured<br>cross-provider consistency is unmeasured<br>trust level remains unknown<br>availability precision remains unknown<br>historical continuity is 0.00, below the 80 target<br>critical fields missing: primary_provider_data |

## Critical Next Actions

- Configure and validate TUSHARE_TOKEN permissions for every required endpoint
- Run date-aligned AKShare/Tushare comparisons across multiple periods
- Backfill dated history or collect forward snapshots until continuity is measurable
- Acquire announcement-time or effective-time evidence for retrieval-time datasets
- Do not treat dual-provider agreement alone as sufficient for Historical Replay
