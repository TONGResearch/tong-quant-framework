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

MIGRATIONS = (NOTIFICATION_HARDENING,)
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
    if migration is not NOTIFICATION_HARDENING:
        raise RuntimeError(f"unknown migration: {migration.migration_id}")
    _add_column_if_missing(connection, "notification_outbox", "lease_expires_at", "TEXT")
    _add_column_if_missing(connection, "notification_outbox", "dead_lettered_at", "TEXT")
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
