import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class Migration:
    migration_id: str
    description: str
    definition: str

    @property
    def checksum(self) -> str:
        payload = f"{self.migration_id}:{self.description}:{self.definition}"
        return sha256(payload.encode("utf-8")).hexdigest()


SCHEMA_BASELINE = Migration(
    migration_id="0000_schema_baseline",
    description="register and verify the legacy Tong Quant baseline schema",
    definition="""
    verify core baseline tables created before the migration ledger;
    no DDL changes;
    """,
)


NOTIFICATION_HARDENING = Migration(
    migration_id="0001_notification_hardening",
    description="add outbox leases, dead letters, and migration audit state",
    definition="""
    notification_outbox.lease_expires_at TEXT;
    notification_outbox.dead_lettered_at TEXT;
    idx_notification_outbox_lease(status, lease_expires_at);
    notification_dead_letters(
        dead_letter_id PRIMARY KEY,
        notification_id UNIQUE REFERENCES notification_outbox ON DELETE CASCADE,
        final_attempt_number,
        error_code,
        reason,
        dead_lettered_at
    );
    """,
)

PIT_DATA_CALIBRATION = Migration(
    migration_id="0002_pit_data_calibration",
    description="add lifecycle, publication, coverage, and provider calibration evidence",
    definition="""
    pit_readiness_assessments.readiness_score REAL;
    pit_readiness_assessments.classification TEXT;
    pit_readiness_assessments.score_components_json TEXT;
    pit_readiness_assessments.assumptions_json TEXT;
    security_lifecycle_events(...);
    fundamental_publication_events(...);
    historical_coverage_assessments(...);
    provider_consistency_reports(...);
    """,
)

PROVIDER_CALIBRATION_PHASE_II = Migration(
    migration_id="0003_provider_calibration_phase_ii",
    description="add provider conflict history and dataset confidence assessments",
    definition="""
    provider_conflicts(...);
    dataset_confidence_assessments(...);
    """,
)

SCHEMA_FINGERPRINT_LEDGER = Migration(
    migration_id="0004_schema_fingerprint_ledger",
    description="add fail-closed physical schema fingerprint tracking",
    definition="""
    schema_fingerprints(
        migration_head PRIMARY KEY,
        schema_fingerprint,
        schema_definition_hash,
        recorded_at
    );
    """,
)

PROVIDER_EVIDENCE_FOUNDATION = Migration(
    migration_id="0005_provider_evidence_foundation",
    description="add provider-neutral evidence and contract monitoring ledgers",
    definition="""
    provider_evidence_records(... REFERENCES ingestion_batches);
    provider_contract_runs(...);
    provider_contract_checks(... REFERENCES provider_contract_runs);
    """,
)

MIGRATIONS = (
    SCHEMA_BASELINE,
    NOTIFICATION_HARDENING,
    PIT_DATA_CALIBRATION,
    PROVIDER_CALIBRATION_PHASE_II,
    SCHEMA_FINGERPRINT_LEDGER,
    PROVIDER_EVIDENCE_FOUNDATION,
)
MIGRATION_HEAD = MIGRATIONS[-1].migration_id


def run_migrations(connection: sqlite3.Connection) -> tuple[str, ...]:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied: list[str] = []
    for migration in MIGRATIONS:
        row = connection.execute(
            "SELECT checksum FROM schema_migrations WHERE migration_id = ?",
            (migration.migration_id,),
        ).fetchone()
        if row is not None:
            if str(row[0]) != migration.checksum:
                raise RuntimeError(
                    f"migration checksum mismatch: {migration.migration_id}"
                )
            continue
        _apply_migration(connection, migration)
        connection.execute(
            """
            INSERT INTO schema_migrations (
                migration_id, checksum, description, applied_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                migration.migration_id,
                migration.checksum,
                migration.description,
                datetime.now(UTC).isoformat(),
            ),
        )
        applied.append(migration.migration_id)
    return tuple(applied)


def _apply_migration(connection: sqlite3.Connection, migration: Migration) -> None:
    if migration is SCHEMA_BASELINE:
        _apply_schema_baseline(connection)
        return
    if migration is NOTIFICATION_HARDENING:
        _apply_notification_hardening(connection)
        return
    if migration is PIT_DATA_CALIBRATION:
        _apply_pit_data_calibration(connection)
        return
    if migration is PROVIDER_CALIBRATION_PHASE_II:
        _apply_provider_calibration_phase_ii(connection)
        return
    if migration is SCHEMA_FINGERPRINT_LEDGER:
        _apply_schema_fingerprint_ledger(connection)
        return
    if migration is PROVIDER_EVIDENCE_FOUNDATION:
        _apply_provider_evidence_foundation(connection)
        return
    raise RuntimeError(f"unknown migration: {migration.migration_id}")


def _apply_schema_baseline(connection: sqlite3.Connection) -> None:
    required = {
        "schema_metadata",
        "instruments",
        "daily_bars",
        "trading_calendar",
        "fundamental_facts",
        "ingestion_batches",
        "research_reports",
        "validation_runs",
        "historical_replay_manifests",
        "portfolio_proposals",
        "notification_outbox",
    }
    existing = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing = sorted(required - existing)
    if missing:
        raise RuntimeError(f"schema baseline is incomplete: {', '.join(missing)}")


def _apply_notification_hardening(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection, "notification_outbox", "lease_expires_at", "TEXT"
    )
    _add_column_if_missing(
        connection, "notification_outbox", "dead_lettered_at", "TEXT"
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notification_outbox_lease
        ON notification_outbox (status, lease_expires_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_dead_letters (
            dead_letter_id TEXT PRIMARY KEY,
            notification_id TEXT NOT NULL UNIQUE,
            final_attempt_number INTEGER NOT NULL,
            error_code TEXT NOT NULL,
            reason TEXT NOT NULL,
            dead_lettered_at TEXT NOT NULL,
            FOREIGN KEY (notification_id)
                REFERENCES notification_outbox (notification_id) ON DELETE CASCADE
        )
        """
    )


