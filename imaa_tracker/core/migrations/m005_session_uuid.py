"""Migration 005: add immersion_sessions.uuid, backfilled deterministically."""
import sqlite3
import uuid

# Namespace derived from a fixed string, makes backfilled UUIDs consistent across all machines and database migrations
_SESSION_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "imaa-tracker.immersion_sessions")
_KEY_COLS = (
    "date", "title_text", "medium_type", "activity_type", "duration_minutes",
    "character_count", "page_count", "episode_count", "created_at",
)


def _column_exists(conn, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def upgrade(conn: sqlite3.Connection):
    if not _column_exists(conn, "immersion_sessions", "uuid"):
        conn.execute("ALTER TABLE immersion_sessions ADD COLUMN uuid TEXT")

    cols = ", ".join(_KEY_COLS)
    rows = conn.execute(
        f"SELECT id, {cols} FROM immersion_sessions WHERE uuid IS NULL ORDER BY id"
    ).fetchall()

    seen: dict[str, int] = {}
    for row in rows:
        session_id = row[0]
        key = "|".join("" if v is None else str(v) for v in row[1:])
        ordinal = seen.get(key, 0)
        seen[key] = ordinal + 1
        conn.execute(
            "UPDATE immersion_sessions SET uuid = ? WHERE id = ?",
            (
                str(uuid.uuid5(_SESSION_NS, f"{key}#{ordinal}")),
                session_id,
            )
        )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_uuid
        ON immersion_sessions(uuid)
    """)
