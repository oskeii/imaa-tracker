"""Immersion sessions"""
import uuid as _uuid

from imaa_tracker.core.utils.text import normalize_title
from imaa_tracker.core.constants import ENUMS
from imaa_tracker.core.db import connect

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
    "notes": {"type": str},
    "uuid": {"type": str},
}
IMMUTABLE_COLS = {"uuid"}


def add_immersion_session(date_str: str, title_text: str, medium_type: str, activity_type: str = "reading", **kwargs) -> int:
    """Insert a new immersion session. Returns the session ID."""
    data = {col: None for col in IMMERSION_SESSIONS_COLS}
    data.update({'date': date_str, 'title_text': title_text, 'medium_type': medium_type, 'activity_type': activity_type, **kwargs})
    if not data.get("uuid"):
        data["uuid"] = str(_uuid.uuid4())  # random, no ancestor to coordinate with

    col_str = ", ".join(IMMERSION_SESSIONS_COLS.keys())
    placeholders = ", ".join(f":{_}" for _ in IMMERSION_SESSIONS_COLS.keys())
    sql = f"""
        INSERT INTO immersion_sessions
        ({col_str})
        VALUES ({placeholders})
    """
    with connect() as conn:
        cur = conn.execute(sql, data)
        session_id = cur.lastrowid
        return session_id


def get_immersion_sessions(
        start_date: str = None,
        end_date: str = None,
        medium_type: str = None,
        activity_type: str = None,
        title_id: int = None,
        limit: int = 200, offset: int = 0
) -> list[dict]:
    """Fetch immersion sessions with optional filters."""
    sql = "SELECT * FROM immersion_sessions WHERE 1=1"
    params = []

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    if medium_type:
        sql += " AND medium_type = ?"
        params.append(medium_type)
    if activity_type:
        sql += " AND activity_type = ?"
        params.append(activity_type)
    if title_id:
        sql += " AND title_id = ?"
        params.append(title_id)

    sql += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_immersion_session_by_id(session_id: int) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM immersion_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        return dict(row)


def delete_immersion_session(session_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM immersion_sessions WHERE id = ?", (session_id,))


def update_immersion_session(session_id: int, **fields) -> None:
    """
    Update field(s) of a single immersion session.
    Returns the updated session.
    """
    updates = {k: v for k, v in fields.items() if k in IMMERSION_SESSIONS_COLS and k not in IMMUTABLE_COLS}
    if not updates:
        return
    if "title_text" in updates:
        updates["title_text"] = normalize_title(updates["title_text"])

    set_str = ", ".join(f"{k} = :{k}" for k in updates)
    sql = f"""
        UPDATE immersion_sessions
        SET {set_str} 
        WHERE id  = :id
    """

    with connect() as conn:
        conn.execute(sql, {**updates, "id": session_id})


def bulk_update_immersion_sessions(session_ids: list[int], **fields) -> int:
    """
    Update multiple sessions with the same field values.
    Returns count updated.
    DO NOT pass title_id directly for bulk updates, unless certain it applies to every selected session.
    """
    updates = {k: v for k, v in fields.items() if k in IMMERSION_SESSIONS_COLS and k not in IMMUTABLE_COLS}
    if not updates or not session_ids:
        return 0

    if "title_text" in updates:
        updates["title_text"] = normalize_title(updates["title_text"])
    set_str = ", ".join(f"{k} = :{k}" for k in updates)
    id_params = {f"bulk_id_{i}": sid for i, sid in enumerate(session_ids)}
    id_str = ", ".join(f":{k}" for k in id_params)
    sql = f"""
        UPDATE immersion_sessions
        SET {set_str}
        WHERE id  IN ({id_str})
    """
    # !! limit number of session ids per update query
    with connect() as conn:
        cur = conn.execute(sql, {**updates, **id_params})
        count = cur.rowcount
        return count


def bulk_delete_immersion_sessions(session_ids: list[int]) -> int:
    """Delete multiple sessions. Returns count deleted."""
    if not session_ids:
        return 0

    placeholders = ", ".join("?" for _ in session_ids)
    with connect() as conn:
        cur = conn.execute(
            f"DELETE FROM immersion_sessions WHERE id IN ({placeholders})",
            session_ids
        )
        count = cur.rowcount
        return count
