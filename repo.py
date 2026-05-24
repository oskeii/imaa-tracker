from db import get_connection, ENUMS
from datetime import date, timedelta

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
def get_all_titles(medium_type: str = None) -> list[dict]:
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
    data = {col: None for col in TITLES_COLS}
    data.update({'name': name, 'medium_type': medium_type, **kwargs})
    col_str = ", ".join(TITLES_COLS.keys())
    placeholders = ", ".join(f":{_}" for _ in TITLES_COLS.keys())

    conn = get_connection()
    cur = conn.execute(f"INSERT INTO titles ({col_str}) VALUES ({placeholders})", data)
    conn.commit()
    title_id = cur.lastrowid
    conn.close()
    return title_id


def get_or_create_title(name: str, medium_type: str) -> int:
    """Find an existing title by name & medium, else create new title. Returns ID"""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM titles WHERE name = ? AND medium_type = ?",
        (name, medium_type)
    ).fetchone()
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
def add_immersion_session(date_str: str, title_text: str, medium_type: str, activity_type: str = "reading", **kwargs) -> int:
    """Insert a new immersion session. Returns the session ID."""
    data = {col: None for col in IMMERSION_SESSIONS_COLS}
    data.update({'date': date_str, 'title_text': title_text, 'medium_type': medium_type, 'activity_type': activity_type, **kwargs})
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


