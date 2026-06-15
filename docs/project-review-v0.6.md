# Project Review After V0.6

## Resolved During V0.6

### Provider-adjusted price leakage

AKShare forward-adjusted and backward-adjusted histories may incorporate later
corporate actions. Strict point-in-time ingestion now rejects adjusted bars
until dated corporate-action factors are available.

### Signal authority

The universal Signal model now enforces stage/action compatibility. Validation
can only emit `REVIEW`; Research cannot emit strategy entry or exit actions.

### Continuous integration

GitHub Actions now runs Pytest, Ruff, and mypy on pushes and pull requests.

## Priority 1

### Historical data contracts exist, but ingestion is incomplete

SQLite can store fundamental revisions, security status, and universe
membership, but the active AKShare pipeline does not populate those histories.
Current universe ingestion only stores instrument snapshots.

Impact: full historical replay and survivorship-safe validation cannot yet be
constructed automatically.

Recommended next step: add versioned ingestion adapters for fundamentals,
security lifecycle, and historical universe membership before trusting broad
historical results.

### V0.4 and V0.5 research models overlap

Screening still owns the older `ResearchOutcome` and `InvestmentAssessment`,
while V0.5 introduced `ResearchReport` and `ResearchAssessment`.

Impact: the path from the V0.5 Research Engine into Investment Score is not a
single canonical contract.

Recommended next step: move post-research investment assessment into a shared
application service that consumes `ResearchReport`, then deprecate the V0.4
compatibility models.

### Historical replay is an interface, not an implemented pipeline

V0.6 validates supplied `ValidationSample` objects and defines a
`HistoricalReplaySource`, but no repository currently reconstructs samples from
stored Discovery, Screening, Research, market, and outcome records.

Impact: validation is reproducible after samples are assembled, but assembling
the samples still requires an external application layer.

Recommended next step: implement a read-only replay builder with explicit
`decision_as_of` and `outcome_as_of` queries.

### Persistence is not atomic across complete runs

Research and Validation repositories call many SQLite save methods, each with a
separate transaction.

Impact: a mid-run failure can leave a failed run with partially persisted child
records. This is useful as an audit trail but is not a complete immutable run
snapshot.

Recommended next step: add unit-of-work transactions for final report
persistence while retaining explicit failed-run diagnostics.

## Priority 2

### Schema versioning is not a migration system

`schema_metadata` records V0.6, but `initialize()` uses `CREATE TABLE IF NOT
EXISTS` and updates the version directly.

Impact: future column or constraint changes could label a partially migrated
database as current.

Recommended next step: introduce ordered migrations with checksums and refuse
unknown or skipped versions.

### Database relationships are not enforced

SQLite enables foreign keys, but analytical tables do not define `REFERENCES`
constraints.

Impact: orphaned report, assessment, outcome, or decision records are possible.

Recommended next step: add foreign keys during the migration work and define
intentional cascade/restrict behavior.

### Publication-time assumptions need source validation

Daily bars are currently considered available one minute after the close, and
trading-calendar dates are treated as known from the beginning of the day.

Impact: emergency closures, late corrections, or delayed final data could make
the assumed availability optimistic.

Recommended next step: create provider-specific availability policies and
retain raw publication/retrieval evidence.

### Framework snapshots are mandatory but caller-supplied

V0.6 stores Git, framework, configuration, research, validation, and schema
versions. The repository verifies the schema version, but it does not verify
the Git commit or framework version against the running process.

Recommended next step: add a runtime snapshot factory that reads package
version, repository commit, dirty-worktree status, and canonical configuration
directly.

### Execution safety is still only a skeleton

The future `Order` model validates quantity and limit price, but does not prove
that a Strategy Signal passed an approved RiskDecision.

Recommended next step: before any paper or live execution milestone, make risk
approval and strategy-action compatibility mandatory construction inputs.

## Priority 3

- Split the growing SQLite storage module into market-data, research, and
  validation repositories behind one transaction manager.
- Add read APIs for stored ResearchReport and ValidationReport reconstruction.
- Add test coverage thresholds and property-based tests for time ordering,
  split isolation, and concentration arithmetic.
- Add provider-backed policy, sentiment, industry heat, and intraday evidence.
- Keep notification and broker adapters disabled until their milestone begins.

## Recommended Sequence

1. Historical replay and missing point-in-time ingestion
2. Canonical ResearchReport-to-Investment-Score contract
3. SQLite migrations, foreign keys, and unit-of-work persistence
4. Runtime-verified framework snapshots
5. Provider availability calibration and corporate-action factors
6. Only then begin portfolio construction or execution-oriented milestones
