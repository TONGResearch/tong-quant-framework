# Tushare Provider Capability Report

Generated at: 2026-06-21T08:26:29.222166+00:00
Environment: **NOT_CONFIGURED**
Credential source: environment only; credential value is never recorded.

## Endpoint Capabilities

| Endpoint | Status | Rows observed | Detail |
|---|---|---:|---|
| stock_basic | not_tested | N/A | credential validation did not permit a live probe |
| namechange | not_tested | N/A | credential validation did not permit a live probe |
| suspend_d | not_tested | N/A | credential validation did not permit a live probe |
| disclosure_date | not_tested | N/A | credential validation did not permit a live probe |
| income | not_tested | N/A | credential validation did not permit a live probe |
| dividend | not_tested | N/A | credential validation did not permit a live probe |
| index_weight | not_tested | N/A | credential validation did not permit a live probe |

## Dataset Capabilities

| Dataset | Status | Required endpoints | Missing endpoints |
|---|---|---|---|
| security_lifecycle | not_tested | namechange, suspend_d, stock_basic | namechange, suspend_d, stock_basic |
| st_status | not_tested | namechange | namechange |
| suspension_status | not_tested | suspend_d | suspend_d |
| delisting_records | not_tested | stock_basic | stock_basic |
| financial_publication_dates | not_tested | disclosure_date | disclosure_date |
| fundamental_revisions | not_tested | income | income |
| corporate_actions | not_tested | dividend | dividend |
| universe_coverage | not_tested | stock_basic | stock_basic |
| csi300_membership | not_tested | index_weight | index_weight |
| csi500_membership | not_tested | index_weight | index_weight |
| csi1000_membership | not_tested | index_weight | index_weight |

## Environment Warnings

- TUSHARE_TOKEN is not configured
