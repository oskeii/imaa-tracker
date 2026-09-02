-- Schema version 0: a snapshot of db.py as it existed BEFORE the migration system.
-- Used by tests/test_migrations.py as the starting point to migrate from.
-- DO NOT EDIT.

CREATE TABLE exam_scores (
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

CREATE TABLE goal_log (
        id              INTEGER PRIMARY KEY,
        goal_id         INTEGER NOT NULL,
        period_date     TEXT NOT NULL,      -- start of the period (YYYY-MM-DD)
        actual_value    INTEGER NOT NULL,
        target_value    INTEGER NOT NULL,   -- snapshot of target value
        is_achieved     BOOLEAN NOT NULL CHECK (is_achieved IN (0,1)),
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
    );

CREATE TABLE goals (
        id              INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,      -- e.g. "Daily reading goal", "300 immersion hours", "200 listening hours"
        goal_type       TEXT NOT NULL,      -- recurring | lifetime
        metric          TEXT NOT NULL,      -- see METRIC_TYPES
        target_value    INTEGER NOT NULL,
        period          TEXT,               -- daily | weekly | monthly (null for lifetime goal)
        
        -- Optional filters
        medium_type     TEXT,   -- null = any medium
        activity_type   TEXT,   -- null = any activity
        
        -- Habit health window (for recurring goals)
        health_window_days  INTEGER DEFAULT 60,     -- health percentage calculated based on  the last N days
        
        is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
        achieved_at     TEXT,       -- for lifetime goal (ISO datetime)
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

CREATE TABLE immersion_sessions (
        id				    INTEGER PRIMARY KEY,
        date			    TEXT NOT NULL,  -- ISO date YYYY-MM-DD
        title_id            INTEGER,    -- FK to titles (nullable for quick-log)
        title_text          TEXT NOT NULL,   -- denormalized title for quick-log/display
        
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

CREATE TABLE milestones (
        id              INTEGER PRIMARY KEY,
        title           TEXT NOT NULL,
        date            TEXT NOT NULL,
        goal_id         INTEGER,        -- nullable FK
        
        -- snapshot of the metric
        metric          TEXT,
        metric_value    INTEGER,
        
        -- Filters used to traceback contributing sessions
        -- Stored as JSON to reconstruct query
        -- e.g. {"medium_type": "light_novel", "start_date": "2024-01-01", "title_id": 15}
        filter_json     TEXT,
        
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
    );

CREATE TABLE resources (
        id              INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,
        resource_type   TEXT NOT NULL,  -- see RESOURCE_TYPES
        level           TEXT,   -- see RESOURCE_LEVELS
        cover_image     TEXT,   
        url             TEXT,   -- link if online resource
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

CREATE TABLE study_sessions (
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

CREATE TABLE titles (
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

CREATE INDEX idx_exam_date ON exam_scores(date);

CREATE INDEX idx_exam_level ON exam_scores(level);

CREATE INDEX idx_goallog_date ON goal_log(period_date);

CREATE INDEX idx_goallog_goal ON goal_log(goal_id);

CREATE UNIQUE INDEX idx_goallog_unique ON goal_log(goal_id, period_date);

CREATE INDEX idx_milestones_date ON milestones(date);

CREATE INDEX idx_sessions_activity ON immersion_sessions(activity_type);

CREATE INDEX idx_sessions_date ON immersion_sessions(date);

CREATE INDEX idx_sessions_medium ON immersion_sessions(medium_type);

CREATE INDEX idx_sessions_title ON immersion_sessions(title_id);

CREATE INDEX idx_study_date ON study_sessions(date);

CREATE INDEX idx_study_resource ON study_sessions(resource_id);

CREATE INDEX idx_study_type ON study_sessions(study_type);

CREATE INDEX idx_titles_medium ON titles(medium_type);

CREATE INDEX idx_titles_name ON titles(name);
