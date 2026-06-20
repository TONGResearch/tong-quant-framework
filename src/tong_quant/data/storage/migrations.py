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

MIGRATIONS = (
    NOTIFICATION_HARDENING,
    PIT_DATA_CALIBRATION,
    PROVIDER_CALIBRATION_PHASE_II,
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
    if migration is NOTIFICATION_HARDENING:
        _apply_notification_hardening(connection)
        return
    if migration is PIT_DATA_CALIBRATION:
        _apply_pit_data_calibration(connection)
        return
    if migration is PROVIDER_CALIBRATION_PHASE_II:
        _apply_provider_calibration_phase_ii(connection)
        return
    raise RuntimeError(f"unknown migration: {migration.migration_id}")


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


__all__ = ["MIGRATION_HEAD", "MIGRATIONS", "Migration", "run_migrations"]
