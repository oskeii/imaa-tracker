"""Migration 002: add the settings table."""


def upgrade(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Seed defaults. INSERT OR IGNORE
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("active_day_minutes", "15"),
    )
