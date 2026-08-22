# Work Packages

Work packages are bounded implementation contracts. Their order and status are
owned by `config/project-governance.toml`.

Rules:

- Start only a package marked `ready`.
- Complete or explicitly block one package before opening another in the same
  ownership area.
- Preserve every listed non-goal.
- Do not mark a package complete because provider access is unavailable.
- Update tests, state documents, risk, and debt records with the implementation.

Use `template.md` when a new package is approved.

`WP-RESEARCH-001` is planned only. It groups correlated technical indicators
by evidence family, treats size as point-in-time cross-sectional context, and
keeps startup and stop concepts inside Research. Indicator formulas alone
cannot make this package ready.

`WP-VALIDATION-001` closes a prior Historical Replay eligibility gap. Replay
results now preserve all samples and fail closed before Validation when trust,
PIT readiness, or required data is insufficient.