def get_immersion_sessions(
        start_date: str = None,
        end_date: str = None,
        medium_type: str = None,
        activity_type: str = None,
        title_id: int = None,
        limit: int = 200, offset: int = 0
) -> list[dict]:
    """Fetch immersion sessions with optional filters."""
    conn = get_connection()
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

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_immersion_session(session_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM immersion_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def update_immersion_session(session_id: int, **fields) -> None:
    """
    Update field(s) of a single immersion session.
    Returns the updated session.
    """
    updates = {k: v for k, v in fields.items() if k in IMMERSION_SESSIONS_COLS}
    print(f"UPDATING SESSION (ID:{session_id}):\n\t{updates}")
    if not updates:
        return {}

    set_str = ", ".join(f"{k} = :{k}" for k in updates)
    sql = f"""
        UPDATE immersion_sessions
        SET {set_str} 
        WHERE id  = {session_id}
    """

    conn = get_connection()
    conn.execute(sql, updates)
    conn.commit()
    conn.close()


def bulk_update_immersion_sessions(session_ids: list[int], **fields) -> dict:
    """
    Update multiple sessions with the same field values.
    Returns number of rows updated, session IDs, and updated field values.
    DO NOT pass title_id directly for bulk updates, unless certain it applies to every selected session.
    """
    results = {
        "count": 0,
        "sessions": [],
        "fields": {}
    }
    updates = {k: v for k, v in fields.items() if k in IMMERSION_SESSIONS_COLS}
    print(f"UPDATING SESSIONS: \nIDs:{session_ids} \nUPDATES: \n\t{updates}")
    if not updates or not session_ids:
        return results

    set_str = ", ".join(f"{k} = :{k}" for k in updates)
    id_str = ", ".join(str(i) for i in session_ids)
    sql = f"""
        UPDATE immersion_sessions
        SET {set_str}
        WHERE id  IN ({id_str})
    """

    conn = get_connection()
    rows = conn.execute(sql, updates).fetchall()
    conn.commit()
    conn.close()

    results["count"] = len(rows)
    results["sessions"] = [r[0] for r in rows]
    results["fields"] = updates
    return results


def bulk_delete_immersion_sessions(session_ids: list[int]) -> int:
    """Delete multiple sessions. Returns count deleted."""
    if not session_ids:
        return 0

    placeholders = ", ".join("?" for _ in session_ids)
    conn = get_connection()
    cur = conn.execute(
        f"DELETE FROM immersion_sessions WHERE id IN ({placeholders})",
        session_ids
    )
    conn.commit()
    count = cur.rowcount
    conn.close()
    return count


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


# ------------------------------------------
# DASHBOARD QUERIES
# __________________________________________
def get_daily_summary(target_date: str = None) -> dict:
    """Stats summary for a single day: total time, character count, sessions, and breakdown by activity
    target_date (ISO string) set to today if not provided.
    """
    if target_date is None:
        target_date = date.today().isoformat()
    conn = get_connection()

    totals_row = conn.execute("""
        SELECT
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
            COALESCE(SUM(character_count), 0)   AS total_chars,
            COUNT(*)                            AS session_count
        FROM immersion_sessions
        WHERE date = ?
    """, (target_date,)).fetchone()

    activity_rows = conn.execute("""
        SELECT activity_type,
            COALESCE(SUM(duration_minutes), 0) AS minutes
        FROM immersion_sessions
        WHERE date = ?
        GROUP BY activity_type
    """, (target_date,)).fetchall()

    conn.close()
    return {
        "date": target_date,
        "total_minutes": totals_row["total_minutes"],
        "total_chars": totals_row["total_chars"],
        "session_count": totals_row["session_count"],
        "by_activity": {row["activity_type"]: row["minutes"] for row in activity_rows},
    }


def get_weekly_summary(week_of: str = None) -> dict:  # !TODO!
    """
    Stats summary for a given week, Monday start. (i.e. total time, character count, sessions, and breakdown by activity)
    week_of (ISO string) can be any date within the target week. uses today's date if not provided
    """
    if week_of is None:
        week_of = date.today()

    return {
        "week_start": "",
        "week_end": "",
        "total_minutes": 0,
        "total_chars": 0,
        "session_count": 0
    }


def get_alltime_totals() -> dict:
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
            COALESCE(SUM(character_count), 0)   AS total_chars,
            COUNT(*)                            AS session_count,
            MIN(date)                           AS first_session,
            MAX(date)                           AS last_session,
            COUNT(DISTINCT date)                AS active_days
        FROM immersion_sessions
    """).fetchone()
    active_rows = conn.execute("""
        SELECT date,
            COALESCE(SUM(duration_minutes), 0)  AS daily_minutes
        FROM immersion_sessions
        GROUP BY date
        HAVING daily_minutes >= 30
    """).fetchall()
    # print(f"ACTIVE DAYS ({len(active_rows)}):", [dict(r) for r in active_rows])

    titles_rows = conn.execute("""
        SELECT medium_type,
            COUNT(DISTINCT title_id) AS title_count
        FROM immersion_sessions
        GROUP BY medium_type ORDER BY title_count DESC
    """).fetchall()
    print("TITLE COUNT BY MEDIUM:", [dict(row) for row in titles_rows])

    conn.close()
    return dict(row)


def get_time_by_medium(start_date: str, end_date: str, activity: str = None) -> list[dict]:
    """
    Immersion time grouped by medium type
    Returns: [{"medium_type": "novel", "total_minutes": 1234, "session_count": 62}, ...]
    """
    # !TODO! filter by activity
    conn = get_connection()
    sql = """
        SELECT medium_type,
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
            COUNT(*)                            AS session_count
        FROM immersion_sessions WHERE 1=1
    """
    params = []

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    sql += " GROUP BY medium_type ORDER BY total_minutes DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_time_by_medium_monthly(start_date: str, end_date: str, activity: str = None) -> dict:
    """
    Immersion time by medium, grouped by month
    Returns: {"2026-04": {"novel": 1234, "anime": 234,...}, "2026-05": {...}, ...}
    """
    # !TODO! filter by activity
    conn = get_connection()
    sql = """
        SELECT strftime('%Y-%m', date) AS month,
            medium_type,
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes
        FROM immersion_sessions WHERE 1=1
    """
    params = []

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    sql += " GROUP BY month, medium_type ORDER BY month DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    print("STACKED TIME BY MEDIUM:", [dict(r) for r in rows])

    # pivot: convert rows into {month: {medium_a: X, medium_b: Y, medium_c: Z, ...}}
    from collections import defaultdict
    periods = defaultdict(lambda: {medium: 0 for medium in ENUMS["MEDIUM_TYPES"]})
    for r in rows:
        periods[r["month"]][r["medium_type"]] += r["total_minutes"]

    print()
    print(dict(periods))

    return dict(periods)


def get_activity_breakdown(start_date: str, end_date: str, group_by="month") -> dict:
    """
    Total minutes grouped by activity
    Returns: {"2026-04": {"reading": 120, "listening": 80, "both": 30, "session_count": 40}, ... }
    """
    conn = get_connection()

    if group_by == "week":
        period_expr = "date(date, 'weekday 0', '-6 days')"
    elif group_by == "month":
        period_expr = "strftime('%Y-%m', date)"
    else:
        period_expr = "'all-time'"

    sql = f"""
        SELECT {period_expr} AS period, 
            activity_type,
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
            COUNT(*)                            AS session_count
        FROM immersion_sessions WHERE 1=1
    """
    params = []

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    sql += " GROUP BY period, activity_type ORDER BY period"
    rows = conn.execute(sql, params).fetchall()
    # print(f"ACTIVITY BREAKDOWN ({len(rows)}):", [dict(r) for r in rows])
    conn.close()

    # pivot: convert rows into {period: {reading: X, listening: Y, both: Z, session_count: 123}}
    from collections import defaultdict
    periods = defaultdict(lambda: {"reading": 0, "listening": 0, "both": 0, "session_count": 0})
    for r in rows:
        periods[r["period"]][r["activity_type"]] += r["total_minutes"]
        periods[r["period"]]["session_count"] += r["session_count"]

    print(f"ACTIVITY BREAKDOWN ({len(periods)}):",)
    print(dict(periods))

    return dict(periods)


def get_daily_totals(start_date: str, end_date: str) -> list[dict]:
    """
    Daily aggregates for time trend charts
    Returns: [{"date": "2026-04-01", "total_minutes": 78, "total_chars": 3665, "session_count": 2}, ...]
    """
    conn = get_connection()
    sql = """
        SELECT date,
            COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
            COALESCE(SUM(character_count), 0)   AS total_chars,
            COUNT(*)                            AS session_count
        FROM immersion_sessions WHERE 1=1
    """
    params = []
    if start_date:
        params.append(start_date)
        sql += " AND date >= ?"
    if end_date:
        params.append(end_date)
        sql += " AND date <= ?"
    sql += " GROUP BY date ORDER BY date"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_reading_speed_data(start_date: str, end_date: str) -> list[dict]:
    conn = get_connection()
    sql = """
        SELECT  date, title_text, title_id, medium_type, reading_direction,
                duration_minutes, character_count
        FROM immersion_sessions
        WHERE character_count IS NOT NULL
            AND character_count > 0
            AND duration_minutes IS NOT NULL
            AND duration_minutes > 0
    """
    params = []
    if start_date:
        params.append(start_date)
        sql += " AND date >= ?"
    if end_date:
        params.append(end_date)
        sql += " AND date <= ?"
    sql += " ORDER BY date"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

