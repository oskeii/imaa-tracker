"""Migration 003: add enum CHECK constraints to titles, immersion_sessions, and goals tables."""
import sqlite3

# Snapshot of ENUMS values as of schema version 3
_V3_MEDIUM_TYPES = (
    "anime", "drama", "visual_novel", "light_novel", "novel", "book",
    "manga", "game", "podcast", "audiobook", "youtube",
)
_V3_ACTIVITY_TYPES = ("reading", "listening", "both")
_V3_API_LIST = ("anilist", "vndb", "tmdb", "igdb", "google_books")
_V3_GOAL_TYPES = ("recurring", "lifetime")
_V3_GOAL_METRICS = ("duration_minutes", "character_count", "episode_count", "page_count", "session_count",)
_V3_GOAL_PERIODS = ("daily", "weekly", "monthly")


def _sql_tuple(values) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def _assert_data_is_clean(conn: sqlite3.Connection, table: str, column: str, allowed) -> None:
    """Check existing data meets constraints before building new table."""
    placeholders = ", ".join("?" for _ in allowed)
    bad_values = conn.execute(
        f"SELECT DISTINCT {column} FROM {table} "
        f"WHERE {column} IS NOT NULL AND {column} NOT IN ({placeholders})",
        tuple(allowed)
    ).fetchall()
    if bad_values:
        values = [row[0] for row in bad_values]
        raise RuntimeError(
            f"Cannot add CHECK constraint: {table}.{column} contains values not in the allowed list: {values}. "
            f"Fix these rows first. \n"
            f"Allowed values: {list(allowed)}"
        )


def _rebuild_table(
        conn: sqlite3.Connection,
        table: str,
        create_new_sql: str,
        columns: list[str],
        index_sqls: list[str]) -> None:
    """
    Caller must:
        - Call inside a transaction
        - PRAGMA foreign_keys=OFF before transaction begins
    """
    cols = ", ".join(columns)

    conn.execute(create_new_sql)  # new table with temporary name
    conn.execute(f"INSERT INTO {table}_new ({cols}) SELECT {cols} from {table}")  # copy over table contents
    conn.execute(f"DROP TABLE {table}")  # drop original
    conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")  # rename new table to replace

    # Recreate indexes
    for sql in index_sqls:
        conn.execute(sql)


def upgrade(conn: sqlite3.Connection):
    media = _sql_tuple(_V3_MEDIUM_TYPES)
    activities = _sql_tuple(_V3_ACTIVITY_TYPES)
    apis = _sql_tuple(_V3_API_LIST)
    goal_types = _sql_tuple(_V3_GOAL_TYPES)
    goal_metrics = _sql_tuple(_V3_GOAL_METRICS)
    goal_periods = _sql_tuple(_V3_GOAL_PERIODS)

    _assert_data_is_clean(conn, "titles", "medium_type", _V3_MEDIUM_TYPES)
    _assert_data_is_clean(conn, "titles", "api", _V3_API_LIST)
    _assert_data_is_clean(conn, "immersion_sessions", "medium_type", _V3_MEDIUM_TYPES)
    _assert_data_is_clean(conn, "immersion_sessions", "activity_type", _V3_ACTIVITY_TYPES)
    _assert_data_is_clean(conn, "goals", "goal_type", _V3_GOAL_TYPES)
    _assert_data_is_clean(conn, "goals", "metric", _V3_GOAL_METRICS)
    _assert_data_is_clean(conn, "goals", "period", _V3_GOAL_PERIODS)
    _assert_data_is_clean(conn, "goals", "medium_type", _V3_MEDIUM_TYPES)
    _assert_data_is_clean(conn, "goals", "activity_type", _V3_ACTIVITY_TYPES)

    # Rebuild titles
    _rebuild_table(
        conn,
        table="titles",
        create_new_sql=f"""
            CREATE TABLE titles_new (
                id                  INTEGER PRIMARY KEY,
                name                TEXT NOT NULL,
                medium_type         TEXT NOT NULL CHECK (medium_type IN {media}),
                genre               TEXT,
                tags                TEXT,
                cover_image         TEXT,
                api                 TEXT CHECK (api IS NULL OR api IN {apis}),
                api_id              TEXT,
                youtube_channel_id  TEXT,
                youtube_url         TEXT,
                notes               TEXT,
                created_at          TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """,
        columns=[
            "id", "name", "medium_type", "genre", "tags", "cover_image",
            "api", "api_id", "youtube_channel_id", "youtube_url",
            "notes", "created_at",
        ],
        index_sqls=[
            "CREATE INDEX IF NOT EXISTS idx_titles_name ON titles(name)",
            "CREATE INDEX IF NOT EXISTS idx_titles_medium ON titles(medium_type)",
        ],
    )

    # Rebuild immersion_sessions
    _rebuild_table(
        conn,
        table="immersion_sessions",
        create_new_sql=f"""
            CREATE TABLE immersion_sessions_new (
                id                  INTEGER PRIMARY KEY,
                date                TEXT NOT NULL,
                title_id            INTEGER,
                title_text          TEXT NOT NULL,
                medium_type         TEXT NOT NULL CHECK (medium_type IN {media}),
                activity_type       TEXT NOT NULL DEFAULT 'reading'
                                        CHECK (activity_type IN {activities}),
                duration_minutes    INTEGER,
                character_count     INTEGER,
                page_count          INTEGER,
                episode_count       INTEGER,
                reading_direction   TEXT,
                volume              TEXT,
                chapter             TEXT,
                episode_name        TEXT,
                urls_json           TEXT,
                notes               TEXT,
                created_at          TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE SET NULL
            )
        """,
        columns=[
            "id", "date", "title_id", "title_text", "medium_type",
            "activity_type", "duration_minutes", "character_count",
            "page_count", "episode_count", "reading_direction", "volume",
            "chapter", "episode_name", "urls_json", "notes", "created_at",
        ],
        index_sqls=[
            "CREATE INDEX IF NOT EXISTS idx_sessions_date ON immersion_sessions(date);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_title ON immersion_sessions(title_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_medium ON immersion_sessions(medium_type)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_activity ON immersion_sessions(activity_type)",
        ],
    )

    # Rebuild goals
    _rebuild_table(
        conn,
        table="goals",
        create_new_sql=f"""
                CREATE TABLE goals_new (
                    id                  INTEGER PRIMARY KEY,
                    name                TEXT NOT NULL,
                    goal_type           TEXT NOT NULL CHECK (goal_type IN {goal_types}),
                    metric              TEXT NOT NULL CHECK (metric IN {goal_metrics}),
                    target_value        INTEGER NOT NULL,
                    period              TEXT CHECK (period IS NULL OR period IN {goal_periods}),
                    medium_type         TEXT CHECK (medium_type IS NULL OR medium_type IN {media}),
                    activity_type       TEXT CHECK (activity_type IS NULL OR activity_type IN {activities}),
                    health_window_days  INTEGER DEFAULT 60,
                    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                    pinned              INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0,1)),
                    show_on_log         INTEGER NOT NULL DEFAULT 0 CHECK (show_on_log IN (0,1)),
                    achieved_at         TEXT,
                    notes               TEXT,
                    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """,
        columns=[
            "id", "name", "goal_type", "metric", "target_value", "period",
            "medium_type", "activity_type", "health_window_days", "is_active",
            "pinned", "show_on_log", "achieved_at", "notes", "created_at",
        ],
        index_sqls=[],  # goals had no indexes in v0->v2
    )

