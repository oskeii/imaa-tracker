from contextlib import closing
from datetime import datetime

import db
from . import m001_goal_flags, m002_settings, m003_enum_checks

# APPEND ONLY (version, description, upgrade_function)
MIGRATIONS = [
    (1, "add goals.pinned and goals.show_on_log", m001_goal_flags.upgrade),
    (2, "add settings table", m002_settings.upgrade),
    (3, "add enum CHECK constraints to titles, immersion_sessions, and goals tables", m003_enum_checks.upgrade),
]

LATEST_VERSION = max(v for v, _, _ in MIGRATIONS)


def open_database(db_path=None) -> int:
    """
    Call at app startup.
    Handles DB creation and schema migrations.
    Returns DB schema version number.
    """
    with db.connect(db_path) as conn:
        has_tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0] > 0

    if not has_tables:
        db.init_db(db_path)
        return db.SCHEMA_VERSION

    return migrate(db_path)


def migrate(db_path=None, backup=True) -> int:
    """
    Apply every migration newer than the database's version stamp.
    Returns the updated version number.
    """
    if db_path is None:
        db_path = db.DB_NAME

    current = db.get_schema_version(db_path)

    pending = [(v, desc, fn) for v, desc, fn in MIGRATIONS if v > current]
    if not pending:
        return current

    if backup:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = f"{db_path}.v{current}.{stamp}.bak"
        db.backup_database(dest, db_path=db_path)
        print(f"[migrate] backup written: {dest}")

    with closing(db.get_connection(db_path)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys=OFF")

        for ver, desc, upgrade in pending:
            print(f"[migrate] {current} -> {ver}: {desc}")
            conn.execute("BEGIN")
            try:
                upgrade(conn)

                # Check for dangling references
                violations = conn.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise RuntimeError(
                        f"migration {ver} left foreign key violations:"
                        f"{[tuple(v) for v in violations]}"
                    )

                conn.execute(f"PRAGMA user_version = {int(ver)}")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            current = ver

    print(f"[migrate] done, now at version {current}")
    return current


assert LATEST_VERSION == db.SCHEMA_VERSION, (
    f"Migration registry tops out at {LATEST_VERSION} but "
    f"db.SCHEMA_VERSION is {db.SCHEMA_VERSION}."
    f"Add the missing migration to the registry or fix the version number."
)
