"""
Database infra: connections, schema creation, backups.
DATABASE SCHEMA VERSION 3
"""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from constants import ENUMS
from utils.formatting import format_minutes, format_duration_str

SCHEMA_VERSION = 3
DB_NAME = "imaa_tracker.db"  # relative path


def sql_enum(values) -> str:
    """Render allowed values as a SQL tuple (for IN clause)."""
    for v in values:
        if "'" in str(v):
            raise ValueError(f"enum value contains a quote, unsuitable for SQL: {v:!r}")
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def enum_check(column: str, key: str, nullable: bool = False) -> str:
    """Build a CHECK constraint for `column` with ENUMS[key]."""
    allowed = sql_enum(ENUMS[key])
    if nullable:
        return f"CHECK ({column} IS NULL OR {column} IN {allowed})"
    return f"CHECK ({column} IN {allowed})"


def get_connection(db_path=None) -> sqlite3.Connection:
    """
    Open a configured connection.
    Caller is responsible for closing. Prefer connect(), which closes it for you.
    """
    if db_path is None:
        db_path = DB_NAME

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connect(db_path=None) -> Iterator[sqlite3.Connection]:
    """Yield a connection. Commit on success, rollback on error, always close."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schema_version(db_path=None) -> int:
    """Read schema version stamped in the DB header. 0= never stamped"""
    with connect(db_path) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


def backup_database(dest_path, db_path=None) -> str:
    """
    Write a single-file copy of the database to dest_path.
    Uses VACUUM INTO 'path': Cannot run inside an explicit transaction.
    Returns dest_path.
    """
    dest = Path(dest_path)

    dest.unlink(missing_ok=True)  # VACUUM INTO refuses to overwrite; must clear target first
    with connect(db_path) as conn:
        conn.execute("VACUUM INTO ?", (str(dest),))

    return str(dest)


def init_db(db_path=None) -> None:
    """Create the current schema in a NEW database and stamp SCHEMA_VERSION"""
    with connect(db_path) as conn:
        cur = conn.cursor()
        _create_immersion_tables(cur)   # TITLES, IMMERSION SESSIONS
        _create_study_tables(cur)       # RESOURCES, STUDY SESSIONS, EXAM SCORES
        _create_goals_tables(cur)       # GOALS, GOAL LOG, MILESTONES
        _create_settings_table(cur)     # SETTINGS
        # TBD: languages, output sessions

        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _create_immersion_tables(cur: sqlite3.Cursor):
    query_titles = f"""
    -- ===== TITLES =====
    -- Media titles for immersion. 
    -- One entry per distinct consumable unit. e.g. "Re:Zero (LN)" and "Re:Zero (Anime)" are separate titles.
    -- YouTube channels and content categories can also be titles.
    CREATE TABLE IF NOT EXISTS titles (
        id				    INTEGER PRIMARY KEY,
        name			    TEXT NOT NULL,
        medium_type		    TEXT NOT NULL {enum_check("medium_type", "MEDIUM_TYPES")},
        
        -- Optional metadata (populated manually or via API)
        genre			    TEXT,	-- comma-separated
        tags			    TEXT,	-- comma-separated
        cover_image		    TEXT,	-- file path or URL
       
        --      External API details
        api			        TEXT {enum_check("api", "API_LIST", nullable=True)},
        api_id		        TEXT,
        youtube_channel_id	TEXT,  -- for YT channel-type titles
        youtube_url		    TEXT,		-- channel URL
        
        notes		        TEXT,
        created_at	        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_titles_name ON titles(name);
    CREATE INDEX IF NOT EXISTS idx_titles_medium ON titles(medium_type);
    """

    query_immersion_sessions = f"""
    -- ===== IMMERSION SESSIONS =====
    CREATE TABLE IF NOT EXISTS immersion_sessions (
        id				    INTEGER PRIMARY KEY,
        date			    TEXT NOT NULL,  -- ISO date YYYY-MM-DD
        title_id            INTEGER,    -- FK to titles (nullable for quick-log)
        title_text          TEXT NOT NULL,   -- denormalized title for quick-log/display
        
        medium_type         TEXT NOT NULL {enum_check("medium_type", "MEDIUM_TYPES")},  -- denormalized
        activity_type       TEXT NOT NULL DEFAULT 'reading' {enum_check("activity_type", "ACTIVITY_TYPES")},
        
        -- Metrics (fill what applies)
        duration_minutes    INTEGER,
        character_count     INTEGER,
        page_count          INTEGER,
        episode_count       INTEGER,
        
        reading_direction   TEXT {enum_check("reading_direction", "READING_DIRECTIONS", nullable=True)},
        
        -- Details
        volume              TEXT,
        chapter             TEXT,
        episode_name        TEXT,
        
        -- URLS (JSON array for multiple)
        urls_json           TEXT,   -- '["https://...", "https://..."]'
        
        notes		        TEXT,
        created_at	        TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE SET NULL        
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_date ON immersion_sessions(date);
    CREATE INDEX IF NOT EXISTS idx_sessions_title ON immersion_sessions(title_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_medium ON immersion_sessions(medium_type);
    CREATE INDEX IF NOT EXISTS idx_sessions_activity ON immersion_sessions(activity_type);
    """

    cur.executescript(query_titles)
    cur.executescript(query_immersion_sessions)


def _create_study_tables(cur: sqlite3.Cursor):
    query_resources = """
    -- ===== RESOURCES =====
    -- Study materials: textbooks, workbooks, video courses, apps, mock exams, etc.
    CREATE TABLE IF NOT EXISTS resources (
        id              INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,
        resource_type   TEXT NOT NULL,  -- see RESOURCE_TYPES
        level           TEXT,   -- see RESOURCE_LEVELS
        cover_image     TEXT,   
        url             TEXT,   -- link if online resource
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """

    query_study_sessions = """
    -- ===== STUDY SESSIONS =====
    CREATE TABLE IF NOT EXISTS study_sessions (
    id                  INTEGER PRIMARY KEY,
    date                TEXT NOT NULL, -- ISO date YYYY-MM-DD
    study_type          TEXT NOT NULL,  -- see STUDY_TYPES
    resource_id         INTEGER,    -- FK to resources
    resource_text       TEXT,   -- denormalized for quick-log/display
    
    duration_minutes    INTEGER,
    
    topic_area          TEXT,   -- topic/area of focus studied. see TOPIC_AREAS
    
    -- Anki specific
    anki_deck           TEXT,
    anki_reviews        INTEGER,
    anki_new_cards      INTEGER,
    
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_study_date ON study_sessions(date);
    CREATE INDEX IF NOT EXISTS idx_study_type ON study_sessions(study_type);
    CREATE INDEX IF NOT EXISTS idx_study_resource ON study_sessions(resource_id);
    """

    query_exam_scores = """
    -- ===== EXAM SCORES =====
    -- Mock exam results. One row per exam sitting.
    CREATE TABLE IF NOT EXISTS exam_scores (
        id              INTEGER PRIMARY KEY,
        date            TEXT NOT NULL,
        level           TEXT NOT NULL,  -- N5 | N4 | N3 | N2 | N1
        exam_type       TEXT NOT NULL,  -- mock | official
        resource_id     INTEGER,    -- FK to resources (which mock exam book, etc.)
        source_text     TEXT,   -- denormalized: "2012 N4 mock", etc.
        
        -- Section scores as JSON for flexibility across JLPT levels.
        -- Structure: {"文字・語彙": {"sections": {"漢字読み": {"score": 6, "total": 8}, ...}},
        --             "文法・読解": {"sections": {...}}, "聴解": {"sections": {...}}}
        sections_json   TEXT,
        
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_exam_date ON exam_scores(date);
    CREATE INDEX IF NOT EXISTS idx_exam_level ON exam_scores(level);
    """

    cur.executescript(query_resources)
    cur.executescript(query_study_sessions)
    cur.executescript(query_exam_scores)


def _create_goals_tables(cur: sqlite3.Cursor):
    query_goals = f"""
    -- ===== GOALS =====
    -- A goal is a rule: a metric, a target, and optionally a recurring period.
    -- e.g. "Read 15k characters per day" or "Reach 1 million characters total."
    CREATE TABLE IF NOT EXISTS goals (
        id              INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,      -- e.g. "Daily reading goal", "300 immersion hours", "200 listening hours"
        goal_type       TEXT NOT NULL {enum_check("goal_type", "GOAL_TYPES")},
        metric          TEXT NOT NULL {enum_check("metric", "GOAL_METRICS")},
        target_value    INTEGER NOT NULL,
        period          TEXT {enum_check("period", "GOAL_PERIODS", nullable=True)},
        
        -- Optional filters (null = any)
        medium_type     TEXT {enum_check("medium_type", "MEDIUM_TYPES", nullable=True)},
        activity_type   TEXT {enum_check("activity_type", "ACTIVITY_TYPES", nullable=True)},
        
        -- Habit health window (for recurring goals)
        health_window_days  INTEGER DEFAULT 60,     -- health percentage calculated based on  the last N days
        
        is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
        pinned          BOOLEAN NOT NULL DEFAULT 0 CHECK (pinned IN (0,1)),
        show_on_log     BOOLEAN NOT NULL DEFAULT 0 CHECK (pinned IN (0,1)),
        
        achieved_at     TEXT,       -- for lifetime goal (ISO datetime)
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """

    query_goal_log = """
    -- ===== GOAL LOG =====
    -- One row per goal per completed period. 
    CREATE TABLE IF NOT EXISTS goal_log (
        id              INTEGER PRIMARY KEY,
        goal_id         INTEGER NOT NULL,
        period_date     TEXT NOT NULL,      -- start of the period (YYYY-MM-DD)
        actual_value    INTEGER NOT NULL,
        target_value    INTEGER NOT NULL,   -- snapshot of target value
        is_achieved     BOOLEAN NOT NULL CHECK (is_achieved IN (0,1)),
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_goallog_goal ON goal_log(goal_id);
    CREATE INDEX IF NOT EXISTS idx_goallog_date ON goal_log(period_date);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_goallog_unique ON goal_log(goal_id, period_date);
    """

    query_milestones = """
    -- ===== MILESTONES =====
    -- A milestone is a notable event. manually created ("Finished my first novel") or auto-generated on lifetime goal achievement.
    CREATE TABLE IF NOT EXISTS milestones (
        id              INTEGER PRIMARY KEY,
        title           TEXT NOT NULL,
        date            TEXT NOT NULL,
        goal_id         INTEGER,        -- nullable FK
        
        -- snapshot of the metric
        metric          TEXT,
        metric_value    INTEGER,
        
        -- Filters used to traceback contributing sessions as JSON to reconstruct query
        -- e.g. {"medium_type": "light_novel", "start_date": "2024-01-01", "title_id": 15}
        filter_json     TEXT,
        
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_milestones_date ON milestones(date);
    """

    cur.executescript(query_goals)
    cur.executescript(query_goal_log)
    cur.executescript(query_milestones)


def _create_settings_table(cur: sqlite3.Cursor):
    query_settings = """
    -- ===== SETTINGS =====
    -- Key-value with TEXT values; just INSERT to add a new setting
    CREATE TABLE IF NOT EXISTS settings (
        key         TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    -- DEFAULTS.
    INSERT OR IGNORE INTO settings (key, value) VALUES ('active_day_minutes', '15');
    """

    cur.executescript(query_settings)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at schema version {SCHEMA_VERSION}: {DB_NAME}")
