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
