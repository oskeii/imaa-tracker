"""Migration 007: add immersion_sessions.comprehension and immersion_sessions.is_passive"""
from ._helpers import column_exists


def upgrade(conn):
    if not column_exists(conn, "immersion_sessions", "is_passive"):
        conn.execute(
            "ALTER TABLE immersion_sessions ADD COLUMN is_passive INTEGER CHECK (is_passive IN (0, 1))"
        )

    if not column_exists(conn, "immersion_sessions", "comprehension"):
        conn.execute(
            "ALTER TABLE immersion_sessions ADD COLUMN comprehension INTEGER CHECK (comprehension BETWEEN 1 AND 5)"
        )
