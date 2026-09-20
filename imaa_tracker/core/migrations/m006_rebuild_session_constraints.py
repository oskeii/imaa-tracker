"""
Migration 006: rebuild immersion_sessions to add the missing reading_direction CHECK,
and make idx_sessions_uuid UNIQUE.

(CORRECTIONS) Both were added to db.py, but mistakenly omitted from the corresponding migrations.
"""
import sqlite3

from ._helpers import assert_data_is_clean, rebuild_table, sql_tuple


# Snapshot of ENUMS values as of schema version 6
_V6_MEDIUM_TYPES = (
    "anime", "drama", "visual_novel", "light_novel", "novel", "book",
    "manga", "game", "podcast", "audiobook", "youtube",
)
_V6_ACTIVITY_TYPES = ("reading", "listening", "both")
_V6_READING_DIRECTIONS = ("horizontal", "vertical")


def upgrade(conn: sqlite3.Connection):
    # --- 1. Normalize row values before validating
    conn.execute("""
        UPDATE immersion_sessions
        SET reading_direction = NULL
        WHERE reading_direction IS NOT NULL AND TRIM(reading_direction) = ''
    """)
    conn.execute("""
        UPDATE immersion_sessions
        SET reading_direction = LOWER(TRIM(reading_direction))
        WHERE reading_direction IS NOT NULL
            AND reading_direction <> LOWER(TRIM(reading_direction))
    """)

    # --- 2. Validate data with CHECK constraints
    assert_data_is_clean(conn, "immersion_sessions", "medium_type", _V6_MEDIUM_TYPES)
    assert_data_is_clean(conn, "immersion_sessions", "activity_type", _V6_ACTIVITY_TYPES)
    assert_data_is_clean(conn, "immersion_sessions", "reading_direction", _V6_READING_DIRECTIONS)

    # --- 3. uuid must be unique before unique index can exist
    dupes = conn.execute("""
        SELECT uuid, COUNT(*) FROM immersion_sessions
        WHERE uuid IS NOT NULL GROUP BY uuid HAVING COUNT(*) > 1
    """).fetchall()
    if dupes:
        raise RuntimeError(
            f"Cannot create UNIQUE index on immersion_sessions.uuid: "
            f"{len(dupes)} duplicated value(s), e.g. {dupes[0][0]!r}. "
            f"Resolve these rows before upgrading."
        )

    # --- 4. Rebuild immersion_sessions
    media = sql_tuple(_V6_MEDIUM_TYPES)
    activities = sql_tuple(_V6_ACTIVITY_TYPES)
    directions = sql_tuple(_V6_READING_DIRECTIONS)
    rebuild_table(
        conn,
        table="immersion_sessions",
        create_new_sql=f"""
            CREATE TABLE IF NOT EXISTS immersion_sessions_new (
                id				    INTEGER PRIMARY KEY,
                date			    TEXT NOT NULL,  -- ISO date YYYY-MM-DD
                title_id            INTEGER,    -- FK to titles 
                title_text          TEXT NOT NULL,   
                
                medium_type         TEXT NOT NULL CHECK (medium_type IN {media}),  
                activity_type       TEXT NOT NULL DEFAULT 'reading' 
                                            CHECK (activity_type IN {activities}),
                
                -- Metrics (fill what applies)
                duration_minutes    INTEGER,
                character_count     INTEGER,
                page_count          INTEGER,
                episode_count       INTEGER,
                
                reading_direction   TEXT CHECK (reading_direction IS NULL
                                                OR reading_direction IN {directions}),
                
                -- Details
                volume              TEXT,
                chapter             TEXT,
                episode_name        TEXT,
                
                -- URLS (JSON array for multiple)
                urls_json           TEXT,   -- '["https://...", "https://..."]'
                
                notes		        TEXT,
                created_at	        TEXT NOT NULL DEFAULT (datetime('now')),
                uuid                TEXT,
                
                FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE SET NULL        
            )
        """,
        columns=[
            "id", "date", "title_id", "title_text", "medium_type",
            "activity_type", "duration_minutes", "character_count",
            "page_count", "episode_count", "reading_direction",
            "volume", "chapter", "episode_name", "urls_json", "notes", "created_at",
            "uuid",
        ],
        index_sqls=[
            "CREATE INDEX IF NOT EXISTS idx_sessions_date ON immersion_sessions(date)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_title ON immersion_sessions(title_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_medium ON immersion_sessions(medium_type)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_activity ON immersion_sessions(activity_type)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_uuid ON immersion_sessions(uuid)",
        ],
    )

