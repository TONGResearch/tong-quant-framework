# AKShare Data Quality Audit

Generated at: 2026-06-21T08:26:29.222166+00:00
AKShare version: `1.18.64`

Quality metrics describe the observed normalized response. They do not upgrade point-in-time trust or prove historical continuity.

| Dataset | Access | Records | Expected coverage | Field completeness | Date validity | Unique keys | Evidence scope |
|---|---|---:|---:|---:|---:|---:|---|
| security_lifecycle | available | 1693 | N/A | 100.00% | 100.00% | 100.00% | partial_history |
| st_status | available | 1464 | N/A | 100.00% | 100.00% | 100.00% | partial_history |
| suspension_status | available | 25 | N/A | 100.00% | 100.00% | 100.00% | date_scoped |
| delisting_records | available | 204 | N/A | 100.00% | 100.00% | 100.00% | terminal_records |
| financial_publication_dates | available | 5189 | N/A | 100.00% | 100.00% | 100.00% | date_scoped |
| fundamental_revisions | available | 23 | N/A | 100.00% | 100.00% | 100.00% | date_scoped |
| corporate_actions | available | 25 | N/A | 100.00% | 100.00% | 100.00% | partial_history |
| universe_coverage | available | 5528 | N/A | 100.00% | N/A | 100.00% | current_snapshot |
| csi300_membership | error | 0 | 0.00% | N/A | N/A | N/A | current_snapshot |
| csi500_membership | error | 0 | 0.00% | N/A | N/A | N/A | current_snapshot |
| csi1000_membership | error | 0 | 0.00% | N/A | N/A | N/A | current_snapshot |

## Dataset Guidance

### security_lifecycle
- Usage: Use as incomplete historical evidence; never infer missing intervals
- Query scope: trade_date=20260619
- Limitation: AKShare dated ST name-change evidence currently covers Shenzhen only
- Limitation: AKShare suspension history is queried by date and retained at retrieval time
- Limitation: AKShare delisting records do not prove complete warning-period coverage

### st_status
- Usage: Use as incomplete historical evidence; never infer missing intervals
- Query scope: no parameters
- Limitation: AKShare dated ST name-change evidence currently covers Shenzhen only

### suspension_status
- Usage: Use with explicit dates and provider limitations; backfill multiple periods
- Query scope: trade_date=20260619
- Limitation: AKShare suspension history is queried by date and retained at retrieval time

### delisting_records
- Usage: Use for terminal-event evidence; warning-period history remains separate
- Query scope: no parameters
- Limitation: AKShare delisting records do not prove complete warning-period coverage

### financial_publication_dates
- Usage: Use with explicit dates and provider limitations; backfill multiple periods
- Query scope: period_end=20251231
- Limitation: AKShare actual disclosure schedule is date-only

### fundamental_revisions
- Usage: Use with explicit dates and provider limitations; backfill multiple periods
- Query scope: end_date=20260621, start_date=20240101, symbol=600000
- Limitation: AKShare CNInfo announcements identify revisions but not prior numeric values

### corporate_actions
- Usage: Use as incomplete historical evidence; never infer missing intervals
- Query scope: symbol=600000
- Limitation: AKShare corporate-action announcement timing remains provider-limited

### universe_coverage
- Usage: Use for forward snapshot collection only, not backward reconstruction
- Query scope: no parameters
- Limitation: AKShare A-share universe is a retrieval-time listing snapshot

### csi300_membership
- Usage: Unavailable until provider access is restored
- Query scope: end_date=20260621, start_date=20260601
- Limitation: provider call failed: AKShare dataset index_membership failed after 2 attempts (URLError)

### csi500_membership
- Usage: Unavailable until provider access is restored
- Query scope: end_date=20260621, start_date=20260601
- Limitation: provider call failed: AKShare dataset index_membership failed after 2 attempts (URLError)

### csi1000_membership
- Usage: Unavailable until provider access is restored
- Query scope: end_date=20260621, start_date=20260601
- Limitation: provider call failed: AKShare dataset index_membership failed after 2 attempts (URLError)
