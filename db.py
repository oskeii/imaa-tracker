"""DATABASE SCHEMA VERSION 0.1.1"""
import sqlite3

DB_NAME = "imaa_tracker.db"
ENUMS = {
    "API_LIST": [
        "anilist",
        "vndb",
        "tmdb",
        "igdb",
        "google_books",
    ],
    "MEDIUM_TYPES": [
        "anime",
        "drama",
        "visual_novel",
        "light_novel",
        "novel",
        "book",
        "manga",
        "game",
        "podcast",
        "audiobook",
        "youtube",
    ],
    "ACTIVITY_TYPES": ["reading", "listening", "both"],
    # "READING_DIRECTIONS": ["horizontal", "vertical"],
    "RESOURCE_TYPES": ["textbook", "workbook", "drills", "video_course", "app", "mock_exam", "other"],
    "RESOURCE_LEVELS": ["N5", "N4", "N3", "N2", "N1", "beginner", "intermediate", "advanced"],
    "STUDY_TYPES": ["anki", "textbook", "video", "grammar", "kanji", "vocab", "other"],
    "TOPIC_AREAS": ["vocab", "kanji", "grammar", "reading_comp", "listening_comp", "other"],
    "GOAL_TYPES": ["recurring", "lifetime"],
    "GOAL_METRICS": [
        "duration_minutes",
        "character_count",
        "episode_count",
        "page_count",
        "session_count",
    ],
    "GOAL_PERIODS": ["daily", "weekly", "monthly"],
}


def get_connection(db_path=DB_NAME) -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row

        return conn
    except Exception as e:
        print(f"Error: {e}")
        raise


def init_db(db_path=DB_NAME):
    conn = get_connection(db_path)
    cur = conn.cursor()

    try:
        # TITLES, IMMERSION SESSIONS
        _create_immersion_tables(cur)
        # RESOURCES, STUDY SESSIONS, JLPT SCORES
        _create_study_tables(cur)
        # GOALS, GOAL LOG, MILESTONES
        _create_goals_tables(cur)

        # TBD: languages, output sessions
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        conn.commit()
        conn.close()


def _create_immersion_tables(cur: sqlite3.Cursor):
    query_titles = """
    -- ===== TITLES =====
    -- Media titles for immersion. 
    -- One entry per distinct consumable unit. e.g. "Re:Zero (LN)" and "Re:Zero (Anime)" are separate titles.
    -- YouTube channels and content categories can also be titles.
    CREATE TABLE IF NOT EXISTS titles (
        id				    INTEGER PRIMARY KEY,
        name			    TEXT NOT NULL,
        medium_type		    TEXT NOT NULL,	-- see MEDIUM_TYPES
        
        -- Optional metadata (populated manually or via API)
        genre			    TEXT,	-- comma-separated
        tags			    TEXT,	-- comma-separated
        cover_image		    TEXT,	-- file path or URL
       
        --      External API details
        api			        TEXT,	-- see API_LIST
        api_id		        TEXT,
        youtube_channel_id	TEXT,  -- for YT channel-type titles
        youtube_url		    TEXT,		-- channel URL
        
        notes		        TEXT,
        created_at	        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_titles_name ON titles(name);
    CREATE INDEX IF NOT EXISTS idx_titles_medium ON titles(medium_type);
    """

    query_immersion_sessions = """
    -- ===== IMMERSION SESSIONS =====
    CREATE TABLE IF NOT EXISTS immersion_sessions (
        id				    INTEGER PRIMARY KEY,
        date			    TEXT NOT NULL,  -- ISO date YYYY-MM-DD
        title_id            INTEGER,    -- FK to titles (nullable for quick-log)
        title_text          TEXT,   -- denormalized title for quick-log/display
        
        medium_type         TEXT NOT NULL,  -- denormalized
        activity_type       TEXT NOT NULL DEFAULT 'reading',    -- reading | listening | both
        
        -- Metrics (fill what applies)
        duration_minutes    INTEGER,
        character_count     INTEGER,
        page_count          INTEGER,
        episode_count       INTEGER,
        
        reading_direction   TEXT,   -- horizontal | vertical
        
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

    try:
        cur.executescript(query_titles)
        print("'Titles' table was created!")

        cur.executescript(query_immersion_sessions)
        print("'Immersion Sessions' table was created!")
    except Exception as e:
        print(f"Error: {e}")
        raise


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

    query_jlpt_scores = """
    -- ===== JLPT SCORES =====
    -- Mock exam results. One row per exam sitting.
    CREATE TABLE IF NOT EXISTS jlpt_scores (
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
    CREATE INDEX IF NOT EXISTS idx_jlpt_date ON jlpt_scores(date);
    CREATE INDEX IF NOT EXISTS idx_jlpt_level ON jlpt_scores(level);
    """

    try:
        cur.executescript(query_resources)
        print("'Resources' table was created!")

        cur.executescript(query_study_sessions)
        print("'Study Sessions' table was created!")

        cur.executescript(query_jlpt_scores)
        print("'JLPT Scores' table was created!")
    except Exception as e:
        print(f"Error: {e}")
        raise


def _create_goals_tables(cur: sqlite3.Cursor):
    query_goals = """
    -- ===== GOALS =====
    -- A goal is a rule: a metric, a target, and optionally a recurring period.
    -- "Read 15k characters per day" or "Reach 1 million characters total."
    
    """

    query_goal_log = """
    -- ===== GOAL LOG =====
    -- One row per goal per completed period. Records whether the goal was
    -- hit and the actual value reached.
    --
    -- For recurring goals: period_date is the start of the period
    --   (the date itself for daily, Monday for weekly, 1st for monthly).
    -- For lifetime goals: one row created when achieved.
    
    """

    query_milestones = """
    -- ===== MILESTONES =====
    -- A milestone is an event: something notable that happened at a point in time.
    -- Can be manually created ("Finished my first novel") or auto-generated
    -- when a lifetime goal is achieved.
    """


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DB_NAME}")
