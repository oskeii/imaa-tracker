"""Dashboard aggregation queries. Read-only reports."""
from datetime import date, timedelta

from imaa_tracker.core.constants import ENUMS
from imaa_tracker.core.db import connect


def get_daily_summary(target_date: str = None) -> dict:
    """Stats summary for a single day: total time, character count, sessions, and breakdown by activity
    target_date (ISO string) set to today if not provided.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    with connect() as conn:
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

        return {
            **totals_row,
            "date": target_date,
            "by_activity": {row["activity_type"]: row["minutes"] for row in activity_rows},
        }


def get_weekly_summary(week_of: str = None) -> dict:
    """
    Stats summary for a given week, Monday start. (i.e. total time, character count, sessions, and breakdown by activity)
    week_of (ISO string) can be any date within the target week. uses today's date if not provided
    Returns: {
        "week_start": (Monday ISO date),
        "week_end": (Sunday ISO date),
        "total_minutes": 0,
        "total_chars": 0,
        "session_count": 0,
        "by_activity": {"reading": 0, "listening": 0, "both": 0},
        "daily_avg": {
            "minutes": 0,
            "chars": 0,
            "reading_minutes": 0,
            "listening_minutes": 0,
        },
        "daily_minutes": {
            "2026-03-30": {"reading": 0, "listening": 0, "both": 0},
            "2026-03-31": {"reading": 0, "listening": 0, "both": 0},
            ...,
        },
        "daily_chars": {
            "2026-03-30": {"reading": 0, "listening": 0, "both": 0},
            "2026-03-31": {"reading": 0, "listening": 0, "both": 0},
            ...,
        }
    }
    """
    if week_of is None:
        target = date.today()
    else:
        target = date.fromisoformat(week_of)

    week_start = target - timedelta(days=target.weekday())
    week_end = week_start + timedelta(days=6)
    days = [(week_start + timedelta(days=i)).isoformat() for i in range(7)]

    with connect() as conn:
        rows = conn.execute("""
            SELECT  date,
                    activity_type,
                    COALESCE(SUM(duration_minutes), 0)  AS minutes,
                    COALESCE(SUM(character_count), 0)  AS chars,
                    COUNT(*) AS sessions
            FROM immersion_sessions
            WHERE date >= ? AND date <= ?
            GROUP BY date, activity_type
        """, (week_start.isoformat(), week_end.isoformat())).fetchall()
    # print("GET WEEKLY SUMMARY:\n", [dict(r) for r in rows])

    daily_minutes = {d: {"reading": 0, "listening": 0, "both": 0} for d in days}
    daily_chars = {d: 0 for d in days}
    total_minutes, total_chars, session_count = 0, 0, 0
    weekly_min_by_activity = {"reading": 0, "listening": 0, "both": 0}

    for r in rows:
        d = r["date"]
        act = r["activity_type"]
        mins = r["minutes"]
        chars = r["chars"]
        sessions = r["sessions"]

        total_minutes += mins
        total_chars += chars
        session_count += sessions

        weekly_min_by_activity[act] += mins
        daily_minutes[d][act] += mins
        daily_chars[d] += chars

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_minutes": total_minutes,
        "total_chars": total_chars,
        "session_count": session_count,
        "by_activity": weekly_min_by_activity,
        "daily_avg": {
            "minutes": round(total_minutes/7),
            "chars": round(total_chars/7),
            "reading_minutes": round(weekly_min_by_activity["reading"]/7),
            "listening_minutes": round(weekly_min_by_activity["listening"]/7),
        },
        "daily_minutes": daily_minutes,
        "daily_chars": daily_chars
    }


def get_alltime_totals() -> dict:
    with connect() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(duration_minutes), 0)  AS total_minutes,
                COALESCE(SUM(character_count), 0)   AS total_chars,
                COUNT(*)                            AS session_count,
                MIN(date)                           AS first_session,
                MAX(date)                           AS last_session,
                COUNT(DISTINCT date)                AS days_since_start,
                COUNT(DISTINCT title_id)            AS title_count,
                COALESCE(SUM(episode_count), 0)     AS total_episodes,
                COALESCE(SUM(page_count), 0)        AS total_pages
            FROM immersion_sessions
        """).fetchone()
        active_days = conn.execute("""
            SELECT date,
                COALESCE(SUM(duration_minutes), 0)  AS daily_minutes
            FROM immersion_sessions
            GROUP BY date
            HAVING daily_minutes >= 15
        """).fetchall()

        activity_rows = conn.execute("""
            SELECT activity_type,
                COALESCE(SUM(duration_minutes), 0)  AS minutes,
                COUNT(*)                            AS session_count
            FROM immersion_sessions
            GROUP BY activity_type
        """).fetchall()

    # titles_row = conn.execute("SELECT COUNT(*) AS title_count FROM titles WHERE medium_type != 'youtube'").fetchone()
    # print("Num of Titles (excl. youtube):", titles_row['title_count'])
    return {
        **row,
        "active_days": len(active_days),
        "by_activity": {row["activity_type"]: row["minutes"] for row in activity_rows},
    }


def get_activity_breakdown(start_date: str, end_date: str, group_by="month") -> dict:
    """
    Total minutes grouped by activity
    Returns: {"2026-04": {"reading": 120, "listening": 80, "both": 30, "session_count": 40}, ... }
    """
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
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    # print(f"ACTIVITY BREAKDOWN ({len(rows)}):", [dict(r) for r in rows])

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

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_reading_speed_data(start_date: str, end_date: str) -> list[dict]:
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

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_time_by_medium(start_date: str, end_date: str, activity: str = None) -> list[dict]:
    """
    Immersion time and session count grouped by medium type
    Returns: [{"medium_type": "novel", "total_minutes": 1234, "session_count": 62}, ...]
    """
    # !TODO! filter by activity
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

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_time_by_medium_monthly(start_date: str, end_date: str, activity: str = None) -> dict:
    """
    Immersion time by medium, grouped by month
    Returns: {"2026-04": {"novel": 1234, "anime": 234,...}, "2026-05": {...}, ...}
    """
    # !TODO! filter by activity
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

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    print("STACKED TIME BY MEDIUM:", [dict(r) for r in rows])

    # pivot: convert rows into {month: {medium_a: X, medium_b: Y, medium_c: Z, ...}}
    from collections import defaultdict
    periods = defaultdict(lambda: {medium: 0 for medium in ENUMS["MEDIUM_TYPES"]})
    for r in rows:
        periods[r["month"]][r["medium_type"]] += r["total_minutes"]

    print()
    print(dict(periods))

    return dict(periods)
