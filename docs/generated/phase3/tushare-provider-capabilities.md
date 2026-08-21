# Tushare Provider Capability Report

Generated at: 2026-07-03T03:15:17.289650+00:00
Environment: **READY_FOR_PROBE**
Credential source: environment only; credential value is never recorded.

## Endpoint Capabilities

| Endpoint | Status | Rows observed | Detail |
|---|---|---:|---|
| stock_basic | permission_denied | N/A | account permission is insufficient for this endpoint |
| namechange | permission_denied | N/A | account permission is insufficient for this endpoint |
| suspend_d | permission_denied | N/A | account permission is insufficient for this endpoint |
| disclosure_date | permission_denied | N/A | account permission is insufficient for this endpoint |
| income | permission_denied | N/A | account permission is insufficient for this endpoint |
| dividend | permission_denied | N/A | account permission is insufficient for this endpoint |
| index_weight | permission_denied | N/A | account permission is insufficient for this endpoint |

## Endpoint Diagnostics

| Endpoint | Required points | Exception detail |
|---|---|---|
| stock_basic | provider/account-tier dependent | 抱歉，您没有接口(stock_basic)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| namechange | provider/account-tier dependent | 抱歉，您没有接口(namechange)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| suspend_d | provider/account-tier dependent | 抱歉，您没有接口(suspend_d)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| disclosure_date | provider/account-tier dependent | 抱歉，您没有接口(disclosure_date)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| income | provider/account-tier dependent | 抱歉，您没有接口(income)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| dividend | provider/account-tier dependent | 抱歉，您没有接口(dividend)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| index_weight | provider/account-tier dependent | 抱歉，您没有接口(index_weight)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |

## Dataset Capabilities

| Dataset | Status | Required endpoints | Missing endpoints | Required points | Reason |
|---|---|---|---|---|---|
| security_lifecycle | unavailable | namechange, suspend_d, stock_basic | namechange, suspend_d, stock_basic | provider/account-tier dependent | namechange: permission_denied (account permission is insufficient for this endpoint); suspend_d: permission_denied (account permission is insufficient for this endpoint); stock_basic: permission_denied (account permission is insufficient for this endpoint) |
| st_status | unavailable | namechange | namechange | provider/account-tier dependent | namechange: permission_denied (account permission is insufficient for this endpoint) |
| suspension_status | unavailable | suspend_d | suspend_d | provider/account-tier dependent | suspend_d: permission_denied (account permission is insufficient for this endpoint) |
| delisting_records | unavailable | stock_basic | stock_basic | provider/account-tier dependent | stock_basic: permission_denied (account permission is insufficient for this endpoint) |
| financial_publication_dates | unavailable | disclosure_date | disclosure_date | provider/account-tier dependent | disclosure_date: permission_denied (account permission is insufficient for this endpoint) |
| fundamental_revisions | unavailable | income | income | provider/account-tier dependent | income: permission_denied (account permission is insufficient for this endpoint) |
| corporate_actions | unavailable | dividend | dividend | provider/account-tier dependent | dividend: permission_denied (account permission is insufficient for this endpoint) |
| universe_coverage | unavailable | stock_basic | stock_basic | provider/account-tier dependent | stock_basic: permission_denied (account permission is insufficient for this endpoint) |
| csi300_membership | unavailable | index_weight | index_weight | provider/account-tier dependent | index_weight: permission_denied (account permission is insufficient for this endpoint) |
| csi500_membership | unavailable | index_weight | index_weight | provider/account-tier dependent | index_weight: permission_denied (account permission is insufficient for this endpoint) |
| csi1000_membership | unavailable | index_weight | index_weight | provider/account-tier dependent | index_weight: permission_denied (account permission is insufficient for this endpoint) |

## Credential Diagnostics

- Token detected: True
