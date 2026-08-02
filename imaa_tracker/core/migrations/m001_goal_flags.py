"""Migration 001: add goals.pinned and goals.show_on_log"""


def _column_exists(conn, table: str, column: str) -> bool:
    table_info = conn.execute(f"PRAGMA table_info({table})")  # one row per column; column name at index 1
    return any(row[1] == column for row in table_info)


def upgrade(conn):
    """Receives an open connection, already inside a transaction; caller must commit and close."""
    if not _column_exists(conn, "goals", "pinned"):
        conn.execute(
            "ALTER TABLE goals ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1))"
        )

    if not _column_exists(conn, "goals", "show_on_log"):
        conn.execute(
            "ALTER TABLE goals ADD COLUMN show_on_log INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1))"
        )

