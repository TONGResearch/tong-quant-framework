# Framework Data Readiness Dashboard

Generated at: 2026-06-21T08:26:29.222166+00:00
Overall: **UNSUITABLE**

## Dataset Readiness

| Dataset | Primary | Secondary | Coverage | Trust | Precision | Consistency | Continuity | PIT | Usage |
|---|---:|---:|---:|---|---|---:|---:|---|---|
| security_lifecycle | 1693 | N/A | N/A | medium | retrieval_time | N/A | 35.00 | unsuitable | Diagnostics only; exclude from historical claims |
| st_status | 1464 | N/A | N/A | medium | retrieval_time | N/A | 50.00 | unsuitable | Diagnostics only; exclude from historical claims |
| suspension_status | 25 | N/A | N/A | medium | retrieval_time | N/A | 20.00 | unsuitable | Diagnostics only; exclude from historical claims |
| delisting_records | 204 | N/A | N/A | medium | retrieval_time | N/A | 55.00 | unsuitable | Diagnostics only; exclude from historical claims |
| financial_publication_dates | 5189 | N/A | N/A | medium | date_only | N/A | 70.00 | unsuitable | Diagnostics only; exclude from historical claims |
| fundamental_revisions | 23 | N/A | N/A | high | exact | N/A | 55.00 | unsuitable | Diagnostics only; exclude from historical claims |
| corporate_actions | 25 | N/A | N/A | medium | retrieval_time | N/A | 55.00 | unsuitable | Diagnostics only; exclude from historical claims |
| universe_coverage | 5528 | N/A | N/A | low | retrieval_time | N/A | 25.00 | unsuitable | Diagnostics only; exclude from historical claims |
| csi300_membership | 0 | N/A | N/A | unknown | unknown | N/A | 0.00 | unsuitable | Diagnostics only; exclude from historical claims |
| csi500_membership | 0 | N/A | N/A | unknown | unknown | N/A | 0.00 | unsuitable | Diagnostics only; exclude from historical claims |
| csi1000_membership | 0 | N/A | N/A | unknown | unknown | N/A | 0.00 | unsuitable | Diagnostics only; exclude from historical claims |

## Framework Areas

| Area | PIT | Datasets | Gaps |
|---|---|---|---|
| Corporate Actions | unsuitable | corporate_actions | None |
| Fundamentals | unsuitable | financial_publication_dates, fundamental_revisions | None |
| Market Regime Inputs | unsuitable | universe_coverage, csi300_membership, csi500_membership, csi1000_membership | price trend, breadth, turnover, volatility, and relative strength are not calibrated here |
| Research Inputs | unsuitable | security_lifecycle, st_status, suspension_status, delisting_records, financial_publication_dates, fundamental_revisions, corporate_actions, universe_coverage, csi300_membership, csi500_membership, csi1000_membership | news, policy, and industry datasets remain outside Phase III |
| Security Lifecycle | unsuitable | security_lifecycle, st_status, suspension_status, delisting_records | None |
| Universe Membership | unsuitable | universe_coverage, csi300_membership, csi500_membership, csi1000_membership | None |
| Validation Inputs | unsuitable | security_lifecycle, st_status, suspension_status, delisting_records, financial_publication_dates, fundamental_revisions, corporate_actions, universe_coverage, csi300_membership, csi500_membership, csi1000_membership | market bars and outcome labels require a separate audit |

## Query Scope

- `security_lifecycle`: trade_date=20260619
- `st_status`: no parameters
- `suspension_status`: trade_date=20260619
- `delisting_records`: no parameters
- `financial_publication_dates`: period_end=20251231
- `fundamental_revisions`: end_date=20260621, start_date=20240101, symbol=600000
- `corporate_actions`: symbol=600000
- `universe_coverage`: no parameters
- `csi300_membership`: end_date=20260621, start_date=20260601
- `csi500_membership`: end_date=20260621, start_date=20260601
- `csi1000_membership`: end_date=20260621, start_date=20260601

## Known Limitations

### security_lifecycle
- AKShare dated ST name-change evidence currently covers Shenzhen only
- AKShare suspension history is queried by date and retained at retrieval time
- AKShare delisting records do not prove complete warning-period coverage
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### st_status
- AKShare dated ST name-change evidence currently covers Shenzhen only
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### suspension_status
- AKShare suspension history is queried by date and retained at retrieval time
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### delisting_records
- AKShare delisting records do not prove complete warning-period coverage
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### financial_publication_dates
- AKShare actual disclosure schedule is date-only
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### fundamental_revisions
- AKShare CNInfo announcements identify revisions but not prior numeric values
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### corporate_actions
- AKShare corporate-action announcement timing remains provider-limited
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### universe_coverage
- AKShare A-share universe is a retrieval-time listing snapshot
- secondary provider unavailable: TUSHARE_TOKEN is not configured
- coverage is unmeasurable
- trust level low is below required medium
- secondary-provider consistency is unknown
- required provider calibration is unavailable

### csi300_membership
- primary provider unavailable: AKShare dataset index_membership failed after 2 attempts (URLError)
- secondary provider unavailable: TUSHARE_TOKEN is not configured

### csi500_membership
- primary provider unavailable: AKShare dataset index_membership failed after 2 attempts (URLError)
- secondary provider unavailable: TUSHARE_TOKEN is not configured

### csi1000_membership
- primary provider unavailable: AKShare dataset index_membership failed after 2 attempts (URLError)
- secondary provider unavailable: TUSHARE_TOKEN is not configured
