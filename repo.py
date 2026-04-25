import random
import sqlite3
from db import get_connection, DB_NAME, ENUMS

TITLES_COLS = {
    "name": {"type": str},
    "medium_type": {
        "type": str,
        "enums": ENUMS["MEDIUM_TYPES"]
    },
    "genre": {"type": str}, "tags": {"type": str},
    "cover_image": {"type": str},
    "api": {
        "type": str,
        "enums": ENUMS["API_LIST"]
    }, "api_id": {"type": str},
    "youtube_channel_id": {"type": str}, "youtube_url": {"type": str},
    "notes": {"type": str}
}
IMMERSION_SESSIONS_COLS = {
    "date": {
        "type": str,  # ISO date YYYY-MM-DD
    },
    "title_id": {"type": int}, "title_text": {"type": str},
    "medium_type": {
        "type": str,
        "enums": ENUMS["MEDIUM_TYPES"]
    },
    "activity_type": {
        "type": str,
        "enums": ENUMS["ACTIVITY_TYPES"]
    },
    "duration_minutes": {"type": int},
    "character_count": {"type": int}, "page_count": {"type": int}, "episode_count": {"type": int},
    "reading_direction": {
        "type": str,
        "enums": ["horizontal", "vertical"]
    },
    "volume": {"type": str}, "chapter": {"type": str}, "episode_name": {"type": str},
    "urls_json": {"type": str},
    "notes": {"type": str}
}
RESOURCES_COLS = {
    "name": {"type": str},
    "resource_type": {
        "type": str,
        "enums": ENUMS["RESOURCE_TYPES"]
    },
    "level": {
        "type": str,
        "enums": ENUMS["RESOURCE_LEVELS"]
    },
    "cover_image": {"type": str},
    "url": {"type": str},
    "notes": {"type": str}
}
STUDY_SESSIONS_COLS = {
    "date": {"type": str},
    "study_type": {
        "type": str,
        "enums": ENUMS["STUDY_TYPES"]
    },
    "resource_id": {"type": str}, "resource_text": {"type": str},
    "durations_minutes": {"type": int},
    "anki_deck": {"type": str}, "anki_reviews": {"type": int}, "anki_new_cards": {"type": int},
    "topic_area": {
        "type": str,
        "enums": ENUMS["TOPIC_AREAS"]
    },
    "notes": {"type": str}
}


# ------------------------------------------
# TITLES
# __________________________________________
def get_all_titles(medium_type: str) -> list[dict]:
    """Fetch all titles, optionally filtered by medium type."""
    conn = get_connection()
    if medium_type:
        rows = conn.execute(
            "SELECT * FROM titles WHERE medium_type = ? ORDER BY name",
            (medium_type,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM titles ORDER BY name").fetchall()
    conn.close()

    return [dict(r) for r in rows]


def add_title(name: str, medium_type: str, **kwargs) -> int:
    """Insert a new title. Returns the new title's ID."""
    pass


def get_or_create_title(name: str, medium_type: str) -> int:
    """Find an existing title by name & medium, else create new title. Returns ID"""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM titles WHERE name = ? AND medium_type = ?",
        (name, medium_type)
    ).fetchone()
    print("TITLE ROW?", row)
    if row:
        conn.close()
        return row["id"]

    cur = conn.execute(
        "INSERT INTO titles (name, medium_type) VALUES (?, ?)",
        (name, medium_type)
    )
    conn.commit()
    title_id = cur.lastrowid
    conn.close()
    print("TITLE CREATED:", title_id)
    return title_id


# ------------------------------------------
# IMMERSION SESSIONS
# __________________________________________
def add_immersion_session(date_str: str, medium_type: str, activity_type: str = "reading", **kwargs) -> int:
    """Insert a new immersion session. Returns the session ID."""
    data = {'date': date_str, 'medium_type': medium_type, 'activity_type': activity_type, **kwargs}
    print(f"RECEIVED NEW SESSION: {data}")

    col_str = ", ".join(IMMERSION_SESSIONS_COLS.keys())
    placeholders = ", ".join(f":{_}" for _ in IMMERSION_SESSIONS_COLS.keys())
    sql = f"""
        INSERT INTO immersion_sessions
        ({col_str})
        VALUES ({placeholders})
    """

    conn = get_connection()
    cur = conn.execute(sql, data)
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


def get_immersion_sessions(limit: int = 200, offset: int = 0) -> list[dict]:
    """Fetch immersion sessions with optional filters."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM immersion_sessions ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------
# RESOURCES
# __________________________________________
def add_resource(name: str, resource_type: str, **kwargs) -> int:
    """Insert a new resource. Returns the resource's ID."""
    pass


# ------------------------------------------
# STUDY SESSIONS
# __________________________________________
def add_study_session(date_str: str, study_type: str, **kwargs) -> int:
    """Insert a new study session. Returns the session ID."""
    pass