def _apply_pit_data_calibration(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "pit_readiness_assessments",
        "readiness_score",
        "REAL NOT NULL DEFAULT 0",
    )
    _add_column_if_missing(
        connection,
        "pit_readiness_assessments",
        "classification",
        "TEXT NOT NULL DEFAULT 'caution'",
    )
    _add_column_if_missing(
        connection,
        "pit_readiness_assessments",
        "score_components_json",
        "TEXT NOT NULL DEFAULT '{}'",
    )
    _add_column_if_missing(
        connection,
        "pit_readiness_assessments",
        "assumptions_json",
        "TEXT NOT NULL DEFAULT '[]'",
    )
    connection.execute(
        """
        UPDATE pit_readiness_assessments
        SET readiness_score = CASE
                WHEN ready_for_historical_replay = 1 THEN 80
                ELSE readiness_score
            END,
            classification = CASE
                WHEN ready_for_historical_replay = 1 THEN 'usable'
                ELSE classification
            END
        """
    )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS security_lifecycle_events (
            event_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            available_at TEXT NOT NULL,
            source TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            details_json TEXT NOT NULL,
            raw_data_hash TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            provider_dataset TEXT NOT NULL,
            availability_precision TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            UNIQUE (
                instrument_id, event_type, effective_date, available_at,
                source, raw_data_hash
            )
        );

        CREATE INDEX IF NOT EXISTS idx_security_lifecycle_pit
        ON security_lifecycle_events (
            instrument_id, effective_date, available_at, event_type
        );

        CREATE TABLE IF NOT EXISTS fundamental_publication_events (
            event_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            period_end TEXT NOT NULL,
            report_type TEXT NOT NULL,
            published_at TEXT NOT NULL,
            available_at TEXT NOT NULL,
            title TEXT NOT NULL,
            revision INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            raw_data_hash TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            provider_dataset TEXT NOT NULL,
            availability_precision TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            UNIQUE (
                instrument_id, period_end, published_at, revision,
                source, source_reference
            )
        );

        CREATE INDEX IF NOT EXISTS idx_fundamental_publication_pit
        ON fundamental_publication_events (
            instrument_id, period_end, available_at, revision
        );

        CREATE TABLE IF NOT EXISTS historical_coverage_assessments (
            assessment_id TEXT PRIMARY KEY,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            dataset TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            assessed_at TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            classification TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            score_components_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            assumptions_json TEXT NOT NULL,
            model_version TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_historical_coverage_subject
        ON historical_coverage_assessments (
            subject_type, subject_id, assessed_at
        );

        CREATE TABLE IF NOT EXISTS provider_consistency_reports (
            report_id TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            primary_provider TEXT NOT NULL,
            secondary_provider TEXT NOT NULL,
            compared_at TEXT NOT NULL,
            primary_count INTEGER NOT NULL,
            secondary_count INTEGER NOT NULL,
            matched_count INTEGER NOT NULL,
            primary_only_count INTEGER NOT NULL,
            secondary_only_count INTEGER NOT NULL,
            key_overlap_score REAL NOT NULL,
            field_match_scores_json TEXT NOT NULL,
            consistency_score REAL NOT NULL,
            trust_level TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            comparison_hash TEXT NOT NULL UNIQUE,
            model_version TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_provider_consistency_dataset
        ON provider_consistency_reports (
            dataset, primary_provider, secondary_provider, compared_at
        );
        """
    )


def _apply_provider_calibration_phase_ii(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS provider_conflicts (
            conflict_id TEXT PRIMARY KEY,
            conflict_fingerprint TEXT NOT NULL,
            report_id TEXT NOT NULL,
            dataset TEXT NOT NULL,
            record_key TEXT NOT NULL,
            field_name TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            primary_provider TEXT NOT NULL,
            secondary_provider TEXT NOT NULL,
            primary_value_json TEXT NOT NULL,
            secondary_value_json TEXT NOT NULL,
            severity TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            model_version TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            UNIQUE (report_id, conflict_fingerprint)
        );

        CREATE INDEX IF NOT EXISTS idx_provider_conflicts_history
        ON provider_conflicts (
            dataset, conflict_fingerprint, detected_at
        );

        CREATE TABLE IF NOT EXISTS dataset_confidence_assessments (
            assessment_id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL UNIQUE,
            dataset TEXT NOT NULL,
            assessed_at TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            trust_level TEXT NOT NULL,
            component_scores_json TEXT NOT NULL,
            conflict_count INTEGER NOT NULL,
            critical_conflict_count INTEGER NOT NULL,
            warnings_json TEXT NOT NULL,
            model_version TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_dataset_confidence_latest
        ON dataset_confidence_assessments (dataset, assessed_at);
        """
    )


def _apply_schema_fingerprint_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_fingerprints (
            migration_head TEXT PRIMARY KEY,
            schema_fingerprint TEXT NOT NULL,
            schema_definition_hash TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )


def _apply_provider_evidence_foundation(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS provider_evidence_records (
            evidence_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            dataset TEXT NOT NULL,
            market TEXT NOT NULL,
            subject TEXT NOT NULL,
            observed_at TEXT,
            published_at TEXT,
            available_at TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            raw_data_hash TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            availability_precision TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            FOREIGN KEY (batch_id)
                REFERENCES ingestion_batches (batch_id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_provider_evidence_pit
        ON provider_evidence_records (
            provider, dataset, market, subject, available_at
        );

        CREATE TABLE IF NOT EXISTS provider_contract_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            implementation_version TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS provider_contract_checks (
            check_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            dataset TEXT NOT NULL,
            market TEXT NOT NULL,
            subject TEXT NOT NULL,
            request_as_of TEXT NOT NULL,
            status TEXT NOT NULL,
            records_observed INTEGER NOT NULL,
            trust_level TEXT NOT NULL,
            availability_precision TEXT NOT NULL,
            latency_ms REAL NOT NULL,
            required_fields_json TEXT NOT NULL,
            missing_fields_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL,
            error_code TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            FOREIGN KEY (run_id)
                REFERENCES provider_contract_runs (run_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_provider_contract_history
        ON provider_contract_checks (provider, dataset, checked_at);
        """
    )


def schema_fingerprint(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'index', 'trigger', 'view')
          AND name NOT LIKE 'sqlite_%'
          AND sql IS NOT NULL
        ORDER BY type, name
        """
    ).fetchall()
    payload = "\n".join(
        ":".join(
            (
                str(row[0]),
                str(row[1]),
                str(row[2]),
                _canonical_sql(str(row[3])),
            )
        )
        for row in rows
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def record_or_validate_schema_fingerprint(
    connection: sqlite3.Connection,
    *,
    migration_head: str,
    schema_definition: str,
) -> str:
    fingerprint = schema_fingerprint(connection)
    definition_hash = sha256(_canonical_sql(schema_definition).encode("utf-8")).hexdigest()
    row = connection.execute(
        """
        SELECT schema_fingerprint, schema_definition_hash
        FROM schema_fingerprints
        WHERE migration_head = ?
        """,
        (migration_head,),
    ).fetchone()
    if row is None:
        connection.execute(
            """
            INSERT INTO schema_fingerprints (
                migration_head, schema_fingerprint,
                schema_definition_hash, recorded_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                migration_head,
                fingerprint,
                definition_hash,
                datetime.now(UTC).isoformat(),
            ),
        )
        return fingerprint
    if str(row[0]) != fingerprint:
        raise RuntimeError(
            f"physical schema fingerprint mismatch at migration head {migration_head}"
        )
    if str(row[1]) != definition_hash:
        raise RuntimeError(
            f"baseline schema definition changed without a migration at {migration_head}"
        )
    return fingerprint


def validate_latest_schema_fingerprint(
    connection: sqlite3.Connection,
    *,
    schema_definition: str,
) -> None:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    if "schema_fingerprints" not in tables or "schema_migrations" not in tables:
        return
    row = connection.execute(
        """
        SELECT fingerprint.migration_head,
               fingerprint.schema_fingerprint,
               fingerprint.schema_definition_hash
        FROM schema_fingerprints AS fingerprint
        JOIN schema_migrations AS migration
          ON migration.migration_id = fingerprint.migration_head
        ORDER BY migration.migration_id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return
    migration_head = str(row[0])
    if str(row[1]) != schema_fingerprint(connection):
        raise RuntimeError(
            f"physical schema fingerprint mismatch before migration at {migration_head}"
        )
    definition_hash = sha256(_canonical_sql(schema_definition).encode("utf-8")).hexdigest()
    if str(row[2]) != definition_hash:
        raise RuntimeError(
            f"baseline schema definition changed without a migration at {migration_head}"
        )


def _canonical_sql(value: str) -> str:
    return " ".join(value.split())


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    declaration: str,
) -> None:
    columns = {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


__all__ = [
    "MIGRATION_HEAD",
    "MIGRATIONS",
    "Migration",
    "record_or_validate_schema_fingerprint",
    "run_migrations",
    "schema_fingerprint",
    "validate_latest_schema_fingerprint",
]
