import argparse
from pathlib import Path

from tong_quant.core.exceptions import DatabaseIntegrityError
from tong_quant.data.storage.engineering import (
    SQLiteBackupService,
    SQLiteIntegrityService,
    database_backup_json,
    database_integrity_json,
    database_restore_json,
    serialize_database_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit, back up, or dry-run restore a Tong Quant SQLite database"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    audit = subcommands.add_parser("audit", help="Run a read-only integrity audit")
    audit.add_argument("--database", type=Path, required=True)
    audit.add_argument("--output", type=Path)

    backup = subcommands.add_parser(
        "backup",
        help="Create a verified SQLite backup without overwriting files",
    )
    backup.add_argument("--database", type=Path, required=True)
    backup.add_argument("--destination", type=Path, required=True)
    backup.add_argument("--output", type=Path)

    restore = subcommands.add_parser(
        "restore-dry-run",
        help="Restore into a new isolated destination and verify migrations",
    )
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    restore.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reserved_output = (
        args.destination if args.command in {"backup", "restore-dry-run"} else None
    )
    _require_new_output(args.output, reserved=reserved_output)
    integrity = SQLiteIntegrityService()
    backup_service = SQLiteBackupService(integrity_service=integrity)
    try:
        if args.command == "audit":
            report = integrity.audit(args.database)
            rendered = serialize_database_report(database_integrity_json(report))
            _emit(rendered, args.output)
            if not report.passed:
                raise SystemExit("Database audit failed closed")
            return
        if args.command == "backup":
            manifest = backup_service.create_backup(
                source_path=args.database,
                destination_path=args.destination,
            )
            _emit(
                serialize_database_report(database_backup_json(manifest)),
                args.output,
            )
            return
        restore = backup_service.dry_run_restore(
            backup_path=args.backup,
            destination_path=args.destination,
        )
        _emit(
            serialize_database_report(database_restore_json(restore)),
            args.output,
        )
    except DatabaseIntegrityError as error:
        raise SystemExit(f"Database operation failed closed: {error}") from error


def _require_new_output(path: Path | None, *, reserved: Path | None) -> None:
    if path is not None and (path.exists() or path.is_symlink()):
        raise SystemExit("Report output already exists; overwrite is disabled")
    if (
        path is not None
        and reserved is not None
        and path.expanduser().resolve() == reserved.expanduser().resolve()
    ):
        raise SystemExit("Report output must differ from the database destination")


def _emit(rendered: str, output: Path | None) -> None:
    if output is None:
        print(rendered)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(rendered + "\n")
    output.chmod(0o600)
    print(output)


if __name__ == "__main__":
    main()
