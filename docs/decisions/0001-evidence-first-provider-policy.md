# ADR 0001: Evidence-First Provider Policy

Status: Accepted

## Decision

Tong Quant consumes evidence, not provider reputation. Every dataset is
evaluated independently for trust, coverage, availability precision, historical
continuity, and cross-provider consistency.

Provider capability, successful authentication, paid access, or a healthy
contract probe cannot by itself upgrade `DataTrustLevel` or PIT readiness.

## Consequences

- All new providers implement `ProviderEvidenceAdapter`.
- Provider-native payloads retain provenance and limitations.
- Unavailable evidence remains visible.
- Calibration and readiness remain separate decisions.
- Provider replacement does not require changes in Research or Validation.
