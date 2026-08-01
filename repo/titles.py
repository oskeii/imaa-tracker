"""Titles - the catalogue of media the user immerses in."""
from constants import ENUMS
from db import connect

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


def get_all_titles(medium_type: str = None) -> list[dict]:
    """Fetch all titles, optionally filtered by medium type."""
    with connect() as conn:
        if medium_type:
            rows = conn.execute(
                "SELECT * FROM titles WHERE medium_type = ? ORDER BY name",
                (medium_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM titles ORDER BY name").fetchall()

    return [dict(r) for r in rows]


def search_titles(query: str, medium_type: str = None) -> list[dict]:
    """Search titles by name (substring match), optionally filter by medium type"""
    sql = "SELECT * FROM titles WHERE name LIKE ?"
    params = [f"%{query}%"]
    if medium_type:
        sql += " AND medium_type = ?"
        params.append(medium_type)
    sql += " ORDER BY name LIMIT 20"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def add_title(name: str, medium_type: str, **kwargs) -> int:
    """Insert a new title. Returns the new title's ID."""
    data = {col: None for col in TITLES_COLS}
    data.update({'name': name, 'medium_type': medium_type, **kwargs})
    col_str = ", ".join(TITLES_COLS.keys())
    placeholders = ", ".join(f":{_}" for _ in TITLES_COLS.keys())

    with connect() as conn:
        cur = conn.execute(f"INSERT INTO titles ({col_str}) VALUES ({placeholders})", data)
        title_id = cur.lastrowid
        return title_id


def get_or_create_title(name: str, medium_type: str) -> int:
    """Find an existing title by name & medium, else create new title. Returns ID"""
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM titles WHERE name = ? AND medium_type = ?",
            (name, medium_type)
        ).fetchone()
        if row:
            return row["id"]

        cur = conn.execute(
            "INSERT INTO titles (name, medium_type) VALUES (?, ?)",
            (name, medium_type)
        )
        title_id = cur.lastrowid
        print("TITLE CREATED:", title_id)
        return title_id
